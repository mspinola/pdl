"""Download the PDL league history from the MyFantasyLeague export API."""
import json, os, time, urllib.request, urllib.parse

RAW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "raw")
UA = "PDL league analytics (+https://github.com/mspinola/pdl)"

# year -> league id, parsed from the 2026 league history block
LEAGUES = {
    2003: 65775, 2004: 53450, 2005: 64832, 2006: 61505, 2007: 61839,
    2008: 71127, 2009: 39444, 2010: 20526, 2011: 17475, 2012: 46585,
    2013: 31368, 2014: 42887, 2015: 41498, 2016: 16177, 2017: 16177,
    2018: 16177, 2019: 16177, 2020: 16177, 2021: 16177, 2022: 16177,
    2023: 16177, 2024: 16177, 2025: 16177, 2026: 16177,
}

# Everything downstream derives its season range from LEAGUES, so a new season
# is one line here (see YEARLY.md). The league has kept id 16177 since 2016.
FIRST_MFL_SEASON = min(LEAGUES)
LAST_SEASON = max(LEAGUES)


def get(year, params, dest):
    path = os.path.join(RAW, dest)
    if os.path.exists(path) and os.path.getsize(path) > 200:
        return json.load(open(path))
    url = f"https://api.myfantasyleague.com/{year}/export?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read().decode("utf-8", "replace")
    data = json.loads(body)
    with open(path, "w") as f:
        json.dump(data, f)
    time.sleep(1.5)
    return data


def main():
    for year, lid in sorted(LEAGUES.items()):
        for kind, extra in (
            ("league", {}),
            ("trades", {"TRANS_TYPE": "TRADE"}),
            ("rosters", {}),
        ):
            ttype = {"league": "league", "trades": "transactions", "rosters": "rosters"}[kind]
            params = {"TYPE": ttype, "L": lid, "JSON": 1, **extra}
            try:
                get(year, params, f"{kind}_{year}.json")
                print(f"ok  {kind} {year}")
            except Exception as e:  # noqa: BLE001
                print(f"ERR {kind} {year}: {e}")
    # global player name table (one call, latest year)
    try:
        get(LAST_SEASON, {"TYPE": "players", "DETAILS": 1, "JSON": 1}, "players.json")
        print("ok  players")
    except Exception as e:  # noqa: BLE001
        print(f"ERR players: {e}")


if __name__ == "__main__":
    main()
