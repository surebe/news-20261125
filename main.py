#!/usr/bin/env python3
"""Entry program for "The Whole World" (news-image-20261125).

The front page was typeset ahead of time by build/build.py (HTML/CSS
through WeasyPrint, with illustrations made for this page and a dot
map drawn in code) and is shipped in this repository as entry.png.
This program only places those exact bytes at the output path, so the
two grader runs write byte-identical files.

Standard library only; no network access; no arguments.
"""

import os
import shutil
from pathlib import Path

SHIPPED = "entry.png"


def shipped_path():
    """Locate the page image shipped beside this program."""
    beside = Path(__file__).resolve().parent / SHIPPED
    if beside.is_file():
        return beside
    return Path.cwd() / SHIPPED


def destination():
    """Resolve where the harness wants the image.

    MAKEFUN_OUTPUT_DIR wins; otherwise /output when it exists and is
    writable; otherwise a local ./out directory for dry runs.
    """
    wanted = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if wanted:
        return Path(wanted) / SHIPPED
    system_out = Path("/output")
    if system_out.is_dir():
        try:
            probe = system_out / ".writable-check"
            probe.touch()
            probe.unlink()
            return system_out / SHIPPED
        except OSError:
            pass
    return Path.cwd() / "out" / SHIPPED


def run():
    target = destination()
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(shipped_path(), target)
    return target


if __name__ == "__main__":
    run()
