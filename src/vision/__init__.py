"""Phase 3 change-detection package — public API surface.

Pipeline position:
    CaptureFrame → ChangeDetector → ChangeResult → [Future OCR / Vision]
"""

from __future__ import annotations

from src.vision.detector import ChangeDetector
from src.vision.result import ChangeResult

__all__ = [
    "ChangeDetector",
    "ChangeResult",
]
