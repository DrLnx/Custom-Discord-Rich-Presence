# PyInstaller build: one self-contained executable, no Python required.
#
# Textual loads its own .tcss files at runtime and drpc loads app.tcss the
# same way, so both have to be collected as data rather than left to the
# import hook to find.

from PyInstaller.utils.hooks import collect_all, collect_data_files

datas = collect_data_files("drpc", includes=["**/*.tcss"])
binaries = []
hiddenimports = []

for package in ("textual", "rich", "pypresence", "platformdirs"):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

a = Analysis(
    ["packaging/entry.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "test", "unittest", "pydoc_data"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="drpc",
    console=True,
    strip=False,
    upx=False,
    onefile=True,
    disable_windowed_traceback=False,
)
