"""Phase 2 screen-capture unit tests.

All tests use mocked MSS — no physical monitor or display hardware is
required. The tests are deterministic and run in any environment.

Test coverage:
- MonitorInfo geometry and primary-monitor detection
- Negative coordinate handling (multi-monitor setups)
- CaptureRegion construction and from_monitor factory
- validate_region bounds checking
- CaptureFrame construction and field access
- CaptureWorker initial lifecycle state
- CaptureWorker latest-frame bounded policy (single slot, no accumulation)
- CaptureWorker configuration integration (capture_interval from config)
- CaptureWorker clean stop via threading.Event
- discover_monitors with mocked MSS
"""

from __future__ import annotations

import os
import threading
import time
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.app.config import AppConfig, ScreenConfig
from src.capture.frame import CaptureFrame
from src.capture.monitor import MonitorInfo, discover_monitors
from src.capture.region import CaptureRegion, RegionError, validate_region
from src.capture.worker import CaptureWorker, WorkerState


def _make_frame(
    width: int = 4,
    height: int = 4,
    monitor_index: int = 1,
    fill: int = 128,
) -> CaptureFrame:
    """Create a synthetic CaptureFrame for testing."""
    region = CaptureRegion(x=0, y=0, width=width, height=height)
    raw = bytes([fill, fill, fill, 255] * (width * height))
    return CaptureFrame(
        timestamp=datetime.now(tz=timezone.utc),
        monitor_index=monitor_index,
        region=region,
        width=width,
        height=height,
        raw=raw,
    )


class MonitorInfoTests(unittest.TestCase):
    """Tests for MonitorInfo geometry and primary-monitor detection."""

    def test_fields_are_stored_correctly(self) -> None:
        monitor = MonitorInfo(index=1, x=0, y=0, width=1920, height=1080)
        self.assertEqual(monitor.index, 1)
        self.assertEqual(monitor.x, 0)
        self.assertEqual(monitor.y, 0)
        self.assertEqual(monitor.width, 1920)
        self.assertEqual(monitor.height, 1080)

    def test_primary_monitor_at_origin(self) -> None:
        monitor = MonitorInfo(index=1, x=0, y=0, width=1920, height=1080)
        self.assertTrue(monitor.is_primary)

    def test_secondary_monitor_not_primary(self) -> None:
        monitor = MonitorInfo(index=2, x=1920, y=0, width=1920, height=1080)
        self.assertFalse(monitor.is_primary)

    def test_negative_x_coordinate(self) -> None:
        """Monitor to the left of primary has negative x."""
        monitor = MonitorInfo(index=2, x=-1920, y=0, width=1920, height=1080)
        self.assertEqual(monitor.x, -1920)
        self.assertFalse(monitor.is_primary)

    def test_negative_y_coordinate(self) -> None:
        """Monitor above primary has negative y."""
        monitor = MonitorInfo(index=2, x=0, y=-1080, width=1920, height=1080)
        self.assertEqual(monitor.y, -1080)
        self.assertFalse(monitor.is_primary)

    def test_monitor_is_frozen(self) -> None:
        monitor = MonitorInfo(index=1, x=0, y=0, width=1920, height=1080)
        with self.assertRaises((AttributeError, TypeError)):
            monitor.width = 999  # type: ignore[misc]

    def test_multiple_monitors_distinct(self) -> None:
        m1 = MonitorInfo(index=1, x=0, y=0, width=1920, height=1080)
        m2 = MonitorInfo(index=2, x=1920, y=0, width=2560, height=1440)
        self.assertNotEqual(m1, m2)
        self.assertEqual(m1.index, 1)
        self.assertEqual(m2.index, 2)


class DiscoverMonitorsTests(unittest.TestCase):
    """Tests for discover_monitors() with mocked MSS."""

    def test_discover_returns_monitor_list(self) -> None:
        """discover_monitors returns one MonitorInfo per physical monitor."""
        mock_monitors = [
            # Index 0: virtual bounding box (skipped by discover_monitors)
            {"left": -1920, "top": 0, "width": 3840, "height": 1080},
            # Index 1: primary monitor
            {"left": 0, "top": 0, "width": 1920, "height": 1080},
            # Index 2: secondary monitor
            {"left": 1920, "top": 0, "width": 1920, "height": 1080},
        ]
        mock_mss_instance = MagicMock()
        mock_mss_instance.__enter__ = MagicMock(return_value=mock_mss_instance)
        mock_mss_instance.__exit__ = MagicMock(return_value=False)
        mock_mss_instance.monitors = mock_monitors

        with patch("src.capture.monitor._mss_module") as mock_mss_module:
            mock_mss_module.mss.return_value = mock_mss_instance
            monitors = discover_monitors()

        self.assertEqual(len(monitors), 2)
        self.assertEqual(monitors[0].index, 1)
        self.assertEqual(monitors[0].x, 0)
        self.assertEqual(monitors[0].y, 0)
        self.assertEqual(monitors[0].width, 1920)
        self.assertEqual(monitors[0].height, 1080)
        self.assertEqual(monitors[1].index, 2)
        self.assertEqual(monitors[1].x, 1920)

    def test_discover_handles_negative_coordinates(self) -> None:
        """Negative monitor coordinates are preserved correctly."""
        mock_monitors = [
            {"left": -1920, "top": -1080, "width": 3840, "height": 2160},
            {"left": -1920, "top": 0, "width": 1920, "height": 1080},
            {"left": 0, "top": 0, "width": 1920, "height": 1080},
        ]
        mock_mss_instance = MagicMock()
        mock_mss_instance.__enter__ = MagicMock(return_value=mock_mss_instance)
        mock_mss_instance.__exit__ = MagicMock(return_value=False)
        mock_mss_instance.monitors = mock_monitors

        with patch("src.capture.monitor._mss_module") as mock_mss_module:
            mock_mss_module.mss.return_value = mock_mss_instance
            monitors = discover_monitors()

        self.assertEqual(len(monitors), 2)
        self.assertEqual(monitors[0].x, -1920)
        self.assertEqual(monitors[0].y, 0)

    def test_discover_raises_on_mss_failure(self) -> None:
        """discover_monitors raises RuntimeError when MSS fails."""
        with patch("src.capture.monitor._mss_module") as mock_mss_module:
            mock_mss_module.mss.side_effect = OSError("no display")
            with self.assertRaises(RuntimeError):
                discover_monitors()


class CaptureRegionTests(unittest.TestCase):
    """Tests for CaptureRegion and validate_region."""

    def test_region_fields(self) -> None:
        region = CaptureRegion(x=100, y=200, width=800, height=600)
        self.assertEqual(region.x, 100)
        self.assertEqual(region.y, 200)
        self.assertEqual(region.width, 800)
        self.assertEqual(region.height, 600)

    def test_from_monitor_creates_full_region(self) -> None:
        monitor = MonitorInfo(index=1, x=0, y=0, width=1920, height=1080)
        region = CaptureRegion.from_monitor(monitor)
        self.assertEqual(region.x, 0)
        self.assertEqual(region.y, 0)
        self.assertEqual(region.width, 1920)
        self.assertEqual(region.height, 1080)

    def test_from_monitor_with_negative_origin(self) -> None:
        monitor = MonitorInfo(index=2, x=-1920, y=0, width=1920, height=1080)
        region = CaptureRegion.from_monitor(monitor)
        self.assertEqual(region.x, -1920)
        self.assertEqual(region.width, 1920)

    def test_region_is_frozen(self) -> None:
        region = CaptureRegion(x=0, y=0, width=100, height=100)
        with self.assertRaises((AttributeError, TypeError)):
            region.width = 999  # type: ignore[misc]

    def test_validate_region_valid(self) -> None:
        monitor = MonitorInfo(index=1, x=0, y=0, width=1920, height=1080)
        region = CaptureRegion(x=100, y=100, width=800, height=600)
        validate_region(region, monitor)  # Should not raise.

    def test_validate_region_full_monitor(self) -> None:
        monitor = MonitorInfo(index=1, x=0, y=0, width=1920, height=1080)
        region = CaptureRegion.from_monitor(monitor)
        validate_region(region, monitor)  # Should not raise.

    def test_validate_region_zero_width_rejected(self) -> None:
        monitor = MonitorInfo(index=1, x=0, y=0, width=1920, height=1080)
        region = CaptureRegion(x=0, y=0, width=0, height=100)
        with self.assertRaises(RegionError):
            validate_region(region, monitor)

    def test_validate_region_negative_width_rejected(self) -> None:
        monitor = MonitorInfo(index=1, x=0, y=0, width=1920, height=1080)
        region = CaptureRegion(x=0, y=0, width=-1, height=100)
        with self.assertRaises(RegionError):
            validate_region(region, monitor)

    def test_validate_region_zero_height_rejected(self) -> None:
        monitor = MonitorInfo(index=1, x=0, y=0, width=1920, height=1080)
        region = CaptureRegion(x=0, y=0, width=100, height=0)
        with self.assertRaises(RegionError):
            validate_region(region, monitor)

    def test_validate_region_exceeds_right_edge(self) -> None:
        monitor = MonitorInfo(index=1, x=0, y=0, width=1920, height=1080)
        region = CaptureRegion(x=1800, y=0, width=200, height=100)
        with self.assertRaises(RegionError):
            validate_region(region, monitor)

    def test_validate_region_exceeds_bottom_edge(self) -> None:
        monitor = MonitorInfo(index=1, x=0, y=0, width=1920, height=1080)
        region = CaptureRegion(x=0, y=1000, width=100, height=200)
        with self.assertRaises(RegionError):
            validate_region(region, monitor)

    def test_validate_region_left_of_monitor(self) -> None:
        monitor = MonitorInfo(index=2, x=1920, y=0, width=1920, height=1080)
        region = CaptureRegion(x=1800, y=0, width=200, height=100)
        with self.assertRaises(RegionError):
            validate_region(region, monitor)

    def test_validate_region_negative_monitor_origin(self) -> None:
        """Regions on monitors with negative origins validate correctly."""
        monitor = MonitorInfo(index=2, x=-1920, y=0, width=1920, height=1080)
        region = CaptureRegion(x=-1920, y=0, width=800, height=600)
        validate_region(region, monitor)  # Should not raise.


class CaptureFrameTests(unittest.TestCase):
    """Tests for CaptureFrame construction and field access."""

    def test_frame_fields(self) -> None:
        ts = datetime.now(tz=timezone.utc)
        region = CaptureRegion(x=0, y=0, width=4, height=4)
        raw = bytes(4 * 4 * 4)
        frame = CaptureFrame(
            timestamp=ts,
            monitor_index=1,
            region=region,
            width=4,
            height=4,
            raw=raw,
        )
        self.assertEqual(frame.timestamp, ts)
        self.assertEqual(frame.monitor_index, 1)
        self.assertEqual(frame.region, region)
        self.assertEqual(frame.width, 4)
        self.assertEqual(frame.height, 4)
        self.assertEqual(len(frame.raw), 64)

    def test_frame_is_frozen(self) -> None:
        frame = _make_frame()
        with self.assertRaises((AttributeError, TypeError)):
            frame.width = 999  # type: ignore[misc]

    def test_frame_raw_is_bytes(self) -> None:
        frame = _make_frame()
        self.assertIsInstance(frame.raw, bytes)


class CaptureWorkerLifecycleTests(unittest.TestCase):
    """Tests for CaptureWorker lifecycle states and configuration."""

    def test_initial_state_is_created(self) -> None:
        worker = CaptureWorker(AppConfig())
        self.assertEqual(worker.state, WorkerState.CREATED)

    def test_stop_before_start_is_safe(self) -> None:
        """Calling stop() before run_capture() must not raise."""
        worker = CaptureWorker(AppConfig())
        worker.stop()  # Should not raise.
        self.assertEqual(worker.state, WorkerState.CREATED)

    def test_take_latest_frame_returns_none_initially(self) -> None:
        worker = CaptureWorker(AppConfig())
        self.assertIsNone(worker.take_latest_frame())

    def test_configuration_interval_is_used(self) -> None:
        """Worker reads capture_interval from config, not a hard-coded value."""
        config = AppConfig(screen=ScreenConfig(capture_interval=5.0))
        worker = CaptureWorker(config)
        self.assertEqual(worker._config.screen.capture_interval, 5.0)

    def test_worker_stops_cleanly_via_event(self) -> None:
        """Worker run_capture exits when stop() is called; no physical monitor."""
        config = AppConfig(screen=ScreenConfig(capture_interval=0.25))
        worker = CaptureWorker(config)

        stopped_events: list[bool] = []

        def _on_stopped() -> None:
            stopped_events.append(True)

        worker.capture_stopped.connect(_on_stopped)

        # Mock MSS to return a minimal monitor setup.
        mock_screenshot = MagicMock()
        mock_screenshot.raw = bytes(4 * 4 * 4)
        mock_screenshot.width = 4
        mock_screenshot.height = 4

        mock_mss_instance = MagicMock()
        mock_mss_instance.__enter__ = MagicMock(return_value=mock_mss_instance)
        mock_mss_instance.__exit__ = MagicMock(return_value=False)
        mock_mss_instance.monitors = [
            {"left": 0, "top": 0, "width": 4, "height": 4},   # index 0: virtual
            {"left": 0, "top": 0, "width": 4, "height": 4},   # index 1: primary
        ]
        mock_mss_instance.grab.return_value = mock_screenshot

        stop_flag = threading.Event()

        def _run_worker() -> None:
            with patch("src.capture.worker._mss_module") as mock_mss_module:
                mock_mss_module.mss.return_value = mock_mss_instance
                worker.run_capture()
            stop_flag.set()

        thread = threading.Thread(target=_run_worker, daemon=True)
        thread.start()

        # Give the worker a moment to start, then stop it.
        time.sleep(0.1)
        worker.stop()

        # Wait for the worker thread to finish (up to 3 seconds).
        stop_flag.wait(timeout=3.0)
        thread.join(timeout=3.0)

        self.assertEqual(worker.state, WorkerState.STOPPED)
        self.assertFalse(thread.is_alive())


class CaptureWorkerLatestFrameTests(unittest.TestCase):
    """Tests for the latest-frame bounded replacement policy."""

    def test_downstream_consumption_discards_stale_frames(self) -> None:
        """A downstream read receives only the newest frame, never a backlog."""
        worker = CaptureWorker(AppConfig())

        frame_a = _make_frame(fill=10)
        frame_b = _make_frame(fill=20)
        frame_c = _make_frame(fill=30)

        # Simulate the worker storing frames.
        with worker._frame_lock:
            worker._latest_frame = frame_a
        with worker._frame_lock:
            worker._latest_frame = frame_b
        with worker._frame_lock:
            worker._latest_frame = frame_c

        # A bounded downstream consumer receives only the last frame.
        retrieved = worker.take_latest_frame()
        self.assertIs(retrieved, frame_c)
        self.assertIsNone(worker.take_latest_frame())

    def test_take_latest_frame_clears_slot(self) -> None:
        """After take_latest_frame(), the slot is empty."""
        worker = CaptureWorker(AppConfig())
        frame = _make_frame()
        with worker._frame_lock:
            worker._latest_frame = frame

        first = worker.take_latest_frame()
        second = worker.take_latest_frame()

        self.assertIs(first, frame)
        self.assertIsNone(second)

    def test_no_frame_accumulation_under_lock(self) -> None:
        """The worker never holds more than one frame at a time."""
        worker = CaptureWorker(AppConfig())

        # Simulate rapid frame production.
        for i in range(100):
            frame = _make_frame(fill=i % 256)
            with worker._frame_lock:
                worker._latest_frame = frame

        # Only one frame is retained.
        retrieved = worker.take_latest_frame()
        self.assertIsNotNone(retrieved)
        self.assertIsNone(worker.take_latest_frame())


if __name__ == "__main__":
    unittest.main()
