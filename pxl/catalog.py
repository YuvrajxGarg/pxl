"""The app list (apps.json) and each app's newest GitHub release.

- apps.json comes from the PXL repository's main branch, so a push adds an app to
  every copy of PXL. The last good copy is cached, and a copy bundled with the app
  is the fallback for a first launch offline.
- Each app's newest release comes from the GitHub API (conditional requests with
  ETags, so refreshes are cheap and don't use up the rate limit). When the API is
  unavailable, the /releases/latest redirect still gives the version.
"""

import copy
import re
import fnmatch
import json
import os
import sys
import threading
import urllib.error

from . import REGISTRY_URL
from .net import GITHUB_API, NetError, log, request
from .settings import app_data_dir

PLATFORM = "mac" if sys.platform == "darwin" else "windows" if os.name == "nt" else "other"


def _bundled_path():
    for base in (getattr(sys, "_MEIPASS", None), os.path.dirname(os.path.dirname(os.path.abspath(__file__)))):
        if base and os.path.isfile(os.path.join(base, "apps.json")):
            return os.path.join(base, "apps.json")
    return None


def _valid(reg):
    return isinstance(reg, dict) and isinstance(reg.get("apps"), list) and all(
        isinstance(a, dict) and a.get("id") and a.get("name") and a.get("repo") for a in reg["apps"])


class Catalog(object):
    def __init__(self):
        self.lock = threading.Lock()
        self.cache_path = os.path.join(app_data_dir(), "catalog-cache.json")
        self.cache = {"registry": None, "releases": {}}
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                self.cache.update(json.load(f))
        except (OSError, ValueError):
            pass
        self.registry = self.cache.get("registry") if _valid(self.cache.get("registry")) else self._bundled()
        self.registry_source = "cache" if self.cache.get("registry") else "bundled"

    # ---- persistence -------------------------------------------------------
    def _save(self):
        tmp = self.cache_path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.cache, f)
            os.replace(tmp, self.cache_path)
        except OSError:
            pass

    def _bundled(self):
        p = _bundled_path()
        if p:
            try:
                with open(p, "r", encoding="utf-8") as f:
                    reg = json.load(f)
                if _valid(reg):
                    return reg
            except (OSError, ValueError):
                pass
        return {"schema": 1, "apps": []}

    # ---- registry ----------------------------------------------------------
    def apps(self):
        with self.lock:
            return copy.deepcopy(self.registry.get("apps", []))

    def app(self, app_id):
        for a in self.apps():
            if a["id"] == app_id:
                return a
        return None

    def refresh_registry(self):
        """Fetch apps.json. Returns True when it changed. Local file wins with PXL_REGISTRY=/path."""
        try:
            if os.path.isfile(REGISTRY_URL):
                with open(REGISTRY_URL, "r", encoding="utf-8") as f:
                    reg = json.load(f)
            else:
                with request(REGISTRY_URL, accept="application/json") as r:
                    reg = json.loads(r.read().decode("utf-8"))
        except Exception as e:
            log("registry fetch failed: %s" % e)
            return False
        if not _valid(reg):
            log("registry is malformed, keeping the last good copy")
            return False
        with self.lock:
            changed = reg != self.registry
            self.registry = reg
            self.registry_source = "live"
            self.cache["registry"] = reg
            self._save()
        return changed

    # ---- releases ----------------------------------------------------------
    def release(self, app):
        """The cached newest release for an app, or None."""
        return self.cache.get("releases", {}).get(app["id"], {}).get("data")

    def refresh_release(self, app):
        """Fetch the newest release of app's repository. Returns the release dict or raises NetError."""
        repo = app["repo"]
        entry = self.cache.setdefault("releases", {}).get(app["id"]) or {}
        headers = {"If-None-Match": entry["etag"]} if entry.get("etag") and entry.get("repo") == repo else {}
        try:
            with request("%s/repos/%s/releases/latest" % (GITHUB_API, repo), headers=headers) as r:
                obj = json.loads(r.read().decode("utf-8"))
                etag = r.headers.get("ETag")
        except urllib.error.HTTPError as e:
            if e.code == 304 and entry.get("data"):
                return entry["data"]
            if e.code == 404:
                raise NetError("%s hasn't published a release yet." % app["name"])
            if e.code in (403, 429):
                data = self._release_from_redirect(app)
                if data:
                    return data
                raise NetError("GitHub is rate-limiting update checks. Try again in a little while.")
            raise NetError("Couldn't reach GitHub (HTTP %d)." % e.code)
        except Exception:
            if entry.get("data"):
                return entry["data"]
            raise NetError("Couldn't reach GitHub. Check your connection.")
        tag = obj.get("tag_name") or ""
        old = entry.get("data") or {}
        if old.get("version") == tag.lstrip("vV") and old.get("notes") and entry.get("repo") == repo:
            notes = old["notes"]  # already filled in for this version
        else:
            notes = release_notes(repo, tag, obj.get("body") or "")
        data = {
            "version": tag.lstrip("vV"),
            "notes": notes,
            "page": obj.get("html_url") or "https://github.com/%s/releases" % repo,
            "published": obj.get("published_at"),
            "assets": {a.get("name"): {"url": a.get("browser_download_url"), "size": a.get("size") or 0}
                       for a in obj.get("assets", []) if a.get("name")},
        }
        with self.lock:
            self.cache["releases"][app["id"]] = {"repo": repo, "etag": etag, "data": data}
            self._save()
        return data

    def _release_from_redirect(self, app):
        """Without the API: github.com/<repo>/releases/latest redirects to /releases/tag/<tag>."""
        repo = app["repo"]
        try:
            with request("https://github.com/%s/releases/latest" % repo, accept="text/html") as r:
                final = r.geturl()
        except Exception:
            return None
        if "/releases/tag/" not in final:
            return None
        version = final.rsplit("/", 1)[-1].lstrip("vV")
        base = "https://github.com/%s/releases/latest/download/" % repo
        assets = {}
        for spec in (app.get("platforms") or {}).values():
            for key in ("asset", "checksum"):
                name = (spec.get(key) or "").replace("*", version)
                if name:
                    assets[name] = {"url": base + name, "size": 0}
        old = self.cache.get("releases", {}).get(app["id"], {}).get("data") or {}
        data = {"version": version, "notes": old.get("notes", "") if old.get("version") == version else "",
                "page": final, "published": old.get("published"), "assets": assets}
        with self.lock:
            self.cache["releases"][app["id"]] = {"repo": repo, "etag": None, "data": data}
            self._save()
        return data


_SKIP_SUBJECT = re.compile(r"^(website|site|docs?|readme)\b", re.I)
_TRAILER = re.compile(r"^(co-authored-by|signed-off-by|reviewed-by):", re.I)


def notes_are_empty(body):
    """True when a release body is only GitHub's generated boilerplate (a changelog link)."""
    for line in (body or "").splitlines():
        s = line.strip().strip("*#- ").strip()
        if not s or s.lower().startswith(("full changelog", "what's changed", "new contributors")):
            continue
        return False
    return True


def _clean_message(msg):
    lines = [l.rstrip() for l in (msg or "").strip().splitlines() if not _TRAILER.match(l.strip())]
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def release_notes(repo, tag, body):
    """The release body, or, when it's only a changelog link, the commit messages since the
    previous release (the way Dwn and Tag are released: detailed commits, generated notes)."""
    if not notes_are_empty(body):
        return body
    try:
        m = re.search(r"/compare/([^\s)]+?)\.\.\.([^\s)]+)", body or "")
        if m:
            with request("%s/repos/%s/compare/%s...%s" % (GITHUB_API, repo, m.group(1), m.group(2))) as r:
                commits = [c.get("commit", {}).get("message", "") for c in json.loads(r.read().decode("utf-8")).get("commits", [])]
            commits.reverse()  # newest first
        else:
            with request("%s/repos/%s/commits/%s" % (GITHUB_API, repo, tag)) as r:
                commits = [json.loads(r.read().decode("utf-8")).get("commit", {}).get("message", "")]
    except Exception as e:
        log("notes for %s %s: %s" % (repo, tag, e))
        return body
    parts = [_clean_message(c) for c in commits if c and not _SKIP_SUBJECT.match(c.strip())]
    parts = [p for p in parts if p][:8]
    return "\n\n".join(parts) if parts else body


def platform_spec(app):
    return (app.get("platforms") or {}).get(PLATFORM)


def find_asset(release, pattern):
    """The release asset matching a name or glob ("Dwn-Setup-*.exe"), skipping .blockmap/.sha256 files."""
    if not release or not pattern:
        return None, None
    assets = release.get("assets") or {}
    if pattern in assets:
        return pattern, assets[pattern]
    for name in sorted(assets):
        if fnmatch.fnmatch(name, pattern) and not name.endswith((".blockmap", ".sha256", ".yml")):
            return name, assets[name]
    return None, None
