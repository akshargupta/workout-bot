# 001 — Test plan

## Automated

Written during `/implement` into `tests/test_config.py`. Run with `uv run pytest`.

Every test is hermetic: both variables are cleared from `os.environ` and any file input
is written into `tmp_path`. **No test reads the developer's real `.env` or shell
exports** — otherwise a test could pass for the wrong reason on one machine and fail on
another.

The isolation fixture is `autouse`, and it does *not* use bare
`monkeypatch.delenv(..., raising=False)`. That records an undo entry only when the
variable was already present, so on a machine where these are unset it records nothing
and whatever `load_config` writes during the test survives teardown into later tests.
Setting first forces the prior state — including absence — to be recorded:

```python
@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch):
    for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL"):
        monkeypatch.setenv(var, "")   # records prior state, incl. absence
        monkeypatch.delenv(var)       # then start from truly-unset

@pytest.fixture
def env_file(tmp_path):
    def _write(text: str) -> str:
        p = tmp_path / ".env"
        p.write_text(text)
        return str(p)
    return _write
```

`autouse` is what makes tests 10–11 trustworthy: they never touch a `.env`, so without it
they read whatever a previous test or the developer's shell left in `os.environ`.

| # | Test | Asserts | AC |
|---|---|---|---|
| 1 | `test_loads_both_values` | `.env` with both keys → `api_key` and `base_url` match the file | 7 |
| 2 | `test_returns_config_type` | result is a `Config`; instance is frozen (assigning to `.api_key` raises `FrozenInstanceError`) | 7 |
| 3 | `test_process_env_beats_dotenv` | `monkeypatch.setenv("ANTHROPIC_API_KEY", "from-env")` + a `.env` with a different value → `from-env` wins | 8 |
| 4 | `test_missing_key_raises` | `.env` with no `ANTHROPIC_API_KEY` → `MissingConfigError`, and `"ANTHROPIC_API_KEY" in str(exc)` | 9 |
| 5 | `test_empty_key_raises` | `ANTHROPIC_API_KEY=` (empty) → same `MissingConfigError` | 9 |
| 6 | `test_whitespace_key_raises` | `ANTHROPIC_API_KEY="   "` → same `MissingConfigError` | 9 |
| 7 | `test_missing_base_url_is_none` | key present, no `ANTHROPIC_BASE_URL` → `base_url is None` | 10 |
| 8 | `test_empty_base_url_is_none` | `ANTHROPIC_BASE_URL=` → `base_url is None`, explicitly **not** `""` | 10 |
| 9 | `test_repr_redacts_key` | secret string absent from both `repr(cfg)` and `str(cfg)`; `"redacted"` present | 11 |
| 10 | `test_client_omits_base_url_when_none` | `build_client(Config(k, None))` → an `anthropic.Anthropic` whose `base_url` is the SDK default (`api.anthropic.com`) | 12 |
| 11 | `test_client_passes_base_url_through` | `build_client(Config(k, "https://gw.example.com"))` → client `base_url` reflects it | 12 |
| 12 | `test_blank_base_url_in_env_file_yields_sdk_default` | `.env` with `ANTHROPIC_BASE_URL=` → **through `load_config` then `build_client`** → client `base_url` is the real default, not `""` | 10, 12 |
| 13 | `test_whitespace_base_url_in_env_file_yields_sdk_default` | same, with a whitespace-only value | 10, 12 |
| 14 | `test_real_base_url_in_env_file_reaches_client` | same path, real value → reaches the client unchanged | 10, 12 |

Tests 12–14 exist because 10 and 11 construct `Config` directly and so never exercise
the `.env` → `os.environ` → SDK path. A blank `ANTHROPIC_BASE_URL=` line is written into
`os.environ` by `load_dotenv`, and the SDK treats an empty string as a real endpoint —
so the documented "leave it blank" onboarding path produced an unusable client while
tests 10 and 11 stayed green. These three close that gap.

Test 9 is the one worth writing carefully: assert on the **absence of the secret substring**,
not on the presence of the word "redacted". A regression that reverts to the dataclass's
generated `__repr__` must fail this test.

AC 13 is satisfied by the suite exiting 0 as a whole. AC 1–6, 14, 15 are file-state
criteria — covered by the manual script below rather than by pytest.

## Manual script

Run from the repo root after `/implement` reports done, on branch `spec/001-port-env-config`.
Steps 1–7 are offline. **Step 8 is the only one that needs network and spends tokens.**

---

**1. Confirm the interpreter is pinned and the venv exists.**

```bash
cat .python-version && uv run python -V
```
Expect: `3.14.5` on both lines (second as `Python 3.14.5`). — AC 4

**2. Confirm the `.env` copy is byte-for-byte.**

```bash
cmp .env ~/Documents/archive/ai-project/.env && echo "IDENTICAL"
```
Expect: `IDENTICAL`, no diff output. — AC 1

**3. Confirm the secret cannot be committed.** The important one.

```bash
git check-ignore -v .env && git status --porcelain | grep -c '\.env$'
```
Expect: a line showing `.gitignore:1:.env`, then `0`. A `0` count means no `.env` is staged
or untracked-and-visible. If you see anything other than `0`, **stop and do not commit.** — AC 2

**4. Confirm `.env.example` is safe to commit.**

```bash
cat .env.example
```
Expect: both variable names present, every value empty or an obvious placeholder, comments
explaining each. Read it and confirm with your own eyes that **no real key appears.** — AC 3

**5. Run the test suite.**

```bash
uv run pytest -q
```
Expect: all tests pass, exit 0, no warnings about skipped tests. — AC 13

**6. Confirm the failure mode is friendly.** Hide the real key and check the error:

```bash
env -u ANTHROPIC_API_KEY uv run python -c "
from workout_bot.config import load_config, MissingConfigError
try:
    load_config(env_file='/dev/null')
except MissingConfigError as e:
    print('OK:', e)
"
```
Expect: `OK: ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it in.`
Not a `KeyError`, not a traceback. — AC 9

**7. Confirm the key is not printable.**

```bash
uv run python -c "
from workout_bot.config import load_config
c = load_config()
print(repr(c)); print(str(c))
assert c.api_key not in repr(c) and c.api_key not in str(c)
print('REDACTED OK')
"
```
Expect: two lines showing `api_key=<redacted>`, then `REDACTED OK`. Your real key must not
appear in the output. — AC 11

**8. Live check — the actual point of the whole spec.** Proves the ported credentials and
endpoint really work. Needs network; costs a trivial number of tokens.

⚠️ **Run it with `env -u ANTHROPIC_BASE_URL`, as written below.** This shell exports
`ANTHROPIC_BASE_URL`, and per AC 8 an export beats the file — so without `env -u` you
would send the `.env`'s key to whatever your shell points at rather than to the endpoint
the `.env` specifies, and get a confusing auth failure that looks like a bad port. Check
with `echo $ANTHROPIC_BASE_URL`; if it prints nothing, the `env -u` is harmless anyway.

```bash
env -u ANTHROPIC_BASE_URL uv run python -c "
from workout_bot.config import load_config, build_client
cfg = load_config()
client = build_client(cfg)
print('endpoint:', client.base_url)
r = client.messages.create(
    model='claude-opus-5',
    max_tokens=1024,
    messages=[{'role': 'user', 'content': 'Reply with exactly: OK'}],
)
print('stop_reason:', r.stop_reason)
print('text:', next((b.text for b in r.content if b.type == 'text'), '<none>'))
"
```
Expect: the endpoint your `.env` specifies, `stop_reason: end_turn`, and text containing
`OK`. An `AuthenticationError` means the copied key is wrong or expired; a connection error
means the base URL is wrong.

**9. Confirm the docs kept up.**

```bash
sed -n '/## Commands/,/## Environment/p' CLAUDE.md && ls wiki/
```
Expect: real commands under Commands — not `_(none yet)_` — and `configuration.md` present
in `wiki/`. — AC 14, 15

---

Then read the diff and `review.md`, and run `/feedback` with your verdict.
