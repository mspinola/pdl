"""Download weekly results and playoff brackets from MyFantasyLeague."""
import json, os, time, urllib.request, urllib.parse, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_mfl import LEAGUES, UA

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = f"{BASE}/raw"


def get(year, params, dest):
    path = os.path.join(RAW, dest)
    if os.path.exists(path) and os.path.getsize(path) > 120:
        return json.load(open(path))
    url = f"https://api.myfantasyleague.com/{year}/export?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8", "replace"))
    with open(path, "w") as f:
        json.dump(data, f)
    time.sleep(1.2)
    return data


def main():
    for year, lid in sorted(LEAGUES.items()):
        try:
            d = get(year, {"TYPE": "schedule", "L": lid, "JSON": 1}, f"schedule_{year}.json")
            weeks = d.get("schedule", {}).get("weeklySchedule", [])
            print(f"ok  schedule {year}: {len(weeks) if isinstance(weeks, list) else 1} weeks")
        except Exception as e:  # noqa: BLE001
            print(f"ERR schedule {year}: {e}")
        # three brackets: two semifinal ladders and the final
        for b in (1, 2, 3):
            try:
                d = get(year, {"TYPE": "playoffBracket", "L": lid, "BRACKET_ID": b, "JSON": 1},
                        f"bracket_{year}_{b}.json")
                tag = "error" if "error" in d else "ok"
                print(f"    bracket {b} {year}: {tag}")
            except Exception as e:  # noqa: BLE001
                print(f"    ERR bracket {b} {year}: {e}")


if __name__ == "__main__":
    main()
