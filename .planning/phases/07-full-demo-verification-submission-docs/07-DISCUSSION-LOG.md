# Phase 7: Full Demo Verification & Submission Docs - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-09
**Phase:** 7-Full Demo Verification & Submission Docs
**Mode:** `--auto` (fully autonomous discuss; recommended option auto-selected per area)
**Areas discussed:** SC1 extension-dependency scoping, demo entrypoint, determinism proof, README, license, diagram, demo script

---

## SC1 scoping — Phase 4 (extension) dependency

| Option | Description | Selected |
|--------|-------------|----------|
| Scope demo to the integrated HTTP pipeline; extension front documented as Phase 4 dependency | "capture" = paste-to-`/capture`, exactly what the extension posts; deterministic capture→proposal→ops in one command | ✓ |
| Block Phase 7 until Phase 4 is built | Stalls the submission docs unnecessarily; a parallel session already owns other prereq work | |
| Fake an extension step | Violates honesty; never fabricate a manual boundary | |

**Auto-selected:** scope to the HTTP pipeline, document the extension front as a Phase 4 dependency. → D-01, D-07. (User explicitly chose Phase 7 over Phase 8 with this scoping surfaced.)

---

## Demo entrypoint

| Option | Description | Selected |
|--------|-------------|----------|
| `backend/scripts/run_demo.py` via FastAPI `TestClient`, in-process, deterministic | One command, no server, no creds, offline-repeatable | ✓ |
| Shell script driving a live `uvicorn` + curl | Adds a server + port + timing flakiness to the demo | |

**Auto-selected:** in-process TestClient driver (recommended default). → D-01.

---

## DEMO-02 determinism proof (SC2)

| Option | Description | Selected |
|--------|-------------|----------|
| `test_demo_determinism.py` runs the full fixture set 3× and asserts identical decision fields | Machine-checkable, joins the existing suite | ✓ |
| Manual "run it three times and eyeball it" | Not repeatable, not gated | |

**Auto-selected:** automated 3×-identical determinism test. → D-02.

---

## Architecture diagram (SC4)

| Option | Description | Selected |
|--------|-------------|----------|
| Mermaid in `docs/architecture.md`, built from real `backend/` symbols | Renders on GitHub, no binary, diffable, matches the object graph | ✓ |
| Exported PNG/SVG from a drawing tool | Binary, drifts from code, not diffable | |

**Auto-selected:** Mermaid diagram grounded in the real object graph. → D-05.

---

## License (DEMO-05)

| Option | Description | Selected |
|--------|-------------|----------|
| MIT `LICENSE` at repo root, copyright-holder user-adjustable, no email | Shortest OSI license; satisfies the About-section submission rule | ✓ |
| Apache-2.0 | Also permitted; longer, patent grant not needed for a demo | |

**Auto-selected:** MIT (recommended default); copyright-holder flagged as user-adjustable. → D-04.

## Claude's Discretion

- Demo-entrypoint CLI flags, determinism comparison subset, MIT copyright string, diagram detail,
  README section ordering, presence-test file layout.

## Deferred Ideas

- Chrome extension (Phase 4); real triage tools (Phase 2, parallel session); the recorded video
  (human); AgentCore (Phase 8).
