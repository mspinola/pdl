"""Who works the waiver wire: stats from every add and drop since 2000.

Reads transactions.json (src/transactions.py) and, for the value of pickups,
the weekly lineups in mfl_archive/<season>/weeks/. Writes:

    datasets/transaction_owners.csv    per owner: claims, pickups, timing, positions, value
    datasets/transaction_seasons.csv   per season: volume, the waiver and free agent split
    datasets/best_pickups.csv          the pickups that started most for the team that added them
    docs/transactions.md               the report

    python3 src/transactions_analysis.py

Definitions:

- an add is one player added, whatever he was added for. A claim is an add
  through the weekly waiver run, a pickup an add from the free agent pool after
  it (first come first served, from 2008). Before 2008 every add was a claim.
- rates are per season the owner was in the league, so a franchise that joined
  in 2001 or changed hands in 2018 is not penalised for missing seasons.
- pickup value (2008 on, where MFL kept lineups): the points a player scored in
  the starting lineup of the team that added him that season, after it added
  him. As a share of the team's starting points it compares across the 2018
  scoring change, which raised points a game by half.
"""
import csv, json, os, sys, statistics
from collections import Counter, defaultdict
import datetime as dt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import identities as I
import weekly
from fetch_mfl import LAST_SEASON

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE = f"{BASE}/mfl_archive"
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def as_list(x):
    return x if isinstance(x, list) else [x] if x else []


def load_moves():
    moves = json.load(open(f"{BASE}/transactions.json"))
    for m in moves:
        m["when"] = dt.datetime.fromisoformat(m["when"]) if m["when"] else None
    return moves


def regular_weeks(season):
    """Weeks of the regular season: through 13, through 14 from 2021."""
    return 14 if season >= 2021 else 13


def pickup_value(moves, slots):
    """Points pickups scored in their new team's lineup, 2008 on."""
    adds = defaultdict(list)   # (season, team, player_id) -> weeks added
    for m in moves:
        if m["source"] == "mfl" and m["action"] == "add" and m["channel"] in ("waiver", "free_agent"):
            adds[(m["season"], m["team"], m["player_id"])].append((m["week"], m["channel"], m["player"], m["position"]))
    team_pts = Counter()       # (season, team) -> starting points, regular season
    from_pickups = Counter()
    by_channel = Counter()
    player_rows = defaultdict(lambda: {"starts": 0, "points": 0.0, "value": 0.0})
    covered = set()
    rows = weekly.seasons()
    averages = weekly.starter_averages(rows)
    for r in rows:
        if r["stage"] != "regular":
            continue
        season, team, week = r["season"], r["team"], r["week"]
        covered.add(season)
        for p in r["players"]:
            pid, score = p["id"], p["score"]
            if True:
                if not p["started"]:
                    continue
                team_pts[(season, team)] += score
                got = [a for a in adds.get((season, team, pid), []) if a[0] <= week]
                if got:
                    wk, channel, name, pos = got[-1]
                    from_pickups[(season, team)] += score
                    by_channel[channel] += score
                    row = player_rows[(season, team, pid)]
                    row.update(name=name, position=pos, channel=channel, week_added=wk)
                    row["starts"] += 1
                    row["points"] += score
                    row["value"] = row.get("value", 0.0) + weekly.over_average(score, season, pos, averages)
    return team_pts, from_pickups, by_channel, player_rows, covered


def write_csv(name, header, rows):
    with open(f"{BASE}/datasets/{name}", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def pct(a, b):
    return 100.0 * a / b if b else 0.0


def main():
    moves = load_moves()
    idents = I.build()
    slots = I.slot_index()
    seasons_of = {k: set(v["seasons"]) for k, v in idents.items()}
    adds = [m for m in moves if m["action"] == "add" and m["channel"] in ("waiver", "free_agent")]
    drops = [m for m in moves if m["action"] == "drop"]
    complete = [y for y in range(2000, LAST_SEASON + 1) if y < LAST_SEASON]   # the season in progress is left out of rates

    team_pts, from_pk, by_channel, player_rows, covered = pickup_value(moves, slots)
    records = {r["owner"]: r for r in csv.DictReader(open(f"{BASE}/datasets/team_records.csv"))}

    owners = []
    for label in sorted(idents):
        mine = [m for m in adds if m["team"] == label]
        full = [y for y in seasons_of[label] if y in complete]
        modern = [y for y in full if y >= 2008]
        claims = [m for m in mine if m["channel"] == "waiver"]
        pickups = [m for m in mine if m["channel"] == "free_agent"]
        mod = [m for m in mine if m["season"] in modern]
        mod_pk = [m for m in mod if m["channel"] == "free_agent"]
        sunday = [m for m in mod_pk if m["when"] and m["when"].weekday() == 6]
        kdef = [m for m in mine if m["position"] in ("K", "Def")]
        in_full = [m for m in mine if m["season"] in full]
        val_seasons = [y for y in modern if y in covered]
        tp = sum(team_pts[(y, label)] for y in val_seasons)
        fp = sum(from_pk[(y, label)] for y in val_seasons)
        quiet = sorted(y for y in full if not any(m["season"] == y for m in mine))
        owners.append({
            "owner": label, "seasons": len(full),
            "adds": len(in_full), "adds_per_season": round(len(in_full) / len(full), 1) if full else 0,
            "claims": len([m for m in claims if m["season"] in full]),
            "pickups": len([m for m in pickups if m["season"] in full]),
            "adds_per_season_2008_on": round(len(mod) / len(modern), 1) if modern else 0,
            "pickup_share_2008_on": round(pct(len(mod_pk), len(mod))),
            "sunday_pickups_2008_on": len(sunday),
            "k_def_share": round(pct(len(kdef), len(mine))),
            "pickup_points_share": round(pct(fp, tp), 1) if tp else None,
            "seasons_without_an_add": len(quiet),
            "win_pct": float(records[label]["win_pct"]) if label in records else None,
            "points_index": float(records[label]["points_index"]) if label in records else None,
            "first_season": min(seasons_of[label]), "last_season": max(seasons_of[label]),
        })
    owners.sort(key=lambda r: -r["adds_per_season"])
    cols = list(owners[0])
    write_csv("transaction_owners.csv", cols, [[r[c] for c in cols] for r in owners])

    seasons = []
    for y in range(2000, LAST_SEASON + 1):
        a = [m for m in adds if m["season"] == y]
        teams = len({k for k, v in seasons_of.items() if y in v})
        pk = [m for m in a if m["channel"] == "free_agent"]
        seasons.append({"season": y, "teams": teams, "adds": len(a), "adds_per_team": round(len(a) / teams, 1),
                        "claims": len(a) - len(pk), "pickups": len(pk),
                        "pickup_share": round(pct(len(pk), len(a))) if y >= 2008 else None,
                        "k_def_share": round(pct(sum(m["position"] in ("K", "Def") for m in a), len(a))),
                        "pickup_points_share": round(pct(sum(from_pk[(y, t)] for t in seasons_of if y in seasons_of[t]),
                                                         sum(team_pts[(y, t)] for t in seasons_of if y in seasons_of[t])), 1)
                        if y in covered else None,
                        "in_progress": y == LAST_SEASON})
    cols = list(seasons[0])
    write_csv("transaction_seasons.csv", cols, [[r[c] for c in cols] for r in seasons])

    best = sorted(({"season": s, "team": t, **v} for (s, t, pid), v in player_rows.items()),
                  key=lambda r: -r["value"])
    share_of = {k: v for k, v in team_pts.items()}
    best_rows = [[r["season"], r["team"], r["name"], r["position"], r["channel"], r["week_added"], r["starts"],
                  round(r["points"], 1), round(pct(r["points"], share_of[(r["season"], r["team"])]), 1),
                  round(r["value"], 1)] for r in best]
    write_csv("best_pickups.csv", ["season", "team", "player", "position", "channel", "week_added", "starts",
                                   "points_started", "share_of_team_starting_points", "value_over_average"], best_rows)

    report(owners, seasons, best_rows, adds, drops, moves, by_channel, covered)
    print(f"wrote datasets/transaction_owners.csv, transaction_seasons.csv, best_pickups.csv and docs/transactions.md")
    print(f"  pickup value covers {len(covered)} seasons: {min(covered) if covered else '-'} to {max(covered) if covered else '-'}")
    return 0


def report(owners, seasons, best_rows, adds, drops, moves, by_channel, covered):
    L = ["# Who works the waiver wire", "",
         "Generated by `python3 src/transactions_analysis.py` from every add and drop since 2000",
         "(`transactions.json`). Owners are reported by team, as everywhere in this project.",
         f"Rates use completed seasons only, so {LAST_SEASON}, still in progress, is left out of them.", ""]
    done = [s for s in seasons if not s["in_progress"]]
    total = sum(s["adds"] for s in done)
    L += ["## The league", "",
          f"{total:,} players added in {len(done)} completed seasons, about "
          f"{statistics.mean(s['adds_per_team'] for s in done):.0f} per team per season, rising from "
          f"{statistics.mean(s['adds_per_team'] for s in done if s['season'] <= 2002):.0f} in 2000 to 2002 to "
          f"{statistics.mean(s['adds_per_team'] for s in done if s['season'] >= 2021):.0f} since 2021.", ""]
    L += ["| Season | Teams | Adds | Per team | Waiver claims | Free agent pickups | Pickup share | K and Def share | Starting points from pickups |",
          "|---|---|---|---|---|---|---|---|---|"]
    for s in seasons:
        L.append(f"| {s['season']}{' (in progress)' if s['in_progress'] else ''} | {s['teams']} | {s['adds']} | {s['adds_per_team']} | "
                 f"{s['claims']} | {s['pickups'] if s['season'] >= 2008 else '-'} | "
                 f"{str(s['pickup_share']) + '%' if s['pickup_share'] is not None else '-'} | {s['k_def_share']}% | "
                 f"{str(s['pickup_points_share']) + '%' if s['pickup_points_share'] is not None else '-'} |")
    L += ["", "Before 2008 every add went through waivers, so there are no pickups to count. From 2008 a dash in the",
          "last column means MFL kept no lineups that season.", ""]

    def table(title, rows, key, fmt, n=None, rev=True, note=""):
        rs = sorted([r for r in rows if r[key] is not None], key=lambda r: r[key], reverse=rev)[:n]
        out = [f"### {title}", ""] + ([note, ""] if note else []) + ["| | Owner | Value |", "|---|---|---|"]
        out += [f"| {i} | {r['owner']} | {fmt(r[key])} |" for i, r in enumerate(rs, 1)]
        return out + [""]

    L += ["## Owners", "",
          "Every owner identity, ranked on each measure. The full table is `datasets/transaction_owners.csv`.", ""]
    L += table("Adds per season, all seasons", owners, "adds_per_season", lambda v: f"{v}")
    L += table("Adds per season since 2008", owners, "adds_per_season_2008_on", lambda v: f"{v}",
               note="The era with free agency. Every owner played all of it except the one franchise that changed "
                    "hands: Bunchalosers to 2017, Couchfire from 2018.")
    L += table("Share of adds that are free agent pickups, since 2008", owners, "pickup_share_2008_on", lambda v: f"{v}%",
               note="High: adds from the first-come pool after the waiver run, which leaves waiver priority alone. "
                    "Low: adds through the run itself, where a successful claim drops the team to the bottom of the order.")
    L += table("Sunday pickups since 2008", owners, "sunday_pickups_2008_on", lambda v: f"{v}",
               note="Game-day adds, usually a kicker or defense replacing one ruled out.")
    L += table("Share of adds that are kickers or defenses", owners, "k_def_share", lambda v: f"{v}%")
    L += table("Share of starting points from pickups", owners, "pickup_points_share", lambda v: f"{v}%",
               note=f"Seasons {min(covered) if covered else ''} to {max(covered) if covered else ''}, regular season: "
                    "the points players a team added that season scored in its lineup.")
    L += table("Seasons without a single add", owners, "seasons_without_an_add", lambda v: f"{v}")

    # does it help?
    mod = [r for r in owners if r["adds_per_season_2008_on"] and r["win_pct"] is not None]
    if len(mod) > 4:
        r1 = statistics.correlation([r["adds_per_season_2008_on"] for r in mod], [r["win_pct"] for r in mod])
        r2 = statistics.correlation([r["adds_per_season_2008_on"] for r in mod], [r["points_index"] for r in mod])
        L += ["## Does working the wire help?", "",
              f"Across the {len(mod)} owners, adds per season since 2008 against career win rate: r = {r1:.2f}. "
              f"Against points scored (indexed to the era): r = {r2:.2f}. With this few owners, a correlation "
              "under about 0.5 in either direction is indistinguishable from none, and the arrow could run either "
              "way: a struggling team has more holes to fill.", ""]

    L += ["## The pickups that paid", "",
          "Players added during a season, ranked by what they gave the team that added them that season: points "
          "above the average starter at their position, counted in that season's average starts (regular season, "
          "2008 on). So +5 is five average starts' worth of points beyond a typical starter. Kickers and defenses "
          "are listed apart: a team that picks one up in week 1 and starts him all year shows many starts but "
          "little edge.", "",
          "| Season | Team | Player | Pos | How | Week added | Starts | Value over average | Share of team's starting points |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in [x for x in best_rows if x[3] not in ("K", "Def")][:20]:
        L.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {'claim' if r[4] == 'waiver' else 'pickup'} | {r[5]} | {r[6]} | {r[9]:+} | {r[8]}% |")
    L += ["", "Kickers and defenses:", "", "| Season | Team | Player | Pos | Starts | Value over average |", "|---|---|---|---|---|---|"]
    for r in [x for x in best_rows if x[3] in ("K", "Def")][:8]:
        L.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[6]} | {r[9]:+} |")
    L += ["", "## Notes on the data", "",
          "- 2000 to 2007 come from the league's own transaction pages, 2008 on from MyFantasyLeague's log.",
          "- MFL logged first-come pickups as waiver moves until 2016. They are separated by time: a claim carries "
          "the timestamp of the weekly waiver run. From 2017, when MFL logs the two apart, every claim sits at a run.",
          "- Weeks run Tuesday to Monday, so a Tuesday or Wednesday add counts toward the coming Thursday's week.",
          "- Couchfire's figures start in 2018 and Bunchalosers' end in 2017, the one change of owner.",
          "- Trades are in the trades analysis, not here. IR moves (2020 and 2026) are not counted as adds.", ""]
    with open(f"{BASE}/docs/transactions.md", "w") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    sys.exit(main())
