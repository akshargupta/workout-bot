"""Client for the bridge server running on Colab (see bridge_server.py and colab/bridge.ipynb).

Configuration comes from the environment, backfilled by a ``.env`` file:

* ``COLAB_URL``   — the bridge's public URL, e.g. ``https://your-name.ngrok-free.app``.
* ``COLAB_TOKEN`` — the bridge's bearer token. May be left unset when something in front of
  this process injects the ``Authorization`` header (a Claude Code cloud environment's
  network secret does exactly that).
"""

import io
import os
import subprocess
import tarfile
from pathlib import Path

import httpx
from dotenv import load_dotenv

__all__ = ["Colab", "ColabError"]


class ColabError(RuntimeError):
    """The bridge was unreachable, misconfigured, or returned an error."""


class Colab:
    def __init__(self, url: str | None = None, token: str | None = None,
                 http: httpx.Client | None = None):
        if http is None:
            load_dotenv(override=False)
            url = (url or os.environ.get("COLAB_URL", "")).strip().rstrip("/")
            token = (token or os.environ.get("COLAB_TOKEN", "")).strip()
            if not url:
                raise ColabError(
                    "COLAB_URL is not set. Put the bridge URL printed by colab/bridge.ipynb "
                    "in .env (see README)."
                )
            headers = {"ngrok-skip-browser-warning": "1"}  # skip ngrok's HTML interstitial
            if token:
                headers["Authorization"] = f"Bearer {token}"
            http = httpx.Client(base_url=url, headers=headers,
                                timeout=httpx.Timeout(60, read=120))
        self.http = http

    def _call(self, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            r = self.http.request(method, path, **kwargs)
        except httpx.HTTPError as e:
            raise ColabError(
                f"Could not reach the bridge ({e.__class__.__name__}: {e}). Is the Colab "
                "notebook still running?"
            ) from e
        if r.status_code == 401:
            raise ColabError("Bridge rejected the token (401). Check COLAB_TOKEN / BRIDGE_TOKEN.")
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except ValueError:
                detail = r.text[:500]
            raise ColabError(f"{method} {path} -> {r.status_code}: {detail}")
        return r

    # -- kernel ---------------------------------------------------------------------------

    def health(self) -> dict:
        return self._call("GET", "/health").json()

    def exec(self, code: str, timeout: float = 300) -> dict:
        """Run code in the persistent kernel. Returns status/stdout/stderr/result/error/images."""
        return self._call("POST", "/exec", json={"code": code, "timeout": timeout},
                          timeout=httpx.Timeout(60, read=timeout + 90)).json()

    def interrupt(self) -> None:
        self._call("POST", "/interrupt")

    def restart(self) -> None:
        self._call("POST", "/restart", timeout=httpx.Timeout(60, read=180))

    # -- jobs -----------------------------------------------------------------------------

    def start_job(self, cmd: str, cwd: str | None = None) -> dict:
        return self._call("POST", "/jobs", json={"cmd": cmd, "cwd": cwd}).json()

    def jobs(self) -> list[dict]:
        return self._call("GET", "/jobs").json()

    def job(self, jid: str) -> dict:
        return self._call("GET", f"/jobs/{jid}").json()

    def job_log(self, jid: str, offset: int = 0, max_bytes: int = 1_000_000) -> dict:
        return self._call("GET", f"/jobs/{jid}/log",
                          params={"offset": offset, "max_bytes": max_bytes}).json()

    def kill_job(self, jid: str) -> dict:
        return self._call("POST", f"/jobs/{jid}/kill", timeout=httpx.Timeout(60, read=60)).json()

    # -- files ----------------------------------------------------------------------------

    def push(self, root: str | os.PathLike = ".") -> dict:
        """Upload the project (git-tracked + untracked-but-not-ignored files) to Colab.

        Files are added or overwritten under <workdir>/project; nothing there is deleted,
        so outputs written next to the code on Colab survive a push.
        """
        root = Path(root).resolve()
        try:
            listed = subprocess.run(
                ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                cwd=root, capture_output=True, check=True,
            ).stdout.decode().split("\0")
        except (OSError, subprocess.CalledProcessError) as e:
            raise ColabError(f"push needs a git checkout at {root}: {e}") from e
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            for name in sorted(set(filter(None, listed))):
                if (root / name).is_file():  # skips files deleted but not yet committed
                    tar.add(root / name, arcname=name)
        return self._call("PUT", "/sync", content=buf.getvalue(),
                          timeout=httpx.Timeout(60, write=300, read=300)).json()

    def get_file(self, remote: str, local: str | os.PathLike) -> Path:
        local = Path(local)
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(self._call("GET", "/files", params={"path": remote},
                                     timeout=httpx.Timeout(60, read=600)).content)
        return local

    def put_file(self, local: str | os.PathLike, remote: str) -> dict:
        return self._call("PUT", "/files", params={"path": remote},
                          content=Path(local).read_bytes(),
                          timeout=httpx.Timeout(60, write=600, read=600)).json()
