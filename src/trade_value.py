"""Trade value: what each side of a trade got out of it, 2008 on.

For every trade from 2008 (trades.json, MFL era, where lineups exist), the
regular-season starts and points each team got from the players it received,
from the trade's season on, for as long as it kept them. Draft picks are
counted but not scored: what a pick turns into depends on who is taken with it,
so a trade with picks on either side is left out of the worst-trade ranking.
A title is credited to a received player when he started a championship playoff
game for the team that season.

    python3 src/trade_value.py      # datasets/trade_value.csv
"""
import csv, json, os, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import weekly
from fetch_mfl import LAST_SEASON

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIRST = weekly.FIRST_RELIABLE


def starts():
    """(player id, team) -> {season: [starts, points]} in the regular season, and the playoff starts."""
    reg, po = defaultdict(lambda: defaultdict(lambda: [0, 0.0])), set()
    for r in weekly.seasons(FIRST, LAST_SEASON):
        for p in r["players"]:
            if not p["started"]:
                continue
            if r["stage"] == "regular":
                s = reg[(p["id"], r["team"])][r["season"]]
                s[0] += 1
                s[1] += p["score"]
            elif r["stage"] == "playoffs":
                po.add((p["id"], r["team"], r["season"]))
    return reg, po


def side(assets, team, season, reg, po, champs):
    players = [a for a in assets if a.get("kind") == "player"]
    n = pts = 0
    titles = set()
    for a in players:
        for y, (k, v) in reg.get((a["id"], team), {}).items():
            if y >= season:
                n += k
                pts += v
        titles |= {y for y in range(season, LAST_SEASON + 1) if champs.get(y) == team and (a["id"], team, y) in po}
    return {"players": "; ".join(a["label"] for a in players), "picks": len(assets) - len(players),
            "starts": n, "points": round(pts, 1), "titles": "; ".join(map(str, sorted(titles)))}


def main():
    reg, po = starts()
    champs = {int(k): v["champion"] for k, v in json.load(open(f"{BASE}/champions.json")).items()}
    out = []
    for t in json.load(open(f"{BASE}/trades.json")):
        if t["season"] < FIRST or not t.get("assets_known"):
            continue
        # each side is what the team received: team_a got b_gave, team_b got a_gave
        a = side(t["b_gave"], t["team_a"], t["season"], reg, po, champs)
        b = side(t["a_gave"], t["team_b"], t["season"], reg, po, champs)
        out.append({"season": t["season"], "date": t["date"], "team_a": t["team_a"], "team_b": t["team_b"],
                    **{f"a_got_{k}": v for k, v in a.items()}, **{f"b_got_{k}": v for k, v in b.items()}})
    cols = list(out[0])
    with open(f"{BASE}/datasets/trade_value.csv", "w", newline="") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(out)
    print(f"{len(out)} trades")


if __name__ == "__main__":
    main()
