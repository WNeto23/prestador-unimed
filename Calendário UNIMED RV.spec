# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app_build.py'],
    pathex=[],
    binaries=[],
    datas=[('api_client.py', '.'), ('notificador.py', '.'), ('templates/email_template.html', 'templates')],
    hiddenimports=['requests', 'dotenv'],
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
    name='Calendário UNIMED RV',
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
    version='C:\\Users\\WALTUI~1.NET\\AppData\\Local\\Temp\\c0084459-a214-42b1-9fe6-8d5e1b223905',
    icon=['unimed_rv.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Calendário UNIMED RV',
)
