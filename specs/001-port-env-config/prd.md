# 001 — Port .env config and stand up the Python runtime

Status: Done
Date: 2026-07-27
Approved: 2026-07-27
Implemented: 2026-07-27 (branch `spec/001-port-env-config`; review in [review.md](review.md))
Signed off: 2026-07-28 (verdict in [signoff.md](signoff.md); merged to `main`)
Source: [source.md](source.md) (backlog item `2026-07-27-port-env-from-original-folder`)

## Problem / motivation

`workout-bot` is currently spec and wiki scaffolding — no code, no config, no runtime.
Nothing can execute until the Claude API credentials and endpoint exist locally and
something can read them. This blocks every subsequent spec that talks to the model.

An existing `.env` holding a working API key and base URL lives at
`~/Documents/archive/ai-project/.env`. That file is the only thing being taken from
that folder: **it is a file to copy, not a project to imitate.** No structure,
stack choice, or convention from `ai-project` carries over.

## Goals

- A working local `.env` carrying the Claude API key and base URL.
- A committed `.env.example` so the required config is documented for a fresh clone.
- A Python runtime this project owns: a `uv`-managed virtualenv on a pinned version.
- One small, tested module that loads and validates that config and hands back a
  configured `anthropic` client.

## Non-goals

- Any workout, training, or bot feature. This spec is plumbing only.
- An `ANTHROPIC_MODEL` variable. Model choice is a per-call decision, not config.
- Any network call to the Claude API from application code. `build_client()` only
  *constructs* a client; the one live call in this spec is a manual test step.
- CI, linting, formatters, or type-checking config. Later specs.

## Decisions taken

**Runtime: Python 3.14.5**, pinned via a committed `.python-version` and managed by
`uv`. Determined empirically, not assumed — `anthropic` 0.120.0 declares
`Requires-Python: >=3.9` and is pure Python, and a 3.13-vs-3.14 comparison produced
byte-identical dependency trees (`pydantic` 2.13.4 / `pydantic-core` 2.46.4), all
prebuilt wheels, no source builds, with the heavy `anthropic[mcp]` extra resolving
cleanly on 3.14. With no compatibility axis to trade off, the newest stable wins.

**Variable names: `ANTHROPIC_API_KEY` and `ANTHROPIC_BASE_URL`.** These are the
Anthropic SDK's own environment variables — a zero-arg `anthropic.Anthropic()` reads
both automatically. No renaming is needed; the names in the source `.env` already match.

**`python-dotenv` is required.** The SDK reads the *process environment*, and Python
does not load `.env` files into it automatically. `python-dotenv` is the bridge.

## User-visible behavior

A developer clones the repo, copies `.env.example` to `.env`, fills in the two values,
runs `uv sync`, and `uv run pytest` passes. Importing `workout_bot.config` and calling
`load_config()` returns validated config; `build_client()` returns a ready
`anthropic.Anthropic`. A missing key produces a named error that says which variable is
missing, not a `KeyError` traceback.

## Acceptance criteria

Config files

1. `.env` at the repo root is a byte-for-byte copy of `~/Documents/archive/ai-project/.env`.
2. `.env` is untracked and ignored: `git check-ignore .env` exits 0, and `git status --porcelain` never lists it.
3. `.env.example` is committed at the repo root, documents `ANTHROPIC_API_KEY` and `ANTHROPIC_BASE_URL` with empty placeholder values plus explanatory comments, and contains no real credential.

Runtime

4. A `uv`-managed virtualenv exists at `.venv` running Python 3.14.5, pinned by a committed `.python-version`.
5. `pyproject.toml` sets `requires-python = ">=3.14"` and declares runtime dependencies `anthropic` and `python-dotenv`, plus dev dependency `pytest`.
6. `.gitignore` covers `.venv/`, `__pycache__/`, and `.pytest_cache/`, retains `.env`, and no longer carries the stale `node_modules/` or `dist/` entries.

Config module

7. `workout_bot.config.load_config()` loads `.env` into the process environment and returns a frozen `Config` with fields `api_key: str` and `base_url: str | None`.
8. A variable already set in the real process environment wins over the same key in `.env` (dotenv loaded with `override=False`).
9. A missing or empty `ANTHROPIC_API_KEY` raises `MissingConfigError` whose message names the variable — not a bare `KeyError`.
10. A missing or empty `ANTHROPIC_BASE_URL` yields `base_url is None`. It is not an error and never an empty string.
11. `repr(config)` and `str(config)` do not contain the API key value.
12. `build_client(cfg)` returns an `anthropic.Anthropic`. When `base_url is None` it omits the argument so the SDK default applies; when set, it is passed through and reflected on the client.

Project wiring

13. `uv run pytest` exits 0 with every test in `tests/` passing.
14. The Commands section of `CLAUDE.md` lists the real install and test commands.
15. `wiki/configuration.md` exists as an OKF v0.2 concept, is linked from `wiki/index.md`, and `wiki/log.md` has an appended entry.

## Open questions

None. The one open question at draft time — whether to drop the stale `node_modules/`
and `dist/` lines left over from before the runtime was decided — was answered **yes** at
approval, and is now folded into acceptance criterion 6.
