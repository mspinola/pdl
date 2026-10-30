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
from frame import E, num, page, record, slug

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


def build(dist):
    with open(f"{dist}/404.html", "w") as f:
        f.write(not_found())
    os.makedirs(f"{dist}/{config()['museum']['path']}", exist_ok=True)
    with open(f"{dist}/{config()['museum']['path']}/index.html", "w") as f:
        f.write(museum())
    # each team's own franchise page sets its egg off on arrival: Barney for F-Jackie (whose
    # title also carries the hint), Moose mode for the Moose, a clip for the teams in
    # eggs.json's "clips". The scripts are assets/*.js.
    b = config()["barney"]
    for t, call, hint in ((b["team"], "pdlBarney", b["hint"]), (team(), "pdlMoose", None)):
        p = f"{dist}/franchises/{slug(t)}.html"
        if os.path.exists(p):
            html = open(p).read()
            if hint:
                html = html.replace("<h1>", f"<h1 title='{E(hint)}'>", 1)
            html = html.replace("</body>", f"<script>addEventListener('load', () => window.{call} && {call}());</script></body>", 1)
            open(p, "w").write(html)
    # the arrival clips have no other trigger, so their script loads on those pages alone
    for c in config()["clips"]:
        p = f"{dist}/franchises/{slug(c['team'])}.html"
        if os.path.exists(p):
            html = open(p).read().replace("</body>", "<script src='../assets/clip.js'></script><script>addEventListener("
                                          f"'load', () => pdlClip({json.dumps(c['clip'])}, {c['seconds']}));</script></body>", 1)
            open(p, "w").write(html)
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
