# -*- mode: python ; coding: utf-8 -*-

# pyinstaller spec file to build a stand-alone Windows .exe application

block_cipher = None


a = Analysis(['FlatCaptureNow1.py'],
             pathex=['\\\\Mac\\Dropbox\\Dropbox\\EWHO\\Application Development\\FlatCaptureNow1'],
             binaries=[],
             datas=[('MainWindow.ui', '.'), ('PrefsWindow.ui','.'), ('SessionConsole.ui', '.')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='FlatCaptureNow1',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False )
