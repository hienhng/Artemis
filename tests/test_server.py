"""Check the actual HTTP/WebSocket server's origin boundary on loopback."""

from pathlib import Path
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

from websockets.exceptions import InvalidStatus
from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parent.parent


class ServerTests(unittest.TestCase):
    def test_health_and_websocket_origin_protection(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        with tempfile.TemporaryDirectory(prefix="chatbot-server-") as directory:
            log_path = Path(directory) / "server.log"
            with log_path.open("w", encoding="utf-8") as log:
                process = subprocess.Popen(
                    [sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py"),
                     "--server.address=127.0.0.1", f"--server.port={port}",
                     "--server.fileWatcherType=none", "--browser.gatherUsageStats=false"],
                    cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                try:
                    # Ignore host proxy settings for a loopback-only health check.
                    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                    deadline = time.monotonic() + 30
                    while True:
                        try:
                            with opener.open(f"http://127.0.0.1:{port}/_stcore/health", timeout=2) as response:
                                self.assertEqual(response.status, 200)
                            break
                        except (OSError, urllib.error.URLError):
                            if process.poll() is not None or time.monotonic() > deadline:
                                self.fail("Streamlit server did not start: " + log_path.read_text(encoding="utf-8"))
                            time.sleep(0.2)
                    url = f"ws://127.0.0.1:{port}/_stcore/stream"
                    with self.assertRaises(InvalidStatus) as rejected:
                        with connect(url, origin="https://untrusted.example", open_timeout=5, proxy=None):
                            pass
                    self.assertEqual(rejected.exception.response.status_code, 403)
                    with connect(url, origin=f"http://127.0.0.1:{port}", open_timeout=5, proxy=None):
                        pass
                finally:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
