# SYMBIOTE GHOST

A local-first Windows desktop screen assistant, implemented in controlled
phases.

## Current stage

Phase 3: change detection (Phases 1, 2, and 3 complete).

The application provides a PySide6 desktop shell, validated YAML
configuration, rotating JSON Lines logs, real Windows screen capture via MSS,
CPU-efficient frame change detection, and a read-only settings viewer.

OCR, Ollama integration, Ghost Mode, overlays, global hotkeys, and voice are
not implemented.

## Requirements

| Requirement | Target |
|---|---|
| Operating system | Windows 10 or Windows 11 |
| Python | CPython 3.14, 64-bit |
| Memory | Target machine has 16 GB |
| GPU | Not required |
| Runtime AI server | Not required for Phase 1 |

## Quick start

From the project root:

```powershell
.\setup.ps1
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\run.ps1
```

Alternatively, after activating the virtual environment:

```powershell
python -m src.main
```

See SETUP.md for installation without PowerShell scripts.

## Status semantics

| Display | Meaning |
|---|---|
| GHOST MODE: OFF | No background processing pipeline exists |
| AI: OFFLINE | No AI provider is connected or probed |
| SCREEN: READY | Capture subsystem ready; not yet started or stopped |
| SCREEN: ACTIVE | MSS capture loop is running on the background thread |
| SCREEN: ERROR | A capture error occurred; see the log file |

Analyze Screen and Ghost Mode display availability explanations.
They do not collect data or activate anything.

Settings displays the loaded configuration and its file path.
It does not edit settings.

## Configuration

Normal startup creates this file if it is missing:

```text
%LOCALAPPDATA%\SYMBIOTE-GHOST\config.yaml
```

Close the application before editing it, then restart.

The repository contains a reference configuration:

```text
config/default.yaml
```

To use that file explicitly:

```powershell
.\.venv\Scripts\python.exe -m src.main --config .\config\default.yaml
```

An explicitly selected configuration must already exist.

Unknown fields, duplicate keys, invalid YAML, invalid types, unsupported
providers, and out-of-range numbers are rejected. Existing invalid files
are not automatically overwritten.

Missing sections and settings receive defaults. An empty document is
invalid; use `{}` for a configuration containing only defaults.

Capture interval accepts 0.25 through 3600 seconds.
Change threshold accepts 0 through 1.

Configuration flags for future subsystems do not activate those
subsystems in Phase 1.

## Privacy and security

The running Phase 1 application makes no network requests.

It does not capture screens, record audio, invoke AI, collect telemetry,
or control other applications. Its persistent output consists of user
configuration and operational logs.

The setup script downloads Python dependencies through pip only when
explicitly run by the user.

Logs contain fixed operational event names and exception types.
Application code must never pass screen text, prompts, responses, window
titles, or sensitive values as log messages or formatting arguments.

The formatter excludes arbitrary extra fields and exception messages.
This is not a general-purpose redaction engine.

## Logs

Default location:

```text
%LOCALAPPDATA%\SYMBIOTE-GHOST\logs\application.jsonl
```

Log rotation uses a 1 MiB active file and three backups.

## Shutdown

Closing the main window exits the application. There is no hidden tray
mode in this phase.

The application restores Python exception hooks and flushes its log
handlers during shutdown.

## Development

Run the automated foundation suite:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Check syntax compilation and installed dependencies:

```powershell
.\.venv\Scripts\python.exe -m compileall -q src tests
.\.venv\Scripts\python.exe -m pip check
```

The UI tests use Qt's offscreen platform. They do not validate actual
Windows rendering, scaling, accessibility, or window-manager behavior.

No lint or static type-check pass is claimed. These checks should be
added and run as the project develops.

## Next phase

Phase 4 introduces bounded local OCR on changed frames.

Do not treat Phases 1–3 as a functioning screen-analysis assistant.
Change detection identifies that the screen changed; it does not read or
interpret screen content.
