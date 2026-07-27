---
name: wiki
description: Author or update a concept in the wiki/ knowledge base — the OKF v0.2 frontmatter fields, reserved-file shapes, and log conventions. Use whenever writing or editing any file under wiki/, or when a change to architecture, storage, tools, or schemas needs to be reflected in the knowledge base.
argument-hint: [concept slug or what changed]
---

Update the knowledge base for: $ARGUMENTS

`wiki/` is an [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
bundle authored against **OKF v0.2**. The bundle root is `wiki/` itself.

## Steps

1. **Read `wiki/index.md`** to see which concepts exist. If one already covers
   the subject, update it — do not create a near-duplicate.
2. **Write or edit the concept**, following the rules below. Keep it accurate to
   the source: a wrong wiki is worse than none. Describe what the code *is*, not
   what a spec hoped it would be.
3. **If the concept is new**, add a bullet to the right section of `index.md`.
4. **Append to `log.md`** — always, for any meaningful add or change.
5. **Report** which concepts changed and the log line you added.

## Concept files

Every file other than `index.md` and `log.md` is a concept: one concept per
file, kebab-case slug for the filename, `title` frontmatter as the display name.

`type` is the **only required field** — a short descriptive string
(`Component`, `Reference`, `Data Model`, `Runbook`, `Playbook`, …). There is no
central registry; pick something self-explanatory and reuse existing values
where they fit.

Recommended: `title`, `description` (one sentence), `resource`, `tags`.

```yaml
---
type: Component
title: Per-user file storage
description: How workout documents are written to and read from disk.
resource: ../src/store.ts
tags: [storage, persistence]
generated:
  by: claude-code/claude-opus-5
  at: 2026-07-27T10:43:01Z
---
```

- **`resource`** is the asset the concept documents, resolved **relative to the
  wiki file** — so `../src/store.ts`, not `src/store.ts`. Omit it entirely for
  abstract concepts that document no single file.
- **Provenance:** `generated: { by, at }` records who wrote the content;
  `verified: [{ by, at }]` is a list of confirmations against the source. `at`
  is ISO 8601. Actors are `human:<id>`, `<producer>/<version>` (agents), or
  `process:<id>`. A concept with a `human:` entry in `verified` is
  human-reviewed; without any `verified`, it is unverified.
- **Lifecycle (optional):** `status` is `draft` | `stable` | `deprecated`
  (default `stable`). `stale_after: YYYY-MM-DD` marks content that expires.
- **Never use `timestamp`** — it is a deprecated v0.1 field, superseded by
  `generated.at`.
- **Links between concepts stay relative** (`spec-workflow.md`). The spec
  recommends bundle-relative `/`-paths, but those resolve to the repo root in
  editors and on GitHub, breaking the link in both. This is a deliberate,
  conformant deviation — relative paths are explicitly allowed.

## Reserved files

`index.md` and `log.md` are OKF reserved files with a fixed shape. Getting these
wrong is the one thing that makes the whole bundle non-conformant.

**`index.md`** — carries no frontmatter, with exactly one exception: the
bundle-root index may carry `okf_version` and nothing else. The body is one or
more sections of links:

```markdown
## Components

* [Per-user file storage](storage-vfs.md) - how workout documents are persisted.
```

**`log.md`** — no frontmatter. Newest first, grouped under ISO date headings:

```markdown
# Directory Update Log

## 2026-07-27
* **Update**: Revised [storage-vfs](storage-vfs.md) for the new write path.
* **Creation**: Added [agent-tools](agent-tools.md).
```

Date headings MUST be `YYYY-MM-DD`. Verbs to use: **Creation**, **Update**,
**Initialization**.

## Conformance

A bundle is conformant when: every non-reserved `.md` has parseable YAML
frontmatter; every frontmatter block has a non-empty `type`; and both reserved
files follow the shapes above. Consumers must tolerate unknown types, unknown
keys, and broken links — so those are quality problems, not conformance ones,
and still worth fixing.
