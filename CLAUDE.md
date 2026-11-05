# local-model

Code lives here; it runs on the user's Colab GPU runtime through the bridge. See README.md
for the architecture and setup.

## Commands

- `uv sync` — install (Python 3.12, matching Colab). Always use `uv run`.
- `uv run pytest` — must pass before committing. Tests run the real bridge + kernel locally.
- `uv run python scripts/build_notebook.py` — after any edit to `src/local_model/bridge_server.py`.

## Running code on Colab

- `uv run colab status` first. If it can't connect, the user needs to (re)run
  `colab/bridge.ipynb` in Colab — ask them; you can't start it yourself.
- Workflow: edit files here → `uv run colab push` → `colab run` for quick, interactive steps
  (state persists across calls, so load a model once and reuse it) → `colab job start` for
  anything that can exceed a few minutes (training, large downloads), then poll `colab job logs ID`.
- Heavy deps (torch, transformers, peft, trl, bitsandbytes, ...) belong on Colab only — install
  with `colab run -c "!pip install -q ..."` or in a job, not in pyproject.toml. Colab already
  ships torch and transformers.
- Colab's disk is ephemeral. Put checkpoints and anything worth keeping under
  `/content/drive/MyDrive/local-model/` (when Drive is mounted) or fetch them with `colab get`.
- Notebooks the user runs by hand go in `notebooks/`: committed without outputs, runnable top to
  bottom with *Run all*, settings in a cell near the top, and a link added to the README table.
- Never print, log or commit BRIDGE_TOKEN / COLAB_TOKEN / HF tokens.
