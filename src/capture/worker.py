"""Background screen-capture worker.

Architecture
------------
CaptureWorker is a QObject that is moved to a dedicated QThread by the
application. It must NOT be subclassed from QThread — the QObject-on-QThread
pattern is used so that signals are delivered on the correct thread and the
worker's slot (run) is invoked via the thread's event loop.

Lifecycle
---------
    CREATED  →  (thread.start() + run_capture slot called)
    RUNNING  →  (stop() called or error)
    STOPPED  →  (capture_stopped signal emitted)

The worker uses a threading.Event for the stop signal so that the capture
interval sleep is interruptible without a busy loop. MSS is initialised once
per run() call and torn down cleanly on exit.

Latest-frame policy
-------------------
The worker maintains a single _latest_frame slot protected by a threading.Lock.
Each new frame atomically replaces the previous one. If downstream processing
falls behind, only the newest frame is retained — stale frames are discarded.
Memory usage is bounded to approximately one frame buffer at all times.

Privacy
-------
Raw pixel data is never logged, persisted, or transmitted. Only fixed event
names are written to the logger.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from enum import Enum, auto

import mss as _mss_module  # type: ignore[import-untyped]

from PySide6.QtCore import QObject, Signal, Slot

from src.app.config import AppConfig
from src.app.logging_config import LOGGER_NAME
from src.capture.frame import CaptureFrame
from src.capture.region import CaptureRegion


class WorkerState(Enum):
    """Deterministic lifecycle states for CaptureWorker."""

    CREATED = auto()
    RUNNING = auto()
    STOPPED = auto()


class CaptureWorker(QObject):
    """Screen-capture worker that runs on a dedicated QThread.

    Signals:
            capture_error(str):         Emitted when a non-fatal capture error
                                        occurs. The string is a fixed event name,
                                        never screen content.
        capture_started():          Emitted once when the capture loop begins.
        capture_stopped():          Emitted once when the capture loop exits.

    Usage::

        worker = CaptureWorker(config)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run_capture)
        worker.capture_stopped.connect(thread.quit)
        thread.start()
        # ... later ...
        worker.stop()
        thread.quit()
        thread.wait()
    """

    capture_error = Signal(str)    # fixed event name only
    capture_started = Signal()
    capture_stopped = Signal()

    def __init__(self, config: AppConfig, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._logger = logging.getLogger(LOGGER_NAME)
        self._stop_event = threading.Event()
        self._frame_lock = threading.Lock()
        self._latest_frame: CaptureFrame | None = None
        self._state = WorkerState.CREATED

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def state(self) -> WorkerState:
        """Current lifecycle state (thread-safe read)."""
        return self._state

    def stop(self) -> None:
        """Signal the capture loop to exit at the next interval boundary.

        Safe to call from any thread. Returns immediately; the loop exits
        asynchronously and emits capture_stopped when done.
        """
        self._stop_event.set()

    def take_latest_frame(self) -> CaptureFrame | None:
        """Atomically retrieve and clear the latest captured frame.

        Returns None if no frame has been captured since the last call.
        This implements the latest-frame replacement policy: the caller
        receives the newest available frame and the slot is cleared.
        """
        with self._frame_lock:
            frame = self._latest_frame
            self._latest_frame = None
            return frame

    # ------------------------------------------------------------------
    # Capture loop (runs on the worker thread)
    # ------------------------------------------------------------------

    @Slot()
    def run_capture(self) -> None:
        """Main capture loop — called by QThread.started signal.

        Initialises MSS once, then captures frames at the configured interval
        until stop() is called. Uses threading.Event.wait() for the interval
        so that stop() interrupts the sleep immediately.

        The monitor index is fixed to 1 (primary monitor) for Phase 2.
        Region capture and multi-monitor support are available via the
        CaptureRegion API; the worker captures the full primary monitor
        by default.
        """
        self._state = WorkerState.RUNNING
        self._stop_event.clear()
        interval = self._config.screen.capture_interval

        self._logger.info("capture_starting")
        self.capture_started.emit()

        try:
            with _mss_module.mss() as screen_capture:
                # Validate that at least one monitor is available.
                if len(screen_capture.monitors) < 2:
                    self._logger.error("capture_no_monitors")
                    self.capture_error.emit("capture_no_monitors")
                    return

                # Use monitor index 1 (primary monitor) for Phase 2.
                monitor_index = 1
                monitor_dict = screen_capture.monitors[monitor_index]

                region = CaptureRegion(
                    x=monitor_dict["left"],
                    y=monitor_dict["top"],
                    width=monitor_dict["width"],
                    height=monitor_dict["height"],
                )

                while not self._stop_event.is_set():
                    try:
                        frame = self._capture_one(
                            screen_capture,
                            monitor_dict,
                            monitor_index,
                            region,
                        )
                        # Latest-frame replacement: overwrite any unconsumed frame.
                        with self._frame_lock:
                            self._latest_frame = frame

                    except Exception:
                        self._logger.error("capture_frame_failed", exc_info=True)
                        self.capture_error.emit("capture_frame_failed")
                        # Continue the loop — one bad frame does not stop capture.

                    # Interruptible sleep: exits immediately when stop() is called.
                    self._stop_event.wait(timeout=interval)

        except Exception:
            self._logger.error("capture_worker_failed", exc_info=True)
            self.capture_error.emit("capture_worker_failed")

        finally:
            self._state = WorkerState.STOPPED
            self._logger.info("capture_stopped")
            self.capture_stopped.emit()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _capture_one(
        self,
        screen_capture: object,
        monitor_dict: dict,
        monitor_index: int,
        region: CaptureRegion,
    ) -> CaptureFrame:
        """Capture a single frame and return a CaptureFrame.

        The MSS screenshot object's raw bytes are copied into a plain bytes
        object so that the MSS internal buffer can be reused safely.
        """
        screenshot = screen_capture.grab(monitor_dict)  # type: ignore[attr-defined]
        timestamp = datetime.now(tz=timezone.utc)

        # Copy raw bytes to decouple from MSS internal buffer.
        raw: bytes = bytes(screenshot.raw)

        return CaptureFrame(
            timestamp=timestamp,
            monitor_index=monitor_index,
            region=region,
            width=screenshot.width,
            height=screenshot.height,
            raw=raw,
        )
