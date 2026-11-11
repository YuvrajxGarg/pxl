"""HTTP, version and file helpers shared by the catalog, installer and self-updater."""

import datetime
import hashlib
import os
import ssl
import time
import urllib.error
import urllib.request

from . import __version__
from .settings import app_data_dir

GITHUB_API = os.environ.get("PXL_GITHUB_API", "https://api.github.com")


class NetError(Exception):
    pass


def log(msg):
    """Append a line to pxl.log in the app data folder (for diagnosing problems)."""
    try:
        path = os.path.join(app_data_dir(), "pxl.log")
        if os.path.exists(path) and os.path.getsize(path) > 512 * 1024:
            os.replace(path, path + ".1")
        with open(path, "a", encoding="utf-8") as f:
            f.write("%s  %s  %s\n" % (datetime.datetime.now().isoformat(timespec="seconds"), __version__, msg))
    except Exception:
        pass


def is_newer(a, b):
    """True when version string a is newer than b ("1.10.0" > "1.9.2")."""
    def parts(v):
        out, cur = [], ""
        for ch in str(v or ""):
            if ch.isdigit():
                cur += ch
            elif cur:
                out.append(int(cur))
                cur = ""
        if cur:
            out.append(int(cur))
        return out

    pa, pb = parts(a), parts(b)
    for i in range(max(len(pa), len(pb))):
        x = pa[i] if i < len(pa) else 0
        y = pb[i] if i < len(pb) else 0
        if x != y:
            return x > y
    return False


def ssl_ctx():
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def request(url, accept="application/vnd.github+json", headers=None, timeout=30):
    h = {"Accept": accept, "User-Agent": "PXL/" + __version__, "Cache-Control": "no-cache"}
    h.update(headers or {})
    return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout, context=ssl_ctx())


def download(url, dest, progress=None):
    """Stream url to dest, calling progress(fraction) at most ~5 times a second."""
    try:
        with request(url, accept="application/octet-stream", timeout=60) as r, open(dest, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            done, last = 0, 0.0
            while True:
                chunk = r.read(1 << 18)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if progress and total and time.time() - last > 0.2:
                    last = time.time()
                    progress(min(0.99, done / float(total)))
    except urllib.error.HTTPError as e:
        raise NetError("The download failed (HTTP %d)." % e.code)
    except NetError:
        raise
    except Exception:
        raise NetError("The download stopped. Check your connection and try again.")
    if total and done != total:
        raise NetError("The download stopped. Check your connection and try again.")


def verify_sha256(path, checksum_url):
    """Compare the file's SHA-256 with the first word of the .sha256 file at checksum_url."""
    try:
        with request(checksum_url, accept="application/octet-stream") as r:
            expected = r.read().decode("utf-8", "replace").split()[0].lower()
    except Exception:
        raise NetError("Couldn't get the checksum to verify the download.")
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    if h.hexdigest() != expected:
        raise NetError("The download didn't arrive intact. Try again.")


def human_size(n):
    if not n:
        return ""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return ("%d %s" % (n, unit)) if unit == "B" else ("%.1f %s" % (n, unit))
        n /= 1024.0
