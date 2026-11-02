# Players UI — design

Date: 2026-11-03. Branch: `local-tweaks`. Inspired by upstream PR zayKenyon/VALORANT-rank-yoinker#171 (closed Vue rewrite), but plain JS + Tailwind and as little code as possible.

## Goal
A new local page, `docs/players.html`, beside the existing `docs/matchLoadouts.html` (left untouched). It shows a rich card per player in the current match; clicking a card opens a modal with that player's equipped loadout.

## Non-goals
- Owned-skin inventories (Riot only exposes other players' *equipped* loadout).
- New Riot API calls, new websocket payloads, or any Python data changes.
- A build step, npm, or a framework.
- Changing `matchLoadouts.*`.

## Data source
The existing `heartbeat` websocket message (`Server.send_payload("heartbeat", heartbeat_data)` in `main.py`). Fields used:

- Top level: `state` (`MENUS`/`PREGAME`/`INGAME`), `mode`, `map` (array; `map[0]` is an image URL, present INGAME only), `puuid` (self), `players` (object keyed by puuid).
- Per player: `name`, `relation` (`ally`/`enemy`), `partyNumber` (0 = solo), `agent` (name), `agentImgLink`, `rank`, `peakRank` (tier ints 0–27), `rr`, `level`, `kd`, `headshotPercentage`, `winPercentage` (string), `title`, `playerCard` (image URL), `weapons` (object keyed by weapon uuid: `weapon`, `skinDisplayName`, `skinDisplayIcon`, `buddy_displayIcon`), `sprays` (object: `displayName`, `displayIcon`, `type`).

Any field may be missing or null; render `—` (or omit the image).

## Files
| File | Purpose |
|---|---|
| `docs/players.html` | Markup skeleton: header, ally/enemy grids, modal `<dialog>`, status line. Loads `vendor/tailwind.js` and `players.js`. |
| `docs/players.js` | Websocket connect/reconnect, render cards, render modal. Target ≤ ~150 lines. |
| `docs/vendor/tailwind.js` | Vendored Tailwind v4 browser build (`@tailwindcss/browser@4`), pinned; no CDN at runtime. |
| `docs/players.sample.json` | A sample heartbeat payload (2 allies incl. one party pair, 2 enemies, weapons, sprays) for `?demo`. |
| `src/server.py` | One extra log line after the tracker URL: `players UI at http://127.0.0.1:{docs_port}/players.html?port={websocket_port}` (only when the docs server started). |
| `tests/test_tracker_server.py` | Assert the docs server serves `players.html`. |
| `UPDATES.md` | Changelog entry. |

## Behaviour
- **Connect:** `ws://${location.hostname || "localhost"}:${port}/`, `port` from `?port=` else `1100` (same rule as `matchLoadouts.js`). On close, show "Disconnected — retrying…" and reconnect every 3 s.
- **Messages:** ignore all types except `heartbeat`; keep the latest and re-render.
- **Demo:** `?demo` fetches `players.sample.json` and renders it once, no websocket.
- **Layout:** header shows `mode`, `state`, and map image as a dimmed background if present. Two columns: Allies, Enemies (by `relation`); MENUS shows one column. Within a column, keep payload order (already level/party sorted by Python).
- **Card:** player card art (or agent image) on the left; name (self highlighted), title, agent; level; rank name + peak rank name; RR; K/D, HS%, WR. Party badge "P{partyNumber}" with a colour per party number when `partyNumber > 0`.
- **Rank names:** JS array of 28 names copied from `NUMBERTORANKS` in `src/constants.py` (`Unranked` ×3, Iron 1 … Immortal 3, Radiant). Out-of-range → `—`.
- **Modal:** native `<dialog>`, opened on card click, closed by button/Esc/backdrop. Shows player card, name, title, then a grid of weapons (skin icon, weapon name, skin name, buddy icon if any) sorted by weapon name, then sprays row.
- **Styling:** Tailwind utility classes only; dark theme; no custom CSS file.

## Error handling
- Bad JSON message → ignored.
- No heartbeat yet / empty `players` → "Waiting for match…".
- Missing images → element not rendered.

## Testing
- `tests/test_tracker_server.py`: new test that `start_docs_server` serves `players.html` (status 200) from a temp docs dir, mirroring the existing entrypoint test.
- Full suite: `uv run python -m unittest discover -s tests -v`.
- Manual: open `http://127.0.0.1:1101/players.html?demo` while running the docs server (or `uv run python -m http.server -d docs 8000` → `/players.html?demo`) and check cards, party badges, modal open/close.

## Constraints
- Do not touch the updater, `status.json` logic, or the websocket bind address.
- No new Python network calls. Images load from URLs already in the payload (valorant-api media), as the existing page does.
- Keep code minimal; match repo style; commit on `local-tweaks`.
