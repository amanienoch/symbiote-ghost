"""Change-detection result representation.

A ChangeResult is produced by ChangeDetector for every frame after the first.
It carries enough metadata for downstream consumers to decide whether to
proceed with OCR or AI processing.

Raw screen content is never included in a ChangeResult. Only the numeric
change score and the changed boolean are exposed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.capture.region import CaptureRegion


@dataclass(frozen=True)
class ChangeResult:
    """Immutable result of a single frame-comparison operation.

    Attributes:
        timestamp:     UTC datetime of the current frame (from CaptureFrame).
        monitor_index: MSS monitor index the frames were captured from.
        region:        The rectangular region that was compared.
        change_score:  Normalised mean absolute difference in [0.0, 1.0].
                       0.0 means identical; 1.0 means completely different.
        changed:       True when change_score >= the configured threshold.
    """

    timestamp: datetime
    monitor_index: int
    region: CaptureRegion
    change_score: float
    changed: bool
