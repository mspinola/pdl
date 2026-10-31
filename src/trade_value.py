"""Trade value: what each side of a trade got out of it, 2008 on, followed down the trade tree.

For every trade from 2008 (trades.json, MFL era, where lineups exist), the
regular-season points each team got from what it received, for as long as it
held it. An asset traded on is followed: the team is credited with a share of
whatever came back, and that is followed in turn, so a trade's value includes
the trades it made possible. When a team sends several assets in one deal, each
carries an equal share of the return. A drop ends the trail.

A draft pick is followed until it is used, then becomes the player taken with
it: the draft results name the slot (this season's picks), and a future pick
is found by its original owner's slot. A pick not yet made
counts nothing and is noted ("pending").

Starts are placed in time by the Sunday of their NFL week, so a player counts
for the team that held him that week. A title is credited to a side when one of
its assets started a championship playoff game for the team that season.

The direct_ columns are the same measures without following anything traded on.
To judge a trade from one side, credit that side with its tree (what it made of
what it got) and the other side with its direct value: the other team's later
trades are its own doing, not this one's.

    python3 src/trade_value.py      # datasets/trade_value.csv
"""
import csv, json, math, os, sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import identities as I
import weekly
from fetch_mfl import LAST_SEASON

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIRST = weekly.FIRST_RELIABLE
ET = ZoneInfo("America/New_York")


def sunday(season, week):
    """The Sunday of an NFL week, as a timestamp: week 1 is the Sunday after Labor Day."""
    sept1 = date(season, 9, 1)
    labor = sept1 + timedelta(days=(7 - sept1.weekday()) % 7)
    d = labor + timedelta(days=6 + 7 * (week - 1))
    return datetime(d.year, d.month, d.day, 13, tzinfo=ET).timestamp()


def starts():
    """(player id, team) -> [(timestamp, season, stage, points)] for every start."""
    out = defaultdict(list)
    for r in weekly.seasons(FIRST, LAST_SEASON):
        ts = sunday(r["season"], r["week"])
        for p in r["players"]:
            if p["started"]:
                out[(p["id"], r["team"])].append((ts, r["season"], r["stage"], p["score"]))
    return out


def drafts():
    """(season, round, pick) -> (pick, player id, team that made it, timestamp), and the same keyed by
    (season, round, original owner). The draft is linear, so a slot belongs to the same team in every
    round: its original owner is the team that picks there most often."""
    slots = I.slot_index()
    by_slot, by_owner = {}, {}
    for y in range(FIRST, LAST_SEASON + 1):
        path = f"{BASE}/mfl_archive/{y}/draft_results.json"
        if not os.path.exists(path):
            continue
        picks = json.load(open(path)).get("draftResults", {}).get("draftUnit", {}).get("draftPick", [])
        picks = [p for p in (picks if isinstance(picks, list) else [picks]) if p.get("round") and p.get("pick")]
        owner = defaultdict(Counter)
        for p in picks:
            owner[int(p["pick"])][p["franchise"]] += 1
        for p in picks:
            if not p.get("player"):
                continue
            r, k = int(p["round"]), int(p["pick"])
            drafter = I.label_for(slots[(y, p["franchise"])], y) if (y, p["franchise"]) in slots else None
            by_slot[(y, r, k)] = (k, p["player"], drafter, float(p.get("timestamp") or 0))
            orig = owner[k].most_common(1)[0][0]
            if (y, orig) in slots:
                by_owner[(y, r, slots[(y, orig)])] = by_slot[(y, r, k)]
    return by_slot, by_owner, slots


class Val:
    def __init__(self):
        self.points, self.starts, self.titles, self.pending, self.flips = 0.0, 0.0, set(), 0, []

    def add(self, o, share=1.0):
        self.points += o.points * share
        self.starts += o.starts * share
        self.titles |= o.titles
        self.pending += o.pending
        self.flips += o.flips


class Trees:
    def __init__(self, trades):
        self.trades = trades
        self.starts = starts()
        self.by_slot, self.by_owner, self.slots = drafts()
        self.champs = {int(k): v["champion"] for k, v in json.load(open(f"{BASE}/champions.json")).items()}
        self.gave = defaultdict(list)    # (team, asset key) -> [(timestamp, trade index)]
        for i, t in enumerate(trades):
            for team, assets in ((t["team_a"], t["a_gave"]), (t["team_b"], t["b_gave"])):
                for a in assets:
                    self.gave[(team, self.key(a, t["season"]))].append((t["timestamp"], i))
        self.drops = defaultdict(list)   # (team, player id) -> [timestamp]
        for m in json.load(open(f"{BASE}/transactions.json")):
            if m["action"] == "drop" and m.get("player_id") and m.get("when"):
                self.drops[(m["team"], m["player_id"])].append(datetime.fromisoformat(m["when"]).timestamp())
        self.memo = {}

    def key(self, a, season):
        if a["kind"] == "player":
            return ("p", a["id"])
        if a.get("current_year"):
            return ("k", season, a["round"], a["pick"])
        origin = self.slots.get((season, a.get("origin_franchise")))
        hit = self.by_owner.get((a["year"], a["round"], origin))
        return ("k", a["year"], a["round"], hit[0]) if hit else ("f", a["year"], a["round"], origin)

    def label(self, a, season):
        """A player's name, or a pick as "2018 R1 P04=<player id>" once it is used."""
        k = self.key(a, season)
        if k[0] == "p":
            return a["label"]
        if k[0] == "k" and k[1:] in self.by_slot:
            return f"{k[1]} R{k[2]} P{k[3]:02d}={self.by_slot[k[1:]][1]}"
        return f"{k[1]} R{k[2]}"

    def side(self, team, assets, season, ts, follow=True):
        v = Val()
        for a in assets:
            v.add(self.value(team, self.key(a, season), ts, follow))
        return v

    def value(self, team, key, t_in, follow=True):
        out = next(((ts, i) for ts, i in sorted(self.gave.get((team, key), [])) if ts > t_in), None) if follow else None
        t_out = out[0] if out else math.inf
        v = Val()
        if key[0] == "p":
            drop = next((ts for ts in sorted(self.drops.get((team, key[1]), [])) if ts > t_in), math.inf)
            for ts, season, stage, pts in self.starts.get((key[1], team), []):
                if t_in < ts < min(t_out, drop):
                    if stage == "regular":
                        v.points += pts
                        v.starts += 1
                    elif stage == "playoffs" and self.champs.get(season) == team:
                        v.titles.add(season)
            if out and t_out < drop:
                v.add(*self.flip(team, out[1]))
        elif key[0] == "k" and key[1:] in self.by_slot:
            _, pid, drafter, dts = self.by_slot[key[1:]]
            if out and t_out < dts:
                v.add(*self.flip(team, out[1]))
            elif drafter == team:
                v.add(self.value(team, ("p", pid), dts, follow))
        elif out:
            v.add(*self.flip(team, out[1]))
        else:
            v.pending += 1
        return v

    def flip(self, team, i):
        """What a team got back for the assets it sent in trade i, followed on, and the share each sent asset carries."""
        if (team, i) not in self.memo:
            t = self.trades[i]
            sent, got = (t["a_gave"], t["b_gave"]) if t["team_a"] == team else (t["b_gave"], t["a_gave"])
            v = self.side(team, got, t["season"], t["timestamp"])
            v.flips = [{"date": t["date"], "team": team, "to": t["team_b"] if t["team_a"] == team else t["team_a"],
                        "sent": [self.label(a, t["season"]) for a in sent],
                        "got": [self.label(a, t["season"]) for a in got]}] + v.flips
            self.memo[(team, i)] = (v, 1 / max(1, len(sent)))
        return self.memo[(team, i)]


def main():
    trades = [t for t in json.load(open(f"{BASE}/trades.json"))
              if t["season"] >= FIRST and t.get("assets_known") and not t.get("incomplete")]
    tree = Trees(trades)
    out = []
    for t in trades:
        row = {"season": t["season"], "date": t["date"], "team_a": t["team_a"], "team_b": t["team_b"]}
        # each side is what the team received: team_a got b_gave, team_b got a_gave
        for s, team, got in (("a", t["team_a"], t["b_gave"]), ("b", t["team_b"], t["a_gave"])):
            v = tree.side(team, got, t["season"], t["timestamp"])
            direct = tree.side(team, got, t["season"], t["timestamp"], follow=False)
            row.update({f"{s}_got_players": "; ".join(a["label"] for a in got if a["kind"] == "player"),
                        f"{s}_got_picks": "; ".join(tree.label(a, t["season"]) for a in got if a["kind"] == "pick"),
                        f"{s}_got_pending": v.pending, f"{s}_got_starts": round(v.starts, 1), f"{s}_got_points": round(v.points, 1),
                        f"{s}_got_direct_starts": round(direct.starts), f"{s}_got_direct_points": round(direct.points, 1),
                        f"{s}_got_direct_titles": "; ".join(map(str, sorted(direct.titles))),
                        f"{s}_got_titles": "; ".join(map(str, sorted(v.titles))), f"{s}_got_flips": json.dumps(v.flips)})
        out.append(row)
    with open(f"{BASE}/datasets/trade_value.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(f"{len(out)} trades")


if __name__ == "__main__":
    main()
