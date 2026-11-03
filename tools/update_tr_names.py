"""Download Riot's Turkish weapon and skin names into docs/players.tr-names.json.

The players page reads this local file in Turkish mode and only goes online for
uuids it does not contain (skins released after the last run). Re-run after big
VALORANT patches:

    uv run python tools/update_tr_names.py
"""

import json
from pathlib import Path

import requests

URL = "https://valorant-api.com/v1/weapons?language=tr-TR"
OUT = Path(__file__).resolve().parents[1] / "docs" / "players.tr-names.json"


def main():
    response = requests.get(URL, timeout=30)
    response.raise_for_status()
    names = {}
    for weapon in response.json()["data"]:
        names[weapon["uuid"].lower()] = weapon["displayName"]
        for skin in weapon["skins"]:
            names[skin["uuid"].lower()] = skin["displayName"]
    # One entry per line, sorted, so a refresh shows a readable git diff.
    OUT.write_text(
        json.dumps(dict(sorted(names.items())), ensure_ascii=False, indent=0) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {len(names)} names to {OUT}")


if __name__ == "__main__":
    main()
