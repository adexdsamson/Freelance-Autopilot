# Phase 7: Full Demo Verification & Submission Docs - Pattern Map

**Mapped:** 2026-09-09
**Files analyzed:** 7
**Analogs found:** 5 / 7 (2 flagged no-analog: LICENSE boilerplate, docs/architecture.md diagram)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/scripts/run_demo.py` | utility (CLI driver) | request-response (in-process HTTP via TestClient) | `backend/tests/conftest.py` (`client`/`file_store` fixtures) + `backend/tests/test_advance_endpoint.py` (call sequence) | role-match (test→script transposition) |
| `backend/tests/test_demo_determinism.py` | test | batch/repeated request-response | `backend/tests/test_advance_endpoint.py` (multi-stage /capture→/advance flow) | exact (same call shape, new assertion axis) |
| `backend/tests/test_submission_artifacts.py` | test | file-I/O (presence/content checks) | `backend/tests/test_single_writer.py` (repo-scanning `Path`/assert pattern) | role-match (static-scan test, not AST but same repo_root convention) |
| `README.md` | config/doc | n/a | `docs/PRD.md`, `docs/COLLABORATION.md` (tone/section structure); `backend/api.py` module docstring (accurate command/path sourcing) | role-match (doc, no code analog) |
| `LICENSE` | config | n/a | none — standard MIT text | no analog |
| `docs/architecture.md` | config/doc (Mermaid diagram) | n/a | none in repo; ground truth is `backend/agents/supervisor.py` + `backend/api.py` object graph | no analog (content grounded in real symbols, not copied from a file) |
| `docs/demo-script.md` | config/doc | n/a | `backend/scripts/run_demo.py` (D-01, itself new) + `backend/fixtures/` fixture names | role-match (doc referencing the new CLI's contract) |

## Pattern Assignments

### `backend/scripts/run_demo.py` (utility, request-response via TestClient)

**Analog:** `backend/tests/conftest.py` fixtures + `backend/tests/test_advance_endpoint.py::test_advance_ops_after_proposal_completes_both_stages`

**TestClient + store-override pattern** (`backend/tests/conftest.py` lines 1-28):
```python
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from store.file_engagement_store import FileEngagementStore

@pytest.fixture
def file_store(tmp_path: Path) -> FileEngagementStore:
    return FileEngagementStore(base_dir=tmp_path)

@pytest.fixture
def client(file_store: FileEngagementStore):
    from api import app, get_store
    app.dependency_overrides[get_store] = lambda: file_store
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
```
`run_demo.py` should reuse this exact "build TestClient(app) in-process" seam — import `app` from `api`, construct `TestClient(app)` directly (no dependency override needed for a real demo run since it should exercise the real default `FileEngagementStore` under `backend/data/engagements/`, OR override `get_store` to a temp/demo-scoped dir if the script must be side-effect-free; either way it must NOT import `store` module logic itself — it only talks to the app via HTTP-shaped calls, preserving REC-03/single-writer since api.py remains the only store writer).

**Full three-stage call sequence to mirror** (`backend/tests/test_advance_endpoint.py` lines 135-176):
```python
capture_response = client.post("/capture", json={"title": ..., "description": ..., "budget": ...})
engagement_id = capture_response.json()["engagement_id"]

proposal_response = client.post(f"/engagements/{engagement_id}/advance", params={"stage": "proposal"})

ops_response = client.post(
    f"/engagements/{engagement_id}/advance",
    params={"stage": "ops", "fixture": "creep"},
)
ops_body = ops_response.json()
# ops_body["ops"]["scope_creep_flags"], ["invoice_flags"], ["status_updates"]

get_response = client.get(f"/engagements/{engagement_id}")
```
`run_demo.py` should print `capture_response.json()` (verdict/score/reasoning), then `proposal_response.json()["proposal"]`/`["contract"]`, then `ops_response.json()["ops"]`, and support a `fixture` selector CLI arg mapping to job payloads (reuse `backend/fixtures/loader.py`'s existing sample job/thread payloads rather than inventing new inline dicts — check `backend/fixtures/loader.py` for the loader's public functions before writing the driver).

**Script/CLI shape (existing `backend/scripts/` convention)** — from `backend/scripts/smoke_test_agents_as_tools.py` lines 43-75: separate a `build_*()`/pure-construction function from a `main()` that performs the actual run and asserts/prints, guarded by `if __name__ == "__main__": main()`. Follow this same construction/invocation split in `run_demo.py` (e.g., `build_client()` / `run_pipeline(client, fixture)` / `main()` with `argparse` for the fixture selector), and keep module-level docstring explaining what it does NOT do (does not add a second store writer, does not require AWS creds by default).

**Constraint (REC-03 / D-01):** `run_demo.py` MUST NOT `import store` or any `store.*` module directly — it only calls through `api.app` via `TestClient`, exactly like `conftest.py`'s `client` fixture. This will be verified against `backend/tests/test_single_writer.py`'s scan if `backend/scripts/` is ever added to `SCAN_DIRS` — even if not currently scanned, honor the convention for consistency.

---

### `backend/tests/test_demo_determinism.py` (test, batch/repeated request-response)

**Analog:** `backend/tests/test_advance_endpoint.py` (imports, `client`/`file_store` fixture usage, full-pipeline call shape shown above)

**Imports pattern** (`backend/tests/test_advance_endpoint.py` lines 1-7):
```python
from uuid import uuid4
from api import app, get_proposal_runner
from models.engagement_record import EngagementRecord, JobSlice, ProposalContractResult
```

**Pattern to apply:** run the same capture→advance(proposal)→advance(ops) sequence **three times** (fresh `engagement_id` each time, or three separate `client` fixture instances via `tmp_path`-scoped stores per run — reuse `file_store`/`client` fixtures from `conftest.py`), collect the three response bodies' decision-relevant subsets (`triage.verdict`, `triage.score`, `triage.reasoning`, `proposal.text`/`needs_human_input`/`question`, `contract.text`/`payment_schedule`, `ops.scope_creep_flags`/`invoice_flags`/`status_updates`), and assert all three are equal — explicitly excluding `engagement_id` (UUID, fresh per run) and any timestamp fields from the comparison, per D-07(a)/Specific Idea note. A `dict` comparison after stripping non-deterministic keys, or comparing `model_dump(exclude={"engagement_id"})`-style subsets, matches the project's Pydantic-model-first convention seen in `models/engagement_record.py`.

**Should iterate the fixture set** — per D-02, "runs the full fixture set three times"; check `backend/fixtures/sample_upwork_jobs.json` and `backend/fixtures/loader.py` for the enumerable fixture list to loop over, rather than hardcoding one job payload three times.

---

### `backend/tests/test_submission_artifacts.py` (test, file-I/O presence checks)

**Analog:** `backend/tests/test_single_writer.py` (repo-root discovery pattern)

**Repo-root resolution pattern** (`backend/tests/test_single_writer.py` lines 27-29):
```python
def test_no_agent_or_tool_module_imports_store():
    # backend/ — this test file's parent's parent.
    repo_root = Path(__file__).resolve().parent.parent
```
Note: `test_single_writer.py`'s `repo_root` resolves to `backend/`, not the actual repo root — for `test_submission_artifacts.py`, which must check repo-ROOT `README.md`/`LICENSE` (not `backend/`-relative), use one more `.parent`:
```python
repo_root = Path(__file__).resolve().parent.parent.parent  # repo root, not backend/
readme = repo_root / "README.md"
license_file = repo_root / "LICENSE"
assert readme.exists()
assert license_file.exists()
assert "MIT" in license_file.read_text()
docs_dir = repo_root / "docs"
assert (docs_dir / "architecture.md").exists()
assert "```mermaid" in (docs_dir / "architecture.md").read_text()
assert (docs_dir / "demo-script.md").exists()
```
Follow `test_single_writer.py`'s style: plain `pathlib.Path` + `assert ... , "message"` with a requirement-ID comment header (e.g., `"""DEMO-03/DEMO-04/DEMO-05/D-07(c)(d): presence tests for submission artifacts."""`), no AST needed here since this is presence/substring checking, not import-graph analysis — don't over-engineer with `ast` module (that pattern is specific to `test_single_writer.py`'s import-scanning need).

---

### `README.md` (doc, repo root)

**Analog:** `docs/PRD.md` / `docs/COLLABORATION.md` for structure/tone; `backend/api.py`'s module docstring (lines 1-32) for accurate command/endpoint naming — the README's "run instructions" and "architecture overview" sections must name real endpoints/paths exactly as they appear in `api.py` (`/capture`, `GET /engagements/{engagement_id}`, `POST /engagements/{engagement_id}/advance?stage=proposal|ops`), not paraphrased.

Section skeleton driven by D-03: one-line value prop → architecture overview (linking `docs/architecture.md`) → setup (`Python 3.10+`, `pip install -r backend/requirements.txt`, optional AWS-credential note for `*_BACKEND=supervisor`) → run instructions (`python backend/scripts/run_demo.py`, `uvicorn api:app --reload` from within `backend/`) → test instructions (`cd backend && python3 -m pytest`) → requirements-traceability table (pull requirement IDs like DEMO-02/03/04/05, ORC-01/02, REC-03, API-03 from `docs/PRD.md`) → documented manual-only boundaries (Chrome extension Phase 4, recorded video, live Bedrock).

Verify exact run commands against `backend/requirements.txt` and how `uvicorn` is invoked elsewhere (check for a `backend/requirements.txt` and any existing run-instructions in `docs/PRD.md` before finalizing wording).

---

### `LICENSE` (repo root)

**No analog** — standard MIT license text. Use `Copyright (c) 2026 Freelance Autopilot` per D-04 (flagged as user-adjustable, no email address).

---

### `docs/architecture.md` (Mermaid diagram)

**No direct analog file**, but the diagram content must be grounded in real symbols verified in this pass:
- `backend/api.py`: `app = FastAPI()`, endpoints `/capture`, `GET /engagements/{engagement_id}`, `POST /engagements/{engagement_id}/advance?stage=proposal|ops` — sole store writer (`get_store()` → `FileEngagementStore`).
- `backend/agents/supervisor.py`: `build_full_supervisor()` (lines 121-176) wires `gig_triage_agent`, `proposal_contract_agent`, `ops_agent` as `.as_tool(..., delegate=True)` into one Supervisor `Agent` — this is the ORC-01 node to depict as the center of the diagram, with three specialist tool nodes hanging off it.
- `backend/agents/{triage_runner,proposal_runner,ops_runner}.py`: the DI seams `api.py` actually depends on (`get_triage_runner`, `get_proposal_runner`, `get_ops_runner`), deterministic-default + `*_BACKEND=supervisor` env-switch — confirm exact env var names inside these three files before drawing (not verified in this pass; read them before writing the diagram).
- `backend/store/{engagement_store.py,file_engagement_store.py}`: `EngagementStore` (interface) / `FileEngagementStore` (impl) as the single persistence node, written to ONLY by `api.py`.
- MV3 extension: draw as dashed/planned (Phase 4, not built).

---

### `docs/demo-script.md` (walkthrough script)

**No direct analog**, grounded in:
- `backend/scripts/run_demo.py` (D-01, this phase) as the exact command every beat runs.
- `backend/fixtures/sample_client_thread.json` (creep) vs `sample_client_thread_clean.json` (clean) and `sample_payment_schedule.json` vs `_clean.json` for the "2 escalation cards" vs "0 ops cards" beats (D-06) — confirm field-level content against `backend/fixtures/loader.py` before writing exact card counts/text into the script.
- An ambiguous proposal fixture triggering `needs_human_input` — mirrors `backend/tests/test_advance_endpoint.py::test_advance_ambiguous_scope_escalates_and_round_trips` (job description `"Looking for someone to help with ongoing design work."` triggers escalation) — reuse this exact same input text for the demo-script beat 3, since it's already proven deterministic in the test suite.

## Shared Patterns

### Repo-root / backend-root Path resolution
**Source:** `backend/tests/test_single_writer.py` lines 27-29
**Apply to:** `test_submission_artifacts.py` — note the off-by-one: `test_single_writer.py`'s `repo_root` (parent.parent from the test file) actually lands on `backend/`, so `test_submission_artifacts.py` needs one extra `.parent` to reach the true repo root where `README.md`/`LICENSE`/`docs/` live.

### Single-writer / REC-03 constraint
**Source:** `backend/tests/test_single_writer.py` (enforcement), `backend/api.py` module docstring line 31 ("api.py is the ONLY module in this codebase that imports the store")
**Apply to:** `backend/scripts/run_demo.py` — must talk to the store exclusively through `TestClient(app)` HTTP calls, never `import store`.

### TestClient + fixture-driven pytest pattern
**Source:** `backend/tests/conftest.py` (`file_store`, `client` fixtures)
**Apply to:** `test_demo_determinism.py` (and optionally `run_demo.py`, if it chooses to reuse pytest fixtures via direct construction rather than a bare script — though a standalone CLI script will likely construct `TestClient(app)` directly rather than depending on pytest fixtures, since it must run outside pytest).

### Requirement-ID doc-comment convention
**Source:** every existing test file's module docstring (e.g. `test_single_writer.py` lines 1-8, `test_advance_endpoint.py` line 1, `smoke_test_agents_as_tools.py` lines 1-27) cites requirement IDs (REC-03, D-05, API-03, SC1/SC2, etc.) inline
**Apply to:** all four new/modified files in this phase — `run_demo.py`, `test_demo_determinism.py`, `test_submission_artifacts.py` should each open with a docstring citing DEMO-02/DEMO-03/DEMO-04/DEMO-05/SC1-SC4/D-01..D-07 as appropriate, matching the codebase's dense traceability-comment convention.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `LICENSE` | config | n/a | Standard MIT boilerplate text, not a code pattern; no codebase analog expected or needed |
| `docs/architecture.md` | doc (diagram) | n/a | No existing diagram in repo; content is derived directly from the real object graph in `backend/api.py` + `backend/agents/supervisor.py` + `backend/store/`, not copied from an analog file |

## Metadata

**Analog search scope:** `backend/tests/`, `backend/scripts/`, `backend/api.py`, `backend/agents/supervisor.py`, `backend/store/`, `docs/`
**Files scanned:** `backend/tests/test_advance_endpoint.py`, `backend/tests/test_single_writer.py`, `backend/tests/conftest.py`, `backend/scripts/smoke_test_agents_as_tools.py`, `backend/api.py`, `backend/agents/supervisor.py`, directory listings of `backend/fixtures/`, `backend/agents/`, `backend/store/`, `backend/models/`
**Pattern extraction date:** 2026-09-09
**Verify-before-write flags:** `backend/agents/{triage_runner,proposal_runner,ops_runner}.py` env-var names for `*_BACKEND=supervisor` switch were NOT read in this pass — read them before finalizing `docs/architecture.md` and the README's live-path note. `backend/fixtures/loader.py`'s public function signatures were NOT read — read before writing `run_demo.py`'s fixture-selection logic and `docs/demo-script.md`'s exact card-count claims. `backend/requirements.txt` existence/exact pip command was NOT verified — confirm before writing README setup section.
