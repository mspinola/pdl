"""Trade value: what each side of a trade got out of it, 2008 on.

For every trade from 2008 (trades.json, MFL era, where lineups exist), the
regular-season starts and points each team got from the players it received,
from the trade's season on, for as long as it kept them. A draft pick is
scored as the player taken with it, for the team that received the pick: the
draft results name the slot (this season's picks) or the pick's original owner
(a future pick, "Pick traded from ..."). A pick flipped again before the draft
is counted ("flipped") rather than scored, and so is a pick not yet made
("pending"): either leaves the trade out of a ranking, since half its story is
another trade. Incomplete trade records are left out. A title is credited to a received player when he
started a championship playoff game for the team that season.

    python3 src/trade_value.py      # datasets/trade_value.csv
"""
import csv, json, os, re, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import identities as I
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


def drafts():
    """(season, round, pick) and (season, round, original owner) -> (pick, player id, team that made the pick)."""
    slots, names = I.slot_index(), {}
    by_slot, by_owner = {}, {}
    for y in range(FIRST, LAST_SEASON + 1):
        path = f"{BASE}/mfl_archive/{y}/draft_results.json"
        if not os.path.exists(path):
            continue
        names = {f["name"]: f["id"] for f in json.load(open(f"{BASE}/mfl_archive/{y}/league.json"))["league"]["franchises"]["franchise"]}
        picks = json.load(open(path)).get("draftResults", {}).get("draftUnit", {}).get("draftPick", [])
        for p in picks if isinstance(picks, list) else [picks]:
            if not (p.get("player") and p.get("round") and p.get("pick")):
                continue
            r, k = int(p["round"]), int(p["pick"])
            drafter = I.label_for(slots[(y, p["franchise"])], y) if (y, p["franchise"]) in slots else None
            by_slot[(y, r, k)] = (k, p["player"], drafter)
            m = re.search(r"Pick traded from (.+?)\.(\n|\]|$)", p.get("comments") or "")
            orig = names.get(m.group(1)) if m else p["franchise"]
            if orig and (y, orig) in slots:
                by_owner[(y, r, slots[(y, orig)])] = by_slot[(y, r, k)]
    return by_slot, by_owner, slots


def resolve(a, season, by_slot, by_owner, slots):
    """A traded pick -> (draft season, player id, label, team that made the pick), or None if it is not made yet."""
    if a.get("current_year"):
        y, (k, pid, drafter) = season, by_slot.get((season, a["round"], a["pick"]), (None, None, None))
    else:
        y = a["year"]
        k, pid, drafter = by_owner.get((y, a["round"], slots.get((season, a.get("origin_franchise")))), (None, None, None))
    return (y, pid, f"{y} R{a['round']} P{k:02d}", drafter) if pid else None


def side(assets, team, season, reg, po, champs, picks):
    players = [(season, a["id"], a["label"]) for a in assets if a.get("kind") == "player"]
    made, pending, flipped = [], 0, 0
    for a in assets:
        if a.get("kind") == "pick":
            r = resolve(a, season, *picks)
            if not r:
                pending += 1
            elif r[3] != team:
                flipped += 1
            else:
                made.append(r[:3])
    n = pts = 0
    titles = set()
    for y0, pid, _ in players + made:
        for y, (k, v) in reg.get((pid, team), {}).items():
            if y >= y0:
                n += k
                pts += v
        titles |= {y for y in range(y0, LAST_SEASON + 1) if champs.get(y) == team and (pid, team, y) in po}
    return {"players": "; ".join(lab for _, _, lab in players),
            "picks": "; ".join(f"{lab}={pid}" for _, pid, lab in made), "pending": pending, "flipped": flipped,
            "starts": n, "points": round(pts, 1), "titles": "; ".join(map(str, sorted(titles)))}


def main():
    reg, po = starts()
    picks = drafts()
    champs = {int(k): v["champion"] for k, v in json.load(open(f"{BASE}/champions.json")).items()}
    out = []
    for t in json.load(open(f"{BASE}/trades.json")):
        if t["season"] < FIRST or not t.get("assets_known") or t.get("incomplete"):
            continue
        # each side is what the team received: team_a got b_gave, team_b got a_gave
        a = side(t["b_gave"], t["team_a"], t["season"], reg, po, champs, picks)
        b = side(t["a_gave"], t["team_b"], t["season"], reg, po, champs, picks)
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
