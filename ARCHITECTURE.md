# Current Architecture

## Scope

SYMBIOTE GHOST is a local-first Windows desktop screen assistant implemented
in controlled phases. Phases 1, 2, and 3 are complete. The system provides a
PySide6 desktop shell, validated YAML configuration, structured local logging,
real Windows screen capture via MSS, and CPU-efficient frame change detection.
No OCR, AI, or cloud integration is implemented.

## Runtime and entry point

- `src/main.py` provides the `python -m src.main` entry point.
- Argument parsing supports `--config` for an explicitly existing YAML file
  and `--version`.
- `src/app/application.py` creates and owns the `QApplication`, applies the
  application identity and stylesheet, loads configuration, creates the main
  window, runs the Qt event loop, and performs orderly shutdown.
- `ExceptionBridge` forwards uncaught system and thread exceptions to the Qt
  thread, records a privacy-conscious critical event, displays a generic
  error, and exits.
- The PowerShell scripts create/use `.venv` and launch the application; they
  do not implement application features.

## Configuration

`src/app/config.py` defines immutable dataclasses for:

- AI provider and model names
- screen interval and change threshold preferences
- Ghost Mode preference
- OCR preference
- voice preference
- screenshot persistence preference

Configuration is loaded from YAML using a strict safe loader. Duplicate keys,
non-string keys, unsafe YAML tags, unknown sections/settings, invalid types,
unsupported providers, non-finite numbers, out-of-range values, invalid UTF-8,
and files larger than 64 KiB are rejected with `ConfigError`.

Without `--config`, the application uses a per-user configuration under
`%LOCALAPPDATA%\SYMBIOTE-GHOST\config.yaml` and creates it only when missing.
An explicitly selected missing or invalid file is not silently repaired.
`config/default.yaml` is the repository reference configuration.

## Logging

`src/app/logging_config.py` configures the `symbiote` logger with a rotating
JSON Lines file at the per-user logs directory. The active file is limited to
1 MiB with three backups. The formatter records timestamps, levels, fixed
event messages, and exception type names, while excluding exception messages,
tracebacks, locals, and arbitrary extra fields.

Application startup, configuration loading/failure, window lifecycle,
unavailable feature actions, and shutdown are represented by fixed event names.

## User interface

`src/ui/main_window.py` contains the Phase 1 desktop shell:

- `MainWindow` displays the SYMBIOTE GHOST branding and status cards.
- Status is intentionally `GHOST MODE: OFF`, `AI: OFFLINE`, and
  `SCREEN: READY`.
- Analyze Screen and Ghost Mode show explanations that the features are not
  implemented and do not collect data or activate processing.
- `SettingsDialog` displays effective YAML and the loaded path as read-only
  views.
- The stylesheet and labels communicate local-first behavior and the absence
  of autonomous computer control.

## Phase 2 — Screen Capture (`src/capture/`)

The capture package implements Windows screen capture using MSS. It is
separated from the UI and designed so that later phases can consume frames.

### Modules

- `src/capture/monitor.py` — `MonitorInfo` frozen dataclass (index, x, y,
  width, height) and `discover_monitors()`. Handles negative coordinates
  correctly; does not assume the primary monitor starts at (0, 0).
- `src/capture/region.py` — `CaptureRegion` frozen dataclass (x, y, width,
  height) and `validate_region()` with bounds checking against a monitor.
- `src/capture/frame.py` — `CaptureFrame` frozen dataclass (timestamp,
  monitor_index, region, width, height, raw: bytes). Raw BGRA bytes from MSS.
  Never logged, persisted, or transmitted.
- `src/capture/worker.py` — `CaptureWorker(QObject)` runs on a dedicated
  `QThread`. MSS is initialised once per run. A `threading.Event` provides
  interruptible interval sleep. A `threading.Lock` protects the single
  `_latest_frame` slot (latest-frame replacement policy). Emits lifecycle and
  error signals: `capture_error`, `capture_started`, and `capture_stopped`.

### Capture pipeline

```
Windows Screen
      ↓
MSS (initialised once per CaptureWorker.run_capture() call)
      ↓
CaptureFrame (frozen dataclass, raw BGRA bytes, UTC timestamp)
      ↓
_latest_frame slot (single slot, Lock-protected, newest replaces oldest)
      ↓
QTimer polls take_latest_frame() → ChangeDetector.process()
```

### Latest-frame policy

The worker maintains exactly one `_latest_frame` slot. If downstream
processing falls behind, the newest frame replaces the previous one. No queue
accumulates. Memory usage is bounded to approximately one frame buffer.

### Worker lifecycle

```
CREATED → (QThread.start() + run_capture slot) → RUNNING → (stop()) → STOPPED
```

`stop()` sets a `threading.Event`. The capture loop's `Event.wait(timeout)`
exits immediately, avoiding a busy loop. The `capture_stopped` signal is
emitted when the loop exits.

## Phase 3 — Change Detection (`src/vision/`)

The vision package implements CPU-efficient frame change detection. It is
pure Python with no NumPy, no OpenCV, and no external dependencies beyond
the Phase 2 capture package.

### Modules

- `src/vision/result.py` — `ChangeResult` frozen dataclass (timestamp,
  monitor_index, region, change_score: float, changed: bool).
- `src/vision/detector.py` — `ChangeDetector`: stride-based pixel sampling,
  BT.601 grayscale conversion, normalised MAD score, threshold comparison.
  Maintains exactly one `_previous_frame` reference (bounded state).

### Change-detection algorithm

```
CaptureFrame (raw BGRA bytes)
      ↓
Stride-based downsampling (every 8th pixel in x and y)
      ↓
BT.601 grayscale: Y = R×0.299 + G×0.587 + B×0.114
      ↓
Mean Absolute Difference (MAD) vs previous frame's samples
      ↓
Normalise: score = MAD / 255  →  [0.0, 1.0]
      ↓
Compare against config.screen.change_threshold (default 0.08)
      ↓
ChangeResult (score, changed bool, metadata)
```

### First-frame behaviour

The first frame passed to `ChangeDetector.process()` establishes the baseline.
It returns `changed=False` and `change_score=0.0`. Every subsequent frame is
compared against the most recently processed frame.

### Bounded state

The detector retains exactly one `_previous_frame` reference and one
`_previous_samples` list. There is no history, no queue, and no accumulation.

## Application wiring (`src/app/application.py`)

`run_application()` creates a `CaptureWorker` and a `ChangeDetector`, moves
the worker to a `QThread`, connects signals to `MainWindow` slots, starts the
thread after the window is shown, and stops it cleanly on `aboutToQuit`.

The `ChangeDetector` is called by a main-thread `QTimer` at the configured
capture interval. Each tick retrieves at most one frame with
`take_latest_frame()`, so stale frames are discarded before processing and no
per-frame Qt signal backlog can accumulate. The detector is not shared across
threads.

## Tests

The test suite uses Python `unittest`:

- `tests/test_config.py` — defaults, strict validation, safe YAML,
  persistence, and size limits (10 tests).
- `tests/test_logging_config.py` — JSON output, rotation, and suppression of
  sensitive exception data (2 tests).
- `tests/test_ui.py` — offscreen Qt: honest status, unavailable controls,
  settings visibility, window lifecycle (5 tests).
- `tests/test_capture.py` — Phase 2: MonitorInfo geometry, negative
  coordinates, CaptureRegion validation, CaptureFrame construction, worker
  lifecycle, latest-frame policy, configuration integration, clean shutdown.
  All tests use mocked MSS; no physical monitor required.
- `tests/test_vision.py` — Phase 3: first-frame baseline, identical frames,
  small/large differences, threshold control, metadata preservation, bounded
  state. All tests use synthetic BGRA frames; fully deterministic.

## Current module boundaries

| Area | Current responsibility |
|---|---|
| `app` | Application lifecycle, configuration, and logging |
| `ui` | Desktop shell, settings display, and capture status slots |
| `capture` | MSS screen capture, monitor discovery, region validation, frame model, background worker |
| `vision` | Frame change detection, change result model |
| `ai` | Reserved for future local Ollama integration |
| `context` | Reserved for future bounded screen/conversation context |
| `ghost` | Reserved for future background orchestration |
| `desktop` | Reserved for future overlay, hotkeys, and tray |
| `audio` | Reserved for future local STT/TTS |
| `diagnostics` | Reserved for future diagnostics and measurements |

## Current limitations

Phases 1–3 do not perform OCR, invoke AI, maintain a context engine, run
background assistance, control other applications, provide overlays/hotkeys/
tray behavior, or package a deployable application. Screen capture runs on
the primary monitor only in Phase 2. Multi-monitor and region selection are
supported by the data model but not yet exposed in the UI.

## Future subsystems

The reserved boundaries above are intentional. Their implementation belongs to
the roadmap phases and must not be represented as current functionality before
the relevant phase is explicitly authorized.
