# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for PromptBoard v1.1.1.

Build with:
    python -m PyInstaller pyinstaller.spec --noconfirm

Produces a single-file Windows executable in ``dist/`` with the
PromptBoard icon, no console window, and the assets bundled in.
"""

block_cipher = None

a = Analysis(
    ['src\\promptboard.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('PromptBoard.ico', '.'),
        ('PromptBoard.png', '.'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtNetwork',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'PIL',
        'IPython',
        'pytest',
    ],
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
    name='PromptBoard-1.1.1-win64',
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
    icon='PromptBoard.ico',
)
