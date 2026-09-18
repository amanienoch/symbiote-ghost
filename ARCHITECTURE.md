# Current Architecture

## Scope

SYMBIOTE GHOST is currently a Phase 1 Windows desktop foundation. The
implemented system is a local PySide6 shell with validated YAML configuration,
structured local logging, explicit unavailable-feature messaging, and a
read-only settings viewer. It does not capture or analyze the screen.

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

## Tests

The test suite uses Python `unittest`:

- `tests/test_config.py` covers defaults, strict validation, safe YAML,
  persistence, and size limits.
- `tests/test_logging_config.py` covers JSON output, rotation ownership, and
  suppression of sensitive exception data.
- `tests/test_ui.py` uses Qt's offscreen platform and covers honest status,
  unavailable controls, settings visibility, and window lifecycle.

## Current module boundaries

| Area | Current responsibility |
|---|---|
| `app` | Application lifecycle, configuration, and logging |
| `ui` | Phase 1 desktop shell and settings display |
| `capture` | Reserved for future screen capture |
| `vision` | Reserved for future OCR/image/vision processing |
| `ai` | Reserved for future local Ollama integration |
| `context` | Reserved for future bounded screen/conversation context |
| `ghost` | Reserved for future background orchestration |
| `desktop` | Reserved for future overlay, hotkeys, and tray |
| `audio` | Reserved for future local STT/TTS |
| `diagnostics` | Reserved for future diagnostics and measurements |

## Current limitations

Phase 1 does not capture screens, record audio, invoke AI, perform OCR,
analyze images, maintain a context engine, run background assistance, control
other applications, provide overlays/hotkeys/tray behavior, or package a
deployable application. Configuration flags for future subsystems are
preferences only and do not activate those subsystems.

## Future subsystems

The reserved boundaries above are intentional. Their implementation belongs to
the roadmap phases and must not be represented as current functionality before
the relevant phase is explicitly authorized.
