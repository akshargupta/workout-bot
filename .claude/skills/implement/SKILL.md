---
name: implement
description: Implement an approved spec from specs/ — branch, code, automated tests, commit, then automatic code review by the code-reviewer agent. Refuses specs still in Draft. Use when the user asks to implement or build a spec.
argument-hint: [specs/NNN-slug]
---

Implement the spec: $ARGUMENTS

If no spec was named: if exactly one spec has `Status: Approved`, use it; otherwise list candidates and ask.

## Gate

Read `prd.md` in the spec dir first. If `Status:` is not `Approved`, STOP and tell the user which status it has. Draft specs are never implemented — the user can approve in one word if they mean to.

## Steps

Copy this checklist into your response and check items off as you go:

```
Implementation progress:
- [ ] Gate passed: spec Status is Approved
- [ ] Branch spec/NNN-<slug> created from clean main
- [ ] Implemented per plan.md (divergences surfaced, plan updated)
- [ ] Automated tests from tests.md written
- [ ] Every command under Commands in CLAUDE.md green (actually run)
- [ ] Wiki updated via /wiki (concepts + log.md) — or explicitly N/A, with reason
- [ ] Committed on branch
- [ ] code-reviewer run → review.md saved, blockers resolved
- [ ] Handoff: diff stat + verdict + manual script printed
```

1. **Branch.** Require a clean working tree on `main` (if dirty, stop and ask). Then `git checkout -b spec/NNN-<slug>`.
2. **Implement** what plan.md says — no more, no less. If reality diverges from the plan (missing API, wrong assumption, better approach discovered), stop, explain the divergence to the user, and update plan.md before continuing. The spec must stay truthful to what was actually built.
3. **Write the automated tests** listed in tests.md, each mapped to its acceptance-criterion number.
4. **Verify.** Run every command listed under **Commands** in `CLAUDE.md` — that section is the definition of "green" for this repo. Fix until they all pass. Report real output — never claim green without having run the commands this session.
5. **Wiki.** Ask whether this change altered architecture, storage, tools, or schemas. If it did, run `/wiki` to update the affected concepts and append to `wiki/log.md`, so the knowledge base ships with the code rather than drifting behind it. If it genuinely changed none of those, say so explicitly and why — "N/A" without a reason is not an answer.
6. **Commit** on the branch: `spec NNN: <summary>`. Code, tests, and wiki updates go in the same commit.
7. **Code review.** Launch the `code-reviewer` agent (Agent tool, subagent_type per its definition) with: the spec dir path, the branch name, and instructions to review the full diff vs main. Save its report verbatim to `specs/NNN-<slug>/review.md`. If it reports blocking issues: fix, re-run step 4, commit, and have it re-review the delta. Do not silently dismiss findings — if a finding is wrong, say why in the handoff.
8. **Handoff.** Set prd.md to `Status: Implemented — awaiting human review`, commit, then print for the user:
   - `git diff main...HEAD --stat`, plus the command to see the full diff
   - the reviewer's verdict line and blocking/nit counts (full report is in review.md)
   - the **Manual script** section of tests.md, verbatim
   - closing line: "When you've reviewed, run `/signoff specs/NNN-<slug> <verdict + notes>`"

Never merge to main here. Merging happens only in /signoff after human sign-off.
