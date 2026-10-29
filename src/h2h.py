"""Head-to-head records, team records and championships for the PDL.

Games come from two sources, as trades do: MyFantasyLeague's weekly schedule
for 2003 to 2026 (`results.py`) and the league's archive schedule pages for
2000 to 2002 (`archive_games.py`). Both carry every score, so unlike the trade
data these two halves are directly comparable and are pooled.

**Points are indexed, never compared raw.** League scoring is not stable: it
drifts from 66 points a team-game in 2000 to 78 by 2017, then jumps to 116 in
2018 on a scoring change and holds there. So a team's points are expressed
against the league average of the seasons it actually played, where 100 is
average. The jump lands in 2018, the same season the one franchise changed
hands, which is exactly why raw points would make the new owner look far
better than the old one for no footballing reason.
"""
import json, os, sys, csv, collections, itertools

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import identities as I
import results as R
import archive_games as AG

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f"{BASE}/datasets"


def all_games():
    games = AG.stage_games() + R.games()
    games.sort(key=lambda g: (g["season"], g["week"]))
    return games


def season_scoring(games):
    """Average points per team-game, per season."""
    acc = collections.defaultdict(list)
    for g in games:
        acc[g["season"]] += [g["score_a"], g["score_b"]]
    return {s: sum(v) / len(v) for s, v in acc.items()}


def team_totals(games, stage=None):
    avg = season_scoring(games)
    t = collections.defaultdict(lambda: collections.Counter())
    for g in games:
        if stage and g["stage"] != stage:
            continue
        base = avg[g["season"]]
        for me, mine, theirs, res in (
            (g["team_a"], g["score_a"], g["score_b"], g["result_a"]),
            (g["team_b"], g["score_b"], g["score_a"],
             "W" if g["result_a"] == "L" else "L" if g["result_a"] == "W" else "T"),
        ):
            r = t[me]
            r["games"] += 1
            r["pts_for"] += mine
            r["pts_against"] += theirs
            r["rel_for"] += mine / base
            r["rel_against"] += theirs / base
            r["wins" if res == "W" else "losses" if res == "L" else "ties"] += 1
    return t


def pair_records(games):
    rec = collections.defaultdict(lambda: collections.Counter())
    for g in games:
        a, b = g["team_a"], g["team_b"]
        key = tuple(sorted((a, b)))
        first = key[0]
        r = rec[key]
        r["games"] += 1
        r["pts_a" if first == a else "pts_b"] += g["score_a"]
        r["pts_b" if first == a else "pts_a"] += g["score_b"]
        if g["result_a"] == "T":
            r["ties"] += 1
        else:
            winner = a if g["result_a"] == "W" else b
            r["wins_a" if winner == first else "wins_b"] += 1
    return rec


def write(name, header, rows):
    with open(f"{OUT}/{name}", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  {name}: {len(rows)} rows, {os.path.getsize(OUT + '/' + name) / 1024:.1f} KB")


def main():
    games = all_games()
    json.dump(games, open(f"{BASE}/games.json", "w"))
    ids = I.build()
    owners = sorted(ids)
    tenure = {o: set(ids[o]["seasons"]) for o in owners}
    avg = season_scoring(games)
    tot = team_totals(games)
    post = team_totals(games, stage="postseason")
    champs = R.champions()
    titles = collections.Counter(v["champion"] for v in champs.values())

    print(f"{len(games)} games, {min(avg)}-{max(avg)}")
    w = sum(r["wins"] for r in tot.values())
    l = sum(r["losses"] for r in tot.values())
    ti = sum(r["ties"] for r in tot.values())
    print(f"  wins {w} = losses {l}, ties {ti}: "
          f"{'ok' if w == l and w + l + ti == 2 * len(games) else 'MISMATCH'}")

    print("\ndatasets:")
    rows = []
    for o in owners:
        r = tot[o]
        g = r["games"]
        if not g:
            continue
        p = post[o]
        rows.append([
            o, len(tenure[o]), g, r["wins"], r["losses"], r["ties"],
            round((r["wins"] + 0.5 * r["ties"]) / g, 3),
            round(100 * r["rel_for"] / g, 1),
            round(100 * r["rel_against"] / g, 1),
            titles[o], p["games"], p["wins"],
            min(tenure[o]), max(tenure[o]),
        ])
    write("team_records.csv",
          ["owner", "seasons", "games", "wins", "losses", "ties", "win_pct",
           "points_index", "points_against_index", "titles",
           "postseason_games", "postseason_wins", "first_season", "last_season"],
          sorted(rows, key=lambda r: -r[6]))

    rec = pair_records(games)
    pm = []
    for a, b in itertools.combinations(owners, 2):
        r = rec.get((a, b), collections.Counter())
        shared = len(tenure[a] & tenure[b])
        pm.append([a, b, r["games"], r["wins_a"], r["wins_b"], r["ties"],
                   round(r["pts_a"], 1), round(r["pts_b"], 1), shared,
                   "yes" if shared else "no"])
    write("head_to_head.csv",
          ["owner_a", "owner_b", "games", "a_wins", "b_wins", "ties",
           "a_points", "b_points", "shared_seasons", "could_meet"],
          sorted(pm, key=lambda r: -r[2]))

    write("champions.csv", ["season", "champion", "source"],
          [[v["season"], v["champion"], v["source"]]
           for v in sorted(champs.values(), key=lambda v: -v["season"])])

    write("season_scoring.csv", ["season", "avg_points_per_team_game", "games"],
          [[s, round(avg[s], 1), sum(1 for g in games if g["season"] == s)]
           for s in sorted(avg)])

    print(f"\n{'team':<22}{'G':>5}{'W':>5}{'L':>4}{'T':>4}{'win%':>7}{'pts idx':>9}{'titles':>8}")
    for r in sorted(rows, key=lambda r: -r[6]):
        print(f"{r[0]:<22}{r[2]:>5}{r[3]:>5}{r[4]:>4}{r[5]:>4}{r[6]:>7.3f}{r[7]:>9.1f}{r[9]:>8}")

    print("\nmost lopsided head-to-head, 12+ games:")
    big = [(max(r[3], r[4]) / r[2], r) for r in pm if r[2] >= 12]
    big.sort(reverse=True)
    for pct, r in big[:8]:
        hi, lo = (r[0], r[1]) if r[3] >= r[4] else (r[1], r[0])
        print(f"  {hi} leads {lo} {max(r[3], r[4])}-{min(r[3], r[4])}"
              f"{'-' + str(r[5]) if r[5] else ''}  ({pct:.0%} of {r[2]})")

    print("\nclosest rivalries, 20+ games:")
    close = [(abs(r[3] - r[4]) / r[2], r) for r in pm if r[2] >= 20]
    close.sort()
    for _, r in close[:6]:
        print(f"  {r[0]} {r[3]}-{r[4]}{'-' + str(r[5]) if r[5] else ''} {r[1]}"
              f"  ({r[2]} games)")

    print("\ntrading activity against success:")
    act = {row["owner"]: row for row in csv.DictReader(open(f"{OUT}/owner_activity.csv"))}
    pairs = []
    for r in rows:
        a = act.get(r[0])
        if a:
            pairs.append((float(a["per_season"]), r[6], r[9], r[0]))
    pairs.sort(reverse=True)
    print(f"  {'team':<22}{'deals/season':>13}{'win%':>8}{'titles':>8}")
    for rate, pct, tl, name in pairs:
        print(f"  {name:<22}{rate:>13.2f}{pct:>8.3f}{tl:>8}")


if __name__ == "__main__":
    main()
