"""End-to-end tests: the real bridge app + a real IPython kernel, driven through the client.

FastAPI's TestClient is an httpx.Client, so it plugs straight into Colab(http=...) and these
tests exercise the same client code the `colab` CLI uses against Colab.
"""

import io
import subprocess
import tarfile
import threading
import time

import pytest
from fastapi.testclient import TestClient

from local_model.bridge_server import create_app
from local_model.cli import main as cli_main
from local_model.colab import Colab, ColabError

TOKEN = "test-token-0123456789abcdef"


@pytest.fixture(scope="module")
def workdir(tmp_path_factory):
    return tmp_path_factory.mktemp("work")


@pytest.fixture(scope="module")
def http(workdir):
    app = create_app(workdir, token=TOKEN)
    with TestClient(app, headers={"Authorization": f"Bearer {TOKEN}"}) as client:
        yield client


@pytest.fixture
def colab(http):
    return Colab(http=http)


def test_rejects_missing_and_wrong_token(http):
    assert http.get("/health", headers={"Authorization": ""}).status_code == 401
    assert http.get("/health", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert http.get("/health").status_code == 200


def test_refuses_to_start_with_weak_token(tmp_path):
    with pytest.raises(SystemExit):
        create_app(tmp_path, token="short")


def test_exec_output_and_result(colab):
    r = colab.exec("print('hello'); 6 * 7")
    assert r["status"] == "ok"
    assert r["stdout"] == "hello\n"
    assert r["result"] == "42"


def test_state_persists_between_calls(colab):
    colab.exec("x = 41")
    assert colab.exec("x + 1")["result"] == "42"


def test_error_reports_traceback(colab):
    r = colab.exec("1 / 0")
    assert r["status"] == "error"
    assert r["error"]["ename"] == "ZeroDivisionError"
    assert "\x1b[" not in r["error"]["traceback"]  # ANSI colour stripped


def test_stderr_captured(colab):
    r = colab.exec("import sys; sys.stderr.write('warn\\n')")
    assert r["stderr"] == "warn\n"


def test_timeout_interrupts_and_kernel_survives(colab):
    colab.exec("kept = 'still here'")
    r = colab.exec("import time; time.sleep(60)", timeout=1)
    assert r["status"] == "timeout"
    assert r["error"]["ename"] == "KeyboardInterrupt"
    assert colab.exec("kept")["result"] == "'still here'"


def test_concurrent_exec_is_rejected_then_interrupt_works(colab):
    first: dict = {}
    t = threading.Thread(target=lambda: first.update(colab.exec("import time; time.sleep(30)")))
    t.start()
    try:
        deadline = time.time() + 10
        while not colab.health()["kernel_busy"] and time.time() < deadline:
            time.sleep(0.05)
        with pytest.raises(ColabError, match="409"):
            colab.exec("1")
        colab.interrupt()
    finally:
        t.join(timeout=30)
    assert first["error"]["ename"] == "KeyboardInterrupt"


def test_restart_wipes_state(colab):
    colab.exec("gone = 1")
    colab.restart()
    assert colab.exec("gone")["error"]["ename"] == "NameError"


def test_plot_is_saved_as_png(colab):
    pytest.importorskip("matplotlib")
    r = colab.exec("import matplotlib.pyplot as plt; plt.plot([1, 2]); plt.show()")
    assert r["images"] and r["images"][0].endswith(".png")


def _wait(colab, jid):
    for _ in range(100):
        info = colab.job(jid)
        if info["status"] == "exited":
            return info
        time.sleep(0.1)
    raise AssertionError("job did not exit")


def test_job_runs_and_logs(colab):
    info = colab.start_job("echo out; echo err >&2; exit 3")
    done = _wait(colab, info["id"])
    assert done["returncode"] == 3
    log = colab.job_log(info["id"])["text"]
    assert "out" in log and "err" in log
    assert colab.job_log(info["id"], offset=-4)["text"] == "err\n"
    assert any(j["id"] == info["id"] for j in colab.jobs())


def test_job_kill(colab):
    info = colab.start_job("sleep 60")
    killed = colab.kill_job(info["id"])
    assert killed["status"] == "exited"


def test_unknown_job_is_404(colab):
    with pytest.raises(ColabError, match="404"):
        colab.job("nope")


def test_push_makes_project_importable(colab, tmp_path, workdir):
    repo = tmp_path / "repo"
    (repo / "src" / "mypkg").mkdir(parents=True)
    (repo / "src" / "mypkg" / "__init__.py").write_text("VALUE = 'pushed'\n")
    (repo / ".gitignore").write_text("secret.txt\n")
    (repo / "secret.txt").write_text("do not upload")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)

    r = colab.push(repo)
    assert r["files"] == 2  # __init__.py and .gitignore; secret.txt is ignored
    assert not (workdir / "project" / "secret.txt").exists()
    assert colab.exec("import mypkg; mypkg.VALUE")["result"] == "'pushed'"
    # jobs see the project too
    info = colab.start_job("python -c 'import mypkg; print(mypkg.VALUE)'")
    _wait(colab, info["id"])
    assert colab.job_log(info["id"])["text"] == "pushed\n"


def test_sync_rejects_path_escape(http, workdir):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        data = b"evil"
        member = tarfile.TarInfo("../escaped.txt")
        member.size = len(data)
        tar.addfile(member, io.BytesIO(data))
    assert http.put("/sync", content=buf.getvalue()).status_code == 400
    assert not (workdir / "escaped.txt").exists()


def test_file_round_trip(colab, tmp_path):
    src = tmp_path / "in.bin"
    src.write_bytes(b"\x00\x01weights")
    colab.put_file(src, "data/in.bin")
    out = colab.get_file("data/in.bin", tmp_path / "out.bin")
    assert out.read_bytes() == b"\x00\x01weights"
    with pytest.raises(ColabError, match="404"):
        colab.get_file("data/missing.bin", tmp_path / "x")


def test_cli_run_and_exit_codes(http, monkeypatch, capsys, tmp_path):
    monkeypatch.setattr("local_model.cli.Colab", lambda: Colab(http=http))
    script = tmp_path / "s.py"
    script.write_text("print('from file')\n")
    assert cli_main(["run", str(script)]) == 0
    assert "from file" in capsys.readouterr().out
    assert cli_main(["run", "-c", "raise ValueError('boom')"]) == 1
    assert "ValueError: boom" in capsys.readouterr().err


def test_cli_job_follow(http, monkeypatch, capsys):
    monkeypatch.setattr("local_model.cli.Colab", lambda: Colab(http=http))
    assert cli_main(["job", "start", "-f", "echo", "line1;", "echo", "line2"]) == 0
    out = capsys.readouterr().out
    assert "line1\nline2\n" in out


def test_client_requires_url(monkeypatch, tmp_path):
    monkeypatch.delenv("COLAB_URL", raising=False)
    monkeypatch.chdir(tmp_path)  # no .env here
    with pytest.raises(ColabError, match="COLAB_URL"):
        Colab()
