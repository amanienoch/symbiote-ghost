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
