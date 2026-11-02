def sort_players_by_level_and_party(players, party_obj):
    """Sort players by level (desc) while keeping premades adjacent."""
    party_of = {
        subject: party_id
        for party_id, subjects in party_obj.items()
        for subject in subjects
    }

    def level(p):
        return p["PlayerIdentity"].get("AccountLevel") or 0

    party_top = {}
    for p in players:
        pid = party_of.get(p["Subject"])
        if pid is not None:
            party_top[pid] = max(party_top.get(pid, 0), level(p))

    def key(p):
        pid = party_of.get(p["Subject"])
        top = party_top[pid] if pid is not None else level(p)
        return (-top, str(pid or ""), -level(p))

    players.sort(key=key)
