# How to run (from source)

Windows only. Runs from source with [uv](https://docs.astral.sh/uv/); never use the fork's `vry.exe` or `updatescript.bat`.

## 1. One-time setup

Install uv (it also installs the right Python, 3.14):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Get the code (branch `local-tweaks`) and install dependencies:

```powershell
git clone -b local-tweaks https://github.com/yurtemre7/VALORANT-rank-yoinker.git
cd VALORANT-rank-yoinker
uv sync
```

## 2. Run

1. Start VALORANT and log in.
2. In the repo folder:

   ```powershell
   uv run python main.py
   ```

The first start writes a default `config.json`. To change settings (columns, weapon, port, …) with a guided menu: `uv run python main.py --config`.

The console shows two clickable links (use Windows Terminal so they are clickable):

- **Player Inventories**: the original loadout page.
- **Players Dashboard**: player cards + loadouts, EN/TR toggle (`http://127.0.0.1:1101/players.html?port=1100`).

### On your phone

Open the console link `vRY Mobile - http://<pc-ip>:1101/players.html?port=1100` on a phone in the same network.

- The phone's browser needs local network access: on Android allow **Nearby devices** for the browser (Settings → Apps → *browser* → Permissions); on iPhone turn on **Local Network** for it (Settings → Privacy & Security → Local Network). Without it the page fails (e.g. `ERR_TOO_MANY_RETRIES`) even on the same Wi-Fi.
- Windows asks once whether Python may accept connections; allow it.

## 3. Try the dashboard without VALORANT

```powershell
uv run python -m http.server -d docs 8000
```

Open http://127.0.0.1:8000/players.html?demo (in match) or `?demo=lobby` (lobby).

## Troubleshooting

| Problem | Fix |
|---|---|
| Windows Firewall asks about Python | Allow it (needed for the phone; the PC pages work either way). |
| Phone link does not load | Allow **Nearby devices** (Android) / **Local Network** (iPhone) for the phone's browser; the phone must be on the same network as the PC. |
| "vRY is being blocked by the firewall!!" | Port 1100 is in use. Close the other vRY / app, or change `"port"` in `config.json`. |
| Garbled symbols or `UnicodeEncodeError` | Use Windows Terminal. When piping output: `$env:PYTHONUTF8=1` first. |
| Stuck waiting / no players | VALORANT must be running and logged in. Restart vRY after restarting VALORANT. |
| Anything else | Check the newest `logs/log-N.txt`. |

## Tests

```powershell
uv run python -m unittest discover -s tests -v
```

## Updating from latenitekode

```powershell
git fetch origin
git rebase origin/main
uv sync
uv run python -m unittest discover -s tests
git push --force-with-lease fork local-tweaks
```

Never merge into `main` or push to `origin` / `upstream` (see `AGENT.md`).

After a VALORANT patch with new skins, refresh the bundled Turkish names (the page also fetches missing ones live):

```powershell
uv run python tools/update_tr_names.py
```
