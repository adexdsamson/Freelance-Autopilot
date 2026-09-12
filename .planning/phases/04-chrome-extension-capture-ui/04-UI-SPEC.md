# Phase 4 UI Spec: Chrome Extension Capture Popup

**Surface:** Chrome MV3 extension popup (`extension/popup.html`)
**Requirements:** CAP-01, CAP-03

## Constraints that drive the design

- Chrome sizes a popup to its content, capped at 800×600. Body is fixed at
  **380px** — the conventional width, and narrow enough that Chrome never adds a
  horizontal scrollbar.
- MV3's CSP forbids inline `<script>` and inline `on*=` handlers. Every listener
  is attached in `popup.js`. Enforced by test.
- The popup follows the **system** theme, not the site's. Both light and dark
  palettes are defined; dark is a `prefers-color-scheme` override of the same
  tokens.
- Untrusted content (the paste) and model output (the reasoning) reach the DOM
  only through `textContent`. Enforced by test.

## States

The popup is in exactly one of four states; `showState()` is the only thing that
changes which.

| State | Shows | Entered when |
|---|---|---|
| `form` | textarea, optional URL, "Run triage" | popup opens; "Back"; "Capture another" |
| `pending` | spinner + "Triaging…" + what is happening | submit with non-empty text |
| `result` | verdict badge, score, reasoning, extracted fields | backend returned 2xx JSON |
| `error` | red card, message, optional detail, "Back" | empty paste, transport failure, non-2xx, non-JSON |

`[hidden] { display: none !important }` is required, not cosmetic: `.panel` sets
`display: flex`, which would otherwise beat the `hidden` attribute's UA
`display: none` and leave "hidden" panels on screen.

## Verdict badge

| Verdict | Background | Text | Why |
|---|---|---|---|
| `apply` | `--apply-bg` green | `--apply-text` | The one outcome that costs a Connect — it should read as a go |
| `skip` | `--skip-bg` red | `--skip-text` | |
| anything else | neutral surface | muted | A verdict the popup does not recognise must not be styled as either |

Colour is never the only signal — the badge carries the verdict word itself, and
the score sits beside it.

## Extracted-fields block

A two-column `<dl>`, rendered only for keys actually present:

- **Title** — omitted if absent
- **Budget** — `$8,500` or `$95/hr` (from `budget_type`), else "not stated"
- **Client** — spend · hire rate · payment-verified, joined by `·`; omitted if
  nothing is known. `payment_verified: false` renders "payment **NOT** verified"
  rather than being dropped, because an unverified client is the signal.
- **Engagement** — the returned `engagement_id`, so a demo can cross-reference
  the persisted record

## Accessibility

- Every control has a `<label>`; the spinner is `aria-hidden` decoration beside
  real text.
- Focus is a 2px accent outline, never removed.
- `prefers-reduced-motion` slows the spinner rather than removing the only
  indication that work is happening.
