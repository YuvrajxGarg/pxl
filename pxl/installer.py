"""Finds, installs, updates, opens and removes apps on macOS and Windows.

Install types (the "type" of a platform in apps.json):

  app-zip     macOS. A zip holding "<Name>.app". Unpacked with ditto, checked against
              its bundle id, then swapped into /Applications (or ~/Applications).
  folder-zip  Windows. A zip holding a "<Name>" folder with <exe> inside. Unpacked to
              %LOCALAPPDATA%\\Programs\\<Name>, with a Start menu shortcut.
  nsis        Windows. An NSIS installer (electron-builder). Run silently with /S;
              found again through its entry in the registry's Uninstall list.
"""

import os
import platform
import plistlib
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

from .catalog import PLATFORM
from .net import NetError, download, log, verify_sha256

NO_WINDOW = 0x08000000 if os.name == "nt" else 0


class InstallError(Exception):
    pass


def _run(args, timeout=60, **kw):
    if os.name == "nt":
        kw.setdefault("creationflags", NO_WINDOW)
    return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, **kw)


# ---------------------------------------------------------------------------
# compatibility
# ---------------------------------------------------------------------------

def compatible(spec):
    """None when this computer can run the app, otherwise a short reason."""
    if not spec:
        return "Not available for %s yet" % ("Mac" if PLATFORM == "mac" else "Windows" if PLATFORM == "windows" else "this system")
    if PLATFORM == "mac":
        need = spec.get("min_os")
        have = platform.mac_ver()[0]
        if need and have:
            from .net import is_newer
            if is_newer(need, have):
                return "Needs macOS %s or later" % (need[:-2] if need.endswith(".0") else need)
        if spec.get("arch") == "arm64" and platform.machine() != "arm64":
            # Intel Macs can't run Apple silicon-only builds.
            return "Needs a Mac with Apple silicon"
    return None


# ---------------------------------------------------------------------------
# macOS
# ---------------------------------------------------------------------------

def _mac_dirs():
    return ["/Applications", os.path.expanduser("~/Applications")]


def _plist(app_path):
    try:
        with open(os.path.join(app_path, "Contents", "Info.plist"), "rb") as f:
            return plistlib.load(f)
    except Exception:
        return {}


def _mac_find(spec):
    candidates = [os.path.join(d, spec["bundle"]) for d in _mac_dirs()]
    try:
        out = _run(["/usr/bin/mdfind", "kMDItemCFBundleIdentifier == '%s'" % spec["bundle_id"]], timeout=5).stdout
        for line in out.decode("utf-8", "replace").splitlines():
            line = line.strip()
            if line.endswith(".app") and "/Library/Application Support/" not in line and "/.Trash/" not in line \
                    and "/Update/" not in line and line not in candidates:
                candidates.append(line)
    except Exception:
        pass
    for path in candidates:
        if os.path.isdir(path):
            p = _plist(path)
            if p.get("CFBundleIdentifier") == spec["bundle_id"]:
                return {"path": path, "version": p.get("CFBundleShortVersionString") or p.get("CFBundleVersion") or ""}
    return None


def _mac_running(spec):
    try:
        import AppKit

        return len(AppKit.NSRunningApplication.runningApplicationsWithBundleIdentifier_(spec["bundle_id"])) > 0
    except Exception:
        try:
            out = _run(["/usr/bin/osascript", "-e", 'application id "%s" is running' % spec["bundle_id"]], timeout=5).stdout
            return out.strip() == b"true"
        except Exception:
            return False


def _mac_quit(spec):
    _run(["/usr/bin/osascript", "-e", 'tell application id "%s" to quit' % spec["bundle_id"]], timeout=20)
    for _ in range(60):
        if not _mac_running(spec):
            return True
        time.sleep(0.25)
    return False


def _mac_install(spec, zpath, version, existing):
    work = tempfile.mkdtemp(prefix="PXL-")
    try:
        out = os.path.join(work, "x")
        r = _run(["/usr/bin/ditto", "-x", "-k", zpath, out], timeout=600)
        if r.returncode != 0:
            raise InstallError("The download couldn't be unpacked.")
        new = os.path.join(out, spec["bundle"])
        if not os.path.isdir(new):
            found = [n for n in os.listdir(out) if n.endswith(".app")]
            if not found:
                raise InstallError("The download doesn't contain an app.")
            new = os.path.join(out, found[0])
        p = _plist(new)
        if p.get("CFBundleIdentifier") != spec["bundle_id"]:
            raise InstallError("The download isn't the app it claims to be.")
        if version and p.get("CFBundleShortVersionString") != version:
            log("note: %s reports %s, release says %s" % (spec["bundle"], p.get("CFBundleShortVersionString"), version))
        _run(["/usr/bin/xattr", "-dr", "com.apple.quarantine", new], timeout=60)

        if existing:
            target = existing["path"]
        else:
            target = os.path.join("/Applications" if os.access("/Applications", os.W_OK) else os.path.expanduser("~/Applications"),
                                  spec["bundle"])
        os.makedirs(os.path.dirname(target), exist_ok=True)
        if not os.access(os.path.dirname(target), os.W_OK):
            raise InstallError("PXL can't write to %s." % os.path.dirname(target))
        old = target + ".pxl-old"
        shutil.rmtree(old, ignore_errors=True)
        if os.path.exists(target):
            os.rename(target, old)
        try:
            shutil.move(new, target)
        except Exception:
            if os.path.exists(old):
                os.rename(old, target)
            raise
        shutil.rmtree(old, ignore_errors=True)
        # Let Launch Services and Spotlight know about the new copy.
        _run(["/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister",
              "-f", target], timeout=30)
        return target
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _mac_trash(path):
    try:
        import Foundation

        url = Foundation.NSURL.fileURLWithPath_(path)
        ok, _, err = Foundation.NSFileManager.defaultManager().trashItemAtURL_resultingItemURL_error_(url, None, None)
        if ok:
            return
    except Exception:
        pass
    r = _run(["/usr/bin/osascript", "-e", 'tell application "Finder" to delete POSIX file "%s"' % path.replace('"', '\\"')], timeout=30)
    if r.returncode != 0:
        raise InstallError("Couldn't move the app to the Trash.")


# ---------------------------------------------------------------------------
# Windows
# ---------------------------------------------------------------------------

def _programs_dir():
    return os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~\\AppData\\Local"), "Programs")


def _start_menu():
    return os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~\\AppData\\Roaming"),
                        "Microsoft", "Windows", "Start Menu", "Programs")


def _win_uninstall_entries():
    import winreg

    roots = [(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
             (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
             (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall")]
    for hive, path in roots:
        try:
            key = winreg.OpenKey(hive, path)
        except OSError:
            continue
        i = 0
        while True:
            try:
                sub = winreg.EnumKey(key, i)
            except OSError:
                break
            i += 1
            try:
                with winreg.OpenKey(key, sub) as k:
                    vals = {}
                    for name in ("DisplayName", "DisplayVersion", "InstallLocation", "UninstallString",
                                 "QuietUninstallString", "DisplayIcon"):
                        try:
                            vals[name] = winreg.QueryValueEx(k, name)[0]
                        except OSError:
                            pass
                    yield vals
            except OSError:
                continue


def _win_find_nsis(spec):
    want = spec.get("display_name") or ""
    for e in _win_uninstall_entries():
        name = e.get("DisplayName") or ""
        if name == want or name.startswith(want + " "):
            # Not every installer records InstallLocation (electron-builder doesn't), so fall back
            # to the folder of the uninstaller or the icon, and always point at the app's own exe.
            loc = (e.get("InstallLocation") or "").strip('"')
            if not loc:
                for key in ("UninstallString", "DisplayIcon"):
                    v = (e.get(key) or "").strip()
                    v = v[1:].split('"', 1)[0] if v.startswith('"') else v.split(",")[0].split(" /")[0]
                    if v:
                        loc = os.path.dirname(v)
                        break
            return {"path": loc, "exe": os.path.join(loc, spec["exe"]) if loc else "", "version": e.get("DisplayVersion") or "",
                    "uninstall": e.get("QuietUninstallString") or e.get("UninstallString")}
    return None


def _win_setup_uninstaller(spec):
    """The uninstaller registered by the app's setup wizard (its installer/windows.iss), or None."""
    try:
        import winreg

        path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\PXLVZN.%s_is1" % spec["folder"]
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as k:
            return winreg.QueryValueEx(k, "UninstallString")[0] or None
    except Exception:
        return None


def _win_folder_root(spec):
    return os.path.join(_programs_dir(), spec["folder"])


def _win_find_folder(spec):
    root = _win_folder_root(spec)
    exe = os.path.join(root, spec["exe"])
    if not os.path.isfile(exe):
        return None
    version = ""
    for vf in (os.path.join(root, "_internal", "VERSION"), os.path.join(root, "VERSION")):
        try:
            with open(vf) as f:
                version = f.read().strip()
                break
        except OSError:
            pass
    return {"path": root, "exe": exe, "version": version}


def _win_running(spec):
    try:
        out = _run(["tasklist", "/FI", "IMAGENAME eq %s" % spec["exe"], "/NH"], timeout=10).stdout
        return spec["exe"].lower().encode() in out.lower()
    except Exception:
        return False


def _win_quit(spec):
    _run(["taskkill", "/IM", spec["exe"]], timeout=15)
    for _ in range(24):
        if not _win_running(spec):
            return True
        time.sleep(0.25)
    _run(["taskkill", "/F", "/IM", spec["exe"]], timeout=15)
    time.sleep(0.5)
    return not _win_running(spec)


def _win_shortcut(name, exe):
    lnk = os.path.join(_start_menu(), name + ".lnk")
    q = lambda s: "'" + s.replace("'", "''") + "'"
    ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut(%s);$s.TargetPath=%s;"
          "$s.WorkingDirectory=%s;$s.Save()" % (q(lnk), q(exe), q(os.path.dirname(exe))))
    _run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], timeout=30)


def _win_install_folder(app, spec, zpath, existing):
    work = tempfile.mkdtemp(prefix="PXL-")
    try:
        out = os.path.join(work, "x")
        with zipfile.ZipFile(zpath) as z:
            z.extractall(out)
        new = os.path.join(out, spec["folder"])
        if not os.path.isfile(os.path.join(new, spec["exe"])):
            if os.path.isfile(os.path.join(out, spec["exe"])):
                new = out
            else:
                raise InstallError("The download doesn't contain %s." % spec["exe"])
        target = _win_folder_root(spec)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        old = target + ".pxl-old"
        shutil.rmtree(old, ignore_errors=True)
        if os.path.exists(target):
            os.rename(target, old)
        try:
            shutil.move(new, target)
        except Exception:
            if os.path.exists(old):
                os.rename(old, target)
            raise
        shutil.rmtree(old, ignore_errors=True)
        _win_shortcut(app["name"], os.path.join(target, spec["exe"]))
        return target
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _win_install_nsis(spec, exe_path):
    r = _run([exe_path, "/S"], timeout=900)
    if r.returncode != 0:
        raise InstallError("The installer stopped with code %d." % r.returncode)
    for _ in range(40):  # the uninstall entry can land a moment after the installer exits
        if _win_find_nsis(spec):
            return
        time.sleep(0.25)


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

def find(spec):
    """{"path", "version", ...} for an installed app, or None."""
    if not spec:
        return None
    try:
        t = spec.get("type")
        if PLATFORM == "mac" and t == "app-zip":
            return _mac_find(spec)
        if PLATFORM == "windows" and t == "folder-zip":
            return _win_find_folder(spec)
        if PLATFORM == "windows" and t == "nsis":
            return _win_find_nsis(spec)
    except Exception as e:
        log("find failed: %s" % e)
    return None


def is_running(spec):
    if not spec:
        return False
    return _mac_running(spec) if PLATFORM == "mac" else _win_running(spec) if PLATFORM == "windows" else False


def quit_app(spec):
    return _mac_quit(spec) if PLATFORM == "mac" else _win_quit(spec) if PLATFORM == "windows" else True


def install(app, spec, asset_url, checksum_url, version, progress):
    """Download, verify and install. progress(phase, fraction)."""
    existing = find(spec)
    work = tempfile.mkdtemp(prefix="PXL-dl-")
    try:
        name = asset_url.rsplit("/", 1)[-1] or "download"
        path = os.path.join(work, name)
        progress("downloading", 0.0)
        download(asset_url, path, lambda f: progress("downloading", f))
        if checksum_url:
            progress("verifying", 1.0)
            verify_sha256(path, checksum_url)
        progress("installing", 1.0)
        t = spec["type"]
        if PLATFORM == "mac" and t == "app-zip":
            _mac_install(spec, path, version, existing)
        elif PLATFORM == "windows" and t == "folder-zip":
            _win_install_folder(app, spec, path, existing)
        elif PLATFORM == "windows" and t == "nsis":
            _win_install_nsis(spec, path)
        else:
            raise InstallError("PXL doesn't know how to install this type of app.")
        found = find(spec)
        if not found:
            raise InstallError("The app was installed but PXL can't find it.")
        log("installed %s %s at %s" % (app["id"], found.get("version"), found.get("path")))
        return found
    except NetError as e:
        raise InstallError(str(e))
    except InstallError:
        raise
    except PermissionError:
        raise InstallError("PXL doesn't have permission to install there.")
    except Exception as e:
        log("install %s failed: %r" % (app.get("id"), e))
        raise InstallError("Install failed: %s" % e)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def uninstall(app, spec):
    found = find(spec)
    if not found:
        return
    t = spec["type"]
    if PLATFORM == "mac":
        _mac_trash(found["path"])
    elif t == "folder-zip":
        # Installed with the app's own setup wizard: let its uninstaller remove the
        # shortcuts and the Settings > Apps entry too.
        cmd = _win_setup_uninstaller(spec)
        if cmd:
            subprocess.run(cmd + " /VERYSILENT /SUPPRESSMSGBOXES /NORESTART", shell=True, timeout=600,
                           creationflags=NO_WINDOW)
            for _ in range(80):  # it finishes in a copy of itself after this one exits
                if not os.path.exists(found["path"]):
                    break
                time.sleep(0.25)
        if os.path.exists(found["path"]):
            shutil.rmtree(found["path"])
        try:
            os.remove(os.path.join(_start_menu(), app["name"] + ".lnk"))
        except OSError:
            pass
    elif t == "nsis":
        cmd = found.get("uninstall")
        if not cmd:
            raise InstallError("Couldn't find %s's uninstaller." % app["name"])
        if "/S" not in cmd:
            cmd += " /S"
        r = subprocess.run(cmd, shell=True, timeout=600, creationflags=NO_WINDOW)
        if r.returncode != 0:
            raise InstallError("The uninstaller stopped with code %d." % r.returncode)
        for _ in range(40):
            if not _win_find_nsis(spec):
                break
            time.sleep(0.25)


def open_app(spec):
    found = find(spec)
    if not found:
        raise InstallError("The app isn't installed.")
    if PLATFORM == "mac":
        subprocess.Popen(["/usr/bin/open", found["path"]])
    elif PLATFORM == "windows":
        os.startfile(found.get("exe") or found["path"])  # type: ignore[attr-defined]


def reveal(spec):
    found = find(spec)
    if not found:
        return
    if PLATFORM == "mac":
        subprocess.Popen(["/usr/bin/open", "-R", found["path"]])
    elif PLATFORM == "windows":
        subprocess.Popen(["explorer", "/select,", os.path.normpath(found.get("exe") or found["path"])])
