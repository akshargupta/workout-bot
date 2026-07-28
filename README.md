# workout-bot

A workout-logging bot built on the [Claude Messages API](https://docs.anthropic.com/en/api/messages).

Early stage: the Python runtime and API configuration are in place, the bot
itself is not built yet.

## Setup

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env
```

Then add your [Claude API key](https://console.anthropic.com/settings/keys) to `.env`.
