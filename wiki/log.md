# Directory Update Log

## 2026-07-28
* **Update**: Renamed the loop's final gate from `/feedback` to `/signoff` in [spec-workflow](spec-workflow.md). Claude Code ships a built-in `/feedback` command that shadowed the project skill, making the gate unreachable by name; the spec artifact it writes is now `signoff.md`.

## 2026-07-27
* **Creation**: Added [configuration](configuration.md), covering the `.env` contract (`ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL`), the python-dotenv bridge and precedence rules, and the Python 3.14.5 / uv runtime. From spec 001-port-env-config.
* **Initialization**: Created the bundle and seeded [spec-workflow](spec-workflow.md), ported from the archived `ai-project` repo along with the rest of the development workflow. Authored against OKF v0.2.
