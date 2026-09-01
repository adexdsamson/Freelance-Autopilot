# Collaboration Guide — Two Engineers on GSD

Freelance Autopilot is built by **two engineers** using the GSD (Getting Stuff Done)
spec-driven workflow. This document explains how we work in parallel without colliding.

## Model: shared roadmap, per-phase branches

- **One shared plan.** `PROJECT.md`, `ROADMAP.md`, `REQUIREMENTS.md`, and the research
  live in `.planning/` and are committed to git (`commit_docs: true`). Both engineers
  read the same specs.
- **Per-phase git branches.** GSD is configured with `git.branching_strategy: "phase"`.
  When a phase is executed, GSD creates/switches to a branch named
  `gsd/phase-<N>-<slug>` (e.g. `gsd/phase-02-gig-triage-agent-standalone`). All of that
  phase's code commits land on that branch.
- **Per-phase worktrees.** `worktree.baseRef: "head"` — phase worktrees fork off HEAD, so
  each engineer can have a phase checked out in its own working directory.
- **One PR per phase.** Each phase branch is opened as its own pull request and reviewed
  independently. This keeps the two engineers' work isolated and reviewable.

## Phase ownership (claim before you start)

To avoid two people planning/executing the same phase, **claim a phase** by adding your
name to the table below in a quick commit before running `/gsd-plan-phase <N>`.

| Phase | Title | Owner | Status |
|-------|-------|-------|--------|
| 1 | Foundations — Engagement Record & Strands/Bedrock spike | Engineer A | planning |
| 2 | Gig Triage Agent (standalone) | _unclaimed_ | pending |
| 3 | Supervisor Wiring + `/capture` | _unclaimed_ | pending |
| 4 | Chrome Extension Capture UI | _unclaimed_ | pending |
| 5 | Proposal-Contract Agent + `/advance` | _unclaimed_ | pending |
| 6 | Ops Agent, Fixtures & Full Supervisor Wiring | _unclaimed_ | pending |
| 7 | Full Demo Verification & Submission Docs | _unclaimed_ | pending |
| 8 | AgentCore Deployment (optional, cut-first) | _unclaimed_ | pending |

**Dependency note (from the research):** Phase 3 depends on Phases 1+2; Phase 6 depends on
Phase 5's SOW schema. Phase 4 (extension) can run in parallel with backend phases once
Phase 3's `/capture` contract is stable. Coordinate on these before parallelizing.

## Onboarding the second engineer

Engineer B, to join:

1. Clone the repo and check out the shared branch that carries the planning docs.
2. GSD Core is already committed under `.claude/` — you have all `/gsd-*` commands
   immediately, no install needed. (If you want it globally too: `npx -y @opengsd/gsd-core@latest --claude --global`.)
3. Read `.planning/PROJECT.md`, `.planning/ROADMAP.md`, and `.planning/research/SUMMARY.md`.
4. Claim an unclaimed phase in the table above (commit the change).
5. Run `/gsd-plan-phase <N>` then `/gsd-execute-phase <N>` — GSD will branch to
   `gsd/phase-<N>-<slug>` for your code.
6. Open a PR from that phase branch. Keep `.planning/` changes (shared specs) coordinated
   with Engineer A to avoid merge churn.

## Rules of the road

- **Never execute a phase someone else has claimed** without checking in.
- **Planning-doc edits** (`.planning/PROJECT.md`, `ROADMAP.md`, `REQUIREMENTS.md`) are
  shared surface — announce big changes so the other engineer can rebase.
- **One phase = one branch = one PR.** Don't stack unrelated phases on one branch.
- Run `/gsd-progress` to see where the project stands before picking up work.

---
*GSD config for this model: `git.branching_strategy: "phase"`, `worktree.baseRef: "head"`, `commit_docs: true`, `parallelization: true`.*
