# Architectural Decisions

## Decision 001 — Python 3.14 runtime

**Status:** Accepted  
**Decision:** The project runtime is 64-bit CPython 3.14.  
**Reason:** The controlled environment update moved setup and documentation to
Python 3.14, matching the validated machine runtime.

## Decision 002 — PySide6 6.10.1 pin

**Status:** Accepted  
**Decision:** PySide6 is pinned to `6.10.1`.  
**Reason:** The previous `6.8.3` pin does not support Python 3.14. Version
`6.10.1` provides the required compatible Windows wheel without a broad
dependency upgrade.

## Decision 003 — PyYAML 6.0.3 pin

**Status:** Accepted  
**Decision:** PyYAML is pinned to `6.0.3`.  
**Reason:** This version provides a native Python 3.14 Windows wheel while
preserving the existing YAML configuration implementation.

## Decision 004 — Phase 1 is locked

**Status:** Accepted  
**Decision:** Phase 1 remains locked after successful validation.  
**Reason:** The foundation has been validated and must remain stable while the
project transitions deliberately to the next authorized phase.

## Decision 005 — Local-first operation

**Status:** Accepted  
**Decision:** The system is local-first and privacy-focused.  
**Reason:** Screen assistance must not depend on cloud AI, telemetry, hidden
analytics, or screenshot uploads.

## Decision 006 — No screenshot persistence by default

**Status:** Accepted  
**Decision:** Screenshots are not persisted by default.  
**Reason:** The default privacy posture minimizes retention of sensitive screen
content. Any future change must be explicit, bounded, and user-controlled.

## Decision 007 — Screen content is untrusted data

**Status:** Accepted  
**Decision:** Screen contents must be treated as untrusted data.  
**Reason:** Screen text and images can contain arbitrary or adversarial content
and must not become trusted instructions, unsafe log data, or autonomous
actions.

## Decision 008 — No model call per captured frame

**Status:** Accepted  
**Decision:** Future AI/model calls must not happen on every captured frame.  
**Reason:** Per-frame inference is unnecessary for a CPU-only target and would
  create avoidable latency, resource use, and privacy exposure.

## Decision 009 — Bounded asynchronous future processing

**Status:** Accepted  
**Decision:** Future processing should use asynchronous workers, bounded
queues, latest-frame replacement, caching, deduplication, and cancellation
where appropriate.  
**Reason:** The target machine has approximately 16 GB RAM, integrated
graphics, and no dedicated GPU. Processing must remain responsive and bounded.

## Decision 010 — MSS for Windows screen capture

**Status:** Accepted
**Decision:** MSS (`mss==9.0.2`) is used for Windows screen capture.
**Reason:** MSS is a lightweight, pure-Python-compatible screen capture
library with no mandatory NumPy or OpenCV dependency. It provides direct
access to raw BGRA pixel bytes, supports multi-monitor setups with negative
coordinates, and has a simple context-manager API that initialises once per
capture session. It is the minimal dependency that satisfies Phase 2
requirements without pulling in heavy computer-vision libraries.

## Decision 011 — QObject-on-QThread worker pattern

**Status:** Accepted
**Decision:** `CaptureWorker` is a `QObject` moved to a `QThread`, not a
`QThread` subclass.
**Reason:** The QObject-on-QThread pattern ensures that Qt signals emitted
by the worker are delivered on the correct thread via the event loop. It
avoids the pitfalls of subclassing `QThread` (where slots would run on the
wrong thread). The worker's `run_capture` slot is connected to
`QThread.started` and executes on the worker thread. Signals to `MainWindow`
slots are delivered on the main thread via Qt's queued connection mechanism.

## Decision 012 — Latest-frame replacement policy

**Status:** Accepted
**Decision:** The capture worker maintains a single `_latest_frame` slot
protected by a `threading.Lock`. New frames atomically replace the previous
one; no queue accumulates.
**Reason:** The target machine (16 GB RAM, Intel UHD 620, CPU-only) cannot
afford unbounded frame accumulation. If downstream processing falls behind,
keeping the newest frame and discarding stale ones is the correct behaviour
for a screen-assistance use case. A queue would accumulate stale screenshots
and waste memory. The single-slot policy bounds memory to approximately one
frame buffer at all times.

## Decision 013 — Pure-Python stride-based change detection

**Status:** Accepted
**Decision:** Frame change detection uses pure Python with no NumPy and no
OpenCV. Frames are downsampled by sampling every 8th pixel in both x and y,
converted to grayscale using BT.601 coefficients, and compared using mean
absolute difference normalised to [0.0, 1.0].
**Reason:** NumPy and OpenCV are heavy dependencies that are not justified
for a simple pixel-comparison task on a CPU-only laptop. The stride-based
approach reduces a 1920×1080 frame to ~32,400 samples, which a pure-Python
loop processes in well under 100 ms. This is sufficient for the 2-second
default capture interval. Adding NumPy would save perhaps 10–50 ms per frame
at the cost of a large binary dependency and increased attack surface.

## Decision 014 — Bounded single-frame detector state

**Status:** Accepted
**Decision:** `ChangeDetector` retains exactly one `_previous_frame`
reference and one `_previous_samples` list. There is no history, no queue,
and no accumulation of frames.
**Reason:** The detector only needs the immediately preceding frame to
compute a change score. Retaining more frames would waste memory without
improving detection quality. The single-reference policy ensures that memory
usage is O(1) regardless of how long the application runs.
