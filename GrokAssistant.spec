# -*- mode: python ; coding: utf-8 -*-
# One executable. No installer. PyInstaller unpacks it when it starts.

from pathlib import Path

import sherpa_onnx
import sounddevice

root = Path(SPECPATH)

# The extension and its DLLs have to stay in sherpa_onnx/lib. Flattening them breaks the import.
sherpa_bins = [
    (str(item), "sherpa_onnx/lib")
    for item in (Path(sherpa_onnx.__file__).parent / "lib").iterdir()
    if item.suffix.lower() in {".dll", ".pyd"}
]
portaudio = Path(sounddevice.__file__).parent / "_sounddevice_data" / "portaudio-binaries" / "libportaudio64bit.dll"

a = Analysis(
    [str(root / "src" / "grok_assistant" / "__main__.py")],
    pathex=[str(root / "src")],
    binaries=sherpa_bins,
    datas=[
        (str(root / "src" / "grok_assistant" / "lines"), "grok_assistant/lines"),
        (str(root / "scripts"), "scripts"),
        (str(root / "listeners"), "listeners"),
        (str(root / "docs" / "img"), "docs/img"),
        (str(portaudio), "_sounddevice_data/portaudio-binaries"),
    ],
    hiddenimports=[
        "grok_assistant",
        "grok_assistant.account_usage",
        "grok_assistant.auth",
        "grok_assistant.brain",
        "grok_assistant.console",
        "grok_assistant.grok_cli",
        "grok_assistant.helptext",
        "grok_assistant.kroko_ear",
        "grok_assistant.offline_ear",
        "sherpa_onnx",
        "sherpa_onnx.lib._sherpa_onnx",
        "sounddevice",
        "_sounddevice_data",
        "numpy",
        "cffi",
        "_cffi_backend",
        "grok_assistant.hub",
        "grok_assistant.listen",
        "grok_assistant.local_llm",
        "grok_assistant.marketplace",
        "grok_assistant.match",
        "grok_assistant.music",
        "grok_assistant.paths",
        "grok_assistant.personality",
        "grok_assistant.quiet",
        "grok_assistant.prompts",
        "grok_assistant.settings",
        "grok_assistant.setup_grok",
        "grok_assistant.speech",
        "grok_assistant.startup",
        "grok_assistant.voiceprint",
        "grok_assistant.refine",
        "grok_assistant.store",
        "grok_assistant.textutil",
        "grok_assistant.tray",
        "grok_assistant.win_tray",
        "pystray",
        "pystray._win32",
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="GrokAssistant",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(root / "docs" / "img" / "grok.ico"),
    disable_windowed_traceback=False,
)
