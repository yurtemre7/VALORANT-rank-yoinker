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

### 2026-11-03 - players UI (spec/plan in `plans/2026-11-03-players-ui*.md`)
| File | Change | Why |
|---|---|---|
| `src/server.py` `Server.start_docs_server` | Extra log line `players UI at http://127.0.0.1:{docs_port}/players.html?port={ws_port}` | Find the new page |
| `docs/players.html`, `docs/players.js` (new) | Plain-JS page: player cards (rank/peak/RR/level/K/D/HS/WR, party badge, self highlight) and a loadout modal (skins, buddies, sprays). Reads only the existing `heartbeat` websocket payload; strings go in via `textContent` only | Rich player view like upstream PR #171, minimal code |
| `docs/vendor/tailwind.js` (new) | Vendored `@tailwindcss/browser@4.3.4` (sha256 `e54f393a…dcb012aa`) | Tailwind without CDN at runtime |
| `docs/players.sample.json`, `docs/players.lobby.sample.json` (new) | Demo payloads for `players.html?demo` (in match) and `?demo=lobby` (MENUS) | Test without VALORANT |
| `tests/test_players_page.py` (new), `tests/test_tracker_server.py` | Fixture shape, page wiring, no `innerHTML` templates, rank names; docs server serves `players.html` and logs its URL | Regression cover |

- Lobby: the MENUS heartbeat has party members' name/rank/level/stats only. Riot exposes other players' equipped loadouts only per match (from agent select), so friends' skins appear in PREGAME/INGAME, not in the lobby.
- Re-port: self-contained in `docs/players.*` + `docs/vendor/`; depends only on the `heartbeat` field names in `main.py`, plus the one log line.

### 2026-11-03 - players UI: English/Turkish toggle
| File | Change | Why |
|---|---|---|
| `docs/players.i18n.json` (new) | `en`/`tr` strings: UI text, game states, game modes (keys = `gamemodes` values in `src/constants.py`), 28 rank names (Riot's official Turkish) | Translations in one place |
| `docs/players.html` | `EN`/`TR` buttons (`data-lang`), `data-i18n` on static labels | Language toggle |
| `docs/players.js` | `setLang` saves to `localStorage["vry.lang"]` (default `en`), sets `<html lang>`, re-renders. In Turkish, weapon and skin names come from `valorant-api.com/v1/weapons?language=tr-TR` (browser fetch once per page load, matched by weapon uuid / `skin` uuid in the payload), English fallback if it fails | Turkish weapon/skin names |
| `docs/players.sample.json` | Weapons carry their `skin` uuid like the real payload | Demo Turkish skin names |
| `tests/test_players_page.py` | en/tr key parity, 28 ranks, every `gamemodes` value translated, toggle wiring, skin uuids in fixture | Regression cover |

- Not translated: agent names (same in Turkish), player titles (English from the payload), K/D and HS.
- If a new mode is added to `gamemodes` in `src/constants.py`, add it to both `modes` maps; `test_i18n_covers_every_game_mode` fails until then.

### 2026-11-03 - players dashboard link in console
| File | Change | Why |
|---|---|---|
| `src/server.py` `Server.start_docs_server` | Sets `os.environ["VRY_PLAYERS_URL"]` to the players URL (same value as the log line) | Hand the URL to the console |
| `main.py` `print_info` | After "Player Inventories", prints `Players Dashboard - View in browser` as an OSC-8 link to `VRY_PLAYERS_URL`, only when it is set (docs server running) | Show the new page at startup |
| `tests/test_tracker_server.py` | Asserts `VRY_PLAYERS_URL` is set | Regression cover |
- Demo fixture: the HTML-injection test name was replaced with `Çağrı#TR1`; injection safety is enforced by `test_page_wiring` (no `innerHTML` templates, strings via `textContent`).

### 2026-11-03 - HOW-TO-RUN.md
- `HOW-TO-RUN.md` (new): minimal setup/run/demo/troubleshooting/update steps for running from source with uv. Docs only.

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
