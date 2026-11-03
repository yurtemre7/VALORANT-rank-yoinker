import unittest

from src.account_info import (
    battlepass,
    daily_store,
    index_metadata,
    own_loadout,
    party_details,
    pod_region,
    rr_history,
    wallet,
)

VP = "85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741"
RAD = "e59aa87c-4cbf-517a-5983-6e81511be9b7"
KC = "85ca954a-41f2-ce94-9b45-8ca3dd39a00d"
TOKENS = "f08d4ae3-939c-4576-ab26-09ce1f23bb37"

VANDAL, MELEE = "9c82e19d-4575-0200-1a81-3eacf00cf872", "2f59173c-4bed-b6c3-2191-dea9b58be9c7"
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
    "currencies": [
        {"uuid": VP, "displayName": "VALORANT POINTS", "displayIcon": "vp.png"},
        {"uuid": RAD, "displayName": "RADIANITE Points", "displayIcon": "rad.png"},
        {"uuid": KC, "displayName": "Kingdom Credits", "displayIcon": "kc.png"},
        {"uuid": TOKENS, "displayName": "Agent Tokens", "displayIcon": "tokens.png"},
    ],
    "contracts": [
        {"uuid": "bp", "displayName": "Season 2026 // Act VI", "content": {"relationType": "Season", "chapters": [{"levels": [{}] * 5}] * 11}},
        {"uuid": "event", "displayName": "Champions", "content": {"relationType": "Event", "chapters": [{"levels": [{}] * 6}]}},
    ],
})


class AccountInfoTests(unittest.TestCase):
    def test_pod_region(self):
        self.assertEqual(pod_region("aresriot.aws-euc1-prod.eu-gp-frankfurt-1"), "Frankfurt")
        self.assertEqual(pod_region("aresriot.aws-sae1-prod.br-gp-sao-paulo-1"), "Sao Paulo")
        self.assertIsNone(pod_region("garbage"))
        self.assertIsNone(pod_region(None))

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

    def test_own_loadout_standard_skin_uses_weapon_icon(self):
        weapons, _ = own_loadout({"Guns": [{"ID": VANDAL, "SkinID": "skin-std", "ChromaID": ""}]}, METADATA)
        self.assertEqual(weapons[VANDAL]["skinDisplayIcon"], "vandal.png")
        self.assertNotIn("buddy_displayIcon", weapons[VANDAL])

    def test_own_loadout_empty(self):
        self.assertEqual(own_loadout(None, METADATA), ({}, {}))

    def test_party_details(self):
        raw = {
            "Members": [
                {"Subject": "me", "IsReady": True, "Pings": [
                    {"Ping": 19, "GamePodID": "aresriot.aws-euw3-prod.eu-gp-paris-1"},
                    {"Ping": 14, "GamePodID": "aresriot.aws-euc1-prod.eu-gp-frankfurt-1"},
                    {"Ping": 0, "GamePodID": "aresriot.aws-x-prod.eu-gp-nowhere-1"},
                ]},
                {"Subject": "mate", "IsReady": False, "Pings": []},
            ],
            "EligibleQueues": ["unrated", "competitive"],
            "QueueIneligibilities": ["SKILL_DISPARITY"],
            "MatchmakingData": {"QueueID": "competitive", "SkillDisparityRRPenalty": 10},
        }
        self.assertEqual(party_details(raw), {
            "members": {
                "me": {"isReady": True, "ping": {"region": "Frankfurt", "ms": 14}},
                "mate": {"isReady": False, "ping": None},
            },
            "eligibleQueues": ["unrated", "competitive"],
            "ineligibilities": ["SKILL_DISPARITY"],
            "rrPenalty": 10,
        })
        self.assertEqual(party_details({"errorCode": "RESOURCE_NOT_FOUND"}), {})
        self.assertEqual(party_details(None), {})

    def test_wallet_order_and_zero_tokens(self):
        raw = {"Balances": {TOKENS: 0, KC: 4200, RAD: 35, VP: 120}}
        self.assertEqual(wallet(raw, METADATA), [
            {"id": VP, "name": "VALORANT POINTS", "amount": 120, "icon": "vp.png"},
            {"id": RAD, "name": "RADIANITE Points", "amount": 35, "icon": "rad.png"},
            {"id": KC, "name": "Kingdom Credits", "amount": 4200, "icon": "kc.png"},
        ])
        self.assertEqual(wallet({"Balances": {TOKENS: 3}}, METADATA)[0]["amount"], 3)
        self.assertEqual(wallet(None, METADATA), [])

    def test_daily_store(self):
        raw = {"SkinsPanelLayout": {
            "SingleItemOffersRemainingDurationInSeconds": 3600,
            "SingleItemStoreOffers": [
                {"Cost": {VP: 1775}, "Rewards": [{"ItemID": "lvl-rgx-1"}]},
                {"Cost": {VP: 875}, "Rewards": [{"ItemID": "unknown-level"}]},
            ],
        }}
        self.assertEqual(daily_store(raw, METADATA, now=1000), {
            "offers": [{"skin": "skin-rgx", "name": "RGX 11z Pro Vandal", "icon": "rgx-l1.png", "cost": 1775}],
            "resetsAt": 4600,
        })
        self.assertEqual(daily_store(None, METADATA, now=1000), {})

    def test_battlepass(self):
        raw = {"Contracts": [
            {"ContractDefinitionID": "event", "ProgressionLevelReached": 6},
            {"ContractDefinitionID": "bp", "ProgressionLevelReached": 33},
        ]}
        self.assertEqual(battlepass(raw, METADATA), {"name": "Season 2026 // Act VI", "level": 33, "maxLevel": 55})
        self.assertIsNone(battlepass({"Contracts": [{"ContractDefinitionID": "event"}]}, METADATA))
        self.assertIsNone(battlepass(None, METADATA))

    def test_rr_history(self):
        matches = [
            {"MapID": "/Game/Maps/Ascent/Ascent", "RankedRatingEarned": 18, "TierAfterUpdate": 15, "RankedRatingAfterUpdate": 40, "MatchStartTime": 2000},
            {"MapID": "/Game/Maps/Duality/Duality", "RankedRatingEarned": -15, "TierAfterUpdate": 15, "RankedRatingAfterUpdate": 22, "MatchStartTime": 1000},
        ] + [{"MapID": "", "RankedRatingEarned": 1, "TierAfterUpdate": 1, "RankedRatingAfterUpdate": 1, "MatchStartTime": t} for t in range(5)]
        maps = {"/game/maps/ascent/ascent": "Ascent", "/game/maps/duality/duality": "Bind"}
        history = rr_history({"Matches": matches}, maps)
        self.assertEqual(len(history), 5)
        self.assertEqual(history[0], {"map": "Ascent", "earned": 18, "tierAfter": 15, "rrAfter": 40, "startTime": 2000, "placement": False})
        placement = rr_history({"Matches": [{"MapID": "", "RankedRatingEarned": 0, "IsPlacementMatch": True, "MatchStartTime": 1}]}, maps)
        self.assertTrue(placement[0]["placement"])
        self.assertEqual(history[1]["map"], "Bind")
        self.assertEqual(rr_history(None, maps), [])


if __name__ == "__main__":
    unittest.main()
