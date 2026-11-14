"""Run 3 x 4 isolated, 120-second comparisons; never opens the working database.

Run with a Python environment containing requirements.txt and locust==2.47.0:
    python tests/load/run_pool_experiment.py --output <new-external-directory>
The source must be committed first. Results identify that immutable commit.
"""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import zipfile


ROOT = Path(__file__).resolve().parents[2]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def run(output, port, baseline_ref):
    with socket.socket() as probe_socket:
        probe_socket.bind(("127.0.0.1", port))
    output.mkdir(parents=True, exist_ok=False)
    sha = git("rev-parse", "HEAD").decode().strip()
    baseline_sha = git("rev-parse", baseline_ref).decode().strip()
    baseline = git("show", f"{baseline_sha}:app/database.py")
    snapshot = output / "source"
    snapshot.mkdir()
    with zipfile.ZipFile(io.BytesIO(git("archive", "--format=zip", sha,
                                     "app", "scripts", "tests/load", "requirements.txt"))) as archive:
        archive.extractall(snapshot)
    manifest = {"source_commit": sha, "baseline_commit": baseline_sha,
                "baseline_database_sha256": hashlib.sha256(baseline).hexdigest(),
                "updated_database_sha256": hashlib.sha256((snapshot / "app/database.py").read_bytes()).hexdigest(),
                "platform": platform.platform(), "processor": platform.processor(),
                "logical_cpus": os.cpu_count(), "python": sys.version,
                "users": 50, "spawn_rate": 10, "duration_seconds": 120, "runs": []}
    (output / "requirements-freeze.txt").write_bytes(
        subprocess.check_output([sys.executable, "-m", "pip", "freeze"]))
    for repeat in range(1, 4):
        for label, size, overflow in [("R0", 5, 10), ("R1", 40, 10), ("R2", 50, 50), ("R3", 5, 10)]:
            name = f"{label}-{repeat}"
            folder = output / name
            source = folder / "source"
            shutil.copytree(snapshot, source)
            if label == "R0":
                (source / "app/database.py").write_bytes(baseline)
            env = os.environ.copy()
            # Use a new key only for disposable, fresh benchmark data; never log it.
            from cryptography.fernet import Fernet
            env.update(BMS_DATABASE_URL=f"sqlite:///{(folder / 'benchmark.db').as_posix()}",
                       BMS_DATA_KEY=Fernet.generate_key().decode(), BMS_DB_POOL_SIZE=str(size),
                       BMS_DB_MAX_OVERFLOW=str(overflow),
                       BMS_LOAD_LOGIN_COUNTS=str(folder / "logins.json"), PYTHONIOENCODING="utf-8")
            print(f"START {name}", flush=True)
            with (folder / "seed.log").open("w", encoding="utf-8") as log:
                subprocess.run([sys.executable, "-B", "-m", "scripts.seed"], cwd=source,
                               env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)
            probe = "from app.database import engine; import json; c=engine.raw_connection(); print(json.dumps({'journal_mode':c.execute('pragma journal_mode').fetchone()[0],'busy_timeout':c.execute('pragma busy_timeout').fetchone()[0],'pool_size':engine.pool.size(),'max_overflow':engine.pool._max_overflow})); c.close(); engine.dispose()"
            actual = json.loads(subprocess.check_output([sys.executable, "-B", "-c", probe], cwd=source, env=env))
            assert actual == {"journal_mode": "delete" if label == "R0" else "wal",
                              "busy_timeout": 5000 if label == "R0" else 30000,
                              "pool_size": size, "max_overflow": overflow}, actual
            with (folder / "server.log").open("w", encoding="utf-8") as log:
                server = subprocess.Popen([sys.executable, "-B", "-m", "uvicorn", "app.main:app",
                                           "--host", "127.0.0.1", "--port", str(port), "--no-access-log"],
                                          cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT)
                try:
                    host = f"http://127.0.0.1:{port}"
                    for _ in range(100):
                        if server.poll() is not None:
                            raise RuntimeError(f"{name}: server stopped; inspect server.log")
                        try:
                            with urllib.request.urlopen(host + "/health", timeout=1) as response:
                                assert response.status == 200
                            break
                        except OSError:
                            time.sleep(0.2)
                    else:
                        raise RuntimeError("Server readiness timed out")
                    started = time.time()
                    with (folder / "locust.log").open("w", encoding="utf-8") as locust_log:
                        result = subprocess.run([sys.executable, "-B", "-m", "locust", "-f", "tests/load/locustfile.py",
                                                 "--headless", "-u", "50", "-r", "10", "-t", "120s",
                                                 "--host", host, "--csv", str(folder / "load"),
                                                 "--csv-full-history", "--stop-timeout", "10"],
                                                cwd=source, env=env, stdout=locust_log,
                                                stderr=subprocess.STDOUT, timeout=180)
                    elapsed = round(time.time() - started, 2)
                finally:
                    server.terminate()
                    server.wait(timeout=20)
            counts = json.loads((folder / "logins.json").read_text())
            with (folder / "load_stats.csv").open(newline="", encoding="utf-8") as stream:
                stats = next(row for row in csv.DictReader(stream) if row["Name"] == "Aggregated")
            row = {"run": name, "configuration": actual, "logins": counts,
                   "locust_exit_code": result.returncode, "elapsed_seconds": elapsed, "statistics": stats,
                   "queuepool_timeouts": (folder / "server.log").read_text().count("sqlalchemy.exc.TimeoutError")}
            manifest["runs"].append(row)
            (output / "results.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            print(f"DONE {name}: requests={stats['Request Count']} failures={stats['Failure Count']} p95={stats['95%']}ms logins={counts}", flush=True)
            if counts != {"successful": 50, "failed": 0} or result.returncode not in (0, 1):
                raise RuntimeError(f"Invalid workload in {name}; inspect logs before continuing")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8770)
    parser.add_argument("--baseline", default="380edd9037f3d1b61a018978c552a56739664b22",
                        help="Commit containing the original database module")
    args = parser.parse_args()
    run(args.output.resolve(), args.port, args.baseline)
