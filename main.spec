# -*- mode: python ; coding: utf-8 -*-
# Copyright (c) 2026, Systems and Standards Group, Institute of Energy Conversion, University of Delaware


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('images/*.png', 'images/'), ('images/*.gif', 'images/')],
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
    name='LIN-CP-Parser',
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
