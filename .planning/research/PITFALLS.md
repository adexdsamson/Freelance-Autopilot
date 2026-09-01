# Pitfalls Research

**Domain:** Strands Agents SDK multi-agent orchestration + FastAPI + Bedrock/Claude + MV3 Chrome extension (hackathon: Freelance Autopilot)
**Researched:** 2026-09-01
**Confidence:** MEDIUM — Strands SDK facts verified against strandsagents.com docs and AWS blog (Sept 2026 snapshot); the SDK is actively evolving, so re-verify exact API names (`.as_tool()`, `delegate=True`) immediately before Phase 1 coding, not from this document alone.

## Critical Pitfalls

### Pitfall 1: Guessing the Strands multi-agent API instead of verifying it

**What goes wrong:**
Strands ships several distinct multi-agent constructs — "Agents as Tools" (orchestrator with sub-agents in its `tools=[]` list), `Graph`, `Swarm`, and a full `multiagent` API surface — and the exact call shape (`Agent(tools=[sub_agent])` auto-wrapping vs. `.as_tool(name=..., description=...)` vs. a hand-written `@tool` wrapper) has changed across SDK versions. Training-data knowledge of "how Strands multi-agent works" is very likely stale or conflated with LangGraph/CrewAI patterns. Building against a guessed API produces code that either doesn't import, silently falls back to single-agent behavior, or breaks in an unpredictable way close to the deadline.

**Why it happens:**
The SDK is young (production/stable only as of mid-2026) and its docs site (strandsagents.com) is the only reliable source — general web knowledge lags actual releases by months. Teams under hackathon time pressure often start coding from memory to move fast, then discover the mismatch during integration, when it's most expensive to fix.

**How to avoid:**
Before writing the Supervisor Agent, fetch `strandsagents.com/docs/user-guide/concepts/multi-agent/agents-as-tools/` and the Python API reference for the installed SDK version, and pin the exact version in `requirements.txt`. Confirm three things concretely: (1) can specialist agents be passed directly as list items in `tools=[...]`, or must each be wrapped with `.as_tool()`; (2) whether "delegation" mode exists in the pinned version and what its constraint is (per current docs: a delegated tool call must be the only tool call in that turn — mixing delegated and non-delegated calls in one turn causes cancellation); (3) whether delegation is compatible with the model provider in use (current docs flag it as incompatible with stateful models that manage conversation state server-side). Write one throwaway smoke-test script that instantiates a 2-agent supervisor/specialist pair and prints the specialist's tool-call trace before touching the real Gig Triage/Proposal/Ops agents.

**Warning signs:**
- Import errors or `AttributeError` on `Agent.as_tool` / similar during the first supervisor script.
- The supervisor's response looks like it never actually invoked a sub-agent (no distinct tool-call entries in the trace/telemetry for the specialist).
- Mixing a delegated and a non-delegated tool call in the same turn producing a silent cancellation instead of an error.

**Phase to address:**
Phase 0/setup (before any specialist agent logic is written) — a dedicated "verify Strands multi-agent API" spike, referenced directly by PROJECT.md's "Verify Strands/AgentCore APIs against live docs" decision.

---

### Pitfall 2: Bedrock model-provider region/credential mismatches

**What goes wrong:**
`BedrockModel` resolves region via `region_name` argument → `AWS_REGION` env var → hardcoded default (`us-west-2` in current docs) — not necessarily the region where the team's Bedrock model access was actually granted. A team that enabled model access in `us-east-1` but leaves region unset (or copies a snippet using `global.anthropic.claude-*` model IDs meant for cross-region inference) gets an opaque `AccessDeniedException` or `ValidationException` that looks like an auth bug but is actually a region/model-ID mismatch. Similarly, boto3's credential chain (env vars → `~/.aws/credentials` → instance role) can silently pick up a different AWS account/profile than the one with Bedrock model access enabled, especially on a shared dev machine.

**Why it happens:**
Bedrock requires an explicit one-time "model access" grant per region per account, which is easy to do once and forget; the SDK doesn't clearly surface "you don't have access to this model in this region" vs. "credentials invalid."

**How to avoid:**
Pin `region_name` explicitly in the `BedrockModel(...)` constructor (don't rely on env var fallback) and document it in README setup. Confirm model access is enabled for the exact model ID used (including whether it's a `global.` cross-region inference profile ID or a plain regional model ID — these are not interchangeable) before writing any agent logic. Add a one-line startup smoke test in `api.py` (or a `scripts/check_bedrock.py`) that makes a trivial Bedrock call and fails fast with a readable error, rather than discovering the misconfiguration mid-demo-recording.

**Warning signs:**
- `AccessDeniedException` / `ValidationException` on first real agent call despite credentials appearing to work for other AWS services.
- Different behavior on the presenter's laptop vs. a teammate's (different default AWS profile/region).

**Phase to address:**
Phase 0/setup — backend scaffolding phase, verified before any agent-specific phase starts.

---

### Pitfall 3: Structured-output exceptions when the LLM wants to ask a question instead of answering the schema

**What goes wrong:**
Strands' structured-output feature (Pydantic-model-constrained responses) throws when the agent's natural response is "I need more info" but the schema has only required fields for a final answer. This lands directly on this project's Proposal-Contract Agent, whose spec requires `{ proposal, contract, payment_schedule, needs_human_input, question }` — if `needs_human_input`/`question` aren't built as first-class optional fields the schema itself can always satisfy, an ambiguous-scope job will crash the agent instead of triggering the intended escalation.

**Why it happens:**
Developers design the "happy path" schema first (full proposal/contract) and bolt on escalation fields as an afterthought, rather than treating escalation as a first-class branch of the schema from the start.

**How to avoid:**
Per Strands' documented workaround: make every field that isn't guaranteed by the escalation path `Optional` (default `None`/empty), and always include a `question`/text field usable when the agent needs more information. Design the Pydantic model as "either a complete deliverable OR an escalation," not "a complete deliverable that might also carry an escalation flag." Write the schema and a forced-ambiguous-input test case in the same PR as the happy-path case — never validate only the happy path.

**Warning signs:**
- Structured-output validation errors/exceptions surfacing only when testing with a deliberately ambiguous fixture job (which is exactly the scenario the demo needs to work).
- `needs_human_input=True` paired with populated `proposal`/`contract` text (schema didn't actually force the branch).

**Phase to address:**
The Proposal-Contract Agent implementation phase — the schema itself is the "phase to address," and the ambiguous-scope escalation fixture must be exercised in that phase's own tests, not deferred to a later integration phase.

---

### Pitfall 4: Building a "single wrapped LLM call" that only looks multi-agent

**What goes wrong:**
Under time pressure, the fastest path is one big system prompt with tool functions attached to a single `Agent`, formatted to emit a JSON blob that resembles supervisor→specialist output (e.g., a "verdict" section and a "proposal" section from one model call). This satisfies the demo video's visuals but fails the judging criteria explicitly named in PRD.md §14 and PROJECT.md's "Judging" line: genuine Strands multi-agent orchestration must be visible in the architecture diagram AND the code. Judges (or a code-reading grader) can trivially tell the difference by checking whether the Supervisor Agent object literally holds sub-agent instances/tools that produce independent tool-call traces, versus a single agent with a long prompt.

**Why it happens:**
A single-call architecture is simpler to build and debug, especially with a 6-week deadline and Strands' own docs showing that agents can be added directly to `tools=[...]` almost trivially — it's tempting to build one mega-agent with many `@tool` functions instead of separate `Agent` instances.

**How to avoid:**
Structurally enforce separation from the start: each specialist (Gig Triage, Proposal-Contract, Ops) must be its own `Agent(...)` instance with its own system prompt and its own tool set, instantiated independently and only exposed to the Supervisor via the tools-array/`.as_tool()` mechanism — never as functions inside one agent's prompt. Verify by inspecting the trace/telemetry of a real run: there should be a distinct sub-agent invocation entry (with its own reasoning/tool calls) for triage, proposal, and ops, not one flat trace. The architecture diagram (a submission requirement) should be drawn from the actual object graph, not aspirational.

**Warning signs:**
- Only one `Agent(...)` instantiation in the codebase (or three system prompts concatenated into one).
- Sub-agent "calls" that are just Python function calls with no independent tool-call trace/telemetry entry.
- The Engagement Record gets fully populated by a single LLM turn instead of across three separate specialist invocations initiated by the supervisor.

**Phase to address:**
Every agent-implementation phase (Gig Triage, Proposal-Contract, Ops) plus a dedicated architecture-review checkpoint before the demo-recording phase — this is a standing constraint across the whole build, not a one-time fix.

---

### Pitfall 5: Chrome MV3 service-worker statelessness breaking the capture flow

**What goes wrong:**
`background.js` is specified as the service worker that performs the `/capture` fetch to avoid CORS. MV3 service workers are terminated after ~30 seconds of inactivity (and any single fetch that takes over 30s without triggering an extension API call, or over 5 minutes total, can be killed mid-request) — so if the demo's `/capture` → Gig Triage Agent round trip is slow (a real LLM call to Bedrock, not a mock), or if in-memory state (e.g., a pending-request map) is kept in a global variable, that state vanishes on worker restart. During a live demo this shows up as the popup silently never receiving a response, or receiving a stale/duplicate one.

**Why it happens:**
Developers test with DevTools open on the service worker, which artificially keeps it alive and masks the termination bug — the bug only appears in front of judges/on a cold demo run.

**How to avoid:**
Never hold pending-request state in a bare global variable in `background.js`; use `chrome.storage.session` (or pass all needed state through the message itself) if any cross-event state is required. Keep the `/capture` request path as a single `fetch()` call triggered directly by the `chrome.runtime.onMessage` listener (which itself resets the idle timer) rather than a long chain of async steps. Test the extension with the service worker DevTools panel CLOSED and after an idle period, not just immediately after reload.

**Warning signs:**
- Popup works during active development (DevTools open) but not on a fresh browser reload or after leaving the popup closed for a minute.
- Duplicate `/capture` POSTs when the user clicks twice because the first request's in-memory tracking was lost.

**Phase to address:**
Chrome extension implementation phase — explicitly test the "cold start after idle" path, not just the "just reloaded the extension" path, before considering that phase done.

---

### Pitfall 6: host_permissions / manifest misconfiguration blocking the FastAPI fetch

**What goes wrong:**
Even with the fetch routed through `background.js`, MV3 extensions still need `host_permissions` (e.g., `http://localhost:8000/*`) declared in `manifest.json` for the service worker's `fetch()` to reach a non-HTTPS local backend without being blocked, and Chrome's extension CSP/host-permission model differs from ordinary page CORS — a missing or overly narrow `host_permissions` entry (e.g., only `https://` when the backend serves plain `http://localhost`) fails silently or with a generic network error rather than a clear permissions message.

**Why it happens:**
`host_permissions` is easy to forget because "background.js avoids CORS" is treated as a complete mental model, when in fact the extension still needs the permission declared; also, developers often start the demo backend on `https` in their head but actually run local `uvicorn` on plain `http`.

**How to avoid:**
Declare `host_permissions` for the exact scheme+host+port the backend runs on (`http://localhost:8000/*` or whatever the demo uses) in `manifest.json` from the start, and keep the backend's actual bound address consistent with it throughout development — don't let it drift (e.g., someone runs on port 8001 locally). Confirm the permission during the extension implementation phase with a real fetch, not just a `manifest.json` review.

**Warning signs:**
- `fetch()` from `background.js` fails with a generic `TypeError: Failed to fetch` and no CORS error in console (a classic sign of missing host_permissions rather than a CORS issue).
- Extension works on the developer's machine (port matches) but fails for a teammate running the backend on a different port.

**Phase to address:**
Chrome extension implementation phase, same phase as Pitfall 5.

---

### Pitfall 7: LLM nondeterminism breaking the repeatable 5-minute demo

**What goes wrong:**
The success metric explicitly requires "a working, deterministic end-to-end run" for the recorded demo, but every stage calls a real Claude model via Bedrock, which is inherently non-deterministic (even at temperature 0, outputs can vary run to run). If the demo script depends on a specific triage verdict, a specific scope-creep detection, or specific wording appearing every take, a re-record can produce a different (or wrong) verdict/escalation and burn recording time right before the deadline.

**Why it happens:**
Teams build fixtures that are "mostly obvious" (e.g., a job posting that's clearly good or clearly bad) assuming the model will always agree, without stress-testing multiple runs, and without separating "deterministic gate" logic from "LLM judgment" logic in the escalation-triggering path.

**How to avoid:**
Push as much of the demo-critical branching as possible into the deterministic, non-LLM code paths already specified: `kill_switch_check` (budget floor, red-flag keywords, client thresholds) for triage, and `check_scope_creep`/`check_invoice_status` comparisons against the fixture SOW/payment schedule for Ops — these are plain Python comparisons against fixture data, not LLM judgment, so their outputs are fully repeatable. Reserve the LLM's role (`llm_scorecard`, proposal drafting, status-update wording) for the parts where variability is acceptable (reasoning text, drafted prose) and never for the verdict/escalation trigger itself. Before recording, run the full fixture set at least 3 times end-to-end and confirm every escalation card and verdict fires identically each time; if any doesn't, tighten the deterministic gate rather than the prompt.

**Warning signs:**
- The scope-creep fixture message doesn't trigger a flag on a re-run, or triggers inconsistently.
- The triage verdict flips between "apply" and "skip" for the same fixture job across two consecutive runs.
- Demo rehearsal requires "just re-run it, it usually works" — a direct signal the pipeline isn't actually deterministic yet.

**Phase to address:**
Design this into each specialist agent's own phase (triage, proposal, ops) as the boundary between deterministic tool and LLM tool is drawn — not something to patch during the demo-recording phase. Confirmed by a dedicated "run fixtures N times, diff outputs" verification step before the demo-script phase.

---

### Pitfall 8: Escalation design that is decorative rather than structural

**What goes wrong:**
PROJECT.md and PRD.md both call out that escalations must be "structurally justified, not decorative" — the risk is building escalation cards that always fire (so they look impressive in the demo but carry no real judgment) or that never actually block/change downstream flow (the pipeline continues identically whether or not the human responds). A decorative escalation is a UI element with no causal effect on the Engagement Record or the next agent's behavior.

**Why it happens:**
Escalation UI (a "card" in the popup/response) is easy to build and demo-friendly, but wiring genuine conditional logic — where the Proposal-Contract Agent actually pauses and the Engagement Record actually records `needs_human_input=true` blocking auto-advance, or where the Ops Agent's flag actually changes what the next `draft_status_update` says — takes more design discipline and is easy to skip under time pressure.

**How to avoid:**
For each of the three named escalation points (kill-switch gate — deliberately non-escalating per spec, scope/budget ambiguity, scope creep, overdue invoice), define explicitly: what field in the Engagement Record does the escalation set, what does `/engagements/{id}/advance` do differently when that field is set (e.g., refuse to auto-draft the contract until `needs_human_input` is resolved), and what does the fixture data look like that makes the condition sometimes true and sometimes false (proving it's conditional, not hardcoded). Test the negative case too: run a fixture where scope is unambiguous and confirm no escalation fires, and one where it's ambiguous and confirm the pipeline actually halts/branches rather than just displaying a card.

**Warning signs:**
- Escalation cards render regardless of fixture content (always-on) — check by running a "clean" fixture with no scope creep and confirming zero flags.
- `/engagements/{id}/advance` behaves identically whether `needs_human_input` is true or false.
- The escalation "resolution" (human answering the question) has no code path that feeds the answer back into the Engagement Record and downstream agent.

**Phase to address:**
Proposal-Contract Agent phase and Ops Agent phase individually (each owns one or two escalation points) plus the Engagement Record / API phase that must implement the actual gating logic in `/advance`.

---

### Pitfall 9: Upwork ToS/scraping risk creeping back in through "convenience" features

**What goes wrong:**
The project's mitigation (paste-based capture only, no DOM scraping, no live Upwork API calls) is a explicit Out-of-Scope decision, but it's easy to accidentally reintroduce risk later — e.g., adding a "fetch job page by URL" convenience feature in the extension (having `background.js` fetch the Upwork URL server-side to auto-fill fields) reintroduces exactly the scraping/ToS risk the paste-based design was meant to avoid, especially if added late as a demo-polish improvement without revisiting the ToS constraint.

**Why it happens:**
"Paste the URL and let the backend fetch it" feels like a small UX improvement that's easy to justify in the moment, but it silently converts the extension from "reads user-pasted text" into "the system fetches Upwork's site," which is the exact scenario Out-of-Scope was written to exclude.

**How to avoid:**
Keep the extension's only server-bound payload as text the user explicitly pasted (job description text, not a URL the backend then fetches) and treat any manifest permission requesting `*://*.upwork.com/*` host access, or any backend code calling `requests.get`/`fetch` against an upwork.com URL, as a hard stop requiring explicit re-discussion, not a normal code review comment.

**Warning signs:**
- A manifest.json diff adds `host_permissions` for `upwork.com`.
- Backend code contains any outbound HTTP call to a `upwork.com` domain.

**Phase to address:**
Chrome extension implementation phase (enforced at the manifest/permissions level) — flag any deviation as a self-review checklist item before that phase is marked done.

---

### Pitfall 10: AgentCore deployment consuming schedule that belongs to core stages

**What goes wrong:**
AgentCore deployment is explicitly a stretch goal that PROJECT.md says to cut first if the timeline slips, but stretch goals have a way of getting started early ("let's get the deployment skeleton going now so it's not a scramble later") and then absorbing debugging time that should go to the three core agents or the extension — especially since AgentCore's own session/memory API surface is called out in Context as needing separate verification against current docs, meaning it carries its own version of Pitfall 1.

**Why it happens:**
Deployment work looks satisfying and demo-impressive ("it's live on AWS!"), and engineers often want infra decided early; but AgentCore is a second unverified SDK surface layered on top of the already-unverified Strands multi-agent API, doubling the research/debugging risk for a feature that doesn't gate the score.

**How to avoid:**
Sequence AgentCore deployment strictly last, after all three specialist agents, the FastAPI backend, the extension, and the fixtures are working end-to-end locally and the demo script/video has at least a rough working cut. Set an explicit calendar checkpoint (e.g., one week before the Sep 14 deadline) at which AgentCore is either fully time-boxed to a fixed number of days or dropped entirely — don't let it run open-ended. If pursued, verify the AgentCore session/memory API against current docs with the same rigor as Pitfall 1 before writing integration code, and keep the local file/SQLite Engagement Record path fully functional as a fallback so a failed AgentCore integration never blocks the demo.

**Warning signs:**
- AgentCore work starts before all three specialist agents pass their own local tests.
- Time spent debugging AgentCore-specific errors (auth, session API mismatches) starts to compress the days remaining before Sep 14 with core-stage work still incomplete.

**Phase to address:**
Treated as its own final, optional phase in the roadmap, explicitly ordered after and gated on completion of the core supervisor/specialist/extension/fixture phases — never interleaved with them.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| One mega-agent with many `@tool` functions instead of 3 separate `Agent` instances | Faster to write, one prompt to tune | Fails the explicit judging criterion (not genuine multi-agent); indistinguishable from a wrapped LLM call on code review | Never — this is a named judging risk, not a normal tradeoff |
| Hardcoding fixture-matching logic in the LLM prompt ("if you see scope creep, say X") instead of a real `check_scope_creep` comparison tool | Ships the escalation card faster | Escalation becomes decorative (Pitfall 8); breaks the moment the fixture changes | Never for the specific demo escalation points; acceptable only for cosmetic wording variations |
| Storing Engagement Record in a Python dict in-memory instead of file/SQLite | Zero setup time | State lost on backend restart mid-demo-rehearsal; can't inspect record between stages for debugging | Only in the very first days of a phase's prototyping, must be replaced before that phase's own verification step |
| Skipping the "run fixtures 3x, diff outputs" determinism check | Saves an afternoon | Demo re-record risk discovered only under recording pressure | Never — cheap enough to always do before the demo-script phase |
| Adding AgentCore deployment work before core stages are demo-ready | Feels like progress on "the AWS-native story" | Steals days from core agents/extension that actually gate the score | Only after all core phases pass their own UAT, and only within a fixed time-box |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|-------------------|
| Amazon Bedrock (Claude) | Leaving `region_name` unset and relying on `AWS_REGION`/default fallback (`us-west-2` per current docs), mismatched with where model access was actually enabled | Pin `region_name` explicitly in `BedrockModel(...)`; verify model access is enabled for that exact region and model ID (including whether it's a cross-region `global.` inference profile) before writing agent code |
| Strands multi-agent (`Agent(tools=[sub_agent])` / `.as_tool()`) | Assuming the API shape from memory/other frameworks (LangGraph, CrewAI) instead of the pinned Strands version's docs | Fetch strandsagents.com docs for the pinned version; smoke-test a minimal 2-agent supervisor before building the real specialists |
| Strands structured output (Pydantic schema) | Required-only fields that can't represent "agent wants to ask a question" → runtime exception on ambiguous input | Make non-guaranteed fields `Optional`, always include a question/text escape hatch field, test the ambiguous-input path explicitly |
| Chrome extension → FastAPI backend | Relying on "background.js avoids CORS" as a complete mental model and omitting `host_permissions` for the backend's actual scheme+host+port | Declare exact `host_permissions` (e.g., `http://localhost:8000/*`) matching the backend's real bound address; keep them in sync as ports/schemes are decided |
| Chrome extension service worker state | Storing pending-request tracking or session data in a bare global variable in `background.js` | Use `chrome.storage.session` or pass state through message payloads; test after an idle period with DevTools closed |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Sequential (non-parallel) specialist agent calls when stages could run concurrently | Demo video runs longer than the 5-minute limit if narration + agent latency stack up | Time the actual Bedrock round-trip latency per agent early; if the demo needs faster feel, consider a shorter model or pre-warmed/cached call for narration-heavy sections | Becomes visible as soon as real (non-mocked) LLM calls replace mocked timing in the demo script rehearsal |
| Service worker fetch exceeding MV3's ~30s inactivity / 5-minute hard limits | Extension popup silently stops showing a result on a slow triage call | Keep the `/capture` LLM path fast enough (test actual Bedrock triage latency), and ensure UI shows a pending state rather than assuming instant response | If a single Bedrock call is unusually slow (rate limiting, retries) during the live demo |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Extension or backend fetching upwork.com URLs server-side "for convenience" | Reintroduces the ToS/scraping risk the paste-based design was built to avoid (see Pitfall 9) | Treat any code path with an outbound request to `upwork.com` or a manifest `host_permissions` entry for it as a hard stop requiring re-discussion |
| Hardcoded AWS credentials or API keys committed to the public hackathon repo | Public repo requirement (submission checklist) means committed secrets are immediately exposed | Use env vars / `.env` (gitignored) for AWS credentials and the local demo API key; add a pre-commit or manual check before each push |
| Single shared local API key with no scoping, accidentally left in a checked-in fixture or README example | Low risk for a local demo, but a leaked-looking key in a public repo can be mistaken for a live credential by anyone browsing the repo | Use an obviously fake/placeholder value in README examples, keep the real value only in an untracked local `.env` |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-------------------|
| Popup shows nothing while waiting for `/capture` → Gig Triage round trip | Judge/viewer assumes the extension is broken during the live demo | Show an explicit pending/loading state in the popup the moment the paste is submitted |
| Escalation cards with no clear action (just informational text) | Undermines the "structurally justified escalation" story — looks decorative even if it isn't | Give each escalation card a concrete resolution action (answer the question, acknowledge the flag) that visibly changes the Engagement Record afterward |
| Paste flow with no format guidance (user pastes a bare URL and gets a confusing extraction failure) | Breaks the "paste-based capture" flow the whole compliance mitigation depends on | Give the paste textarea a placeholder/example showing pasted job text is expected, and have `extract_job_fields` degrade gracefully (partial extraction + explanation) rather than failing hard |

## "Looks Done But Isn't" Checklist

- [ ] **Supervisor + specialists:** Often "done" as one agent with many tools — verify by checking there are 4 distinct `Agent(...)` instantiations (supervisor + 3 specialists) and that a real run's trace shows independent sub-agent tool-call entries, not a single flat trace.
- [ ] **Escalation cards:** Often decorative — verify by running one fixture that should NOT trigger the escalation and confirming zero cards, and one that should, confirming `/engagements/{id}/advance` actually branches (not just UI text) on the resulting flag.
- [ ] **Determinism:** Often "it worked when I tried it" — verify by running the full fixture set 3 times end-to-end and diffing verdicts/flags/escalation triggers (not the LLM's exact prose, which can vary) for identical results.
- [ ] **Chrome extension capture:** Often tested only with DevTools open — verify by reloading the extension, waiting >30s idle, then testing capture cold, and confirm `host_permissions` matches the exact backend URL used in the demo recording.
- [ ] **Bedrock region/model access:** Often works on the developer's machine only — verify a teammate (or a clean AWS profile) can run the same `region_name`/model ID combination successfully before the demo-recording phase.
- [ ] **Upwork ToS boundary:** Often drifts as "quality of life" features get added — verify no code path or manifest permission touches `upwork.com` directly before submission.
- [ ] **AgentCore stretch goal:** Often half-started and half-abandoned — verify the fallback (local file/SQLite Engagement Record) still works end-to-end even if AgentCore integration is incomplete or reverted.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|-----------------|
| Discover mid-build that the guessed Strands multi-agent API is wrong | MEDIUM | Stop, re-fetch current docs for the pinned version, rewrite the supervisor wiring (usually contained to the supervisor's `tools=[...]` construction, not the specialist agents' internal logic) |
| Bedrock region/credential misconfiguration found late | LOW | Set `region_name` explicitly, confirm model access via AWS console for that region/model ID, re-run smoke test |
| Structured-output exception surfaces only on the ambiguous-scope fixture during rehearsal | LOW–MEDIUM | Make the failing fields `Optional`, add the question/text escape hatch, add the ambiguous fixture as a permanent regression test for that agent |
| Discover the built system is a single wrapped call, not genuine multi-agent, close to deadline | HIGH | Requires restructuring the supervisor/specialist split — budget this as a multi-day fix, which is why Pitfall 4 must be caught structurally per-phase, not at the end |
| Determinism failure discovered during demo recording | MEDIUM | Move the failing branch logic from the LLM prompt into a deterministic tool function (comparison against fixture data), re-verify with the 3x-run check, re-record |
| AgentCore integration stalls close to deadline | LOW (if sequenced correctly) | Revert to the local file/SQLite Engagement Record path (must have been kept working throughout) and drop AgentCore from the submission — it was explicitly scoped as cuttable |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|-------------------|----------------|
| Guessed Strands multi-agent API | Phase 0 / backend setup spike | 2-agent smoke test shows independent sub-agent trace entries before real specialists are built |
| Bedrock region/credential mismatch | Phase 0 / backend setup | Startup smoke-test script makes a trivial Bedrock call and fails fast with readable error |
| Structured-output exception on ambiguous input | Proposal-Contract Agent phase | Ambiguous-scope fixture test passes without exception; schema fields reviewed as Optional-except-guaranteed |
| Single wrapped LLM call disguised as multi-agent | Every specialist-agent phase + pre-demo architecture review | Trace inspection confirms 4 distinct `Agent` instances with independent tool-call entries; architecture diagram matches actual object graph |
| MV3 service worker statelessness | Chrome extension phase | Cold-start test (DevTools closed, idle >30s) still completes a capture round trip |
| host_permissions/CORS misconfiguration | Chrome extension phase | Real fetch from `background.js` to the exact demo backend URL succeeds without manifest changes needed later |
| LLM nondeterminism vs. repeatable demo | Each specialist-agent phase (deterministic/LLM boundary) + pre-demo-script verification | Full fixture set run 3x end-to-end with identical verdicts/flags |
| Decorative escalation design | Proposal-Contract Agent phase, Ops Agent phase, Engagement Record/API phase | Negative-case fixture (no ambiguity/creep/overdue) produces zero escalations; positive-case fixture visibly changes `/advance` behavior |
| Upwork ToS drift | Chrome extension phase | Manifest and backend code reviewed for zero `upwork.com` host permissions or outbound calls before submission |
| AgentCore consuming core-stage time | Final/optional phase, explicitly ordered last | Core phases (agents, backend, extension, fixtures, demo script) verified complete before any AgentCore work begins; local fallback confirmed working throughout |

## Sources

- [Agents as Tools with Strands Agents SDK](https://strandsagents.com/docs/user-guide/concepts/multi-agent/agents-as-tools/) — orchestrator/specialist pattern, `.as_tool()`, delegation constraints
- [Strands Agents SDK: A technical deep dive into agent architectures and observability (AWS ML Blog)](https://aws.amazon.com/blogs/machine-learning/strands-agents-sdk-a-technical-deep-dive-into-agent-architectures-and-observability/)
- [5 Multi-Agent Patterns in Strands Agents: Which One and When](https://dev.to/aws-heroes/5-multi-agent-patterns-in-strands-agents-which-one-and-when-48gh)
- [Amazon Bedrock model provider — Strands docs](https://strandsagents.com/docs/user-guide/concepts/model-providers/amazon-bedrock/) and [API reference](https://strandsagents.com/latest/documentation/docs/api-reference/python/models/bedrock/) — region/credential resolution behavior
- [strands.tools.structured_output.structured_output_tool](https://strandsagents.com/docs/api/python/strands.tools.structured_output.structured_output_tool/) — structured-output exception behavior and Optional-fields workaround
- [Streaming Events — Strands docs](https://strandsagents.com/docs/user-guide/concepts/streaming/)
- [The extension service worker lifecycle — Chrome for Developers](https://developer.chrome.com/docs/extensions/develop/concepts/service-workers/lifecycle) — 30s inactivity termination, 5-minute request cap
- [Chrome extension Manifest V3: host_permissions, CORS for cross-origin](https://corsapi.com/en/blog/chrome-extension-manifest-v3-cors-host-permissions)
- [Manifest V3 Migration Pitfalls — Lessons from 17 Chrome Extensions](https://dev.to/_350df62777eb55e1/manifest-v3-migration-pitfalls-lessons-from-17-chrome-extensions-2j3h)
- Project-internal: `.planning/PROJECT.md`, `docs/PRD.md` (explicit judging criteria, ToS mitigation, AgentCore stretch-goal decision, escalation-design constraint)

---
*Pitfalls research for: Freelance Autopilot (Strands multi-agent + FastAPI + Bedrock + MV3 extension hackathon)*
*Researched: 2026-09-01*
