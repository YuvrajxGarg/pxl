"""Validates apps.json and checks each app's latest GitHub release.

    python tools/check_apps.py            # check everything
    python tools/check_apps.py --offline  # only the file itself

Exits non-zero if anything is wrong, so CI blocks a broken app list.
"""

import fnmatch
import json
import os
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
TYPES = {"mac": {"app-zip"}, "windows": {"folder-zip", "nsis"}}
REQUIRED = {
    "app-zip": ["asset", "bundle", "bundle_id"],
    "folder-zip": ["asset", "folder", "exe"],
    "nsis": ["asset", "display_name", "exe"],
}


def problems(reg):
    out = []
    if not isinstance(reg.get("apps"), list) or not reg["apps"]:
        return ["apps.json needs a non-empty \"apps\" list"]
    seen = set()
    for i, a in enumerate(reg["apps"]):
        where = a.get("id") or "app #%d" % (i + 1)
        for k in ("id", "name", "tagline", "description", "repo", "platforms"):
            if not a.get(k):
                out.append("%s: missing %r" % (where, k))
        if a.get("id") in seen:
            out.append("%s: duplicate id" % where)
        seen.add(a.get("id"))
        if a.get("id") and not re.fullmatch(r"[a-z0-9]{3}", a["id"]):
            out.append("%s: ids are three lowercase letters or digits" % where)
        if a.get("repo") and not re.fullmatch(r"[\w.-]+/[\w.-]+", a["repo"]):
            out.append("%s: repo should look like owner/name" % where)
        glyph = (a.get("mark") or {}).get("glyph")
        if glyph not in (None, "", "arrow", "strike", "pixel", "wipe", "tracks", "go", "sync"):
            out.append("%s: mark.glyph must be arrow, strike, pixel, wipe, tracks, go, sync or empty" % where)
        for plat, spec in (a.get("platforms") or {}).items():
            if plat not in TYPES:
                out.append("%s: unknown platform %r (use mac or windows)" % (where, plat))
                continue
            t = spec.get("type")
            if t not in TYPES[plat]:
                out.append("%s/%s: type must be one of %s" % (where, plat, ", ".join(sorted(TYPES[plat]))))
                continue
            for k in REQUIRED[t]:
                if not spec.get(k):
                    out.append("%s/%s: missing %r" % (where, plat, k))
    return out


def release_problems(reg):
    out = []
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    for a in reg["apps"]:
        req = urllib.request.Request("https://api.github.com/repos/%s/releases/latest" % a["repo"],
                                     headers={"Accept": "application/vnd.github+json", "User-Agent": "pxl-check",
                                              **({"Authorization": "Bearer " + token} if token else {})})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                rel = json.load(r)
        except Exception as e:
            out.append("%s: no latest release in %s (%s)" % (a["id"], a["repo"], e))
            continue
        names = [x["name"] for x in rel.get("assets", [])]
        for plat, spec in a["platforms"].items():
            for key in ("asset", "checksum"):
                pat = spec.get(key)
                if pat and not any(fnmatch.fnmatch(n, pat) for n in names):
                    out.append("%s/%s: %s %r isn't in release %s" % (a["id"], plat, key, pat, rel.get("tag_name")))
        print("  %-4s %-10s %s" % (a["id"], rel.get("tag_name"), ", ".join(names)))
    return out


def main():
    reg = json.loads((ROOT / "apps.json").read_text(encoding="utf-8"))
    errs = problems(reg)
    if not errs and "--offline" not in sys.argv:
        errs += release_problems(reg)
    for e in errs:
        print("x " + e)
    if errs:
        sys.exit(1)
    print("apps.json looks good (%d apps)" % len(reg["apps"]))


if __name__ == "__main__":
    main()
