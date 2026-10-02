# -*- mode: python ; coding: utf-8 -*-
# One executable. No installer. PyInstaller unpacks it when it starts.

from pathlib import Path

import sherpa_onnx
import sounddevice

root = Path(SPECPATH)
sys_path = str(root / "src")
if sys_path not in __import__("sys").path:
    __import__("sys").path.insert(0, sys_path)
from grok_assistant.buildinfo import write_stamp

write_stamp(root / "src" / "grok_assistant" / "build_stamp.txt")

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
        (str(root / "src" / "grok_assistant" / "lang"), "grok_assistant/lang"),
        (str(root / "src" / "grok_assistant" / "ui" / "themes"), "grok_assistant/ui/themes"),
        (str(root / "scripts"), "scripts"),
        (str(root / "listeners"), "listeners"),
        (str(root / "docs" / "img"), "docs/img"),
        (str(root / "LICENSE.md"), "."),
        (str(root / "src" / "grok_assistant" / "build_stamp.txt"), "grok_assistant"),
        (str(portaudio), "_sounddevice_data/portaudio-binaries"),
    ],
    hiddenimports=[
        "grok_assistant",
        "grok_assistant.cloud.account_usage",
        "grok_assistant.cloud.account_agents",
        "grok_assistant.cloud.grok_cli",
        "grok_assistant.cloud.prompts",
        "grok_assistant.cloud.setup_grok",
        "grok_assistant.console",
        "grok_assistant.buildinfo",
        "grok_assistant.house.helptext",
        "grok_assistant.house.updates",
        "grok_assistant.house.marketplace",
        "grok_assistant.house.music",
        "grok_assistant.house.personality",
        "grok_assistant.listening.kroko_ear",
        "grok_assistant.listening.listen",
        "grok_assistant.listening.offline_ear",
        "grok_assistant.listening.refine",
        "grok_assistant.listening.voiceprint",
        "grok_assistant.mind.local_llm",
        "grok_assistant.notebook.auth",
        "grok_assistant.notebook.settings",
        "grok_assistant.notebook.store",
        "grok_assistant.rules.brain",
        "grok_assistant.rules.hub",
        "grok_assistant.rules.match",
        "grok_assistant.speaking.speech",
        "grok_assistant.ui.app",
        "grok_assistant.ui.theme",
        "grok_assistant.ui.win_tray",
        "sherpa_onnx",
        "sherpa_onnx.lib._sherpa_onnx",
        "sounddevice",
        "_sounddevice_data",
        "numpy",
        "cffi",
        "_cffi_backend",
        "grok_assistant.i18n",
        "grok_assistant.paths",
        "grok_assistant.quiet",
        "grok_assistant.startup",
        "grok_assistant.textutil",
        "pystray",
        "pystray._win32",
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
        "PIL.ImageTk",
        "grok_assistant.ui.round",
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
    version=str(root / "packaging" / "version-info.txt"),
    disable_windowed_traceback=False,
)
