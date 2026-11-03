"""Parsers for your own account and party data shown in the players page lobby.

Pure functions (no I/O). Inputs are Riot responses fetched by src/account_service.py and
valorant-api metadata lists; see plans/2026-11-03-lobby-account-design.md for the endpoints.
"""

import re

VP = "85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741"
RADIANITE = "e59aa87c-4cbf-517a-5983-6e81511be9b7"
KINGDOM_CREDITS = "85ca954a-41f2-ce94-9b45-8ca3dd39a00d"
AGENT_TOKENS = "f08d4ae3-939c-4576-ab26-09ce1f23bb37"
CURRENCY_ORDER = [VP, RADIANITE, KINGDOM_CREDITS]
RR_HISTORY_SIZE = 5

_POD_REGION = re.compile(r"-gp-([a-z-]+?)-\d+$")


def _key(value):
    return str(value or "").lower()


def _by_uuid(items):
    return {_key(item.get("uuid")): item for item in items or [] if isinstance(item, dict) and item.get("uuid")}


def index_metadata(lists):
    """Index valorant-api lists by uuid, plus skin-level and buddy-level lookups."""
    index = {name: _by_uuid(lists.get(name)) for name in ("weapons", "buddies", "sprays", "flex", "currencies", "contracts")}
    index["skin_levels"] = {
        _key(level.get("uuid")): (weapon, skin)
        for weapon in index["weapons"].values()
        for skin in weapon.get("skins") or []
        for level in skin.get("levels") or []
        if level.get("uuid")
    }
    index["buddy_levels"] = {
        _key(level.get("uuid")): buddy
        for buddy in index["buddies"].values()
        for level in buddy.get("levels") or []
        if level.get("uuid")
    }
    return index


def pod_region(game_pod_id):
    """'aresriot.aws-euc1-prod.eu-gp-frankfurt-1' -> 'Frankfurt'."""
    match = _POD_REGION.search(str(game_pod_id or ""))
    return match.group(1).replace("-", " ").title() if match else None


def _skin_icon(weapon, skin, chroma_id):
    # Same rules as Loadouts.convertLoadoutToJsonArray: default skins show the weapon itself.
    name = str(skin.get("displayName") or "")
    if name.startswith("Standard") or name.startswith("Melee"):
        return weapon.get("displayIcon")
    for chroma in skin.get("chromas") or []:
        if _key(chroma.get("uuid")) == _key(chroma_id) and (chroma.get("displayIcon") or chroma.get("fullRender")):
            return chroma.get("displayIcon") or chroma.get("fullRender")
    return skin.get("displayIcon") or ((skin.get("levels") or [{}])[0].get("displayIcon"))


def own_loadout(raw, meta):
    """Your equipped loadout (playerloadout v3) in the players page shape: (weapons, sprays)."""
    weapons, sprays = {}, {}
    for gun in (raw or {}).get("Guns") or []:
        weapon = meta["weapons"].get(_key(gun.get("ID")))
        if not weapon:
            continue
        skin = next((s for s in weapon.get("skins") or [] if _key(s.get("uuid")) == _key(gun.get("SkinID"))), None)
        entry = {"weapon": weapon.get("displayName"), "skin": _key(gun.get("SkinID"))}
        if skin:
            entry["skinDisplayName"] = skin.get("displayName")
            entry["skinDisplayIcon"] = _skin_icon(weapon, skin, gun.get("ChromaID"))
        buddy = meta["buddies"].get(_key(gun.get("CharmID"))) or meta["buddy_levels"].get(_key(gun.get("CharmLevelID")))
        if buddy and buddy.get("displayIcon"):
            entry["buddy_displayIcon"] = buddy.get("displayIcon")
        weapons[_key(gun.get("ID"))] = entry
    for expression in (raw or {}).get("ActiveExpressions") or []:
        asset = _key(expression.get("AssetID"))
        for kind, table in (("spray", meta["sprays"]), ("flex", meta["flex"])):
            if asset in table:
                item = table[asset]
                sprays[str(len(sprays))] = {"type": kind, "displayName": item.get("displayName"), "displayIcon": item.get("displayIcon")}
                break
    return weapons, sprays


def party_details(raw):
    """Ready state and best server ping per member, queue eligibility of the party."""
    if not isinstance(raw, dict) or "Members" not in raw:
        return {}
    members = {}
    for member in raw.get("Members") or []:
        pings = [p for p in member.get("Pings") or [] if (p.get("Ping") or 0) > 0 and pod_region(p.get("GamePodID"))]
        best = min(pings, key=lambda p: p["Ping"]) if pings else None
        members[member.get("Subject")] = {
            "isReady": bool(member.get("IsReady")),
            "ping": {"region": pod_region(best["GamePodID"]), "ms": best["Ping"]} if best else None,
        }
    return {
        "members": members,
        "eligibleQueues": list(raw.get("EligibleQueues") or []),
        "ineligibilities": list(raw.get("QueueIneligibilities") or []),
        "rrPenalty": (raw.get("MatchmakingData") or {}).get("SkillDisparityRRPenalty") or 0,
    }


def wallet(raw, meta):
    """Balances ordered VP, Radianite, Kingdom Credits, then others; empty Agent Tokens hidden."""
    balances = {_key(k): v for k, v in ((raw or {}).get("Balances") or {}).items()}
    ordered = [c for c in CURRENCY_ORDER if c in balances] + sorted(c for c in balances if c not in CURRENCY_ORDER)
    result = []
    for currency in ordered:
        if currency == AGENT_TOKENS and not balances[currency]:
            continue
        info = meta["currencies"].get(currency, {})
        result.append({"id": currency, "name": info.get("displayName"), "amount": balances[currency], "icon": info.get("displayIcon")})
    return result


def daily_store(raw, meta, now):
    """Today's skin offers (name, icon, VP cost) and when they rotate (epoch seconds)."""
    panel = (raw or {}).get("SkinsPanelLayout")
    if not panel:
        return {}
    offers = []
    for offer in panel.get("SingleItemStoreOffers") or []:
        level_id = _key(((offer.get("Rewards") or [{}])[0]).get("ItemID"))
        found = meta["skin_levels"].get(level_id)
        if not found:
            continue
        weapon, skin = found
        level = next((l for l in skin.get("levels") or [] if _key(l.get("uuid")) == level_id), {})
        offers.append({
            "skin": _key(skin.get("uuid")),
            "name": skin.get("displayName"),
            "icon": level.get("displayIcon") or skin.get("displayIcon") or weapon.get("displayIcon"),
            "cost": (offer.get("Cost") or {}).get(VP),
        })
    return {"offers": offers, "resetsAt": int(now + (panel.get("SingleItemOffersRemainingDurationInSeconds") or 0))}


def battlepass(raw, meta):
    """The current act's battle pass: the contract whose definition is a 'Season' contract."""
    for contract in (raw or {}).get("Contracts") or []:
        definition = meta["contracts"].get(_key(contract.get("ContractDefinitionID")))
        content = (definition or {}).get("content") or {}
        if content.get("relationType") == "Season":
            return {
                "name": definition.get("displayName"),
                "level": contract.get("ProgressionLevelReached") or 0,
                "maxLevel": sum(len(ch.get("levels") or []) for ch in content.get("chapters") or []),
            }
    return None


def rr_history(raw, map_names):
    """Last competitive matches, newest first: map, RR earned, rank and RR afterwards."""
    matches = sorted((raw or {}).get("Matches") or [], key=lambda m: m.get("MatchStartTime") or 0, reverse=True)
    return [
        {
            "map": map_names.get(_key(m.get("MapID"))),
            "earned": m.get("RankedRatingEarned"),
            "tierAfter": m.get("TierAfterUpdate"),
            "rrAfter": m.get("RankedRatingAfterUpdate"),
            "startTime": m.get("MatchStartTime"),
        }
        for m in matches[:RR_HISTORY_SIZE]
    ]
