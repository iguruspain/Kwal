"""Settings app model: the list of app tabs shown in the UI."""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import (
    QAbstractListModel,
    QModelIndex,
    QObject,
    Qt,
    Signal,
    Slot,
)

from .common import SettingsApp

# Logger
logger = logging.getLogger(__name__)


class SettingsAppModel(QAbstractListModel):
    TitleRole = Qt.UserRole + 1
    SectionRole = Qt.UserRole + 2
    PageRole = Qt.UserRole + 3
    AppNameRole = Qt.UserRole + 4

    def __init__(self, apps: list[SettingsApp] | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._apps: list[SettingsApp] = apps or []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._apps)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < self.rowCount()):
            return None
        app = self._apps[index.row()]
        if role == SettingsAppModel.AppNameRole:
            return app.app_name
        if role == SettingsAppModel.TitleRole:
            return app.title
        if role == SettingsAppModel.SectionRole:
            return app.section
        if role == SettingsAppModel.PageRole:
            return app.qml_page
        return None

    def roleNames(self) -> dict[int, bytes]:
        return {
            SettingsAppModel.AppNameRole: b"app_name",
            SettingsAppModel.TitleRole: b"title",
            SettingsAppModel.SectionRole: b"section",
            SettingsAppModel.PageRole: b"qmlpage",
        }

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        default_flags = super().flags(index)  # type: ignore
        if index.isValid():
            return default_flags | Qt.ItemIsDragEnabled
        return default_flags

    @Slot(int, result="QVariantMap")
    def get(self, row: int) -> dict[str, str]:
        if 0 <= row < self.rowCount():
            app = self._apps[row]
            return {
                "app_name": app.app_name,
                "title": app.title,
                "section": app.section,
                "qmlpage": app.qml_page
            }
        return {}

    def resetApps(self, apps: list[SettingsApp]) -> None:
        """Replace the app list using incremental row operations.

        Avoids beginResetModel/endResetModel which triggers a null-item
        access bug in the KDE Desktop style TabBar implementation.
        """
        old_count = len(self._apps)
        if old_count > 0:
            self.beginRemoveRows(QModelIndex(), 0, old_count - 1)
            self._apps = []
            self.endRemoveRows()
        if apps:
            self.beginInsertRows(QModelIndex(), 0, len(apps) - 1)
            self._apps = apps
            self.endInsertRows()

    @Slot(int, int, int)
    def move(self, source: int, destination: int, count: int = 1) -> None:
        if source == destination:
            return

        qt_dest = destination + 1 if source < destination else destination

        if self.beginMoveRows(QModelIndex(), source, source, QModelIndex(), qt_dest):
            item = self._apps.pop(source)
            self._apps.insert(destination, item)
            self.endMoveRows()
