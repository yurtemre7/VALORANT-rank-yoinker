"use strict";

const DEFAULT_PORT = "1100";
const LANG_KEY = "vry.lang";
// Riot's official Turkish weapon and skin names, looked up by the uuids in the payload.
// The bundled file (tools/update_tr_names.py) is used first; the live list is only
// downloaded when an open loadout has a uuid the file does not know yet.
const TR_NAMES_FILE = "players.tr-names.json";
const TR_WEAPONS_URL = "https://valorant-api.com/v1/weapons?language=tr-TR";
// One colour per rank group (Unranked, Iron, ..., Radiant); index = Math.floor(tier / 3).
const RANK_COLORS = [
    "text-zinc-400", "text-stone-400", "text-amber-600", "text-slate-300", "text-yellow-400",
    "text-cyan-400", "text-violet-400", "text-emerald-400", "text-rose-400", "text-amber-200",
];
const PARTY_COLORS = ["bg-amber-500", "bg-sky-500", "bg-fuchsia-500", "bg-emerald-500", "bg-rose-500"];

let I18N = null;
let lang = localStorage.getItem(LANG_KEY) === "tr" ? "tr" : "en";
let trNames = null; // Map uuid -> Turkish name, from the bundled file (+ live names after a miss)
let trLive = null; // at most one live download per page load
let lastHeartbeat = null;
let openPlayer = null;
let statusKey = "connecting";

const $ = (id) => document.getElementById(id);
// The Python side sends "N/A" for missing K/D and HS, and "None (0)" for a missing win rate.
const missing = (v) => v === null || v === undefined || v === "" || v === "N/A" || /^(None|N\/A) \(/.test(String(v));
const show = (v) => (missing(v) ? "—" : String(v));
const percent = (v) => (missing(v) ? "—" : `${v}%`);
// main.py sends "Unknown" until the player locks an agent.
const agentOf = (p) => (p.agent && p.agent !== "Unknown" ? p.agent : null);
const subtitle = (p) => [agentOf(p), p.title].filter(Boolean).join(" · ");
// Player cards come in three shapes on valorant-api: smallart (square), wideart (horizontal),
// largeart (tall). The payload carries largeart; every image slot on this page is square.
const squareCard = (url) => (url ? String(url).replace(/\/largeart\.png$/i, "/smallart.png") : url);
const hms = (seconds) => {
    const s = Math.max(0, Math.floor(seconds));
    return `${Math.floor(s / 3600)}:${String(Math.floor((s % 3600) / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
};
const modeName = (mode) => (mode ? I18N[lang].modes[mode] ?? mode : null);
const clock = (seconds) => {
    const s = Math.max(0, Math.floor(seconds));
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = String(s % 60).padStart(2, "0");
    return h ? `${h}:${String(m).padStart(2, "0")}:${sec}` : `${m}:${sec}`;
};
const t = (key) => I18N[lang].ui[key];

function localName(uuid, fallback) {
    if (lang !== "tr" || !trNames || !uuid) return fallback;
    const name = trNames.get(String(uuid).toLowerCase());
    if (name === undefined) fetchLiveTrNames();
    return name || fallback;
}

function fetchLiveTrNames() {
    if (trLive) return;
    trLive = fetch(TR_WEAPONS_URL)
        .then((r) => r.json())
        .then(({ data }) => {
            for (const weapon of data) {
                trNames.set(weapon.uuid, weapon.displayName);
                for (const skin of weapon.skins) trNames.set(skin.uuid, skin.displayName);
            }
            rerender();
        })
        .catch(() => {}); // unknown skins keep their English names
}

// The only way payload strings reach the DOM: textContent, never innerHTML.
function el(tag, className = "", text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
}

function img(src, className) {
    if (!src) return null;
    const node = el("img", className);
    node.src = src;
    node.alt = "";
    node.loading = "lazy";
    return node;
}

function rank(tier, label) {
    const name = I18N[lang].ranks[tier];
    return el("span", name ? RANK_COLORS[Math.floor(tier / 3)] : "text-zinc-500", `${label} ${name ?? "—"}`.trim());
}

// Streamer mode / unresolved names arrive as "#" (src/names.py), like the terminal fallback in src/colors.py.
function displayName(p) {
    if (!/^#*$/.test(p.name || "")) return p.name;
    return agentOf(p) ? `${agentOf(p)} (${t("hidden")})` : t("hiddenPlayer");
}

function iconRow(heading, items) {
    if (!items.length) return [];
    const row = el("div", "mt-4 flex flex-wrap gap-3");
    for (const item of items) row.append(img(item.displayIcon, "h-16 w-16 rounded bg-white/5 object-contain p-1"));
    return [el("h3", "mt-6 text-sm font-semibold uppercase tracking-widest text-zinc-400", heading), row];
}

const label = (text, cls = "text-xs font-semibold uppercase tracking-widest text-zinc-400") => el("h3", cls, text);

// Lobby only: your own wallet, daily store, battle pass and last ranked games
// (src/account_info.py via src/account_service.py). Any part may be missing.
function accountPanel(account) {
    const parts = [];
    if (account.wallet?.length) {
        const row = el("div", "flex flex-wrap gap-2");
        for (const c of account.wallet) {
            const chip = el("div", "flex items-center gap-2 rounded-lg bg-white/5 px-3 py-1.5");
            const icon = img(c.icon, "h-5 w-5 object-contain");
            if (icon) chip.append(icon);
            chip.append(el("span", "font-semibold", String(c.amount)),
                el("span", "text-xs text-zinc-400", I18N[lang].currencies[c.id] ?? c.name ?? ""));
            row.append(chip);
        }
        parts.push(row);
    }
    if (account.store?.offers?.length) {
        const box = el("div", "grid gap-2");
        const head = el("div", "flex items-baseline gap-3");
        const reset = el("span", "ml-auto text-xs text-zinc-400");
        reset.id = "storeReset";
        reset.dataset.resetsAt = account.store.resetsAt;
        reset.textContent = storeResetText();
        head.append(label(t("dailyStore")), reset);
        const offers = el("div", "grid grid-cols-2 gap-2");
        offers.id = "storeOffers";
        for (const o of account.store.offers) {
            const tile = el("div", "flex flex-col gap-1 rounded-lg bg-white/5 p-2");
            tile.append(img(o.icon, "h-12 w-full object-contain") || el("div", "h-12"),
                el("div", "truncate text-xs", localName(o.skin, o.name)),
                el("div", "text-xs text-zinc-400", `${o.cost ?? "—"} VP`));
            offers.append(tile);
        }
        box.append(head, offers);
        parts.push(box);
    }
    if (account.battlepass) {
        const bp = account.battlepass;
        const box = el("div", "grid gap-1");
        const head = el("div", "flex items-baseline justify-between text-sm");
        head.append(label(t("battlePass")), el("span", "", `${t("level")} ${bp.level} / ${bp.maxLevel}`));
        const track = el("div", "h-2 overflow-hidden rounded bg-white/10");
        const bar = el("div", "h-full bg-amber-400");
        bar.id = "bpBar";
        bar.style.width = `${bp.maxLevel ? Math.min(100, (bp.level / bp.maxLevel) * 100) : 0}%`;
        track.append(bar);
        box.append(head, track, el("div", "truncate text-xs text-zinc-500", bp.name || ""));
        parts.push(box);
    }
    if (account.rrHistory?.length) {
        const box = el("div", "grid gap-2");
        const row = el("div", "flex flex-wrap gap-2 text-sm font-semibold");
        row.id = "rrHistory";
        for (const m of account.rrHistory) {
            const text = m.placement ? `${t("placement")} ${show(m.map)}`
                : `${m.earned > 0 ? "+" : m.earned < 0 ? "−" : "±"}${Math.abs(m.earned ?? 0)} ${show(m.map)}`;
            const chip = el("span", `rounded-lg bg-white/5 px-2 py-1 ${m.placement || !m.earned ? "text-zinc-300" : m.earned > 0 ? "text-emerald-400" : "text-rose-400"}`, text);
            if (m.rrAfter != null && !m.placement) chip.title = `${I18N[lang].ranks[m.tierAfter] ?? "—"} · ${m.rrAfter} RR`;
            row.append(chip);
        }
        box.append(label(t("recentRanked")), row);
        parts.push(box);
    }
    return parts;
}

const storeResetText = () => {
    const at = lastHeartbeat?.account?.store?.resetsAt;
    return at ? `${t("resetsIn")} ${hms(at - Date.now() / 1000)}` : "";
};

function afkBadge() {
    return el("span", "rounded bg-zinc-600 px-1.5 text-xs font-bold text-zinc-100", t("afk"));
}

// Lobby only (src/lobby_info.party_status): queue timer, open/closed party, size.
function partyLine(hb) {
    const party = hb?.state === "MENUS" ? hb.party : null;
    if (!party?.state) return "";
    const parts = [];
    if (party.state === "MATCHMAKING") {
        parts.push(party.queueEntry ? `${t("inQueue")} ${clock(Date.now() / 1000 - party.queueEntry)}` : t("inQueue"));
    } else if (party.state === "MATCHMADE_GAME_STARTING") {
        parts.push(t("matchFound"));
    }
    if (party.accessibility) parts.push(t(party.accessibility === "OPEN" ? "openParty" : "closedParty"));
    if (party.size && party.maxSize) parts.push(`${party.size}/${party.maxSize}`);
    if (party.rrPenalty > 0) parts.push(`${t("rankGap")} ${party.rrPenalty}%`);
    if (party.ineligibilities?.length) parts.push(`${t("queueBlocked")}: ${party.ineligibilities.join(", ")}`);
    return parts.join(" · ");
}

// One online friend outside the party (src/lobby_info.friends_activity).
function friendRow(f) {
    const row = el("div", "flex items-center gap-3 rounded-lg border border-white/10 bg-white/5 p-2");
    row.append(img(squareCard(f.playerCard), "h-10 w-10 shrink-0 rounded object-cover") || el("div", "h-10 w-10 shrink-0 rounded bg-white/10"));
    const info = el("div", "min-w-0 flex-1");
    const top = el("div", "flex items-center gap-2");
    top.append(el("span", "truncate font-semibold", displayName(f)));
    if (f.isIdle) top.append(afkBadge());
    top.append(el("span", "ml-auto text-xs text-zinc-400", `${t("lv")} ${show(f.level)}`));
    const score = f.scoreAlly != null && f.scoreEnemy != null ? `${f.scoreAlly}–${f.scoreEnemy}` : null;
    const activity = [I18N[lang].states[f.state] ?? show(f.state), modeName(f.mode), f.map, score].filter(Boolean).join(" · ");
    const line = el("div", "flex flex-wrap gap-x-3 text-xs");
    line.append(el("span", "text-zinc-300", activity), rank(f.rank, ""));
    if (f.partySize > 1) line.append(el("span", "text-zinc-400", `${f.partySize}/${f.maxPartySize}`));
    info.append(top, line);
    row.append(info);
    return row;
}

function card(puuid, p, selfPuuid) {
    const self = puuid === selfPuuid;
    const root = el("button", "flex w-full items-center gap-4 rounded-xl border bg-white/5 p-3 text-left transition hover:bg-white/10 "
        + (self ? "border-amber-400/70" : "border-white/10"));
    root.type = "button";
    root.append(img(squareCard(p.playerCard) || p.agentImgLink, "h-20 w-20 shrink-0 rounded-lg object-cover")
        || el("div", "flex h-20 w-20 shrink-0 items-center justify-center rounded-lg bg-white/10 text-2xl font-bold", displayName(p).slice(0, 1)));

    const info = el("div", "min-w-0 flex-1");
    const top = el("div", "flex items-center gap-2");
    top.append(el("span", "truncate font-semibold" + (self ? " text-amber-300" : ""), displayName(p)));
    if (p.isOwner) {
        const crown = el("span", "text-sm", "👑");
        crown.title = t("partyLeader");
        top.append(crown);
    }
    if (p.isIdle) top.append(afkBadge());
    if (p.isReady === false) top.append(el("span", "rounded bg-rose-600/80 px-1.5 text-xs font-bold text-white", t("notReady")));
    if (p.partyNumber > 0) {
        top.append(el("span", `rounded px-1.5 text-xs font-bold text-zinc-950 ${PARTY_COLORS[(p.partyNumber - 1) % PARTY_COLORS.length]}`, `P${p.partyNumber}`));
    }
    top.append(el("span", "ml-auto text-sm text-zinc-400", `${t("lv")} ${show(p.level)}`));
    info.append(top);
    if (subtitle(p)) info.append(el("div", "truncate text-xs text-zinc-400", subtitle(p)));

    const ranks = el("div", "mt-1 flex flex-wrap gap-x-3 text-sm");
    ranks.append(rank(p.rank, ""), rank(p.peakRank, t("peak")), el("span", "text-zinc-400", `${show(p.rr)} RR`));
    const stats = el("div", "mt-1 flex flex-wrap gap-x-3 text-xs text-zinc-400");
    stats.append(el("span", "", `${t("kd")} ${show(p.kd)}`), el("span", "", `${t("hs")} ${percent(p.headshotPercentage)}`),
        el("span", "", `${t("wr")} ${show(p.winPercentage)}`));
    // Lobby: best server and ping from the party endpoint (src/account_info.party_details).
    if (p.ping) stats.append(el("span", "text-emerald-400", `${p.ping.region} ${p.ping.ms} ms`));
    info.append(ranks, stats);
    root.append(info);
    root.addEventListener("click", () => openLoadout(p));
    return root;
}

function openLoadout(p) {
    openPlayer = p;
    const head = $("loadoutHead");
    const body = $("loadoutBody");
    head.replaceChildren();
    body.replaceChildren();
    const art = img(squareCard(p.playerCard) || p.agentImgLink, "h-24 w-24 rounded-lg object-cover");
    if (art) head.append(art);
    const who = el("div");
    who.append(el("div", "text-xl font-bold", displayName(p)), el("div", "text-sm text-zinc-400", subtitle(p)));
    head.append(who);

    const weapons = Object.entries(p.weapons || {}).filter(([, w]) => w.weapon)
        .map(([id, w]) => ({ ...w, weapon: localName(id, w.weapon), skinDisplayName: localName(w.skin, w.skinDisplayName) }))
        .sort((a, b) => a.weapon.localeCompare(b.weapon, lang));
    if (!weapons.length) {
        body.append(el("p", "py-8 text-center text-zinc-400", "weapons" in p ? t("noLoadout") : `${t("noLoadout")}. ${t("lobbyNote")}`));
    } else {
        const grid = el("div", "grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4");
        for (const w of weapons) {
            const tile = el("div", "relative flex flex-col gap-2 rounded-lg border border-white/10 bg-white/5 p-3");
            tile.append(img(w.skinDisplayIcon, "h-16 w-full object-contain") || el("div", "h-16"),
                // Uppercase in JS, not CSS: under lang="tr" CSS would turn an English fallback "Sheriff" into "SHERİFF".
                el("div", "text-xs tracking-wide text-zinc-400", w.weapon.toUpperCase()),
                el("div", "truncate text-sm", show(w.skinDisplayName)));
            const buddy = img(w.buddy_displayIcon, "absolute right-2 top-2 h-8 w-8");
            if (buddy) tile.append(buddy);
            grid.append(tile);
        }
        body.append(grid);
    }

    // src/Loadouts.py tags each expression as "spray" or "flex" (emote).
    const expressions = Object.values(p.sprays || {}).filter((s) => s && s.displayIcon);
    body.append(...iconRow(t("sprays"), expressions.filter((s) => s.type !== "flex")),
        ...iconRow(t("emotes"), expressions.filter((s) => s.type === "flex")));
    if (!$("loadout").open) $("loadout").showModal();
}

function render(hb) {
    lastHeartbeat = hb;
    $("mode").textContent = modeName(hb.mode) ?? "—";
    $("state").textContent = I18N[lang].states[hb.state] ?? show(hb.state);
    // main.py sends the map name in "map" and its image in "mapSplash".
    const splash = hb.mapSplash || (/^https?:/.test(hb.map?.[0] || "") ? hb.map[0] : "");
    document.body.style.backgroundImage = splash ? `url(${JSON.stringify(splash)})` : "";

    const entries = Object.entries(hb.players || {});
    const lobby = hb.state === "MENUS";
    const allies = entries.filter(([, p]) => p.relation !== "enemy");
    const enemies = entries.filter(([, p]) => p.relation === "enemy");
    $("alliesTitle").textContent = t(lobby ? "party" : "allies");
    $("allies").replaceChildren(...allies.map(([id, p]) => card(id, p, hb.puuid)));
    $("enemies").replaceChildren(...enemies.map(([id, p]) => card(id, p, hb.puuid)));
    $("enemiesSection").hidden = !enemies.length;
    $("partyStatus").textContent = partyLine(hb);
    const friends = lobby ? hb.friends || [] : [];
    $("friends").replaceChildren(...friends.map(friendRow));
    $("friendsSection").hidden = !friends.length;
    const panel = lobby && hb.account ? accountPanel(hb.account) : [];
    $("account").replaceChildren(...panel);
    $("accountSection").hidden = !panel.length;
    $("lobbyAside").hidden = $("friendsSection").hidden && $("accountSection").hidden;
    if (!entries.length) $("allies").append(el("p", "text-zinc-400", t(lobby ? "waitingParty" : "waiting")));
    else if (lobby) $("allies").append(el("p", "text-xs text-zinc-500", t("lobbyNote")));
}

function setStatus(key) {
    statusKey = key;
    $("status").textContent = t(key);
}

function rerender() {
    for (const node of document.querySelectorAll("[data-i18n]")) node.textContent = t(node.dataset.i18n);
    document.title = t("title");
    setStatus(statusKey);
    if (lastHeartbeat) render(lastHeartbeat);
    if (openPlayer && $("loadout").open) openLoadout(openPlayer);
}

function setLang(next) {
    lang = next;
    localStorage.setItem(LANG_KEY, lang);
    document.documentElement.lang = lang;
    for (const button of document.querySelectorAll("[data-lang]")) {
        button.classList.toggle("bg-white/20", button.dataset.lang === lang);
    }
    rerender();
    if (lang === "tr" && !trNames) {
        fetch(TR_NAMES_FILE)
            .then((r) => r.json())
            .catch(() => ({})) // no local file: every uuid is a miss, so the live list fills in
            .then((names) => {
                trNames = new Map(Object.entries(names));
                rerender();
            });
    }
}

function connect() {
    const port = new URLSearchParams(location.search).get("port") || DEFAULT_PORT;
    const socket = new WebSocket(`ws://${location.hostname || "localhost"}:${port}/`);
    socket.addEventListener("open", () => setStatus("connected"));
    socket.addEventListener("message", (event) => {
        let msg;
        try { msg = JSON.parse(event.data); } catch { return; }
        if (msg.type === "heartbeat") render(msg);
    });
    socket.addEventListener("close", () => {
        setStatus("disconnected");
        setTimeout(connect, 3000);
    });
}

async function init() {
    I18N = await (await fetch("players.i18n.json")).json();
    const dialog = $("loadout");
    $("loadoutClose").addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
    for (const button of document.querySelectorAll("[data-lang]")) {
        button.addEventListener("click", () => setLang(button.dataset.lang));
    }
    setLang(lang);
    setInterval(() => {
        if (!lastHeartbeat) return;
        $("partyStatus").textContent = partyLine(lastHeartbeat);
        if ($("storeReset")) $("storeReset").textContent = storeResetText();
    }, 1000);

    const demo = new URLSearchParams(location.search).get("demo");
    if (demo === null) return connect();
    setStatus("demo");
    try {
        const response = await fetch(demo === "lobby" ? "players.lobby.sample.json" : "players.sample.json");
        const hb = await response.json();
        if (hb.party?.queueEntry) hb.party.queueEntry = Date.now() / 1000 - 83; // demo: a queue that started 1:23 ago
        if (hb.account?.store?.resetsAt > 1e9 && demo === "lobby") hb.account.store.resetsAt = Math.floor(Date.now() / 1000) + 5 * 3600 + 12 * 60 + 3;
        render(hb);
    } catch {
        setStatus("demoFailed");
    }
}

init();
