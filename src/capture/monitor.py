"""Windows monitor discovery using MSS.

Represents monitor geometry explicitly and handles negative coordinates
correctly. Does not assume the primary monitor starts at (0, 0).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import mss as _mss_module  # type: ignore[import-untyped]

from src.app.logging_config import LOGGER_NAME


@dataclass(frozen=True)
class MonitorInfo:
    """Immutable geometry descriptor for a single physical monitor.

    Attributes:
        index:  MSS monitor index (1-based; 0 is the virtual all-monitors
                bounding box and is never returned by discover_monitors).
        x:      Left edge in virtual screen coordinates (may be negative).
        y:      Top edge in virtual screen coordinates (may be negative).
        width:  Width in pixels (always positive).
        height: Height in pixels (always positive).
    """

    index: int
    x: int
    y: int
    width: int
    height: int

    @property
    def is_primary(self) -> bool:
        """True when this monitor contains the virtual-screen origin (0, 0).

        MSS does not expose a primary-monitor flag directly, so we use the
        conventional Windows definition: the monitor whose top-left corner
        is at (0, 0) is the primary monitor.
        """
        return self.x == 0 and self.y == 0


def discover_monitors() -> list[MonitorInfo]:
    """Return geometry for every physical monitor detected by MSS.

    MSS index 0 is the virtual bounding box covering all monitors; it is
    excluded from the returned list. Indices 1..N correspond to individual
    physical monitors.

    Negative coordinates are preserved as-is; they occur on multi-monitor
    setups where a secondary monitor is positioned to the left of or above
    the primary monitor.

    Returns:
        A list of MonitorInfo objects, one per physical monitor, ordered by
        MSS index. The list is empty if no monitors are detected.

    Raises:
        RuntimeError: If MSS cannot be initialised or monitor enumeration
                      fails. The caller is responsible for handling this.
    """
    logger = logging.getLogger(LOGGER_NAME)
    try:
        with _mss_module.mss() as screen_capture:
            # monitors[0] is the virtual all-monitors bounding box; skip it.
            monitors = [
                MonitorInfo(
                    index=index,
                    x=monitor["left"],
                    y=monitor["top"],
                    width=monitor["width"],
                    height=monitor["height"],
                )
                for index, monitor in enumerate(
                    screen_capture.monitors[1:], start=1
                )
            ]
        logger.info("monitors_discovered")
        return monitors

    except Exception:
        logger.error("monitor_discovery_failed", exc_info=True)
        raise RuntimeError(
            "Monitor discovery failed. MSS could not enumerate displays."
        )
