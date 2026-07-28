---
type: Playbook
title: Spec-driven development loop
description: The backlog → spec → approve → implement → review → signoff cycle used in this repo.
resource: ../CLAUDE.md
tags: [workflow, process, skills]
generated:
  by: claude-code/claude-opus-5
  at: 2026-07-27T10:43:01Z
---

# Spec-driven development loop

All non-trivial work follows a human-gated cycle. Rules of record live in
[`CLAUDE.md`](../CLAUDE.md); the steps are implemented as skills in
`.claude/skills/`.

## The loop

1. **Capture** — drop an idea, bug, or error into `backlog/` (one file each).
2. **`/spec`** — produces `specs/NNN-slug/` with `prd.md` (numbered acceptance
   criteria = the contract), `plan.md`, and `tests.md` (automated + a manual
   script). Then it **stops**.
3. **Human approves** — `prd.md` flips to `Status: Approved`. Nothing is built
   before this.
4. **`/implement`** — branch `spec/NNN-slug`, code to the plan, write the tests,
   go green (every command under **Commands** in `CLAUDE.md`), update the wiki via
   `/wiki`, commit, then run the
   **[code-reviewer](../.claude/agents/code-reviewer.md)** agent → `review.md`.
5. **Human reviews** — read the diff and `review.md`, run the manual script.
6. **`/signoff`** — in-scope fixes land on the branch; new-scope requests become
   fresh `backlog/` files (feeding step 1). On sign-off, merge to `main`,
   `Status: Done`.

## Statuses

`Draft → Approved → Implemented — awaiting human review → Done` (or `Rejected`).

## Invariants

- Never implement from a `Draft` spec.
- Merge to `main` happens only in `/signoff`, after human sign-off — never
  during `/implement`.
- Acceptance criteria are the single contract judged by code, tests, and review.
- New ideas go to `backlog/`, not straight into code.

## Wiki upkeep

When a spec changes architecture, storage, tools, or schemas, update the matching
concept here and add a line to [log.md](log.md). This is step 5 of `/implement`
and a line on its checklist, so it is answered every cycle rather than remembered
— the `/wiki` skill carries the OKF format rules. Good candidates to spin off as
backlog items: "add a test runner," "enforce OKF conformance in CI."
