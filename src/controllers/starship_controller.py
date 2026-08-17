"""Starship feature mixin: prompt theme preview and config application."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from PySide6.QtCore import QObject, Property, Signal, Slot
from ..models.models import StarshipTemplateModel
from ..utils import file_utils

class StarshipMixin:
    starshipDraftColorChanged = Signal()

    starshipIsFileModeChanged = Signal()

    starshipTemplateIndexChanged = Signal()

    starshipBackupExistsChanged = Signal()

    @Property(QObject, constant=True)
    def starshipModel(self) -> QObject:
        """Expose the StarshipModel instance to QML as an object."""
        return getattr(self, "_starship_model", None)

    def _get_starship_draft_color(self) -> str:
        return self._starship_draft_color

    def _set_starship_draft_color(self, val: str) -> None:
        if self._starship_draft_color != val:
            self._starship_draft_color = val
            self.starshipDraftColorChanged.emit()

    starshipDraftColor = Property(str, _get_starship_draft_color, _set_starship_draft_color, notify=starshipDraftColorChanged)

    def _get_starship_is_file_mode(self) -> bool:
        return self._starship_is_file_mode

    def _set_starship_is_file_mode(self, val: bool) -> None:
        if self._starship_is_file_mode != val:
            self._starship_is_file_mode = val
            self.starshipIsFileModeChanged.emit()

    starshipIsFileMode = Property(bool, _get_starship_is_file_mode, _set_starship_is_file_mode, notify=starshipIsFileModeChanged)

    def _get_starship_template_index(self) -> int:
        return self._starship_template_index

    def _set_starship_template_index(self, val: int) -> None:
        if self._starship_template_index != val:
            self._starship_template_index = val
            self.starshipTemplateIndexChanged.emit()

    starshipTemplateIndex = Property(int, _get_starship_template_index, _set_starship_template_index, notify=starshipTemplateIndexChanged)

    @Property(QObject, constant=True)
    def starshipTemplateModel(self) -> StarshipTemplateModel:
        return self._starship_template_model

    def _get_starship_backup_exists(self) -> bool:
        cfg = Path.home() / ".config" / "starship.toml"
        bak = cfg.with_name(cfg.name + ".bak")
        return bak.exists() and bak.is_file()

    hasStarshipBackup = Property(bool, _get_starship_backup_exists, notify=starshipBackupExistsChanged)

    @Property(bool, notify=starshipBackupExistsChanged) # Re-using signal for simplicity as file IO usually affects both
    def hasStarshipConfig(self) -> bool:
        cfg = Path.home() / ".config" / "starship.toml"
        return cfg.exists() and cfg.is_file()

    @Slot()
    def starshipClearSelection(self) -> None:
        """Clear starship selection state."""
        # Use public Property assignments so QML bindings reliably receive
        # notifications. Also refresh the Starship template model to ensure
        # the UI (ComboBox) reflects the cleared state.
        try:
            self.starshipIsFileMode = False
        except Exception:
            self._set_starship_is_file_mode(False)

        try:
            self.starshipTemplateIndex = -1
        except Exception:
            self._set_starship_template_index(-1)

        # Clear any selected custom file and reset draft color
        self.clearSelectedFile()
        try:
            self.starshipDraftColor = "transparent"
        except Exception:
            self._set_starship_draft_color("transparent")

        # Ensure template model is refreshed from the StarshipModel's template folder
        try:
            if hasattr(self, "_starship_template_model") and hasattr(self, "_starship_model") and getattr(self._starship_model, "_template_folder", None):
                self._starship_template_model.refresh(self._starship_model._template_folder)
            elif hasattr(self, "_starship_template_model"):
                # Fallback: try refreshing with None (model should handle missing path)
                try:
                    self._starship_template_model.refresh()
                except Exception:
                    pass
        except Exception:
            # Best-effort refresh; ignore failures here
            pass

    @Slot()
    def restoreStarshipBackup(self) -> None:
        """Restore the starship config backup."""
        try:
            ok = file_utils.restore_starship_config_backup(None)
            if ok:
                msg = "Restored starship config from backup"
                self._show_result_dialog(msg)
                self.starshipBackupExistsChanged.emit()
                
                # Refresh model
                self._starship_model.refresh()
                # Reload current preview since we changed disk state
                self._starship_model.reloadCurrentConfigPreview()
                
                # Clear selection
                self.starshipClearSelection()
            else:
                msg = "No backup found to restore"
                self._show_result_dialog(msg)
        except Exception:
            self._logger.exception("Failed restoring starship backup")
            self._show_result_dialog("Unexpected error restoring backup")

    @Slot()
    def applyStarshipConfig(self) -> None:
        """Apply the current starship configuration state to ~/.config/starship.toml."""
        from ..utils.file_utils import apply_starship_palettes_atomic
        try:
            # Determine Source
            source_path = ""
            if self._starship_is_file_mode and self._selected_file:
                source_path = self._selected_file.replace("file://", "")
            elif self._starship_template_index >= 0:
                data = self._starship_template_model.get(self._starship_template_index)
                if data and "filePath" in data:
                    source_path = data["filePath"]
            else:
                # Use current config as base if no template selected (just applying palette edits to current)
                source_path = self._starship_model.configPath

            if not source_path or not os.path.exists(source_path):
                self._show_result_dialog("Invalid source configuration.")
                return

            dest_path = Path.home() / ".config" / "starship.toml"
            self._logger.info("Applying starship config (Surgical) Source: %s -> Dest: %s", source_path, dest_path)

            # Decide if we should copy the selected source into the dest.
            # Per spec:
            # - If dest does not exist -> copy source (template/file/current) to initialize
            # - If dest exists and user selected a template/file (not Current Config) -> overwrite dest with source
            # - If dest exists and user selected Current Config -> do NOT overwrite, only apply palette edits
            is_template_selection = bool(self._starship_template_index >= 0 or self._starship_is_file_mode)
            should_copy_to_dest = (not dest_path.exists()) or is_template_selection

            # Create Backup of existing config (do this before any filesystem changes)
            if file_utils.backup_config_file(dest_path) is not None:
                self.starshipBackupExistsChanged.emit()

            # Ensure destination directory exists (after attempting backup)
            try:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                self._logger.exception("Failed ensuring starship config dir")
                self._show_result_dialog("Failed ensuring config directory")
                return

            # If we should initialize/overwrite dest from the selected source, do it now
            if should_copy_to_dest:
                try:
                    if source_path and os.path.exists(source_path):
                        shutil.copy2(source_path, dest_path)
                    else:
                        # If no valid source, create an empty file so surgical updater has something to work on
                        dest_path.touch()
                except Exception as e:
                    self._logger.error("Failed to initialize config file from source: %s", e)
                    self._show_result_dialog(f"Failed to initialize config file: {e}")
                    return

            # 3. Prepare Data from Model (which holds the current edited state)
            names = self._starship_model._palette_names
            values = self._starship_model._palette_values
            keys = self._starship_model._palette_keys
            
            if not names:
                 self._show_result_dialog("No palette data available to apply.")
                 return

            # 4. Construct Palette Dictionaries
            palettes_to_save = []
            for idx, pname in enumerate(names):
                if idx < len(values) and idx < len(keys):
                    pvals = values[idx]
                    pkeys = keys[idx]
                    
                    palette_dict = {}
                    # Single value check logic preserved from original, though rare for starship palettes
                    if len(pkeys) == 1 and pkeys[0] == "value":
                         # If it's a single value, surgical tool can't handle it as a [block]
                         # Skip or warn? For now, skip to avoid breaking standard palettes
                         continue
                    else:
                         for k, v in zip(pkeys, pvals):
                             palette_dict[k] = v
                    palettes_to_save.append(( pname, palette_dict))

            # 5. Apply Updates atomically in a single write to avoid multiple
            # overwrites and duplicated log entries. Move first palette to the end
            # so the original index 0 becomes the active palette.
            if palettes_to_save:
                ordered = palettes_to_save[1:] + [palettes_to_save[0]] if len(palettes_to_save) > 1 else palettes_to_save
                active_name = ordered[-1][0]
            else:
                ordered = []
                active_name = None

            if ordered:
                if not apply_starship_palettes_atomic(str(dest_path), ordered, active_name):
                    self._logger.error("Atomic update failed for starship config")
                    self._show_result_dialog("Failed writing to config file (Atomic Error).")
                    return
            
              # success path continues

            self._show_result_dialog("Starship configuration applied successfully.")
            
            # Refresh to reflect disk state
            self._starship_model.refresh(str(dest_path))
            # Force reload of current preview
            self._starship_model.reloadCurrentConfigPreview()

        except Exception as e:
            self._logger.exception("Failed processing starship config")
            self._show_result_dialog(f"Error applying config: {e}")
