import shutil
import sys
from importlib import resources
from pathlib import Path

from .xdg_paths import xdg_config_home


def _copy_tree(src: Path, dst: Path, force: bool = False) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for p in src.rglob("*"):
        rel = p.relative_to(src)
        target = dst.joinpath(rel)
        if p.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not force:
            continue
        shutil.copy2(p, target)


def install_templates_to_user(config_home: Path | None = None, force: bool = False) -> None:
    """Install packaged templates to the user's XDG config directory.

    The function searches for templates in several candidate locations:
    1. Packaged resources inside the `kwal` package (`resources/templates`).
    2. Repository path `src/resources/templates` (useful in development).
    3. System share paths under the installation prefix
       (`sys.prefix/share/kwal/templates`), `/usr/share/kwal/templates`,
       or `/usr/local/share/kwal/templates`.

    The directory structure is copied recursively into `XDG_CONFIG_HOME/kwal/templates`.
    """
    dest = (config_home or xdg_config_home()) / "kwal" / "templates"
    dest.mkdir(parents=True, exist_ok=True)

    # Candidate sources in order of preference
    candidates = []

    # 1) packaged resource via importlib.resources (Traversable)
    try:
        pkg_root = resources.files("kwal").joinpath("resources", "templates")
        # resources.files may return a Traversable; use as_file to get a real path
        with resources.as_file(pkg_root) as pkg_path:
            pkg_path = Path(pkg_path)
            if pkg_path.exists():
                candidates.append(pkg_path)
    except Exception:
        pass

    # 2) repository layout (development)
    try:
        repo_root = Path(__file__).resolve().parents[2]
        dev_path = repo_root / "src" / "resources" / "templates"
        if dev_path.exists():
            candidates.append(dev_path)
    except Exception:
        pass

    # 3) system-wide share locations
    try:
        candidates.append(Path(sys.prefix) / "share" / "kwal" / "templates")
    except Exception:
        pass
    candidates.extend([
        Path("/usr/share/kwal/templates"),
        Path("/usr/local/share/kwal/templates"),
    ])

    # Pick first existing candidate that contains files
    src = None
    for c in candidates:
        try:
            if c.exists():
                # check for at least one file
                if any(c.rglob("*")):
                    src = c
                    break
        except Exception:
            continue

    if src is None:
        # nothing to copy
        return

    _copy_tree(src, dest, force=force)
