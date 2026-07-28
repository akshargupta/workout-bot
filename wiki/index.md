---
okf_version: "0.2"
---

# workout-bot knowledge base

An [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
bundle: one markdown file per concept, each with a required `type` in its
frontmatter. Humans read and edit these; agents can consume them as curated
context. Authoring conventions live in [CLAUDE.md](../CLAUDE.md).

## Components

* [Configuration and runtime](configuration.md) - how Claude API credentials reach the SDK, and the Python runtime that loads them.

## Playbooks

* [Spec-driven development loop](spec-workflow.md) - the backlog → spec → approve → implement → review → feedback cycle used in this repo.
