# -*- mode: python ; coding: utf-8 -*-
import os
import customtkinter

block_cipher = None

ctk_path = os.path.dirname(customtkinter.__file__)

a = Analysis(
    ['run_gui.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        (ctk_path, 'customtkinter'),
    ],
    hiddenimports=[
        'pixellab_tool',
        'pixellab_tool.client',
        'pixellab_tool.utils',
        'PIL',
        'PIL._tkinter_finder',
        'dotenv',
        'requests',
        'customtkinter',
        'charset_normalizer',
        'charset_normalizer.md__mypyc',
    ],
    hookspath=[],
    hooksconfig={},
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PixelLab-Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    windowed=True,
    icon=None,
)
