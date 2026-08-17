"""Shared dataclasses used across Kwal models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Folder:
    name: str
    path: str


@dataclass
class SettingsApp:
    app_name: str
    section: str
    qml_page: str
    title: str = ""

    def __post_init__(self) -> None:
        if not self.title:
            self.title = self.app_name.capitalize()
