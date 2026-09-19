# Roadmap

The roadmap describes intended future work only. A phase is not implemented
merely because it appears here, and no later phase may begin without explicit
authorization.

| Phase | Status | Intended purpose |
|---|---|---|
| Phase 1 — Foundation | COMPLETE | Establish the Python desktop shell, configuration validation, local structured logging, honest UI status, and foundation tests. |
| Phase 2 — Screen Capture | IMPLEMENTED | MSS-based Windows screen capture, monitor discovery, region model, background QThread worker, latest-frame replacement policy. |
| Phase 3 — Change Detection | IMPLEMENTED | Pure-Python stride-based grayscale change detection, normalised MAD score, configurable threshold, bounded single-frame state. |
| Phase 4 — OCR | PLANNED | Add bounded local text extraction from authorized captured content. |
| Phase 5 — Ollama / Local AI | PLANNED | Integrate an explicitly local Ollama provider with lazy, cancellable, user-controlled requests. |
| Phase 6 — Vision | PLANNED | Add local image/vision interpretation for supported screen-analysis workflows. |
| Phase 7 — Context | PLANNED | Add bounded conversation and screen context with retention limits and privacy controls. |
| Phase 8 — Ghost Mode | PLANNED | Add background orchestration while preserving explicit status, cancellation, and user control. |
| Phase 9 — Desktop Overlay / Hotkeys / Tray | PLANNED | Add optional desktop interaction surfaces without autonomous clicking or typing. |
| Phase 10 — Voice | PLANNED | Add optional local speech-to-text and text-to-speech capabilities. |
| Phase 11 — Diagnostics | PLANNED | Add local diagnostics and performance measurements without telemetry. |
| Phase 12 — Testing / Hardening | PLANNED | Expand testing, failure handling, privacy checks, and security/performance hardening. |
| Phase 13 — Packaging | PLANNED | Prepare a controlled Windows distribution and installation process. |

All future phases must preserve the local-first model, treat screen content as
untrusted data, avoid autonomous computer control, and remain suitable for a
CPU-only laptop with approximately 16 GB RAM.
