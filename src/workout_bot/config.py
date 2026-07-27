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
    """Validated configuration for talking to the Claude API.

    Build these with :func:`load_config`, not by hand. Beyond validating the
    fields, it guarantees that a blank ``ANTHROPIC_BASE_URL`` is *absent* from
    ``os.environ`` rather than empty — an invariant :func:`build_client` relies
    on, and which a hand-constructed ``Config`` would not establish.
    """

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

    Note that this mutates ``os.environ`` — both via ``load_dotenv`` and via the
    blank-value normalization below. A second call with a different ``env_file``
    in the same process therefore still sees the first file's values.

    Args:
        env_file: Path to the file to read. Defaults to a ``.env`` located by
            ``python-dotenv``'s own search, which starts at the calling module's
            file rather than the working directory. Tests pass an explicit path so
            they never depend on the developer's real ``.env``.

    Raises:
        MissingConfigError: If ``ANTHROPIC_API_KEY`` is absent or empty.
    """
    # override=False: a variable already exported in the real environment wins
    # over the same key in the file.
    load_dotenv(env_file, override=False)

    # Normalize before validating. `load_dotenv` has already written any blank
    # value straight into os.environ, and the SDK's fallback chain only treats
    # *absent* as "use the default" — an empty string is taken as a real base
    # URL and yields a client that cannot reach anything. This has to happen
    # ahead of the api_key check: a caller that catches MissingConfigError and
    # then builds a zero-arg `anthropic.Anthropic()` would otherwise inherit the
    # blank value we failed to clean up.
    base_url = _clean(os.environ.get(BASE_URL_VAR))
    if base_url is None:
        os.environ.pop(BASE_URL_VAR, None)

    api_key = _clean(os.environ.get(API_KEY_VAR))
    if api_key is None:
        raise MissingConfigError(
            f"{API_KEY_VAR} is not set. Copy .env.example to .env and fill it in."
        )

    return Config(api_key=api_key, base_url=base_url)


def build_client(config: Config) -> anthropic.Anthropic:
    """Build a Claude API client from validated configuration.

    Passing ``base_url=None`` is identical to omitting the argument: the SDK
    normalizes ``None`` first, then falls back to ``ANTHROPIC_BASE_URL`` and
    finally to its own default. ``load_config`` guarantees that variable is
    absent rather than empty, so that fallback resolves correctly.
    """
    return anthropic.Anthropic(api_key=config.api_key, base_url=config.base_url)
