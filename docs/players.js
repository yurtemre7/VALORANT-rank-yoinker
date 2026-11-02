"use strict";

const DEFAULT_PORT = "1100";
const RANKS = [
    "Unranked", "Unranked", "Unranked",
    "Iron 1", "Iron 2", "Iron 3", "Bronze 1", "Bronze 2", "Bronze 3",
    "Silver 1", "Silver 2", "Silver 3", "Gold 1", "Gold 2", "Gold 3",
    "Platinum 1", "Platinum 2", "Platinum 3", "Diamond 1", "Diamond 2", "Diamond 3",
    "Ascendant 1", "Ascendant 2", "Ascendant 3", "Immortal 1", "Immortal 2", "Immortal 3",
    "Radiant",
];
// One colour per rank group (Unranked, Iron, ..., Radiant); index = Math.floor(tier / 3).
const RANK_COLORS = [
    "text-zinc-400", "text-stone-400", "text-amber-600", "text-slate-300", "text-yellow-400",
    "text-cyan-400", "text-violet-400", "text-emerald-400", "text-rose-400", "text-amber-200",
];
const PARTY_COLORS = ["bg-amber-500", "bg-sky-500", "bg-fuchsia-500", "bg-emerald-500", "bg-rose-500"];
const LOBBY_NOTE = "Riot only shares loadouts once agent select starts.";

const $ = (id) => document.getElementById(id);
const show = (v) => (v === null || v === undefined || v === "" ? "—" : String(v));

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
    const name = RANKS[tier];
    return el("span", name ? RANK_COLORS[Math.floor(tier / 3)] : "text-zinc-500", `${label} ${name ?? "—"}`);
}

// Streamer mode / unresolved names arrive as "#" (src/names.py), like the terminal fallback in src/colors.py.
function displayName(p) {
    if (!/^#*$/.test(p.name || "")) return p.name;
    return p.agent ? `${p.agent} (hidden)` : "—";
}

function card(puuid, p, selfPuuid) {
    const self = puuid === selfPuuid;
    const root = el("button", "flex w-full items-center gap-4 rounded-xl border bg-white/5 p-3 text-left transition hover:bg-white/10 "
        + (self ? "border-amber-400/70" : "border-white/10"));
    root.type = "button";
    root.append(img(p.playerCard || p.agentImgLink, "h-20 w-20 shrink-0 rounded-lg object-cover")
        || el("div", "flex h-20 w-20 shrink-0 items-center justify-center rounded-lg bg-white/10 text-2xl font-bold", displayName(p).slice(0, 1)));

    const info = el("div", "min-w-0 flex-1");
    const top = el("div", "flex items-center gap-2");
    top.append(el("span", "truncate font-semibold" + (self ? " text-amber-300" : ""), displayName(p)));
    if (p.partyNumber > 0) {
        top.append(el("span", `rounded px-1.5 text-xs font-bold text-zinc-950 ${PARTY_COLORS[(p.partyNumber - 1) % PARTY_COLORS.length]}`, `P${p.partyNumber}`));
    }
    top.append(el("span", "ml-auto text-sm text-zinc-400", `Lv ${show(p.level)}`));
    info.append(top);
    if (p.title || p.agent) info.append(el("div", "truncate text-xs text-zinc-400", [p.agent, p.title].filter(Boolean).join(" · ")));

    const ranks = el("div", "mt-1 flex flex-wrap gap-x-3 text-sm");
    ranks.append(rank(p.rank, ""), rank(p.peakRank, "Peak"), el("span", "text-zinc-400", `${show(p.rr)} RR`));
    const stats = el("div", "mt-1 flex flex-wrap gap-x-3 text-xs text-zinc-400");
    stats.append(el("span", "", `K/D ${show(p.kd)}`), el("span", "", `HS ${show(p.headshotPercentage)}%`), el("span", "", `WR ${show(p.winPercentage)}`));
    info.append(ranks, stats);
    root.append(info);
    root.addEventListener("click", () => openLoadout(p));
    return root;
}

function openLoadout(p) {
    const head = $("loadoutHead");
    const body = $("loadoutBody");
    head.replaceChildren();
    body.replaceChildren();
    const art = img(p.playerCard || p.agentImgLink, "h-24 w-24 rounded-lg object-cover");
    if (art) head.append(art);
    const who = el("div");
    who.append(el("div", "text-xl font-bold", displayName(p)), el("div", "text-sm text-zinc-400", [p.agent, p.title].filter(Boolean).join(" · ")));
    head.append(who);

    const weapons = Object.values(p.weapons || {}).filter((w) => w.weapon)
        .sort((a, b) => a.weapon.localeCompare(b.weapon));
    if (!weapons.length) {
        body.append(el("p", "py-8 text-center text-zinc-400", "weapons" in p ? "No loadout data" : `No loadout data. ${LOBBY_NOTE}`));
    } else {
        const grid = el("div", "grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4");
        for (const w of weapons) {
            const tile = el("div", "relative flex flex-col gap-2 rounded-lg border border-white/10 bg-white/5 p-3");
            tile.append(img(w.skinDisplayIcon, "h-16 w-full object-contain") || el("div", "h-16"),
                el("div", "text-xs uppercase tracking-wide text-zinc-400", w.weapon),
                el("div", "truncate text-sm", show(w.skinDisplayName)));
            const buddy = img(w.buddy_displayIcon, "absolute right-2 top-2 h-8 w-8");
            if (buddy) tile.append(buddy);
            grid.append(tile);
        }
        body.append(grid);
    }

    const sprays = Object.values(p.sprays || {}).filter((s) => s && s.displayIcon);
    if (sprays.length) {
        const row = el("div", "mt-4 flex gap-3");
        for (const s of sprays) row.append(img(s.displayIcon, "h-16 w-16 rounded bg-white/5 object-contain p-1"));
        body.append(el("h3", "mt-6 text-sm font-semibold uppercase tracking-widest text-zinc-400", "Sprays"), row);
    }
    $("loadout").showModal();
}

function render(hb) {
    $("mode").textContent = show(hb.mode);
    $("state").textContent = show(hb.state);
    document.body.style.backgroundImage = hb.map?.[0] ? `url(${JSON.stringify(hb.map[0])})` : "";

    const entries = Object.entries(hb.players || {});
    const lobby = hb.state === "MENUS";
    const allies = entries.filter(([, p]) => p.relation !== "enemy");
    const enemies = entries.filter(([, p]) => p.relation === "enemy");
    $("alliesTitle").textContent = lobby ? "Party" : "Allies";
    $("allies").replaceChildren(...allies.map(([id, p]) => card(id, p, hb.puuid)));
    $("enemies").replaceChildren(...enemies.map(([id, p]) => card(id, p, hb.puuid)));
    $("enemiesSection").hidden = !enemies.length;
    if (!entries.length) $("allies").append(el("p", "text-zinc-400", "Waiting for match…"));
    else if (lobby) $("allies").append(el("p", "text-xs text-zinc-500", LOBBY_NOTE));
}

function connect() {
    const port = new URLSearchParams(location.search).get("port") || DEFAULT_PORT;
    const socket = new WebSocket(`ws://${location.hostname || "localhost"}:${port}/`);
    socket.addEventListener("open", () => { $("status").textContent = "Connected"; });
    socket.addEventListener("message", (event) => {
        let msg;
        try { msg = JSON.parse(event.data); } catch { return; }
        if (msg.type === "heartbeat") render(msg);
    });
    socket.addEventListener("close", () => {
        $("status").textContent = "Disconnected — retrying…";
        setTimeout(connect, 3000);
    });
}

function init() {
    const dialog = $("loadout");
    $("loadoutClose").addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });

    const demo = new URLSearchParams(location.search).get("demo");
    if (demo === null) return connect();
    $("status").textContent = "Demo";
    fetch(demo === "lobby" ? "players.lobby.sample.json" : "players.sample.json")
        .then((r) => r.json())
        .then(render);
}

init();
