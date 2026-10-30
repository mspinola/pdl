"""The franchise pages: site/dist/franchises/index.html and franchises/<team>.html.

One page per owner identity, the unit every analysis reports by. Bunchalosers
and Couchfire are one franchise under two owners, so each has its own page and
each links to the other.
"""
import os
from collections import defaultdict

import league_data as d
from frame import E, num, page, record, slug


def team_link(t):
    return f'<a href="{slug(t)}.html">{E(t)}</a>'


def season_link(y):
    return f'<a href="../seasons/{y}.html">{y}</a>'


def fact(label, value):
    return f"<div class='fact'><span class='k'>{E(label)}</span><span class='v'>{value}</span></div>"


def seasons_table(team, seasons):
    rows = []
    for y in seasons:
        r = next((x for x in d.standings(y) if x["team"] == team), None)
        if not r:
            continue
        rank = [x["team"] for x in d.standings(y)].index(team) + 1
        fin = d.finish(y, team)
        allplay = "" if r["allplay"] is None else f"{r['allplay']:.3f}".lstrip("0")
        luck = "" if r["luck"] is None else f"{r['luck']:+.1f}"
        rows.append(f"<tr class='{'champ' if fin == 'champion' else ''}'><td>{season_link(y)}</td>"
                    f"<td>{record(r['w'], r['l'], r['t'])}</td><td>{rank}</td><td>{num(r['pf'])}</td>"
                    f"<td>{allplay}</td><td>{luck}</td><td class='l'>{fin.capitalize()}</td></tr>")
    return ("<div class='table-wrap'><table class='data'><thead><tr><th>Season</th><th>Record</th><th>Rank</th>"
            "<th>Points</th><th>All-play</th><th>Luck</th><th class='l'>Finish</th></tr></thead><tbody>"
            + "".join(reversed(rows)) + "</tbody></table></div>")


def h2h_table(team):
    rows = []
    for opp, r in sorted(d.head_to_head().get(team, {}).items(), key=lambda kv: -(kv[1]["w"] - kv[1]["l"])):
        if not r["games"]:
            continue
        rows.append(f"<tr><td class='l'>{team_link(opp)}</td><td>{r['games']}</td><td>{record(r['w'], r['l'], r['t'])}</td>"
                    f"<td>{100 * (r['w'] + 0.5 * r['t']) / r['games']:.0f}%</td></tr>")
    return ("<div class='table-wrap'><table class='data'><thead><tr><th class='l'>Opponent</th><th>Games</th>"
            "<th>Record</th><th>Win rate</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def franchise_page(team, ident, owners):
    seasons = [y for y in d.seasons() if y in ident["seasons"]]
    titles = sorted(y for y, c in d.champions().items() if c == team)
    reg = [x for y in seasons for x in d.standings(y) if x["team"] == team]
    w = sum(x["w"] for x in reg)
    l = sum(x["l"] for x in reg)
    t = sum(x["t"] for x in reg)
    playoffs = [y for y in seasons if d.finish(y, team) in ("champion", "runner-up", "playoffs")]
    finals = [y for y in seasons if d.finish(y, team) == "runner-up"]
    rec = owners["records"].get(team, {})
    hist = d.name_history().get(team, [])
    hist = [(y, n) for y, n in hist if not (team == "Bunchalosers" and y >= 2018) and not (team == "Couchfire" and y < 2018)]
    # only worth showing when the name changed
    names = " ".join(f"<span class='chip'>{E(n)} <span class='meta'>from {y}</span></span>" for y, n in hist) if len(hist) > 1 else ""
    note = E(ident.get("note") or "")
    if team == "Bunchalosers":
        note += f" The franchise continues as {team_link('Couchfire')}."
    if team == "Couchfire":
        note += f" The franchise was {team_link('Bunchalosers')} before."
    facts = [fact("Seasons", f"{seasons[0]} to {seasons[-1]} ({len(seasons)})"),
             fact("Regular season", f"{record(w, l, t)} ({100 * (w + 0.5 * t) / max(1, w + l + t):.0f}%)"),
             fact("Titles", (", ".join(season_link(y) for y in titles) if titles else "none")),
             fact("Super Bowl losses", (", ".join(season_link(y) for y in finals) if finals else "none")),
             fact("Playoff seasons", str(len(playoffs))),
             fact("Playoff record", record(*d.playoff_record(team)))]
    style = []
    tr = owners["trades"].get(team)
    if tr:
        style.append(fact("Trades", f"{tr['trades']} ({tr['per_season']} a season), most often with {team_link(tr['top_partner'])} ({tr['top_partner_trades']})"))
    tx = owners["transactions"].get(team)
    if tx:
        style.append(fact("Adds a season", f"{tx['adds_per_season']} all time, {tx['adds_per_season_2008_on']} since 2008, "
                                           f"{tx['pickup_share_2008_on']}% of them free agent pickups"))
    lu = owners["lineups"].get(team)
    if lu:
        style.append(fact("Lineups", f"{lu['efficiency']}% of the best possible score started ({float(lu['vs_league']):+.1f} against the league), "
                                     f"{lu['lineup_losses']} regular-season losses the best lineup would have won"))
    lk = owners["luck"].get(team)
    if lk:
        style.append(fact("Schedule luck", f"{float(lk['luck']):+.1f} wins against what its scoring was worth "
                                           f"({float(lk['luck_z']):+.1f} standard deviations)"))
    dr = owners["draft"].get(team)
    if dr:
        style.append(fact("Drafting", f"{dr['hit_rate']}% of picks became starters, {dr['kept_rate']}% for this team. "
                                      f"{float(dr['any_team_over_slot']):+.2f} starts a pick over the slot"))
    best = sorted([p for p in d.draft_value() if p["team"] == team], key=lambda p: -float(p["value_any_team"]))[:5]
    best_rows = "".join(f"<li>{season_link(p['season'])}, round {p['round']} pick {p['pick']}: {E(p['player'])} "
                        f"({E(p['position'] or '')}), {p['starts_any_team']} starts"
                        + (f", {p['starts']} of them for {E(team)}" if p['starts'] != p['starts_any_team'] else "")
                        + "</li>" for p in best)
    away = [g for g in d.got_away() if g["dropped_by"] == team and g["position"] not in ("K", "Def")][:3]
    away_rows = "".join(f"<li>{season_link(g['season'])}: {E(g['player'])} ({E(g['position'] or '')}), "
                        f"{g['starts_elsewhere']} starts elsewhere</li>" for g in away)
    body = (f"<div class='franchise'><h1>{E(team)}</h1>"
            + (f"<p class='lede'>{note}</p>" if note else "")
            + (f"<p class='names'>{names}</p>" if names else "")
            + f"<div class='facts'>{''.join(facts)}</div>"
            + (f"<h2>How it is run</h2><div class='facts'>{''.join(style)}</div>" if style else "")
            + "<h2>Season by season</h2>" + seasons_table(team, seasons)
            + "<h2>Head to head</h2><p class='meta'>Every game, regular season and postseason.</p>" + h2h_table(team)
            + (f"<h2>Best draft picks</h2><p class='meta'>By value over three seasons, for whichever teams started him, 2008 on.</p><ul>{best_rows}</ul>" if best_rows else "")
            + (f"<h2>The ones that got away</h2><ul>{away_rows}</ul>" if away_rows else "")
            + "</div>")
    return page(f"{team}, PDL", body, description=f"The {team} franchise in the Premier Dynasty League.")


def index_page(idents, owners):
    rows = []
    def pct(team):
        w, l, t = d.regular_record(team)
        return (w + 0.5 * t) / max(1, w + l + t)
    for team in sorted(idents, key=lambda t: -pct(t)):
        titles = sorted(y for y, c in d.champions().items() if c == team)
        ident = idents[team]
        pw, pl = d.playoff_record(team)
        rows.append(f"<tr><td class='l'>{team_link(team)}</td><td>{ident['first_season']} to {ident['last_season']}</td>"
                    f"<td>{record(*d.regular_record(team))}</td><td>{f'{pct(team):.3f}'.lstrip('0')}</td>"
                    f"<td>{record(pw, pl)}</td><td>{len(titles)}</td>"
                    f"<td class='l'>{', '.join(str(y) for y in titles)}</td></tr>")
    body = ("<div class='franchise'><h1>Franchises</h1><p class='lede'>Every team in the league's history, by its "
            "current name, by regular-season win rate. The playoff record counts championship games only, not the toilet "
            "bowl. Bunchalosers and Couchfire are one franchise under its "
            "two owners, the league's only change of owner, in 2018.</p><div class='table-wrap'><table class='data'>"
            "<thead><tr><th class='l'>Team</th><th>Seasons</th><th>Regular season</th><th>Win rate</th><th>Playoffs</th><th>Titles</th>"
            f"<th class='l'>Title seasons</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></div>")
    return page("PDL franchises", body, description="Every PDL franchise since 2000.")


def build(dist):
    os.makedirs(f"{dist}/franchises", exist_ok=True)
    idents = d.identities()
    owners = {"records": d.by_owner("team_records.csv"), "trades": d.by_owner("owner_activity.csv"),
              "transactions": d.by_owner("transaction_owners.csv"), "lineups": d.by_owner("lineup_owners.csv"),
              "luck": d.by_owner("luck_owners.csv"), "draft": d.by_owner("draft_owners.csv")}
    for team, ident in idents.items():
        with open(f"{dist}/franchises/{slug(team)}.html", "w") as f:
            f.write(franchise_page(team, ident, owners))
    with open(f"{dist}/franchises/index.html", "w") as f:
        f.write(index_page(idents, owners))
    return len(idents) + 1
