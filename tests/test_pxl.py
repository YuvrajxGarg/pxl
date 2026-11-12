import json
import os
import pathlib
import plistlib
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

# Keep settings and caches out of the real app data folder.
_tmp = tempfile.mkdtemp()
os.environ["HOME"] = _tmp
os.environ["APPDATA"] = _tmp
os.environ["PXL_REGISTRY"] = str(ROOT / "apps.json")

from pxl import catalog, installer  # noqa: E402
from pxl.net import is_newer  # noqa: E402
import check_apps  # noqa: E402


class Versions(unittest.TestCase):
    def test_is_newer(self):
        self.assertTrue(is_newer("1.10.0", "1.9.9"))
        self.assertTrue(is_newer("v2", "1.99"))
        self.assertTrue(is_newer("1.0.1", "1.0"))
        self.assertFalse(is_newer("1.0.0", "1.0"))
        self.assertFalse(is_newer("", "1.0"))


class Registry(unittest.TestCase):
    def test_apps_json_is_valid(self):
        reg = json.loads((ROOT / "apps.json").read_text(encoding="utf-8"))
        self.assertEqual(check_apps.problems(reg), [])

    def test_checker_catches_mistakes(self):
        bad = {"apps": [{"id": "toolong", "name": "X", "tagline": "t", "description": "d", "repo": "a/b",
                         "platforms": {"mac": {"type": "nsis"}}}]}
        errs = check_apps.problems(bad)
        self.assertTrue(any("three" in e for e in errs))
        self.assertTrue(any("type must be" in e for e in errs))

    def test_catalog_loads_local_registry(self):
        c = catalog.Catalog()
        c.refresh_registry()
        ids = [a["id"] for a in c.apps()]
        self.assertIn("dwn", ids)
        self.assertIn("tag", ids)
        self.assertEqual(c.registry_source, "live")


class Assets(unittest.TestCase):
    rel = {"assets": {"Dwn-Setup-1.1.0.exe": {"url": "u1", "size": 1}, "Dwn-Setup-1.1.0.exe.blockmap": {"url": "u2", "size": 1},
                      "Dwn-mac.zip": {"url": "u3", "size": 1}}}

    def test_glob_skips_blockmap(self):
        self.assertEqual(catalog.find_asset(self.rel, "Dwn-Setup-*.exe")[0], "Dwn-Setup-1.1.0.exe")

    def test_exact(self):
        self.assertEqual(catalog.find_asset(self.rel, "Dwn-mac.zip")[1]["url"], "u3")

    def test_missing(self):
        self.assertEqual(catalog.find_asset(self.rel, "Nope.zip"), (None, None))


@unittest.skipUnless(sys.platform == "darwin", "macOS install path")
class MacInstall(unittest.TestCase):
    def _fake_app_zip(self, work, version, bundle_id="com.example.zzz"):
        app = os.path.join(work, "src", "Zzz.app", "Contents")
        os.makedirs(os.path.join(app, "MacOS"))
        with open(os.path.join(app, "Info.plist"), "wb") as f:
            plistlib.dump({"CFBundleIdentifier": bundle_id, "CFBundleShortVersionString": version}, f)
        z = os.path.join(work, "Zzz-%s.zip" % version)
        subprocess.run(["/usr/bin/ditto", "-c", "-k", "--keepParent", os.path.join(work, "src", "Zzz.app"), z], check=True)
        return z

    def test_install_and_update_in_place(self):
        work = tempfile.mkdtemp()
        spec = {"type": "app-zip", "bundle": "Zzz.app", "bundle_id": "com.example.zzz"}
        target = os.path.join(work, "Apps", "Zzz.app")
        os.makedirs(os.path.dirname(target))
        z1 = self._fake_app_zip(os.path.join(work, "a"), "1.0.0")
        # First install goes where an existing copy lives; pretend one is there.
        installer._mac_install(spec, z1, "1.0.0", {"path": target})
        self.assertEqual(installer._plist(target)["CFBundleShortVersionString"], "1.0.0")
        z2 = self._fake_app_zip(os.path.join(work, "b"), "1.1.0")
        installer._mac_install(spec, z2, "1.1.0", {"path": target})
        self.assertEqual(installer._plist(target)["CFBundleShortVersionString"], "1.1.0")
        self.assertFalse(os.path.exists(target + ".pxl-old"))

    def test_rejects_wrong_bundle(self):
        work = tempfile.mkdtemp()
        z = self._fake_app_zip(work, "1.0.0", bundle_id="com.evil.app")
        spec = {"type": "app-zip", "bundle": "Zzz.app", "bundle_id": "com.example.zzz"}
        with self.assertRaises(installer.InstallError):
            installer._mac_install(spec, z, "1.0.0", {"path": os.path.join(work, "Zzz.app")})


class FolderZip(unittest.TestCase):
    def test_folder_zip_layout(self):
        # The Windows folder-zip installer expects <folder>/<exe> inside the zip, like Tag-windows.zip.
        work = tempfile.mkdtemp()
        z = os.path.join(work, "Tag-windows.zip")
        with zipfile.ZipFile(z, "w") as f:
            f.writestr("Tag/Tag.exe", b"MZ")
            f.writestr("Tag/_internal/VERSION", "1.0.0")
        with zipfile.ZipFile(z) as f:
            self.assertIn("Tag/Tag.exe", f.namelist())


if __name__ == "__main__":
    unittest.main()



class JsApiTest(unittest.TestCase):
    def test_exposes_only_methods(self):
        """pywebview walks every public attribute of the js_api object. A public attribute holding the
        window sent it into the WinForms form's endless .NET object graph on Windows, freezing PXL on its splash."""
        import inspect
        import types

        try:
            import webview  # noqa: F401
        except Exception:
            sys.modules["webview"] = types.SimpleNamespace(settings={})
        from pxl.webapp import Api

        api = Api()
        public = {n: getattr(api, n) for n in dir(api) if not n.startswith("_")}
        self.assertTrue(public)
        self.assertEqual([n for n, v in public.items() if not inspect.ismethod(v)], [])
