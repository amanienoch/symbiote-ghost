"""Desktop shell, read-only configuration viewer, and capture status slots."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src import __version__
from src.app.config import AppConfig, config_to_yaml
from src.app.logging_config import LOGGER_NAME


STYLESHEET = """
QMainWindow, QDialog {
    background-color: #0a101a;
}
QWidget {
    color: #e6edf7;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QLabel#Brand {
    color: #6ef5ce;
    font-size: 30pt;
    font-weight: 700;
}
QLabel#Subtitle, QLabel#Muted {
    color: #99abc2;
}
QLabel#SectionTitle {
    color: #e6edf7;
    font-size: 15pt;
    font-weight: 600;
}
QLabel#CardTitle {
    color: #91a5be;
    font-size: 9pt;
    font-weight: 600;
}
QLabel#StatusValue {
    color: #6ef5ce;
    font-size: 19pt;
    font-weight: 700;
}
QFrame#Panel, QFrame#StatusCard {
    background-color: #111d2c;
    border: 1px solid #26394f;
    border-radius: 12px;
}
QPushButton {
    background-color: #182b3e;
    border: 1px solid #35516c;
    border-radius: 8px;
    padding: 11px 18px;
    font-weight: 600;
    min-height: 22px;
}
QPushButton:hover {
    background-color: #223c53;
    border-color: #6ef5ce;
}
QPushButton:pressed {
    background-color: #102031;
}
QPushButton:focus {
    border: 2px solid #6ef5ce;
}
QPushButton#PrimaryButton {
    background-color: #6ef5ce;
    border-color: #6ef5ce;
    color: #071810;
}
QPushButton#PrimaryButton:hover {
    background-color: #9affdf;
}
QPlainTextEdit {
    background-color: #0d1623;
    color: #dce7f5;
    border: 1px solid #31465e;
    border-radius: 6px;
    padding: 10px;
    selection-background-color: #31576c;
}
QStatusBar {
    color: #91a5be;
    background-color: #0d1623;
}
"""


def make_label(
    text: str,
    object_name: str = "",
    *,
    word_wrap: bool = False,
) -> QLabel:
    label = QLabel(text)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setObjectName(object_name)
    label.setWordWrap(word_wrap)
    return label


class SettingsDialog(QDialog):
    """Show effective settings without pretending editing is implemented."""

    def __init__(
        self,
        config: AppConfig,
        config_path: Path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("SYMBIOTE GHOST — Settings")
        self.resize(660, 620)
        self.setMinimumSize(500, 420)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.addWidget(make_label("Effective configuration", "SectionTitle"))
        layout.addWidget(
            make_label(
                "Read-only in Phase 1. Close the application, edit the "
                "configuration file, and restart to reload it. Omitted "
                "settings are shown with their defaults.",
                "Muted",
                word_wrap=True,
            )
        )

        self.path_view = QPlainTextEdit()
        self.path_view.setReadOnly(True)
        self.path_view.setMaximumHeight(70)
        self.path_view.setPlainText(str(config_path))
        self.path_view.setAccessibleName("Configuration file path")
        layout.addWidget(self.path_view)

        self.config_view = QPlainTextEdit()
        self.config_view.setReadOnly(True)
        self.config_view.setPlainText(config_to_yaml(config))
        self.config_view.setAccessibleName("Effective configuration YAML")
        layout.addWidget(self.config_view, 1)

        layout.addWidget(
            make_label(
                "These are preferences, not live subsystem status. "
                "Capture, OCR, AI, Ghost Mode, and voice remain inactive "
                "in this phase, regardless of their configured values.",
                "Muted",
                word_wrap=True,
            )
        )

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class MainWindow(QMainWindow):
    """A functional shell with explicit boundaries for future features."""

    def __init__(self, config: AppConfig, config_path: Path) -> None:
        super().__init__()
        self.config = config
        self.config_path = config_path
        self.logger = logging.getLogger(LOGGER_NAME)

        self.setWindowTitle(f"SYMBIOTE GHOST — Foundation {__version__}")
        self.resize(1000, 700)
        self.setMinimumSize(800, 620)

        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(22)

        layout.addWidget(make_label("SYMBIOTE", "Brand"))
        layout.addWidget(
            make_label(
                "GHOST  /  LOCAL-FIRST SCREEN ASSISTANT",
                "Subtitle",
            )
        )

        status_row = QHBoxLayout()
        status_row.setSpacing(14)
        ghost_card, self.ghost_status = self._status_card("GHOST MODE", "OFF")
        ai_card, self.ai_status = self._status_card("AI", "OFFLINE")
        screen_card, self.screen_status = self._status_card("SCREEN", "READY")
        self.change_detection_active = False
        status_row.addWidget(ghost_card)
        status_row.addWidget(ai_card)
        status_row.addWidget(screen_card)
        layout.addLayout(status_row)

        layout.addWidget(
            make_label(
                "SCREEN: READY means the shell is ready for the future "
                "capture module. Capture becomes ACTIVE when screen capture "
                "starts successfully. Screen analysis and AI are not "
                "available in the current phase.",
                "Muted",
                word_wrap=True,
            )
        )

        panel = QFrame()
        panel.setObjectName("Panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(24, 24, 24, 24)
        panel_layout.setSpacing(16)
        panel_layout.addWidget(make_label("Capture foundation online", "SectionTitle"))
        panel_layout.addWidget(
            make_label(
                "The desktop shell, configuration loader, local event "
                "logging, screen capture, and change detection are available.",
                word_wrap=True,
            )
        )
        panel_layout.addWidget(
            make_label(
                "OCR, AI explanations, and background assistance belong to "
                "later phases. The controls below explain their current "
                "availability.",
                "Muted",
                word_wrap=True,
            )
        )

        button_row = QHBoxLayout()
        button_row.setSpacing(12)
        self.analyze_button = QPushButton("Analyze Screen")
        self.analyze_button.setObjectName("PrimaryButton")
        self.analyze_button.setToolTip("Screen analysis is not available yet")
        self.ghost_button = QPushButton("Ghost Mode")
        self.ghost_button.setToolTip("Not available until Phase 8")
        self.settings_button = QPushButton("Settings")

        self.analyze_button.clicked.connect(self._show_analysis_unavailable)
        self.ghost_button.clicked.connect(self._show_ghost_unavailable)
        self.settings_button.clicked.connect(self._show_settings)

        button_row.addWidget(self.analyze_button)
        button_row.addWidget(self.ghost_button)
        button_row.addWidget(self.settings_button)
        panel_layout.addLayout(button_row)
        layout.addWidget(panel)

        layout.addStretch(1)
        layout.addWidget(
            make_label(
                "LOCAL BY DEFAULT\n"
                "No cloud AI • No telemetry • No screen recording\n"
                "No screenshot storage • No autonomous computer control",
                "Muted",
                word_wrap=True,
            )
        )
        self.statusBar().showMessage(
            "PHASE 2/3  |  Capture inactive  |  AI inactive  |  Close window to exit"
        )

    @staticmethod
    def _status_card(title: str, value: str) -> tuple[QFrame, QLabel]:
        card = QFrame()
        card.setObjectName("StatusCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.addWidget(make_label(title, "CardTitle"))
        value_label = make_label(value, "StatusValue")
        value_label.setAccessibleName(f"{title}: {value}")
        layout.addWidget(value_label)
        return card, value_label

    def _show_analysis_unavailable(self) -> None:
        self.logger.info("analysis_unavailable")
        capture_state = {
            "ACTIVE": "ACTIVE",
            "ERROR": "ERROR",
        }.get(self.screen_status.text(), "INACTIVE")
        detection_state = (
            "ACTIVE" if self.change_detection_active else "INACTIVE"
        )
        QMessageBox.information(
            self,
            "Screen analysis is not available yet",
            f"Capture: {capture_state}\n"
            f"Change detection: {detection_state}\n"
            "Latest change details: not surfaced in this view.\n\n"
            "Screen capture and change detection are available in Phases 2 "
            "and 3, but this control does not produce an analysis result.\n\n"
            "OCR and AI explanations require later phases. No screen "
            "content is displayed or sent to a cloud service.",
        )

    def _show_ghost_unavailable(self) -> None:
        self.logger.info("ghost_unavailable")
        QMessageBox.information(
            self,
            "Ghost Mode is not available yet",
            "The background pipeline is introduced in Phase 8.\n\n"
            "Ghost Mode remains OFF. No background capture, OCR, "
            "or inference was started.",
        )

    def _show_settings(self) -> None:
        self.logger.info("settings_opened")
        dialog = SettingsDialog(self.config, self.config_path, self)
        try:
            dialog.exec()
        finally:
            dialog.deleteLater()

    # ------------------------------------------------------------------
    # Phase 2 capture state slots
    # These slots are connected by application.py after the window is
    # created. The initial state (READY / "Capture inactive") is set in
    # __init__ and is not changed until the worker emits its first signal.
    # ------------------------------------------------------------------

    @Slot()
    def slot_capture_started(self) -> None:
        """Update the SCREEN status card when capture begins."""
        self.change_detection_active = True
        self.screen_status.setText("ACTIVE")
        self.screen_status.setAccessibleName("SCREEN: ACTIVE")
        self.statusBar().showMessage(
            "PHASE 2  |  Capture active  |  AI inactive  |  Close window to exit"
        )

    @Slot()
    def slot_capture_stopped(self) -> None:
        """Restore the SCREEN status card when capture stops."""
        self.change_detection_active = False
        self.screen_status.setText("READY")
        self.screen_status.setAccessibleName("SCREEN: READY")
        self.statusBar().showMessage(
            "PHASE 2  |  Capture inactive  |  AI inactive  |  Close window to exit"
        )

    @Slot(str)
    def slot_capture_error(self, event_name: str) -> None:
        """Update the SCREEN status card on a capture error.

        The event_name is a fixed log event string — never screen content.
        """
        self.change_detection_active = False
        self.screen_status.setText("ERROR")
        self.screen_status.setAccessibleName("SCREEN: ERROR")
        self.statusBar().showMessage(
            "PHASE 2  |  Capture error  |  AI inactive  |  Close window to exit"
        )
