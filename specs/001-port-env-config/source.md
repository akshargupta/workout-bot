# Port over the .env from the original folder

Bring the `.env` from the original project folder into `workout-bot` — it holds the
API key and the base URL the bot needs to talk to the model provider.

## Why

This repo is currently spec/wiki scaffolding only — no code, no config. Nothing can
actually run until the credentials and endpoint are in place locally, so this blocks
the first implementation spec that touches the provider.

## Ingredients

- Source: the original folder's `.env`. **Open question — which folder?** Two
  candidates under `~/Documents/archive/` both have a `.env`: `adaptive-tutor/` and
  `ai-project/`. Confirm the right one before copying.
- Variables of interest: the API key and the base URL. Whatever else is in the
  source `.env` should be reviewed rather than copied wholesale — this project may
  not need it.
- Destination: `workout-bot/.env`, already listed in [.gitignore](../.gitignore),
  so the real file stays out of git. Copy it locally; do not commit it.

## Open questions

- Exact variable names to standardise on (e.g. `ANTHROPIC_API_KEY` /
  `ANTHROPIC_BASE_URL` vs. whatever the original used) — worth picking deliberately
  now rather than inheriting a name.
- Should a committed `.env.example` land alongside it, listing the required keys
  with empty values, so the setup is documented for anyone cloning the repo?
