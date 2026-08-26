"""Ulauncher feature mixin: theme management and config application."""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from ..models.ulauncher_models import UlauncherModel, UlauncherTemplateModel
from ..utils.xdg_paths import kwal_config_dir


class UlauncherMixin:
    ulauncherDraftColorChanged = Signal()

    ulauncherIsFileModeChanged = Signal()

    ulauncherTemplateIndexChanged = Signal()

    ulauncherBackupExistsChanged = Signal()

    ulauncherNewThemeNameChanged = Signal()

    ulauncherTemplatesChanged = Signal()

    def _get_ulauncher_templates_generation(self) -> int:
        return getattr(self, "_ulauncher_templates_gen", 0)

    ulauncherTemplatesGeneration = Property(int, _get_ulauncher_templates_generation, notify=ulauncherTemplatesChanged)

    def _increment_ulauncher_templates_gen(self) -> None:
        val = getattr(self, "_ulauncher_templates_gen", 0)
        self._ulauncher_templates_gen = val + 1
        self.ulauncherTemplatesChanged.emit()

    def _get_ulauncher_draft_color(self) -> str:
        # Re-use simple string storage for draft (persisted per session if needed)
        return getattr(self, "_ulauncher_draft_color", "transparent")

    def _set_ulauncher_draft_color(self, val: str) -> None:
        if getattr(self, "_ulauncher_draft_color", "") != val:
            self._ulauncher_draft_color = val
            self.ulauncherDraftColorChanged.emit()

    ulauncherDraftColor = Property(
        str, _get_ulauncher_draft_color, _set_ulauncher_draft_color,
        notify=ulauncherDraftColorChanged,
    )

    def _get_ulauncher_is_file_mode(self) -> bool:
        return getattr(self, "_ulauncher_is_file_mode", False)

    def _set_ulauncher_is_file_mode(self, val: bool) -> None:
        if getattr(self, "_ulauncher_is_file_mode", False) != val:
            self._ulauncher_is_file_mode = val
            self.ulauncherIsFileModeChanged.emit()

    ulauncherIsFileMode = Property(
        bool, _get_ulauncher_is_file_mode, _set_ulauncher_is_file_mode,
        notify=ulauncherIsFileModeChanged,
    )

    def _get_ulauncher_template_index(self) -> int:
        return getattr(self, "_ulauncher_template_index", -1)

    def _set_ulauncher_template_index(self, val: int) -> None:
        if getattr(self, "_ulauncher_template_index", -1) != val:
            self._ulauncher_template_index = val
            self.ulauncherTemplateIndexChanged.emit()

    ulauncherTemplateIndex = Property(
        int, _get_ulauncher_template_index, _set_ulauncher_template_index,
        notify=ulauncherTemplateIndexChanged,
    )

    def _get_ulauncher_new_theme_name(self) -> str:
        return getattr(self, "_ulauncher_new_theme_name", "")

    def _set_ulauncher_new_theme_name(self, val: str) -> None:
        if getattr(self, "_ulauncher_new_theme_name", "") != val:
            self._ulauncher_new_theme_name = val
            self.ulauncherNewThemeNameChanged.emit()

    ulauncherNewThemeName = Property(
        str, _get_ulauncher_new_theme_name, _set_ulauncher_new_theme_name,
        notify=ulauncherNewThemeNameChanged,
    )

    @Property(QObject, constant=True)
    def ulauncherModel(self) -> QObject:
        return getattr(self, "_ulauncher_model", None)

    @Property(QObject, constant=True)
    def ulauncherTemplateModel(self) -> QObject:
        return getattr(self, "_ulauncher_template_model", None)

    @Property(bool, notify=ulauncherBackupExistsChanged)
    def hasUlauncherBackup(self) -> bool:
        if self._ulauncher_model:
            return self._ulauncher_model.hasBackup
        return False

    @Slot()
    def restoreUlauncherBackup(self) -> None:
        """Restore Ulauncher backups (settings and theme) and notify user."""
        try:
            if self._ulauncher_model:
                self._ulauncher_model.restore()
                self._show_result_dialog("Restored Ulauncher settings and theme from backups.")
                self.ulauncherBackupExistsChanged.emit()
                # Clear any transient selection state
                self.ulauncherClearSelection()
        except Exception:
            self._logger.exception("Failed restoring Ulauncher backup")
            self._show_result_dialog("Error restoring Ulauncher backup.")

    @Slot()
    def ulauncherClearSelection(self) -> None:
        self.ulauncherIsFileMode = False
        self.ulauncherTemplateIndex = -1
        self.clearSelectedFile()
        self.ulauncherDraftColor = "transparent"
        # Refresh from current config
        if hasattr(self, "_ulauncher_model"):
            self._ulauncher_model.refresh()

    @Slot()
    def ulauncherCreateNewTheme(self) -> None:
        """Create a new theme from the current selection (template or existing theme)."""
        try:
            name = self.ulauncherNewThemeName.strip()
            if not name:
                self._show_result_dialog("Please provide a name for the new theme.")
                return

            # Determine Source
            source_path = ""
            if self.ulauncherTemplateIndex >= 0:
                info = self._ulauncher_template_model.get(self.ulauncherTemplateIndex)
                source_path = info.get("filePath", "")

            if not source_path:
                 # Fallback to current config path if valid
                 source_path = self._ulauncher_model.configPath

            if not source_path:
                self._show_result_dialog("No source theme selected.")
                return

            new_path = self._ulauncher_model.createNewTheme(source_path, name)
            if new_path:
                self._show_result_dialog(f"Theme '{name}' created successfully.")
                self.ulauncherNewThemeName = ""

                # Refresh templates list to show new theme
                self._ulauncher_template_model.refresh(self._ulauncher_model.templateFolder)
                self._increment_ulauncher_templates_gen()

                # Select the new theme
                self._ulauncher_model.refresh(new_path)

                # Find index in template model
                tm = self._ulauncher_template_model
                for i in range(tm.rowCount()):
                    if tm.get(i)["filePath"] == new_path:
                        self.ulauncherTemplateIndex = i
                        break
            else:
                self._show_result_dialog("Failed to create theme. Check logs for details.")
        except Exception as e:
            self._logger.exception("ulauncherCreateNewTheme failed")
            self._show_result_dialog(f"Error creating theme: {e}")

    @Slot()
    def ulauncherSaveTheme(self) -> None:
        """Save changes to the currently selected USER theme."""
        try:
            # Prevent saving if it's a template
            if self.ulauncherTemplateIndex >= 0:
                info = self._ulauncher_template_model.get(self.ulauncherTemplateIndex)
                if info.get("isTemplate", False):
                    self._show_result_dialog("Cannot save changes to a template directly.\nPlease create a new theme.")
                    return

            err = self._ulauncher_model.saveTheme()
            if err:
                self._show_result_dialog(f"Failed to save theme:\n{err}")
            else:
                self._show_result_dialog("Theme saved successfully.")
                # Reload to clear modified state, keeping selection
                self._ulauncher_model.refresh(self._ulauncher_model.configPath)
        except Exception as e:
             self._logger.exception("ulauncherSaveTheme failed")
             self._show_result_dialog(f"Error saving theme: {e}")

    @Slot()
    def ulauncherDeleteTheme(self) -> None:
        """Delete the currently selected theme."""
        try:
             path = self._ulauncher_model.configPath
             if not path:
                 return

             # Double check via model's logic
             if self._ulauncher_model.deleteTheme(path):
                 self._show_result_dialog("Theme deleted successfully.")
                 self._ulauncher_template_model.refresh(self._ulauncher_model.templateFolder)
                 self._increment_ulauncher_templates_gen()
                 # Reset selection to actual current
                 self.ulauncherClearSelection()
             else:
                 self._show_result_dialog("Failed to delete theme.\n(Cannot delete active theme or templates).")
        except Exception as e:
            self._logger.exception("ulauncherDeleteTheme failed")
            self._show_result_dialog(f"Error deleting theme: {e}")

    @Slot()
    def ulauncherApplyTheme(self) -> None:
        """Apply the currently selected theme to system config."""
        try:
            err = self._ulauncher_model.apply()
            if err:
                 self._show_result_dialog(f"Failed to apply theme:\n{err}")
            else:
                 self._show_result_dialog("Theme applied to Ulauncher configuration.")
                 self._ulauncher_model.refresh()
        except Exception as e:
            self._logger.exception("ulauncherApplyTheme failed")
            self._show_result_dialog(f"Error applying theme: {e}")

    @Slot()
    def applyUlauncherConfig(self) -> None:
        self.ulauncherApplyTheme()

    def _init_ulauncher(self) -> None:
        """Initialize ulauncher models."""
        try:
            default_ulauncher_templates = str(kwal_config_dir() / "templates" / "ulauncher")
            self._ulauncher_model = UlauncherModel(template_folder=default_ulauncher_templates)
            self._ulauncher_template_model = UlauncherTemplateModel()
            self._ulauncher_template_model.refresh(default_ulauncher_templates)
            try:
                self._ulauncher_model.refresh()
            except Exception:
                self._logger.debug("Initial ulauncher model refresh failed or no theme set")
            self._ulauncher_model.configPathChanged.connect(self.ulauncherBackupExistsChanged)
        except Exception:
            self._logger.exception("Failed initializing UlauncherModel")
