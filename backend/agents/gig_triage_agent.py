"""The Gig Triage Agent — Stage 1 specialist.

This module carries two things that arrived from two phases and are both kept:

1. The **real** Stage 1 specialist (Phase 2, TRI-01..04): `GigTriageAgent` /
   `run_triage`, a deterministic driver over the real
   `extract_job_fields` / `kill_switch_check` / `llm_scorecard` tools that
   always returns a `TriageResult` and never escalates.
2. The **Supervisor-facing builder** (Phase 3, ORC-02): `build_gig_triage_agent`,
   which constructs the Strands `Agent` the Supervisor wraps agents-as-tools on
   the live `TRIAGE_BACKEND=supervisor` path.

Both are preserved deliberately. Phase 2's tests import `GigTriageAgent` /
`run_triage`; Phase 3's `agents/supervisor.py` imports `build_gig_triage_agent`.
Wiring the Supervisor path onto Phase 2's `run_triage` (replacing the
placeholder gate) is a follow-up integration behind the existing
`TriageRunner` seam, intentionally out of scope for this merge.

This module must never import the store (REC-03/D-05).

Fully autonomous by design: the specialist always returns a verdict and never
asks a human anything. `TriageResult` has no escalation fields and forbids
extras, so that autonomy is structural rather than a convention someone can
drift from. Stage 2's Proposal-Contract Agent is where escalation becomes a
first-class outcome.

Why a deterministic driver instead of an Agent with tools=[...]
----------------------------------------------------------------
Phase 1 (D-07) established agents-as-tools as the orchestration mechanism,
and Phase 3 wraps `run_triage` in an `@tool` so the Supervisor calls this
specialist exactly that way. Inside the specialist, though, the three steps
run in a fixed Python sequence rather than being handed to a model to order,
for three reasons:

1. The gate must actually gate. If a model decides whether to call
   `kill_switch_check`, a posting containing "unpaid test" can still collect
   an enthusiastic score -- the disqualification becomes advisory.
2. DEMO-02 requires three fixture runs with identical verdicts. Model-chosen
   tool ordering is precisely the variance that requirement rules out.
3. A rejected posting costs zero tokens, because the LLM step is never
   reached.

The LLM judgement is not diminished by this: `llm_scorecard` runs a real
Bedrock-backed `Agent` with `structured_output`, and that call is a genuine,
independently traceable Agent invocation -- the second one Phase 3's success
criteria look for.
"""
from __future__ import annotations

import os

from strands import Agent
from strands.models import BedrockModel

from models.engagement_record import TriageSlice
from models.triage import ExtractedJobFields, KillSwitchResult, Scorecard, TriageResult
from tools.placeholder_triage import placeholder_kill_switch_check
from tools.triage_config import APPLY_SCORE_THRESHOLD
from tools.triage_tools import extract_job_fields, kill_switch_check, llm_scorecard


def _rejection_reasoning(gate: KillSwitchResult) -> str:
    reasons = "; ".join(gate.rejections)
    return f"Skipped by the deterministic pre-screen: {reasons}."


def _scored_reasoning(card: Scorecard, gate: KillSwitchResult, verdict: str) -> str:
    parts = [
        f"{card.reasoning.strip()}",
        (
            f"Scores — fit {card.fit_score:g}/10, competition "
            f"{card.competition_score:g}/10, rate {card.rate_reasonableness_score:g}/10 "
            f"→ composite {card.score:g}/100 "
            f"({'at or above' if verdict == 'apply' else 'below'} the "
            f"{APPLY_SCORE_THRESHOLD:g} apply threshold)."
        ),
    ]
    if gate.flags:
        parts.append("Pre-screen concerns weighed: " + "; ".join(gate.flags) + ".")
    return " ".join(parts)


class GigTriageAgent:
    """Stage 1 specialist: raw pasted posting in, `TriageResult` out.

    Holds no state between runs -- two calls with the same text take the same
    path -- so a single instance is safe to reuse across engagements and a
    fresh one is never required for correctness.
    """

    def run(self, raw_text: str) -> TriageResult:
        """Triage one pasted job posting.

        Args:
            raw_text: The posting exactly as the freelancer pasted it.

        Returns:
            A `TriageResult` with verdict, score, reasoning and
            extracted_fields -- and nothing else.

        Raises:
            ValueError: if `raw_text` is empty.
        """
        fields = ExtractedJobFields.model_validate(extract_job_fields(raw_text))
        gate = KillSwitchResult.model_validate(kill_switch_check(fields.model_dump()))

        if not gate.passed:
            # Short-circuit: no model call, score pinned to 0 so a
            # disqualified posting can never outrank a scored one.
            return TriageResult(
                verdict="skip",
                score=0.0,
                reasoning=_rejection_reasoning(gate),
                extracted_fields=fields,
            )

        card = Scorecard.model_validate(llm_scorecard(fields.model_dump(), gate.flags))
        verdict = "apply" if card.score >= APPLY_SCORE_THRESHOLD else "skip"

        return TriageResult(
            verdict=verdict,
            score=card.score,
            reasoning=_scored_reasoning(card, gate, verdict),
            extracted_fields=fields,
        )


def run_triage(raw_text: str) -> TriageResult:
    """Module-level entry point for the Gig Triage Agent.

    This is the callable Phase 3 wraps in an `@tool` for the Supervisor.
    """
    return GigTriageAgent().run(raw_text)


# --- Phase 3 (ORC-02): Supervisor-facing placeholder builder -----------------
# Constructs (does not invoke) the Strands Agent the Supervisor wraps
# agents-as-tools on the live TRIAGE_BACKEND=supervisor path. Construction
# performs NO network call (Pitfall 2, RESEARCH.md) -- only invoking the
# returned Agent touches Bedrock, which is what lets the offline construction
# test pass without AWS credentials.

MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
REGION = os.environ.get("AWS_REGION", "us-east-1")


def build_gig_triage_agent() -> Agent:
    """Construct (do not invoke) the Gig Triage specialist Agent."""
    return Agent(
        name="gig_triage_agent",
        model=BedrockModel(model_id=MODEL_ID, region_name=REGION),
        system_prompt=(
            "You are the Gig Triage specialist (Phase 2 placeholder). Call "
            "placeholder_kill_switch_check with the job's budget and "
            "description, then return its result."
        ),
        tools=[placeholder_kill_switch_check],
        structured_output_model=TriageSlice,
    )
