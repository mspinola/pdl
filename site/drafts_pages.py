"""Drafts: drafts/index.html and drafts/<year>.html, every pick from 2008.

Before 2008 the drafts are on the original site's draft boards, linked from the
index. Each pick shows how it turned out over three seasons (draft_value.py).
"""
import json, os
import statistics
from collections import defaultdict

import league_data as d
from frame import E, page, slug

LEGACY = "https://mspinola.github.io/mspinola/pdl"
BOARDS = {**{y: f"pdl{y}/setup/draft.html" for y in range(2000, 2005)},
          **{y: f"pdl{y}/setup/draft_rnd.html" for y in range(2005, 2008)}}


def team_link(t):
    return f"<a href='../franchises/{slug(t)}.html'>{E(t)}</a>"


def year_page(y, picks, years):
    complete = picks[0]["complete"] == "True"
    rounds = defaultdict(list)
    for p in picks:
        rounds[int(p["round"])].append(p)
    out = []
    for rd in sorted(rounds):
        rows = "".join(
            f"<tr class='{'hit' if p['hit'] == 'True' else ''}'><td>{p['pick']}</td><td>{p['overall']}</td>"
            f"<td class='l'>{team_link(p['team'])}</td><td class='l'>{E(p['player'])}</td><td>{E(p['position'] or '')}</td>"
            f"<td>{p['starts_any_team']}</td><td>{p['starts']}</td></tr>"
            for p in sorted(rounds[rd], key=lambda p: int(p["pick"])))
        out.append(f"<h2>Round {rd}</h2><div class='table-wrap'><table class='data'><thead><tr><th>Pick</th><th>Overall</th>"
                   f"<th class='l'>Team</th><th class='l'>Player</th><th>Pos</th><th>Starts</th>"
                   f"<th>For the drafting team</th></tr></thead><tbody>{rows}</tbody></table></div>")
    nav = [f"<a href='{y - 1}.html'>{y - 1}</a>" if y - 1 in years else "", "<a href='index.html'>All drafts</a>",
           f"<a href='{y + 1}.html'>{y + 1}</a>" if y + 1 in years else "", f"<a href='../seasons/{y}.html'>The {y} season</a>"]
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw = json.load(open(f"{base}/mfl_archive/{y}/draft_results.json")).get("draftResults", {}).get("draftUnit", {}).get("draftPick", [])
    passed = sum(1 for x in (raw if isinstance(raw, list) else [raw]) if not (x.get("player") or "").strip("-"))
    passed_note = f", and {passed} passed (a team with a full roster skips its pick)" if passed else ""
    body = (f"<div class='season'><h1>The {y} draft</h1><nav class='pn'>{' '.join(x for x in nav if x)}</nav>"
            f"<p class='lede'>{len(picks)} picks made{passed_note}. Starts are regular-season starts in {y} and the two seasons after"
            f"{'' if complete else ', so far'}: for any team, and for the team that made the pick. Shaded rows "
            f"are hits, 10 or more starts for any team: the pick became a starter, whoever started him.</p>{''.join(out)}</div>")
    return page(f"PDL {y} draft", body, description=f"Every pick of the PDL {y} draft.")


def index_page(by_year):
    done = [p for ps in by_year.values() for p in ps if p["complete"] == "True"]
    rounds = defaultdict(list)
    for p in done:
        rounds[int(p["round"])].append(p)

    def rate(ps, key="hit"):
        return f"{100 * sum(p[key] == 'True' for p in ps) / len(ps):.0f}%" if ps else "-"
    rrows = "".join(
        f"<tr><td>{rd}</td><td>{len(ps)}</td><td>{rate(ps)}</td>"
        f"<td>{rate([p for p in ps if p['position'] not in ('K', 'Def')])}</td>"
        f"<td>{rate(ps, 'kept')}</td>"
        f"<td>{statistics.mean(int(p['starts_any_team']) for p in ps):.1f}</td></tr>" for rd, ps in sorted(rounds.items()) if rd <= 12)
    owners = sorted(d.read_csv("draft_owners.csv"), key=lambda r: -float(r["any_team_over_slot"]))
    orows = "".join(f"<tr><td class='l'>{team_link(r['owner'])}</td><td>{r['picks']}</td><td>{r['hit_rate']}%</td>"
                    f"<td>{r['kept_rate']}%</td><td>{float(r['any_team_over_slot']):+.2f}</td>"
                    f"<td>{float(r['starts_over_slot']):+.2f}</td><td>{r['started_elsewhere']}%</td></tr>" for r in owners)
    years = "".join(f"<a class='chip' href='{y}.html'>{y}</a>" for y in sorted(by_year, reverse=True))
    legacy = "".join(f"<a class='chip' href='{LEGACY}/{BOARDS[y]}'>{y}</a>" for y in sorted(BOARDS, reverse=True))
    body = ("<div class='season'><h1>Drafts</h1><p class='lede'>The annual draft of rookies and free agents. From 2008 "
            "every pick is here with how it turned out over three seasons. Earlier drafts are on the original site's "
            "draft boards.</p>"
            f"<h2>By year</h2><p class='names'>{years}</p><p class='meta'>On the original site:</p><p class='names'>{legacy} "
            f"<a class='chip' href='{LEGACY}/pdl2001/setup/expdraft.html'>2001 expansion</a></p>"
            "<h2>What a round is worth</h2><p class='meta'>Drafts 2008 to 2023, whose three seasons are all played. A hit is "
            "10 or more starts for any team: a drafted player is also trade currency, so a pick that became a starter "
            "elsewhere still worked. Kept is 10 or more for the team that drafted him. Kickers and defenses start every "
            "week once drafted, so the skill positions column is the fairer read of the middle rounds.</p>"
            "<div class='table-wrap'><table class='data'>"
            "<thead><tr><th>Round</th><th>Picks</th><th>Hit rate</th><th>Skill positions</th><th>Kept</th><th>Starts per pick</th></tr>"
            f"</thead><tbody>{rrows}</tbody></table></div>"
            "<h2>Who drafts well</h2><p class='meta'>Starts a pick above what that point in the draft usually yields, "
            "for any team (did he pick a player who became a starter) and for the drafting team (did that player "
            "start for him). Differences under about 1.5 starts a pick are within chance. The full method is in the "
            "<a href='../analysis/draft-value.html'>draft value report</a>.</p><div class='table-wrap'><table class='data'>"
            "<thead><tr><th class='l'>Team</th><th>Picks</th><th>Hit rate</th><th>Kept</th><th>Over slot, any team</th><th>Over slot, his team</th>"
            f"<th>Started elsewhere</th></tr></thead><tbody>{orows}</tbody></table></div></div>")
    return page("PDL drafts", body, description="Every PDL draft pick since 2008.")


def build(dist):
    os.makedirs(f"{dist}/drafts", exist_ok=True)
    by_year = defaultdict(list)
    for p in d.draft_value():
        by_year[int(p["season"])].append(p)
    years = set(by_year)
    for y, picks in by_year.items():
        with open(f"{dist}/drafts/{y}.html", "w") as f:
            f.write(year_page(y, picks, years))
    with open(f"{dist}/drafts/index.html", "w") as f:
        f.write(index_page(by_year))
    return len(by_year) + 1
