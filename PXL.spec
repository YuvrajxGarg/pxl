# PyInstaller build recipe for macOS (.app) and Windows (folder with .exe).
#   pyinstaller --noconfirm PXL.spec
import os
import sys

root = SPECPATH
version = open(os.path.join(root, "VERSION")).read().strip()

datas = [
    (os.path.join(root, "pxl", "ui"), os.path.join("pxl", "ui")),
    (os.path.join(root, "VERSION"), "."),
    (os.path.join(root, "apps.json"), "."),   # offline fallback for the app list
]

a = Analysis(
    [os.path.join(root, "PXL.py")],
    pathex=[root],
    datas=datas,
    hiddenimports=["certifi"],
    excludes=["tkinter", "_tkinter"],
)
pyz = PYZ(a.pure)
icon = os.path.join(root, "assets", "AppIcon.icns" if sys.platform == "darwin" else "icon.ico")

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="PXL",
    console=False,
    icon=icon,
)
coll = COLLECT(exe, a.binaries, a.datas, name="PXL")

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="PXL.app",
        icon=icon,
        bundle_identifier="com.yuvrajgarg.pxl",
        version=version,
        info_plist={
            "CFBundleShortVersionString": version,
            "CFBundleVersion": version,
            "CFBundleDisplayName": "PXL",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
            "NSRequiresAquaSystemAppearance": False,
            "NSAppleEventsUsageDescription": "PXL asks apps to quit before it updates them.",
        },
    )
