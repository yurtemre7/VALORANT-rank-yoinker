# Lobby Account Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Own loadout, party details and an Account panel in the lobby view of `docs/players.html`.

**Architecture:** Pure parsers (`src/account_info.py`) + a cached fetcher (`src/account_service.py`) feeding the MENUS heartbeat in `main.py`; the page renders the new fields.

**Tech Stack:** Python 3.14 `unittest`, plain JS + Tailwind, Playwright (dev-only) for the browser check.

**Spec:** `plans/2026-11-03-lobby-account-design.md`

## Global Constraints
- Riot calls only through `Requests.fetch`; only the endpoints in the spec table; all GET except storefront `POST {}`.
- TTLs: party 10 s, loadout 60 s, wallet/rr/contracts 300 s, store until `resetsAt`. Calls only from the MENUS branch.
- Failures never raise out of `AccountService`; the table must keep rendering.
- Page strings via `textContent` only; every new label in `players.i18n.json` en+tr.
- Tests: `uv run python -m unittest discover -s tests -v`. One commit per task, trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. `UPDATES.md` entry listing each endpoint.

## Review Focus
1. Endpoint returns error dict / non-200 → that section absent, no exception (service tests).
2. Party with one member / no `Pings` → no ping shown, no crash (parser test).
3. Store offer whose skin level is unknown to metadata → offer skipped (parser test).
4. Loadout gun without buddy, expression neither spray nor flex → no buddy / skipped (parser test).
5. Clock: store `resetsAt` in the past → countdown shows 0:00:00, not negative (page check).

### Task 1: Parsers — `src/account_info.py`
Tests `tests/test_account_info.py` first (RED), then implement:
- `pod_region(game_pod_id) -> str|None`: `"aresriot.aws-euc1-prod.eu-gp-frankfurt-1"` → `"Frankfurt"`; `"…-gp-sao-paulo-1"` → `"Sao Paulo"`; garbage → None.
- `own_loadout(raw, meta) -> (weapons, sprays)`; `meta` = dict of uuid-indexed valorant-api lists `weapons`, `buddies`, `sprays`, `flex` (built by `index_metadata(lists)`). Output shapes per spec; chroma icon preferred, Standard/Melee default skins use weapon icon (as `Loadouts.convertLoadoutToJsonArray`).
- `party_details(raw) -> dict`: `{members: {puuid: {isReady, ping: {region, ms}|None}}, eligibleQueues, ineligibilities, rrPenalty}`.
- `wallet(raw, currencies) -> list` ordered VP, Radianite, Kingdom Credits, others; zero-balance Agent Tokens dropped.
- `daily_store(raw, meta, now) -> {offers, resetsAt}`; skin level uuid → parent skin.
- `battlepass(raw, contracts_meta) -> {name, level, maxLevel}|None`.
- `rr_history(raw, map_names) -> list` (max 5, newest first).

### Task 2: Service — `src/account_service.py`
Tests `tests/test_account_service.py` with a fake Requests (records calls, returns canned data/errors) and fake clock: TTL respected, failures → last good / empty, store refetched after `resetsAt`, no calls when puuid missing.
`AccountService(requests, metadata, map_names, clock=time.time)`; `lobby(puuid) -> {"loadout": (weapons, sprays)|None, "party": dict|None, "account": dict}`. `metadata()` callable returns index from `index_metadata`.

### Task 3: Wiring + page part 1 (own loadout, party details)
`main.py` MENUS: one `AccountService` created at startup (metadata from `loadoutsClass._api_get`), merge into heartbeat per spec. Fixture `docs/players.lobby.sample.json` gets self weapons/sprays, pings, isReady, party extras; tests assert fixture keys == parser output keys. Page: own-card loadout, ping line, Not ready badge, party line extras; i18n; browser check RED→GREEN.

### Task 4: Page part 2 (Account panel)
Fixture `account`; page panel per spec with live store countdown; i18n; browser check EN/TR RED→GREEN.

### Task 5: Docs, live check, final review
`UPDATES.md` (endpoints), live read-only `AccountService.lobby` run against the client, fresh-reviewer final review, fixes.
