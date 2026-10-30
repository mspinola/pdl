"""The record book: records/index.html, computed from every game since 2000.

Points records are split at 2018, when the rule changes raised scoring by about
half, so a 2005 score is not set against a 2022 one. Games are the regular
season and the championship playoffs. The toilet bowl is left out.
"""
import os
from collections import defaultdict

import league_data as d
from frame import E, num, page, record, slug

# the current era first, so the page opens on records still in play
ERAS = [("2018 on", 2018, 9999), ("2000 to 2017", 2000, 2017)]


def team_link(t):
    return f"<a href='../franchises/{slug(t)}.html'>{E(t)}</a>"


def real_games():
    out = []
    for y in d.seasons():
        playoff, _ = d.postseason(y)
        out += [g for g in d.season_games(y) if g["stage"] == "regular"] + playoff
    return out


def sides(g):
    yield g["team_a"], g["score_a"], g["team_b"], g["score_b"], g["result_a"]
    yield g["team_b"], g["score_b"], g["team_a"], g["score_a"], {"W": "L", "L": "W", "T": "T"}[g["result_a"]]


def table(head, rows):
    return ("<div class='table-wrap'><table class='data'><thead><tr>" + "".join(f"<th class='{c}'>{h}</th>" for h, c in head)
            + "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def game_row(y, w, stage, team, score, opp, opp_score):
    return (f"<tr><td class='l'>{team_link(team)}</td><td>{num(score)}</td><td class='l'>{team_link(opp)} {num(opp_score)}</td>"
            f"<td><a href='../seasons/{y}.html'>{y}</a></td><td>{w}{' (playoffs)' if stage != 'regular' else ''}</td></tr>")


GHEAD = [("Team", "l"), ("Score", ""), ("Opponent", "l"), ("Season", ""), ("Week", "")]


def single_games(games):
    out = []
    for label, lo, hi in ERAS:
        era = [g for g in games if lo <= g["season"] <= hi]
        scores = [(s, t, o, os_, g) for g in era for t, s, o, os_, _ in sides(g)]
        high = sorted(scores, key=lambda x: -x[0])[:10]
        low = sorted([x for x in scores if x[0] > 0], key=lambda x: x[0])[:5]
        margin = sorted(era, key=lambda g: -abs(g["score_a"] - g["score_b"]))[:5]
        combined = sorted(era, key=lambda g: -(g["score_a"] + g["score_b"]))[:5]
        out.append(f"<h3>Highest scores, {label}</h3>" + table(GHEAD, [game_row(g['season'], g['week'], g['stage'], t, s, o, os_) for s, t, o, os_, g in high]))
        out.append(f"<h3>Lowest scores, {label}</h3>" + table(GHEAD, [game_row(g['season'], g['week'], g['stage'], t, s, o, os_) for s, t, o, os_, g in low]))

        def winner_first(g):
            return (g["team_a"], g["score_a"], g["team_b"], g["score_b"]) if g["score_a"] >= g["score_b"] else (g["team_b"], g["score_b"], g["team_a"], g["score_a"])
        out.append(f"<h3>Biggest margins, {label}</h3>" + table(
            [("Winner", "l"), ("Score", ""), ("Loser", "l"), ("Margin", ""), ("Season", ""), ("Week", "")],
            [(lambda w, ws, l, ls: f"<tr><td class='l'>{team_link(w)}</td><td>{num(ws)}</td><td class='l'>{team_link(l)} {num(ls)}</td>"
              f"<td>{num(ws - ls)}</td><td><a href='../seasons/{g['season']}.html'>{g['season']}</a></td><td>{g['week']}</td></tr>")(*winner_first(g))
             for g in margin]))
        out.append(f"<h3>Highest combined scores, {label}</h3>" + table(
            [("Game", "l"), ("Combined", ""), ("Season", ""), ("Week", "")],
            [f"<tr><td class='l'>{team_link(g['team_a'])} {num(g['score_a'])}, {team_link(g['team_b'])} {num(g['score_b'])}</td>"
             f"<td>{num(g['score_a'] + g['score_b'])}</td><td><a href='../seasons/{g['season']}.html'>{g['season']}</a></td>"
             f"<td>{g['week']}</td></tr>" for g in combined]))
    return "".join(out)


def seasons_records():
    done = [y for y in d.seasons() if y in d.champions()]
    rows = [(y, r) for y in done for r in d.standings(y)]
    out = []
    SHEAD = [("Team", "l"), ("Season", ""), ("Record", ""), ("Points", ""), ("All-play", "")]

    def srow(y, r):
        return (f"<tr><td class='l'>{team_link(r['team'])}</td><td><a href='../seasons/{y}.html'>{y}</a></td>"
                f"<td>{record(r['w'], r['l'], r['t'])}</td><td>{num(r['pf'])}</td>"
                f"<td>{'' if r['allplay'] is None else format(r['allplay'], '.3f').lstrip('0')}</td></tr>")

    def pct(r):
        return (r["w"] + 0.5 * r["t"]) / max(1, r["w"] + r["l"] + r["t"])
    for label, lo, hi in ERAS:
        era = [x for x in rows if lo <= x[0] <= hi]
        out.append(f"<h3>Most points in a regular season, {label}</h3>" + table(SHEAD, [srow(*x) for x in sorted(era, key=lambda x: -x[1]["pf"])[:8]]))
    out.append("<h3>Best regular-season records</h3>" + table(SHEAD, [srow(*x) for x in sorted(rows, key=lambda x: (-pct(x[1]), -x[1]["pf"]))[:10]]))
    out.append("<h3>Worst regular-season records</h3>" + table(SHEAD, [srow(*x) for x in sorted(rows, key=lambda x: (pct(x[1]), x[1]["pf"]))[:8]]))
    out.append("<h3>Best all-play seasons</h3><p class='meta'>The share of every other team outscored, week by week: the "
               "best measure of a dominant season, whoever the schedule served up.</p>"
               + table(SHEAD, [srow(*x) for x in sorted([x for x in rows if x[1]["allplay"] is not None], key=lambda x: -x[1]["allplay"])[:8]]))
    return "".join(out)


def year_by_year(games):
    """One row a finished season, newest first, as the original site's record book ran."""
    rows = []
    for y in sorted((y for y in d.seasons() if y in d.champions()), reverse=True):
        st = d.standings(y)
        best = max(st, key=lambda r: ((r["w"] + 0.5 * r["t"]) / max(1, r["w"] + r["l"] + r["t"]), r["pf"]))
        most = max(st, key=lambda r: r["pf"])
        high = max(((s, t) for g in games if g["season"] == y and g["stage"] == "regular" for t, s, *_ in sides(g)),
                   default=None)
        rows.append(f"<tr><td><a href='../seasons/{y}.html'>{y}</a></td><td class='l'>{team_link(d.champions()[y])}</td>"
                    f"<td class='l'>{team_link(best['team'])} {record(best['w'], best['l'], best['t'])}</td>"
                    f"<td class='l'>{team_link(most['team'])} {num(most['pf'])}</td>"
                    f"<td class='l'>{team_link(high[1]) + ' ' + num(high[0]) if high else ''}</td></tr>")
    return ("<p class='meta'>Regular season only, as the original site's record book counts it. Best record breaks "
            "ties on points. Points are not comparable across 2018, when scoring rose by about half.</p>"
            + table([("Season", ""), ("Champion", "l"), ("Best record", "l"), ("Most points", "l"), ("Top game", "l")], rows))


def streaks():
    by_team = defaultdict(list)
    for g in sorted([g for g in d.games() if g["stage"] == "regular"], key=lambda g: (g["season"], g["week"])):
        for t, _, _, _, res in sides(g):
            by_team[t].append((g["season"], g["week"], res))
    best = {"W": [], "L": []}
    for t, seq in by_team.items():
        for kind in ("W", "L"):
            run, start = 0, None
            for y, w, res in seq + [(None, None, None)]:
                if res == kind:
                    run, start = run + 1, start or (y, w)
                else:
                    if run:
                        best[kind].append((run, t, start, prev))
                    run, start = 0, None
                prev = (y, w)
    out = []
    for kind, label in (("W", "Longest winning streaks"), ("L", "Longest losing streaks")):
        rows = [f"<tr><td class='l'>{team_link(t)}</td><td>{n}</td><td class='l'>{s[0]} week {s[1]} to {e[0]} week {e[1]}</td></tr>"
                for n, t, s, e in sorted(best[kind], key=lambda x: -x[0])[:8]]
        out.append(f"<h3>{label}</h3><p class='meta'>Regular-season games in a row, across seasons.</p>"
                   + table([("Team", "l"), ("Games", ""), ("From and to", "l")], rows))
    return "".join(out)


def franchise_records():
    teams = d.identities()
    done = [y for y in d.seasons() if y in d.champions()]
    rows = []
    for t, ident in teams.items():
        titles = [y for y in done if d.champions()[y] == t]
        finals = [y for y in done if d.finish(y, t) in ("champion", "runner-up")]
        playoff = [y for y in done if d.finish(y, t)]
        run = longest = 0
        for y in done:
            if y in ident["seasons"] and y in playoff:
                run += 1
                longest = max(longest, run)
            else:
                run = 0
        last = max(titles) if titles else None
        drought = (done[-1] - last) if last else (done[-1] - ident["first_season"] + 1)
        rows.append((t, len(titles), len(finals), len(playoff), longest, drought, last))
    trows = [f"<tr><td class='l'>{team_link(t)}</td><td>{n}</td><td>{f}</td><td>{p}</td><td>{r}</td>"
             f"<td>{dr if last else str(dr) + ' (never)'}</td></tr>"
             for t, n, f, p, r, dr, last in sorted(rows, key=lambda x: (-x[1], -x[2], -x[3]))]
    return ("<h3>Titles and playoff runs</h3><p class='meta'>Title drought: seasons since the last title, or since the "
            "franchise began if it has never won.</p>"
            + table([("Team", "l"), ("Titles", ""), ("Super Bowls", ""), ("Playoff seasons", ""), ("Longest playoff run", ""),
                     ("Title drought", "")], trows))


def lineup_records():
    losses = d.lineup_losses()
    worst = sorted(losses, key=lambda r: -float(r["best_lineup_margin"]))[:8]
    rows = [f"<tr><td class='l'>{team_link(r['team'])}</td><td>{num(r['score'])}</td><td>{num(r['best_possible'])}</td>"
            f"<td class='l'>{team_link(r['opponent'])} {num(r['opponent_score'])}</td>"
            f"<td><a href='../seasons/{r['season']}.html'>{r['season']}</a></td><td>{r['week']}{' (playoffs)' if r['stage'] == 'playoffs' else ''}</td></tr>"
            for r in worst]
    return ("<h3>The costliest benchings</h3><p class='meta'>Losses the best lineup would have won by the most, 2008 on.</p>"
            + table([("Team", "l"), ("Scored", ""), ("Best possible", ""), ("Opponent", "l"), ("Season", ""), ("Week", "")], rows))


def build(dist):
    os.makedirs(f"{dist}/records", exist_ok=True)
    games = real_games()
    body = ("<div class='season'><h1>The record book</h1><p class='lede'>Computed from every game since 2000: the regular "
            "season and the championship playoffs, not the toilet bowl. Points records are split at 2018, when the rule "
            "changes raised scoring by about half. The season in progress is left out of season and franchise records.</p>"
            "<nav class='pn'><a href='#years'>Year by year</a><a href='#games'>Games</a><a href='#seasons'>Seasons</a>"
            "<a href='#streaks'>Streaks</a><a href='#franchises'>Franchises</a><a href='#lineups'>Lineups</a></nav>"
            f"<h2 id='years'>Year by year</h2>{year_by_year(games)}"
            f"<h2 id='games'>Single games</h2>{single_games(games)}"
            f"<h2 id='seasons'>Seasons</h2>{seasons_records()}"
            f"<h2 id='streaks'>Streaks</h2>{streaks()}"
            f"<h2 id='franchises'>Franchises</h2>{franchise_records()}"
            f"<h2 id='lineups'>Lineups</h2>{lineup_records()}</div>")
    with open(f"{dist}/records/index.html", "w") as f:
        f.write(page("PDL record book", body, description="The PDL record book, computed from every game since 2000."))
    return 1
