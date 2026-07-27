---
type: Component
title: Configuration and runtime
description: How Claude API credentials reach the SDK, and the Python runtime that loads them.
resource: ../src/workout_bot/config.py
tags: [configuration, environment, runtime, secrets]
generated:
  by: claude-code/claude-opus-5
  at: 2026-07-27T12:31:58Z
---

# Configuration and runtime

## Runtime

Python **3.14.5**, pinned in [`.python-version`](../.python-version) and managed by
[uv](https://docs.astral.sh/uv/). Dependencies and the dev group are declared in
[`pyproject.toml`](../pyproject.toml) and locked in `uv.lock`; the virtualenv lives at
`.venv/` and is gitignored.

The version was chosen empirically rather than assumed. `anthropic` declares
`Requires-Python: >=3.9` and is pure Python, and a 3.13-vs-3.14 comparison produced
identical dependency trees — same `pydantic` and `pydantic-core`, all prebuilt wheels,
no source builds. With no compatibility axis to trade off, the newest stable won.

The project uses a **src layout**, so `uv sync` installs `workout-bot` itself into the
venv. Run everything through `uv run`; a bare `pytest` cannot import `workout_bot`.

## The two variables

| Variable | Required | Meaning |
|---|---|---|
| `ANTHROPIC_API_KEY` | yes | Claude API key |
| `ANTHROPIC_BASE_URL` | no | API endpoint; unset means the public Claude API |

Both names are the **Anthropic SDK's own environment variables** — a zero-argument
`anthropic.Anthropic()` reads them without help. Nothing here renames or wraps them,
which is why porting an existing `.env` needed no translation.

## Why python-dotenv is in the dependency list

The SDK reads the *process environment*. Python does not load `.env` files into that
environment on its own — unlike Node, where tooling often does it implicitly. So
`python-dotenv` is the bridge, and without it a populated `.env` would simply be
invisible to the SDK.

## Precedence

`load_dotenv(..., override=False)` means **an already-exported variable wins over the
same key in `.env`**. That ordering is deliberate: it lets CI, a shell export, or a
one-off `env VAR=… uv run …` override the file without editing it.

## Empty is the same as unset

`load_config()` strips each value and collapses empty and whitespace-only strings to
`None`. Two consequences:

- A blank `ANTHROPIC_API_KEY` raises `MissingConfigError` naming the variable, rather
  than sending an empty key and failing later with an opaque 401.
- A blank `ANTHROPIC_BASE_URL` yields `None` **and is deleted from `os.environ`**.

That deletion is load-bearing, and the reason is worth stating precisely. The SDK
resolves the endpoint as:

    base_url kwarg  >  ANTHROPIC_BASE_URL in the environment  >  https://api.anthropic.com

Only an *absent* variable reaches that final default — an empty string is accepted as a
real base URL. Since `load_dotenv` writes a blank `ANTHROPIC_BASE_URL=` line straight
into `os.environ`, following `.env.example`'s "leave it empty for the public API"
instruction would otherwise build a client pointed at `""`, which fails every request
with an opaque connection error. Deleting the variable makes the process environment
agree with the returned `Config`, so the SDK's own fallback fires.

Passing `base_url=None` is exactly equivalent to omitting the argument — the SDK
normalizes `None` before the environment lookup — so `build_client()` just passes the
value straight through with no branch.

## Secrets

`.env` is gitignored and never committed. [`.env.example`](../.env.example) is the
committed template and holds only empty placeholders.

`Config` overrides `__repr__` to print `api_key=<redacted>`; the frozen dataclass would
otherwise generate one that prints the key in full, so any log line, traceback, or REPL
echo of a `Config` would leak it. `str()` falls back to `__repr__`, so the single
override covers both. A test asserts on the *absence of the secret substring*, so
reverting to the generated repr fails the suite rather than passing quietly.

The redaction covers representation, not extraction — `dataclasses.asdict(cfg)`,
`astuple(cfg)`, and `vars(cfg)` all still return the key in clear. That is correct
(code that asks for the field wants the field), but it means **never log a `Config`
through `asdict`**; log the object itself.

## Related

* [Spec-driven development loop](spec-workflow.md) — the cycle that produced this.
