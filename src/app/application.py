"""Qt application ownership, exception reporting, and orderly shutdown."""

from __future__ import annotations

import logging
import sys
import threading
from pathlib import Path
from types import TracebackType

from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal, Slot
from PySide6.QtWidgets import QApplication, QMessageBox

from src import __version__
from src.app.config import ConfigError, load_config, runtime_directory
from src.app.logging_config import close_logging, configure_logging
from src.capture.worker import CaptureWorker
from src.ui.main_window import MainWindow, STYLESHEET
from src.vision.detector import ChangeDetector


def show_error(title: str, message: str) -> None:
    """Use plain text so configuration-related text cannot become HTML."""
    dialog = QMessageBox()
    dialog.setIcon(QMessageBox.Icon.Critical)
    dialog.setWindowTitle(title)
    dialog.setTextFormat(Qt.TextFormat.PlainText)
    dialog.setText(message)
    dialog.exec()


class ExceptionBridge(QObject):
    """Forward uncaught Python exceptions to the Qt main thread."""

    fatal_error = Signal()

    def __init__(
        self,
        application: QApplication,
        logger: logging.Logger,
    ) -> None:
        super().__init__(application)
        self.application = application
        self.logger = logger
        self.failed = False
        self._reporting = False
        self._previous_system_hook = sys.excepthook
        self._previous_thread_hook = threading.excepthook
        self.fatal_error.connect(
            self._report_fatal_error,
            Qt.ConnectionType.QueuedConnection,
        )

    def install(self) -> None:
        sys.excepthook = self._system_exception
        threading.excepthook = self._thread_exception

    def restore(self) -> None:
        sys.excepthook = self._previous_system_hook
        threading.excepthook = self._previous_thread_hook

    def _system_exception(
        self,
        exception_type: type[BaseException],
        exception: BaseException,
        traceback: TracebackType | None,
    ) -> None:
        self.logger.critical(
            "unhandled_exception",
            exc_info=(exception_type, exception, traceback),
        )
        self.fatal_error.emit()

    def _thread_exception(self, arguments: threading.ExceptHookArgs) -> None:
        self._system_exception(
            arguments.exc_type,
            arguments.exc_value,
            arguments.exc_traceback,
        )

    @Slot()
    def _report_fatal_error(self) -> None:
        self.failed = True
        if self._reporting:
            return

        self._reporting = True
        show_error(
            "SYMBIOTE GHOST — Unexpected error",
            "An unexpected error occurred. The application will close.\n\n"
            "The local event log records the exception type only. "
            "Exception messages, screen contents, and local variables "
            "are not included.",
        )
        self.application.exit(1)


def run_application(config_path: Path | None = None) -> int:
    """Create one Qt application and own all Phase 1/2/3 resources."""
    application = QApplication([sys.argv[0]])
    application.setApplicationName("SYMBIOTE GHOST")
    application.setApplicationVersion(__version__)
    application.setOrganizationName("SYMBIOTE")
    application.setStyle("Fusion")
    application.setStyleSheet(STYLESHEET)
    application.setQuitOnLastWindowClosed(True)

    logger: logging.Logger | None = None
    bridge: ExceptionBridge | None = None
    window: MainWindow | None = None
    capture_worker: CaptureWorker | None = None
    capture_thread: QThread | None = None
    capture_timer: QTimer | None = None

    try:
        data_directory = runtime_directory()
        logger = configure_logging(data_directory / "logs")
        logger.info("application_starting")

        effective_path = (
            config_path.expanduser().resolve()
            if config_path is not None
            else data_directory / "config.yaml"
        )
        configuration = load_config(
            effective_path,
            create_if_missing=config_path is None,
        )
        logger.info("configuration_loaded")

        bridge = ExceptionBridge(application, logger)
        bridge.install()

        window = MainWindow(configuration, effective_path)

        # --- Phase 2: capture worker on a dedicated thread ---
        capture_worker = CaptureWorker(configuration)
        capture_thread = QThread()
        capture_worker.moveToThread(capture_thread)

        # Connect worker signals to MainWindow slots.
        capture_worker.capture_started.connect(window.slot_capture_started)
        capture_worker.capture_stopped.connect(window.slot_capture_stopped)
        capture_worker.capture_error.connect(window.slot_capture_error)

        # --- Phase 3: bounded latest-frame consumption ---
        detector = ChangeDetector(configuration)

        def _consume_latest_frame() -> None:
            """Process at most the newest frame currently available."""
            if capture_worker is None:
                return
            frame = capture_worker.take_latest_frame()
            if frame is None:
                return
            try:
                result = detector.process(frame)
                if result.changed:
                    logger.info("screen_changed")
            except Exception:
                logger.error("change_detection_failed", exc_info=True)

        capture_timer = QTimer(application)
        capture_timer.setInterval(
            max(1, round(configuration.screen.capture_interval * 1000))
        )
        capture_timer.timeout.connect(_consume_latest_frame)

        # Start the capture thread when the worker's run_capture slot fires.
        capture_thread.started.connect(capture_worker.run_capture)

        # When the worker stops, quit the thread's event loop.
        capture_worker.capture_stopped.connect(capture_thread.quit)

        def _request_shutdown() -> None:
            logger.info("shutdown_requested")
            if capture_worker is not None:
                capture_worker.stop()

        application.aboutToQuit.connect(_request_shutdown)

        window.show()
        logger.info("main_window_shown")

        # Start capture after the window is shown so the UI is responsive.
        capture_thread.start()
        capture_timer.start()

        exit_code = application.exec()
        return 1 if bridge.failed else exit_code

    except ConfigError as exc:
        if logger is not None:
            logger.error("configuration_failed", exc_info=True)
        show_error(
            "SYMBIOTE GHOST — Configuration error",
            f"{exc}\n\n"
            "Correct the configuration and restart. An existing invalid "
            "configuration is not replaced automatically.",
        )
        return 1

    except Exception:
        if logger is not None:
            logger.critical("application_failed", exc_info=True)
        show_error(
            "SYMBIOTE GHOST — Startup error",
            "The application could not start or complete its lifecycle.\n\n"
            "Check that the virtual environment is installed correctly "
            "and that your local application-data directory is writable.",
        )
        return 1

    finally:
        if bridge is not None:
            bridge.restore()

        # Stop capture worker and wait for the thread to finish.
        if capture_timer is not None:
            capture_timer.stop()
        if capture_worker is not None:
            capture_worker.stop()
        if capture_thread is not None and capture_thread.isRunning():
            capture_thread.quit()
            capture_thread.wait(3000)  # Wait up to 3 seconds.

        if window is not None:
            window.close()

        if logger is not None:
            logger.info("application_stopped")
            close_logging(logger)
