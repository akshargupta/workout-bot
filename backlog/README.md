# Backlog

The inbox of the spec cycle. One file per item — a feature idea, a bug, a pasted error
dump, a half-formed thought. No required format; more context makes a better spec.
Useful ingredients: what happened or what you want, why it matters, repro steps or
error text if applicable.

Name files `YYYY-MM-DD-short-slug.md`.

Start the cycle with:

    /spec backlog/<file>.md

When an item gets specced, it moves into its spec dir as `source.md`, so whatever
remains in this folder is exactly the work not yet specced.
