# Specs

One directory per unit of work: `specs/NNN-slug/`, numbered in the order they are
created. Written by `/spec`, never by hand-waving.

Files, in the order they appear:

| File | Written by | When |
|---|---|---|
| `source.md` | `/spec` | if the spec came from a `backlog/` item (moved, not copied) |
| `prd.md` | `/spec` | the what and why — **numbered acceptance criteria are the contract** |
| `plan.md` | `/spec` | the how — files, sequence, risks, what's deferred |
| `tests.md` | `/spec` | automated tests + a manual script the human runs by hand |
| `review.md` | `code-reviewer` agent | end of `/implement`, saved verbatim |
| `feedback.md` | `/feedback` | the human's verdict, verbatim, dated |

`prd.md` status ladder: `Draft → Approved → Implemented — awaiting human review → Done`
(or `Rejected`). Nothing is implemented before `Approved`; nothing merges to `main`
before sign-off in `/feedback`.
