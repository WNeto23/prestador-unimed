# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app_build.py'],
    pathex=[],
    binaries=[],
    datas=[('database_neon.py', '.'), ('notificador.py', '.'), ('email_template.html', '.')],
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
    a.binaries,
    a.datas,
    [],
    name='Calendário UNIMED RV',
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
    version='C:\\Users\\WALTUI~1.NET\\AppData\\Local\\Temp\\c80ecda5-d5ef-4bd1-afb8-df045cd87b22',
    icon=['unimed_rv.ico'],
)
