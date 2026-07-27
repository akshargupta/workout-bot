---
name: feedback
description: Record the human's review of an implemented spec, fix in-scope issues, spin out-of-scope requests into backlog items, and close the loop (merge on sign-off, iterate otherwise). Use after the user has read the diff and run the manual test script.
argument-hint: [specs/NNN-slug] [verdict and notes]
---

Process review feedback: $ARGUMENTS

1. **Record.** Append the user's feedback verbatim, with today's date, to `specs/NNN-<slug>/feedback.md` (create if missing).
2. **Triage** each point, confirming the split with the user:
   - **In-scope fix** — a gap against the acceptance criteria, or a small correction: fix it on the spec branch now, re-run typecheck/tests/smoke, commit. For non-trivial fixes, have the `code-reviewer` agent re-check the delta and append to review.md.
   - **New scope** — a feature request or behavior change beyond the PRD: write it as a new file in `backlog/` (one file per item, `YYYY-MM-DD-slug.md`, enough context to /spec it cold in a future session). Do not implement it now, even if it's tempting.
3. **Close or iterate:**
   - **Sign-off** → `git checkout main && git merge --no-ff spec/NNN-<slug>`, set prd.md `Status: Done`, commit, and list any backlog items created — those are the seeds of the next cycle.
   - **Fixes were made** → hand back the updated diff summary + manual script for another review round; status stays `Implemented — awaiting human review`.
   - **Rejected** → set `Status: Rejected`, record why in feedback.md, leave the branch unmerged.
