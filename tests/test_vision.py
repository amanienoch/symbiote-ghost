"""Phase 3 change-detection unit tests.

All tests use synthetic deterministic BGRA frames — no physical monitor,
no MSS, no network access, no AI. Tests are fully deterministic.

Test coverage:
1. First frame establishes baseline (changed=False, score=0.0).
2. Identical frames produce approximately zero change score.
3. Small controlled differences produce a small score.
4. Large controlled differences produce a larger score.
5. Threshold controls the changed boolean.
6. Configured threshold is respected (not hard-coded).
7. Metadata (timestamp, monitor_index, region) is preserved in ChangeResult.
8. No unbounded frame history — detector retains only one frame reference.
9. reset() clears the baseline so the next frame is treated as first.
10. Score is normalised to [0.0, 1.0].
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from src.app.config import AppConfig, ScreenConfig
from src.capture.frame import CaptureFrame
from src.capture.region import CaptureRegion
from src.vision.detector import ChangeDetector, _grayscale_samples, _mean_absolute_difference
from src.vision.result import ChangeResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_frame(
    width: int = 8,
    height: int = 8,
    fill_bgra: tuple[int, int, int, int] = (128, 128, 128, 255),
    monitor_index: int = 1,
    timestamp: datetime | None = None,
) -> CaptureFrame:
    """Create a synthetic CaptureFrame filled with a uniform BGRA colour."""
    if timestamp is None:
        timestamp = datetime.now(tz=timezone.utc)
    region = CaptureRegion(x=0, y=0, width=width, height=height)
    b, g, r, a = fill_bgra
    raw = bytes([b, g, r, a] * (width * height))
    return CaptureFrame(
        timestamp=timestamp,
        monitor_index=monitor_index,
        region=region,
        width=width,
        height=height,
        raw=raw,
    )


def _make_frame_with_pattern(
    width: int,
    height: int,
    pattern: bytes,
    monitor_index: int = 1,
    timestamp: datetime | None = None,
) -> CaptureFrame:
    """Create a CaptureFrame with an explicit raw BGRA byte pattern."""
    if timestamp is None:
        timestamp = datetime.now(tz=timezone.utc)
    assert len(pattern) == width * height * 4, (
        f"Pattern length {len(pattern)} != {width * height * 4}"
    )
    region = CaptureRegion(x=0, y=0, width=width, height=height)
    return CaptureFrame(
        timestamp=timestamp,
        monitor_index=monitor_index,
        region=region,
        width=width,
        height=height,
        raw=pattern,
    )


def _default_config(threshold: float = 0.08) -> AppConfig:
    return AppConfig(screen=ScreenConfig(change_threshold=threshold))


# ---------------------------------------------------------------------------
# ChangeResult tests
# ---------------------------------------------------------------------------

class ChangeResultTests(unittest.TestCase):
    """Tests for the ChangeResult frozen dataclass."""

    def test_fields_are_stored(self) -> None:
        ts = datetime.now(tz=timezone.utc)
        region = CaptureRegion(x=0, y=0, width=8, height=8)
        result = ChangeResult(
            timestamp=ts,
            monitor_index=1,
            region=region,
            change_score=0.05,
            changed=False,
        )
        self.assertEqual(result.timestamp, ts)
        self.assertEqual(result.monitor_index, 1)
        self.assertEqual(result.region, region)
        self.assertAlmostEqual(result.change_score, 0.05)
        self.assertFalse(result.changed)

    def test_result_is_frozen(self) -> None:
        ts = datetime.now(tz=timezone.utc)
        region = CaptureRegion(x=0, y=0, width=8, height=8)
        result = ChangeResult(
            timestamp=ts,
            monitor_index=1,
            region=region,
            change_score=0.0,
            changed=False,
        )
        with self.assertRaises((AttributeError, TypeError)):
            result.change_score = 1.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Internal algorithm tests
# ---------------------------------------------------------------------------

class GrayscaleSamplesTests(unittest.TestCase):
    """Tests for the _grayscale_samples helper."""

    def test_uniform_black_frame(self) -> None:
        """All-black BGRA frame produces all-zero grayscale samples."""
        raw = bytes([0, 0, 0, 255] * 64)  # 8x8 black
        samples = _grayscale_samples(raw, width=8, height=8)
        self.assertTrue(all(s == 0.0 for s in samples))

    def test_uniform_white_frame(self) -> None:
        """All-white BGRA frame produces all-255 grayscale samples."""
        raw = bytes([255, 255, 255, 255] * 64)  # 8x8 white
        samples = _grayscale_samples(raw, width=8, height=8)
        self.assertTrue(all(abs(s - 255.0) < 1.0 for s in samples))

    def test_pure_red_pixel(self) -> None:
        """Pure red (BGRA: 0, 0, 255, 255) → Y ≈ 255 * 0.299 ≈ 76.245."""
        raw = bytes([0, 0, 255, 255] * 64)  # 8x8 pure red
        samples = _grayscale_samples(raw, width=8, height=8)
        expected = 255 * 0.299
        for s in samples:
            self.assertAlmostEqual(s, expected, places=1)

    def test_samples_are_downsampled(self) -> None:
        """Stride-based sampling produces fewer samples than total pixels."""
        raw = bytes([128, 128, 128, 255] * (32 * 32))
        samples = _grayscale_samples(raw, width=32, height=32)
        # With stride=8, we expect (32/8) * (32/8) = 16 samples.
        self.assertEqual(len(samples), 16)


class MeanAbsoluteDifferenceTests(unittest.TestCase):
    """Tests for the _mean_absolute_difference helper."""

    def test_identical_lists_produce_zero(self) -> None:
        samples = [100.0, 150.0, 200.0, 50.0]
        self.assertAlmostEqual(_mean_absolute_difference(samples, samples), 0.0)

    def test_empty_lists_produce_zero(self) -> None:
        self.assertAlmostEqual(_mean_absolute_difference([], []), 0.0)

    def test_mismatched_lengths_produce_zero(self) -> None:
        self.assertAlmostEqual(_mean_absolute_difference([1.0], [1.0, 2.0]), 0.0)

    def test_maximum_difference(self) -> None:
        """Black vs white: MAD = 255/255 = 1.0."""
        a = [0.0] * 4
        b = [255.0] * 4
        self.assertAlmostEqual(_mean_absolute_difference(a, b), 1.0)

    def test_half_difference(self) -> None:
        """128 vs 0: MAD = 128/255 ≈ 0.502."""
        a = [128.0] * 4
        b = [0.0] * 4
        result = _mean_absolute_difference(a, b)
        self.assertAlmostEqual(result, 128.0 / 255.0, places=3)


# ---------------------------------------------------------------------------
# ChangeDetector tests
# ---------------------------------------------------------------------------

class ChangeDetectorFirstFrameTests(unittest.TestCase):
    """Test 1: First frame establishes baseline without producing a change."""

    def test_first_frame_returns_not_changed(self) -> None:
        detector = ChangeDetector(_default_config())
        frame = _make_frame()
        result = detector.process(frame)
        self.assertFalse(result.changed)

    def test_first_frame_score_is_zero(self) -> None:
        detector = ChangeDetector(_default_config())
        frame = _make_frame()
        result = detector.process(frame)
        self.assertAlmostEqual(result.change_score, 0.0)

    def test_first_frame_sets_previous_frame(self) -> None:
        detector = ChangeDetector(_default_config())
        frame = _make_frame()
        detector.process(frame)
        self.assertIs(detector._previous_frame, frame)


class ChangeDetectorIdenticalFramesTests(unittest.TestCase):
    """Test 2: Identical frames produce approximately zero change score."""

    def test_identical_frames_score_near_zero(self) -> None:
        detector = ChangeDetector(_default_config(threshold=0.08))
        frame_a = _make_frame(fill_bgra=(100, 150, 200, 255))
        frame_b = _make_frame(fill_bgra=(100, 150, 200, 255))
        detector.process(frame_a)
        result = detector.process(frame_b)
        self.assertAlmostEqual(result.change_score, 0.0, places=6)
        self.assertFalse(result.changed)

    def test_identical_black_frames(self) -> None:
        detector = ChangeDetector(_default_config())
        frame_a = _make_frame(fill_bgra=(0, 0, 0, 255))
        frame_b = _make_frame(fill_bgra=(0, 0, 0, 255))
        detector.process(frame_a)
        result = detector.process(frame_b)
        self.assertAlmostEqual(result.change_score, 0.0, places=6)


class ChangeDetectorSmallDifferenceTests(unittest.TestCase):
    """Test 3: Small controlled differences produce a small score."""

    def test_small_brightness_change_produces_small_score(self) -> None:
        """Changing brightness by ~10/255 ≈ 0.039 should produce a small score."""
        detector = ChangeDetector(_default_config(threshold=0.08))
        # Frame A: mid-grey (128, 128, 128)
        frame_a = _make_frame(fill_bgra=(128, 128, 128, 255))
        # Frame B: slightly brighter (138, 138, 138) — delta ≈ 10/255 ≈ 0.039
        frame_b = _make_frame(fill_bgra=(138, 138, 138, 255))
        detector.process(frame_a)
        result = detector.process(frame_b)
        self.assertGreater(result.change_score, 0.0)
        self.assertLess(result.change_score, 0.08)  # Below default threshold.
        self.assertFalse(result.changed)


class ChangeDetectorLargeDifferenceTests(unittest.TestCase):
    """Test 4: Large controlled differences produce a larger score."""

    def test_black_to_white_produces_large_score(self) -> None:
        """Black → white is the maximum possible change (score ≈ 1.0)."""
        detector = ChangeDetector(_default_config(threshold=0.08))
        frame_a = _make_frame(fill_bgra=(0, 0, 0, 255))
        frame_b = _make_frame(fill_bgra=(255, 255, 255, 255))
        detector.process(frame_a)
        result = detector.process(frame_b)
        self.assertGreater(result.change_score, 0.5)
        self.assertTrue(result.changed)

    def test_large_difference_exceeds_threshold(self) -> None:
        detector = ChangeDetector(_default_config(threshold=0.08))
        frame_a = _make_frame(fill_bgra=(0, 0, 0, 255))
        frame_b = _make_frame(fill_bgra=(200, 200, 200, 255))
        detector.process(frame_a)
        result = detector.process(frame_b)
        self.assertTrue(result.changed)
        self.assertGreater(result.change_score, 0.08)


class ChangeDetectorThresholdTests(unittest.TestCase):
    """Test 5 & 6: Threshold controls changed bool; configured threshold respected."""

    def test_score_below_threshold_is_not_changed(self) -> None:
        """Score just below threshold → changed=False."""
        # Use a high threshold so a moderate change is below it.
        detector = ChangeDetector(_default_config(threshold=0.5))
        frame_a = _make_frame(fill_bgra=(0, 0, 0, 255))
        frame_b = _make_frame(fill_bgra=(100, 100, 100, 255))
        detector.process(frame_a)
        result = detector.process(frame_b)
        # Score ≈ 100/255 ≈ 0.392, which is below 0.5.
        self.assertFalse(result.changed)

    def test_score_above_threshold_is_changed(self) -> None:
        """Score just above threshold → changed=True."""
        # Use a very low threshold so even a small change triggers it.
        detector = ChangeDetector(_default_config(threshold=0.01))
        frame_a = _make_frame(fill_bgra=(0, 0, 0, 255))
        frame_b = _make_frame(fill_bgra=(10, 10, 10, 255))
        detector.process(frame_a)
        result = detector.process(frame_b)
        # Score ≈ 10/255 ≈ 0.039, which is above 0.01.
        self.assertTrue(result.changed)

    def test_configured_threshold_is_used_not_hardcoded(self) -> None:
        """Two detectors with different thresholds produce different changed values."""
        frame_a = _make_frame(fill_bgra=(0, 0, 0, 255))
        frame_b = _make_frame(fill_bgra=(50, 50, 50, 255))

        # High threshold: not changed.
        detector_high = ChangeDetector(_default_config(threshold=0.5))
        detector_high.process(frame_a)
        result_high = detector_high.process(frame_b)

        # Low threshold: changed.
        detector_low = ChangeDetector(_default_config(threshold=0.01))
        detector_low.process(frame_a)
        result_low = detector_low.process(frame_b)

        self.assertFalse(result_high.changed)
        self.assertTrue(result_low.changed)

    def test_default_threshold_is_0_08(self) -> None:
        """Default config threshold is 0.08 as specified."""
        config = AppConfig()
        self.assertAlmostEqual(config.screen.change_threshold, 0.08)
        detector = ChangeDetector(config)
        self.assertAlmostEqual(detector._threshold, 0.08)


class ChangeDetectorMetadataTests(unittest.TestCase):
    """Test 7: Metadata is preserved in ChangeResult."""

    def test_timestamp_from_current_frame(self) -> None:
        """ChangeResult.timestamp matches the current frame's timestamp."""
        detector = ChangeDetector(_default_config())
        ts_a = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        ts_b = datetime(2024, 1, 1, 0, 0, 2, tzinfo=timezone.utc)
        frame_a = _make_frame(timestamp=ts_a)
        frame_b = _make_frame(timestamp=ts_b)
        detector.process(frame_a)
        result = detector.process(frame_b)
        self.assertEqual(result.timestamp, ts_b)

    def test_monitor_index_preserved(self) -> None:
        detector = ChangeDetector(_default_config())
        frame_a = _make_frame(monitor_index=2)
        frame_b = _make_frame(monitor_index=2)
        detector.process(frame_a)
        result = detector.process(frame_b)
        self.assertEqual(result.monitor_index, 2)

    def test_region_preserved(self) -> None:
        detector = ChangeDetector(_default_config())
        frame_a = _make_frame()
        frame_b = _make_frame()
        detector.process(frame_a)
        result = detector.process(frame_b)
        self.assertEqual(result.region, frame_b.region)

    def test_first_frame_metadata_preserved(self) -> None:
        """First-frame ChangeResult carries the frame's own metadata."""
        detector = ChangeDetector(_default_config())
        ts = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        frame = _make_frame(monitor_index=3, timestamp=ts)
        result = detector.process(frame)
        self.assertEqual(result.timestamp, ts)
        self.assertEqual(result.monitor_index, 3)


class ChangeDetectorBoundedStateTests(unittest.TestCase):
    """Test 8: No unbounded frame history — detector retains only one frame."""

    def test_only_one_previous_frame_retained(self) -> None:
        """After N frames, only the most recent is stored."""
        detector = ChangeDetector(_default_config())
        frames = [_make_frame(fill_bgra=(i, i, i, 255)) for i in range(10)]
        for frame in frames:
            detector.process(frame)
        # Only the last frame should be the previous frame.
        self.assertIs(detector._previous_frame, frames[-1])

    def test_no_frame_list_or_history_attribute(self) -> None:
        """Detector has no list or history of frames."""
        detector = ChangeDetector(_default_config())
        # The detector should not have any list-type attributes that grow.
        for attr_name in dir(detector):
            if attr_name.startswith("_") and not attr_name.startswith("__"):
                value = getattr(detector, attr_name)
                if isinstance(value, list):
                    self.assertEqual(
                        len(value),
                        0,
                        f"Unexpected non-empty list attribute: {attr_name}",
                    )

    def test_previous_samples_replaced_not_accumulated(self) -> None:
        """_previous_samples is replaced, not appended to."""
        detector = ChangeDetector(_default_config())
        frame_a = _make_frame(width=8, height=8)
        frame_b = _make_frame(width=8, height=8)
        detector.process(frame_a)
        samples_after_a = detector._previous_samples
        detector.process(frame_b)
        samples_after_b = detector._previous_samples
        # The samples object should be replaced, not the same list.
        self.assertIsNot(samples_after_a, samples_after_b)


class ChangeDetectorResetTests(unittest.TestCase):
    """Tests for the reset() method."""

    def test_reset_clears_baseline(self) -> None:
        detector = ChangeDetector(_default_config())
        frame = _make_frame()
        detector.process(frame)
        self.assertIsNotNone(detector._previous_frame)
        detector.reset()
        self.assertIsNone(detector._previous_frame)
        self.assertIsNone(detector._previous_samples)

    def test_after_reset_next_frame_is_baseline(self) -> None:
        """After reset(), the next frame is treated as the first."""
        detector = ChangeDetector(_default_config())
        frame_a = _make_frame(fill_bgra=(0, 0, 0, 255))
        frame_b = _make_frame(fill_bgra=(255, 255, 255, 255))
        detector.process(frame_a)
        detector.reset()
        # frame_b is now the first frame after reset — should not be "changed".
        result = detector.process(frame_b)
        self.assertFalse(result.changed)
        self.assertAlmostEqual(result.change_score, 0.0)


class ChangeDetectorScoreRangeTests(unittest.TestCase):
    """Test 10: Score is normalised to [0.0, 1.0]."""

    def test_score_is_between_zero_and_one(self) -> None:
        detector = ChangeDetector(_default_config())
        frame_a = _make_frame(fill_bgra=(0, 0, 0, 255))
        frame_b = _make_frame(fill_bgra=(255, 255, 255, 255))
        detector.process(frame_a)
        result = detector.process(frame_b)
        self.assertGreaterEqual(result.change_score, 0.0)
        self.assertLessEqual(result.change_score, 1.0)

    def test_score_for_identical_frames_is_zero(self) -> None:
        detector = ChangeDetector(_default_config())
        frame_a = _make_frame(fill_bgra=(200, 100, 50, 255))
        frame_b = _make_frame(fill_bgra=(200, 100, 50, 255))
        detector.process(frame_a)
        result = detector.process(frame_b)
        self.assertAlmostEqual(result.change_score, 0.0, places=6)


if __name__ == "__main__":
    unittest.main()
