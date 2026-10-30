"""The Moose easter eggs, driven by site/eggs.json. None changes a number or a rule.

    antlers(html)            in every table, the team's name gets an antler on hover
    banner_class(champion)   the title-season watermark
    season_tooltip(season)   a tooltip on a season's title
    rivalry_caption(a, b, r) a line on the team's best series and every series it loses
    build(dist)              the 404 page and the unlinked museum at /moose/, and the F-Jackie
                             egg's hint (the egg itself, typing "barney", is assets/barney.js),
                             and the arrival eggs on franchise pages
"""
import json, os, re
from functools import lru_cache

import league_data as d
from frame import E, num, page, record, slug, ver

SITE = os.path.dirname(os.path.abspath(__file__))


@lru_cache(maxsize=None)
def config():
    return json.load(open(f"{SITE}/eggs.json"))


def team():
    return config()["team"]


def antlers(html):
    """Wrap the team's name in table links, only inside tables."""
    name = re.escape(E(team()))

    def in_table(m):
        return re.sub(rf">({name})</a>", r"><span class='moose'>\1</span></a>", m.group(0))
    return re.sub(r"<table.*?</table>", in_table, html, flags=re.S)


def banner_class(champion):
    return " moose-title" if champion == team() else ""


def season_tooltip(season):
    return config().get("season_tooltips", {}).get(str(season), "")


@lru_cache(maxsize=None)
def best_series():
    """The team's most one-sided winning series (20 or more games)."""
    rows = [(opp, r) for opp, r in d.head_to_head().get(team(), {}).items() if r["games"] >= 20]
    return max(rows, key=lambda x: (x[1]["w"] - x[1]["l"]) / x[1]["games"])[0] if rows else None


def rivalry_caption(a, b, r):
    """r is the record of a against b."""
    t = team()
    if t not in (a, b):
        return ""
    opp = b if a == t else a
    w, l = (r["w"], r["l"]) if a == t else (r["l"], r["w"])
    caps = config()["rivalry_captions"]
    if opp == best_series():
        return f"<p class='egg'>{E(caps['best'].format(team=t, opp=opp, w=w, l=l))}</p>"
    if l > w:
        return f"<p class='egg'>{E(caps['losing'].format(team=t, opp=opp, w=w, l=l))}</p>"
    return ""


def moose_svg():
    return open(f"{SITE}/assets/manic-moose.svg").read()


def not_found():
    c = config()["not_found"]
    # GitHub Pages serves this at any depth, so links are from the site root
    body = (f"<div class='home lost'><div class='runner' aria-hidden='true'>{moose_svg()}</div>"
            f"<h1>{E(c['title'])}</h1><p class='lede'>{E(c['text'])}</p>"
            "<p><a href='/pdl/'>Back to the league</a></p></div>")
    html = page("Retained by the Moose", body, depth=0, description="Page not found.")
    return html.replace('href="assets/', 'href="/pdl/assets/').replace('src="assets/', 'src="/pdl/assets/') \
               .replace('href="index.html"', 'href="/pdl/"').replace('href="seasons/', 'href="/pdl/seasons/') \
               .replace('href="franchises/', 'href="/pdl/franchises/').replace('href="h2h/', 'href="/pdl/h2h/') \
               .replace('href="trades/', 'href="/pdl/trades/').replace('href="drafts/', 'href="/pdl/drafts/') \
               .replace('href="records/', 'href="/pdl/records/').replace('href="analysis/', 'href="/pdl/analysis/') \
               .replace('href="rules/', 'href="/pdl/rules/')


def museum():
    t = team()
    c = config()["museum"]
    seasons = [y for y in d.seasons() if y in d.champions()]
    titles = sorted(y for y in seasons if d.champions()[y] == t)
    w, l, ties = d.regular_record(t)
    rates = sorted(((sum(x[:1]) + 0.5 * x[2]) / max(1, sum(x)), o) for o in d.identities() for x in [d.regular_record(o)])
    rank = [o for _, o in sorted(rates, reverse=True)].index(t) + 1
    pw, pl = d.playoff_record(t)
    case = []
    for y in titles:
        g = d.final(y)
        if g:
            ms, os_ = (g["score_a"], g["score_b"]) if g["team_a"] == t else (g["score_b"], g["score_a"])
            case.append(f"<li><a href='../seasons/{y}.html'>{y}</a>: beat {E(d.runner_up(y))} {num(ms)} to {num(os_)}</li>")
    best = best_series()
    br = d.head_to_head()[t][best] if best else None
    finals = [y for y in seasons if d.finish(y, t) == "runner-up"]
    body = (f"<div class='home museum'><div class='runner' aria-hidden='true'>{moose_svg()}</div>"
            f"<h1>{E(c['title'])}</h1><p class='lede'>{E(c['text'])}</p>"
            f"<div class='facts'><div class='fact'><span class='k'>The best win rate in the league</span><span class='v'>"
            f"{(w + 0.5 * ties) / max(1, w + l + ties):.3f}".replace("0.", ".", 1) + f" in the regular season, {record(w, l, ties)}"
            f"{'' if rank == 1 else f' (rank {rank}, but the Moose prefer not to discuss it)'}</span></div>"
            f"<div class='fact'><span class='k'>Titles</span><span class='v'>{len(titles)}</span></div>"
            f"<div class='fact'><span class='k'>Playoff record</span><span class='v'>{record(pw, pl)}</span></div>"
            f"<div class='fact'><span class='k'>Super Bowl appearances</span><span class='v'>{len(titles) + len(finals)}</span></div></div>"
            f"<h2>The trophy case</h2><ul>{''.join(case)}</ul>"
            + (f"<h2>The rivalry</h2><p>{E(best)}: {record(br['w'], br['l'], br['t'])} in {br['games']} games.</p>" if best else "")
            + f"<p><a href='../franchises/{slug(t)}.html'>The official record</a></p></div>")
    return page(c["title"], body, description="America's Team.")


def arrive(dist, t, call, scripts=(), extra=""):
    """Run call when team t's franchise page loads, after extra (markup) and scripts (in assets/)."""
    p = f"{dist}/franchises/{slug(t)}.html"
    if not os.path.exists(p):
        return
    tag = "".join(f"<script src='../assets/{sc}?v={ver('assets/' + sc)}'></script>" for sc in scripts)
    html = open(p).read().replace("</body>", f"{extra}{tag}<script>addEventListener('load', () => {call});</script></body>", 1)
    open(p, "w").write(html)


def caption(c):
    """A clip's caption, if it has one, with {playoffs} and {seasons}: the team's playoff trips and
    finished seasons."""
    if "caption" not in c:
        return None
    done = [y for y in d.seasons() if y in d.champions()]
    seasons = [y for y in d.identities()[c["team"]]["seasons"] if y in done]
    return c["caption"].format(playoffs=sum(1 for y in seasons if d.finish(y, c["team"])), seasons=len(seasons))


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def magazine():
    """The Karpet Munchers' draft guide, a <template> for assets/clip.js. Its can't-miss sleepers
    are the team's four worst early picks: rounds 1 and 2, 2008 on, by starts under what the
    slot usually yields."""
    m = config()["magazine"]
    picks = sorted((r for r in d.draft_value() if r["team"] == m["team"] and r["complete"] == "True" and int(r["round"]) <= 2),
                   key=lambda r: float(r["starts_over_slot"]))[:4]
    names = "".join(f"<li>{E(' '.join(reversed(r['player'].split(', '))))}</li>" for r in picks)
    slots = sorted(int(r["overall"]) for r in picks)
    got = sum(int(r["starts_any_team"]) for r in picks)
    usual = round(sum(float(r["expected_starts"]) for r in picks))
    since = d.identities()[m["team"]]["first_season"]
    return (f"<template id='pdl-magazine'><aside class='mag' title='Click to close'>"
            f"<div class='mag-top'><span>{max(d.seasons())} Draft Guide</span><span>$7.99 US<br>$9.99 CAN</span></div>"
            f"<div class='mag-title'>PDL<small>Fantasy Football</small></div>"
            f"<div class='mag-burst'>300 players ranked!</div>"
            f"<div class='mag-line'><b>Can't-miss sleepers!</b><ul>{names}</ul></div>"
            f"<div class='mag-line mag-small'>{E(m['cover_line'])} Mock drafts! Bye weeks!</div>"
            f"<div class='mag-foot'><div class='mag-label'>{E(m['team']).upper()}<br>SUBSCRIBER SINCE {since}</div>"
            f"<div class='mag-barcode'></div></div>"
            f"<p class='mag-note'>Printed in June, before training camp. Drafted {ordinal(slots[0])} to "
            f"{ordinal(slots[-1])} overall by the {E(m['team'])}, these four started {got} PDL games between "
            f"them in their first three seasons. Those draft slots usually yield {usual}. {E(m['note_extra'])}</p>"
            f"</aside></template>")


def grumbles():
    """Ho Train's lines: eggs.json's, and two from the record, its best season and this one."""
    g = config()["grumpy_train"]
    done = [y for y in d.seasons() if y in d.champions()]
    rows = [(y, r) for y in d.seasons() for r in d.standings(y) if r["team"] == g["team"]]
    pct = lambda r: (r["w"] + 0.5 * r["t"]) / max(1, r["w"] + r["l"] + r["t"])
    by, br = max(((y, r) for y, r in rows if y in done), key=lambda x: (pct(x[1]), x[1]["pf"]))
    lines = list(g["lines"]) + [g["best"].format(year=by, record=record(br["w"], br["l"], br["t"]))]
    ny, nr = rows[-1]
    if ny not in done:
        lines.append(g["now"].format(record=record(nr["w"], nr["l"], nr["t"])))
    return lines


def build_log(dist):
    """The commissioner's build log, eggs.json's lines filled in from the record and the site."""
    root = os.path.dirname(SITE)
    titles = sorted(y for y, t in d.champions().items() if t == team())
    facts = {
        "seasons": len(d.seasons()), "games": f"{len(d.games()):,}",
        "changes": len(json.load(open(f"{root}/rules/ledger.json"))["changes"]),
        "titles": len(titles), "title_years": ", ".join(map(str, titles)),
        "pages": sum(f.endswith(".html") for _, _, fs in os.walk(dist) for f in fs),
    }
    return [line.format(**facts) for line in config()["build_log"]["lines"]]


def build(dist):
    with open(f"{dist}/404.html", "w") as f:
        f.write(not_found())
    os.makedirs(f"{dist}/{config()['museum']['path']}", exist_ok=True)
    with open(f"{dist}/{config()['museum']['path']}/index.html", "w") as f:
        f.write(museum())
    # each team's own franchise page sets its egg off on arrival: Barney for F-Jackie (whose
    # title also carries the hint), Moose mode for the Moose, a clip for the teams in
    # eggs.json's "clips", the draft guide for the Karpet Munchers, the power cut for the Texas
    # Nashvillians, the trade offer for Couchfire and the grumpy engine for Ho Train. The scripts are assets/*.js.
    b = config()["barney"]
    p = f"{dist}/franchises/{slug(b['team'])}.html"
    if os.path.exists(p):
        html = open(p).read().replace("<h1>", f"<h1 title='{E(b['hint'])}'>", 1)
        open(p, "w").write(html)
    arrive(dist, b["team"], "window.pdlBarney && pdlBarney()")
    arrive(dist, team(), "window.pdlMoose && pdlMoose()")
    # and once the moose has run, the commissioner's build log
    arrive(dist, team(), f"setTimeout(() => pdlBuildLog({json.dumps(build_log(dist))}), {config()['build_log']['delay_ms']})",
           ["commish.js"])
    # the rest have no other trigger, so their scripts load on those pages alone
    for c in config()["clips"]:
        arrive(dist, c["team"], f"pdlClip({json.dumps(c['clip'])}, {c['seconds']}, {json.dumps(c.get('youtube'))}, "
                                f"{json.dumps(caption(c))})", ["clip.js"])
    m = config()["magazine"]
    arrive(dist, m["team"], f"pdlMagazine({m['seconds']})", ["clip.js"], magazine())
    arrive(dist, config()["outage"]["team"], "pdlOutage()", ["outage.js"])
    t = config()["trade_offer"]
    arrive(dist, t["team"], f"setTimeout(() => pdlTradeOffer({json.dumps({k: v for k, v in t.items() if k != 'what'})}), 800)", ["clip.js", "trade.js"])
    g = config()["grumpy_train"]
    arrive(dist, g["team"], f"pdlGrumpyTrain({json.dumps(grumbles())})", ["train.js"])
    # the antlers go on last, over every finished page
    n = 0
    for root, _, files in os.walk(dist):
        for name in files:
            if name.endswith(".html"):
                p = os.path.join(root, name)
                html = open(p).read()
                new = antlers(html)
                if new != html:
                    open(p, "w").write(new)
                    n += 1
    return n
