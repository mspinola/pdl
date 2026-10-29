"""Trading-behaviour analytics for the PDL, 2000-2026."""
import json, os, sys, collections, itertools

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

T = json.load(open(f"{BASE}/trades.json"))
IDS = json.load(open(f"{BASE}/identities.json"))
OWNERS = sorted(IDS)
SEASONS = sorted({t["season"] for t in T})
MFL = [t for t in T if t["source"] == "mfl"]
MFL_SEASONS = sorted({t["season"] for t in MFL})

tenure = {o: set(IDS[o]["seasons"]) for o in OWNERS}


def h(s):
    print(f"\n{'=' * 70}\n{s}\n{'=' * 70}")


def sides(trades):
    c = collections.Counter()
    for t in trades:
        c[t["team_a"]] += 1
        c[t["team_b"]] += 1
    return c


h("1. TRADE VOLUME BY SEASON")
by_season = collections.Counter(t["season"] for t in T)
src = {y: {t["source"] for t in T if t["season"] == y} for y in SEASONS}
for y in SEASONS:
    n = by_season[y]
    tag = "archive" if src[y] == {"archive"} else "MFL"
    print(f"  {y}  {n:3d}  {'#' * n:<28} {tag}")
print(f"\n  {len(T)} trades over {len(SEASONS)} seasons")
print(f"  2000-2007 ({sum(by_season[y] for y in range(2000, 2008))} trades) is a hand-kept")
print("  archive, so read it as a floor. 2008-2026 is the MFL log and is complete.")

h("2. WHO TRADES, AND WHO DOES NOT")
cnt = sides(T)
active = {o: len({t["season"] for t in T if o in (t["team_a"], t["team_b"])}) for o in OWNERS}
print(f"  {'owner':<22}{'trades':>7}{'seasons':>9}{'per season':>12}{'yrs w/ a deal':>15}")
for o in sorted(OWNERS, key=lambda x: -cnt[x] / len(tenure[x])):
    yrs = len(tenure[o])
    print(f"  {o:<22}{cnt[o]:>7}{yrs:>9}{cnt[o] / yrs:>12.2f}"
          f"{active[o]:>11}/{yrs}")
print("\n  Rate per season is the fair comparison: the two expansion teams have 26")
print("  seasons, and the franchise that changed hands splits into two owners.")

h("3. THE ONE OWNER CHANGE")
for o in ("Bunchalosers", "Couchfire"):
    yrs = len(tenure[o])
    print(f"  {o:<16} {IDS[o]['first_season']}-{IDS[o]['last_season']}  "
          f"{cnt[o]:>3} trades over {yrs:>2} seasons = {cnt[o] / yrs:.2f}/season")
print("\n  Same franchise, same roster lineage, different owner. Roster overlap")
print("  cannot tell them apart, which is why the split is applied by hand.")

h("4. TRADE PARTNERS")
pair = collections.Counter()
for t in T:
    pair[tuple(sorted((t["team_a"], t["team_b"])))] += 1
possible = [p for p in itertools.combinations(OWNERS, 2) if tenure[p[0]] & tenure[p[1]]]
impossible = [p for p in itertools.combinations(OWNERS, 2) if not (tenure[p[0]] & tenure[p[1]])]
never = [p for p in possible if pair[p] == 0]
print("  most common partnerships:")
for (a, b), n in pair.most_common(12):
    shared = len(tenure[a] & tenure[b])
    print(f"   {n:3d}  {a} and {b}   ({n / shared:.2f} per shared season)")
print(f"\n  {len(possible)} pairings were possible, {len(possible) - len(never)} have traded, "
      f"{len(never)} never have")
print(f"  {len(impossible)} pairing could never happen: "
      f"{', '.join(a + ' and ' + b for a, b in impossible)}")
print("  (they are the same franchise under its two owners, never in the league together)")
print("\n  never traded with each other:")
for a, b in sorted(never, key=lambda p: -len(tenure[p[0]] & tenure[p[1]])):
    print(f"     {a} and {b}   ({len(tenure[a] & tenure[b])} shared seasons)")

h("5. PARTNER CONCENTRATION")
print(f"  {'owner':<22}{'partners':>10}{'of':>4}{'top partner':>26}{'share':>8}")
for o in sorted(OWNERS, key=lambda x: -cnt[x]):
    partners = collections.Counter()
    for t in T:
        if t["team_a"] == o:
            partners[t["team_b"]] += 1
        elif t["team_b"] == o:
            partners[t["team_a"]] += 1
    avail = sum(1 for x in OWNERS if x != o and tenure[o] & tenure[x])
    if not partners:
        continue
    top, tn = partners.most_common(1)[0]
    print(f"  {o:<22}{len(partners):>10}{avail:>4}{top + ' (' + str(tn) + ')':>26}"
          f"{tn / sum(partners.values()):>8.0%}")

h("6. WHAT GETS TRADED (MFL seasons only, 2008-2026)")
pl = sum(1 for t in MFL for a in t["a_gave"] + t["b_gave"] if a["kind"] == "player")
pk = sum(1 for t in MFL for a in t["a_gave"] + t["b_gave"] if a["kind"] == "pick")
inc = sum(1 for t in MFL if t["incomplete"])
print(f"  {pl} players and {pk} picks changed hands ({pk / (pl + pk):.0%} picks)")
print(f"  {inc} of {len(MFL)} MFL records name only one side's assets, so these")
print("  counts are a floor. The two franchises on those trades are still correct.")
print("  The 2000-2007 archive carries no structured assets, so it is excluded here.")
flow = {o: dict(po=0, ko=0, pi=0, ki=0) for o in OWNERS}
for t in MFL:
    for me, other, gave in ((t["team_a"], t["team_b"], t["a_gave"]),
                            (t["team_b"], t["team_a"], t["b_gave"])):
        for a in gave:
            if a["kind"] == "player":
                flow[me]["po"] += 1; flow[other]["pi"] += 1
            else:
                flow[me]["ko"] += 1; flow[other]["ki"] += 1
print(f"\n  {'owner':<22}{'plyr out':>9}{'plyr in':>9}{'pick out':>10}{'pick in':>9}{'net picks':>11}")
for o in sorted(OWNERS, key=lambda x: -(flow[x]["ki"] - flow[x]["ko"])):
    f = flow[o]
    if not any(f.values()):
        continue
    print(f"  {o:<22}{f['po']:>9}{f['pi']:>9}{f['ko']:>10}{f['ki']:>9}"
          f"{f['ki'] - f['ko']:>+11}")

h("7. WHEN TRADES HAPPEN (MFL seasons only, the archive has no dates)")
mon = collections.Counter(int(t["date"][5:7]) for t in MFL)
names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
for m in range(1, 13):
    print(f"  {names[m]}  {mon[m]:3d}  {'#' * mon[m]}")

h("8. SOURCES AND LIMITS")
print(f"  2000-2007: {len(T) - len(MFL)} trades from the league's GitHub archive")
print("    (pdl/history/trades.html), hand-written prose. Franchises parsed with")
print("    confidence; assets kept as the original sentence. A floor, not a count.")
print(f"  2008-2026: {len(MFL)} trades from the MyFantasyLeague export API.")
print("    MFL holds no transaction log for 2003-2006 and one record for 2007.")
print("    The archive's offseason sections are offset by a year, corrected on the")
print("    evidence that its 2007 offseason section is MFL's 2008 trades.")
print(f"  {sum(1 for t in MFL if t.get('merged_records'))} MFL deals were written as two records and are merged.")
