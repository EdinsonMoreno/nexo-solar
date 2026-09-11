# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Incluir solo los módulos de PyQt6 que PyInstaller no detecta automáticamente
hiddenimports = [
    'PyQt6.sip',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtNetwork',
    'PyQt6.QtPrintSupport',
    'PyQt6.QtSvg',
    'PyQt6.QtOpenGL',
    'PyQt6.QtWebEngineCore',
    'PyQt6.QtWebEngineWidgets',
    'PyQt6.QtWebChannel',
    'PyQt6.QtWebSockets',
    'PyQt6.QtCharts',
]

a = Analysis([
    'modbuspython/main_app.py',
],
    pathex=['.'],
    binaries=[],
    datas=[
        # Recursos UI y backend
        ('Mockup/*', 'Mockup'),
        ('Mockup/vendor/leaflet/*', 'Mockup/vendor/leaflet'),
        ('modbuspython/ui/assets/leaflet/*', 'ui/assets/leaflet'),
        ('modbuspython/ui/assets/leaflet/images/*', 'ui/assets/leaflet/images'),
        ('modbuspython/ui/assets/images/*', 'ui/assets/images'),
        ('modbuspython/ui/assets/mapa.html', 'ui/assets'),
        ('modbuspython/assets/LogoNexoSolar.png', 'assets'),
        ('modbuspython/assets/tripod_assembly.glb', 'assets'),
        ('modbuspython/assets/threejs/*', 'assets/threejs'),
        # Documentación relevante
        ('modbuspython/DOCUMENTACION_COMPLETA.md', 'modbuspython'),
        ('modbuspython/config/*.yaml', 'modbuspython/config'),
        ('modbuspython/config/*.json', 'modbuspython/config'),
        ('docs/*.md', 'docs'),
        # Archivos HTML y recursos 3D
        ('modbuspython/ui/visor_3d_piranometro.html', 'ui'),
        # Iconos
        ('modbuspython/ico/*', 'ico'),
    ],
    hiddenimports=hiddenimports,
    hookspath=['.'],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Nexo Solar',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='modbuspython/ico/ico.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Nexo Solar'
)
