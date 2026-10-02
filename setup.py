"""Stage the files a pip install needs, then let pyproject.toml describe the package."""

import sys
from pathlib import Path
import shutil

from setuptools import setup

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
PACKAGE = ROOT / "src" / "grok_assistant"
BUNDLE = PACKAGE / "_bundle"


def stage() -> None:
    """Copy repo files into the package. A wheel built from the sdist already has them."""
    from grok_assistant.buildinfo import write_stamp

    speak = ROOT / "scripts" / "speak.ps1"
    if not speak.is_file():
        if not (BUNDLE / "scripts" / "speak.ps1").is_file():
            raise SystemExit("scripts/speak.ps1 is missing")
        return
    if BUNDLE.exists():
        shutil.rmtree(BUNDLE)
    shutil.copytree(ROOT / "scripts", BUNDLE / "scripts")
    shutil.copytree(ROOT / "listeners", BUNDLE / "listeners")
    images = BUNDLE / "docs" / "img"
    images.mkdir(parents=True)
    for name in ("grok.ico", "grok-mark.png"):
        source = ROOT / "docs" / "img" / name
        if source.is_file():
            shutil.copy2(source, images / name)
    shutil.copy2(ROOT / "LICENSE.md", BUNDLE / "LICENSE.md")
    write_stamp(PACKAGE / "build_stamp.txt")


def packaged_files() -> list[str]:
    names: list[str] = []
    for folder in ("lines", "lang", "ui/themes", "_bundle"):
        base = PACKAGE / folder
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file():
                names.append(path.relative_to(PACKAGE).as_posix())
    stamp = PACKAGE / "build_stamp.txt"
    if stamp.is_file():
        names.append("build_stamp.txt")
    return names


stage()
setup(package_data={"grok_assistant": packaged_files()})
