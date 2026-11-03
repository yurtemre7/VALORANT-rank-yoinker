import unittest

from src.account_service import AccountService
from tests.test_account_info import METADATA, VANDAL, VP

ME = "me-puuid"


class FakeResponse:
    def __init__(self, status, data):
        self.status_code, self._data, self.ok = status, data, status == 200

    def json(self):
        return self._data


class FakeRequests:
    """Answers by endpoint prefix; records every call."""

    def __init__(self):
        self.calls = []
        self.pd = {
            f"/personalization/v3/players/{ME}/playerloadout": (200, {"Guns": [{"ID": VANDAL, "SkinID": "skin-rgx", "ChromaID": "chroma-red"}]}),
            f"/store/v1/wallet/{ME}": (200, {"Balances": {VP: 120}}),
            f"/store/v3/storefront/{ME}": (200, {"SkinsPanelLayout": {"SingleItemOffersRemainingDurationInSeconds": 100,
                                                                      "SingleItemStoreOffers": [{"Cost": {VP: 1775}, "Rewards": [{"ItemID": "lvl-rgx-1"}]}]}}),
            f"/contracts/v1/contracts/{ME}": (200, {"Contracts": [{"ContractDefinitionID": "bp", "ProgressionLevelReached": 33}]}),
            f"/mmr/v1/players/{ME}/competitiveupdates": (200, {"Matches": [{"MapID": "/Game/Maps/Ascent/Ascent", "RankedRatingEarned": 18,
                                                                            "TierAfterUpdate": 15, "RankedRatingAfterUpdate": 40, "MatchStartTime": 5}]}),
        }
        self.glz = {
            f"/parties/v1/players/{ME}": {"CurrentPartyID": "party-1"},
            "/parties/v1/parties/party-1": {"Members": [{"Subject": ME, "IsReady": True, "Pings": [
                {"Ping": 14, "GamePodID": "aresriot.aws-euc1-prod.eu-gp-frankfurt-1"}]}], "EligibleQueues": ["unrated"]},
        }

    def fetch(self, url_type, endpoint, method, rate_limit_seconds=5, json_body=None):
        self.calls.append((url_type, endpoint.split("?")[0], method))
        table = self.pd if url_type == "pd" else self.glz
        for prefix, value in table.items():
            if endpoint.startswith(prefix):
                return FakeResponse(*value) if url_type == "pd" else value
        return FakeResponse(404, {}) if url_type == "pd" else {"errorCode": "RESOURCE_NOT_FOUND", "_http_status": 404}


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def make():
    requests, clock = FakeRequests(), Clock()
    service = AccountService(requests, lambda: METADATA, {"/game/maps/ascent/ascent": "Ascent"}, clock=clock)
    return service, requests, clock


class AccountServiceTests(unittest.TestCase):
    def test_lobby_assembles_every_part(self):
        service, requests, _ = make()
        result = service.lobby(ME)
        weapons, sprays = result["loadout"]
        self.assertEqual(weapons[VANDAL]["skinDisplayName"], "RGX 11z Pro Vandal")
        self.assertEqual(result["party"]["members"][ME]["ping"], {"region": "Frankfurt", "ms": 14})
        account = result["account"]
        self.assertEqual(account["wallet"][0]["amount"], 120)
        self.assertEqual(account["store"], {"offers": [{"skin": "skin-rgx", "name": "RGX 11z Pro Vandal", "icon": "rgx-l1.png", "cost": 1775}], "resetsAt": 1100})
        self.assertEqual(account["battlepass"], {"name": "Season 2026 // Act VI", "level": 33, "maxLevel": 55})
        self.assertEqual(account["rrHistory"][0]["map"], "Ascent")
        self.assertIn(("pd", f"/store/v3/storefront/{ME}", "post"), requests.calls)

    def test_ttls(self):
        service, requests, clock = make()
        service.lobby(ME)
        first = len(requests.calls)
        clock.now += 5
        service.lobby(ME)
        self.assertEqual(len(requests.calls), first, "nothing refetched within 5 s")
        clock.now += 6  # 11 s: party only (lookup + party)
        service.lobby(ME)
        self.assertEqual([c[1] for c in requests.calls[first:]], [f"/parties/v1/players/{ME}", "/parties/v1/parties/party-1"])
        clock.now += 50  # 61 s: party again + loadout
        before = len(requests.calls)
        service.lobby(ME)
        self.assertIn(("pd", f"/personalization/v3/players/{ME}/playerloadout", "get"), requests.calls[before:])
        self.assertNotIn(("pd", f"/store/v1/wallet/{ME}", "get"), requests.calls[before:])

    def test_store_refetched_after_rotation(self):
        service, requests, clock = make()
        service.lobby(ME)
        clock.now += 101  # past resetsAt (1100)
        before = len(requests.calls)
        service.lobby(ME)
        self.assertIn(("pd", f"/store/v3/storefront/{ME}", "post"), requests.calls[before:])

    def test_failure_omits_part_and_keeps_last_good(self):
        service, requests, clock = make()
        requests.pd[f"/store/v1/wallet/{ME}"] = (500, {})
        self.assertNotIn("wallet", service.lobby(ME)["account"])
        service, requests, clock = make()
        service.lobby(ME)
        requests.pd[f"/store/v1/wallet/{ME}"] = (429, {})
        clock.now += 301
        self.assertEqual(service.lobby(ME)["account"]["wallet"][0]["amount"], 120, "last good wallet kept")

    def test_failed_call_is_not_retried_immediately(self):
        service, requests, clock = make()
        requests.pd[f"/store/v1/wallet/{ME}"] = (500, {})
        service.lobby(ME)
        clock.now += 5
        before = len(requests.calls)
        service.lobby(ME)
        self.assertNotIn(("pd", f"/store/v1/wallet/{ME}", "get"), requests.calls[before:])

    def test_no_party(self):
        service, requests, _ = make()
        requests.glz[f"/parties/v1/players/{ME}"] = {"errorCode": "RESOURCE_NOT_FOUND", "_http_status": 404}
        self.assertIsNone(service.lobby(ME)["party"])

    def test_exceptions_never_escape(self):
        service, requests, _ = make()

        def boom(*args, **kwargs):
            raise RuntimeError("network down")

        requests.fetch = boom
        self.assertEqual(service.lobby(ME), {"loadout": None, "party": None, "account": {}})

    def test_no_puuid_makes_no_calls(self):
        service, requests, _ = make()
        self.assertEqual(service.lobby(None), {"loadout": None, "party": None, "account": {}})
        self.assertEqual(requests.calls, [])


if __name__ == "__main__":
    unittest.main()
