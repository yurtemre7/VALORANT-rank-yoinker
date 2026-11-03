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
        self.assertEqual(len(players), 6)
        relations = [p["relation"] for p in players.values()]
        self.assertEqual(relations.count("ally"), 3)
        self.assertEqual(relations.count("enemy"), 3)
        self.assertEqual(players[hb["puuid"]]["relation"], "ally")

        parties = [p["partyNumber"] for p in players.values() if p["partyNumber"] > 0]
        self.assertEqual(len(parties), 2)
        self.assertEqual(len(set(parties)), 1)

        names = [p["name"] for p in players.values()]
        self.assertIn("Çağrı#TR1", names)  # non-ASCII name renders as-is
        self.assertIn("#", names)  # streamer mode: src/names.py sends "#"
        self.assertTrue(any(p["weapons"] is None and p["sprays"] is None for p in players.values()))

        full = [p for p in players.values() if p["weapons"] and len(p["weapons"]) >= 3]
        self.assertTrue(full)
        for weapon in full[0]["weapons"].values():
            for key in ("weapon", "skinDisplayName", "skinDisplayIcon"):
                self.assertIn(key, weapon)

    def test_sample_payload_edge_cases(self):
        # Placeholders exactly as the Python side sends them (src/player_stats.py, src/rank.py, main.py).
        players = load("players.sample.json")["players"].values()
        self.assertTrue(any(
            p["kd"] == "N/A" and p["headshotPercentage"] == "N/A" and p["winPercentage"] == "None (0)"
            for p in players
        ))
        self.assertTrue(any(p["name"] == "#" and p["agent"] == "Unknown" for p in players))
        types = {s["type"] for p in players for s in (p["sprays"] or {}).values()}
        self.assertTrue({"spray", "flex"} <= types)

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
            for key in ("relation", "agent"):
                self.assertNotIn(key, p)

    def test_lobby_extras_match_python_output(self):
        # Same keys as src/lobby_info.py produces for the MENUS heartbeat.
        from src.lobby_info import friends_activity, member_extras, party_status
        from tests.test_lobby_info import FRIEND, ME, private, row

        hb = load("players.lobby.sample.json")
        self.assertLessEqual(set(party_status(private())), set(hb["party"]))  # plus party_details keys
        self.assertEqual(hb["party"]["state"], "MATCHMAKING")
        extras = set(member_extras(private(), {}))
        for p in hb["players"].values():
            self.assertLessEqual(extras, set(p))
        self.assertEqual(sum(p["isOwner"] for p in hb["players"].values()), 1)
        self.assertTrue(any(p["isIdle"] for p in hb["players"].values()))

        friend_keys = set(friends_activity([row(FRIEND, private())], ME, {ME}, {}, {})[0])
        self.assertTrue(hb["friends"])
        for friend in hb["friends"]:
            self.assertEqual(set(friend), friend_keys)
        self.assertEqual({f["state"] for f in hb["friends"]}, {"INGAME", "PREGAME", "MENUS"})

    def test_lobby_account_part1_matches_python_output(self):
        # Shapes produced by src/account_info.py (own_loadout, party_details) via main.py.
        from src.account_info import party_details
        from tests.test_account_info import METADATA, VANDAL
        from src.account_info import own_loadout

        hb = load("players.lobby.sample.json")
        details = party_details({"Members": [{"Subject": "x", "IsReady": True, "Pings": []}]})
        self.assertLessEqual(set(details) - {"members"}, set(hb["party"]))
        member_keys = set(details["members"]["x"])
        for p in hb["players"].values():
            self.assertLessEqual(member_keys, set(p))
        self.assertTrue(any(p["isReady"] is False for p in hb["players"].values()))
        self.assertGreater(hb["party"]["rrPenalty"], 0)
        me = hb["players"][hb["puuid"]]
        weapon_keys = set(own_loadout({"Guns": [{"ID": VANDAL, "SkinID": "skin-rgx", "ChromaID": "chroma-red", "CharmID": "buddy-1"}]}, METADATA)[0][VANDAL])
        self.assertTrue(me["weapons"])
        for weapon in me["weapons"].values():
            self.assertLessEqual(set(weapon) - {"buddy_displayIcon"}, weapon_keys)
        others = [p for puuid, p in hb["players"].items() if puuid != hb["puuid"]]
        self.assertTrue(all("weapons" not in p for p in others))

    def test_lobby_account_panel_matches_python_output(self):
        # Shapes produced by src/account_info.py and assembled by src/account_service.py.
        from src.account_info import battlepass, daily_store, rr_history, wallet
        from tests.test_account_info import METADATA, VP

        account = load("players.lobby.sample.json")["account"]
        self.assertEqual(set(account), {"wallet", "store", "battlepass", "rrHistory"})
        sample_wallet = wallet({"Balances": {VP: 1}}, METADATA)[0]
        for chip in account["wallet"]:
            self.assertEqual(set(chip), set(sample_wallet))
        self.assertEqual({c["id"] for c in account["wallet"]}, {
            "85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741", "e59aa87c-4cbf-517a-5983-6e81511be9b7", "85ca954a-41f2-ce94-9b45-8ca3dd39a00d"})
        store = daily_store({"SkinsPanelLayout": {"SingleItemStoreOffers": [{"Cost": {VP: 1}, "Rewards": [{"ItemID": "lvl-rgx-1"}]}]}}, METADATA, now=0)
        self.assertEqual(set(account["store"]), set(store))
        self.assertEqual(len(account["store"]["offers"]), 4)
        for offer in account["store"]["offers"]:
            self.assertEqual(set(offer), set(store["offers"][0]))
        pass_ = battlepass({"Contracts": [{"ContractDefinitionID": "bp", "ProgressionLevelReached": 1}]}, METADATA)
        self.assertEqual(set(account["battlepass"]), set(pass_))
        history_keys = set(rr_history({"Matches": [{"MatchStartTime": 1}]}, {})[0])
        self.assertEqual(len(account["rrHistory"]), 5)
        for match in account["rrHistory"]:
            self.assertEqual(set(match), history_keys)
        self.assertTrue(any(m["placement"] for m in account["rrHistory"]))
        self.assertTrue(any(m["earned"] < 0 for m in account["rrHistory"]))
        # Turkish skin names are looked up by the offer's skin uuid in the bundled file.
        names = load("players.tr-names.json")
        for offer in account["store"]["offers"]:
            self.assertIn(offer["skin"], names)

    def test_ingame_map_is_name_with_splash(self):
        # main.py sends the map name in "map" and the image in "mapSplash".
        hb = load("players.sample.json")
        self.assertEqual(hb["map"], ["Ascent"])
        self.assertTrue(hb["mapSplash"].startswith("https://media.valorant-api.com/maps/"))

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
        for section in ("ui", "states", "modes", "currencies"):
            self.assertEqual(sorted(en[section]), sorted(tr[section]), section)
        self.assertEqual(len(en["ranks"]), 28)
        self.assertEqual(len(tr["ranks"]), 28)
        self.assertEqual(en["ranks"][27], "Radiant")
        self.assertEqual(en["ranks"][26], "Immortal 3")
        self.assertEqual(tr["ranks"][27], "Radyant")
        self.assertEqual(sorted(en["states"]), ["INGAME", "MENUS", "PREGAME"])
        for key in ("hiddenPlayer", "emotes", "waitingParty", "demoFailed", "friends", "inQueue", "matchFound",
                    "openParty", "closedParty", "partyLeader", "afk", "notReady", "rankGap", "queueBlocked",
                    "account", "dailyStore", "resetsIn", "battlePass", "level", "recentRanked", "placement"):
            self.assertIn(key, en["ui"])

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
        for needle in ("players.i18n.json", '"vry.lang"', "players.tr-names.json", "language=tr-TR"):
            self.assertIn(needle, js)

    def test_sample_weapons_carry_skin_ids(self):
        # Real payloads carry the skin uuid under "skin" (src/Loadouts.py); Turkish names are looked up by it.
        hb = load("players.sample.json")
        weapons = [w for p in hb["players"].values() for w in (p["weapons"] or {}).values()]
        self.assertTrue(weapons)
        self.assertTrue(all(re.fullmatch(r"[0-9a-f-]{36}", w.get("skin", "")) for w in weapons))

    def test_square_card_art(self):
        # Every card slot on the page is square: use valorant-api's smallart, not the tall largeart from the payload.
        js = (DOCS / "players.js").read_text(encoding="utf-8")
        self.assertIn("/smallart.png", js)
        self.assertEqual(len(re.findall(r"img\((?:p|f)\.playerCard", js)), 0)

    def test_bundled_turkish_names(self):
        # Local copy of Riot's tr-TR names; the page only goes online for uuids missing here.
        names = load("players.tr-names.json")
        self.assertTrue(all(re.fullmatch(r"[0-9a-f-]{36}", uuid) for uuid in names))
        self.assertEqual(names["9c82e19d-4575-0200-1a81-3eacf00cf872"], "VANDAL")
        self.assertEqual(names["2f59173c-4bed-b6c3-2191-dea9b58be9c7"], "YAKIN DÖVÜŞ SİLAHI")
        hb = load("players.sample.json")
        for p in hb["players"].values():
            for weapon_id, w in (p["weapons"] or {}).items():
                self.assertIn(weapon_id, names)
                self.assertIn(w["skin"], names)


if __name__ == "__main__":
    unittest.main()
