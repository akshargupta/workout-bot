"""HTTP bridge that lets a remote agent run code on this machine — meant for a Colab GPU runtime.

What it serves (every route needs ``Authorization: Bearer $BRIDGE_TOKEN``):

* ``POST /exec``        run code in a persistent IPython kernel — variables, loaded models and
                        imports survive between calls, like cells in one notebook.
* ``POST /interrupt``   Ctrl-C the kernel.   ``POST /restart``   fresh kernel, state wiped.
* ``POST /jobs``        start a background shell command (training runs etc.), logged to disk.
* ``GET  /jobs``, ``GET /jobs/{id}``, ``GET /jobs/{id}/log``, ``POST /jobs/{id}/kill``
* ``PUT  /sync``        upload a .tar.gz of the project; extracted (add/overwrite, never delete)
                        into ``<workdir>/project``, whose ``src/`` is on the kernel's sys.path.
* ``GET/PUT /files``    download / upload a single file.
* ``GET  /health``      GPU, disk, kernel and job status.

This file is copied verbatim into the Colab notebook (see scripts/build_notebook.py), so it
must stay self-contained: stdlib plus fastapi, uvicorn, jupyter_client and ipykernel — all of
which Colab ships — and Python 3.11-compatible syntax.
"""

import argparse
import hmac
import json
import os
import queue
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import threading
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from jupyter_client.kernelspec import KernelSpecManager
from jupyter_client.manager import KernelManager
from pydantic import BaseModel

DEFAULT_WORKDIR = "/content/work"
MAX_STREAM_CHARS = 200_000  # per stream per /exec; the tail is kept
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


class ExecRequest(BaseModel):
    code: str
    timeout: float = 300


class JobRequest(BaseModel):
    cmd: str
    cwd: str | None = None


def _trim(text: str) -> str:
    if len(text) <= MAX_STREAM_CHARS:
        return text
    return f"[... {len(text) - MAX_STREAM_CHARS} chars trimmed ...]\n" + text[-MAX_STREAM_CHARS:]


class Kernel:
    """One persistent IPython kernel; one execution at a time."""

    def __init__(self, workdir: Path):
        self.workdir = workdir
        self.project = workdir / "project"
        self.outputs = workdir / "outputs"
        self.lock = threading.Lock()  # held for the duration of an /exec
        self.generation = 0  # bumped on restart so an in-flight /exec can bail out
        spec_dir = workdir / ".kernels" / "bridge"
        spec_dir.mkdir(parents=True, exist_ok=True)
        # A plain ipykernel on this interpreter, rather than whatever "python3" spec the
        # host registers (Colab's wraps its own launcher, which expects a browser frontend).
        (spec_dir / "kernel.json").write_text(json.dumps({
            "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "display_name": "bridge",
            "language": "python",
            "env": {"PYTHONPATH": f"{self.project / 'src'}{os.pathsep}{self.project}"},
        }))
        ksm = KernelSpecManager(kernel_dirs=[str(spec_dir.parent)])
        self.km = KernelManager(kernel_name="bridge", kernel_spec_manager=ksm)
        self.km.start_kernel(cwd=str(self.project))
        self.kc = self.km.client()
        self.kc.start_channels()
        self.kc.wait_for_ready(timeout=120)

    @property
    def busy(self) -> bool:
        return self.lock.locked()

    def execute(self, code: str, timeout: float) -> dict:
        if not self.lock.acquire(blocking=False):
            raise HTTPException(409, "Kernel is busy with another /exec. Wait, or POST /interrupt.")
        try:
            return self._execute(code, timeout)
        finally:
            self.lock.release()

    def _execute(self, code: str, timeout: float) -> dict:
        started = time.monotonic()
        gen = self.generation
        out = {"status": "ok", "stdout": "", "stderr": "", "result": None,
               "error": None, "images": []}
        msg_id = self.kc.execute(code, store_history=True, allow_stdin=False)
        deadline = started + timeout
        interrupted = False
        while True:
            if self.generation != gen:
                out["status"] = "restarted"
                out["stderr"] += "\n[bridge] kernel was restarted during this execution"
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                if interrupted:  # interrupt ignored (e.g. stuck in C code): last resort
                    self._restart()
                    out["stderr"] += "\n[bridge] kernel ignored interrupt; restarted, state lost"
                    break
                self.km.interrupt_kernel()
                interrupted = True
                out["status"] = "timeout"
                deadline = time.monotonic() + 30
                continue
            try:
                msg = self.kc.get_iopub_msg(timeout=min(remaining, 1.0))
            except queue.Empty:
                continue
            if msg["parent_header"].get("msg_id") != msg_id:
                continue
            kind, content = msg["msg_type"], msg["content"]
            if kind == "stream":
                out["stdout" if content["name"] == "stdout" else "stderr"] += content["text"]
            elif kind in ("execute_result", "display_data"):
                data = content.get("data", {})
                if "image/png" in data:
                    out["images"].append(self._save_png(data["image/png"]))
                elif "text/plain" in data:
                    if kind == "execute_result":
                        out["result"] = data["text/plain"]
                    else:
                        out["stdout"] += data["text/plain"] + "\n"
            elif kind == "error":
                out["error"] = {
                    "ename": content["ename"],
                    "evalue": content["evalue"],
                    "traceback": "\n".join(ANSI.sub("", line) for line in content["traceback"]),
                }
                if out["status"] == "ok":
                    out["status"] = "error"
            elif kind == "status" and content["execution_state"] == "idle":
                break
        out["stdout"] = _trim(out["stdout"])
        out["stderr"] = _trim(out["stderr"])
        out["elapsed"] = round(time.monotonic() - started, 3)
        return out

    def _save_png(self, b64: str) -> str:
        import base64

        self.outputs.mkdir(parents=True, exist_ok=True)
        path = self.outputs / f"plot-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}.png"
        path.write_bytes(base64.b64decode(b64))
        return str(path)

    def interrupt(self) -> None:
        self.km.interrupt_kernel()

    def _restart(self) -> None:
        self.generation += 1
        self.km.restart_kernel(now=True)
        self.kc.wait_for_ready(timeout=120)

    def restart(self) -> None:
        self._restart()

    def shutdown(self) -> None:
        self.kc.stop_channels()
        self.km.shutdown_kernel(now=True)


class Jobs:
    """Background shell commands with their output in <workdir>/.jobs/<id>.log."""

    def __init__(self, workdir: Path):
        self.workdir = workdir
        self.dir = workdir / ".jobs"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.jobs: dict[str, dict] = {}

    def start(self, cmd: str, cwd: str | None) -> dict:
        jid = time.strftime("%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
        log = self.dir / f"{jid}.log"
        project = self.workdir / "project"
        workdir = Path(cwd) if cwd else project
        if not workdir.is_absolute():
            workdir = project / workdir
        if not workdir.is_dir():
            raise HTTPException(400, f"cwd does not exist: {workdir}")
        env = {**os.environ, "PYTHONUNBUFFERED": "1",
               "PYTHONPATH": os.pathsep.join(
                   p for p in (str(project / "src"), str(project), os.environ.get("PYTHONPATH"))
                   if p)}
        with open(log, "wb") as f:
            proc = subprocess.Popen(["bash", "-c", cmd], cwd=workdir, stdout=f,
                                    stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                    env=env, start_new_session=True)
        self.jobs[jid] = {"proc": proc, "cmd": cmd, "cwd": str(workdir), "log": log,
                          "started": time.time()}
        return self.info(jid)

    def _get(self, jid: str) -> dict:
        if jid not in self.jobs:
            raise HTTPException(404, f"no such job: {jid}")
        return self.jobs[jid]

    def info(self, jid: str) -> dict:
        job = self._get(jid)
        rc = job["proc"].poll()
        return {"id": jid, "cmd": job["cmd"], "cwd": job["cwd"], "log": str(job["log"]),
                "status": "running" if rc is None else "exited", "returncode": rc,
                "started": job["started"], "log_size": job["log"].stat().st_size}

    def list(self) -> list[dict]:
        return [self.info(jid) for jid in self.jobs]

    def read_log(self, jid: str, offset: int, max_bytes: int) -> dict:
        job = self._get(jid)
        size = job["log"].stat().st_size
        if offset < 0:  # negative: the last -offset bytes
            offset = max(0, size + offset)
        with open(job["log"], "rb") as f:
            f.seek(offset)
            data = f.read(max_bytes)
        return {"text": data.decode("utf-8", "replace"), "next_offset": offset + len(data),
                "size": size}

    def kill(self, jid: str) -> dict:
        proc = self._get(jid)["proc"]
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            except ProcessLookupError:
                pass
        return self.info(jid)

    def shutdown(self) -> None:
        for jid in list(self.jobs):
            self.kill(jid)


def _gpu() -> str | None:
    if not shutil.which("nvidia-smi"):
        return None
    try:
        return subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.used,memory.total,utilization.gpu",
             "--format=csv,noheader"], capture_output=True, text=True, timeout=10,
        ).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def create_app(workdir: str | os.PathLike = DEFAULT_WORKDIR, token: str | None = None) -> FastAPI:
    token = token if token is not None else os.environ.get("BRIDGE_TOKEN", "")
    if len(token) < 16:
        raise SystemExit("BRIDGE_TOKEN must be set and at least 16 characters long.")
    expected = f"Bearer {token}".encode()
    root = Path(workdir).resolve()
    # Must exist before the kernel starts: Python caches a missing sys.path dir as absent,
    # so code pushed later into a not-yet-created src/ would never become importable.
    (root / "project" / "src").mkdir(parents=True, exist_ok=True)

    def authorize(request: Request) -> None:
        got = request.headers.get("authorization", "").encode()
        if not hmac.compare_digest(got, expected):
            raise HTTPException(401, "missing or wrong bearer token")

    state: dict = {}

    @asynccontextmanager
    async def lifespan(_app):
        state["kernel"] = Kernel(root)
        state["jobs"] = Jobs(root)
        try:
            yield
        finally:
            state["jobs"].shutdown()
            state["kernel"].shutdown()

    app = FastAPI(title="colab bridge", lifespan=lifespan, dependencies=[Depends(authorize)])

    def resolve(path: str) -> Path:
        p = Path(path).expanduser()
        return p if p.is_absolute() else root / p

    @app.get("/health")
    def health():
        usage = shutil.disk_usage(root)
        return {"ok": True, "python": sys.version.split()[0], "workdir": str(root),
                "gpu": _gpu(), "disk_free_gb": round(usage.free / 1e9, 1),
                "kernel_busy": state["kernel"].busy,
                "jobs_running": sum(j["status"] == "running" for j in state["jobs"].list())}

    @app.post("/exec")
    def execute(req: ExecRequest):
        return state["kernel"].execute(req.code, req.timeout)

    @app.post("/interrupt")
    def interrupt():
        state["kernel"].interrupt()
        return {"ok": True}

    @app.post("/restart")
    def restart():
        state["kernel"].restart()
        return {"ok": True}

    @app.post("/jobs")
    def start_job(req: JobRequest):
        return state["jobs"].start(req.cmd, req.cwd)

    @app.get("/jobs")
    def list_jobs():
        return state["jobs"].list()

    @app.get("/jobs/{jid}")
    def job_info(jid: str):
        return state["jobs"].info(jid)

    @app.get("/jobs/{jid}/log")
    def job_log(jid: str, offset: int = 0, max_bytes: int = 1_000_000):
        return state["jobs"].read_log(jid, offset, max_bytes)

    @app.post("/jobs/{jid}/kill")
    def kill_job(jid: str):
        return state["jobs"].kill(jid)

    @app.put("/sync")
    async def sync(request: Request):
        import io

        dest = root / "project"
        try:
            with tarfile.open(fileobj=io.BytesIO(await request.body()), mode="r:gz") as tar:
                names = tar.getnames()
                tar.extractall(dest, filter="data")  # refuses absolute paths, "..", devices
        except (tarfile.TarError, OSError) as e:
            raise HTTPException(400, f"bad archive: {e}") from e
        return {"ok": True, "dest": str(dest), "files": len(names)}

    @app.get("/files")
    def get_file(path: str):
        p = resolve(path)
        if not p.is_file():
            raise HTTPException(404, f"not a file: {p}")
        return FileResponse(p)

    @app.put("/files")
    async def put_file(path: str, request: Request):
        p = resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(await request.body())
        return {"ok": True, "path": str(p), "bytes": p.stat().st_size}

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the colab bridge server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--workdir", default=os.environ.get("BRIDGE_WORKDIR", DEFAULT_WORKDIR))
    args = parser.parse_args()

    import uvicorn

    uvicorn.run(create_app(args.workdir), host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
