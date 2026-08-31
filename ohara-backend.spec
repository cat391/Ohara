# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Ohara backend sidecar.
# Build:  pyinstaller ohara-backend.spec
# Output: dist/ohara-backend (single-file binary, bundled into the Tauri app)
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

# Packages with native libraries, data files, or dynamic imports that
# PyInstaller's static import scan misses.
collected = [
    'llama_cpp',              # native dylibs in llama_cpp/lib (incl. Metal backend)
    'transformers',
    'sentence_transformers',
    'llama_index',
    'llama_index.core',
    'llama_index.embeddings.huggingface',
    'llama_index.vector_stores.qdrant',
    'llama_index.readers.obsidian',
    'huggingface_hub',
    'qdrant_client',
    'uvicorn',                # loops/protocols loaded via dynamic import
]
for pkg in collected:
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports

hiddenimports += [
    'watchdog.observers',
    'watchdog.events',
    # tiktoken registers encodings (cl100k_base) via namespace plugins that
    # the static import scan can't see
    'tiktoken_ext',
    'tiktoken_ext.openai_public',
]

a = Analysis(
    ['backend/main.py'],
    pathex=['backend'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='ohara-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
