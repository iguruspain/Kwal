"""Custom commands CRUD mixin."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Property, Signal, Slot


class CommandsMixin:
    customCommandsChanged = Signal()

    @staticmethod
    def _normalize_custom_commands(raw: list) -> list[dict[str, Any]]:
        """Normalize custom commands to {"command": str, "enabled": bool}."""
        normalized: list[dict[str, Any]] = []
        for item in raw:
            if isinstance(item, str):
                normalized.append({"command": item, "enabled": True})
            elif isinstance(item, dict):
                normalized.append({
                    "command": str(item.get("command", "")),
                    "enabled": bool(item.get("enabled", True)),
                })
        return normalized

    def _get_custom_commands(self) -> list[dict[str, Any]]:
        return self._custom_commands

    def _set_custom_commands(self, cmds: list) -> None:
        normalized = self._normalize_custom_commands(cmds)
        if self._custom_commands != normalized:
            self._custom_commands = normalized
            self._save_config()
            self.customCommandsChanged.emit()

    customCommands = Property("QVariantList", _get_custom_commands, _set_custom_commands, notify=customCommandsChanged)

    @Slot(str)
    def addCustomCommand(self, cmd: str) -> None:
        self._custom_commands.append({"command": cmd, "enabled": True})
        self._save_config()
        self.customCommandsChanged.emit()

    @Slot(int, str)
    def updateCustomCommand(self, index: int, cmd: str) -> None:
        if 0 <= index < len(self._custom_commands):
            self._custom_commands[index]["command"] = cmd
            self._save_config()
            self.customCommandsChanged.emit()

    @Slot(int, bool)
    def setCustomCommandEnabled(self, index: int, enabled: bool) -> None:
        if 0 <= index < len(self._custom_commands):
            self._custom_commands[index]["enabled"] = enabled
            self._save_config()
            self.customCommandsChanged.emit()

    @Slot(int, int)
    def moveCustomCommand(self, from_index: int, to_index: int) -> None:
        if not (0 <= from_index < len(self._custom_commands)):
            return
        if not (0 <= to_index < len(self._custom_commands)):
            return
        if from_index == to_index:
            return
        command = self._custom_commands.pop(from_index)
        self._custom_commands.insert(to_index, command)
        self._save_config()
        self.customCommandsChanged.emit()

    @Slot(int)
    def removeCustomCommand(self, index: int) -> None:
        if 0 <= index < len(self._custom_commands):
            self._custom_commands.pop(index)
            self._save_config()
            self.customCommandsChanged.emit()
