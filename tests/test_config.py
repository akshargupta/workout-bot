"""Tests for workout_bot.config — see specs/001-port-env-config/tests.md.

Every test is hermetic: both variables are cleared from os.environ and an explicit
env file is written into tmp_path, so nothing here reads the developer's real .env.
"""

import dataclasses

import anthropic
import pytest

from workout_bot.config import (
    Config,
    MissingConfigError,
    build_client,
    load_config,
)

SECRET = "sk-ant-test-do-not-log-me"


@pytest.fixture
def env_file(tmp_path, monkeypatch):
    """Write a .env into tmp_path with both vars cleared from the real environment."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)

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


# AC 12 — base_url omitted when None, so the SDK default applies
def test_client_omits_base_url_when_none():
    client = build_client(Config(api_key=SECRET, base_url=None))
    assert isinstance(client, anthropic.Anthropic)
    assert "api.anthropic.com" in str(client.base_url)


# AC 12 — base_url passed through when set
def test_client_passes_base_url_through():
    client = build_client(Config(api_key=SECRET, base_url="https://gw.example.com"))
    assert "gw.example.com" in str(client.base_url)
