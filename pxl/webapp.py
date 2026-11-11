"""PXL's window: the HTML/CSS interface in pxl/ui inside a native WebKit (macOS) or
Edge WebView2 (Windows) view, via pywebview. Same shell as Tag."""

import json
import os
import queue
import sys
import threading
import time

import webview

from . import __version__
from . import installer
from .catalog import PLATFORM, Catalog, find_asset, platform_spec
from .net import NetError, human_size, is_newer, log
from .settings import Settings
from .updater import Updater

UI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    UI_DIR = os.path.join(sys._MEIPASS, "pxl", "ui")

BG = "#0b0b0c"
REFRESH_EVERY = 3 * 3600
SAFE_URLS = ("https://github.com/", "https://raw.githubusercontent.com/", "https://pxlvzn.in", "https://www.pxlvzn.in",
             "https://dwn.pxlvzn.in", "https://tag.pxlvzn.in")


class Api(object):
    def __init__(self):
        self.window = None
        self.settings = Settings()
        self.catalog = Catalog()
        self.updater = Updater(self.settings, lambda st: self._emit("update", st))
        self.jobs = {}            # app id -> {"phase", "progress", "error", "kind"}
        self.queue = queue.Queue()
        self.errors = {}          # app id -> last release-check error
        self.detected = {}        # app id -> installer.find() result
        self.refreshing = False
        self.notified = set()
        self.lock = threading.Lock()
        threading.Thread(target=self._worker, daemon=True).start()

    # ---- plumbing ----------------------------------------------------------
    def _emit(self, event, payload):
        if self.window:
            try:
                self.window.evaluate_js("window.App && App.on(%s, %s)" % (json.dumps(event), json.dumps(payload)))
            except Exception:
                pass

    def _detect(self, app):
        found = installer.find(platform_spec(app))
        self.detected[app["id"]] = found
        return found

    def _public(self, app, detect=False):
        spec = platform_spec(app)
        found = self._detect(app) if detect or app["id"] not in self.detected else self.detected.get(app["id"])
        rel = self.catalog.release(app)
        latest = rel.get("version") if rel else None
        asset_name, asset = find_asset(rel, spec.get("asset") if spec else None)
        reason = installer.compatible(spec)
        installed = bool(found)
        cur = (found or {}).get("version") or ""
        has_update = bool(installed and latest and asset and is_newer(latest, cur))
        seen = self.settings.get("seen_apps")
        status = "unavailable" if reason and not installed else "update" if has_update else "installed" if installed else "get"
        if status == "get" and not asset:
            status = "soon" if not rel else "unavailable"
            if rel and not reason:
                reason = "No %s download in the latest release" % ("Mac" if PLATFORM == "mac" else "Windows")
        return {
            "id": app["id"], "name": app["name"], "mark": app.get("mark") or {"text": app["name"].lower()},
            "icon": app.get("icon"), "tagline": app.get("tagline", ""), "description": app.get("description", ""),
            "category": app.get("category", ""), "repo": app["repo"], "site": app.get("site"),
            "added": app.get("added"), "highlights": app.get("highlights") or [], "screenshots": app.get("screenshots") or [],
            "platforms": sorted((app.get("platforms") or {}).keys()),
            "installed": installed, "installed_version": cur, "path": (found or {}).get("path"),
            "latest": latest, "notes": (rel or {}).get("notes", ""), "page": (rel or {}).get("page") or "https://github.com/%s/releases" % app["repo"],
            "published": (rel or {}).get("published"), "size": human_size(asset["size"]) if asset else "",
            "status": status, "reason": reason, "job": self.jobs.get(app["id"]), "error": self.errors.get(app["id"]),
            "new": seen is not None and app["id"] not in seen,
        }

    def _emit_app(self, app_id, detect=False):
        app = self.catalog.app(app_id)
        if app:
            self._emit("app", self._public(app, detect=detect))

    # ---- called from JS ----------------------------------------------------
    def info(self):
        return {"version": __version__, "platform": sys.platform, "os": PLATFORM,
                "settings": self.settings.public(), "update": self.updater.state(), "home": os.path.expanduser("~")}

    def apps(self):
        return [self._public(a, detect=True) for a in self.catalog.apps()]

    def set_setting(self, key, value):
        if key in ("auto_check", "auto_update_apps", "auto_install", "notify_new", "welcomed", "toured"):
            self.settings.set(key, value)
            if key == "auto_install" and value and self.updater.phase == "available":
                threading.Thread(target=self.updater.stage_newest, daemon=True).start()
            if key == "auto_update_apps" and value:
                threading.Thread(target=self._auto_update, daemon=True).start()
        return self.settings.public()

    def mark_seen(self, app_id=None):
        seen = set(self.settings.get("seen_apps") or [])
        if app_id:
            seen.add(app_id)
        else:
            seen.update(a["id"] for a in self.catalog.apps())
        self.settings.set("seen_apps", sorted(seen))
        return True

    def refresh(self, manual=False):
        threading.Thread(target=self._refresh, args=(bool(manual),), daemon=True).start()

    def install(self, app_id, quit_first=False):
        """Install or update an app. Returns {"needs_quit": True} when it's open and must close first."""
        app = self.catalog.app(app_id)
        if not app:
            return {"ok": False}
        spec = platform_spec(app)
        if self.detected.get(app_id) and installer.is_running(spec) and not quit_first:
            return {"needs_quit": True, "name": app["name"]}
        self._enqueue(app_id, quit_first=quit_first)
        return {"ok": True}

    def update_all(self):
        n = 0
        for a in self.catalog.apps():
            pub = self._public(a)
            if pub["status"] == "update" and not pub["job"]:
                self._enqueue(a["id"], quit_first=True)
                n += 1
        return n

    def cancel(self, app_id):
        with self.lock:
            j = self.jobs.get(app_id)
            if j and j["phase"] == "queued":
                self.jobs.pop(app_id, None)
        self._emit_app(app_id)

    def uninstall(self, app_id):
        app = self.catalog.app(app_id)
        if not app or self.jobs.get(app_id):
            return
        def go():
            spec = platform_spec(app)
            self.jobs[app_id] = {"phase": "removing", "progress": 0, "kind": "remove"}
            self._emit_app(app_id)
            try:
                if installer.is_running(spec):
                    installer.quit_app(spec)
                installer.uninstall(app, spec)
                self._emit("toast", {"text": "%s was removed" % app["name"] + (" (moved to the Trash)" if PLATFORM == "mac" else "")})
            except Exception as e:
                self._emit("toast", {"text": str(e), "err": True})
            finally:
                self.jobs.pop(app_id, None)
                self._emit_app(app_id, detect=True)
        threading.Thread(target=go, daemon=True).start()

    def open_app(self, app_id):
        app = self.catalog.app(app_id)
        if app:
            try:
                installer.open_app(platform_spec(app))
            except Exception as e:
                self._emit("toast", {"text": str(e), "err": True})

    def reveal(self, app_id):
        app = self.catalog.app(app_id)
        if app:
            installer.reveal(platform_spec(app))

    def open_url(self, url):
        if not url or not str(url).startswith(SAFE_URLS):
            return
        import webbrowser
        webbrowser.open(url)

    # PXL's own updates
    def check_updates(self):
        return self.updater.check(manual=True)

    def download_update(self):
        threading.Thread(target=self.updater.stage_newest, daemon=True).start()

    def install_update(self):
        def go():
            if self.updater.install() == "open_page":
                self.open_url(self.updater.state()["page"])
        threading.Thread(target=go, daemon=True).start()

    # ---- background work ---------------------------------------------------
    def start(self):
        if getattr(self, "_started", False):
            return
        self._started = True
        self.updater.start()

        def loop():
            time.sleep(0.8)
            self._refresh(manual=False, first=True)
            while True:
                time.sleep(REFRESH_EVERY)
                if self.settings.get("auto_check"):
                    self._refresh(manual=False)

        threading.Thread(target=loop, daemon=True).start()

    def _refresh(self, manual=False, first=False):
        if self.refreshing:
            return
        self.refreshing = True
        self._emit("refreshing", {"on": True})
        try:
            before = {a["id"] for a in self.catalog.apps()}
            self.catalog.refresh_registry()
            apps = self.catalog.apps()
            for a in apps:
                try:
                    self.catalog.refresh_release(a)
                    self.errors.pop(a["id"], None)
                except NetError as e:
                    self.errors[a["id"]] = str(e)
                    log("release check %s: %s" % (a["id"], e))
            pubs = [self._public(a, detect=True) for a in apps]
            self._emit("apps", pubs)
            self.settings.set("last_checked", time.strftime("%Y-%m-%dT%H:%M:%S"))
            if self.settings.get("seen_apps") is not None and self.settings.get("notify_new"):
                for p in pubs:
                    if p["new"] and p["id"] not in self.notified and (p["id"] not in before or first):
                        self.notified.add(p["id"])
                        self._emit("new_app", p)
            if manual:
                n = sum(1 for p in pubs if p["status"] == "update")
                self._emit("toast", {"text": "%d update%s available" % (n, "" if n == 1 else "s") if n else "Everything is up to date"})
        finally:
            self.refreshing = False
            self._emit("refreshing", {"on": False})
        if self.settings.get("auto_update_apps"):
            self._auto_update()

    def _auto_update(self):
        """Quietly update installed apps that aren't open right now."""
        for a in self.catalog.apps():
            pub = self._public(a)
            if pub["status"] == "update" and not pub["job"] and not installer.is_running(platform_spec(a)):
                self._enqueue(a["id"], quit_first=False, auto=True)

    def _enqueue(self, app_id, quit_first=False, auto=False):
        with self.lock:
            if self.jobs.get(app_id):
                return
            self.jobs[app_id] = {"phase": "queued", "progress": 0, "kind": "install", "auto": auto}
        self._emit_app(app_id)
        self.queue.put((app_id, quit_first, auto))

    def _worker(self):
        while True:
            app_id, quit_first, auto = self.queue.get()
            if app_id not in self.jobs:
                continue  # cancelled while queued
            app = self.catalog.app(app_id)
            try:
                if app:
                    self._run_install(app, quit_first, auto)
            except Exception as e:
                log("worker: %r" % e)
            finally:
                self.jobs.pop(app_id, None)
                if app:
                    self._emit_app(app_id, detect=True)

    def _run_install(self, app, quit_first, auto):
        app_id = app["id"]
        spec = platform_spec(app)
        was = self.detected.get(app_id)

        def progress(phase, frac):
            j = self.jobs.get(app_id)
            if j is not None:
                j.update(phase=phase, progress=frac)
                self._emit("job", {"id": app_id, "job": dict(j)})

        try:
            if was and installer.is_running(spec):
                if auto and not quit_first:
                    return  # opened since it was queued; try again next time
                progress("closing", 0)
                if not installer.quit_app(spec):
                    raise installer.InstallError("%s didn't close. Quit it and try again." % app["name"])
            rel = self.catalog.release(app)
            if not rel:
                rel = self.catalog.refresh_release(app)
            asset_name, asset = find_asset(rel, spec.get("asset"))
            if not asset:
                raise installer.InstallError("There's no download for this computer in %s %s." % (app["name"], rel.get("version")))
            ck_name, ck = find_asset(rel, spec.get("checksum")) if spec.get("checksum") else (None, None)
            found = installer.install(app, spec, asset["url"], ck["url"] if ck else None, rel.get("version"), progress)
            self.detected[app_id] = found
            verb = "Updated" if was else "Installed"
            self._emit("installed", {"id": app_id, "name": app["name"], "version": found.get("version"), "verb": verb, "auto": auto})
        except (installer.InstallError, NetError) as e:
            self._emit("toast", {"text": "%s: %s" % (app["name"], e), "err": True})


# ---- native window chrome -------------------------------------------------

def _style_mac(window):
    """Dark, transparent title bar with content running underneath (like Dwn and Tag)."""
    try:
        import AppKit
        from PyObjCTools import AppHelper

        def apply():
            w = window.native
            w.setStyleMask_(w.styleMask() | AppKit.NSWindowStyleMaskFullSizeContentView)
            w.setTitlebarAppearsTransparent_(True)
            w.setTitleVisibility_(AppKit.NSWindowTitleHidden)
            w.setAppearance_(AppKit.NSAppearance.appearanceNamed_(AppKit.NSAppearanceNameDarkAqua))
            w.setBackgroundColor_(AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(0.043, 0.043, 0.047, 1.0))
            w.setMovableByWindowBackground_(False)
            try:
                w.contentView().superview().subviews().lastObject().setBackgroundColor_(AppKit.NSColor.clearColor())
            except Exception:
                pass
            if hasattr(w, "setToolbarStyle_"):
                w.setToolbarStyle_(AppKit.NSWindowToolbarStyleUnifiedCompact)

        AppHelper.callAfter(apply)
    except Exception:
        pass


def _style_windows(window):
    """Dark title bar on Windows 10/11; caption colour matches the app on Windows 11."""
    try:
        import ctypes

        hwnd = window.native.Handle.ToInt32()
        dwm = ctypes.windll.dwmapi
        on = ctypes.c_int(1)
        for attr in (20, 19):
            if dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(on), 4) == 0:
                break
        caption = ctypes.c_int(0x000C0B0B)
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption), 4)
    except Exception:
        pass


def main():
    api = Api()
    webview.settings["DRAG_REGION_DIRECT_TARGET_ONLY"] = True
    window = webview.create_window(
        "PXL", url=os.path.join(UI_DIR, "index.html"), js_api=api,
        width=1180, height=760, min_size=(920, 600), background_color=BG, easy_drag=False,
    )
    api.window = window

    def quit_for_install():
        try:
            window.destroy()
        finally:
            threading.Timer(3.0, lambda: os._exit(0)).start()

    api.updater.on_quit_for_install = quit_for_install
    window.events.closing += lambda: api.updater.install_on_quit()
    window.events.loaded += lambda: api.start()

    if sys.platform == "darwin":
        window.events.before_show += lambda: _style_mac(window)
    elif os.name == "nt":
        window.events.shown += lambda: _style_windows(window)
    webview.start(debug=bool(os.environ.get("PXL_DEBUG")))


if __name__ == "__main__":
    main()
