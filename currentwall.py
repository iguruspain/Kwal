#!/usr/bin/env python3
"""Small test script that calls Controller.getCurrentSystemWallpaper()

This imports the `Controller` from the project and prints the detected
system wallpaper path (or an explicit marker if none is found).
"""
from __future__ import annotations

import logging
import sys

from src.controllers.controller import Controller


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    try:
        ctrl = Controller()
        res = ctrl.getCurrentSystemWallpaper()
        if res:
            print(res)
        else:
            print("<empty>")
    except Exception:
        logging.exception("Error calling getCurrentSystemWallpaper")
        # Ensure script exits non-zero so CI / caller can detect failure
        sys.exit(1)


if __name__ == "__main__":
    main()
