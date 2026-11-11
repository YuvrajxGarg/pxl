@echo off
rem Builds dist\PXL\PXL.exe on Windows. Needs Python 3.9+.
python -m venv .venv-build
call .venv-build\Scripts\activate.bat
pip install --quiet pyinstaller -r requirements.txt
pyinstaller --noconfirm --log-level WARN PXL.spec
echo Done: dist\PXL\PXL.exe
