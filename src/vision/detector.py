"""CPU-efficient frame change detector — pure Python, no NumPy, no OpenCV.

Algorithm
---------
1. Downsample: sample every STRIDE-th pixel from the raw BGRA bytes.
   This reduces the comparison cost by a factor of STRIDE^2 while
   preserving coarse spatial structure.

2. Grayscale: convert each sampled BGRA pixel to a single luminance value
   using the standard BT.601 coefficients:
       Y = R * 0.299 + G * 0.587 + B * 0.114
   (MSS returns BGRA order: byte 0=B, 1=G, 2=R, 3=A)

3. Compare: compute the mean absolute difference (MAD) between the
   grayscale samples of the previous and current frames.

4. Normalise: divide by 255 to produce a score in [0.0, 1.0].

5. Threshold: compare the score against config.screen.change_threshold.

First-frame behaviour
---------------------
The first frame passed to process() establishes the baseline. It does NOT
produce a "changed" event — the returned ChangeResult has change_score=0.0
and changed=False. Every subsequent frame is compared against the most
recently processed frame.

Memory boundedness
------------------
The detector retains exactly one frame reference (_previous_frame). There
is no history list, no queue, and no accumulation. Each call to process()
replaces the previous reference with the current frame.

Performance
-----------
STRIDE=8 reduces a 1920×1080 frame (2,073,600 pixels) to ~32,400 samples.
At 4 bytes per pixel, the sampled data is ~130 KB — well within the target
16 GB RAM budget. The pure-Python loop over ~32,400 samples completes in
well under 100 ms on a CPU-only laptop.

Privacy
-------
Raw pixel data is never logged, persisted, or transmitted. Only the numeric
change_score and the changed boolean are exposed in ChangeResult.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.app.config import AppConfig
from src.app.logging_config import LOGGER_NAME
from src.capture.frame import CaptureFrame
from src.vision.result import ChangeResult


# Pixel stride for downsampling. Every STRIDE-th pixel in both x and y
# is sampled. Increasing this value reduces CPU cost at the expense of
# sensitivity to small localised changes.
_STRIDE: int = 8

# Bytes per pixel in MSS BGRA output.
_BYTES_PER_PIXEL: int = 4

# BT.601 luminance coefficients for BGRA byte order (B=0, G=1, R=2, A=3).
_COEFF_B: float = 0.114
_COEFF_G: float = 0.587
_COEFF_R: float = 0.299


def _grayscale_samples(raw: bytes, width: int, height: int) -> list[float]:
    """Extract stride-downsampled grayscale values from raw BGRA bytes.

    Args:
        raw:    Raw BGRA bytes from a CaptureFrame.
        width:  Frame width in pixels.
        height: Frame height in pixels.

    Returns:
        A list of float luminance values in [0.0, 255.0], one per sampled
        pixel. The list length is approximately (width/STRIDE)*(height/STRIDE).
    """
    samples: list[float] = []
    row_stride = width * _BYTES_PER_PIXEL

    for row in range(0, height, _STRIDE):
        row_offset = row * row_stride
        for col in range(0, width, _STRIDE):
            pixel_offset = row_offset + col * _BYTES_PER_PIXEL
            b = raw[pixel_offset]
            g = raw[pixel_offset + 1]
            r = raw[pixel_offset + 2]
            # Alpha channel (pixel_offset + 3) is ignored.
            samples.append(r * _COEFF_R + g * _COEFF_G + b * _COEFF_B)

    return samples


def _mean_absolute_difference(
    samples_a: list[float],
    samples_b: list[float],
) -> float:
    """Compute the normalised mean absolute difference between two sample lists.

    Args:
        samples_a: Grayscale samples from the previous frame.
        samples_b: Grayscale samples from the current frame.

    Returns:
        A float in [0.0, 1.0]. Returns 0.0 if either list is empty or if
        the lists have different lengths (defensive fallback).
    """
    count = len(samples_a)
    if count == 0 or count != len(samples_b):
        return 0.0

    total = sum(abs(a - b) for a, b in zip(samples_a, samples_b))
    # Divide by count to get mean, then by 255 to normalise to [0, 1].
    return total / (count * 255.0)


class ChangeDetector:
    """Stateful frame change detector.

    Maintains a single previous-frame reference. Each call to process()
    compares the new frame against the previous one and returns a ChangeResult.

    The first call establishes the baseline and always returns changed=False
    with change_score=0.0.

    Thread safety: ChangeDetector is NOT thread-safe. It is designed to be
    called from a single thread (the application's main thread or a dedicated
    processing thread). Do not share a ChangeDetector instance across threads.
    """

    def __init__(self, config: AppConfig) -> None:
        self._threshold: float = config.screen.change_threshold
        self._logger = logging.getLogger(LOGGER_NAME)
        self._previous_frame: CaptureFrame | None = None
        # Cache the grayscale samples of the previous frame to avoid
        # recomputing them on every call.
        self._previous_samples: list[float] | None = None

    def process(self, frame: CaptureFrame) -> ChangeResult:
        """Compare frame against the previous frame and return a ChangeResult.

        First-frame behaviour: the first call stores the frame as the baseline
        and returns ChangeResult with change_score=0.0 and changed=False.

        Subsequent calls: compare the current frame against the previous frame
        using stride-downsampled grayscale MAD. The previous frame reference
        is then replaced with the current frame (bounded single-frame state).

        Args:
            frame: The current CaptureFrame to process.

        Returns:
            A ChangeResult with the comparison metadata.
        """
        if self._previous_frame is None:
            # First frame: establish baseline, no comparison.
            self._previous_frame = frame
            self._previous_samples = _grayscale_samples(
                frame.raw, frame.width, frame.height
            )
            self._logger.info("change_detector_baseline_set")
            return ChangeResult(
                timestamp=frame.timestamp,
                monitor_index=frame.monitor_index,
                region=frame.region,
                change_score=0.0,
                changed=False,
            )

        # Compute grayscale samples for the current frame.
        current_samples = _grayscale_samples(frame.raw, frame.width, frame.height)

        # Compute normalised MAD score.
        if self._previous_samples is not None:
            score = _mean_absolute_difference(self._previous_samples, current_samples)
        else:
            score = 0.0

        changed = score >= self._threshold

        # Replace previous frame reference (bounded single-frame state).
        self._previous_frame = frame
        self._previous_samples = current_samples

        return ChangeResult(
            timestamp=frame.timestamp,
            monitor_index=frame.monitor_index,
            region=frame.region,
            change_score=score,
            changed=changed,
        )

    def reset(self) -> None:
        """Clear the baseline so the next frame is treated as the first.

        Useful when the capture target changes (e.g., different monitor or
        region). After reset(), the next call to process() will establish
        a new baseline.
        """
        self._previous_frame = None
        self._previous_samples = None
        self._logger.info("change_detector_reset")
