import base64
import json
import unittest

from src.lobby_info import (
    card_art,
    friends_activity,
    member_extras,
    party_status,
    private_by_puuid,
    queue_entry_epoch,
)

ME, FRIEND, PARTY_MATE, LOL = "me-1", "friend-2", "mate-3", "lol-4"
CARD = "c8b2f5fd-4331-b172-f3b7-c8a26f356a1f"
MAPS = {"/game/maps/ascent/ascent": "Ascent"}
MODES = {"competitive": "Competitive", "swiftplay": "Swiftplay"}
TITLES = {"title-1": "Sharpshooter"}


def private(**overrides):
    data = {
        "isValid": True,
        "isIdle": False,
        "sessionLoopState": "MENUS",
        "queueId": "competitive",
        "matchPresenceData": {"sessionLoopState": "MENUS", "matchMap": "", "queueId": "competitive", "provisioningFlow": "Invalid"},
        "partyPresenceData": {
            "partyId": "party-a", "partySize": 2, "maxPartySize": 5, "isPartyOwner": True,
            "partyState": "DEFAULT", "partyAccessibility": "CLOSED", "queueEntryTime": "0001.01.01-00.00.00",
            "partyOwnerMatchScoreAllyTeam": 0, "partyOwnerMatchScoreEnemyTeam": 0,
        },
        "playerPresenceData": {"accountLevel": 412, "competitiveTier": 21, "playerCardId": CARD, "playerTitleId": "title-1"},
    }
    for path, value in overrides.items():
        target = data
        *parents, leaf = path.split("__")
        for key in parents:
            target = target[key]
        target[leaf] = value
    return data


def row(puuid, data, product="valorant", name="Player", tag="EUW"):
    return {
        "puuid": puuid, "product": product, "game_name": name, "game_tag": tag,
        "private": base64.b64encode(json.dumps(data).encode()).decode(),
    }


class LobbyInfoTests(unittest.TestCase):
    def test_card_art_url(self):
        self.assertEqual(card_art(CARD), f"https://media.valorant-api.com/playercards/{CARD}/largeart.png")
        self.assertIsNone(card_art(""))
        self.assertIsNone(card_art(None))

    def test_queue_entry_epoch(self):
        self.assertEqual(queue_entry_epoch("2026.11.03-15.14.49"), 1793718889)  # UTC
        self.assertIsNone(queue_entry_epoch("0001.01.01-00.00.00"))
        self.assertIsNone(queue_entry_epoch(""))
        self.assertIsNone(queue_entry_epoch("garbage"))

    def test_private_by_puuid_skips_other_products_and_invalid(self):
        rows = [row(ME, private()), row(LOL, private(), product="league_of_legends"), {"puuid": "x", "product": "valorant", "private": "%%%"}]
        self.assertEqual(list(private_by_puuid(rows)), [ME])

    def test_party_status_idle_lobby(self):
        self.assertEqual(party_status(private()), {
            "state": "DEFAULT", "queueId": "competitive", "queueEntry": None,
            "accessibility": "CLOSED", "size": 2, "maxSize": 5,
        })

    def test_party_status_in_queue(self):
        status = party_status(private(partyPresenceData__partyState="MATCHMAKING", partyPresenceData__queueEntryTime="2026.11.03-15.14.49"))
        self.assertEqual(status["state"], "MATCHMAKING")
        self.assertEqual(status["queueEntry"], 1793718889)

    def test_party_status_without_presence(self):
        self.assertEqual(party_status(None), {})

    def test_member_extras(self):
        self.assertEqual(member_extras(private(isIdle=True), TITLES), {
            "playerCard": card_art(CARD), "title": "Sharpshooter", "isOwner": True, "isIdle": True,
        })
        self.assertEqual(member_extras(None, TITLES), {"playerCard": None, "title": None, "isOwner": False, "isIdle": False})

    def test_friends_activity(self):
        in_match = private(
            sessionLoopState="INGAME",
            matchPresenceData__sessionLoopState="INGAME", matchPresenceData__matchMap="/Game/Maps/Ascent/Ascent",
            partyPresenceData__partyOwnerMatchScoreAllyTeam=9, partyPresenceData__partyOwnerMatchScoreEnemyTeam=7,
        )
        rows = [
            row(ME, private()),
            row(PARTY_MATE, private()),
            row(FRIEND, in_match, name="Kenji", tag="0001"),
            row(LOL, private(), product="league_of_legends"),
        ]
        friends = friends_activity(rows, ME, {ME, PARTY_MATE}, MAPS, MODES)
        self.assertEqual(friends, [{
            "puuid": FRIEND, "name": "Kenji#0001", "state": "INGAME", "mode": "Competitive",
            "map": "Ascent", "scoreAlly": 9, "scoreEnemy": 7, "rank": 21, "level": 412,
            "partySize": 2, "maxPartySize": 5, "isIdle": False, "playerCard": card_art(CARD),
        }])

    def test_friends_activity_lobby_has_no_map_or_score(self):
        friends = friends_activity([row(FRIEND, private())], ME, {ME}, MAPS, MODES)
        self.assertEqual((friends[0]["state"], friends[0]["map"], friends[0]["scoreAlly"]), ("MENUS", None, None))

    def test_friends_activity_custom_game_and_unknown_queue(self):
        custom = private(matchPresenceData__provisioningFlow="CustomGame")
        unknown = private(queueId="newqueue", matchPresenceData__queueId="newqueue")
        friends = friends_activity([row("a", custom, name="A"), row("b", unknown, name="B")], ME, {ME}, MAPS, MODES)
        self.assertEqual([f["mode"] for f in friends], ["Custom Game", "newqueue"])

    def test_friends_activity_sorts_in_match_first(self):
        rows = [
            row("lobby", private(), name="Zed"),
            row("match", private(sessionLoopState="INGAME", matchPresenceData__sessionLoopState="INGAME"), name="Yan"),
            row("select", private(sessionLoopState="PREGAME", matchPresenceData__sessionLoopState="PREGAME"), name="Xia"),
        ]
        names = [f["name"] for f in friends_activity(rows, ME, {ME}, MAPS, MODES)]
        self.assertEqual(names, ["Yan#EUW", "Xia#EUW", "Zed#EUW"])


if __name__ == "__main__":
    unittest.main()
