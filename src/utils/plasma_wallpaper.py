"""KDE Plasma wallpaper helper via qdbus."""

from __future__ import annotations

import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)


def _find_qdbus() -> str | None:
    return shutil.which("qdbus") or shutil.which("qdbus-qt6") or shutil.which("qdbus6")


def set_wallpaper(path: str, mode: str = "image") -> bool:
    """Set the desktop wallpaper on KDE Plasma. Returns True on success."""
    qdbus_path = _find_qdbus()
    if not qdbus_path:
        logger.warning("qdbus not found")
        return False

    safe_path = path.replace("'", r"\'")
    script = (
        "var allDesktops = desktops();\n"
        "for (var i = 0; i < allDesktops.length; i++) {\n"
        "  var d = allDesktops[i];\n"
        "  d.wallpaperPlugin = 'org.kde.image';\n"
        "  d.currentConfigGroup = Array('Wallpaper','org.kde.image','General');\n"
        f"  d.writeConfig('Image', 'file://{safe_path}');\n"
        "}\n"
    )
    try:
        subprocess.run(
            [qdbus_path, "org.kde.plasmashell", "/PlasmaShell", "org.kde.PlasmaShell.evaluateScript", script],
            capture_output=True, text=True, check=False,
        )
        return True
    except Exception:
        logger.exception("Failed to call qdbus")
        return False
