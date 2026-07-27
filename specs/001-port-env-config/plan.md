# 001 — Implementation plan

Branch: `spec/001-port-env-config`

## Files to create / modify, in order

| # | Path | Action | Covers AC |
|---|---|---|---|
| 1 | `.python-version` | create — `3.14.5` | 4 |
| 2 | `pyproject.toml` | create | 5 |
| 3 | `.gitignore` | modify — add Python entries, drop Node leftovers | 6 |
| 4 | `.env` | create — verbatim copy, never committed | 1, 2 |
| 5 | `.env.example` | create — authored fresh, committed | 3 |
| 6 | `src/workout_bot/__init__.py` | create — empty package marker | — |
| 7 | `src/workout_bot/config.py` | create — the module | 7–12 |
| 8 | `tests/test_config.py` | create — the tests | 7–13 |
| 9 | `CLAUDE.md` | modify — fill in Commands | 14 |
| 10 | `wiki/configuration.md`, `wiki/index.md`, `wiki/log.md` | create / modify via `/wiki` | 15 |

## Step-by-step sequence

**1. Pin the interpreter and create the venv.**

```
echo 3.14.5 > .python-version
uv venv                      # reads .python-version, creates .venv
```

**2. Author `pyproject.toml`.** src-layout, so the build backend needs pointing at `src/`.

```toml
[project]
name = "workout-bot"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = ["anthropic>=0.120.0", "python-dotenv>=1.2.2"]

[dependency-groups]
dev = ["pytest>=9.1.1"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/workout_bot"]
```

Then `uv sync` to resolve and write `uv.lock` (commit the lock).

**3. Rewrite `.gitignore`.** Add `.venv/`, `__pycache__/`, `.pytest_cache/`; keep the
existing `.env` line — it is what satisfies AC 2 — and **drop `node_modules/` and
`dist/`**, leftovers from before the runtime was decided and inert on a Python project.
(Answered `yes` at approval; AC 6 now covers it.)

**4. Copy the `.env`.** A literal copy — do not open, reformat, reorder, or prune it:

```
cp ~/Documents/archive/ai-project/.env .env
```

Verify with `cmp` (AC 1) and `git check-ignore .env` (AC 2). The source file carries two
commented-out `LIFE_OS_*` lines from the old project; they stay, because "copy verbatim"
is the criterion and commented lines are inert. The loader simply never reads them.

**5. Author `.env.example`** by hand — it documents *this* project's two variables, so it
is not derived from the copied file and must never contain a real value.

**6. Write `src/workout_bot/config.py`.** Shape:

```python
from __future__ import annotations
from dataclasses import dataclass
import os
import anthropic
from dotenv import load_dotenv

class MissingConfigError(RuntimeError): ...

@dataclass(frozen=True)
class Config:
    api_key: str
    base_url: str | None
    def __repr__(self) -> str:                      # AC 11
        return f"Config(api_key=<redacted>, base_url={self.base_url!r})"

def load_config(env_file: str | os.PathLike[str] | None = None) -> Config:
    load_dotenv(env_file, override=False)            # AC 8: real env wins
    api_key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not api_key:                                  # AC 9
        raise MissingConfigError(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it in."
        )
    base_url = (os.environ.get("ANTHROPIC_BASE_URL") or "").strip() or None  # AC 10
    return Config(api_key=api_key, base_url=base_url)

def build_client(config: Config) -> anthropic.Anthropic:   # AC 12
    if config.base_url is None:
        return anthropic.Anthropic(api_key=config.api_key)
    return anthropic.Anthropic(api_key=config.api_key, base_url=config.base_url)
```

Two details that carry the design:

- `@dataclass(frozen=True)` generates a `__repr__` that would print the key; the explicit
  `__repr__` override replaces it. `str()` falls back to `__repr__`, so one override
  covers both halves of AC 11.
- `or None` after `.strip()` collapses unset, empty, and whitespace-only into a single
  `None` — the SDK must receive either a real URL or no argument at all, never `""`.

**7. Write `tests/test_config.py`.** See tests.md for the case list.

**8. Update `CLAUDE.md`** Commands with `uv sync` and `uv run pytest`.

**9. Run `/wiki`** to author `wiki/configuration.md` and append to `wiki/log.md`. Do not
hand-author these — CLAUDE.md is explicit that the OKF format has rules that are easy to
get subtly wrong.

## Data model / schema changes

None — no persistence in this spec. The only new "schema" is the two-variable env contract
fixed by `.env.example`.

## Risks and edge cases

| Risk | Handling |
|---|---|
| **Committing a real secret.** The single highest-consequence failure here. | `.env` is already gitignored (pre-existing line). AC 2 asserts it explicitly, and the manual script re-checks `git status` after staging. `.env.example` is authored by hand, never copied from `.env`. |
| Tests accidentally reading the developer's real `.env` and passing for the wrong reason. | `load_config()` takes an `env_file` parameter for exactly this. Every test uses `monkeypatch.delenv` on both keys plus a `tmp_path` env file — hermetic, no dependence on the machine. |
| `load_dotenv(override=False)` leaking state between tests via `os.environ`. | `monkeypatch` restores `os.environ` after each test automatically. |
| Base URL points at a gateway rather than the public API, so the live manual check behaves unexpectedly. | The manual step reports the endpoint it actually hit, so a surprise is visible rather than silent. Whatever the value is, it is passed through untouched. |
| src-layout package not importable in tests. | `uv sync` installs the project itself into `.venv`, so `import workout_bot` resolves. `uv run pytest` — not a bare `pytest` — is the command of record. |

## Deliberately deferred

- `ANTHROPIC_MODEL` or any model default (PRD non-goal).
- Any real Claude API call in application code — only in the manual test script.
- Async client, retries, timeouts, custom `http_client` — SDK defaults are correct here.
- CI, ruff/black, mypy.
