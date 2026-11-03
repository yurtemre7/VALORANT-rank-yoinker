# AGENT.md

Guide for an AI agent continuing work in this repo.

## Purpose
Local, personal fork of the VALORANT rank yoinker (latenitekode fork): a console tool that reads the local Riot client and shows ranks, levels, skins and parties for everyone in a match. The fork is third-party and was audited 2026-11-03 (see `UPDATES.md`). Work on branch `local-tweaks`.

## Run and test
- Run (needs VALORANT open; do not run it unattended): `PYTHONUTF8=1 uv run python main.py` (set `PYTHONUTF8=1` when piping output).
- Tests (no network): `uv run python -m unittest discover -s tests -v`
- Python 3.14 via uv. Never run the fork's exe or updater.

## Architecture map
- `main.py`: startup, then the main loop that switches on game state (menus / pregame / coregame), builds the player list and renders the table. Uses `sort_players_by_level_and_party` from `src/party_sort.py`.
- `src/requestsV.py`: Riot local and remote API calls, also contains the update/status check (do not touch).
- `src/live_backbone.py`: `LiveBackbone`, validates game-state transitions using presence and GLZ membership; sticky during network errors.
- `src/presences.py`: reads and decodes local presence (game state, private presence).
- `src/states/menu.py`, `pregame.py`, `coregame.py`: per-state API access; party detection is in `menu.py` (`get_party_members`, `get_party_json`).
- `src/colors.py`: name/team colouring, including the hidden-name fallback.
- `src/table.py`: rich table and column flags (`col_flags`).
- `src/constants.py`: `DEFAULT_CONFIG`, `hide_names`, `hide_levels`, version.
- `src/party_sort.py`: local premade-aware sort. `tests/test_local_tweaks.py` covers it.

## Known limits
- Enemy premades cannot be detected: Riot only exposes presence for visible players.
- Streamer-mode names come back blank from Riot's name service; the fallback is `<Agent> (hidden)`.

## Config
- `config.json` is gitignored and local; it overrides defaults. Defaults live in `DEFAULT_CONFIG` in `src/constants.py`.

## Rules
- Append every future change to `UPDATES.md` (dated entry: file, what, why, plus re-port notes).
- Keep edits minimal and match surrounding style; commit on `local-tweaks`.
- New Riot calls are allowed only if they (1) use community-documented endpoints (valapidocs) through `Requests.fetch` with the auth vRY already has, no scraping or workarounds; (2) read only your own account/party data or data the game client itself shows you; (3) never reveal hidden information (streamer-mode names, hidden enemy data) or automate gameplay (no instalock); (4) are cached and on demand, never tight polling. Add each new endpoint to `UPDATES.md`.
- Never merge `local-tweaks` into `main` and never open PRs upstream. Remotes: `fork` = the user's own fork `yurtemre7/VALORANT-rank-yoinker` (`local-tweaks` tracks `fork/local-tweaks`; push there only when asked), `origin` = latenitekode, `upstream` = zayKenyon (fetch only, never push).
- Do not touch: the updater (`updatescript.bat`, update logic in `src/requestsV.py`), the `status.json` check, or the websocket server on `0.0.0.0:1100` beyond what is asked.
