"""Export one JSON bundle plus the dashboard's dataset CSVs."""
import json, os, csv, collections, itertools

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f"{BASE}/datasets"
os.makedirs(OUT, exist_ok=True)

T = json.load(open(f"{BASE}/trades.json"))
IDS = json.load(open(f"{BASE}/identities.json"))
OWNERS = sorted(IDS)
SEASONS = sorted({t["season"] for t in T})
MFL = [t for t in T if t["source"] == "mfl"]
tenure = {o: set(IDS[o]["seasons"]) for o in OWNERS}

MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def write(name, header, rows):
    with open(f"{OUT}/{name}", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  {name}: {len(rows)} rows, {os.path.getsize(OUT + '/' + name) / 1024:.1f} KB")


cnt = collections.Counter()
for t in T:
    cnt[t["team_a"]] += 1
    cnt[t["team_b"]] += 1

pair = collections.Counter()
for t in T:
    pair[tuple(sorted((t["team_a"], t["team_b"])))] += 1

flow = {o: dict(players_out=0, picks_out=0, players_in=0, picks_in=0) for o in OWNERS}
for t in MFL:
    for me, other, gave in ((t["team_a"], t["team_b"], t["a_gave"]),
                            (t["team_b"], t["team_a"], t["b_gave"])):
        for a in gave:
            k = "players" if a["kind"] == "player" else "picks"
            flow[me][f"{k}_out"] += 1
            flow[other][f"{k}_in"] += 1

owners_rows, owners_json = [], []
for o in OWNERS:
    partners = collections.Counter()
    for t in T:
        if t["team_a"] == o:
            partners[t["team_b"]] += 1
        elif t["team_b"] == o:
            partners[t["team_a"]] += 1
    top, tn = partners.most_common(1)[0] if partners else ("", 0)
    yrs = len(tenure[o])
    avail = sum(1 for x in OWNERS if x != o and tenure[o] & tenure[x])
    active = len({t["season"] for t in T if o in (t["team_a"], t["team_b"])})
    f = flow[o]
    row = dict(
        owner=o, trades=cnt[o], seasons=yrs,
        per_season=round(cnt[o] / yrs, 2),
        seasons_with_a_trade=active, distinct_partners=len(partners),
        possible_partners=avail, top_partner=top, top_partner_trades=tn,
        first_season=IDS[o]["first_season"], last_season=IDS[o]["last_season"],
        net_picks=f["picks_in"] - f["picks_out"], **f,
    )
    owners_rows.append([row[k] for k in (
        "owner", "trades", "seasons", "per_season", "seasons_with_a_trade",
        "distinct_partners", "possible_partners", "top_partner", "top_partner_trades",
        "players_out", "players_in", "picks_out", "picks_in", "net_picks",
        "first_season", "last_season")])
    owners_json.append({**row, "partners": dict(partners), "note": IDS[o]["note"]})

print("datasets:")
write("owner_activity.csv",
      ["owner", "trades", "seasons", "per_season", "seasons_with_a_trade",
       "distinct_partners", "possible_partners", "top_partner", "top_partner_trades",
       "players_out", "players_in", "picks_out", "picks_in", "net_picks",
       "first_season", "last_season"],
      sorted(owners_rows, key=lambda r: -r[3]))

src_of = {y: ("archive" if {t["source"] for t in T if t["season"] == y} == {"archive"}
              else "MFL") for y in SEASONS}
write("season_volume.csv", ["season", "trades", "source"],
      [[y, sum(1 for t in T if t["season"] == y), src_of[y]] for y in SEASONS])

pm = []
for a, b in itertools.combinations(OWNERS, 2):
    shared = len(tenure[a] & tenure[b])
    pm.append([a, b, pair[(a, b)], shared, "yes" if shared else "no"])
write("pair_matrix.csv",
      ["owner_a", "owner_b", "trades", "shared_seasons", "could_trade"],
      sorted(pm, key=lambda r: -r[2]))

write("monthly.csv", ["month_num", "month", "trades"],
      [[m, MONTHS[m], sum(1 for t in MFL if int(t["date"][5:7]) == m)] for m in range(1, 13)])

log = sorted(T, key=lambda x: (x["season"], x["timestamp"]), reverse=True)
write("trade_log.csv",
      ["trade_id", "season", "date", "owner_a", "a_gave", "owner_b", "b_gave",
       "assets", "source", "detail"],
      [[f"T{i:03d}", t["season"],
        t["date"] if t["date_precision"] == "day" else "",
        t["team_a"], "; ".join(a["label"] for a in t["a_gave"]),
        t["team_b"], "; ".join(a["label"] for a in t["b_gave"]),
        len(t["a_gave"]) + len(t["b_gave"]),
        t["source"], t.get("raw", "")]
       for i, t in enumerate(log, start=1)])

players = sum(1 for t in MFL for a in t["a_gave"] + t["b_gave"] if a["kind"] == "player")
picks = sum(1 for t in MFL for a in t["a_gave"] + t["b_gave"] if a["kind"] == "pick")
bundle = {
    "meta": {
        "league": "PDL",
        "seasons": f"{min(SEASONS)}-{max(SEASONS)}",
        "trades": len(T),
        "trades_mfl": len(MFL),
        "trades_archive": len(T) - len(MFL),
        "owners": len(OWNERS),
        "players_moved": players,
        "picks_moved": picks,
        "incomplete_records": sum(1 for t in MFL if t["incomplete"]),
        "possible_pairings": sum(1 for a, b in itertools.combinations(OWNERS, 2)
                                 if tenure[a] & tenure[b]),
    },
    "owners": owners_json,
    "identities": IDS,
    "seasons": [{"season": y, "trades": sum(1 for t in T if t["season"] == y),
                 "source": src_of[y]} for y in SEASONS],
    "pairs": [{"a": a, "b": b, "trades": pair[(a, b)],
               "shared_seasons": len(tenure[a] & tenure[b])}
              for a, b in itertools.combinations(OWNERS, 2)],
    "trades": T,
}
json.dump(bundle, open(f"{BASE}/pdl_trades_bundle.json", "w"), indent=1)
print(f"\nbundle: {os.path.getsize(f'{BASE}/pdl_trades_bundle.json') // 1024} KB")
print(f"  {len(T)} trades, {len(OWNERS)} owners, {players} players + {picks} picks")
