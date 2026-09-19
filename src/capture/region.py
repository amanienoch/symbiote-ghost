"""Rectangular capture region representation and validation.

A region defines the sub-rectangle of a monitor to capture. Full-monitor
capture is represented by a region that exactly matches the monitor geometry.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.capture.monitor import MonitorInfo


@dataclass(frozen=True)
class CaptureRegion:
    """An immutable rectangular region in virtual screen coordinates.

    Attributes:
        x:      Left edge in virtual screen coordinates.
        y:      Top edge in virtual screen coordinates.
        width:  Width in pixels (must be positive).
        height: Height in pixels (must be positive).
    """

    x: int
    y: int
    width: int
    height: int

    @classmethod
    def from_monitor(cls, monitor: MonitorInfo) -> "CaptureRegion":
        """Create a full-monitor region from a MonitorInfo."""
        return cls(
            x=monitor.x,
            y=monitor.y,
            width=monitor.width,
            height=monitor.height,
        )


class RegionError(ValueError):
    """A capture region is invalid or outside monitor bounds."""


def validate_region(region: CaptureRegion, monitor: MonitorInfo) -> None:
    """Validate that a region is non-empty and fits within the monitor.

    Args:
        region:  The region to validate.
        monitor: The monitor the region must fit within.

    Raises:
        RegionError: If the region has non-positive dimensions or extends
                     outside the monitor boundaries.
    """
    if region.width <= 0:
        raise RegionError(
            f"Region width must be positive, got {region.width}."
        )
    if region.height <= 0:
        raise RegionError(
            f"Region height must be positive, got {region.height}."
        )

    monitor_right = monitor.x + monitor.width
    monitor_bottom = monitor.y + monitor.height
    region_right = region.x + region.width
    region_bottom = region.y + region.height

    if region.x < monitor.x:
        raise RegionError(
            f"Region left edge ({region.x}) is outside monitor "
            f"left edge ({monitor.x})."
        )
    if region.y < monitor.y:
        raise RegionError(
            f"Region top edge ({region.y}) is outside monitor "
            f"top edge ({monitor.y})."
        )
    if region_right > monitor_right:
        raise RegionError(
            f"Region right edge ({region_right}) exceeds monitor "
            f"right edge ({monitor_right})."
        )
    if region_bottom > monitor_bottom:
        raise RegionError(
            f"Region bottom edge ({region_bottom}) exceeds monitor "
            f"bottom edge ({monitor_bottom})."
        )
