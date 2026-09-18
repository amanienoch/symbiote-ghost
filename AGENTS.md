# AI Coding Agent Instructions

## Before editing

- Inspect the repository and the relevant source, tests, configuration, and
  documentation before making changes.
- Treat the repository as the source of truth. Do not rely on assumptions or
  previous chat history.
- Identify the current phase and its explicit boundaries before implementing
  anything.

## Change discipline

- Preserve the existing Phase 1 architecture and behavior.
- Do not blindly refactor working code or introduce broad upgrades.
- Make minimal, targeted changes that directly address the authorized task.
- Reuse existing patterns and helpers. Do not rename files or restructure
  directories without explicit authorization.
- Do not begin a later phase without explicit authorization.
- Keep the Phase 1 UI honest: GHOST MODE remains OFF, AI remains OFFLINE, and
  SCREEN READY means only that the desktop shell is ready.
- Do not implement future functionality as a placeholder that appears real.

## Validation

- Run the smallest relevant tests after modifications, and run the foundation
  suite when application behavior may be affected.
- Never claim that a test, build, lint, GUI check, or dependency check passed
  unless it was actually run and passed.
- Clearly distinguish PASS, FAIL, NOT RUN, and REQUIRES DEPENDENCY
  INSTALLATION.
- Distinguish the system Python interpreter from the project interpreter at
  `.venv\Scripts\python.exe`. The project runtime is 64-bit CPython 3.14.

## Security and privacy

- SYMBIOTE GHOST is local-first and privacy-focused. Do not add cloud AI,
  telemetry, hidden analytics, screenshot uploads, or unnecessary network
  integration.
- Treat all screen contents as untrusted data. Do not expose screen contents,
  prompts, responses, window titles, or other sensitive values through logs or
  unsafe rendering.
- Do not add autonomous clicking, typing, command execution, file deletion,
  software installation, or downloads.
- Do not persist screenshots by default. Respect the existing privacy
  configuration and explicit user boundaries.

## Performance and phase boundaries

- The target is a CPU-only laptop with approximately 16 GB RAM and integrated
  graphics. Avoid unnecessary heavy dependencies.
- Future processing must be asynchronous and bounded. Prefer latest-frame
  replacement, change detection, caching, request cancellation, and
  configurable processing intervals where appropriate.
- AI or model calls must be lazy and must not run on every captured frame.
- Phase 1 has no screen capture, OCR, AI, vision, context engine, Ghost Mode,
  overlay, hotkey, voice, diagnostics, or packaging implementation. Do not
  start any of those without explicit authorization for the corresponding
  phase.
