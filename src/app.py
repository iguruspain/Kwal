#!/usr/bin/env python3

import os
import sys
import signal
import logging
from typing import Optional
import argparse
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import qInstallMessageHandler, QtMsgType
from .controllers.controller import Controller


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="kwal", description="Kwal Kirigami application")
    parser.add_argument(
        "--log-level",
        "-l",
        dest="log_level",
        help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Can also be set via LOG_LEVEL env var.",
        default=None,
    )
    return parser.parse_args(argv)

def main():
    """Initializes and manages the application execution

    Refactored to initialize logging, controller and expose the model
    to QML via context properties.
    """
    args = _parse_args()

    # Determine log level: CLI arg > env var > INFO
    level_name = args.log_level or os.environ.get("LOG_LEVEL") or "INFO"
    try:
        level = getattr(logging, level_name.upper())
    except Exception:
        level = logging.INFO
    logging.basicConfig(level=level)
    logger = logging.getLogger(__name__)
    logger.debug("Log level set to %s", logging.getLevelName(level))

    # Use QApplication because we use Qt Widgets (QFileDialog) in controller
    app = QApplication(sys.argv)
    app.setApplicationName("kwal")
    app.setApplicationDisplayName("Kwal")
    app.setOrganizationName("Kwal")
    app.setDesktopFileName("org.kde.kwal")
    engine = QQmlApplicationEngine()

    # Needed to close the app with Ctrl+C
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Needed to get proper KDE style outside of Plasma
    if not os.environ.get("QT_QUICK_CONTROLS_STYLE"):
        os.environ["QT_QUICK_CONTROLS_STYLE"] = "org.kde.desktop"

    # Create controller and expose to QML
    controller = Controller()
    engine.rootContext().setContextProperty("pyController", controller)
    engine.rootContext().setContextProperty("wallpaperFolderModel", controller.wallpaperModel())
    engine.rootContext().setContextProperty("imageModel", controller.imageModel())

    # Route Qt/QML messages into Python logging and respect application log level.
    def _qt_message_handler(msg_type: QtMsgType, context, message: str) -> None:
        # Map Qt message types to Python logging levels
        mapping = {
            QtMsgType.QtDebugMsg: logging.DEBUG,
            QtMsgType.QtInfoMsg: logging.INFO,
            QtMsgType.QtWarningMsg: logging.WARNING,
            QtMsgType.QtCriticalMsg: logging.ERROR,
            QtMsgType.QtFatalMsg: logging.CRITICAL,
        }
        lvl = mapping.get(msg_type, logging.INFO)
        qt_logger = logging.getLogger("qt")
        # include context info when available
        try:
            ctx_info = f"{context.file}:{context.line}"
        except Exception:
            ctx_info = ""
        qt_logger.log(lvl, "%s %s", message, ctx_info)

    qInstallMessageHandler(_qt_message_handler)
    # Ensure qt logger follows configured level so messages can be hidden like regular logging
    logging.getLogger("qt").setLevel(level)

    base_path = os.path.abspath(os.path.dirname(__file__))
    url = QUrl(f"file://{base_path}/qml/main.qml")
    logger.info("Loading QML: %s", url.toString())
    engine.load(url)

    if len(engine.rootObjects()) == 0:
        logger.error("No root objects loaded, exiting")
        sys.exit(1)

    return app.exec()


if __name__ == "__main__":
    main()