"""The season pages: site/dist/seasons/index.html and seasons/<year>.html."""
import os
from collections import defaultdict

import league_data as d
from frame import E, num, page, record, slug
import eggs

RULES_FROM = 2006   # the first season the layered rule book covers


def team_link(t, up="../"):
    return f'<a href="{up}franchises/{slug(t)}.html">{E(t)}</a>'


def game_line(g, up="../"):
    a, b = g["team_a"], g["team_b"]
    sa, sb = g["score_a"], g["score_b"]
    win_a = g["result_a"] == "W"
    win_b = g["result_a"] == "L"
    left = f'<span class="{"won" if win_a else ""}">{team_link(a, up)} {num(sa)}</span>'
    right = f'<span class="{"won" if win_b else ""}">{num(sb)} {team_link(b, up)}</span>'
    return f"<li>{left} <span class='vs'>v</span> {right}</li>"


def standings_table(season):
    rows = d.standings(season)
    has_div = any(r["division"] for r in rows)
    head = ("<tr><th>#</th><th class='l'>Team</th>" + ("<th class='l'>Division</th>" if has_div else "")
            + "<th>Record</th><th>Points</th><th>Against</th><th title='Share of all other teams beaten each week'>All-play</th>"
              "<th title='Wins minus the wins its scoring was worth against everyone'>Luck</th><th class='l'>Finish</th></tr>")
    body = []
    for i, r in enumerate(rows, 1):
        fin = ("Champion" if r["champion"] else "Runner-up" if r["runner_up"] else "Playoffs" if r["playoffs"] else "")
        allplay = "" if r["allplay"] is None else f"{r['allplay']:.3f}".lstrip("0")
        luck = "" if r["luck"] is None else f"{r['luck']:+.1f}"
        body.append(
            f"<tr class='{'champ' if r['champion'] else ''}'><td>{i}</td><td class='l'>{team_link(r['team'])}</td>"
            + (f"<td class='l'>{E(r['division'] or '')}</td>" if has_div else "")
            + f"<td>{record(r['w'], r['l'], r['t'])}</td><td>{num(r['pf'])}</td><td>{num(r['pa'])}</td>"
              f"<td>{allplay}</td><td>{luck}</td><td class='l'>{fin}</td></tr>")
    return f"<div class='table-wrap'><table class='data'><thead>{head}</thead><tbody>{''.join(body)}</tbody></table></div>"


def conference_section(season):
    """The standings as the league is built: two conferences, two divisions each."""
    rows = d.standings(season)
    divs = d.divisions(season)
    if not divs:
        return ""
    seeds = d.seeds(season)
    drec = d.division_records(season)
    confs = {}
    for r in rows:
        div = divs.get(r["team"])
        if div:
            confs.setdefault(div.split()[0], {}).setdefault(div, []).append(r)
    blocks = []
    for conf in sorted(confs):
        tables = []
        for div in sorted(confs[conf]):
            teams = confs[conf][div]   # already in record-then-points order
            if seeds:
                # the bracket says who won the division: seed 1 or 2
                teams = sorted(teams, key=lambda r: (0 if seeds.get(r["team"]) in (1, 2) else 1,
                                                     teams.index(r)))
            body = []
            for i, r in enumerate(teams):
                seed = seeds.get(r["team"])
                won = seed in (1, 2) if seeds else i == 0
                mark = f"<span class='seed' title='Playoff seed'>{seed}</span>" if seed else ("" if seeds else
                       ("<span class='seed' title='Division leader'>&#9679;</span>" if won else ""))
                dr = drec.get(r["team"], [0, 0, 0])
                body.append(f"<tr class='{'champ' if r['champion'] else ''}'><td class='l'>{mark} {team_link(r['team'])}</td>"
                            f"<td>{record(r['w'], r['l'], r['t'])}</td><td>{record(*dr)}</td><td>{num(r['pf'])}</td></tr>")
            tables.append(f"<h4>{E(div)}</h4><div class='table-wrap'><table class='data div'><thead><tr><th class='l'>Team</th>"
                          f"<th>Record</th><th>Division</th><th>Points</th></tr></thead><tbody>{''.join(body)}</tbody></table></div>")
        blocks.append(f"<div class='conf'><h3>{E(conf)}</h3>{''.join(tables)}</div>")
    if seeds:
        note = ("The number is the team's playoff seed in its conference: 1 and 2 won their divisions, 3 and 4 are "
                "the wild cards (rule book 2.3).")
    else:
        note = ("The dot marks each division's leader by record, then points. The league's own tiebreaks can "
                "differ where records are level.")
    return (f"<h2 id='conferences'>By conference and division</h2><p class='meta'>{note} Divisions are as MFL "
            f"records them{' (from the league standings page before 2003)' if season < 2003 else ''}.</p>"
            f"<div class='confs'>{''.join(blocks)}</div>")


def postseason_section(season):
    playoff, consolation = d.postseason(season)
    if not playoff:
        return ""
    out = ["<h2 id='playoffs'>Playoffs</h2>"]
    weeks = sorted({g["week"] for g in playoff})
    names = {len(weeks) - 1: "Super Bowl", len(weeks) - 2: "Conference championships"} if len(weeks) >= 3 else {}
    for i, w in enumerate(weeks):
        label = names.get(i, "First round") if names else f"Week {w}"
        out.append(f"<h3>{label} <span class='week'>week {w}</span></h3><ul class='games'>"
                   + "".join(game_line(g) for g in playoff if g["week"] == w) + "</ul>")
    if consolation:
        out.append("<details><summary>Toilet bowl and consolation games</summary>")
        for w in sorted({g["week"] for g in consolation}):
            out.append(f"<h4>Week {w}</h4><ul class='games'>"
                       + "".join(game_line(g) for g in consolation if g["week"] == w) + "</ul>")
        out.append("</details>")
    return "\n".join(out)


def weeks_section(season):
    reg = [g for g in d.season_games(season) if g["stage"] == "regular"]
    if not reg:
        return ""
    out = ["<h2 id='weeks'>Week by week</h2>"]
    for w in sorted({g["week"] for g in reg}):
        gs = [g for g in reg if g["week"] == w]
        top = max(max(g["score_a"], g["score_b"]) for g in gs)
        out.append(f"<details class='week'><summary>Week {w} <span class='meta'>high score {num(top)}</span></summary>"
                   f"<ul class='games'>{''.join(game_line(g) for g in gs)}</ul></details>")
    return "\n".join(out)


def draft_section(season):
    picks = [p for p in d.draft_value() if int(p["season"]) == season and p["round"] == "1"]
    if not picks:
        return ""
    picks.sort(key=lambda p: int(p["pick"]))
    complete = picks[0]["complete"] == "True"
    rows = "".join(f"<tr><td>{p['pick']}</td><td class='l'>{team_link(p['team'])}</td><td class='l'>{E(p['player'])}</td>"
                   f"<td>{E(p['position'] or '')}</td><td>{p['starts']}</td><td>{p['starts_any_team']}</td></tr>" for p in picks)
    note = ("Starts are regular-season starts in this and the next two seasons"
            + ("." if complete else ", so far."))
    return (f"<h2 id='draft'>The draft's first round</h2><p class='meta'>{note} The full draft, every round, is in "
            f"<code>datasets/draft_value.csv</code>.</p><div class='table-wrap'><table class='data'><thead><tr><th>Pick</th>"
            f"<th class='l'>Team</th><th class='l'>Player</th><th>Pos</th><th>Starts for the team</th><th>Starts anywhere</th>"
            f"</tr></thead><tbody>{rows}</tbody></table></div>")


def trades_section(season):
    ts = [t for t in d.trades() if t["season"] == season]
    if not ts:
        return ""
    ts.sort(key=lambda t: t.get("date") or "")
    items = []
    for t in ts:
        a = ", ".join(E(d.asset_label(x)) for x in t["a_gave"]) or "unrecorded"
        b = ", ".join(E(d.asset_label(x)) for x in t["b_gave"]) or "unrecorded"
        items.append(f"<li><span class='meta'>{E(t.get('date') or '')}</span> {team_link(t['team_a'])} sent {a}. "
                     f"{team_link(t['team_b'])} sent {b}.</li>")
    return f"<h2 id='trades'>Trades</h2><p class='meta'>{len(ts)} in all.</p><ul class='trades'>{''.join(items)}</ul>"


def pickups_section(season):
    ps = [p for p in d.best_pickups() if int(p["season"]) == season and p["position"] not in ("K", "Def")
          and float(p["value_over_average"]) > 0][:5]
    if not ps:
        return ""
    rows = "".join(f"<tr><td class='l'>{team_link(p['team'])}</td><td class='l'>{E(p['player'])}</td><td>{E(p['position'])}</td>"
                   f"<td>{p['week_added']}</td><td>{p['starts']}</td><td>{float(p['value_over_average']):+.1f}</td></tr>" for p in ps)
    return ("<h2 id='pickups'>Pickups that paid</h2><p class='meta'>Players added during the season, by the points they "
            "scored above an average starter at their position, in average starts.</p><div class='table-wrap'>"
            "<table class='data'><thead><tr><th class='l'>Team</th><th class='l'>Player</th><th>Pos</th><th>Week added</th>"
            f"<th>Starts</th><th>Value</th></tr></thead><tbody>{rows}</tbody></table></div>")


def rules_section(season):
    changes = [c for c in d.ledger() if c["meeting"] == season and c["status"] != "open"]
    out = []
    if changes:
        out.append(f"<h2 id='rules'>Rule changes from the {season} summer meeting</h2><ul class='changes'>")
        for c in changes:
            eff = f" From {c['effective']}." if c.get("effective") and c["effective"] != season else ""
            out.append(f"<li>{E(c['change'])}{eff} <a href='../rules/changes.html#{E(c['id'])}'>Record</a></li>")
        out.append("</ul>")
    if season >= RULES_FROM:
        out.append(f"<p><a href='../rules/{season}.html'>The rules in force for {season}</a></p>")
    return "\n".join(out)


def season_page(season, seasons):
    champ = d.champions().get(season)
    ru = d.runner_up(season)
    fin = d.final(season)
    st = d.standings(season)
    in_progress = season == seasons[-1] and not champ
    banner = ""
    if champ:
        score = ""
        if fin:
            cs, rs = (fin["score_a"], fin["score_b"]) if fin["team_a"] == champ else (fin["score_b"], fin["score_a"])
            score = f", {num(cs)} to {num(rs)}"
        banner = (f"<div class='banner{eggs.banner_class(champ)}'><span class='label'>Champion</span> <strong>{team_link(champ)}</strong>"
                  + (f" <span class='meta'>beat {team_link(ru)} in the Super Bowl{score}</span>" if ru else "") + "</div>")
    elif in_progress:
        banner = "<div class='banner'><span class='label'>In progress</span> The season is still being played.</div>"
    nav = []
    if season - 1 in seasons:
        nav.append(f"<a href='{season - 1}.html'>{season - 1}</a>")
    nav.append("<a href='index.html'>All seasons</a>")
    if season + 1 in seasons:
        nav.append(f"<a href='{season + 1}.html'>{season + 1}</a>")
    sections = [s for s in (postseason_section(season), draft_section(season), trades_section(season),
                            pickups_section(season), rules_section(season), weeks_section(season)) if s]
    tip = eggs.season_tooltip(season)
    body = (f"<div class='season'><h1{f' title={chr(39)}{E(tip)}{chr(39)}' if tip else ''}>{season}</h1><nav class='pn'>{' '.join(nav)}</nav>{banner}"
            f"<h2 id='standings'>Standings</h2><p class='meta'>Regular season, ranked by record then points. All-play is "
            f"the share of all other teams a team outscored each week. Luck is wins minus what that scoring was worth.</p>"
            f"{standings_table(season)}{conference_section(season)}{''.join(sections)}</div>")
    return page(f"PDL {season}", body, description=f"The PDL {season} season: standings, playoffs, draft, trades.")


def index_page(seasons):
    rows = []
    for y in reversed(seasons):
        st = d.standings(y)
        if not st:
            continue
        best = st[0]
        top = max(st, key=lambda r: r["pf"])
        champ = d.champions().get(y)
        rows.append(f"<tr><td><a href='{y}.html'>{y}</a></td><td class='l'>{team_link(champ, '../') if champ else '<em>in progress</em>'}</td>"
                    f"<td class='l'>{team_link(d.runner_up(y)) if d.runner_up(y) else ''}</td>"
                    f"<td class='l'>{team_link(best['team'])} {record(best['w'], best['l'], best['t'])}</td>"
                    f"<td class='l'>{team_link(top['team'])} {num(top['pf'])}</td><td>{len(st)}</td></tr>")
    body = ("<div class='season'><h1>Seasons</h1><p class='lede'>Every PDL season since 2000. The best record is the "
            "regular season's. Points are as scored: the 2018 rule changes raised scoring by about half, so compare "
            "points within an era.</p><div class='table-wrap'><table class='data'><thead><tr><th>Season</th>"
            "<th class='l'>Champion</th><th class='l'>Runner-up</th><th class='l'>Best record</th><th class='l'>Most points</th>"
            f"<th>Teams</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></div>")
    return page("PDL seasons", body, description="Every PDL season since 2000.")


def build(dist):
    os.makedirs(f"{dist}/seasons", exist_ok=True)
    seasons = d.seasons()
    for y in seasons:
        with open(f"{dist}/seasons/{y}.html", "w") as f:
            f.write(season_page(y, seasons))
    with open(f"{dist}/seasons/index.html", "w") as f:
        f.write(index_page(seasons))
    return len(seasons) + 1
