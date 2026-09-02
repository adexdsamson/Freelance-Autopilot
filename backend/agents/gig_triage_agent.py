"""The Gig Triage Agent — Stage 1 specialist (TRI-04).

Fully autonomous by design: it always returns a verdict and never asks a
human anything. `TriageResult` has no escalation fields and forbids extras,
so that autonomy is structural rather than a convention someone can drift
from. Stage 2's Proposal-Contract Agent is where escalation becomes a
first-class outcome.

Why a deterministic driver instead of an Agent with tools=[...]
----------------------------------------------------------------
Phase 1 (D-07) established agents-as-tools as the orchestration mechanism,
and Phase 3 will wrap `run_triage` in an `@tool` so the Supervisor calls this
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

This module must never import the store (REC-03/D-05).
"""
from __future__ import annotations

from models.triage import ExtractedJobFields, KillSwitchResult, Scorecard, TriageResult
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
