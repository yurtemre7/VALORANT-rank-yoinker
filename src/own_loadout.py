"""Your own equipped loadout for the players page lobby view.

Riot only shares other players' loadouts once agent select starts, but your own is
readable any time: one GET per lobby entry (not polled) through Requests.fetch.
"""

METADATA_URLS = {
    "weapons": "https://valorant-api.com/v1/weapons",
    "buddies": "https://valorant-api.com/v1/buddies",
    "sprays": "https://valorant-api.com/v1/sprays",
    "flex": "https://valorant-api.com/v1/flex",
}


def _key(value):
    return str(value or "").lower()


def _by_uuid(items):
    return {_key(item.get("uuid")): item for item in items or [] if isinstance(item, dict) and item.get("uuid")}


def index_metadata(lists):
    """Index the valorant-api lists in METADATA_URLS by uuid (plus buddy levels)."""
    index = {name: _by_uuid(lists.get(name)) for name in METADATA_URLS}
    index["buddy_levels"] = {
        _key(level.get("uuid")): buddy
        for buddy in index["buddies"].values()
        for level in buddy.get("levels") or []
        if level.get("uuid")
    }
    return index


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
    """playerloadout v3 -> (weapons, sprays) in the same shape as the in-match players page data."""
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


def fetch_own_loadout(requests, puuid, meta):
    """Your equipped loadout as (weapons, sprays), or None if Riot does not answer."""
    if not puuid:
        return None
    try:
        response = requests.fetch("pd", f"/personalization/v3/players/{puuid}/playerloadout", "get")
        if not getattr(response, "ok", False):
            return None
        return own_loadout(response.json(), meta)
    except Exception:
        return None


def apply_own_loadout(players, puuid, loadout):
    """Add your loadout to your own entry of the heartbeat players (lobby only)."""
    if loadout and puuid in players:
        players[puuid]["weapons"], players[puuid]["sprays"] = loadout
