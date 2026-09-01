---
phase: 01-foundations-engagement-record-strands-bedrock-verification-spike
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/pyproject.toml
  - backend/requirements.txt
  - backend/models/__init__.py
  - backend/models/engagement_record.py
  - backend/store/__init__.py
  - backend/store/engagement_store.py
  - backend/store/file_engagement_store.py
  - backend/agents/__init__.py
  - backend/tools/__init__.py
  - backend/scripts/__init__.py
  - backend/scripts/smoke_test_agents_as_tools.py
  - backend/scripts/smoke_test_bedrock_connectivity.py
  - backend/tests/__init__.py
  - backend/tests/conftest.py
  - backend/tests/test_engagement_record.py
  - backend/tests/test_store.py
  - backend/tests/test_single_writer.py
  - backend/tests/test_agents_as_tools_smoke.py
  - backend/tests/test_bedrock_smoke.py
  - .gitignore
autonomous: true
requirements: [REC-01, REC-02, REC-03, ORC-03]

user_setup:
  - service: aws-bedrock
    why: "Optional — a live Bedrock completion (the success path of the connectivity smoke test) needs real AWS credentials with Claude model access. This phase PASSES without them via the fail-fast path (D-08); real validation is a manual, later-environment step."
    env_vars:
      - name: BEDROCK_MODEL_ID
        source: "AWS Bedrock console -> Model access -> the enabled inference-profile Claude id (e.g. us.anthropic.claude-sonnet-4-6). Code default is a placeholder to be confirmed against the account."
      - name: AWS_REGION
        source: "The region where Bedrock model access was granted (e.g. us-east-1)."
      - name: AWS_ACCESS_KEY_ID
        source: "AWS credentials with bedrock:InvokeModel permission (or via aws configure / instance role)."
      - name: AWS_SECRET_ACCESS_KEY
        source: "Paired secret for the access key above."

estimate:
  tokens: 42000
  raw_tokens: 42000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "A developer can create, save, and reload an EngagementRecord by engagement_id through EngagementStore and get back an equivalent Pydantic object (REC-01, REC-02, D-01/D-03)."
    - "The store has exactly one writer seam: no module under backend/agents/ or backend/tools/ imports the store module (REC-03, D-05)."
    - "The throwaway agents-as-tools supervisor constructs with a distinct @tool-wrapped specialist registered against the pinned strands-agents==1.54.0, and with live creds shows an independent specialist tool-call trace entry (ORC-03, D-07)."
    - "The Bedrock connectivity smoke test returns a completion with an explicit model id + region, OR fails fast with a readable, diagnosable error that never leaks credential values (ORC-03, D-06/D-08)."
  artifacts:
    - backend/models/engagement_record.py
    - backend/store/engagement_store.py
    - backend/store/file_engagement_store.py
    - backend/tests/test_engagement_record.py
    - backend/tests/test_store.py
    - backend/tests/test_single_writer.py
    - backend/scripts/smoke_test_agents_as_tools.py
    - backend/scripts/smoke_test_bedrock_connectivity.py
    - backend/tests/test_agents_as_tools_smoke.py
    - backend/tests/test_bedrock_smoke.py
    - backend/pyproject.toml
  key_links:
    - "FileEngagementStore is the only concrete EngagementStore, constructed at one DI point -> Phase 8 AgentCore swap is a config change, not a rewrite (D-02)."
    - "EngagementRecord.engagement_id is a UUID (default_factory=uuid4) -> FileEngagementStore._path() only ever receives a validated UUID, closing off path traversal (D-04)."
    - "BedrockModel(model_id=BEDROCK_MODEL_ID, region_name=AWS_REGION) is constructed explicitly, never a bare model-id string -> model id + region are visible in code (ORC-03, D-06)."
---

<user_story>
**As a** backend developer building the Freelance Autopilot pipeline,
**I want to** create, persist, and reload a typed Engagement Record through a single store
seam, and have the Strands agents-as-tools wiring and the Bedrock model provider proven to
work (or to fail fast with a readable error) before any specialist agent exists,
**so that** every later phase builds on a verified schema, a swappable persistence boundary,
and a de-risked orchestration mechanism instead of untested assumptions.

Sourced from the ROADMAP Phase 1 goal and Success Criterion 1 (developer as the actor of a
backend foundations phase). No end user exists in Phase 1 — UI is Phase 4.
</user_story>

<objective>
Establish the shared Engagement Record schema + persisted single-writer store, and prove the
Strands agents-as-tools + Bedrock wiring against the pinned `strands-agents==1.54.0`, before
any specialist agent logic is written.

Purpose: These are the two highest-uncertainty foundations of the whole project. Proving them
now — the schema/store fully offline, the Strands/Bedrock mechanism as a throwaway spike that
is allowed to fail-fast readably in a credential-less sandbox — means Phases 2-8 build on
verified ground instead of training-data assumptions (PITFALLS.md Pitfall 1).

Output: A `backend/` package with the `EngagementRecord` Pydantic model, an `EngagementStore`
interface + `FileEngagementStore` implementation, an AST single-writer test, two throwaway
smoke scripts (agents-as-tools + Bedrock fail-fast), and the pytest suite that verifies all of
it. Covers REC-01, REC-02, REC-03, ORC-03.
</objective>

<execution_context>
@/home/user/Freelance-Autopilot/.claude/gsd-core/workflows/execute-plan.md
@/home/user/Freelance-Autopilot/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@docs/PRD.md
@.planning/phases/01-foundations-engagement-record-strands-bedrock-verification-spike/01-CONTEXT.md
@.planning/phases/01-foundations-engagement-record-strands-bedrock-verification-spike/01-RESEARCH.md
@.planning/phases/01-foundations-engagement-record-strands-bedrock-verification-spike/01-VALIDATION.md
@.planning/research/STACK.md
@.planning/research/ARCHITECTURE.md
@.planning/research/PITFALLS.md
</context>

<artifacts_this_phase_produces>
Newly-created symbols and files (source-grounding excludes these — they do not exist before
this plan runs):

**Modules / files:**
- `backend/pyproject.toml` — pytest config (`testpaths = ["tests"]`, `pythonpath = ["."]`) + pinned deps
- `backend/requirements.txt` — pinned dependency list
- `backend/models/engagement_record.py`
- `backend/store/engagement_store.py`
- `backend/store/file_engagement_store.py`
- `backend/agents/__init__.py`, `backend/tools/__init__.py` — empty placeholder packages (single-writer scan targets)
- `backend/scripts/smoke_test_agents_as_tools.py`, `backend/scripts/smoke_test_bedrock_connectivity.py`
- `backend/tests/conftest.py`, `backend/tests/test_engagement_record.py`, `backend/tests/test_store.py`, `backend/tests/test_single_writer.py`, `backend/tests/test_agents_as_tools_smoke.py`, `backend/tests/test_bedrock_smoke.py`

**Symbols:**
- `JobSlice`, `TriageSlice`, `ProposalSlice`, `ContractSlice`, `OpsSlice`, `EngagementRecord` (in `models/engagement_record.py`)
- `EngagementStore` (ABC: `create`, `get`, `save`), `FileEngagementStore` (in `store/`)
- `build_supervisor()`, `echo_specialist` (in `smoke_test_agents_as_tools.py`)
- `main()`, `MODEL_ID`, `REGION` (in `smoke_test_bedrock_connectivity.py`)
- Env-var names: `BEDROCK_MODEL_ID`, `AWS_REGION`
</artifacts_this_phase_produces>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Scaffold backend + Engagement Record model + file store, round-tripped end-to-end</name>
  <reversibility rating="costly">Implements D-03: the EngagementRecord shape is a contract shared by FastAPI I/O, Strands structured_output(), and every later phase — renaming fields later touches all specialists. Costly, not one-way; no decision checkpoint required.</reversibility>
  <files>backend/pyproject.toml, backend/requirements.txt, backend/models/__init__.py, backend/models/engagement_record.py, backend/store/__init__.py, backend/store/engagement_store.py, backend/store/file_engagement_store.py, backend/agents/__init__.py, backend/tools/__init__.py, backend/scripts/__init__.py, backend/tests/__init__.py, backend/tests/conftest.py, backend/tests/test_engagement_record.py, backend/tests/test_store.py, .gitignore</files>
  <read_first>
    - docs/PRD.md §6.2 — the exact Engagement Record JSON shape to mirror
    - .planning/phases/01-.../01-RESEARCH.md → "Pattern 1: Optional-stage-slice Engagement Record" and "Pattern 2: Abstract store + single concrete implementation" (verbatim Pydantic v2 + FileEngagementStore code, incl. atomic write) and "Recommended Project Structure"
    - .planning/phases/01-.../01-CONTEXT.md → D-01, D-02, D-03, D-04
    - .planning/phases/01-.../01-VALIDATION.md → Test Infrastructure + Wave 0 Requirements (pyproject, conftest, tmp store dir)
    - .planning/research/STACK.md §"Version Compatibility" (Pydantic v2 semantics; do NOT mix v1)
    - .gitignore (root — will be edited to ignore the runtime data dir)
  </read_first>
  <behavior>
    - test_engagement_record: EngagementRecord(job=JobSlice(title=..., description=...)) validates with triage/proposal/contract/ops all None, and auto-assigns a UUID engagement_id.
    - test_engagement_record: an invalid triage verdict (e.g. verdict="maybe") raises pydantic.ValidationError (Literal["apply","skip"] enforced).
    - test_engagement_record: engagement_id typed as UUID — constructing with a path-traversal string like "../../etc/passwd" raises ValidationError (path-traversal mitigation T-01-01).
    - test_store: FileEngagementStore(base_dir=tmp_path).create(record) then .get(record.engagement_id) returns an EngagementRecord equal (by model_dump) to the original — the create->save->reload round trip.
    - test_store: .get(<random unknown uuid>) returns None.
    - test_store: after .save, exactly one file data/engagements/{id}.json exists under tmp_path and no leftover .tmp file remains (atomic-write behavior).
  </behavior>
  <action>
    Scaffold the `backend/` package per RESEARCH.md "Recommended Project Structure" and build
    the schema + store as the walking-skeleton tracer.

    1. Create `backend/pyproject.toml` with `[tool.pytest.ini_options]` setting `testpaths = ["tests"]`
       and `pythonpath = ["."]` (so `import models` / `import store` resolve when pytest runs from
       `backend/`), and a `[project]` section pinning `pydantic>=2.13,<3`, `strands-agents==1.54.0`,
       `boto3>=1.43,<2`, and dev dep `pytest`. Also write `backend/requirements.txt` with the same
       pins (per RESEARCH.md Installation line). Run the install so the suite can run.
    2. Create empty-but-docstringed `__init__.py` for `models/`, `store/`, `agents/`, `tools/`,
       `scripts/`, `tests/`. `agents/__init__.py` and `tools/__init__.py` carry a one-line docstring
       stating they are placeholder packages that real specialists (Phase 2+) build inside, and are
       the scan target for the single-writer test — no imports.
    3. `models/engagement_record.py`: define `JobSlice`, `TriageSlice`, `ProposalSlice`,
       `ContractSlice`, `OpsSlice`, `EngagementRecord` as Pydantic v2 BaseModels exactly per
       RESEARCH.md Pattern 1 and PRD §6.2. `engagement_id: UUID = Field(default_factory=uuid4)`
       (D-04); `job: JobSlice` required; `triage`/`proposal`/`contract`/`ops` each `Optional[...] = None`
       (D-03). `TriageSlice.verdict: Literal["apply","skip"]`.
    4. `store/engagement_store.py`: `EngagementStore(ABC)` with abstract `create(record)->EngagementRecord`,
       `get(engagement_id: UUID)->EngagementRecord | None`, `save(record)->None` (RESEARCH.md Pattern 2, D-01).
    5. `store/file_engagement_store.py`: `FileEngagementStore(EngagementStore)` writing one JSON file
       per id under a `base_dir` (default `Path("data/engagements")`), using Pydantic v2
       `model_dump_json`/`model_validate_json` and atomic write (tmp file + `os.replace`). `_path()`
       accepts only a `UUID` and never interpolates a raw string (T-01-01). This is the single
       swappable construction point (D-02) — keep `FileEngagementStore` named in exactly one place.
    6. `tests/conftest.py`: a fixture returning a `FileEngagementStore` bound to pytest's `tmp_path`
       so tests never touch the real `data/engagements/`.
    7. `tests/test_engagement_record.py` and `tests/test_store.py`: implement the assertions in
       <behavior>.
    8. Edit the root `.gitignore` (scoped Edit, not overwrite) to add `backend/data/` so runtime
       Engagement Record JSON files are never committed.

    Do NOT create any real specialist Agent, tool logic, or FastAPI endpoint — out of scope
    (CONTEXT.md Phase Boundary). Use Pydantic v2 method names only (`model_dump_json`,
    `model_validate_json`) — v1 `.json()`/`.parse_raw()` raise AttributeError on the pinned version.
  </action>
  <verify>
    <automated>cd backend && python -m pytest tests/test_engagement_record.py tests/test_store.py -q</automated>
    <fails_when>Exit code is non-zero, OR pytest output shows a failed/errored assertion, OR output contains "ModuleNotFoundError" / "AttributeError" (unresolved package layout or a Pydantic v1 method name).</fails_when>
  </verify>
  <acceptance_criteria>
    - `backend/models/engagement_record.py` defines `EngagementRecord` with `engagement_id: UUID` (default_factory=uuid4), required `job: JobSlice`, and Optional `triage`/`proposal`/`contract`/`ops` defaulting to None.
    - `EngagementRecord(job=JobSlice(title="t", description="d"))` validates and `.triage is None`.
    - `TriageSlice(verdict="maybe", score=1, reasoning="x")` raises `pydantic.ValidationError`.
    - `FileEngagementStore(base_dir=tmp_path).create(r)` followed by `.get(r.engagement_id)` returns a record whose `model_dump()` equals the original's; `.get(uuid4())` returns None.
    - After a save, one `{id}.json` exists under tmp_path and no `.tmp` file remains.
    - `cd backend && python -m pytest tests/test_engagement_record.py tests/test_store.py -q` exits 0.
  </acceptance_criteria>
  <done>REC-01 and REC-02 are satisfied: a job-only record validates, and a record round-trips create->save->reload to an equivalent object through the store seam, verified by a green pytest run.</done>
</task>

<task type="auto">
  <name>Task 2: Single-writer import-graph test (REC-03)</name>
  <reversibility rating="costly">Implements D-05: the sole-writer boundary is the core determinism guarantee the judging narrative rests on. Costly to change later, not one-way; no decision checkpoint required.</reversibility>
  <files>backend/tests/test_single_writer.py</files>
  <read_first>
    - .planning/phases/01-.../01-RESEARCH.md → "Single-writer enforcement test (REC-03)" (verbatim AST-based test code) and "Don't Hand-Roll" (use `ast`, not regex, for import detection)
    - .planning/phases/01-.../01-CONTEXT.md → D-05
    - .planning/research/ARCHITECTURE.md → "Pattern 3" / "Internal Boundaries" (FastAPI is the only writer)
    - backend/agents/__init__.py, backend/tools/__init__.py (the scan targets created in Task 1)
  </read_first>
  <behavior>
    - The test AST-parses every `*.py` under `backend/agents/` and `backend/tools/` and collects imported module names from `ast.Import` and `ast.ImportFrom` nodes.
    - It asserts none of those names equals or is prefixed by `store` / `backend.store`.
    - With only the empty placeholder packages present, the test passes today; it becomes a real regression guard the moment Phase 2 adds specialist code that imports the store.
  </behavior>
  <action>
    Create `backend/tests/test_single_writer.py` implementing the AST import-graph check from
    RESEARCH.md "Single-writer enforcement test (REC-03)". Resolve the scan root as the test file's
    parent's parent (`backend/`), scan `agents` and `tools`, walk `ast.Import` / `ast.ImportFrom`
    nodes, and assert no imported module name equals or starts with a forbidden store-module prefix.
    Use Python's `ast` module — never a regex/text search over file contents (RESEARCH.md Don't
    Hand-Roll: regex false-positives on docstrings and misses aliased/dynamic imports). Skip scan
    directories that do not exist so the test is robust before Phase 2.
  </action>
  <verify>
    <automated>cd backend && python -m pytest tests/test_single_writer.py -q</automated>
    <fails_when>Exit code is non-zero, OR the assertion message "REC-03 violation" appears in output (an agent/tool module imported the store), OR output contains "ModuleNotFoundError".</fails_when>
  </verify>
  <acceptance_criteria>
    - `backend/tests/test_single_writer.py` uses `ast.walk` over `ast.Import`/`ast.ImportFrom` (no regex/string matching of source text).
    - It scans `backend/agents/` and `backend/tools/` and asserts no module imports a store-prefixed name.
    - The test passes against the current empty placeholder packages: `cd backend && python -m pytest tests/test_single_writer.py -q` exits 0.
    - A deliberate local experiment (adding `from store.engagement_store import EngagementStore` to a temp file under `backend/agents/`) would make the test fail — the guard is live, not vacuous.
  </acceptance_criteria>
  <done>REC-03 is satisfied: an AST-based test proves no module under backend/agents/ or backend/tools/ imports the store, encoding the single-writer boundary before any specialist exists.</done>
</task>

<task type="auto">
  <name>Task 3: Strands agents-as-tools + Bedrock fail-fast smoke spike (ORC-03)</name>
  <reversibility rating="reversible">Throwaway spike scripts (D-07/D-08); not part of the API import path, freely rewritable.</reversibility>
  <files>backend/scripts/smoke_test_agents_as_tools.py, backend/scripts/smoke_test_bedrock_connectivity.py, backend/tests/test_agents_as_tools_smoke.py, backend/tests/test_bedrock_smoke.py</files>
  <read_first>
    - .planning/phases/01-.../01-RESEARCH.md → "Pattern 3: Agents-as-tools smoke test" and "Pattern 4: BedrockModel wiring + fail-fast connectivity smoke test" (verbatim scripts + the exact botocore exception types to branch on) and Pitfalls 1, 2, 3 and "Anti-Patterns to Avoid"
    - .planning/phases/01-.../01-CONTEXT.md → D-06, D-07, D-08
    - .planning/phases/01-.../01-VALIDATION.md → Manual-Only Verifications (live Bedrock + trace are manual) and Per-Task map row 1-01-05
    - .planning/research/STACK.md §2 (agents-as-tools shapes), §4 (BedrockModel construction, region resolution order)
    - .planning/research/PITFALLS.md → Pitfall 1 (verify trace attr names against the live 1.54.0), Pitfall 2 (construction proves nothing — must call the model), Pitfall 3 (branch on ClientError code, this sandbox surfaces UnrecognizedClientException)
    - Environment note: this sandbox has AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY set to the literal "proxy-injected" and no AWS_REGION — the fail-fast path is what runs here and is a PASS.
  </read_first>
  <behavior>
    - test_agents_as_tools_smoke (offline, no Bedrock call): importing the script module succeeds, and `build_supervisor()` constructs a supervisor Agent with the `@tool`-wrapped `echo_specialist` registered in its tools — proving the pinned strands-agents==1.54.0 API shape (`Agent`, `tool`, `tools=[...]`) matches assumptions. This guards Pitfall 1's import/AttributeError risk without needing credentials.
    - test_bedrock_smoke (integration, runs the real fail-fast path here): `smoke_test_bedrock_connectivity.main()` returns an int in {0, 1} and never raises a raw traceback. When it returns 1 (this sandbox), captured stderr contains a "FAIL:" diagnostic naming the cause (e.g. UnrecognizedClientException / no model access). The literal credential value "proxy-injected" never appears in captured stdout/stderr (secret non-disclosure, T-01-02).
  </behavior>
  <action>
    Build both throwaway ORC-03 smoke scripts under `backend/scripts/` (NOT imported by any future
    api.py — D-08) plus pytest wrappers that give Nyquist-automated coverage without requiring live
    AWS credentials.

    1. `scripts/smoke_test_agents_as_tools.py` (RESEARCH.md Pattern 3): a `@tool`-decorated
       `echo_specialist` that constructs and calls its own `Agent` internally, and a
       `build_supervisor()` factory returning `Agent(system_prompt=..., tools=[echo_specialist])`
       (agents-as-tools shape 1, D-07). A `main()` under `if __name__ == "__main__"` calls the
       supervisor and asserts an independent specialist tool-call trace via `supervisor.messages`
       and `result.metrics.tool_metrics`. Per Pitfall 1, the executor MUST first run the script once
       (with real creds, if available) and `print()` the real shape of `supervisor.messages` /
       `result.metrics.tool_metrics` from the installed 1.54.0, then write the assertion against the
       observed shape — do not hardcode `toolUse` vs `tool_use` from the research example. Keep
       construction (`build_supervisor`) separate from invocation (`main`) so the offline test can
       construct without a Bedrock call.
    2. `scripts/smoke_test_bedrock_connectivity.py` (RESEARCH.md Pattern 4, D-06/D-08): read
       `MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", <inference-profile placeholder>)` and
       `REGION = os.environ.get("AWS_REGION", "us-east-1")`, construct
       `BedrockModel(model_id=MODEL_ID, region_name=REGION)` explicitly (never a bare model-id
       string), wrap `Agent(model=model)`, and in `main()->int` actually call the model once, then
       branch: success -> print "PASS" + return 0; `NoCredentialsError` / `ClientError` (inspect
       `e.response["Error"]["Code"]` for AccessDeniedException / UnrecognizedClientException /
       ValidationException) / `EndpointConnectionError` -> print a specific, readable remediation to
       stderr and return 1. Do NOT catch bare `Exception` as the primary strategy. NEVER print
       `os.environ` credential values or the caught exception in a way that echoes secrets — print
       only the error Code + a static remediation string (T-01-02, security V6).
    3. `tests/test_agents_as_tools_smoke.py`: import the module and assert `build_supervisor()`
       constructs without raising and the specialist tool is registered (assert against the real
       registration attribute the executor confirms on 1.54.0; if the exact attribute is uncertain,
       assert at minimum that construction does not raise and the returned object is an `Agent`).
       No network call.
    4. `tests/test_bedrock_smoke.py`: call `smoke_test_bedrock_connectivity.main()` inside
       `capsys`/captured output, assert the return value is in (0, 1) and that `main()` did not raise;
       if the return is 1, assert captured stderr contains "FAIL:"; assert "proxy-injected" is not in
       captured output.
  </action>
  <verify>
    <automated>cd backend && python -m pytest tests/test_agents_as_tools_smoke.py tests/test_bedrock_smoke.py -q</automated>
    <fails_when>Exit code is non-zero, OR output shows main() raised an uncaught exception / traceback, OR the return code was outside {0,1}, OR the "proxy-injected" credential literal was found in captured output, OR an ImportError/AttributeError on the strands API surface (Pitfall 1 caught).</fails_when>
  </verify>
  <acceptance_criteria>
    - `scripts/smoke_test_bedrock_connectivity.py` constructs `BedrockModel(model_id=..., region_name=...)` explicitly (no bare model-id string) and branches on `NoCredentialsError`, `ClientError` (by `Error.Code`), and `EndpointConnectionError` — not a bare `Exception` first.
    - `scripts/smoke_test_agents_as_tools.py` exposes a `build_supervisor()` that wires an `@tool`-wrapped specialist into a supervisor `Agent(tools=[...])` (agents-as-tools, D-07), separate from a `main()` that runs the trace assertion.
    - `smoke_test_bedrock_connectivity.main()` returns 0 or 1 and never raises; in this sandbox it returns 1 with a "FAIL:" diagnostic and no credential value in its output.
    - `cd backend && python -m pytest tests/test_agents_as_tools_smoke.py tests/test_bedrock_smoke.py -q` exits 0.
    - Manual (recorded as evidence, not gating): running `python -m scripts.smoke_test_bedrock_connectivity` from `backend/` prints a readable fail-fast diagnosis here; with real creds it prints PASS. Running `python -m scripts.smoke_test_agents_as_tools` with real creds shows a distinct specialist tool-call trace entry.
  </acceptance_criteria>
  <done>ORC-03 is satisfied: the agents-as-tools wiring constructs against the pinned SDK and the Bedrock smoke test returns a completion OR fails fast with a readable, non-secret-leaking error — both verified by a green pytest run, with the live trace/completion captured manually as evidence.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| engagement_id → filesystem path | An identifier used to build `data/engagements/{id}.json`; if it were free-form user input it could traverse the filesystem. |
| Bedrock smoke test → stderr/logs | AWS credential material is present in the environment; error output must not echo it. |
| pip install → local environment | Third-party packages (`strands-agents`, `pydantic`, `boto3`, `pytest`) execute install-time code. |
| EngagementRecord construction → in-process data | Untrusted/malformed data validated at the Pydantic model boundary (V5). |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-01-01 | Tampering | `FileEngagementStore._path()` | high | mitigate | `engagement_id` typed as `UUID` (Pydantic-validated, D-04); `_path()` only ever receives a `UUID`, never interpolates a raw string. Test asserts a path-traversal string raises `ValidationError` (Task 1). |
| T-01-02 | Information Disclosure | `smoke_test_bedrock_connectivity.py` error output | high | mitigate | Branch on typed botocore exceptions and print only the error Code + a static remediation string; never print `os.environ` credential values. Test asserts the placeholder credential literal is absent from captured output (Task 3). |
| T-01-03 | Tampering (data integrity) | `FileEngagementStore.save()` | medium | mitigate | Atomic write: serialize to a `.tmp` file then `os.replace` onto the final path, so an interrupted write cannot leave a torn JSON record (Task 1). |
| T-01-04 | Tampering (input validation) | `EngagementRecord` / stage slices | low | mitigate | Pydantic v2 validation rejects malformed data at the model boundary (V5); `TriageSlice.verdict` constrained to `Literal["apply","skip"]` (Task 1). |
| T-01-SC | Tampering | pip installs (`strands-agents`, `pydantic`, `boto3`, `pytest`) | high | mitigate | RESEARCH.md `## Package Legitimacy Audit` verified all four against PyPI + official GitHub orgs with long continuous version history; the seam's `SUS` flags trace to a sandbox download-stats gap (`unknown-downloads`/`too-new`), not a real supply-chain signal. Researcher explicitly recommends NO blocking human-verify checkpoint for these — none inserted. No `[SLOP]`/genuine `[ASSUMED]` packages present. |

**ASVS L1, block on high:** the two high threats (T-01-01 path traversal, T-01-02 credential
disclosure) each carry an automated test that proves the mitigation; T-01-SC is dispositioned
by the researcher's completed legitimacy audit.
</threat_model>

<verification>
Run the full backend suite from `backend/`:

```
cd backend && python -m pytest -q
```

Expected: all tests green (`test_engagement_record.py`, `test_store.py`,
`test_single_writer.py`, `test_agents_as_tools_smoke.py`, `test_bedrock_smoke.py`). Runtime
~5s. In this sandbox `test_bedrock_smoke.py` passes via the fail-fast branch (placeholder AWS
credentials) — that is the designed PASS per D-08, not a failure.

Manual evidence to capture (non-gating, per VALIDATION.md Manual-Only table):
- `cd backend && python -m scripts.smoke_test_bedrock_connectivity` — record the readable
  fail-fast diagnosis here (or a PASS + completion with real creds).
- `cd backend && python -m scripts.smoke_test_agents_as_tools` — with real creds, record the
  distinct specialist tool-call trace entry (`supervisor.messages` / `result.metrics.tool_metrics`).
</verification>

<success_criteria>
Mapped to ROADMAP Phase 1 Success Criteria:
1. A developer can create, save, and reload an Engagement Record by `engagement_id` through the
   store interface and get back an equivalent Pydantic object. → Task 1, `test_store.py` (REC-01, REC-02).
2. The store interface has exactly one caller path — no agent or tool writes to it directly. →
   Task 2, `test_single_writer.py` (REC-03).
3. A throwaway two-agent Strands smoke test shows a supervisor routing to a distinct specialist
   agent with independent tool-call trace entries. → Task 3, `smoke_test_agents_as_tools.py` +
   `test_agents_as_tools_smoke.py` (ORC-03); live trace captured manually.
4. A Bedrock connectivity smoke test calls Claude with an explicitly pinned model id + region, or
   fails fast with a readable, diagnosable error. → Task 3, `smoke_test_bedrock_connectivity.py` +
   `test_bedrock_smoke.py` (ORC-03).

All four requirement IDs covered: REC-01, REC-02 (Task 1), REC-03 (Task 2), ORC-03 (Task 3).
</success_criteria>

<multi_source_coverage_audit>
| Source | Item | Covered by |
|--------|------|-----------|
| GOAL | Engagement Record schema/store proven | Task 1 |
| GOAL | Strands multi-agent + Bedrock wiring proven | Task 3 |
| GOAL | Success Criterion 1 (create/save/reload round-trip) | Task 1 |
| GOAL | Success Criterion 2 (one caller path) | Task 2 |
| GOAL | Success Criterion 3 (2-agent trace) | Task 3 |
| GOAL | Success Criterion 4 (Bedrock fail-fast) | Task 3 |
| REQ | REC-01 | Task 1 |
| REQ | REC-02 | Task 1 |
| REQ | REC-03 | Task 2 |
| REQ | ORC-03 | Task 3 |
| RESEARCH | Pattern 1 (Optional-slice Pydantic model) | Task 1 |
| RESEARCH | Pattern 2 (abstract store + atomic-write file impl) | Task 1 |
| RESEARCH | Single-writer AST test | Task 2 |
| RESEARCH | Pattern 3 (agents-as-tools smoke) | Task 3 |
| RESEARCH | Pattern 4 (Bedrock fail-fast smoke) | Task 3 |
| RESEARCH | Recommended Project Structure + pyproject/pytest scaffold | Task 1 |
| CONTEXT | D-01 file store behind interface | Task 1 |
| CONTEXT | D-02 single swappable construction point | Task 1 |
| CONTEXT | D-03 Optional stage slices | Task 1 |
| CONTEXT | D-04 uuid4 engagement_id | Task 1 |
| CONTEXT | D-05 single-writer boundary + test | Task 2 |
| CONTEXT | D-06 explicit BedrockModel(model_id, region_name) | Task 3 |
| CONTEXT | D-07 agents-as-tools (not Swarm/Graph) | Task 3 |
| CONTEXT | D-08 Bedrock fail-fast standalone script | Task 3 |

No unplanned items. Exclusions (correctly out of scope): SQLite / AgentCore Memory backends
(CONTEXT Deferred), real specialist/tool/endpoint/extension code (CONTEXT Phase Boundary; later
phases), RESEARCH "out of scope" AgentCore items.
</multi_source_coverage_audit>

<output>
Create `.planning/phases/01-foundations-engagement-record-strands-bedrock-verification-spike/01-01-SUMMARY.md` when done.
</output>
