# workout-bot

A workout bot built on the Claude Messages API.

Founding spec: [001-port-env-config](specs/001-port-env-config/prd.md) — established the
Python runtime and the API configuration contract.

## Commands

These commands ARE the definition of "green" — /implement runs every one of them
before handing work back.

- `uv sync` — create/refresh `.venv` and install all dependencies (incl. dev)
- `uv run pytest` — run the full test suite

Always go through `uv run`; a bare `pytest` misses the project install and fails to
import `workout_bot`.

## Knowledge base — OKF wiki

`wiki/` is the project's knowledge base — one curated concept per markdown file,
in [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
v0.2. **`wiki/index.md` is the map**: read it when you need background on how
something works, and follow the link to the concept rather than reverse-engineering
it from source.

- When a change alters architecture, storage, tools, or schemas, the matching
  concept **must** be updated in the same commit, and `wiki/log.md` appended.
  Stale concepts are worse than no concepts.
- Run `/wiki` to write or update one — it carries the OKF frontmatter fields,
  the reserved-file shapes, and the log conventions. Don't hand-author wiki
  files from memory; the format has rules that are easy to get subtly wrong.

## Development workflow — spec-driven, human-gated

All non-trivial work follows this cycle:

```
backlog/ item ──▶ /spec ──▶ human approves prd ──▶ /implement ──▶ code-reviewer agent
     ▲                                                                    │
     │                                                       human reads diff + review.md,
     └──── new-scope items ◀── /feedback ◀─────────────────── runs manual script in tests.md
                    (merge on sign-off)
```

Rules — these override default behavior:

1. **Never implement from a Draft spec.** `prd.md` must say `Status: Approved`.
   If asked to "just build it", point at the gate — approval takes one word.
2. **Trivial fixes** (typo-level, no behavior change) may skip the cycle, but say
   explicitly that the cycle is being skipped.
3. Every spec lives in `specs/NNN-slug/`: `prd.md` + `plan.md` + `tests.md`,
   joined after implementation by `review.md` and `feedback.md`.
   Statuses: `Draft → Approved → Implemented — awaiting human review → Done`
   (or `Rejected`).
4. Implementation happens on branch `spec/NNN-slug`. Merge to main only in
   /feedback, after human sign-off — never during /implement.
5. The `code-reviewer` agent reviews every /implement before human handoff; its
   report is saved to the spec dir. Findings get fixed or explicitly rebutted,
   never silently dropped.
6. The numbered acceptance criteria in prd.md are the contract. Implementation,
   tests, and review are all judged against them. Scope creep is flagged, not
   quietly shipped.
7. New ideas and bugs go to `backlog/` (one file each) — not straight into code.
