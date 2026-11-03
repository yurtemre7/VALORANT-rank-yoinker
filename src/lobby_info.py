"""Lobby details for the players page, read from the local presence vRY already fetches.

Pure helpers (no network): the presence rows come from /chat/v4/presences, which
main.py loads anyway for party detection.
"""

import calendar
import time

from src.presences import Presences

CARD_ART_URL = "https://media.valorant-api.com/playercards/{}/largeart.png"
# Riot sends "0001.01.01-00.00.00" when the party is not queued.
QUEUE_TIME_FORMAT = "%Y.%m.%d-%H.%M.%S"
STATE_ORDER = {"INGAME": 0, "PREGAME": 1, "MENUS": 2}


def card_art(card_id):
    return CARD_ART_URL.format(card_id) if card_id else None


def queue_entry_epoch(value):
    """Riot's UTC queue entry time as epoch seconds, or None when not queued."""
    try:
        epoch = calendar.timegm(time.strptime(str(value), QUEUE_TIME_FORMAT))
    except (ValueError, OverflowError):
        return None
    return epoch if epoch > 0 else None


def private_by_puuid(rows):
    """Decoded private presence of every VALORANT row, keyed by puuid."""
    result = {}
    for presence in rows or []:
        if str(presence.get("product") or "").lower() != "valorant":
            continue
        decoded = Presences._decode_private_value(presence.get("private"))
        if isinstance(decoded, dict) and decoded.get("isValid") and presence.get("puuid"):
            result[presence["puuid"]] = decoded
    return result


def _party(private):
    return (private or {}).get("partyPresenceData") or {}


def _player(private):
    return (private or {}).get("playerPresenceData") or {}


def _match(private):
    return (private or {}).get("matchPresenceData") or {}


def _loop_state(private):
    return _match(private).get("sessionLoopState") or (private or {}).get("sessionLoopState")


def party_status(private):
    """Queue/party line for the lobby, from your own private presence."""
    if not private:
        return {}
    party = _party(private)
    return {
        "state": party.get("partyState"),
        "queueId": _match(private).get("queueId") or private.get("queueId"),
        "queueEntry": queue_entry_epoch(party.get("queueEntryTime")),
        "accessibility": party.get("partyAccessibility"),
        "size": party.get("partySize"),
        "maxSize": party.get("maxPartySize"),
    }


def member_extras(private, title_names):
    """Card art, title, party leader and AFK flags for one party member."""
    player = _player(private)
    return {
        "playerCard": card_art(player.get("playerCardId")),
        "title": title_names.get(str(player.get("playerTitleId") or "").lower()) or None,
        "isOwner": bool(_party(private).get("isPartyOwner")),
        "isIdle": bool((private or {}).get("isIdle")),
    }


def friends_activity(rows, self_puuid, exclude, map_names, mode_names):
    """Online VALORANT friends outside your party: what they are doing right now."""
    names = {row.get("puuid"): f"{row.get('game_name', '')}#{row.get('game_tag', '')}" for row in rows or []}
    friends = []
    for puuid, private in private_by_puuid(rows).items():
        if puuid == self_puuid or puuid in exclude:
            continue
        state = _loop_state(private)
        match, party, player = _match(private), _party(private), _player(private)
        queue_id = match.get("queueId") or private.get("queueId")
        if match.get("provisioningFlow") == "CustomGame":
            mode = "Custom Game"
        else:
            mode = mode_names.get(queue_id, queue_id or None)
        in_match = state == "INGAME"
        friends.append({
            "puuid": puuid,
            "name": names.get(puuid, "#"),
            "state": state,
            "mode": mode,
            "map": map_names.get(str(match.get("matchMap") or "").lower()) if in_match else None,
            "scoreAlly": party.get("partyOwnerMatchScoreAllyTeam") if in_match else None,
            "scoreEnemy": party.get("partyOwnerMatchScoreEnemyTeam") if in_match else None,
            "rank": player.get("competitiveTier"),
            "level": player.get("accountLevel"),
            "partySize": party.get("partySize"),
            "maxPartySize": party.get("maxPartySize"),
            "isIdle": bool(private.get("isIdle")),
            "playerCard": card_art(player.get("playerCardId")),
        })
    friends.sort(key=lambda f: (STATE_ORDER.get(f["state"], 3), f["name"].lower()))
    return friends
