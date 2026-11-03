import json
import re
import unittest
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "docs"


def load(name):
    return json.loads((DOCS / name).read_text(encoding="utf-8"))


class PlayersPageTests(unittest.TestCase):
    def test_sample_payload_shape(self):
        hb = load("players.sample.json")
        self.assertEqual(hb["type"], "heartbeat")
        self.assertEqual(hb["state"], "INGAME")
        players = hb["players"]
        self.assertEqual(len(players), 5)
        relations = [p["relation"] for p in players.values()]
        self.assertEqual(relations.count("ally"), 3)
        self.assertEqual(relations.count("enemy"), 2)
        self.assertEqual(players[hb["puuid"]]["relation"], "ally")

        parties = [p["partyNumber"] for p in players.values() if p["partyNumber"] > 0]
        self.assertEqual(len(parties), 2)
        self.assertEqual(len(set(parties)), 1)

        names = [p["name"] for p in players.values()]
        self.assertIn("<img src=x onerror=alert(1)>", names)
        self.assertIn("#", names)  # streamer mode: src/names.py sends "#"
        self.assertTrue(any(p["weapons"] is None and p["sprays"] is None for p in players.values()))

        full = [p for p in players.values() if p["weapons"] and len(p["weapons"]) >= 3]
        self.assertTrue(full)
        for weapon in full[0]["weapons"].values():
            for key in ("weapon", "skinDisplayName", "skinDisplayIcon"):
                self.assertIn(key, weapon)

    def test_lobby_payload_shape(self):
        # Mirrors the MENUS heartbeat in main.py: party members only, no loadout fields.
        hb = load("players.lobby.sample.json")
        self.assertEqual(hb["type"], "heartbeat")
        self.assertEqual(hb["state"], "MENUS")
        players = hb["players"]
        self.assertGreaterEqual(len(players), 2)
        self.assertIn(hb["puuid"], players)
        for p in players.values():
            for key in ("name", "rank", "level"):
                self.assertIn(key, p)
            for key in ("relation", "weapons", "agent"):
                self.assertNotIn(key, p)

    def test_page_wiring(self):
        html = (DOCS / "players.html").read_text(encoding="utf-8")
        self.assertIn("vendor/tailwind.js", html)
        self.assertIn("players.js", html)
        self.assertTrue((DOCS / "vendor" / "tailwind.js").is_file())

        js = (DOCS / "players.js").read_text(encoding="utf-8")
        for needle in ('"heartbeat"', '"1100"', "players.sample.json", "players.lobby.sample.json"):
            self.assertIn(needle, js)
        self.assertIsNone(re.search(r"innerHTML\s*=\s*`", js))

    def test_i18n_languages_match(self):
        i18n = load("players.i18n.json")
        self.assertEqual(sorted(i18n), ["en", "tr"])
        en, tr = i18n["en"], i18n["tr"]
        self.assertEqual(sorted(en), sorted(tr))
        for section in ("ui", "states", "modes"):
            self.assertEqual(sorted(en[section]), sorted(tr[section]), section)
        self.assertEqual(len(en["ranks"]), 28)
        self.assertEqual(len(tr["ranks"]), 28)
        self.assertEqual(en["ranks"][27], "Radiant")
        self.assertEqual(en["ranks"][26], "Immortal 3")
        self.assertEqual(tr["ranks"][27], "Radyant")
        self.assertEqual(sorted(en["states"]), ["INGAME", "MENUS", "PREGAME"])

    def test_i18n_covers_every_game_mode(self):
        from src.constants import gamemodes

        modes = load("players.i18n.json")["tr"]["modes"]
        for mode in set(gamemodes.values()):
            self.assertIn(mode, modes)

    def test_language_toggle_wiring(self):
        html = (DOCS / "players.html").read_text(encoding="utf-8")
        self.assertIn('data-lang="en"', html)
        self.assertIn('data-lang="tr"', html)
        js = (DOCS / "players.js").read_text(encoding="utf-8")
        for needle in ("players.i18n.json", '"vry.lang"', "language=tr-TR"):
            self.assertIn(needle, js)

    def test_sample_weapons_carry_skin_ids(self):
        # Real payloads carry the skin uuid under "skin" (src/Loadouts.py); Turkish names are looked up by it.
        hb = load("players.sample.json")
        weapons = [w for p in hb["players"].values() for w in (p["weapons"] or {}).values()]
        self.assertTrue(weapons)
        self.assertTrue(all(re.fullmatch(r"[0-9a-f-]{36}", w.get("skin", "")) for w in weapons))


if __name__ == "__main__":
    unittest.main()
