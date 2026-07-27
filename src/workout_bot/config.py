"""Load and validate the Claude API configuration.

The Anthropic SDK reads ``ANTHROPIC_API_KEY`` and ``ANTHROPIC_BASE_URL`` from the
*process* environment. Python does not load ``.env`` files into that environment on
its own, so ``python-dotenv`` bridges the gap here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import anthropic
from dotenv import load_dotenv

__all__ = ["Config", "MissingConfigError", "build_client", "load_config"]

API_KEY_VAR = "ANTHROPIC_API_KEY"
BASE_URL_VAR = "ANTHROPIC_BASE_URL"


class MissingConfigError(RuntimeError):
    """Raised when a required configuration variable is absent or empty."""


@dataclass(frozen=True)
class Config:
    """Validated configuration for talking to the Claude API."""

    api_key: str
    base_url: str | None

    def __repr__(self) -> str:
        # Overrides the repr the dataclass would generate, which would print the
        # key in full. `str()` falls back to `__repr__`, so this covers both.
        return f"Config(api_key=<redacted>, base_url={self.base_url!r})"


def _clean(value: str | None) -> str | None:
    """Collapse unset, empty, and whitespace-only values into a single ``None``."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def load_config(env_file: str | os.PathLike[str] | None = None) -> Config:
    """Load configuration from the environment, backfilled by a ``.env`` file.

    Args:
        env_file: Path to the file to read. Defaults to a ``.env`` discovered by
            walking up from the current working directory. Tests pass an explicit
            path so they never depend on the developer's real ``.env``.

    Raises:
        MissingConfigError: If ``ANTHROPIC_API_KEY`` is absent or empty.
    """
    # override=False: a variable already exported in the real environment wins
    # over the same key in the file.
    load_dotenv(env_file, override=False)

    api_key = _clean(os.environ.get(API_KEY_VAR))
    if api_key is None:
        raise MissingConfigError(
            f"{API_KEY_VAR} is not set. Copy .env.example to .env and fill it in."
        )

    return Config(api_key=api_key, base_url=_clean(os.environ.get(BASE_URL_VAR)))


def build_client(config: Config) -> anthropic.Anthropic:
    """Build a Claude API client from validated configuration.

    When ``base_url`` is ``None`` the argument is omitted entirely so the SDK
    applies its own default — passing ``None`` explicitly is not the same thing.
    """
    if config.base_url is None:
        return anthropic.Anthropic(api_key=config.api_key)
    return anthropic.Anthropic(api_key=config.api_key, base_url=config.base_url)
