"""Phase 2 screen-capture package — public API surface.

Pipeline position:
    Windows Screen → MSS Capture → CaptureFrame → Change Detection
"""

from __future__ import annotations

from src.capture.frame import CaptureFrame
from src.capture.monitor import MonitorInfo, discover_monitors
from src.capture.region import CaptureRegion, validate_region
from src.capture.worker import CaptureWorker

__all__ = [
    "CaptureFrame",
    "CaptureRegion",
    "CaptureWorker",
    "MonitorInfo",
    "discover_monitors",
    "validate_region",
]
