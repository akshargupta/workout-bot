"""Generate colab/bridge.ipynb from src/local_model/bridge_server.py.

The notebook embeds the server source so it works even when this repo is private (Colab can
open the notebook from GitHub, but the runtime cannot clone a private repo without a token).
Rerun after editing the server:  uv run python scripts/build_notebook.py
tests/test_notebook.py fails if the committed notebook is out of date.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "src" / "local_model" / "bridge_server.py"
NOTEBOOK = ROOT / "colab" / "bridge.ipynb"

INTRO = """\
# local-model — Colab bridge

Runs a small authenticated server on this runtime and exposes it through an ngrok tunnel, so
code can be sent here from elsewhere (e.g. a Claude Code session) and run on this GPU.

**One-time setup** — add these in the 🔑 *Secrets* panel (left sidebar) and enable
*Notebook access* for each:

| Secret | Value |
|---|---|
| `NGROK_AUTHTOKEN` | from https://dashboard.ngrok.com/get-started/your-authtoken |
| `NGROK_DOMAIN` | your free static domain from https://dashboard.ngrok.com/domains, e.g. `name-words.ngrok-free.app` |
| `BRIDGE_TOKEN` | a long random password you make up (32+ chars). Anyone with it can run code here. |

**Every session:** *Runtime → Change runtime type* → a GPU, then *Runtime → Run all*.
Keep this tab open; stop the last cell to shut the bridge down.
"""

GPU_CHECK = """\
!nvidia-smi -L || echo "No GPU attached: Runtime > Change runtime type"
"""

DRIVE_MD = """\
Optional: mount Google Drive so checkpoints survive the runtime being recycled. Set
`MOUNT_DRIVE = True`; save long-lived outputs under `/content/drive/MyDrive/local-model/`.
"""

DRIVE = """\
MOUNT_DRIVE = False
if MOUNT_DRIVE:
    from google.colab import drive
    drive.mount("/content/drive")
"""

START = """\
!pip install -q "pyngrok>=9,<10" fastapi uvicorn jupyter_client ipykernel

import json, os, subprocess, sys, time, urllib.request
from google.colab import userdata
from pyngrok import conf, ngrok

PORT = 8765
token = userdata.get("BRIDGE_TOKEN")
domain = userdata.get("NGROK_DOMAIN").strip().removeprefix("https://").rstrip("/")
assert len(token) >= 16, "BRIDGE_TOKEN must be at least 16 characters"

if "server" in globals() and server.poll() is None:  # re-running this cell: replace it
    server.terminate(); server.wait()
ngrok.kill()

log = open("/content/bridge.log", "ab")
server = subprocess.Popen(
    [sys.executable, "/content/bridge_server.py", "--port", str(PORT)],
    env={**os.environ, "BRIDGE_TOKEN": token}, stdout=log, stderr=subprocess.STDOUT,
)

def health(base=f"http://127.0.0.1:{PORT}"):
    req = urllib.request.Request(f"{base}/health", headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)

for _ in range(120):
    try:
        print("bridge up:", health()); break
    except Exception:
        if server.poll() is not None:
            raise RuntimeError(open("/content/bridge.log").read()[-3000:])
        time.sleep(1)
else:
    raise RuntimeError("bridge did not start; see /content/bridge.log")

conf.get_default().auth_token = userdata.get("NGROK_AUTHTOKEN")
tunnel = ngrok.connect(str(PORT), "http", url=f"https://{domain}")
print("\\nBridge is live at:", tunnel.public_url)
print("Set COLAB_URL to that URL wherever you run the `colab` CLI.")
"""

KEEPALIVE = """\
# Leave this running. It reports status every minute; stop it (■) to shut the bridge down.
try:
    while True:
        if server.poll() is not None:
            print(open("/content/bridge.log").read()[-3000:])
            raise RuntimeError("bridge server exited")
        h = health()
        print(time.strftime("%H:%M:%S"), "gpu:", h["gpu"], "| kernel busy:", h["kernel_busy"],
              "| jobs running:", h["jobs_running"], flush=True)
        time.sleep(60)
except KeyboardInterrupt:
    ngrok.kill()
    server.terminate()
    print("bridge stopped")
"""


def _cell(kind: str, text: str) -> dict:
    cell = {"cell_type": kind, "metadata": {}, "source": text.splitlines(keepends=True)}
    if kind == "code":
        cell["execution_count"] = None
        cell["outputs"] = []
    return cell


def build() -> str:
    server = "%%writefile /content/bridge_server.py\n" + SERVER.read_text()
    nb = {
        "nbformat": 4,
        "nbformat_minor": 0,
        "metadata": {
            "accelerator": "GPU",
            "colab": {"provenance": [], "gpuType": "T4"},
            "kernelspec": {"name": "python3", "display_name": "Python 3"},
            "language_info": {"name": "python"},
        },
        "cells": [
            _cell("markdown", INTRO),
            _cell("code", GPU_CHECK),
            _cell("markdown", DRIVE_MD),
            _cell("code", DRIVE),
            _cell("code", server),
            _cell("code", START),
            _cell("code", KEEPALIVE),
        ],
    }
    return json.dumps(nb, indent=1, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    NOTEBOOK.parent.mkdir(exist_ok=True)
    NOTEBOOK.write_text(build())
    print(f"wrote {NOTEBOOK.relative_to(ROOT)}")
