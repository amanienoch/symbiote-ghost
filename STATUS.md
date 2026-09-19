# Project Status

## Current phase

**Phase 3 — Change Detection — IMPLEMENTED**

## Previous phases

**Phase 1 — COMPLETE / LOCKED** (tag: `v0.1.0-foundation`)
**Phase 2 — Screen Capture — IMPLEMENTED**

## Currently implemented

### Phase 1 (COMPLETE / LOCKED)
- Python 3.14 desktop runtime
- PySide6 application shell
- Strict, safe YAML configuration loading and validation
- Per-user configuration creation and read-only settings viewing
- Structured rotating local JSON Lines logging
- Qt lifecycle and generic exception reporting
- Honest status indicators (GHOST MODE: OFF, AI: OFFLINE, SCREEN: READY)
- Foundation tests (17 tests)

### Phase 2 — Screen Capture
- `src/capture/__init__.py` — public API
- `src/capture/monitor.py` — `MonitorInfo` dataclass + `discover_monitors()`
- `src/capture/region.py` — `CaptureRegion` dataclass + `validate_region()`
- `src/capture/frame.py` — `CaptureFrame` dataclass (raw BGRA bytes)
- `src/capture/worker.py` — `CaptureWorker(QObject)` on `QThread`
  - MSS initialised once per run
  - `threading.Event` stop signal (interruptible interval sleep)
  - `threading.Lock` latest-frame slot (single replacement, no queue)
  - Signals: `capture_error`, `capture_started`, `capture_stopped`
  - Main-thread timer consumes at most the newest stored frame per tick
- `mss==9.0.2` dependency added
- `MainWindow` capture status slots: `slot_capture_started`, `slot_capture_stopped`, `slot_capture_error`
- SCREEN status card transitions: READY → ACTIVE → READY/ERROR

### Phase 3 — Change Detection
- `src/vision/__init__.py` — public API
- `src/vision/result.py` — `ChangeResult` dataclass (score, changed, metadata)
- `src/vision/detector.py` — `ChangeDetector`
  - Pure Python, no NumPy, no OpenCV
  - Stride-8 downsampling (1920×1080 → ~32,400 samples)
  - BT.601 grayscale conversion
  - Normalised MAD score in [0.0, 1.0]
  - First frame = baseline (changed=False, score=0.0)
  - Bounded single-frame state (O(1) memory)
  - Threshold from `config.screen.change_threshold`

## Currently not implemented

- OCR
- Ollama integration
- Vision (beyond change detection)
- Context engine
- Ghost Mode orchestration
- Desktop overlay
- Global hotkeys
- System tray behavior
- Voice
- Diagnostics
- Packaging

## Validated (Phase 2 + 3)

- Python 3.14.7
- `mss==9.0.2` installed successfully
- `compileall` passes (src + tests)
- All tests pass (17 original + new Phase 2/3 tests)
- `pip check` passes
- No Phase 4+ functionality implemented

## Lock constraints

Phase 1 source code, tests, and the `v0.1.0-foundation` tag must not be
modified. Phase 4 (OCR) and later phases must not begin without explicit
authorization. Preserve the local-first and privacy-focused behavior.
