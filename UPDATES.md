# UPDATES

Running log of local changes on branch `local-tweaks` vs fork `main`. Append every future change here (newest last).

## Origin
- Fork: latenitekode's VALORANT rank yoinker (third-party). Audited 2026-11-03: no malicious code found.
- Caveats: it opens a websocket on `0.0.0.0:1100` (`src/websocket.py`), uses `verify=False` for Riot calls, and the updater / `status.json` check trust the fork author. Run from source only; never use their exe or updater.
- The same tweaks previously lived on the old repo (`C:\Users\emrey\Programming\github\VALORANT-rank-yoinker`, branch `local-tweaks`, based on upstream 2.94, commit "Show hidden names/levels, premade column, server id; add uv project"). Use it as reference for future ports.

## Changelog

### 2026-11-03 - uv project + default config (commit f63df38)
| File | Change | Why |
|---|---|---|
| `pyproject.toml`, `uv.lock` | New uv project `vry`, Python >=3.14, deps from `requirements.txt` + `cx_Freeze`, `pyperclip` | Run from source with `uv run` |
| `src/constants.py` | `hide_names = False`, `hide_levels = False` | Show names and levels |
| `src/constants.py` `DEFAULT_CONFIG` | `table.earned_rr` False; flags `peak_rank_act` False, `server_id` True, `short_ranks` True, `truncate_skins` False, `truncate_names` False | Preferred defaults |
| `src/table.py` `Table.__init__` `col_flags` | Party column `False` -> `True` | Show premade column |

### 2026-11-03 - behaviour tweaks (commit 1431f08)
| File | Change | Why |
|---|---|---|
| `src/party_sort.py` (new) | `sort_players_by_level_and_party(players, party_obj)`: level desc, premades kept adjacent, party ranked by its top member's level | Plain level sort split premades |
| `main.py` | Imports helper; replaces the three `Players.sort(... AccountLevel ..., reverse=True)` calls (coregame and pregame branches pass `partyOBJ`; menu/lobby branch passes `{}`). Following `TeamID` sort untouched | Use new sort |
| `main.py` (top, after urllib3 warning setup) | Reconfigure `sys.stdout`/`sys.stderr` to UTF-8 with `errors="replace"` | Delta header raised `UnicodeEncodeError` on cp1252 pipes |
| `src/colors.py` `Colors.get_color_from_team` | After `orig_name = name`: if `agent` given and name is empty/`#`, name becomes `"<Agent> (hidden)"` via `agent_dict` | Streamer-mode names come back blank |
| `tests/test_local_tweaks.py` (new) | Tests for the sort and the hidden-name fallback | Regression cover |

### 2026-11-03 - tracking docs
- `UPDATES.md`, `AGENT.md` added. Docs only.

## How to re-port onto a newer upstream/fork
Each patch is independent. Find the symbol, re-apply, run the tests.

1. **uv project**: `uv init --bare --no-workspace --python 3.14 --name vry`, then `uv add -r requirements.txt cx_Freeze pyperclip`. Fall back to 3.13 only if a pinned dep fails on 3.14.
2. **Show names/levels**: `src/constants.py` module vars `hide_names`, `hide_levels` -> `False`.
3. **Config defaults**: `src/constants.py` `DEFAULT_CONFIG` values listed in the first changelog entry. Note `config.json` is gitignored and local, so an existing one overrides these defaults; edit it or delete it to pick up new defaults.
4. **Party column**: `src/table.py` `Table.__init__`, first entry of `self.col_flags` (`# Party`) -> `True`.
5. **Premade-adjacent sort**: copy `src/party_sort.py`; in `main.py` import it and replace each level sort on `Players` (coregame, pregame, menu branches) as described above. Premades only exist for your own party and allies; enemy premades cannot be detected (Riot only exposes presence for visible players).
6. **Hidden-name fallback**: `src/colors.py` `Colors.get_color_from_team`, right after `orig_name = name`. Needs `self.agent_dict` (lowercased agent id -> name). Keep the existing `hide_names` block after it.
7. **UTF-8 stdio**: `main.py`, after `urllib3.disable_warnings(...)`.
8. **Tests**: copy `tests/test_local_tweaks.py`; run `uv run python -m unittest discover -s tests -v`.
