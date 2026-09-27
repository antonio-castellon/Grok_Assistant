# -*- mode: python ; coding: utf-8 -*-
# One executable. No installer. PyInstaller unpacks it when it starts.

from pathlib import Path

root = Path(SPECPATH)

a = Analysis(
    [str(root / "src" / "grok_assistant" / "__main__.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=[
        (str(root / "src" / "grok_assistant" / "lines"), "grok_assistant/lines"),
        (str(root / "scripts"), "scripts"),
        (str(root / "listeners"), "listeners"),
    ],
    hiddenimports=[
        "grok_assistant",
        "grok_assistant.auth",
        "grok_assistant.brain",
        "grok_assistant.console",
        "grok_assistant.grok_cli",
        "grok_assistant.helptext",
        "grok_assistant.hub",
        "grok_assistant.listen",
        "grok_assistant.match",
        "grok_assistant.music",
        "grok_assistant.paths",
        "grok_assistant.prompts",
        "grok_assistant.settings",
        "grok_assistant.setup_grok",
        "grok_assistant.speech",
        "grok_assistant.store",
        "grok_assistant.textutil",
        "grok_assistant.tray",
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
