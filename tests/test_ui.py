"""Offscreen Qt smoke tests; no capture, AI, or network access."""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from src.app.config import AppConfig, GhostConfig
from src.ui.main_window import MainWindow, SettingsDialog, STYLESHEET


class UserInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        instance = QApplication.instance()
        cls.application = (
            instance if instance is not None else QApplication([])
        )
        cls.application.setStyleSheet(STYLESHEET)
        cls.application.setQuitOnLastWindowClosed(False)

    def setUp(self) -> None:
        self.window = MainWindow(AppConfig(), Path("test-config.yaml"))

    def tearDown(self) -> None:
        self.window.close()
        self.window.deleteLater()
        self.application.processEvents()

    def test_initial_status_is_honest(self) -> None:
        self.assertEqual(self.window.ghost_status.text(), "OFF")
        self.assertEqual(self.window.ai_status.text(), "OFFLINE")
        self.assertEqual(self.window.screen_status.text(), "READY")
        self.assertIn("Capture inactive", self.window.statusBar().currentMessage())

    def test_unavailable_controls_explain_without_activating(self) -> None:
        with patch(
            "src.ui.main_window.QMessageBox.information"
        ) as information:
            self.window.analyze_button.click()
            self.window.ghost_button.click()

        self.assertEqual(information.call_count, 2)
        self.assertEqual(self.window.ghost_status.text(), "OFF")
        self.assertEqual(self.window.ai_status.text(), "OFFLINE")

    def test_settings_are_actual_configuration_and_read_only(self) -> None:
        dialog = SettingsDialog(
            AppConfig(),
            Path("test-config.yaml"),
            self.window,
        )
        try:
            self.assertTrue(dialog.config_view.isReadOnly())
            self.assertTrue(dialog.path_view.isReadOnly())
            self.assertIn("provider: ollama", dialog.config_view.toPlainText())
            self.assertIn(
                "save_screenshots: false",
                dialog.config_view.toPlainText(),
            )
        finally:
            dialog.close()
            dialog.deleteLater()

    def test_future_preference_does_not_fake_running_ghost_mode(self) -> None:
        other_window = MainWindow(
            AppConfig(ghost=GhostConfig(enabled=True)),
            Path("test-config.yaml"),
        )
        try:
            self.assertEqual(other_window.ghost_status.text(), "OFF")
        finally:
            other_window.close()
            other_window.deleteLater()

    def test_window_can_be_shown_and_closed(self) -> None:
        self.window.show()
        self.application.processEvents()
        self.assertTrue(self.window.isVisible())
        self.window.close()
        self.assertFalse(self.window.isVisible())


if __name__ == "__main__":
    unittest.main()
