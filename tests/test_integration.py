import csv
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest

import psutil

from master_sort import probe

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER = os.path.join(ROOT, "master_sort.py")
WORKER = os.path.join(ROOT, "worker_sort.py")


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def stop_worker(proc):
    try:
        parent = psutil.Process(proc.pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except Exception:
        proc.kill()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass


def run_master(args, csv_path):
    cmd = [sys.executable, MASTER] + args + ["--csv", csv_path]
    return subprocess.run(cmd, cwd=ROOT, text=True, encoding="utf-8", errors="replace",
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)


def read_rows(csv_path):
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class TestIntegration(unittest.TestCase):
    def test_seq_and_local_write_expected_rows(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "r.csv")
            r = run_master(["seq", "--size", "100000", "--repeat", "2"], path)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertEqual(len(read_rows(path)), 2)
            self.assertTrue(all(x["ok"] == "True" for x in read_rows(path)))

            os.remove(path)
            r = run_master(["local", "--size", "100000", "--procs", "1,2", "--repeat", "1"], path)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertEqual(len(read_rows(path)), 2)

    def test_dist_honors_explicit_repeat(self):
        port = free_port()
        proc = subprocess.Popen(
            [sys.executable, "-u", WORKER, "--port", str(port), "--procs", "2"],
            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.time() + 15
            while time.time() < deadline:
                if probe("127.0.0.1", port, 0.3):
                    break
                time.sleep(0.2)
            else:
                self.fail("worker loopback tidak merespons")

            with tempfile.TemporaryDirectory() as d:
                path = os.path.join(d, "r.csv")
                r = run_master(["dist", "--size", "200000",
                                "--hosts", f"127.0.0.1:{port}", "--repeat", "2"], path)
                self.assertEqual(r.returncode, 0, r.stdout)
                self.assertIn("LULUS", r.stdout)
                rows = read_rows(path)
                self.assertEqual(len(rows), 2)
                self.assertTrue(all(x["ok"] == "True" for x in rows))
                self.assertTrue(all(x["repeat"] in ("1", "2") for x in rows))
        finally:
            stop_worker(proc)


if __name__ == "__main__":
    unittest.main()
