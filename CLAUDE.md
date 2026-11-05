# local-model

A collection of Colab notebooks. The user opens them from GitHub in Colab (often on a phone)
and runs them with *Runtime → Run all*. Claude can't run them — the user pastes back errors
or output.

## Writing notebooks

- One notebook per task in `notebooks/`, named `snake_case.ipynb`.
- Must run top to bottom with *Run all* and no edits. Put settings (model id, steps, etc.) in
  one cell near the top with comments; nothing else should need changing.
- First code cell shows the GPU (`!nvidia-smi ...`) so a missing GPU runtime is obvious.
- `pip install` what's needed inside the notebook; Colab already ships torch and transformers.
- Secrets (e.g. `HF_TOKEN`) come from Colab's Secrets panel via `google.colab.userdata`,
  never hard-coded.
- Long runs (fine-tuning) save checkpoints to Google Drive so a disconnect doesn't lose work.
- Commit without outputs, set `metadata.accelerator = "GPU"`, and before committing check the
  JSON parses and every code cell compiles (ignoring `!`/`%` lines).
- Add each notebook to the table in README.md with an "Open in Colab" link.
