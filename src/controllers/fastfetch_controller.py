"""Fastfetch feature mixin: tinting, preview, and config application."""

from __future__ import annotations

import shutil
import threading
from pathlib import Path
from typing import Any
from PySide6.QtCore import Property, Signal, Slot
from PySide6.QtGui import QColor
from ..utils import color_utils, file_utils
from ..utils.xdg_paths import fastfetch_config_path

class FastfetchMixin:
    fastfetchTintedPreviewChanged = Signal()

    fastfetchTintingChanged = Signal()

    fastfetchBackupExistsChanged = Signal()

    fastfetchConfigImageChanged = Signal()

    fastfetchConfigImagePathChanged = Signal()

    fastfetchDraftColorChanged = Signal()

    tintResult = Signal(str)

    fastfetchApplyResult = Signal(bool, str)

    def _get_fastfetch_tinted_preview(self) -> str:
        return self._fastfetch_tinted_preview

    fastfetchTintedPreview = Property(str, _get_fastfetch_tinted_preview, notify=fastfetchTintedPreviewChanged)

    def _get_fastfetch_tinting(self) -> bool:
        return self._fastfetch_tinting

    fastfetchTinting = Property(bool, _get_fastfetch_tinting, notify=fastfetchTintingChanged)

    def _get_fastfetch_config_image(self) -> str:
        return self._fastfetch_config_image

    def _set_fastfetch_config_image(self, path: str) -> None:
        p = path or ""
        if self._fastfetch_config_image != p:
            self._fastfetch_config_image = p
            self.fastfetchConfigImageChanged.emit()
            self._emit_fastfetch_config_image_path()

    fastfetchConfigImage = Property(str, _get_fastfetch_config_image, _set_fastfetch_config_image, notify=fastfetchConfigImageChanged)

    def _get_fastfetch_config_image_path(self) -> str:
        """Return the clean file path (no file:// prefix, no cache-buster query)."""
        p = self._fastfetch_config_image or ""
        p = p.replace("file://", "")
        q = p.find("?")
        if q != -1:
            p = p[:q]
        return p

    def _emit_fastfetch_config_image_path(self) -> None:
        self.fastfetchConfigImagePathChanged.emit()

    fastfetchConfigImagePath = Property(str, _get_fastfetch_config_image_path, notify=fastfetchConfigImagePathChanged)

    def _get_fastfetch_backup_exists(self) -> bool:
        cfg = fastfetch_config_path()
        bak = cfg.with_name(cfg.name + ".bak")
        return bak.exists() and bak.is_file()

    hasFastfetchBackup = Property(bool, _get_fastfetch_backup_exists, notify=fastfetchBackupExistsChanged)

    def _get_fastfetch_draft_color(self) -> str:
        return self._fastfetch_draft_color

    def _set_fastfetch_draft_color(self, color: str) -> None:
        # Normalize incoming color to a consistent #AARRGGBB when possible.
        val = color or ""
        norm: str = val
        try:
            if val and val.lower() != "transparent" and QColor.isValidColor(val):
                qc = QColor(val)
                try:
                    norm = qc.name(QColor.HexArgb)
                except TypeError:
                    # Fallback construction: #AARRGGBB
                    norm = "#{:02x}{:02x}{:02x}{:02x}".format(qc.alpha(), qc.red(), qc.green(), qc.blue())
        except Exception:
            self._logger.debug("Failed normalizing color %r", val)

        if self._fastfetch_draft_color != norm:
            self._fastfetch_draft_color = norm
            self.fastfetchDraftColorChanged.emit()

    fastfetchDraftColor = Property(str, _get_fastfetch_draft_color, _set_fastfetch_draft_color, notify=fastfetchDraftColorChanged)

    @Slot(result=bool)
    def fastfetchTintedExists(self) -> bool:
        """Check if a tinted image already exists next to the selected file."""
        try:
            if not self._selected_file:
                return False
            src_path = self._selected_file.replace("file://", "") if self._selected_file.startswith("file://") else self._selected_file
            tinted_path = self._get_tinted_path(src_path)
            return tinted_path.exists()
        except Exception:
            return False

    def _get_tinted_path(self, src: str) -> Path:
        """Calculate the tinted image path next to the source image.
        
        Always uses .png extension since tint_image always outputs PNG.
        """
        src_path = Path(src.replace("file://", "") if src.startswith("file://") else src)
        stem = src_path.stem
        return src_path.with_name(f"{stem}-tinted.png")

    @Slot(str, str, result=str)
    def generateTintedPreview(self, src: str, tint_hex: str, strength: float = 0.8) -> str:
        """Generate a tinted preview in a background thread."""
        if src.startswith("file://"):
            src_path = src.replace("file://", "")
        else:
            src_path = src

        if not self._is_valid_tint(tint_hex):
            self._clear_tinted_preview()
            return ""

        try:
            self._fastfetch_tinting = True
            self.fastfetchTintingChanged.emit()
            
            thr = threading.Thread(
                target=self._tint_image_task, 
                args=(src_path, tint_hex, float(strength)), 
                daemon=True
            )
            thr.start()
            self._tint_thread = thr
            return ""
        except Exception:
            self._logger.exception("Failed starting background tint thread for %s", src)
            return ""

    def _is_valid_tint(self, tint_hex: str) -> bool:
        try:
            if not tint_hex or str(tint_hex).lower() == "transparent":
                return False
            return QColor.isValidColor(tint_hex)
        except Exception:
            self._logger.debug("Validation failed for color %r", tint_hex)
            return False

    def _clear_tinted_preview(self) -> None:
        self._fastfetch_tinted_preview = ""
        self.fastfetchTintedPreviewChanged.emit()

    def _tint_image_task(self, src: str, tint_hex: str, strength: float) -> None:
        """Background task for tinting."""
        try:
            res = color_utils.tint_image(src, tint_hex, strength)
            self.tintResult.emit(res if res else "")
        except Exception:
            self._logger.exception("Background tint failed for %s", src)
            self.tintResult.emit("")

    @Slot()
    def _on_tint_done(self, dst: str) -> None:
        """Handle tint completion."""
        try:
            self._fastfetch_tinted_preview = ("file://" + str(Path(dst))) if dst else ""
            self.fastfetchTintedPreviewChanged.emit()
        finally:
            self._fastfetch_tinting = False
            self.fastfetchTintingChanged.emit()
            self._tint_thread = None

    @Slot()
    def refreshFastfetchConfigImage(self) -> None:
        """Re-detect the current fastfetch config image from disk.
        
        Forces re-read and emits change signal with a cache-buster to ensure
        QML Image reloads even if the file path is the same but content changed.
        """
        try:
            import time
            detected = self._detect_current_fastfetch_image()
            if detected:
                # Append cache-buster to force QML Image reload
                url = f"file://{detected}?t={int(time.time() * 1000)}"
                self._fastfetch_config_image = url
                self.fastfetchConfigImageChanged.emit()
                self._emit_fastfetch_config_image_path()
            else:
                if self._fastfetch_config_image != "":
                    self._fastfetch_config_image = ""
                    self.fastfetchConfigImageChanged.emit()
                    self._emit_fastfetch_config_image_path()
        except Exception:
            self._logger.exception("Failed refreshing fastfetch config image")

    @Slot(result="QVariantMap")
    def getFastfetchInfo(self) -> dict[str, str]:
        """Return info for QML."""
        try:
            config_image = self._detect_current_fastfetch_image()
            # Also update property if it differs (sync state)
            if config_image:
                 url = "file://" + config_image
                 if self._fastfetch_config_image != url:
                     self._fastfetch_config_image = url
                     self.fastfetchConfigImageChanged.emit()

            return {
                "config_image": config_image,
                "config_path": ""
            }
        except Exception:
            self._logger.exception("Failed reading fastfetch info")
            return {
                "config_image": "",
                "config_path": ""
            }

    def _detect_current_fastfetch_image(self) -> str:
        try:
            config_image = ""
            for key in ("config_image", "image", "source", "logo", "icon"):
                val, _ = file_utils.read_config_fastfetch(key, None)
                if val:
                    p = Path(str(val)).expanduser()
                    if p.exists():
                        config_image = str(p)
                        break
            
            if not config_image:
                fallback = Path.home() / ".config" / "fastfetch" / "chica-tinted.png"
                if fallback.exists():
                    config_image = str(fallback)
            return config_image
        except Exception:
            self._logger.warning("Error detecting fastfetch image")
            return ""

    @Slot(result=bool)
    def applyTintedImage(self) -> bool:
        """Apply the tinted image: save it next to the original and update fastfetch config."""
        if not self._selected_file:
            self._show_result_dialog("No image selected.")
            return False

        src = self._selected_file.replace("file://", "") if self._selected_file.startswith("file://") else self._selected_file

        thr = threading.Thread(
            target=self._apply_tint_task,
            args=(src,),
            daemon=True
        )
        thr.start()
        self._apply_thread = thr
        return True

    def _apply_tint_task(self, src: str) -> None:
        """Generate tinted image next to the original and update fastfetch config."""
        try:
            src_path = Path(src)
            tinted_path = self._get_tinted_path(src)

            # Tint the image and save next to the original
            tint_hex = self._fastfetch_draft_color
            if not self._is_valid_tint(tint_hex):
                msg = "No valid tint color selected."
                self.fastfetchApplyResult.emit(False, msg)
                self._show_result_dialog(msg)
                return

            dst_str = color_utils.tint_image(str(src_path), tint_hex, 0.8)
            if not dst_str:
                msg = "Failed to generate tinted image."
                self.fastfetchApplyResult.emit(False, msg)
                self._show_result_dialog(msg)
                return

            # The tint_image function returns a temp file; copy it to the final location
            import shutil
            shutil.copy2(dst_str, str(tinted_path))
            # Clean up temp file
            try:
                Path(dst_str).unlink()
            except Exception:
                pass

            # Create backup of fastfetch config before modifying
            self._backup_fastfetch_config()

            # Update fastfetch config with the tinted image path
            ok = file_utils.set_fastfetch_source_inplace(None, str(tinted_path))

            if not ok:
                msg = f"Generated tinted image at {tinted_path} but failed to update fastfetch config."
                self.fastfetchApplyResult.emit(False, msg)
                self._show_result_dialog(msg)
            else:
                self._on_apply_success(str(tinted_path))

        except FileNotFoundError as exc:
            self._logger.error("applyTintedImage task: %s", exc)
            self.fastfetchApplyResult.emit(False, str(exc))
            self._show_result_dialog(str(exc))
        except Exception:
            self._logger.exception("applyTintedImage task failed")
            self.fastfetchApplyResult.emit(False, "Unexpected error.")
            self._show_result_dialog("Unexpected error while applying tinted image.")

    def _backup_fastfetch_config(self) -> None:
        """Create a backup of the fastfetch config before modifying it.

        Uses the XDG config location so it stays consistent with the writer.
        """
        if file_utils.backup_config_file(fastfetch_config_path()) is not None:
            self.fastfetchBackupExistsChanged.emit()

    @Slot(result=bool)
    def applyOriginalImage(self) -> bool:
        """Apply the selected image directly to the fastfetch config, without tinting."""
        if not self._selected_file:
            self._show_result_dialog("No image selected.")
            return False

        src = self._selected_file.replace("file://", "") if self._selected_file.startswith("file://") else self._selected_file

        thr = threading.Thread(
            target=self._apply_original_task,
            args=(src,),
            daemon=True
        )
        thr.start()
        self._apply_thread = thr
        return True

    def _apply_original_task(self, src: str) -> None:
        """Update the fastfetch config to point at the selected image, without tinting."""
        try:
            src_path = Path(src)
            if not src_path.exists() or not src_path.is_file():
                msg = "The selected image no longer exists."
                self.fastfetchApplyResult.emit(False, msg)
                self._show_result_dialog(msg)
                return

            # Create backup of fastfetch config before modifying
            self._backup_fastfetch_config()

            # Update fastfetch config with the original image path
            ok = file_utils.set_fastfetch_source_inplace(None, str(src_path))

            if not ok:
                msg = "Failed to update fastfetch config with the selected image."
                self.fastfetchApplyResult.emit(False, msg)
                self._show_result_dialog(msg)
            else:
                self._on_apply_success(str(src_path))

        except FileNotFoundError as exc:
            self._logger.error("applyOriginalImage task: %s", exc)
            self.fastfetchApplyResult.emit(False, str(exc))
            self._show_result_dialog(str(exc))
        except Exception:
            self._logger.exception("applyOriginalImage task failed")
            self.fastfetchApplyResult.emit(False, "Unexpected error.")
            self._show_result_dialog("Unexpected error while applying the image.")

    def _on_apply_success(self, dst_path: str) -> None:
        """Handle successful apply."""
        self.fastfetchTintedPreviewChanged.emit()

        try:
            file_utils.clear_fastfetch_cache()
        except Exception:
            self._logger.warning("Failed clearing fastfetch cache")

        msg = f"Applied image to {dst_path}"
        self._set_fastfetch_config_image("file://" + dst_path)
        self.fastfetchBackupExistsChanged.emit()
        self.fastfetchApplyResult.emit(True, msg)
        self._show_result_dialog(msg)

    @Slot(result="QVariantMap")
    def restoreFastfetchBackup(self) -> dict[str, Any]:
        """Restore the fixed fastfetch config backup."""
        try:
            ok = file_utils.restore_fastfetch_config_backup(None)
            if ok:
                try:
                    file_utils.clear_fastfetch_cache()
                except Exception:
                    pass
                
                msg = "Restored fastfetch config from backup"
                self._show_result_dialog(msg)
                
                # Update info
                try:
                    info = self.getFastfetchInfo()
                    if info and info.get("config_image"):
                        self._set_fastfetch_config_image("file://" + str(info.get("config_image")))
                    else:
                        self._set_fastfetch_config_image("")
                except Exception:
                    pass

                self.fastfetchBackupExistsChanged.emit()
                self.fastfetchApplyResult.emit(True, msg)
                return {"success": True, "message": msg}
            else:
                msg = "No backup found to restore"
                self._show_result_dialog(msg)
                self.fastfetchApplyResult.emit(False, msg)
                return {"success": False, "message": msg}
        except Exception:
            self._logger.exception("Failed restoring fastfetch backup")
            return {"success": False, "message": "Unexpected error"}

    @Slot()
    def stopTintWorker(self) -> None:
        """Stop any running tint worker."""
        self._stop_bg_thread(self._tint_thread)
        self._fastfetch_tinting = False
        self.fastfetchTintingChanged.emit()
