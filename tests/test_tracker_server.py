import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import urlopen

import src.server as server_module


class TrackerServerTests(unittest.TestCase):
    def test_frozen_build_prefers_docs_beside_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            docs.mkdir()
            (docs / "matchLoadouts.html").write_text("tracker-ok", encoding="utf-8")
            (root / "lib").mkdir()

            with patch.object(server_module, "PROJECT_ROOT", root / "lib"), patch.object(
                server_module.sys, "frozen", True, create=True
            ), patch.object(server_module.sys, "executable", str(root / "vry.exe")):
                self.assertEqual(server_module._resolve_docs_dir(), docs.resolve())

    def test_local_tracker_server_serves_entrypoint_from_frozen_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            docs.mkdir()
            (docs / "matchLoadouts.html").write_text("tracker-ok", encoding="utf-8")
            (root / "lib").mkdir()

            logs = []
            tracker = server_module.Server(logs.append, Error=None)

            with patch.object(server_module, "PROJECT_ROOT", root / "lib"), patch.object(
                server_module.sys, "frozen", True, create=True
            ), patch.object(server_module.sys, "executable", str(root / "vry.exe")):
                tracker.start_docs_server(65535)
                try:
                    url = tracker.get_match_loadouts_url(65535)
                    with urlopen(url, timeout=2) as response:
                        self.assertEqual(response.status, 200)
                        self.assertEqual(response.read().decode("utf-8"), "tracker-ok")
                finally:
                    tracker.docs_server.shutdown()
                    tracker.docs_server.server_close()

    def test_docs_server_serves_players_page_and_logs_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            docs.mkdir()
            (docs / "matchLoadouts.html").write_text("tracker-ok", encoding="utf-8")
            (docs / "players.html").write_text("players-ok", encoding="utf-8")

            logs = []
            tracker = server_module.Server(logs.append, Error=None)

            with patch.object(server_module, "PROJECT_ROOT", root), patch.dict(server_module.os.environ):
                tracker.start_docs_server(65535)
                try:
                    url = f"http://127.0.0.1:{tracker.docs_port}/players.html"
                    with urlopen(url, timeout=2) as response:
                        self.assertEqual(response.read().decode("utf-8"), "players-ok")
                        # Browsers must revalidate, or an updated players.js is ignored after an update.
                        self.assertEqual(response.headers.get("Cache-Control"), "no-cache")
                    self.assertTrue(
                        any("/players.html?port=65535" in line for line in logs), logs
                    )
                    self.assertEqual(
                        server_module.os.environ.get("VRY_PLAYERS_URL"),
                        f"http://127.0.0.1:{tracker.docs_port}/players.html?port=65535",
                    )
                finally:
                    tracker.docs_server.shutdown()
                    tracker.docs_server.server_close()

    def test_docs_server_is_reachable_from_lan_for_phones(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "docs"
            docs.mkdir()
            (docs / "matchLoadouts.html").write_text("tracker-ok", encoding="utf-8")

            tracker = server_module.Server(lambda _: None, Error=None)
            self.assertIsNone(tracker.get_players_url(65535, host="192.168.1.5"))

            with patch.object(server_module, "PROJECT_ROOT", root), patch.dict(server_module.os.environ):
                tracker.start_docs_server(65535)
                try:
                    # All interfaces, so a phone on the same network can load the pages.
                    self.assertEqual(tracker.docs_server.server_address[0], "0.0.0.0")
                    self.assertEqual(
                        tracker.get_players_url(65535, host="192.168.1.5"),
                        f"http://192.168.1.5:{tracker.docs_port}/players.html?port=65535",
                    )
                finally:
                    tracker.docs_server.shutdown()
                    tracker.docs_server.server_close()


if __name__ == "__main__":
    unittest.main()
