"""The wall of shame: records/shame.html, the records nobody wants.

Computed from the same games as the record book (records_page.real_games: the regular season and
the championship playoffs, not the toilet bowl) and the same datasets as the franchise pages. Game
and streak records include the season in progress. Season, playoff and franchise records use
finished seasons only. Each card's last line is a joke, and the only thing on it that is not a
number from the record.
"""
import os

import league_data as d
import records_page as R
from eggs import ordinal, playoff_games
from frame import E, num, page, record

link = R.team_link


def card(big, title, who, detail, quip):
    return (f"<article class='shame-card'><p class='shame-num'>{big}</p><h3>{E(title)}</h3><p class='shame-who'>{who}</p>"
            f"<p class='shame-detail'>{detail}</p><p class='shame-quip'>{E(quip)}</p></article>")


def season_link(y):
    return f"<a href='../seasons/{y}.html'>{y}</a>"


def names(teams):
    teams = [link(t) for t in teams]
    return teams[0] if len(teams) == 1 else ", ".join(teams[:-1]) + " and " + teams[-1]


def games_cards(games):
    scores = [(s, t, o, os_, g) for g in games for t, s, o, os_, _ in R.sides(g)]
    s, t, o, os_, g = min(scores, key=lambda x: x[0])
    out = [card(num(s), "Lowest score ever", link(t),
                f"{season_link(g['season'])}, week {g['week']}, against {link(o)} ({num(os_)}).",
                "Below zero. The lineup lost points just by showing up." if s < 0 else "A kicker alone would have done better.")]
    g = max(games, key=lambda g: abs(g["score_a"] - g["score_b"]))
    w, ws, l, ls = ((g["team_a"], g["score_a"], g["team_b"], g["score_b"]) if g["score_a"] > g["score_b"]
                    else (g["team_b"], g["score_b"], g["team_a"], g["score_a"]))
    out.append(card(num(ws - ls), "Biggest beating", link(l),
                    f"Lost to {link(w)} {num(ws)} to {num(ls)}, {season_link(g['season'])} week {g['week']}. The widest margin on record.",
                    "The margin alone would have won most weeks."))
    # the longest losing run, across seasons, as the record book counts it
    run, best, seq = 0, None, {}
    for g in sorted([g for g in d.games() if g["stage"] == "regular"], key=lambda g: (g["season"], g["week"])):
        for t, _, _, _, res in R.sides(g):
            n, start = seq.get(t, (0, None))
            seq[t] = (n + 1, start or (g["season"], g["week"])) if res == "L" else (0, None)
            if res == "L" and (best is None or seq[t][0] > best[0]):
                best = (seq[t][0], t, seq[t][1], (g["season"], g["week"]))
    n, t, start, end = best
    out.append(card(str(n), "Longest losing streak", link(t),
                    f"Regular-season losses in a row, {start[0]} week {start[1]} to {end[0]} week {end[1]}.",
                    f"{n} straight weeks. Longer than an NFL regular season."))
    return out


def seasons_cards(done):
    rows = [(y, r) for y in done for r in d.standings(y)]
    pct = lambda r: (r["w"] + 0.5 * r["t"]) / max(1, r["w"] + r["l"] + r["t"])
    low = min(pct(r) for _, r in rows)
    worst = sorted([(y, r) for y, r in rows if pct(r) == low], key=lambda x: x[0])
    out = [card(record(worst[0][1]["w"], worst[0][1]["l"], worst[0][1]["t"]), "Worst regular season",
                ", ".join(f"{link(r['team'])} ({season_link(y)})" for y, r in worst),
                "The fewest wins for the games played, in a finished season." + (f" It has happened {len(worst)} times." if len(worst) > 1 else ""),
                "One win. Somebody lost to them, too." if worst[0][1]["w"] == 1 else "Barely a win to show for it.")]
    missed = []
    for y in done:
        st = sorted(d.standings(y), key=lambda r: -r["pf"])
        missed += [(i + 1, y, r) for i, r in enumerate(st) if not r["playoffs"]]
    rank, y, r = min(missed, key=lambda x: (x[0], -x[2]["pf"]))
    out.append(card(f"{ordinal(rank)} in points", "Scored the most, stayed home" if rank == 1 else "Scored plenty, stayed home",
                    f"{link(r['team'])} ({season_link(y)})",
                    f"{record(r['w'], r['l'], r['t'])} with {num(r['pf'])} points, {ordinal(rank)} in the league, and no playoff spot.",
                    "The best offense in the league, watching the playoffs from the couch." if rank == 1 else "All those points, no playoffs."))
    y, r = min(rows, key=lambda x: x[1]["luck"] or 0)
    rank = sorted(d.standings(y), key=lambda x: -x["pf"]).index(r) + 1
    out.append(card(f"{r['luck']:+.1f}", "Unluckiest season", f"{link(r['team'])} ({season_link(y)})",
                    f"Wins against what its scoring was worth: {record(r['w'], r['l'], r['t'])} while {ordinal(rank)} in points.",
                    "The schedule had it out for them."))
    return out


def playoff_cards(done):
    out = []
    finals = [(d.final(y), y) for y in done if d.final(y)]
    f, y = min(finals, key=lambda x: min(x[0]["score_a"], x[0]["score_b"]))
    lose_a = f["score_a"] < f["score_b"]
    loser, ls, winner, ws = ((f["team_a"], f["score_a"], f["team_b"], f["score_b"]) if lose_a
                             else (f["team_b"], f["score_b"], f["team_a"], f["score_a"]))
    out.append(card(num(ls), "Lowest score in a title game", link(loser),
                    f"The {season_link(y)} final, lost to {link(winner)} {num(ws)} to {num(ls)}.",
                    "The biggest game of the year, and the offense stayed home."))
    games = [g for y in done for g in d.postseason(y)[0]]
    g = max(games, key=lambda g: abs(g["score_a"] - g["score_b"]))
    w, ws, l, ls = ((g["team_a"], g["score_a"], g["team_b"], g["score_b"]) if g["score_a"] > g["score_b"]
                    else (g["team_b"], g["score_b"], g["team_a"], g["score_a"]))
    out.append(card(num(ws), "Most points given up in a playoff game", link(l),
                    f"Lost to {link(w)} {num(ws)} to {num(ls)}, {season_link(g['season'])}. The widest playoff margin on record.",
                    "One-and-done, emphasis on done."))
    g = min(games, key=lambda g: abs(g["score_a"] - g["score_b"]))
    w, ws, l, ls = ((g["team_a"], g["score_a"], g["team_b"], g["score_b"]) if g["score_a"] > g["score_b"]
                    else (g["team_b"], g["score_b"], g["team_a"], g["score_a"]))
    seed = (d.seeds(g["season"]) or {}).get(l)
    champ = d.champions().get(g["season"]) == w
    out.append(card(num(ws - ls, 1), "Closest playoff loss", link(l),
                    f"Lost to {link(w)} {num(ws)} to {num(ls)}, {season_link(g['season'])}"
                    + (f", as the #{seed} seed" if seed else "") + (f". {link(w)} went on to win the title." if champ else "."),
                    "Closer than one missed extra point."))
    po = [r for r in d.lineup_losses() if r["stage"] == "playoffs" and int(r["season"]) in done]
    r = max(po, key=lambda r: float(r["best_lineup_margin"]))
    bench = float(r["best_possible"]) - float(r["score"])
    out.append(card(num(bench), "Most points left on the bench in a playoff loss", f"{link(r['team'])} ({season_link(r['season'])})",
                    f"Scored {num(r['score'])}, could have scored {num(r['best_possible'])}, lost to {link(r['opponent'])} "
                    f"{num(r['opponent_score'])} to {num(r['score'])}.",
                    "The winning lineup was right there, on the bench."))
    loss = max(((g, t) for g in games for t in (g["team_a"], g["team_b"])
                if (g["score_a"] < g["score_b"]) == (t == g["team_a"])),
               key=lambda x: min(x[0]["score_a"], x[0]["score_b"]))
    g, t = loss
    mine, theirs = (g["score_a"], g["score_b"]) if t == g["team_a"] else (g["score_b"], g["score_a"])
    opp = g["team_b"] if t == g["team_a"] else g["team_a"]
    out.append(card(num(mine), "Most points in a playoff loss", link(t),
                    f"Lost to {link(opp)} {num(theirs)} to {num(mine)}, {season_link(g['season'])}.",
                    "Any other week, that wins."))
    return out


def franchise_cards(done):
    out = []
    teams = d.identities()
    rows = []
    for t, v in teams.items():
        playoffs = [y for y in done if d.finish(y, t)]
        titles = [y for y in done if d.champions()[y] == t]
        lost = sum(not g["won"] for g in playoff_games(t))
        rows.append((t, v, playoffs, titles, lost))
    t, v, playoffs, titles, lost = max([x for x in rows if not x[3]], key=lambda x: len(x[2]))
    won = len(playoff_games(t)) - lost
    out.append(card(str(len(playoffs)), "Playoff trips, no title", link(t),
                    f"{len(playoffs)} trips to the playoffs, a {won}-{lost} playoff record and no championship.",
                    "Always invited, never the guest of honor."))
    never = sorted([(len([y for y in v["seasons"] if y in done]), t) for t, v, p, ti, _ in rows if not ti], reverse=True)
    most = never[0][0]
    out.append(card(str(len(never)), "Franchises without a title", names([t for _, t in never]),
                    f"The longest wait: {most} seasons, by {names([t for n, t in never if n == most])}.",
                    "Next year. Every year."))
    best = None
    for t, v, *_ in rows:
        run = 0
        for y in done:
            if y not in v["seasons"]:
                continue
            run = 0 if d.finish(y, t) else run + 1
            if run and (best is None or run > best[0]):
                best = (run, t, y - run + 1, y)
    n, t, a, b = best
    out.append(card(str(n), "Longest playoff drought", link(t), f"Seasons in a row without the playoffs, {a} to {b}.",
                    f"{n} straight Decembers on the couch."))
    luck = d.by_owner("luck_owners.csv")
    t = min(luck, key=lambda t: float(luck[t]["luck"]))
    out.append(card(f"{float(luck[t]['luck']):+.1f}", "Unluckiest franchise", link(t),
                    f"Wins against what its scoring was worth, over {luck[t]['seasons']} seasons.",
                    f"{abs(float(luck[t]['luck'])):.0f} wins the schedule took away. More than a full season's worth."
                    if abs(float(luck[t]["luck"])) > 13 else "The schedule has it out for them."))
    lo = d.by_owner("lineup_owners.csv")
    t = min(lo, key=lambda t: float(lo[t]["efficiency"]))
    out.append(card(f"{lo[t]['efficiency']}%", "Worst lineup setter", link(t),
                    f"The share of the best possible score it started, the lowest in the league ({lo[t]['seasons']} seasons, 2008 on).",
                    "The points were on the roster. Just not in the lineup."))
    r = max(d.lineup_losses(), key=lambda r: float(r["best_lineup_margin"]))
    out.append(card(num(r["best_lineup_margin"]), "Costliest benching", f"{link(r['team'])} ({season_link(r['season'])})",
                    f"Week {r['week']}: scored {num(r['score'])}, could have scored {num(r['best_possible'])}, lost to "
                    f"{link(r['opponent'])} by {num(float(r['opponent_score']) - float(r['score']))}. The best lineup wins by "
                    f"{num(r['best_lineup_margin'])}.", "Set it and forget it, then forget it some more."))
    return out


def office_cards():
    out = []
    dv = [r for r in d.draft_value() if r["complete"] == "True" and r["round"] == "1" and int(r["starts"]) == 0]
    r = min(dv, key=lambda r: int(r["overall"]))
    last, _, first = r["player"].partition(", ")
    out.append(card(f"#{r['overall']}", "Worst first-round pick", f"{link(r['team'])} ({season_link(r['season'])})",
                    f"{E(first)} {E(last)}, {ordinal(int(r['overall']))} overall: no starts, for this team or anyone else in the league."
                    if r["starts_any_team"] == "0" else f"{E(first)} {E(last)}, {ordinal(int(r['overall']))} overall: no starts for this team.",
                    "The pick was in. The player never was."))
    do = d.by_owner("draft_owners.csv")
    t = min(do, key=lambda t: float(do[t]["hit_rate"]))
    tr = d.by_owner("team_records.csv")
    top = max(tr, key=lambda t: float(tr[t]["win_pct"]))
    out.append(card(f"{do[t]['hit_rate']}%", "Worst drafter", link(t),
                    f"The lowest share of picks that became starters (finished drafts, 2008 on)."
                    + (" Also the best win percentage in league history." if top == t else ""),
                    "Can't draft. Wins anyway. Nobody can explain it." if top == t else "Picks made, players not."))
    ga = max(d.got_away(), key=lambda r: float(r["points_elsewhere"]))
    last, _, first = ga["player"].partition(", ")
    out.append(card(num(ga["points_elsewhere"]), "The one that got away", f"{link(ga['dropped_by'])} ({season_link(ga['season'])})",
                    f"Dropped {E(first)} {E(last)} ({ga['position']}), who went on to start {ga['starts_elsewhere']} games for "
                    f"{names(ga['started_for'].split('; '))} and score {num(ga['points_elsewhere'])} points.",
                    "Somebody else's championship, from your waiver wire."))
    oa = d.by_owner("owner_activity.csv")
    t = min(oa, key=lambda t: int(oa[t]["net_picks"]))
    out.append(card(oa[t]["net_picks"], "Most draft picks traded away", link(t),
                    f"{abs(int(oa[t]['net_picks']))} more draft picks traded away than taken in, over {oa[t]['trades']} trades.",
                    "The future is now. It was always now."))
    return out


def grid(cards):
    return "<div class='shame-grid'>" + "".join(cards) + "</div>"


def build(dist):
    os.makedirs(f"{dist}/records", exist_ok=True)
    games = R.real_games()
    done = [y for y in d.seasons() if y in d.champions()]
    body = ("<div class='season shame'><h1>The wall of shame</h1><p class='lede'>Every record nobody wants, computed from the "
            "same games as the <a href='index.html'>record book</a>: the regular season and the championship playoffs, not the "
            "toilet bowl. Game and streak records count the season in progress. Season, playoff and franchise records use "
            "finished seasons. The numbers are the record. The jokes are not.</p>"
            f"<h2>Single games</h2>{grid(games_cards(games))}"
            f"<h2>Seasons</h2>{grid(seasons_cards(done))}"
            f"<h2>The playoffs</h2>{grid(playoff_cards(done))}"
            f"<h2>Franchises</h2>{grid(franchise_cards(done))}"
            f"<h2>The front office</h2>{grid(office_cards())}</div>")
    with open(f"{dist}/records/shame.html", "w") as f:
        f.write(page("PDL wall of shame", body, description="The PDL records nobody wants, computed from every game since 2000."))
    return 1
