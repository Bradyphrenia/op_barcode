# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['barcode.py'],
    pathex=[],
    binaries=[('m_window.cpython-312-darwin.so', 'mainwindow'), ('mainwindow.cpython-312-darwin.so', 'mainwindow'), ('data.cpython-312-darwin.so', 'data')],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='barcode',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
app = BUNDLE(
    exe,
    name='barcode.app',
    icon=None,
    bundle_identifier=None,
)
