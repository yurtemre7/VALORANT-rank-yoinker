# Players UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A new local page `docs/players.html` showing rich player cards and a per-player equipped-loadout modal, fed by the existing `heartbeat` websocket payload.

**Architecture:** Static page served by the existing docs HTTP server in `src/server.py`. One small JS file connects to the existing websocket, keeps the latest `heartbeat`, and re-renders. Tailwind is vendored as a single browser build; no build step. Python only gains one log line.

**Tech Stack:** Plain JS (ES2020, no modules needed), Tailwind v4 browser build (vendored), Python 3.14 `unittest` for the server test.

**Spec:** `plans/2026-11-03-players-ui-design.md`

## Global Constraints
- Branch `local-tweaks`; one commit per task; commit trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Tests: `uv run python -m unittest discover -s tests -v` (no network).
- Do not modify `docs/matchLoadouts.*`, the updater, `status.json` logic, or the websocket bind address. No new Python network calls, no new websocket payloads.
- Websocket URL: `ws://${location.hostname || "localhost"}:${port}/`, `port` = `?port=` else `"1100"`.
- Tailwind utility classes only, dark theme, no custom CSS file. `docs/players.js` target ≤ ~150 lines.
- Player-supplied strings (`name`, `title`, `agent`, skin names) are rendered with `textContent` / DOM APIs, never interpolated into `innerHTML`.
- Missing/null fields render `—`; missing image URLs render no `<img>`.
- Append a dated entry to `UPDATES.md` (file / what / why) for every change.

## Review Focus
1. Player name containing HTML (`<img src=x onerror=alert(1)>`) → shown as literal text, no script runs. Pinned by sample fixture player in Task 2.
2. Player with `weapons: null` / `sprays: null` (pregame fallback payload) → card renders, modal shows "No loadout data". Pinned by sample fixture in Task 2.
3. Page served from docs port (1101) → still connects to websocket port from `?port=`, not the page's own port. Pinned by Task 1 log URL test + Task 2 connect rule.
4. Empty name (streamer mode / hidden) → card shows agent name instead of blank. Pinned by sample fixture in Task 2.
5. MENUS state (no enemies, `relation` all `ally`) → single column, no empty "Enemies" header. Manual check in Task 2 by editing `state` in demo.

---

### Task 1: Players URL log line in docs server

**Files:**
- Modify: `src/server.py` (`Server.start_docs_server`, after the existing `tracker UI serving …` log)
- Test: `tests/test_tracker_server.py`

**Interfaces:**
- Produces: log line `players UI at http://127.0.0.1:{docs_port}/players.html?port={websocket_port}`; nothing else depends on it.

- [ ] **Step 1: Write the failing test** `test_docs_server_serves_players_page_and_logs_url` in `TrackerServerTests`, mirroring `test_local_tracker_server_serves_entrypoint_from_frozen_layout`: temp `docs/` containing `matchLoadouts.html` and `players.html` (text `players-ok`); call `tracker.start_docs_server(65535)`; then
  - `urlopen(f"http://127.0.0.1:{tracker.docs_port}/players.html").read().decode() == "players-ok"`
  - `any(f"/players.html?port=65535" in line for line in logs)`
  - shut down `tracker.docs_server` in `finally` as the existing test does.
- [ ] **Step 2: Run it, expect FAIL on the log assertion**
  `uv run python -m unittest tests.test_tracker_server -v`
- [ ] **Step 3: Add the log line** in `start_docs_server` right after `self.log(f"tracker UI serving …")`, using `self.docs_port` and `int(websocket_port)`.
- [ ] **Step 4: Run full suite, expect all PASS**
  `uv run python -m unittest discover -s tests -v`
- [ ] **Step 5: Commit** `src/server.py tests/test_tracker_server.py` — "Log players UI URL from docs server".

### Task 2: Players page (Tailwind, cards, loadout modal, demo fixture)

**Files:**
- Create: `docs/vendor/tailwind.js`, `docs/players.html`, `docs/players.js`, `docs/players.sample.json`
- Modify: `UPDATES.md`
- Test: `tests/test_players_page.py`

**Interfaces:**
- Consumes: `heartbeat` message fields listed in the spec's *Data source* section (exact names: `state`, `mode`, `map`, `puuid`, `players{puuid: {name, relation, partyNumber, agent, agentImgLink, rank, peakRank, rr, level, kd, headshotPercentage, winPercentage, title, playerCard, weapons{uuid: {weapon, skinDisplayName, skinDisplayIcon, buddy_displayIcon}}, sprays{i: {displayName, displayIcon, type}}}}`).
- Produces: nothing consumed by other tasks.

- [ ] **Step 1: Write the failing test** `tests/test_players_page.py` (`unittest`, no network, paths relative to repo root via `Path(__file__).resolve().parents[1] / "docs"`):
  - `test_sample_payload_shape`: `players.sample.json` loads; `type == "heartbeat"`; `len(players) == 5`; exactly 3 `relation == "ally"` (one is `puuid`, i.e. self) and 2 `"enemy"`; exactly two players share a `partyNumber > 0`; one player's `name` is `"<img src=x onerror=alert(1)>"`; one has `name == ""`; one has `weapons` and `sprays` null; at least one player has ≥3 weapons each with `weapon`, `skinDisplayName`, `skinDisplayIcon`.
  - `test_page_wiring`: `players.html` contains `vendor/tailwind.js` and `players.js`; `players.js` contains `"heartbeat"`, `"1100"`, `"players.sample.json"`, and does **not** contain `innerHTML =` followed by a template literal (regex `innerHTML\s*=\s*\``).
  - `test_rank_names`: `players.js` contains `"Radiant"` and `"Immortal 3"`.
- [ ] **Step 2: Run it, expect FAIL** (files missing)
  `uv run python -m unittest tests.test_players_page -v`
- [ ] **Step 3: Vendor Tailwind** — download `https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4/dist/index.global.js` to `docs/vendor/tailwind.js`; note the resolved version (from the file's header comment or `https://data.jsdelivr.com/v1/package/npm/@tailwindcss/browser`) for `UPDATES.md`.
- [ ] **Step 4: Write `docs/players.sample.json`** satisfying `test_sample_payload_shape`; `state: "INGAME"`, a `map` array with one valorant-api map splash URL, image URLs pointing at `media.valorant-api.com`.
- [ ] **Step 5: Write `docs/players.html`** — dark Tailwind body; header (`#mode`, `#state`, `#status`, map background `#map`); `#allies` and `#enemies` grids each under a heading; `<dialog id="loadout">` with close button; scripts `vendor/tailwind.js` then `players.js` (`defer`).
- [ ] **Step 6: Write `docs/players.js`** with these functions:
  - `RANKS` — 28 names: `Unranked`×3, `Iron 1`…`Iron 3`, `Bronze`, `Silver`, `Gold`, `Platinum`, `Diamond`, `Ascendant`, `Immortal` 1–3 each, `Radiant`.
  - `el(tag, className, text)` → element with `textContent` (the only way strings reach the DOM).
  - `connect()` — websocket per Global Constraints; on `message` parse JSON (ignore errors), keep only `type === "heartbeat"`, call `render(msg)`; on `close` set status "Disconnected — retrying…" and `setTimeout(connect, 3000)`.
  - `render(hb)` — header fields; map background if `hb.map?.[0]`; split players by `relation`; hide the Enemies section when it has none; "Waiting for match…" when no players.
  - `card(p, selfPuuid)` — card art (`playerCard` or `agentImgLink`), display name = `p.name || p.agent || "—"`, self ring highlight, title, agent, `Lv {level}`, rank / peak via `RANKS[n] ?? "—"`, RR, K/D, HS%, WR; party badge `P{partyNumber}` coloured from a small palette indexed by `partyNumber` when `> 0`; click → `openLoadout(p)`.
  - `openLoadout(p)` — fill dialog: card art, name, title; weapons sorted by `weapon` as tiles (skin icon, weapon, skin name, buddy icon); sprays row; "No loadout data" when `weapons` is empty/null; `dialog.showModal()`; close on button and backdrop click.
  - Entry: `?demo` → `fetch("players.sample.json")` → `render`; else `connect()`.
- [ ] **Step 7: Run test, expect PASS**, then full suite
  `uv run python -m unittest discover -s tests -v`
- [ ] **Step 8: Manual check** — `uv run python -m http.server -d docs 8000`, open `http://127.0.0.1:8000/players.html?demo`: 3 allies / 2 enemies, party pair shares a badge colour, XSS name shows as literal text, empty-name card shows its agent, null-loadout modal says "No loadout data", Esc and backdrop close the modal. Temporarily change sample `state` to `MENUS` and all `relation` to `ally` → Enemies section hidden; revert.
- [ ] **Step 9: `UPDATES.md`** — append dated section "players UI": table rows for each new file and the `server.py` log line (what/why), Tailwind version pinned, and the re-port note "self-contained in `docs/players.*` + `docs/vendor/`; depends only on the `heartbeat` payload field names".
- [ ] **Step 10: Commit** the four `docs/` files, `tests/test_players_page.py`, `UPDATES.md` — "Add Tailwind players page with loadout modal".
