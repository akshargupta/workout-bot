# local-model

Write code here, run it on a **Google Colab GPU** — inference, fine-tuning, LoRA, whatever.

A notebook on Colab ([`colab/bridge.ipynb`](colab/bridge.ipynb)) starts a small authenticated
server and exposes it through an ngrok tunnel. The `colab` command in this repo talks to it, so
you — or Claude Code running in a cloud session — can push code, run it in a persistent Python
kernel, and launch long training jobs without touching the notebook.

```
 this repo / Claude Code ──HTTPS + token──▶ ngrok static domain ──▶ Colab runtime (GPU)
   uv run colab ...                                                  bridge_server.py
                                                                      ├─ persistent IPython kernel
                                                                      ├─ background jobs + logs
                                                                      └─ /content/work/project  (your pushed code)
```

## One-time setup

1. **ngrok** (free): sign up at https://ngrok.com, then copy
   - your authtoken — https://dashboard.ngrok.com/get-started/your-authtoken
   - your free static domain — https://dashboard.ngrok.com/domains (looks like `name-words.ngrok-free.app`)
2. **Colab secrets**: open [`colab/bridge.ipynb`](colab/bridge.ipynb) in Colab
   (*File → Open notebook → GitHub*, or the badge below), open the 🔑 *Secrets* panel and add
   `NGROK_AUTHTOKEN`, `NGROK_DOMAIN`, and `BRIDGE_TOKEN` (a long random string you make up — it is
   the password for running code on your runtime). Turn on *Notebook access* for all three.
3. **This side**:
   - *Claude Code cloud session*: give Claude your ngrok domain. It will ask to allow that host
     in the environment's network settings and open a secure form for `BRIDGE_TOKEN`
     (stored as a network secret, never in the repo).
   - *Your own machine*: `uv sync`, `cp .env.example .env`, fill in `COLAB_URL` and `COLAB_TOKEN`.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/akshargupta/workout-bot/blob/main/colab/bridge.ipynb)

## Every session

In Colab: pick a GPU runtime, *Runtime → Run all*, keep the tab open. Then:

```bash
uv run colab status                         # GPU, disk, kernel, jobs
uv run colab run examples/gpu_check.py      # run a file in the persistent kernel
uv run colab run -c "x = 1"                 # snippets; state (x, loaded models...) persists
uv run colab push                           # upload this repo -> /content/work/project (src/ is importable)
uv run colab job start -f "python -m local_model.train"   # long work: background job, streamed log
uv run colab job ls | logs ID [-f] | kill ID
uv run colab get outputs/plot-*.png         # download a file;  `colab put` uploads one
uv run colab interrupt | restart
```

Rules of thumb: `run` is for interactive steps (default 5-minute timeout, then Ctrl-C);
anything longer — training, big downloads — goes in a `job`. `push` adds and overwrites files
but never deletes, so outputs on Colab are safe. Colab's disk is wiped when the runtime is
recycled: keep checkpoints on Drive (mount it in the notebook) or `colab get` them.

## Notes

- Colab Pro runtimes stay up while the tab is open, up to ~24 h; Pro+ adds background execution.
- ngrok's free tier has monthly request/bandwidth caps. Only code and logs cross the tunnel —
  models and datasets download directly to Colab — so normal use stays well inside them.
- The bridge only accepts requests carrying `BRIDGE_TOKEN`. Treat it like a password; rotate it
  in the Secrets panel if it leaks.
- Edited `src/local_model/bridge_server.py`? Regenerate the notebook:
  `uv run python scripts/build_notebook.py` (a test fails if you forget).

## Development

```bash
uv sync          # Python 3.12, matching Colab
uv run pytest    # runs the real bridge + kernel locally; no Colab needed
```
