"""Trades: trades/index.html, every trade since 2000 with who trades and with whom."""
import os
from collections import Counter

import league_data as d
from frame import E, page, slug


def team_link(t):
    return f"<a href='../franchises/{slug(t)}.html'>{E(t)}</a>"


def build(dist):
    os.makedirs(f"{dist}/trades", exist_ok=True)
    owners = sorted(d.read_csv("owner_activity.csv"), key=lambda r: -float(r["per_season"]))
    pairs = sorted(d.read_csv("pair_matrix.csv"), key=lambda r: -int(r["trades"]))
    trades = sorted(d.trades(), key=lambda t: (t["season"], t.get("date") or ""), reverse=True)
    per_season = Counter(t["season"] for t in trades)

    orow = "".join(f"<tr><td class='l'>{team_link(r['owner'])}</td><td>{r['trades']}</td><td>{r['per_season']}</td>"
                   f"<td>{r['distinct_partners']}</td><td class='l'>{team_link(r['top_partner'])} ({r['top_partner_trades']})</td>"
                   f"<td>{r['picks_out']}</td><td>{r['picks_in']}</td></tr>" for r in owners)
    prow = "".join(f"<li>{team_link(r['owner_a'])} and {team_link(r['owner_b'])}: {r['trades']}</li>" for r in pairs[:10])
    never = [r for r in pairs if int(r["trades"]) == 0 and r["could_trade"] == "yes"]
    top = max(per_season.values())
    bars = "".join(f"<div class='bar'><span class='y'>{y}</span><span class='b' style='width:{100 * n / top:.0f}%'></span>"
                   f"<span class='n'>{n}</span></div>" for y, n in sorted(per_season.items()))
    log = []
    for y in sorted(per_season, reverse=True):
        items = []
        for t in [x for x in trades if x["season"] == y]:
            a = ", ".join(E(d.asset_label(x)) for x in t["a_gave"]) or "unrecorded"
            b = ", ".join(E(d.asset_label(x)) for x in t["b_gave"]) or "unrecorded"
            items.append(f"<li data-teams='{E(t['team_a'])}|{E(t['team_b'])}'><span class='meta'>{E(t.get('date') or '')}</span> "
                         f"{team_link(t['team_a'])} sent {a}. {team_link(t['team_b'])} sent {b}.</li>")
        log.append(f"<details class='week' open><summary>{y} <span class='meta'>{per_season[y]} trades</span></summary>"
                   f"<ul class='trades'>{''.join(items)}</ul></details>")
    options = "".join(f"<option>{E(t)}</option>" for t in sorted(d.identities()))
    body = (f"<div class='season'><h1>Trades</h1><p class='lede'>All {len(trades)} trades since 2000: who trades, "
            "with whom, and what moved. Before 2008 the trades come from the league's own trade page, which does "
            "not always record every asset.</p>"
            "<h2>Who trades</h2><div class='table-wrap'><table class='data'><thead><tr><th class='l'>Team</th><th>Trades</th>"
            "<th>A season</th><th>Partners</th><th class='l'>Most often with</th><th>Picks sent</th><th>Picks received</th>"
            f"</tr></thead><tbody>{orow}</tbody></table></div>"
            f"<h2>The busiest partnerships</h2><ul>{prow}</ul>"
            f"<p class='meta'>{len(never)} pairs of teams that shared a season have never traded with each other.</p>"
            f"<h2>By season</h2><div class='bars'>{bars}</div>"
            "<h2>Every trade</h2><p><label for='team'>Show trades of </label><select id='team'><option value=''>every team"
            f"</option>{options}</select></p><div id='log'>{''.join(log)}</div>"
            "<script>document.getElementById('team').addEventListener('change', e => {"
            " const t = e.target.value;"
            " document.querySelectorAll('#log li').forEach(li => li.hidden = t && !li.dataset.teams.split('|').includes(t));"
            " document.querySelectorAll('#log details').forEach(d => d.hidden = ![...d.querySelectorAll('li')].some(li => !li.hidden));"
            "});</script></div>")
    with open(f"{dist}/trades/index.html", "w") as f:
        f.write(page("PDL trades", body, description="Every PDL trade since 2000."))
    return 1
