# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app_build.py'],
    pathex=[],
    binaries=[],
    datas=[('database_neon.py', '.'), ('notificador.py', '.'), ('templates/email_template.html', '.')],
    hiddenimports=['psycopg2', 'psycopg2.extras', 'psycopg2._psycopg', 'dotenv'],
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
    version='C:\\Users\\WALTUI~1.NET\\AppData\\Local\\Temp\\cd72920d-6d10-4e84-bc99-45142db40568',
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
