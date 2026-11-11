import os
import sys


def _read_version():
    here = os.path.dirname(os.path.abspath(__file__))
    for base in (getattr(sys, "_MEIPASS", None), os.path.dirname(here)):
        if base:
            try:
                with open(os.path.join(base, "VERSION")) as f:
                    return f.read().strip()
            except OSError:
                pass
    return "0.0.0"


__version__ = _read_version()

# GitHub repository PXL updates itself from, and whose apps.json lists every app.
UPDATE_REPO = os.environ.get("PXL_REPO", "YuvrajxGarg/pxl")

# The live app list. Pushing a change to apps.json on main shows up in every copy
# of PXL on its next refresh, without a new PXL release.
REGISTRY_URL = os.environ.get(
    "PXL_REGISTRY", "https://raw.githubusercontent.com/%s/main/apps.json" % UPDATE_REPO)
