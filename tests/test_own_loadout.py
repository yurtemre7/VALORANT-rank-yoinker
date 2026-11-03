import unittest

from src.own_loadout import apply_own_loadout, fetch_own_loadout, index_metadata, own_loadout

VANDAL, MELEE = "9c82e19d-4575-0200-1a81-3eacf00cf872", "2f59173c-4bed-b6c3-2191-dea9b58be9c7"
ME = "me-puuid"
METADATA = index_metadata({
    "weapons": [
        {"uuid": VANDAL.upper(), "displayName": "Vandal", "displayIcon": "vandal.png", "skins": [
            {"uuid": "skin-rgx", "displayName": "RGX 11z Pro Vandal", "displayIcon": None,
             "chromas": [{"uuid": "chroma-red", "displayIcon": "rgx-red.png"}], "levels": [{"uuid": "lvl-rgx-1", "displayIcon": "rgx-l1.png"}]},
            {"uuid": "skin-std", "displayName": "Standard Vandal", "displayIcon": None, "chromas": [], "levels": [{"uuid": "lvl-std", "displayIcon": None}]},
        ]},
        {"uuid": MELEE, "displayName": "Melee", "displayIcon": "melee.png", "skins": [
            {"uuid": "skin-melee", "displayName": "Melee", "displayIcon": None, "chromas": [], "levels": [{"uuid": "lvl-melee", "displayIcon": None}]},
        ]},
    ],
    "buddies": [{"uuid": "buddy-1", "displayIcon": "buddy.png", "levels": [{"uuid": "buddy-1-lvl"}]}],
    "sprays": [{"uuid": "spray-1", "displayName": "Cans On", "displayIcon": "spray.png"}],
    "flex": [{"uuid": "flex-1", "displayName": "Megaphone", "displayIcon": "flex.png"}],
})


class FakeResponse:
    def __init__(self, status, data):
        self.status_code, self._data, self.ok = status, data, status == 200

    def json(self):
        return self._data


class FakeRequests:
    def __init__(self, response):
        self.response, self.calls = response, []

    def fetch(self, url_type, endpoint, method, rate_limit_seconds=5, json_body=None):
        self.calls.append((url_type, endpoint, method))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class OwnLoadoutTests(unittest.TestCase):
    def test_own_loadout(self):
        raw = {
            "Guns": [
                {"ID": VANDAL, "SkinID": "skin-rgx", "SkinLevelID": "lvl-rgx-1", "ChromaID": "chroma-red", "CharmID": "buddy-1", "CharmLevelID": "buddy-1-lvl"},
                {"ID": MELEE, "SkinID": "skin-melee", "SkinLevelID": "lvl-melee", "ChromaID": ""},
                {"ID": "unknown-weapon", "SkinID": "x"},
            ],
            "ActiveExpressions": [{"AssetID": "spray-1"}, {"AssetID": "flex-1"}, {"AssetID": "nothing"}],
        }
        weapons, sprays = own_loadout(raw, METADATA)
        self.assertEqual(weapons, {
            VANDAL: {"weapon": "Vandal", "skin": "skin-rgx", "skinDisplayName": "RGX 11z Pro Vandal",
                     "skinDisplayIcon": "rgx-red.png", "buddy_displayIcon": "buddy.png"},
            MELEE: {"weapon": "Melee", "skin": "skin-melee", "skinDisplayName": "Melee", "skinDisplayIcon": "melee.png"},
        })
        self.assertEqual(sprays, {
            "0": {"type": "spray", "displayName": "Cans On", "displayIcon": "spray.png"},
            "1": {"type": "flex", "displayName": "Megaphone", "displayIcon": "flex.png"},
        })

    def test_standard_skin_uses_weapon_icon_and_no_buddy(self):
        weapons, _ = own_loadout({"Guns": [{"ID": VANDAL, "SkinID": "skin-std", "ChromaID": ""}]}, METADATA)
        self.assertEqual(weapons[VANDAL]["skinDisplayIcon"], "vandal.png")
        self.assertNotIn("buddy_displayIcon", weapons[VANDAL])

    def test_empty_input(self):
        self.assertEqual(own_loadout(None, METADATA), ({}, {}))
        self.assertEqual(own_loadout({"Guns": None, "ActiveExpressions": None}, METADATA), ({}, {}))

    def test_fetch_uses_v3_endpoint_once(self):
        requests = FakeRequests(FakeResponse(200, {"Guns": [{"ID": VANDAL, "SkinID": "skin-rgx", "ChromaID": ""}]}))
        weapons, sprays = fetch_own_loadout(requests, ME, METADATA)
        self.assertEqual(weapons[VANDAL]["skinDisplayName"], "RGX 11z Pro Vandal")
        self.assertEqual(requests.calls, [("pd", f"/personalization/v3/players/{ME}/playerloadout", "get")])

    def test_fetch_failure_returns_none(self):
        self.assertIsNone(fetch_own_loadout(FakeRequests(FakeResponse(404, {})), ME, METADATA))
        self.assertIsNone(fetch_own_loadout(FakeRequests(RuntimeError("network down")), ME, METADATA))
        self.assertIsNone(fetch_own_loadout(FakeRequests(FakeResponse(200, {})), None, METADATA))

    def test_apply_adds_loadout_to_own_entry_only(self):
        players = {ME: {"name": "me"}, "mate": {"name": "mate"}}
        apply_own_loadout(players, ME, ({"w": {"weapon": "Vandal"}}, {"0": {"type": "spray"}}))
        self.assertEqual(players[ME]["weapons"], {"w": {"weapon": "Vandal"}})
        self.assertEqual(players[ME]["sprays"], {"0": {"type": "spray"}})
        self.assertNotIn("weapons", players["mate"])

    def test_apply_ignores_missing_data_or_player(self):
        players = {ME: {"name": "me"}}
        apply_own_loadout(players, ME, None)
        apply_own_loadout(players, "someone-else", ({"w": {}}, {}))
        self.assertEqual(players, {ME: {"name": "me"}})


if __name__ == "__main__":
    unittest.main()
