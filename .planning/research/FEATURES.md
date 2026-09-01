# Feature Research

**Domain:** Freelance engagement lifecycle automation (agentic: triage → proposal/contract → live-engagement ops)
**Researched:** 2026-09-01
**Confidence:** MEDIUM — PRD/PROJECT.md are detailed and treated as primary source; freelance-ops norms (invoicing, SOW structure, scope-creep detection) are well-established industry practice, not deeply sourced externally given hackathon time budget. Strands/AgentCore API specifics are explicitly unverified (flagged in PROJECT.md) and out of scope for this document.

## Feature Landscape

### Stage 1 — Gig Triage

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Structured field extraction from pasted job text | Can't score what isn't parsed — title, budget (fixed/hourly), description, client stats, skills | LOW-MEDIUM | LLM extraction into a fixed schema; brittle against inconsistent paste formats (Upwork copy/paste often loses table structure) |
| Deterministic kill-switch gate | Users need predictable, explainable "hard no" filtering that doesn't vary run-to-run; also cheaper (no LLM call needed to reject obvious junk) | LOW | Pure Python/rules; must run **before** the LLM scorecard to save cost/latency |
| Budget floor check | The #1 reason freelancers waste Connects is applying to underpriced jobs | LOW | Simple numeric threshold (e.g. reject fixed-price < $X or hourly < $Y); threshold should be configurable, not hardcoded |
| Client spend / hire-rate check | Industry-standard trust signal on Upwork-like platforms — $0 spend + 0% hire rate is a classic red flag combo | LOW | Deterministic thresholds (e.g. spend > $0 OR hire-rate > N% OR reviews exist) |
| Red-flag keyword detection | Catches scam/lowball language ("equity only," "unlimited revisions," "long-term partnership" as a bait phrase, "test project" for free) | LOW | Keyword/regex list; deterministic — this is exactly the kind of pattern-match a kill switch should own, not an LLM call |
| LLM scorecard (fit + reasoning) | Deterministic rules can't judge nuanced fit — domain match, description quality/vagueness, tone, whether the ask matches the stated budget | MEDIUM | This is the LLM-judgment layer; must run only on jobs that pass the kill switch |
| Verdict + score + reasoning output | Freelancer needs a fast, legible decision, not just a number | LOW | `{verdict, score, reasoning, extracted_fields}` per PRD — reasoning must reference the specific factors, not generic text |
| Competition / proposals-count signal | High proposal count on a mediocre budget signals a race-to-the-bottom, low reply-rate job | LOW-MEDIUM | Deterministic if a numeric field is present; otherwise LLM must reason about it qualitatively |
| Rate reasonableness vs. scope | A job description implying weeks of senior work at a junior hourly rate is the most common rate trap | MEDIUM | This is inherently an LLM judgment (scope-to-rate ratio), not a hard threshold — scope descriptions are unstructured text |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Full autonomy (zero escalation at triage) | Explicit PRD requirement and a genuine judging differentiator: this stage never blocks on a human, proving the kill-switch + LLM split is trustworthy enough to run unattended | LOW (behaviorally — the discipline is in NOT adding an escalation path) | Contrast against Stage 2/3 which *do* escalate — this asymmetry is the demo's "structurally justified HITL" story |
| Deterministic-gate-then-LLM-judgment architecture as a visible, explainable pipeline | Judges/users can see exactly why a job was auto-rejected (cheap, fast, reproducible) vs. why it was scored (LLM reasoning) — this transparency is rare in "AI scores your gig" tools, which are usually one opaque LLM call | LOW-MEDIUM | Emit which gate stage produced the verdict (`kill_switch_check` vs `llm_scorecard`) in the reasoning payload |
| Extracted-fields transparency in output | Lets the user sanity-check what the agent "read" from the paste, catching extraction errors before they propagate into scoring | LOW | Cheap addition to the existing output contract |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|------------------|-------------|
| Live Upwork DOM scraping / auto-capture | Removes the "paste" friction step; feels more "automated" | Violates Upwork ToS; explicit non-goal in PROJECT.md and a real legal/account-ban risk for any real user | Paste-based capture via the extension popup (already the chosen design) |
| Live Upwork API integration for job search/browsing | Would let the tool proactively find gigs, not just score pasted ones | Requires Upwork partner API access freelancers don't have; ToS and scope risk; also turns a hackathon demo into an integration project | Stay reactive: score what the user pastes |
| LLM-based kill switch (asking the LLM to check budget floor/spend/keywords) | Seems simpler — "just ask the model" | Non-deterministic, slower, costs tokens on jobs that should be free/instant rejects, and undermines the demo's "explainable gate" story that judges are explicitly scoring for | Deterministic Python checks; reserve the LLM for genuinely judgment-heavy fit/rate-reasonableness scoring |
| Escalating triage decisions to the human | Feels "safer" to always let the human have final say | PRD explicitly designs Stage 1 as fully autonomous — a triage escalation defeats the point of triage (saving the user's time) and dilutes the demo's HITL narrative (escalations should be rare and meaningful, not everywhere) | Autonomous verdict with legible reasoning; user acts on the verdict, doesn't approve it |

---

### Stage 2 — Proposal + Contract Drafting

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Phased-scope proposal draft | Standard freelance-proposal structure: problem understanding → phased approach → why-me → CTA; unphased "wall of text" proposals read as generic/low-effort | MEDIUM | Reuse `software-dev-proposal` pattern per PROJECT.md prior art |
| SOW with explicit deliverables per phase | A proposal without deliverable boundaries can't later be checked for scope creep — this is a hard dependency, not a nice-to-have | MEDIUM | Deliverables must be enumerable/structured (not prose only) so Stage 3's `check_scope_creep` has something concrete to diff against |
| Milestone breakdown tied to phases | Freelance client-side norm: pay-per-milestone, not lump sum, for anything beyond small fixed-price work | LOW-MEDIUM | Each milestone = deliverable(s) + amount + due date |
| Payment schedule (amounts + due dates per milestone) | Required for Stage 3's overdue-invoice detection to function at all — direct dependency | LOW | Structured list: `{milestone, amount, due_date, status}` |
| Missing-input detection (`check_scope_clarity`) | A proposal built on an ambiguous budget/timeline/deliverables is worse than no proposal — locks in bad scope | LOW-MEDIUM | Deterministic-ish checks: are budget, timeline, and deliverables list all present and non-vague in the extracted job fields? |
| Escalation question when scope/budget is ambiguous | This is the PRD's named Stage 2 HITL point — genuinely justified because guessing wrong here creates the exact disputes Stage 3 exists to catch | LOW | Must be a *specific* question ("What's the budget ceiling — the post says 'competitive' with no number"), not a generic "please confirm scope" |
| Contract terms boilerplate (IP ownership, revision limits, kill clause) | Any freelance contract missing these is incomplete by industry norm | LOW-MEDIUM | Can be templated boilerplate merged with per-engagement specifics |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Escalation is targeted and singular, not a scope-review committee | PRD explicitly wants ONE clear escalation question, not a checklist dump — mirrors how a competent human freelancer would ask one clarifying question, not stall for a full brief | LOW | Output contract already models this: `needs_human_input: bool, question: string|null` |
| Deliverables structured for machine comparison (not just prose) | Makes Stage 3 scope-creep detection tractable and demonstrably grounded in Stage 2's actual output — this is the multi-agent "shared state" story judges want to see | MEDIUM | This is the load-bearing design choice connecting Stage 2 → Stage 3; get the SOW schema right early |
| Rate/scope consistency check against Stage 1's extracted fields | Proposal grounded in the same budget the triage agent scored against, not re-derived independently — reinforces Engagement Record as genuine shared state across agents | LOW-MEDIUM | Read `job.budget` from Engagement Record rather than re-parsing |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|------------------|-------------|
| Auto-send proposal/contract to client | Feels like "full automation" — no human touch needed | No live email/message integration exists (explicit non-goal); also legally/reputationally risky to auto-send a contract without a human reviewing terms and price | Draft only; human reviews and sends manually (fixture-driven demo doesn't need send capability at all) |
| E-signature / legal-binding contract execution | Sounds like it "completes the loop" | Real legal complexity (jurisdiction, enforceability) way outside a 6-week hackathon; not needed to demonstrate the agent architecture | Draft the contract text; execution is explicitly a human's job outside the system |
| Escalating on every proposal (e.g. "confirm before I draft") | Feels cautious/safe | Turns the differentiator (rare, meaningful escalation) into decorative busywork exactly like the PRD warns against; every proposal escalating means the agent isn't doing its job | Escalate only when `check_scope_clarity` finds a genuine gap (missing budget/timeline/deliverables) |
| Negotiation / back-and-forth proposal revision agent | Seems like a natural v2 extension of drafting | Requires live client communication (out of scope) and multi-turn state well beyond hackathon timeline | Single draft; revisions are a human/manual follow-up, or fixture-only future work |

---

### Stage 3 — Live-Engagement Ops

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Scope-creep detection vs. signed SOW | Core Stage 3 promise; without a structured SOW (Stage 2 dependency) this is just vibes-based text comparison | MEDIUM-HIGH | Compare incoming client message content against the SOW's deliverables list; LLM judgment call ("is this ask covered by deliverable X, or new?") layered on structured input |
| Overdue-invoice flagging vs. payment schedule | Directly mechanical: today's date vs. milestone due_date + status != paid | LOW | This is deterministic — pure date comparison, no LLM judgment needed; should NOT be an LLM call |
| Client-ready status update drafting | Freelancers routinely under-communicate status; a drafted, professional update is high-value low-effort output | LOW-MEDIUM | LLM drafting task; needs current milestone state + any flags as input |
| Distinct escalation card per flag type | PRD requirement: scope creep, overdue invoice, and judgment-needed status updates each surface as separate, addressable cards, not one blob | LOW | UI/output-shape decision more than a new capability — but important for the "structurally justified, not decorative" HITL story |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Scope-creep flag cites the specific SOW deliverable it falls outside | Makes the escalation actionable and defensible to show a client ("this wasn't in scope per milestone 2"), rather than a vague "this might be scope creep" | LOW-MEDIUM | Requires the SOW schema to be structured (Stage 2 dependency) — reinforces the shared Engagement Record design |
| Overdue-invoice flag as pure deterministic check, contrasted with scope-creep's LLM judgment | Demonstrates the same "know which layer does what" discipline as Stage 1's kill-switch/LLM split — a second instance of the same architectural principle, which is a stronger judging story than doing it once | LOW | Mirrors Stage 1's pattern; worth calling out explicitly in the architecture diagram |
| Status update auto-drafted but never auto-sent | Keeps the human as the actual communicator with their own client (trust/tone reasons) while eliminating the "what do I even say" blank-page problem | LOW | No send capability needed — draft-only is both simpler to build and more defensible product behavior |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|------------------|-------------|
| Live client-message ingestion (email/Slack/Upwork messages API) | Would make scope-creep detection "real" instead of fixture-driven | No live integration is in scope for the demo (explicit non-goal); adds auth, polling, and reliability surface with no judging payoff in a 5-minute deterministic demo | Fixture: `sample_client_thread.json` with a deliberately crafted scope-creep message |
| Live payment-provider integration (Stripe/PayPal/Upwork escrow) for real invoice status | Would make overdue detection "real" | Explicit non-goal; adds OAuth/webhook complexity disproportionate to hackathon timeline | Fixture: `sample_payment_schedule.json` with one deliberately overdue milestone |
| Auto-escalating every incoming client message as a potential scope-creep flag | Seems maximally safe/thorough | Alert fatigue — turns a meaningful signal into noise, which is exactly the "decorative escalation" anti-pattern the PRD warns against | Flag only messages the LLM judges as outside the structured SOW deliverables; let clearly-in-scope chatter pass silently |
| Auto-sending overdue-invoice reminders to the client | Feels like it "closes the loop" on collections | No live email integration (out of scope); also a judgment call freelancers usually want to control the tone/timing of themselves | Flag + drafted reminder text; human sends |

## Feature Dependencies

```
Structured field extraction (Stage 1)
    └──requires──> Deterministic kill-switch gate
                       └──feeds──> LLM scorecard
                                      └──produces──> Engagement Record.triage

Engagement Record.triage (verdict=apply)
    └──requires──> Proposal draft (Stage 2)
                       └──requires──> check_scope_clarity
                                          └──may trigger──> Escalation question (human)
                       └──produces──> SOW with structured deliverables
                                          └──requires──> Milestone breakdown
                                                             └──requires──> Payment schedule (amounts + due dates)

SOW with structured deliverables ──requires──> Scope-creep detection (Stage 3)
Payment schedule ──requires──> Overdue-invoice flagging (Stage 3)
[Scope-creep flags + Invoice flags + milestone state] ──feeds──> Status update drafting (Stage 3)

Deterministic kill-switch gate (Stage 1) ──same architectural pattern as──> Overdue-invoice flagging (Stage 3)
LLM scorecard (Stage 1) ──same architectural pattern as──> Scope-creep judgment (Stage 3)

Live Upwork scraping/API (anti-feature) ──conflicts──> Paste-based capture (chosen design)
Auto-send proposal/contract (anti-feature) ──conflicts──> Draft-only output contract
Live client-message/payment integration (anti-feature) ──conflicts──> Fixture-driven Stage 2–3 demo determinism
```

### Dependency Notes

- **Scope-creep detection requires structured SOW deliverables:** This is the single most important cross-stage dependency in the whole system. If Stage 2's `draft_contract` output leaves deliverables as unstructured prose, Stage 3's `check_scope_creep` has nothing concrete to diff against and degrades into vague LLM vibes-checking — undermining the "cites the specific SOW deliverable" differentiator. Get the SOW schema (a list of discrete, named deliverables per milestone) right during Stage 2 planning, before Stage 3 is built.
- **Overdue-invoice flagging requires the payment schedule's due dates:** Purely mechanical dependency — Stage 3 cannot flag anything without Stage 2 having produced dated milestones. This is also why the payment schedule fixture must include at least one deliberately overdue milestone (already planned per PROJECT.md).
- **Deterministic-gate-then-LLM-judgment is a repeated architectural pattern, not a one-off:** Stage 1 (kill switch → scorecard) and Stage 3 (invoice date-check → scope-creep judgment) both split a cheap deterministic check from an expensive LLM judgment call. Treating this as one reusable pattern (rather than reinventing it per stage) is both an implementation efficiency and a stronger, more coherent judging narrative.
- **Escalation-question quality depends on extracted-fields transparency:** Stage 2's ambiguity check is only as good as Stage 1's `extract_job_fields` output. If budget/timeline were extracted sloppily in Stage 1, Stage 2 will either escalate unnecessarily (noise) or miss a real gap (silent under-scoping). This argues for treating the Engagement Record's `extracted_fields` as authoritative shared state, not re-extracting per stage.
- **Live-integration anti-features conflict with demo determinism:** Every live-integration anti-feature (Upwork API/scraping, live client messages, live payment providers) directly conflicts with the PRD's hard requirement of a deterministic, repeatable 5-minute demo. This isn't just a ToS/scope call — it's a structural requirement of the chosen demo format, reinforcing why fixtures are correct for Stages 2–3 rather than a corner cut.

## MVP Definition

### Launch With (v1 — hackathon submission)

- [ ] Chrome extension paste-capture → `/capture` → Gig Triage Agent verdict shown inline — proves the one real (non-fixture) integration point
- [ ] Deterministic kill-switch gate (budget floor, client spend/hire-rate, red-flag keywords) — cheap, explainable, and the first half of the "gate then judgment" story
- [ ] LLM scorecard (fit, rate reasonableness, competition) with reasoning — the second half of that story; must run only past the gate
- [ ] Proposal-Contract Agent: phased proposal + SOW with structured deliverables + milestone/payment schedule — SOW structure is the hard dependency everything in Stage 3 needs
- [ ] `check_scope_clarity` with a single targeted escalation question on ambiguity — the Stage 2 HITL proof point
- [ ] Ops Agent: `check_scope_creep` (LLM vs. structured SOW), `check_invoice_status` (deterministic date check), `draft_status_update` — each as a distinct escalation card
- [ ] Fixtures: sample jobs (mixed fit, to make triage results legible), one client thread with a deliberate scope-creep message, one payment schedule with one overdue milestone
- [ ] Engagement Record persisted per engagement, read/written by all three agents — the visible "shared state" that proves genuine multi-agent orchestration
- [ ] Supervisor Agent visibly orchestrating the three specialists (not one wrapped call) — this is the top judging criterion and must be legible in the architecture diagram and the code, not just functionally present

### Add After Validation (v1.x — only if time remains inside the 6-week window)

- [ ] Amazon Bedrock AgentCore deployment (explicit PRD stretch goal; cut first under time pressure)
- [ ] Multiple/rich sample fixtures (more client-thread variety, more job postings) to make the demo feel less scripted
- [ ] Richer contract boilerplate (IP terms, revision-limit language) beyond a minimal viable SOW

### Future Consideration (v2+ — beyond hackathon, if this became a real product)

- [ ] Live email/calendar integration for delivering drafted status updates and invoice reminders — defer until there's a real user willing to grant integration access and the deterministic-demo constraint no longer applies
- [ ] Live payment-provider integration (Stripe/Upwork escrow) for real invoice status instead of a fixture schedule — defer for the same reason, plus real auth/webhook complexity
- [ ] Multi-client dashboard / portfolio view across concurrent engagements — a real product need for the stated persona (freelancers running multiple concurrent engagements) but far beyond a single-engagement hackathon demo
- [ ] Negotiation-support agent for proposal back-and-forth — requires live client communication, out of scope until integrations exist

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|----------------------|----------|
| Deterministic kill-switch gate | HIGH | LOW | P1 |
| LLM scorecard | HIGH | MEDIUM | P1 |
| Extension paste-capture + inline verdict | HIGH | MEDIUM | P1 |
| Structured SOW/deliverables in contract draft | HIGH | MEDIUM | P1 |
| check_scope_clarity + single escalation question | HIGH | LOW-MEDIUM | P1 |
| check_scope_creep vs. SOW | HIGH | MEDIUM-HIGH | P1 |
| check_invoice_status (deterministic) | HIGH | LOW | P1 |
| draft_status_update | MEDIUM | LOW-MEDIUM | P1 |
| Engagement Record shared state | HIGH (judging criterion) | MEDIUM | P1 |
| Supervisor + specialist visible orchestration | HIGH (top judging criterion) | MEDIUM-HIGH | P1 |
| AgentCore deployment | MEDIUM (bonus points) | HIGH | P3 |
| Richer/varied fixtures | LOW-MEDIUM | LOW | P2 |
| Extended contract boilerplate | LOW | LOW | P3 |
| Live integrations (any) | MEDIUM (real-product value) | HIGH | Anti-feature for this milestone |

## Competitor Feature Analysis

No direct commercial competitor combines all three stages (triage → proposal/contract → ops) into one agentic pipeline for freelancers; the closest comparisons are point solutions.

| Feature | Existing point tools (e.g. standalone "gig scorer" tools, proposal-writing GPT wrappers) | Freelance platforms' native features (Upwork's own proposal tools, client dashboards) | Our Approach |
|---------|---|---|---|
| Gig scoring/triage | Usually a single opaque LLM call scoring "fit" with no deterministic gate; the prior "Gig Triage" (micro1) submission this project supersedes was itself single-stage | None — platforms don't score jobs for freelancers, they surface job feeds | Two-layer gate-then-judgment pipeline with legible, distinct reasoning per layer |
| Proposal drafting | Generic LLM-wrapper "write me a proposal" tools with no structured SOW/deliverable output | Upwork has a proposal text box only; no SOW/milestone drafting | Structured SOW + milestone + payment schedule designed explicitly to feed downstream ops checks |
| Scope-creep / invoice tracking | Essentially nonexistent as an agentic feature; freelancers do this manually or not at all | Upwork has manual milestone/escrow tracking but no automated scope-creep detection against the original agreement | Automated flag generation grounded in the agent's own earlier SOW output — a genuinely novel combination, not a rebuild of an existing feature |
| Human-in-the-loop design | Typically either fully autonomous (no escalation ever) or fully manual (human does everything) — few tools model *selective, justified* escalation | Platforms leave all judgment to the human by default | Escalation only at three specific, structurally justified points (scope/budget ambiguity, scope creep, overdue invoice) — deliberately absent at triage |

## Sources

- `/home/user/Freelance-Autopilot/.planning/PROJECT.md` (primary)
- `/home/user/Freelance-Autopilot/docs/PRD.md` (primary)
- General freelance-marketplace and freelance-ops industry norms (client spend/hire-rate as trust signals, milestone-based payment schedules, SOW/deliverable structuring, scope-creep-vs-signed-scope practice) — established freelancing-community conventions, applied via domain knowledge rather than a specific external source given the PRD's completeness and hackathon time budget.
- Existing `upwork-gig-scorer` skill in this environment's skill catalog corroborates the triage signal set (budget floor, client stats, red-flag keywords, rate reasonableness, competition) as the standard set freelancers actually use to decide apply/skip.

---
*Feature research for: Freelance Autopilot (freelance engagement lifecycle automation)*
*Researched: 2026-09-01*
