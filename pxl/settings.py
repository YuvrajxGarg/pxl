"""Small JSON settings store in the per-user app data folder."""

import json
import os
import sys
import threading

APP_NAME = "PXL"

DEFAULTS = {
    "auto_check": True,          # refresh the app list and look for updates in the background
    "auto_update_apps": True,    # install app updates in the background (only while that app is closed)
    "auto_install": True,        # PXL itself: download in the background, install on quit
    "notify_new": True,          # toast when a new app joins PXL
    "welcomed": False,
    "toured": False,
    "seen_apps": None,           # app ids already shown once; anything else gets a "New" badge
    "staged_version": None,
    "last_checked": None,
}

PUBLIC = ("auto_check", "auto_update_apps", "auto_install", "notify_new", "welcomed", "toured")


def app_data_dir():
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    elif os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~\\AppData\\Roaming")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    d = os.path.join(base, APP_NAME)
    os.makedirs(d, exist_ok=True)
    return d


class Settings(object):
    def __init__(self, path=None):
        self.path = path or os.path.join(app_data_dir(), "settings.json")
        self.lock = threading.Lock()
        self.data = dict(DEFAULTS)
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.data.update(json.load(f))
        except (OSError, ValueError):
            pass

    def get(self, key):
        return self.data.get(key, DEFAULTS.get(key))

    def set(self, key, value):
        with self.lock:
            self.data[key] = value
            tmp = self.path + ".tmp"
            try:
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, indent=2)
                os.replace(tmp, self.path)
            except OSError:
                pass

    def public(self):
        return {k: self.data.get(k, DEFAULTS.get(k)) for k in PUBLIC}
