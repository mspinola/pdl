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
    html = open(p).read().replace("</body>", f"{extra}{tag}<script>addEventListener('load', () => {{ {call}; }});</script></body>", 1)
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
    # the Pounders' and the Otters' heckles, the Munchers' own trades and seasons filled in
    trades = sum(1 for x in d.trades() if m["team"] in (x["team_a"], x["team_b"]))
    facts = {"trades": trades, "seasons": len(d.identities()[m["team"]]["seasons"])}
    heckles = "".join(f"<p class='mag-heckle mag-heckle-{i}'>{E(h['text'].format(**facts))}<i>{E(h['by'])}</i></p>"
                      for i, h in enumerate(m["heckles"], 1))
    return (f"<template id='pdl-magazine'><aside class='mag' title='Click to close'>"
            f"<div class='mag-top'><span>{max(d.seasons())} Draft Guide</span><span>$7.99 US<br>$9.99 CAN</span></div>"
            f"<div class='mag-title'>PDL<small>Fantasy Football</small></div>"
            f"<div class='mag-burst'>300 players ranked!</div>"
            f"<div class='mag-line'><b>Can't-miss sleepers!</b><ul>{names}</ul></div>"
            f"<div class='mag-line mag-small'>{E(m['cover_line'])} Mock drafts! Bye weeks!</div>"
            f"{heckles}"
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
    losses = [y for y in d.seasons() if d.finish(y, team()) == "runner-up"]
    facts.update(losses=len(losses), loss_years=", ".join(map(str, losses)))
    # schedule luck, as the franchise pages give it: wins against what the scoring was worth
    luck = sorted(d.by_owner("luck_owners.csv").items(), key=lambda kv: -float(kv[1]["luck"]))
    rank = [t for t, _ in luck].index(team()) + 1
    facts.update(luck=f"{float(dict(luck)[team()]['luck']):+.1f}", luck_rank=ordinal(rank),
                 luckier=luck[0][0], luckier_luck=f"{float(luck[0][1]['luck']):+.1f}")
    # trades the record marks as processed by the commissioner, the Moose's and everyone else's
    mine = [x for x in d.trades() if team() in (x["team_a"], x["team_b"])]
    others = [x for x in d.trades() if team() not in (x["team_a"], x["team_b"])]
    facts.update(trades=len(mine), by_commish=sum(x["by_commish"] for x in mine),
                 mine_rate=round(100 * sum(x["by_commish"] for x in mine) / max(1, len(mine))),
                 others_rate=round(100 * sum(x["by_commish"] for x in others) / max(1, len(others))))
    b = config()["build_log"]
    lines = []
    for line in b["lines"]:
        lines += b["luck_lines" if rank > 1 else "luck_first_lines"] if line == "{luck_block}" else [line]
    return [line.format(**facts) for line in lines]


def y2k():
    """The Dunbar Dogs' home page from 2000, a <template> for assets/y2k.js, its news from the rule
    book's ledger (the divisions drawn from a hat, then restored) and the team's draft picks."""
    y = config()["y2k"]
    ledger = {c["id"]: c for c in json.load(open(f"{os.path.dirname(SITE)}/rules/ledger.json"))["changes"]}
    hat, back = int(ledger[y["redraw"]]["effective"]), int(ledger[y["restore"]]["effective"])
    picks = [r for r in d.all_drafts() if r["team"] == y["team"]]
    wr = sum(r["position"] == "WR" for r in picks)
    facts = {"restored": back, "hat_seasons": back - hat, "changes": len(ledger), "wr": wr,
             "wr_pct": round(100 * wr / len(picks)), "team": y["team"]}
    new = "<b class='y2k-new'>NEW!</b>"
    news = "".join(f"<tr><td>{new if i == 0 else ''}</td><td>{E(line.format(**facts))}</td></tr>"
                   for i, line in enumerate(y["news"]))
    return (f"<template id='pdl-y2k'><div class='y2k-top'>"
            f"<div class='y2k-marquee'><span>{E(y['marquee'])}</span></div>"
            f"<p class='y2k-h'>{E(y['welcome'].format(**facts))}</p>"
            f"<div class='y2k-construction'><span>UNDER CONSTRUCTION</span></div>"
            f"<table class='y2k-news'><tr><th colspan='2'>LEAGUE NEWS</th></tr>{news}</table>"
            f"<p class='y2k-counter'>You are visitor number <span></span></p>"
            f"<p class='y2k-small'>{E(y['footer'])}</p>"
            f"<button type='button' class='y2k-off'>{E(y['button'])}</button></div></template>")


def tank_facts():
    """The tank season: the year before the team drafted the player 1st overall, its record and
    points against the next-lowest, his starts, and the titles since."""
    k = config()["tank"]
    pick = next(r for r in d.all_drafts() if r["team"] == k["team"] and r["player"] == k["player"])
    drafted = int(pick["season"])
    st = d.standings(drafted - 1)
    me = next(r for r in st if r["team"] == k["team"])
    others = min(r["pf"] for r in st if r["team"] != k["team"])
    first, last = (pick["player"].split(", ") + [""])[1], pick["player"].split(", ")[0]
    return {"year": drafted - 1, "draft_year": drafted, "record": record(me["w"], me["l"], me["t"]),
            "pf": num(me["pf"]), "gap": num(others - me["pf"]), "player": f"{first} {last}", "last": last,
            "overall": ordinal(int(pick["overall"])), "starts": pick["starts_any_team"],
            "titles": sum(1 for y, t in d.champions().items() if t == k["team"] and y >= drafted)}


def tank_card():
    k, f = config()["tank"], tank_facts()
    return {"flag": E(k["flag"].format(**f)), "title": k["title"].format(**f), "grade": k["grade"],
            "lines": [line.format(**f) for line in k["lines"]]}


def attendance():
    """The Tally Wackers' draft and meeting sign-in sheet, a <template> for assets/clip.js: present
    in eggs.json's years, absent in every other season."""
    k, f = config()["tank"], tank_facts()
    a = k["attendance"]
    cells = "".join(f"<span>{y} " + ("<i class='attend-yes'>&#10003;</i>" if y in a["present"] else "<i class='attend-no'>ABSENT</i>")
                    + "</span>" for y in d.seasons())
    notes = "".join(f"<p class='attend-note'>{E(n.format(**f))}</p>" for n in a["notes"])
    return (f"<template id='pdl-attendance'><aside class='attend' title='Click to close'><div class='attend-paper'>"
            f"<h3>{E(a['title'])}</h3><p>Sign-in sheet: {E(k['team'])}</p><div class='attend-grid'>{cells}</div>"
            f"{notes}</div></aside></template>")


def beers():
    """Beers' notes and rumors, for assets/notes.js and rumor.js: a page on every franchise they
    have traded with (trades from the record, the scrawl from eggs.json), and the rumor mill with
    its blanks filled in from the same counts."""
    b = config()["beers"]
    partners = {}
    for x in d.trades():
        for me, them in ((x["team_a"], x["team_b"]), (x["team_b"], x["team_a"])):
            if me == b["team"]:
                partners[them] = partners.get(them, 0) + 1
    total = sum(partners.values())
    ranked = sorted(partners.items(), key=lambda kv: -kv[1])
    scrawl = b["scrawl"]
    pages = [[t.upper(), f"{n} trades w/ us", b["about"].get(t, scrawl[i % len(scrawl)])] for i, (t, n) in enumerate(ranked)]
    pages += b["extra_pages"]
    most = max(sum(1 for x in d.trades() if t in (x["team_a"], x["team_b"])) for t in d.identities() if t != b["team"])
    facts = {"team": b["team"], "total": total, "franchises": len(partners), "top": ranked[0][0], "top_n": ranked[0][1],
             "top_next": ranked[0][1] + 1, "next_most": most}
    notes = {"team": b["team"], "seconds": b["notes_seconds"], "pages": pages,
             "partners": [{"team": t, "n": n} for t, n in ranked], "total": b["total"].format(**facts)}
    rumors = {"label": b["label"], "rumors": [r.format(**facts) for r in b["rumors"]]}
    return notes, rumors


@lru_cache(maxsize=None)
def roster_runs():
    """Every run of seasons in a row a player spent on one team's roster, from the archived MFL
    rosters (2003 on): (seasons, first, last, player id, team), longest first."""
    root = os.path.dirname(SITE)
    on = {}
    years = sorted(int(y) for y in os.listdir(f"{root}/mfl_archive") if y.isdigit())
    for yr in years:
        names = {f["id"]: f["name"] for f in json.load(open(f"{root}/mfl_archive/{yr}/league.json"))["league"]["franchises"]["franchise"]}
        for f in json.load(open(f"{root}/mfl_archive/{yr}/rosters.json"))["rosters"]["franchise"]:
            for pl in (f["player"] if isinstance(f.get("player"), list) else [f["player"]] if f.get("player") else []):
                on.setdefault((names[f["id"]], pl["id"]), []).append(yr)
    runs = []
    for (t, pid), ys in on.items():
        start = prev = ys[0]
        for y in ys[1:] + [None]:
            if y != prev + 1 if y is not None else True:
                runs.append((prev - start + 1, start, prev, pid, t))
                start = y
            prev = y if y is not None else prev
    return sorted(runs, reverse=True), years[0]


def player_name(pid):
    idx = json.load(open(f"{os.path.dirname(SITE)}/player_index.json"))
    last, _, first = idx.get(pid, {}).get("name", pid).partition(", ")
    return f"{first} {last}".strip()


def plaque():
    """The Iron City Pounders' plaque: their longest-kept player, if it is the archive's longest
    run on any roster, the runner-up on their own roster, and their trades over that run."""
    ic = config()["iron_city"]
    runs, since = roster_runs()
    mine = [r for r in runs if r[4] == ic["team"]]
    n, start, end, pid, _ = mine[0]
    record = runs[0][4] == ic["team"]
    in_run = [x for x in d.trades() if ic["team"] in (x["team_a"], x["team_b"]) and start <= int(x["season"]) <= end]
    quiet = [y for y in range(start, end + 1) if not any(int(x["season"]) == y for x in in_run)]
    facts = {"player": player_name(pid), "n": n, "start": start, "end": end, "since": since,
             "runner": player_name(mine[1][3]), "runner_n": mine[1][0], "trades": len(in_run), "quiet": len(quiet),
             "record": ic["record"].format(since=since) if record else ""}
    lines = "".join(f"<p>{E(line.format(**facts))}</p>" for line in ic["plaque_lines"])
    return (f"<div class='plaque' title='{E(ic['plaque_hint'])}'><div class='plaque-brass'><b>{E(ic['plaque_title'])}</b>"
            f"<small>{E(ic['plaque_sub'].format(**facts))}</small><strong>{E(facts['player'])}</strong>{lines}"
            f"<em>{E(ic['motto'])}</em></div></div>")


def autumn():
    """The Iron City Pounders' Autumn Bowl program, a <template> for assets/clip.js."""
    ic = config()["iron_city"]
    b = ic["program"]
    return (f"<template id='pdl-autumn'><aside class='bowl' title='Click to close'>"
            f"<p class='bowl-parish'>{E(b['masthead'])}</p><h3>{E(b['title'])}</h3>"
            f"<p class='bowl-vs'>{E(b['home'])}<span>vs.</span>{E(b['away'])}</p>"
            + "".join(f"<p>{E(t)}</p>" for t in b["details"])
            + f"<hr><p class='bowl-feat'>{E(b['featuring'].format(team=ic['team']))}</p>"
            f"<p class='bowl-small'>{E(b['footer'])}</p></aside></template>")


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
    # the Moose's own page crosses out its Super Bowl losses in favour of appearances
    r = config()["relabel"]
    p = f"{dist}/franchises/{slug(team())}.html"
    if os.path.exists(p):
        html = open(p).read().replace(f"<span class='k'>{E(r['from'])}</span>",
                                      f"<span class='k'><s>{E(r['from'])}</s> {E(r['to'])}</span>", 1)
        open(p, "w").write(html)
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
    # the Tally Wackers' tank rolls through while the tube man flails, and the attendance sheet
    # follows once he has gone
    k = config()["tank"]
    arrive(dist, k["team"], f"pdlTank({json.dumps(tank_card())}); setTimeout(() => pdlCard('pdl-attendance', "
                            f"{k['sheet_seconds']}), {k['sheet_after_ms']})", ["tank.js"], attendance())
    # the Iron City Pounders: the Autumn Bowl program on arrival, and the plaque on the wall
    ic = config()["iron_city"]
    arrive(dist, ic["team"], f"pdlCard('pdl-autumn', {ic['program_seconds']})", ["clip.js"], autumn())
    p = f"{dist}/franchises/{slug(ic['team'])}.html"
    if os.path.exists(p):
        html = open(p).read().replace("</h1>", "</h1>" + plaque(), 1)
        open(p, "w").write(html)
    bc = config()["beers"]
    notes, rumors = beers()
    arrive(dist, bc["team"], f"setTimeout(() => pdlNotes({json.dumps(notes)}), {bc['notes_after_ms']}); "
                             f"setTimeout(() => pdlRumors({json.dumps(rumors)}), {bc['rumors_after_ms']})",
           ["notes.js", "rumor.js"])
    y = config()["y2k"]
    arrive(dist, y["team"], f"setTimeout(pdlY2K, {y['delay_ms']})", ["y2k.js"], y2k())
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
