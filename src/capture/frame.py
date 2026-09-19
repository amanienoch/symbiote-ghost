"""Captured frame representation.

A CaptureFrame holds the raw pixel data from a single MSS screenshot along
with enough metadata for downstream processing. Raw pixel data is never
logged, persisted to disk, or uploaded.

MSS returns BGRA (Blue, Green, Red, Alpha) byte order on Windows.
Each pixel occupies 4 bytes. Total buffer size = width * height * 4.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.capture.region import CaptureRegion


@dataclass(frozen=True)
class CaptureFrame:
    """An immutable snapshot from a single screen-capture operation.

    Attributes:
        timestamp:     UTC datetime when the capture completed.
        monitor_index: MSS monitor index (1-based) the frame was taken from.
        region:        The rectangular region that was captured.
        width:         Frame width in pixels (matches region.width).
        height:        Frame height in pixels (matches region.height).
        raw:           Raw BGRA pixel bytes from MSS. Length = width*height*4.
                       Never log, persist, or transmit this data.
    """

    timestamp: datetime
    monitor_index: int
    region: CaptureRegion
    width: int
    height: int
    raw: bytes
