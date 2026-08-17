"""Ulauncher models: theme list and the editable theme model."""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

from PySide6.QtCore import (
    QAbstractListModel,
    QModelIndex,
    QObject,
    Property,
    Qt,
    Signal,
    Slot,
)

from ..utils.xdg_paths import kwal_config_dir
from .preview_base import PreviewModelBase

# Logger
logger = logging.getLogger(__name__)


class UlauncherTemplateModel(QAbstractListModel):
    FolderNameRole = Qt.UserRole + 1
    FolderPathRole = Qt.UserRole + 2
    FolderUrlRole = Qt.UserRole + 3
    IsTemplateRole = Qt.UserRole + 4

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._items: list[dict[str, Any]] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < self.rowCount()):
            return None
        item = self._items[index.row()]
        p = item["path"]
        if role == UlauncherTemplateModel.FolderNameRole:
            return p.name
        if role == UlauncherTemplateModel.FolderPathRole:
            return str(p)
        if role == UlauncherTemplateModel.FolderUrlRole:
            return "file://" + str(p)
        if role == UlauncherTemplateModel.IsTemplateRole:
            return item["is_template"]
        return None

    def roleNames(self) -> dict[int, bytes]:
        return {
            UlauncherTemplateModel.FolderNameRole: b"fileName",
            UlauncherTemplateModel.FolderPathRole: b"filePath",
            UlauncherTemplateModel.FolderUrlRole: b"fileUrl",
            UlauncherTemplateModel.IsTemplateRole: b"isTemplate",
        }

    @Slot()
    @Slot(str)
    def refresh(self, template_folder: str | None = None) -> None:
        """Populate model from multiple theme sources.

        Sources:
        1. Managed templates (configured folder) -> is_template=True
        2. Internal templates (src/resources/templates/ulauncher) -> is_template=True
        3. User themes (~/.config/ulauncher/user-themes/) -> is_template=False
        """
        try:
            from ..utils.file_utils import list_ulauncher_templates

            new_items: list[dict[str, Any]] = []
            seen_paths: set[str] = set()

            # 1. Managed templates (external config)
            if template_folder:
                for p_str in list_ulauncher_templates(template_folder):
                    p = Path(p_str)
                    res_path = str(p.resolve())
                    theme_key = p.name # Use folder name as key
                    if theme_key not in seen_paths and res_path not in seen_paths:
                        new_items.append({"path": p.resolve(), "is_template": True})
                        seen_paths.add(theme_key)
                        seen_paths.add(res_path)

            # 2. Internal templates (Development/Bundled)
            try:
                internal_root = Path(__file__).parent.parent / "resources" / "templates" / "ulauncher"
                if internal_root.is_dir():
                    for p_str in list_ulauncher_templates(internal_root):
                        p = Path(p_str)
                        res_path = str(p.resolve())
                        theme_key = p.name
                        if theme_key not in seen_paths and res_path not in seen_paths:
                            new_items.append({"path": p.resolve(), "is_template": True})
                            seen_paths.add(theme_key)
                            seen_paths.add(res_path)
            except Exception:
                pass

            # 3. User themes (These are installed, so we don't deduplicate against templates folder names,
            # but we still check path to avoid absolute path duplicates)
            user_themes = Path.home() / ".config" / "ulauncher" / "user-themes"
            for p_str in list_ulauncher_templates(user_themes):
                p = Path(p_str)
                res_path = str(p.resolve())
                if res_path not in seen_paths:
                    new_items.append({"path": p.resolve(), "is_template": False})
                    seen_paths.add(res_path)

            self.beginResetModel()
            self._items = new_items
            self.endResetModel()
            logger.debug("UlauncherTemplateModel refreshed %d items", len(self._items))
        except Exception:
            logger.exception("Failed refreshing UlauncherTemplateModel")

    @Slot(int, result="QVariantMap")
    def get(self, row: int) -> dict[str, Any]:
        """Expose item as map for QML."""
        if 0 <= row < self.rowCount():
            item = self._items[row]
            return {
                "fileName": item["path"].name,
                "filePath": str(item["path"]),
                "fileUrl": "file://" + str(item["path"]),
                "isTemplate": item["is_template"]
            }
        return {}


class UlauncherModel(PreviewModelBase):
    """QObject model exposing Ulauncher theme info for QML.

    Provides:
    - `configPath` (str): path to current theme directory
    - `templateFolder` (str): templates folder for ulauncher
    - `paletteNames` (list[str]): ["manifest", "theme"]
    - `paletteValues` (list[list[str]]): colors corresponding to keys
    - `paletteKeys` (list[list[str]]): keys for manifest and theme.css
    """

    configPathChanged = Signal()
    actualConfigPathChanged = Signal()
    templateFolderChanged = Signal()
    paletteNamesChanged = Signal()
    paletteValuesChanged = Signal()
    paletteKeysChanged = Signal()

    def __init__(self, config_path: str | None = None, template_folder: str | None = None, parent: QObject | None = None) -> None:
        super().__init__(default_scale=0.4, default_width=650, render_interval_ms=50, parent=parent)
        from pathlib import Path

        # Ulauncher config default
        self._config_file = Path.home() / ".config" / "ulauncher" / "settings.json"

        default_templates = str(kwal_config_dir() / "templates" / "ulauncher")

        self._current_theme_path: str = config_path or ""
        self._template_folder: str = template_folder or default_templates
        self._palette_names: list[str] = []
        self._palette_values: list[list[str]] = []
        self._palette_keys: list[list[str]] = []

        # Internal storage of full extracted data
        self._full_data: dict[str, Any] = {}
        self._original_palette_values: list[list[str]] = []

        # Debounce timer to avoid lag during resizing/editing
        self._render_timer.timeout.connect(self._refresh_previews)

    def _get_config_path(self) -> str:
        return self._current_theme_path

    def _set_config_path(self, p: str) -> None:
        val = str(p or "")
        if self._current_theme_path != val:
            self._current_theme_path = val
            self.configPathChanged.emit()

    def _get_template_folder(self) -> str:
        return self._template_folder

    def _set_template_folder(self, p: str) -> None:
        val = str(p or "")
        if self._template_folder != val:
            self._template_folder = val
            self.templateFolderChanged.emit()

    def _get_palette_names(self) -> list[str]:
        return list(self._palette_names)

    def _get_palette_values(self) -> list[list[str]]:
        return [list(x) for x in self._palette_values]

    def _get_palette_keys(self) -> list[list[str]]:
        return [list(x) for x in self._palette_keys]


    @Slot(int, int, str)
    def setPaletteColor(self, palette_idx: int, color_idx: int, color: str) -> None:
        try:
            from ..utils import color_utils
            if 0 <= palette_idx < len(self._palette_values):
                current_vals = self._palette_values[palette_idx]
                if 0 <= color_idx < len(current_vals):
                    # Smart format: Hex if solid, rgba if transparent
                    formatted_color = color_utils.format_css_color(color)
                    current_vals[color_idx] = formatted_color

                    # Update _full_data for preview
                    section_name = self._palette_names[palette_idx]
                    key_name = self._palette_keys[palette_idx][color_idx]
                    if section_name in self._full_data:
                        self._full_data[section_name][key_name] = formatted_color

                    # Update Preview
                    try:
                        self._render_timer.start()
                    except Exception:
                        pass

                    self.paletteValuesChanged.emit()
        except Exception:
            logger.exception("Failed setting ulauncher palette color")

    def _get_live_colors(self) -> dict[str, str]:
        """Flatten hierarchical palette into a single dict."""
        flat = {}
        for p_idx, p_name in enumerate(self._palette_names):
            # We only care about root values (manifest keys, theme variable names)
            # for the preview renderer logic.
            keys = self._palette_keys[p_idx]
            values = self._palette_values[p_idx]
            for k, v in zip(keys, values):
                flat[k] = str(v)
        return flat

    def _resolve_current_theme_path(self) -> str:
        """Read ulauncher settings.json, get theme_name, then find folder where manifest['name'] matches."""
        try:
            if not self._config_file.exists():
                return ""

            with self._config_file.open("r", encoding="utf-8") as f:
                settings = json.load(f)

            required_theme_name = settings.get("theme_name", "")
            if not required_theme_name:
                return ""

            # Helper to check a root directory
            def find_in_root(root: Path) -> str | None:
                if not root.is_dir():
                    return None
                for child in root.iterdir():
                    if child.is_dir():
                        manifest = child / "manifest.json"
                        if manifest.exists():
                            try:
                                with manifest.open("r", encoding="utf-8") as mf:
                                    data = json.load(mf)
                                    if data.get("name") == required_theme_name:
                                        return str(child.resolve())
                            except Exception:
                                pass
                return None

            # 1. Check user themes (Priority)
            found = find_in_root(Path.home() / ".config" / "ulauncher" / "user-themes")
            if found: return found

            # 2. Check system themes (Standard locations)
            # ~/.local/share/ulauncher/themes
            found = find_in_root(Path.home() / ".local" / "share" / "ulauncher" / "themes")
            if found: return found

            # /usr/share/ulauncher/themes
            found = find_in_root(Path("/usr/share/ulauncher/themes"))
            if found: return found

            # Fallback: check if directory exists with that name directly (old behavior/fallback)
            for p in [
                Path.home() / ".config" / "ulauncher" / "user-themes" / required_theme_name,
                Path("/usr/share/ulauncher/themes") / required_theme_name
            ]:
                if p.is_dir():
                    return str(p.resolve())

            return ""
        except Exception:
            logger.exception("Failed resolving ulauncher theme path")
            return ""

    @Slot(result=bool)
    def _get_is_modified(self) -> bool:
        return self._palette_values != self._original_palette_values

    def _get_all_colors_filled(self) -> bool:
        """Check if any color is still 'transparent' (the placeholder for ulauncher)."""
        for section in self._palette_values:
            for val in section:
                if str(val).lower() == "transparent":
                    return False
        return True

    def _refresh_previews(self) -> None:
        """Internal helper to start background tasks for HTML generation."""
        try:
            from ..utils import ulauncher_preview
            live = self._get_live_colors()

            # Resolve paths
            actual_current_path = self._resolve_current_theme_path()
            target_path = self._current_theme_path or actual_current_path

            if not target_path:
                return

            # 1. Update Live Preview
            self._start_worker(
                ulauncher_preview.generate_preview_html,
                (target_path, live, self._preview_scale, self._preview_width),
                "previewHtml"
            )

            # 2. Update Current Config Preview (if missing or if we just switched/resized)
            # For simplicity, we refresh it whenever _refresh_previews is called (timer/resize)
            # if they are different paths or if it's empty.
            if actual_current_path:
                self._start_worker(
                    ulauncher_preview.generate_preview_html,
                    (actual_current_path, {}, self._preview_scale, self._preview_width),
                    "currentConfigPreviewHtml"
                )

            # Also trigger current config preview if needed
            # For simplicity we could run another worker or just do it sequentially if they are light.
            # But let's stick to one worker for now to avoid too much overhead.
            # We will only background the "active" preview which is what feels laggy.
        except Exception:
            logger.exception("Failed starting Ulauncher background preview task")

    configPath = Property(str, _get_config_path, _set_config_path, notify=configPathChanged)
    actualConfigPath = Property(str, _resolve_current_theme_path, notify=actualConfigPathChanged)
    templateFolder = Property(str, _get_template_folder, _set_template_folder, notify=templateFolderChanged)
    paletteNames = Property('QVariantList', _get_palette_names, notify=paletteNamesChanged)
    paletteValues = Property('QVariantList', _get_palette_values, notify=paletteValuesChanged)
    paletteKeys = Property('QVariantList', _get_palette_keys, notify=paletteKeysChanged)
    isModified = Property(bool, _get_is_modified, notify=paletteValuesChanged)
    allColorsFilled = Property(bool, _get_all_colors_filled, notify=paletteValuesChanged)

    @Slot(result="QVariantMap")
    @Slot(str, result="QVariantMap")
    def refresh(self, path: str | None = None) -> dict:
        """Read ulauncher theme at path (or resolve current if None)."""
        try:
            from ..utils import file_utils

            target_path = path
            if not target_path:
                target_path = self._resolve_current_theme_path()
                # On startup/auto-refresh, signal that the actual config path is resolved
                self.actualConfigPathChanged.emit()

            self._set_config_path(target_path)

            if not target_path:
                # Clear if no theme found
                self._palette_names = []
                self._palette_values = []
                self._palette_keys = []
                self.paletteNamesChanged.emit()
                self.paletteValuesChanged.emit()
                self.paletteKeysChanged.emit()
                return {"config_path": "", "palettes_count": 0}

            data = file_utils.read_ulauncher_theme(target_path)
            self._full_data = data

            # Convert to lists for QML
            # We enforce a specific order: manifest, theme
            names = []
            keys = []
            values = []

            # Manifest
            manifest = data.get("manifest", {})
            if manifest:
                names.append("manifest")
                m_keys = list(manifest.keys())
                keys.append(m_keys)
                values.append([str(manifest[k]) for k in m_keys])

            # Theme
            theme = data.get("theme", {})
            if theme:
                 names.append("theme")
                 t_keys = list(theme.keys())
                 keys.append(t_keys)
                 values.append([str(theme[k]) for k in t_keys])

            self._palette_names = names
            self._palette_keys = keys
            self._palette_values = values
            self._original_palette_values = [list(x) for x in values] # Deep copy

            # Generate Preview - use timer for initial load too if it's the first time
            # or if we are refreshing against a new path.
            # This avoids blocking the UI when first opening the tab.
            self._render_timer.start()

            self.paletteNamesChanged.emit()
            self.paletteKeysChanged.emit()
            self.paletteValuesChanged.emit()

            return {"config_path": target_path, "palettes_count": len(names)}
        except Exception:
            logger.exception("UlauncherModel.refresh failed")
            return {"config_path": "", "palettes_count": 0}

    def _get_has_backup(self) -> bool:
        try:
             # Check if theme-specific .bak files exist
             theme_bak = False
             if self._current_theme_path:
                 p = Path(self._current_theme_path)
                 theme_bak = (p / "theme.css.bak").exists() or (p / "manifest.json.bak").exists()

             return theme_bak
        except Exception:
            return False

    hasBackup = Property(bool, _get_has_backup, notify=configPathChanged) # Re-check when config path changes

    @Slot(str)
    def deleteTheme(self, path: str) -> bool:
        """Delete a user theme directory.

        Validation:
        1. Cannot delete current ACTUAL config path (active theme).
        2. Cannot delete if it is a template (checking against template folder or internal resources).
        """
        try:
            if not path:
                return False

            p = Path(path).resolve()

            # 1. Protect Active Theme
            current_theme_path = self._resolve_current_theme_path()
            if current_theme_path and Path(current_theme_path).resolve() == p:
                logger.warning("Cannot delete active theme: %s", p)
                return False

            # 2. Protect Templates (simple heuristic: must be in user-themes)
            user_themes_root = Path.home() / ".config" / "ulauncher" / "user-themes"
            if user_themes_root.resolve() not in p.parents:
                 # It might be in local share or usr share, definitely protect those
                 logger.warning("Attempted to delete theme outside user-themes: %s", p)
                 return False

            if p.exists() and p.is_dir():
                shutil.rmtree(p)
                logger.info("Deleted Ulauncher theme: %s", p)
                return True
            return False
        except Exception:
            logger.exception("Failed to delete theme %s", path)
            return False

    @Slot(str, str, result=str)
    def createNewTheme(self, source_path: str, new_name: str) -> str:
        """Create a new theme based on source_path.

        Args:
            source_path: Path to the template/theme to copy.
            new_name: Name for the new theme directory.

        Returns:
            Absolute path to the new theme if successful, empty string otherwise.
        """
        try:
            if not source_path or not new_name:
                return ""

            src = Path(source_path).resolve()
            if not src.exists():
                return ""

            dest_root = Path.home() / ".config" / "ulauncher" / "user-themes"
            dest_root.mkdir(parents=True, exist_ok=True)

            dest = dest_root / new_name
            if dest.exists():
                logger.warning("Theme already exists: %s", dest)
                return ""

            # Copy all files recursively, excluding .bak
            # shutil.copytree with ignore_patterns

            def ignore_bak(dir, files):
                return [f for f in files if f.endswith('.bak')]

            shutil.copytree(src, dest, ignore=ignore_bak)

            # Now we must update manifest.json with the new name
            manifest_path = dest / "manifest.json"
            if manifest_path.exists():
                with manifest_path.open("r", encoding="utf-8") as f:
                    mdata = json.load(f)

                mdata["name"] = new_name
                mdata["display_name"] = new_name

                with manifest_path.open("w", encoding="utf-8") as f:
                    json.dump(mdata, f, indent=4)

            logger.info("Created new theme at %s", dest)
            return str(dest)

        except Exception:
            logger.exception("Failed to create new theme")
            return ""

    @Slot(str, result=str)
    def saveTheme(self, target_path: str = "") -> str:
        """Write current in-memory palette to target_path.

        Args:
             target_path: Destination folder. If empty, uses current `configPath`.

        Returns:
             Error message if failed/invalid, empty string on success.
        """
        try:
            save_to = target_path if target_path else self._current_theme_path
            if not save_to:
                return "No implementation path found."

            # Validation: reject themes that still contain "provisional" placeholder values
            for row in self._palette_values:
                for col in row:
                    val = str(col).lower()
                    if "provisional" in val:
                         return "Theme contains provisional values. Please customize all colors."

            from ..utils import file_utils

            data_to_write = {"manifest": {}, "theme": {}}

            for i, name in enumerate(self._palette_names):
                if i >= len(self._palette_keys) or i >= len(self._palette_values):
                    continue

                k_list = self._palette_keys[i]
                v_list = self._palette_values[i]

                combined = {}
                for j, key in enumerate(k_list):
                    val = v_list[j] if j < len(v_list) else ""
                    combined[key] = val

                if name == "manifest":
                    data_to_write["manifest"] = combined
                elif name == "theme":
                    data_to_write["theme"] = combined

            # Write to save_to
            if file_utils.write_ulauncher_theme(save_to, data_to_write, skip_backup=False):
                 return ""
            else:
                 return "Failed to write theme files."

        except Exception as e:
            logger.exception("saveTheme failed")
            return str(e)

    @Slot()
    def restore(self) -> None:
        """Restore .bak files if they exist (both settings and theme files)."""
        try:
            restored = False

            # Restore Theme Files
            if self._current_theme_path:
                p = Path(self._current_theme_path)

                # Restore Manifest
                man_bak = p / "manifest.json.bak"
                man_orig = p / "manifest.json"
                if man_bak.exists():
                    shutil.copy2(man_bak, man_orig)
                    restored = True

                # Restore CSS
                css_bak = p / "theme.css.bak"
                css_orig = p / "theme.css"
                if css_bak.exists():
                    shutil.copy2(css_bak, css_orig)
                    restored = True

            if restored:
                logger.info("Restored Ulauncher backups")
                self.refresh() # Reload model
                # Trigger property changes
                self.configPathChanged.emit()
        except Exception:
            logger.exception("Failed to restore Ulauncher backup")

    @Slot(result=str)
    def apply(self) -> str:
        """Apply current selection to Ulauncher system config.

        Logic:
        1. If it's a template, DO NOT apply. Return error.
        2. If it's a user theme, check if we need to set the `theme_name` in settings.json.
        3. Note: This method DOES NOT save the palette colors. It assumes they are saved.
           In the new flow, User clicks Save (writes to disk), then Apply (updates Ulauncher config).
        """
        try:
             p = Path(self._current_theme_path).resolve()
             user_themes_root = (Path.home() / ".config" / "ulauncher" / "user-themes").resolve()

             # Only allow applying user themes; templates and system themes are immutable.
             if user_themes_root not in p.parents:
                  return "Cannot apply a template directly. Please create a new theme from it."

             # Get the directory name, that is the `theme_name`
             theme_name = p.name

             # Locate settings.json
             settings_path = Path.home() / ".config" / "ulauncher" / "settings.json"
             if not settings_path.exists():
                 return "Ulauncher settings.json not found."

             with settings_path.open("r", encoding="utf-8") as f:
                 sdata = json.load(f)

             if sdata.get("theme_name") != theme_name:
                 sdata["theme_name"] = theme_name
                 with settings_path.open("w", encoding="utf-8") as f:
                     json.dump(sdata, f, indent=4)

                 # Force resolve update
                 self.actualConfigPathChanged.emit()
                 return "" # Success

             return "" # Already applied

        except Exception as e:
            logger.exception("UlauncherModel.apply failed")
