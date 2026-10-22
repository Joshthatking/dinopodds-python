# -*- mode: python ; coding: utf-8 -*-
# Build:  python -m PyInstaller DinoPodds.spec --noconfirm --clean
#   Windows -> dist/DinoPodds/DinoPodds.exe   (ship the whole folder)
#   Mac     -> dist/DinoPodds.app             (built by .github/workflows/release.yml)
import sys

IS_MAC = sys.platform == 'darwin'

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')],
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
    [],
    exclude_binaries=True,
    name='DinoPodds',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/DinoPodds.icns' if IS_MAC else 'assets/DinoPodds.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DinoPodds',
)

if IS_MAC:   # wrap the folder as a double-clickable DinoPodds.app
    app = BUNDLE(
        coll,
        name='DinoPodds.app',
        icon='assets/DinoPodds.icns',
        bundle_identifier='com.joshthatking.dinopodds',
        info_plist={
            'CFBundleDisplayName': 'DinoPodds',
            'NSHighResolutionCapable': True,
        },
    )
