# Lobby account features (B) — design

Date: 2026-11-03. Branch `local-tweaks`. Follows `AGENT.md` rule on legitimate Riot calls (own/party data, documented endpoints via `Requests.fetch`, cached, on demand).

## Goal
In the lobby (MENUS) the players page shows: your own equipped loadout, party details (best server ping, ready state, queue problems) and an Account panel (wallet, daily store, battle pass, last competitive RR changes).

## Non-goals
Buying, Night Market, missions, other players' accounts, anything outside MENUS.

## Riot endpoints (all verified live 2026-11-03, own account)
| Data | Call | Notes |
|---|---|---|
| Own loadout | `GET pd /personalization/v3/players/{puuid}/playerloadout` | v2 is 404. `Guns[]`: `ID` (weapon), `SkinID`, `SkinLevelID`, `ChromaID`, optional `CharmID`/`CharmLevelID` (buddy). `ActiveExpressions[]`: `AssetID` (spray or flex) |
| Party | `GET glz /parties/v1/players/{puuid}` → `CurrentPartyID`; `GET glz /parties/v1/parties/{id}` | `Members[]`: `Subject`, `IsReady`, `Pings[]` (`Ping`, `GamePodID` like `aresriot.aws-euc1-prod.eu-gp-frankfurt-1`); `EligibleQueues`, `QueueIneligibilities`, `MatchmakingData.SkillDisparityRRPenalty` |
| Wallet | `GET pd /store/v1/wallet/{puuid}` | `Balances{currencyId: amount}` |
| Store | `POST pd /store/v3/storefront/{puuid}` body `{}` | `SkinsPanelLayout.SingleItemStoreOffers[]`: `Rewards[0].ItemID` (skin level uuid), `Cost{VP id: n}`; `SingleItemOffersRemainingDurationInSeconds` |
| Contracts | `GET pd /contracts/v1/contracts/{puuid}` | `Contracts[]`: `ContractDefinitionID`, `ProgressionLevelReached`. Battle pass = contract whose valorant-api `content.relationType == "Season"`; max level = sum of `content.chapters[].levels` |
| RR history | `GET pd /mmr/v1/players/{puuid}/competitiveupdates?startIndex=0&endIndex=5&queue=competitive` | `Matches[]`: `MapID`, `RankedRatingEarned`, `TierAfterUpdate`, `RankedRatingAfterUpdate`, `MatchStartTime` (ms) |

Static metadata (valorant-api, cached via `Loadouts._api_get`): weapons, buddies, sprays, flex, currencies (`/v1/currencies`), contracts (`/v1/contracts`). Map names via `map_urls`.

Currency ids: VP `85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741`, Radianite `e59aa87c-4cbf-517a-5983-6e81511be9b7`, Kingdom Credits `85ca954a-41f2-ce94-9b45-8ca3dd39a00d`, Agent Tokens `f08d4ae3-939c-4576-ab26-09ce1f23bb37`.

## Units
- `src/account_info.py` — pure parsers (no I/O): `pod_region`, `own_loadout`, `party_details`, `wallet`, `daily_store`, `battlepass`, `rr_history`.
- `src/account_service.py` — `AccountService`: fetches via `Requests.fetch`, TTL cache per endpoint, swallows failures (returns last good value or empty). TTLs: party 10 s, loadout 60 s, wallet/rr/contracts 300 s, store until `resetsAt`.
- `main.py` MENUS branch — merges results into the heartbeat.
- `docs/players.*` — page.

## Heartbeat additions (MENUS only)
- `players[self].weapons` / `.sprays`: same shape as in-match (`{weaponUuid: {weapon, skin, skinDisplayName, skinDisplayIcon, buddy_displayIcon?}}`, `{i: {type, displayName, displayIcon}}`).
- `players[*].ping`: `{region, ms}` (lowest ping) or absent; `players[*].isReady`: bool.
- `party.eligibleQueues`: list; `party.ineligibilities`: list of strings; `party.rrPenalty`: number.
- `account`: `{wallet: [{id, name, amount, icon}], store: {offers: [{skin, name, icon, cost}], resetsAt}, battlepass: {name, level, maxLevel}, rrHistory: [{map, earned, tierAfter, rrAfter, startTime}]}`; any part may be missing.

## Page
- Own card click opens the loadout modal with own weapons (others keep the lobby note).
- Party cards: "Frankfurt 14 ms", "Not ready" badge when `isReady === false`.
- Party line: appends rank-gap penalty when `rrPenalty > 0`, and ineligibility reasons when present.
- Account panel (right column, above Friends): wallet chips (VP, Radianite, Kingdom Credits; Agent Tokens only if > 0), store 4 skins (icon, name, VP) + "Resets in h:mm:ss", battle pass "Level 33 / 55" with bar, last 5 RR changes "+18 Ascent".
- EN/TR for every label; skin names through the Turkish names file (uses the `skin` uuid).

## Error handling
Every fetch failure → that part omitted; table and page keep working. No retries beyond `Requests.fetch`.

## Testing
Unit tests for every parser and the service cache (fake `Requests`, fake clock). Demo fixture with all fields; Python test that fixture keys equal parser output keys. Headless browser check of the lobby demo (EN/TR). One live read-only check of the service against the running client.

## Scope change (same day, after Task 4)
The user asked to keep this a companion, not a standalone app, and not to build too many features. Shipped result: **own equipped loadout in the lobby only** (`src/own_loadout.py`, one endpoint). The Account panel (wallet, store, battle pass, RR history) and the party ping/ready display were removed; they remain in git history (`0361121`, `c18e7e1`). The final review also showed the lobby branch runs once per lobby entry (see `UPDATES.md`), which made live-looking ping/ready data misleading.
