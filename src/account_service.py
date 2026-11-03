"""Cached fetching of your own account and party data for the players page lobby.

Only the endpoints listed in plans/2026-11-03-lobby-account-design.md, all through
Requests.fetch (auth, retries, 429 back-off). Every part has its own TTL; failures
never raise, they keep the last good value (or leave the part out) and are retried
after FAILURE_RETRY seconds at the earliest.
"""

import time

from src import account_info

# valorant-api lists the parsers need (cached by Loadouts._api_get under the same keys).
METADATA_URLS = {
    "weapons": "https://valorant-api.com/v1/weapons",
    "buddies": "https://valorant-api.com/v1/buddies",
    "sprays": "https://valorant-api.com/v1/sprays",
    "flex": "https://valorant-api.com/v1/flex",
    "currencies": "https://valorant-api.com/v1/currencies",
    "contracts": "https://valorant-api.com/v1/contracts",
}
TTL = {"party": 10, "loadout": 60, "wallet": 300, "rr": 300, "contracts": 300, "store": 300}
FAILURE_RETRY = 30


class AccountService:
    def __init__(self, requests, metadata, map_names, clock=time.time, log=None):
        self.requests = requests
        self._metadata_source = metadata  # callable -> account_info.index_metadata(...)
        self._metadata = None
        self.map_names = map_names
        self.clock = clock
        self.log = log or (lambda *_: None)
        self._cache = {}  # key -> (expires_at, value)

    def _meta(self):
        if not self._metadata or not self._metadata.get("weapons"):
            self._metadata = self._metadata_source()
        return self._metadata

    def _pd(self, endpoint, method="get", body=None):
        response = self.requests.fetch("pd", endpoint, method, json_body=body)
        if not getattr(response, "ok", False):
            raise RuntimeError(f"pd {endpoint} -> {getattr(response, 'status_code', None)}")
        return response.json()

    def _glz(self, endpoint):
        data = self.requests.fetch("glz", endpoint, "get")
        if not isinstance(data, dict) or data.get("errorCode"):
            raise RuntimeError(f"glz {endpoint} -> {(data or {}).get('errorCode') if isinstance(data, dict) else data}")
        return data

    def _cached(self, key, load, ttl_for=None):
        """Value for `key`, reloading after its TTL; on failure keep the last good value."""
        now = self.clock()
        expires, value = self._cache.get(key, (0, None))
        if now < expires:
            return value
        try:
            fresh = load()
        except Exception as exc:
            self.log(f"account {key} unavailable: {exc}")
            self._cache[key] = (now + FAILURE_RETRY, value)
            return value
        ttl = ttl_for(fresh) if ttl_for else TTL[key]
        self._cache[key] = (now + ttl, fresh)
        return fresh

    def _party(self, puuid):
        party_id = self._glz(f"/parties/v1/players/{puuid}").get("CurrentPartyID")
        return account_info.party_details(self._glz(f"/parties/v1/parties/{party_id}")) if party_id else None

    def lobby(self, puuid):
        """{"loadout": (weapons, sprays)|None, "party": dict|None, "account": {...}} for the MENUS heartbeat."""
        if not puuid:
            return {"loadout": None, "party": None, "account": {}}
        try:
            meta = self._meta()
        except Exception as exc:
            self.log(f"account metadata unavailable: {exc}")
            return {"loadout": None, "party": None, "account": {}}
        now = self.clock()
        loadout = self._cached("loadout", lambda: account_info.own_loadout(
            self._pd(f"/personalization/v3/players/{puuid}/playerloadout"), meta))
        party = self._cached("party", lambda: self._party(puuid))
        account = {
            "wallet": self._cached("wallet", lambda: account_info.wallet(self._pd(f"/store/v1/wallet/{puuid}"), meta)),
            "store": self._cached(
                "store",
                lambda: account_info.daily_store(self._pd(f"/store/v3/storefront/{puuid}", "post", {}), meta, now),
                # Keep today's offers until they rotate.
                ttl_for=lambda store: max(FAILURE_RETRY, store.get("resetsAt", 0) - now) if store else TTL["store"],
            ),
            "battlepass": self._cached("contracts", lambda: account_info.battlepass(self._pd(f"/contracts/v1/contracts/{puuid}"), meta)),
            "rrHistory": self._cached("rr", lambda: account_info.rr_history(self._pd(
                f"/mmr/v1/players/{puuid}/competitiveupdates?startIndex=0&endIndex=5&queue=competitive"), self.map_names)),
        }
        return {"loadout": loadout, "party": party, "account": {k: v for k, v in account.items() if v}}
