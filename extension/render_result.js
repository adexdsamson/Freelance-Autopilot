/**
 * Shared verdict renderer, used by BOTH the popup (paste mode) and the
 * capture window (screenshot mode).
 *
 * Extracted rather than copied: the two surfaces must agree on what an
 * `apply` looks like, how a missing budget reads, and — most importantly —
 * that untrusted content only ever reaches the DOM through textContent. Two
 * copies would drift on exactly those points.
 *
 * Exposed as a global because MV3 classic scripts have no module loader here.
 */
const FAResult = (() => {
  /**
   * Accept either shape the backend might return: the whole EngagementRecord
   * (verdict nested under `triage`, PRD 6.2) or the bare CaptureResponse
   * (verdict at the top level).
   */
  function normalize(data) {
    const triage =
      data && typeof data.triage === "object" && data.triage !== null ? data.triage : data;
    return {
      verdict: triage?.verdict ?? null,
      score: triage?.score ?? null,
      reasoning: triage?.reasoning ?? "",
      extracted: data?.extracted_fields ?? triage?.extracted_fields ?? data?.job ?? null,
      engagementId: data?.engagement_id ?? null,
    };
  }

  function formatBudget(extracted) {
    if (extracted.budget === null || extracted.budget === undefined) return "not stated";
    const amount = `$${Number(extracted.budget).toLocaleString()}`;
    return extracted.budget_type === "hourly" ? `${amount}/hr` : amount;
  }

  function formatClientStats(stats) {
    if (!stats || typeof stats !== "object") return null;
    const parts = [];
    if (stats.total_spend !== null && stats.total_spend !== undefined) {
      parts.push(`$${Number(stats.total_spend).toLocaleString()} spent`);
    }
    if (stats.hire_rate !== null && stats.hire_rate !== undefined) {
      parts.push(`${Math.round(stats.hire_rate * 100)}% hire rate`);
    }
    if (stats.payment_verified === true) parts.push("payment verified");
    if (stats.payment_verified === false) parts.push("payment NOT verified");
    return parts.length ? parts.join(" · ") : null;
  }

  /** Render into the standard result elements. Elements are passed in so each
   *  surface owns its own markup. */
  function render(data, els) {
    const { verdict, score, reasoning, extracted, engagementId } = normalize(data);

    const verdictText = verdict ? String(verdict) : "unknown";
    els.badge.textContent = verdictText;
    els.badge.className = "badge";
    if (verdictText === "apply" || verdictText === "skip") {
      els.badge.classList.add(`badge--${verdictText}`);
    }

    els.score.textContent =
      score === null || score === undefined ? "" : `Score ${score}/100`;
    els.reasoning.textContent = reasoning || "No reasoning returned.";

    els.extracted.replaceChildren();
    const define = (term, value) => {
      const dt = document.createElement("dt");
      dt.textContent = term;
      const dd = document.createElement("dd");
      // textContent, never innerHTML: this is a posting read off an untrusted
      // page plus model output. Neither is ever parsed as markup.
      dd.textContent = value;
      els.extracted.append(dt, dd);
    };

    if (extracted && typeof extracted === "object") {
      if (extracted.title) define("Title", extracted.title);
      define("Budget", formatBudget(extracted));
      const clientSummary = formatClientStats(extracted.client_stats);
      if (clientSummary) define("Client", clientSummary);
    }
    if (engagementId) define("Engagement", engagementId);
  }

  return { normalize, formatBudget, formatClientStats, render };
})();

// Node/pytest can't see this, but keeping the reference silences bundler-style
// "unused" warnings in editors and documents the intended global.
if (typeof window !== "undefined") window.FAResult = FAResult;
