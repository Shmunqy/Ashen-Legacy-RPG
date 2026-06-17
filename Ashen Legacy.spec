# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['Ashen Legacy.py'],
    pathex=[],
    binaries=[],
    datas=[('Ashen Legacy - Weapons', 'Ashen Legacy - Weapons'), ('Ashen Legacy - Enemies', 'Ashen Legacy - Enemies'), ('Ashen Legacy - Lone Warrior', 'Ashen Legacy - Lone Warrior'), ('Ashen Legacy - Particles', 'Ashen Legacy - Particles'), ('Ashen Legacy - Portal', 'Ashen Legacy - Portal'), ('Ashen Legacy - SFX', 'Ashen Legacy - SFX'), ('Ashen Legacy - Boss', 'Ashen Legacy - Boss'), ('Ashen Legacy - Vine.png', 'Ashen Legacy - Vine.png'), ('Ashen Legacy - Cave Wall.png', 'Ashen Legacy - Cave Wall.png'), ('Ashen Legacy - Cave Background.png', 'Ashen Legacy - Cave Background.png'), ('Ashen Legacy - Bush.png', 'Ashen Legacy - Bush.png'), ('Ashen Legacy - Tree Border.png', 'Ashen Legacy - Tree Border.png'), ('Ashen Legacy - Grass Background.png', 'Ashen Legacy - Grass Background.png'), ('Ashen Legacy - Splash Screen.png', 'Ashen Legacy - Splash Screen.png'), ('Ashen Legacy - Menu Rect.png', 'Ashen Legacy - Menu Rect.png'), ('Ashen Legacy - Menu Background.png', 'Ashen Legacy - Menu Background.png'), ('Ashen Legacy - Font.ttf', 'Ashen Legacy - Font.ttf')],
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
    name='Ashen Legacy',
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
