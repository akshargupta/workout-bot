"""Tests for workout_bot.config — see specs/001-port-env-config/tests.md.

Every test is hermetic: both variables are cleared from os.environ and an explicit
env file is written into tmp_path, so nothing here reads the developer's real .env.
"""

import dataclasses
import os

import anthropic
import pytest

from workout_bot.config import (
    Config,
    MissingConfigError,
    build_client,
    load_config,
)

SECRET = "sk-ant-test-do-not-log-me"


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch):
    """Start every test with both variables truly unset, and restore afterwards.

    autouse, because `load_config` writes into `os.environ` and the tests that
    never touch a .env file (the `build_client` ones) would otherwise read
    whatever a previous test — or the developer's shell — left behind.

    `delenv(raising=False)` alone is not enough: monkeypatch records an undo
    entry only when the variable was already present, so on a machine where
    these are unset it records nothing and values written during the test
    survive teardown. Setting first forces the prior state (including absence)
    to be recorded, then deleting gives a clean start.
    """
    for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL"):
        monkeypatch.setenv(var, "")
        monkeypatch.delenv(var)


@pytest.fixture
def env_file(tmp_path):
    """Write a .env into tmp_path and return its path."""

    def _write(text: str) -> str:
        path = tmp_path / ".env"
        path.write_text(text)
        return str(path)

    return _write


# AC 7 — load_config returns both values
def test_loads_both_values(env_file):
    path = env_file(
        f"ANTHROPIC_API_KEY={SECRET}\nANTHROPIC_BASE_URL=https://gw.example.com\n"
    )
    config = load_config(path)
    assert config.api_key == SECRET
    assert config.base_url == "https://gw.example.com"


# AC 7 — result is a frozen Config
def test_returns_frozen_config(env_file):
    config = load_config(env_file(f"ANTHROPIC_API_KEY={SECRET}\n"))
    assert isinstance(config, Config)
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.api_key = "mutated"


# AC 8 — the real process environment wins over the file
def test_process_env_beats_dotenv(env_file, monkeypatch):
    path = env_file("ANTHROPIC_API_KEY=from-dotenv\n")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "from-process-env")
    assert load_config(path).api_key == "from-process-env"


# AC 9 — missing key raises a named error that says which variable
def test_missing_key_raises(env_file):
    path = env_file("ANTHROPIC_BASE_URL=https://gw.example.com\n")
    with pytest.raises(MissingConfigError) as exc:
        load_config(path)
    assert "ANTHROPIC_API_KEY" in str(exc.value)


# AC 10 — the blank-base-URL cleanup happens even when validation then fails,
# so a caller that catches the error and builds a zero-arg client is not left
# holding an empty ANTHROPIC_BASE_URL.
def test_blank_base_url_cleaned_even_when_key_missing(env_file):
    path = env_file("ANTHROPIC_BASE_URL=\n")
    with pytest.raises(MissingConfigError):
        load_config(path)
    assert "ANTHROPIC_BASE_URL" not in os.environ
    assert "api.anthropic.com" in str(anthropic.Anthropic(api_key="k").base_url)


# AC 9 — empty key is treated as missing
def test_empty_key_raises(env_file):
    with pytest.raises(MissingConfigError):
        load_config(env_file("ANTHROPIC_API_KEY=\n"))


# AC 9 — whitespace-only key is treated as missing
def test_whitespace_key_raises(env_file):
    with pytest.raises(MissingConfigError):
        load_config(env_file('ANTHROPIC_API_KEY="   "\n'))


# AC 10 — absent base URL becomes None
def test_missing_base_url_is_none(env_file):
    config = load_config(env_file(f"ANTHROPIC_API_KEY={SECRET}\n"))
    assert config.base_url is None


# AC 10 — empty base URL becomes None, never ""
def test_empty_base_url_is_none(env_file):
    path = env_file(f"ANTHROPIC_API_KEY={SECRET}\nANTHROPIC_BASE_URL=\n")
    config = load_config(path)
    assert config.base_url is None
    assert config.base_url != ""


# AC 11 — the key never appears in repr or str
def test_repr_redacts_key(env_file):
    config = load_config(env_file(f"ANTHROPIC_API_KEY={SECRET}\n"))
    # Assert on absence of the secret, so reverting to the generated __repr__ fails.
    assert SECRET not in repr(config)
    assert SECRET not in str(config)
    assert "redacted" in repr(config)


# AC 12 — a None base_url resolves to the SDK default
def test_client_uses_sdk_default_when_base_url_is_none():
    client = build_client(Config(api_key=SECRET, base_url=None))
    assert isinstance(client, anthropic.Anthropic)
    assert "api.anthropic.com" in str(client.base_url)


# AC 12 — base_url passed through when set
def test_client_passes_base_url_through():
    client = build_client(Config(api_key=SECRET, base_url="https://gw.example.com"))
    assert "gw.example.com" in str(client.base_url)


# AC 10 + AC 12 — regression: the documented onboarding path, end to end.
# .env.example ships `ANTHROPIC_BASE_URL=` and says to leave it blank for the
# public API. Going through load_config -> build_client must therefore produce
# the real default, not a client pointed at "". The two tests above construct
# Config directly and so cannot catch this.
def test_blank_base_url_in_env_file_yields_sdk_default(env_file):
    path = env_file(f"ANTHROPIC_API_KEY={SECRET}\nANTHROPIC_BASE_URL=\n")
    client = build_client(load_config(path))
    assert "api.anthropic.com" in str(client.base_url)
    assert str(client.base_url) != ""


# AC 10 + AC 12 — same path, whitespace-only value
def test_whitespace_base_url_in_env_file_yields_sdk_default(env_file):
    path = env_file(f'ANTHROPIC_API_KEY={SECRET}\nANTHROPIC_BASE_URL="   "\n')
    client = build_client(load_config(path))
    assert "api.anthropic.com" in str(client.base_url)


# AC 10 + AC 12 — a real value in the file still reaches the client
def test_real_base_url_in_env_file_reaches_client(env_file):
    path = env_file(
        f"ANTHROPIC_API_KEY={SECRET}\nANTHROPIC_BASE_URL=https://gw.example.com\n"
    )
    client = build_client(load_config(path))
    assert "gw.example.com" in str(client.base_url)
