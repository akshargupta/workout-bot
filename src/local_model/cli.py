"""`colab` — run code on the Colab GPU runtime from here.

    colab status                      GPU, disk, kernel and job status
    colab run script.py               run a file in the persistent kernel (state is kept)
    colab run -c "print(1+1)"         run a snippet
    colab interrupt | restart         stop the running cell | wipe kernel state
    colab push                        upload this repo to <workdir>/project on Colab
    colab job start "python train.py" background job (for anything longer than a few minutes)
    colab job ls | logs ID [-f] | kill ID
    colab get REMOTE [LOCAL]          download a file      colab put LOCAL [REMOTE]  upload one
"""

import argparse
import json
import sys
import time
from pathlib import Path

from local_model.colab import Colab, ColabError


def _print_exec(result: dict) -> int:
    if result["stdout"]:
        sys.stdout.write(result["stdout"])
    if result["result"] is not None:
        print(result["result"])
    if result["stderr"]:
        sys.stderr.write(result["stderr"])
    for path in result["images"]:
        print(f"[image saved on Colab: {path}  — fetch with: colab get {path}]")
    if result["error"]:
        sys.stderr.write(result["error"]["traceback"] + "\n")
    print(f"[{result['status']} in {result['elapsed']}s]", file=sys.stderr)
    return {"ok": 0, "timeout": 124}.get(result["status"], 1)


def _follow(colab: Colab, jid: str, offset: int) -> int:
    while True:
        chunk = colab.job_log(jid, offset)
        sys.stdout.write(chunk["text"])
        sys.stdout.flush()
        offset = chunk["next_offset"]
        if offset < chunk["size"]:
            continue
        info = colab.job(jid)
        if info["status"] == "exited":
            rest = colab.job_log(jid, offset)  # output written between the two calls
            sys.stdout.write(rest["text"])
            print(f"[job {jid} exited with {info['returncode']}]", file=sys.stderr)
            return 0 if info["returncode"] == 0 else 1
        time.sleep(3)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="colab", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="show GPU, disk, kernel and job status")

    run = sub.add_parser("run", help="run a file or snippet in the persistent kernel")
    run.add_argument("file", nargs="?", help="python file to run ('-' for stdin)")
    run.add_argument("-c", "--code", help="code to run instead of a file")
    run.add_argument("-t", "--timeout", type=float, default=300,
                     help="seconds before the kernel is interrupted (default 300)")

    sub.add_parser("interrupt", help="interrupt the running execution")
    sub.add_parser("restart", help="restart the kernel (all state is lost)")

    push = sub.add_parser("push", help="upload this repo to Colab")
    push.add_argument("root", nargs="?", default=".")

    job = sub.add_parser("job", help="background jobs")
    jsub = job.add_subparsers(dest="job_command", required=True)
    start = jsub.add_parser("start", help="start a shell command in the background")
    start.add_argument("cmd", nargs=argparse.REMAINDER)
    start.add_argument("--cwd", help="working dir (default: the pushed project)")
    start.add_argument("-f", "--follow", action="store_true", help="stream its log")
    jsub.add_parser("ls", help="list jobs")
    logs = jsub.add_parser("logs", help="show a job's log")
    logs.add_argument("id")
    logs.add_argument("-n", "--bytes", type=int, default=20_000, help="tail size in bytes")
    logs.add_argument("-f", "--follow", action="store_true", help="keep streaming until it exits")
    kill = jsub.add_parser("kill", help="stop a job")
    kill.add_argument("id")

    get = sub.add_parser("get", help="download a file from Colab")
    get.add_argument("remote")
    get.add_argument("local", nargs="?")
    put = sub.add_parser("put", help="upload a file to Colab")
    put.add_argument("local")
    put.add_argument("remote", nargs="?")

    args = parser.parse_args(argv)
    try:
        colab = Colab()
        match args.command:
            case "status":
                print(json.dumps(colab.health(), indent=2))
            case "run":
                if args.code is not None:
                    code = args.code
                elif args.file == "-":
                    code = sys.stdin.read()
                elif args.file:
                    code = Path(args.file).read_text()
                else:
                    parser.error("run needs a FILE or -c CODE")
                return _print_exec(colab.exec(code, args.timeout))
            case "interrupt":
                colab.interrupt()
            case "restart":
                colab.restart()
                print("kernel restarted")
            case "push":
                r = colab.push(args.root)
                print(f"pushed {r['files']} files to {r['dest']}")
            case "job":
                match args.job_command:
                    case "start":
                        cmd = " ".join(args.cmd).strip()
                        if not cmd:
                            parser.error("job start needs a command")
                        info = colab.start_job(cmd, args.cwd)
                        print(f"started job {info['id']}  (log: {info['log']})", file=sys.stderr)
                        if args.follow:
                            return _follow(colab, info["id"], 0)
                        print(info["id"])
                    case "ls":
                        for j in colab.jobs():
                            rc = "" if j["returncode"] is None else f" rc={j['returncode']}"
                            print(f"{j['id']}  {j['status']}{rc}  {j['cmd']}")
                    case "logs":
                        if args.follow:
                            return _follow(colab, args.id, -args.bytes)
                        sys.stdout.write(colab.job_log(args.id, -args.bytes)["text"])
                    case "kill":
                        info = colab.kill_job(args.id)
                        print(f"job {info['id']} {info['status']} rc={info['returncode']}")
            case "get":
                local = args.local or Path(args.remote).name
                print(colab.get_file(args.remote, local))
            case "put":
                remote = args.remote or f"project/{args.local}"
                print(colab.put_file(args.local, remote)["path"])
    except ColabError as e:
        print(f"colab: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
