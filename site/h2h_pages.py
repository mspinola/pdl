"""Head to head: h2h/index.html (the matrix) and h2h/<a>--<b>.html (every game of a pairing)."""
import os
from collections import defaultdict

import league_data as d
from frame import E, num, page, record, slug
import eggs


def pair_slug(a, b):
    a, b = sorted((a, b))
    return f"{slug(a)}--{slug(b)}"


SHORT = {"Beers": "BEE", "Blitzkrieg": "BLZ", "Bunchalosers": "BUN", "Carter's Commandos": "CC", "Couchfire": "CF",
         "Da Funk": "DF", "Dunbar Dogs": "DD", "F-Jackie": "FJ", "Ho Train": "HT", "Iron City Pounders": "ICP",
         "Karpet Munchers": "KM", "Manic Moose": "MM", "OakalDoakals": "OD", "Otters": "OTT",
         "Scooter's Boozers": "SB", "Tally Wackers": "TW", "Texas Nashvillians": "TN"}


def short(team):
    """A column heading short enough for a 17-column table, and unambiguous."""
    return SHORT.get(team) or "".join(w[0] for w in team.replace("-", " ").split()).upper()[:3]


def matrix(teams):
    h2h = d.head_to_head()
    head = "<tr><th class='l'>Team</th>" + "".join(f"<th title='{E(t)}'>{E(short(t))}</th>" for t in teams) + "</tr>"
    rows = []
    for a in teams:
        cells = []
        for b in teams:
            if a == b:
                cells.append("<td class='na'></td>")
                continue
            r = h2h.get(a, {}).get(b)
            if not r or not r["games"]:
                cells.append("<td class='na'>-</td>")
                continue
            share = (r["w"] + 0.5 * r["t"]) / r["games"]
            tone = "up" if share > 0.55 else "down" if share < 0.45 else ""
            cells.append(f"<td class='{tone}'><a href='{pair_slug(a, b)}.html' title='{E(a)} against {E(b)}'>"
                         f"{record(r['w'], r['l'], r['t'])}</a></td>")
        rows.append(f"<tr><th class='l'><a href='../franchises/{slug(a)}.html'>{E(a)}</a></th>{''.join(cells)}</tr>")
    return f"<div class='table-wrap'><table class='data matrix'><thead>{head}</thead><tbody>{''.join(rows)}</tbody></table></div>"


def rivalries(teams):
    h2h = d.head_to_head()
    pairs = [(a, b, h2h[a][b]) for i, a in enumerate(teams) for b in teams[i + 1:] if h2h.get(a, {}).get(b, {}).get("games")]
    most = sorted(pairs, key=lambda p: -p[2]["games"])[:8]
    lopsided = sorted([p for p in pairs if p[2]["games"] >= 20],
                      key=lambda p: -abs(p[2]["w"] - p[2]["l"]) / p[2]["games"])[:8]

    def li(a, b, r):
        lead, trail, w, l = (a, b, r["w"], r["l"]) if r["w"] >= r["l"] else (b, a, r["l"], r["w"])
        return (f"<li><a href='{pair_slug(a, b)}.html'>{E(lead)} and {E(trail)}</a>: {r['games']} games, "
                f"{E(lead)} lead {w}-{l}{'-' + str(r['t']) if r['t'] else ''}</li>")
    return ("<h2>Most played</h2><ul>" + "".join(li(*p) for p in most) + "</ul>"
            "<h2>Most one-sided</h2><p class='meta'>Pairings with 20 or more games.</p><ul>"
            + "".join(li(*p) for p in lopsided) + "</ul>")


def pair_page(a, b):
    games = sorted([g for g in d.games() if {g["team_a"], g["team_b"]} == {a, b}], key=lambda g: (g["season"], g["week"]))
    r = d.head_to_head()[a][b]
    rows = []
    for g in games:
        sa, sb = (g["score_a"], g["score_b"]) if g["team_a"] == a else (g["score_b"], g["score_a"])
        res = g["result_a"] if g["team_a"] == a else {"W": "L", "L": "W", "T": "T"}[g["result_a"]]
        winner = a if res == "W" else b if res == "L" else ""
        rows.append(f"<tr><td><a href='../seasons/{g['season']}.html'>{g['season']}</a></td><td>{g['week']}</td>"
                    f"<td class='l'>{'Playoffs' if g['stage'] != 'regular' else ''}</td>"
                    f"<td class='{'won' if res == 'W' else ''}'>{num(sa)}</td><td class='{'won' if res == 'L' else ''}'>{num(sb)}</td>"
                    f"<td class='l'>{E(winner) or 'tie'}</td></tr>")
    post = [g for g in games if g["stage"] != "regular"]
    body = (f"<div class='season'><h1>{E(a)} and {E(b)}</h1><nav class='pn'><a href='index.html'>All of head to head</a>"
            f"<a href='../franchises/{slug(a)}.html'>{E(a)}</a><a href='../franchises/{slug(b)}.html'>{E(b)}</a></nav>"
            f"<div class='facts'><div class='fact'><span class='k'>Games</span><span class='v'>{r['games']}</span></div>"
            f"<div class='fact'><span class='k'>{E(a)}</span><span class='v'>{record(r['w'], r['l'], r['t'])}, "
            f"{num(r['pf'])} points</span></div><div class='fact'><span class='k'>{E(b)}</span><span class='v'>"
            f"{record(r['l'], r['w'], r['t'])}, {num(r['pa'])} points</span></div>"
            f"<div class='fact'><span class='k'>In the postseason</span><span class='v'>{len(post)} games</span></div></div>"
            f"{eggs.rivalry_caption(a, b, r)}<h2>Every game</h2><p class='meta'>Postseason games include the toilet bowl from 2014.</p>"
            f"<div class='table-wrap'><table class='data'><thead><tr><th>Season</th><th>Week</th><th class='l'></th>"
            f"<th>{E(a)}</th><th>{E(b)}</th><th class='l'>Winner</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></div>")
    return page(f"{a} and {b}, PDL", body, description=f"Every game between {a} and {b}.")


def build(dist):
    os.makedirs(f"{dist}/h2h", exist_ok=True)
    teams = sorted(d.identities())
    n = 0
    for i, a in enumerate(teams):
        for b in teams[i + 1:]:
            if d.head_to_head().get(a, {}).get(b, {}).get("games"):
                x, y = sorted((a, b))
                with open(f"{dist}/h2h/{pair_slug(a, b)}.html", "w") as f:
                    f.write(pair_page(x, y))
                n += 1
    body = ("<div class='h2h'><h1>Head to head</h1><p class='lede'>Every pairing's record, read across: the row "
            "team's wins and losses against the column team, regular season and postseason. Each record opens the "
            "pairing's games. Shaded: a record of 55% or better, or 45% or worse.</p>"
            + matrix(teams) + rivalries(teams) + "</div>")
    with open(f"{dist}/h2h/index.html", "w") as f:
        f.write(page("PDL head to head", body, description="Every PDL head-to-head record."))
    return n + 1
