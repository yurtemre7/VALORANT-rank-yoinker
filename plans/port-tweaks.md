# Port local tweaks onto the latenitekode fork

Repo: this fork (branch `local-tweaks`). Run everything with `uv` (Python 3.14). Never run the fork's exe/updater.
The fork is third-party, audited as non-malicious; do not add network calls or touch the updater.

## Global Constraints
- Python 3.14 via uv: `uv run python ...`, tests: `uv run python -m unittest discover -s tests -v`.
- Keep edits minimal; match surrounding style; do not refactor unrelated code.
- Do not modify `requestsV.py` update/status logic.
- Commit each task separately on branch `local-tweaks`. Commit trailer: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Task 1: uv project + default config tweaks
Files: `pyproject.toml` (new), `uv.lock` (new), `.python-version` (optional), `src/constants.py`, `src/table.py`.
1. `uv init --bare --no-workspace --python 3.14 --name vry` then `uv add -r requirements.txt cx_Freeze pyperclip`. (Fallback to 3.13 only if a pinned dep fails to install on 3.14 and note it.)
2. `src/constants.py`: `hide_names = False`, `hide_levels = False`; in DEFAULT_CONFIG: table `"earned_rr": False`; flags `"peak_rank_act": False`, `"server_id": True`, `"short_ranks": True`, `"truncate_skins": False`, `"truncate_names": False`.
3. `src/table.py` line ~52: Party column flag `False` -> `True`.
4. Verify: `uv run python -c "import src.constants, src.table"` succeeds and `uv run python -m unittest discover -s tests` passes.

## Task 2: behaviour tweaks + tests
Files: `main.py`, `src/colors.py`, `tests/test_local_tweaks.py` (new).
1. `src/colors.py` `Colors.get_color_from_team`: right after `orig_name = name`, if `agent is not None and name.strip("#") == ""` then `name = orig_name = self.agent_dict.get(agent.lower(), "Player") + " (hidden)"` (comment: streamer mode returns an empty name). Keep the existing hide_names block after it.
2. `main.py`: add module-level helper `sort_players_by_level_and_party(players, party_obj)` (before `program_exit` or equivalent top-level spot, not inside main flow). Semantics: sort by level desc (`p["PlayerIdentity"].get("AccountLevel") or 0`) but keep premades adjacent: party_of = {subject: party_id for party_id, subjects in party_obj.items() for subject in subjects}; a party's top level = max member level; key = (-(party top level if in party else own level), str(party id or ""), -own level). Replace each of the three `Players.sort(key=...AccountLevel..., reverse=True)` calls (coregame ~L647 and pregame ~L968 pass `partyOBJ`; the lobby/menu one ~L1199 passes `{}` because no partyOBJ exists there). Leave the following `Players.sort(key=TeamID...)` untouched (stable sort keeps premades adjacent within team).
3. `main.py` near the top after imports/urllib3 warning setup: reconfigure stdout and stderr to UTF-8 (`errors="replace"`) when `reconfigure` exists, so the Δ header cannot raise UnicodeEncodeError on cp1252 pipes.
4. Tests in `tests/test_local_tweaks.py` (unittest, no network): helper sort keeps a 2-player party adjacent and ordered by party top level, solos by level; colors fallback returns text containing "(hidden)" for name "#" and "" with an agent id present in agent_dict, and leaves real names alone. If importing `main` is impractical (it runs the program), move the helper into `src/live_backbone.py`-independent new module `src/party_sort.py` and import it from main; test that module. Prefer this module approach.
5. Run full test suite; all pass.

## Task 3: tracking docs
Files: `AGENT.md`, `UPDATES.md` (new, repo root).
- `UPDATES.md`: dated changelog of every change in this branch vs fork `main` (file, what, why), plus a "How to re-port onto a newer upstream/fork" section listing each tweak as an independent patch with the exact touch points (symbols, not line numbers). Include the origin story: fork audited 2026-11-03, no malicious code found, caveats (open websocket 0.0.0.0:1100, `verify=False`, updater/status.json trust the fork author; run from source, never use their exe/updater).
- `AGENT.md`: instructions for another AI continuing work: repo purpose, how to run (`uv run python main.py`, needs VALORANT open; pipe with PYTHONUTF8=1), tests command, architecture map (main.py loop, requestsV.py, colors.py, table.py, presences/menu party detection, live_backbone), known limits (enemy premades not detectable: Riot only exposes presence for visible players; streamer-mode names blank server-side), local-only config notes, rule to append every future change to UPDATES.md, branch `local-tweaks`, do-not-touch list (updater, status check).
