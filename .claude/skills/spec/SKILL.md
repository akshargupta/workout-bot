---
name: spec
description: Turn a feature idea, bug report, error dump, or backlog item into a numbered spec — PRD + implementation plan + test plan — that waits for human approval before any code is written. Use when the user wants new work specced out, references a backlog/ file, or pastes an error they want fixed properly.
argument-hint: [idea, backlog file path, or pasted error]
---

Create a spec from this input: $ARGUMENTS

If no input was given, list `backlog/` and ask which item to spec.

## Steps

1. **Understand the ask.** If the input is a file path, read the file. Read the code the change would touch. List `specs/` to find the next number NNN and check whether an existing spec already covers this — if one does, say so and stop.
2. **Clarify before writing.** If scope, behavior, or constraints are ambiguous, ask the user targeted questions (AskUserQuestion) first. Do not guess on product decisions.
3. **Create `specs/NNN-<slug>/`** with exactly three files:

   **`prd.md`** — the what and why:
   - Header: `Status: Draft`, date, source (backlog file / conversation / error)
   - Problem / motivation
   - Goals and Non-goals
   - User-visible behavior
   - **Acceptance criteria** — numbered, individually testable statements. These are the contract that implementation, code review, and tests are all judged against.
   - Open questions — if any remain, the spec is not approvable; surface them to the user

   **`plan.md`** — the how:
   - Files to create/modify, in order
   - Step-by-step implementation sequence
   - Data model / schema changes
   - Risks and edge cases
   - What is deliberately deferred

   **`tests.md`** — the proof, two sections:
   - **Automated** — tests to be written during /implement, each mapped to an acceptance-criterion number
   - **Manual script** — a numbered checklist the human runs by hand after implementation: exact commands to type, exact things to say to the agent, expected observable outcome for each. Write it so a tired person can follow it mechanically.

4. **If the input was a backlog file**, move it into the spec dir as `source.md`.
5. **Stop.** Print the spec path and a ≤5-line summary. Ask the user to read all three files and either approve or request changes. Do NOT implement anything. Do NOT edit code. The approval gate is the whole point of this workflow.

When the user approves (any clear "approved"/"looks good, go"): flip `Status: Draft` → `Status: Approved` in prd.md and tell them the next step is `/implement specs/NNN-<slug>`.

For bug/error inputs: acceptance criteria are "the failing case now behaves correctly"; the repro goes in tests.md's manual script.
