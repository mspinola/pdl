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
    finished seasons. A clip with a "pick" (season and player) also gets {pick}, that pick, and
    {next}, the next three picks. A newline in a caption is kept."""
    if "caption" not in c:
        return None
    done = [y for y in d.seasons() if y in d.champions()]
    seasons = [y for y in d.identities()[c["team"]]["seasons"] if y in done]
    facts = {"playoffs": sum(1 for y in seasons if d.finish(y, c["team"])), "seasons": len(seasons)}
    if "pick" in c:
        board = sorted((r for r in d.all_drafts() if r["season"] == str(c["pick"]["season"])), key=lambda r: int(r["overall"]))
        i = next(i for i, r in enumerate(board) if r["player"] == c["pick"]["player"])
        name = lambda r: " ".join(reversed(r["player"].split(", ")))
        after = [name(r) for r in board[i + 1:i + 4]]
        facts.update(pick=name(board[i]), overall=ordinal(int(board[i]["overall"])), year=c["pick"]["season"],
                     next=", ".join(after[:-1]) + " and " + after[-1])
    return c["caption"].format(**facts)


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
            "lines": [line.format(**f) for line in k["lines"]], "heckle": k.get("heckle")}


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


def rx():
    """F-Jackie's prescription, a <template> for assets/clip.js: the diagnosis is the team's schedule
    luck against the league's, from the luck table the franchise pages use."""
    r = config()["rx"]
    luck = sorted(d.by_owner("luck_owners.csv").items(), key=lambda kv: float(kv[1]["luck"]))
    names = [t for t, _ in luck]
    rank = names.index(r["team"]) + 1
    other = luck[1] if rank == 1 else luck[0]
    facts = {"team": r["team"], "luck": f"{float(dict(luck)[r['team']]['luck']):+.1f}",
             "rank": "the worst in the league" if rank == 1 else f"{ordinal(rank)} worst in the league",
             "other": other[0], "other_luck": f"{float(other[1]['luck']):+.1f}",
             "other_label": "next worst" if rank == 1 else "worst"}
    # a scrawled signature
    sign = ("<svg class='rx-sign' viewBox='0 0 130 30' aria-hidden='true'><path d='M4 22 C14 2 20 30 28 14 S40 4 44 18 "
            "S58 26 62 12 S74 2 80 20 S96 28 102 10 S118 6 126 16' fill='none' stroke='#1b3f8f' stroke-width='2'/></svg>")
    body = "".join(f"<p>{E(line.format(**facts))}</p>" for line in r["lines"])
    return (f"<template id='pdl-rx'><aside class='rx' title='Click to close'><div class='rx-head'><b>{E(r['doctor'])}</b>"
            f"<small>{E(r['clinic'])}</small></div><div class='rx-body'>{body}"
            f"<span class='rx-sym'>&#8478;</span><p class='rx-script'>{E(r['script'])}</p>"
            f"<p class='rx-second'>{E(r['second'])}</p>{sign}</div></aside></template>")


def page_heckle(h):
    """A quote pinned to a franchise page, signed, with a line checked against the record if it has a
    "check": {playoffs},
    {finals} and {titles} for the team, {next_team} and {next_playoffs}, the most playoff trips
    of any other team without a title, and {season}, {record_now}, {rank_now} and {teams} for this
    season so far."""
    done = [y for y in d.seasons() if y in d.champions()]
    def counts(t):
        return (sum(1 for y in done if d.finish(y, t)), sum(1 for y in done if d.finish(y, t) in ("champion", "runner-up")),
                sum(1 for y in done if d.champions()[y] == t))
    quote = f"<p class='page-heckle'>\u201c{E(h['text'])}\u201d<i>{E(h['by'])}</i>"
    # the check is optional: some things said (trade offers, for one) are not in the record
    if "check" not in h:
        return quote + "</p>"
    playoffs, finals, titles = counts(h["team"])
    rest = sorted(((counts(t)[0], t) for t in d.identities() if t != h["team"] and counts(t)[2] == 0), reverse=True)
    # and this season so far: {record_now}, {rank_now} of {teams}
    now = max(d.seasons())
    table = sorted(d.standings(now), key=lambda r: (-(r["w"] + .5 * r["t"]) / max(1, r["w"] + r["l"] + r["t"]), -r["pf"]))
    facts = {"playoffs": playoffs, "finals": finals, "titles": titles, "next_team": rest[0][1], "next_playoffs": rest[0][0],
             "season": now, "teams": len(table)}
    # a franchise no longer playing has no season so far
    rank, me = next(((i, r) for i, r in enumerate(table, 1) if r["team"] == h["team"]), (None, None))
    if me:
        facts.update(record_now=record(me["w"], me["l"], me["t"]), rank_now=ordinal(rank))
    return quote + f"<small>{E(h['check'].format(**facts))}</small></p>"


def draft_grade():
    """Scooter's Boozers' self-graded draft card, a <template> for assets/clip.js: the A+, then the
    record's revision, the share of picks that became starters (finished drafts, 2008 on, as the
    franchise pages count it) for the team and the league, overall and since eggs.json's year."""
    g = config()["draft_grade"]
    picks = [r for r in d.draft_value() if r["complete"] == "True"]
    rate = lambda rs: round(100 * sum(r["hit"] == "True" for r in rs) / max(1, len(rs)), 1)
    mine = [r for r in picks if r["team"] == g["team"]]
    recent = lambda rs: [r for r in rs if int(r["season"]) >= g["since"]]
    facts = {"team": g["team"], "rate": rate(mine), "league": rate(picks), "since": g["since"],
             "last": max(int(r["season"]) for r in picks),
             "recent": round(rate(recent(mine))), "recent_league": round(rate(recent(picks)))}
    revised = "".join(f"<p>{line.format(**{k: E(str(v)) for k, v in facts.items()})}</p>" for line in g["revised"])
    return (f"<template id='pdl-grade'><aside class='grade' title='Click to close'><h3>{E(g['title'])}</h3>"
            + "".join(f"<p class='grade-meta'>{E(line.format(**facts))}</p>" for line in g["meta"])
            + f"<span class='grade-mark'>{E(g['grade'])}</span><span class='grade-stamp'>REVISED</span>"
            f"<div class='grade-revised'>{revised}</div></aside></template>")


def out_of_office():
    """F-Jackie's former co-manager's automatic reply, a <template> for assets/clip.js, the rule
    book's changes counted from its ledger."""
    oo = config()["out_of_office"]
    changes = len(json.load(open(f"{os.path.dirname(SITE)}/rules/ledger.json"))["changes"])
    body = "".join(f"<p>{E(line.format(team=oo['team']))}</p>" for line in oo["body"])
    rules = E(oo["rules"]).replace("{link}", f"<a href='../rules/index.html'>{E(oo['link_text'])}</a>").replace("{changes}", str(changes))
    envelope = ("<svg viewBox='0 0 16 12' aria-hidden='true'><rect x='.5' y='.5' width='15' height='11' rx='1.5' fill='none' "
                "stroke='#555'/><path d='M1 1 L8 7 L15 1' fill='none' stroke='#555'/></svg>")
    return (f"<template id='pdl-ooo'><aside class='ooo' title='Click to close'><div class='ooo-head'>{envelope}"
            f"{E(oo['app'])}</div><div class='ooo-body'><p class='ooo-from'>From: {E(oo['from'])}</p>"
            f"<p class='ooo-subject'>{E(oo['subject'].format(team=oo['team']))}</p>{body}<p>{rules}</p></div></aside></template>")


def texts():
    """Blitzkrieg's unanswered texts, a <template> for assets/clip.js. Each sender's {n} is their
    trades with the team, from the record, and {next} one more; the last line is its latest title."""
    tx = config()["texts"]
    me = tx["team"]
    pairs = {}
    for x in d.trades():
        if me in (x["team_a"], x["team_b"]):
            other = x["team_b"] if x["team_a"] == me else x["team_a"]
            pairs[other] = pairs.get(other, 0) + 1
    seasons = len(d.identities()[me]["seasons"])
    msgs = ""
    for i, m in enumerate(tx["messages"]):
        n = pairs.get(m["from"], 0)
        text = m["text"].format(n=n, next=n + 1, seasons=seasons)
        msgs += (f"<p class='sms-from' style='--i:{i}'>{E(m['from'])}</p>"
                 f"<p class='sms-msg' style='--i:{i}'>{E(text)}</p>")
    last = len(tx["messages"]) - 1
    msgs += f"<p class='sms-status' style='--i:{last}'>Delivered</p>"
    at = round(.7 + .9 * len(tx["messages"]) + .4, 1)
    titles = sorted(y for y, t in d.champions().items() if t == me)
    system = E(tx["system"]).replace("{title}", f"<b>{titles[-1]}</b>") if titles else ""
    return (f"<template id='pdl-texts'><aside class='sms' title='Click to close' style='--at:{at};--wait:{tx['typing_seconds']}'>"
            f"<div class='sms-head'><span class='sms-avatar'>{E(me[0])}</span><b>{E(me)}</b>"
            f"<small>{E(tx['status'].format(seasons=seasons))}</small></div><div class='sms-body'>{msgs}"
            f"<div class='sms-end'><span class='sms-typing' aria-label='typing'><i></i><i></i><i></i></span>"
            f"<p class='sms-system'>{system}</p></div></div></aside></template>")


@lru_cache(maxsize=None)
def nfl_teams(season):
    """Each player's NFL team in that season's archived MFL player list (2003 on), by id and by name."""
    p = f"{os.path.dirname(SITE)}/mfl_archive/{season}/players.json"
    if not os.path.exists(p):
        return {}, {}
    ps = json.load(open(p))["players"]["player"]
    return {x["id"]: x["team"] for x in ps}, {x["name"]: x["team"] for x in ps}


def nfl_team(r):
    """A draft pick's NFL team in that season's archived player list, by its MFL id or, without one, its name."""
    by_id, by_name = nfl_teams(int(r["season"]))
    return by_id.get(r.get("player_id") or "") or by_name.get(r["player"])


def pick_name(r):
    """A draft pick's name, first name first, from the player index when the pick has an id."""
    if r.get("player_id"):
        name = player_name(r["player_id"])
    else:
        last, _, first = r["player"].partition(", ")
        name = f"{first} {last}".strip()
    return name + (" defense" if r["position"] == "Def" else "")


@lru_cache(maxsize=None)
def roster_share(nfl):
    """Each franchise's share of its end-of-season roster spots (2003 on, players only, not team
    units) on one NFL team: {franchise: percent}."""
    root = os.path.dirname(SITE)
    slot = {(int(y), s): t for t, v in d.identities().items() for y, s in v["slots"].items()}
    on, total = {}, {}
    for yr in sorted(int(y) for y in os.listdir(f"{root}/mfl_archive") if y.isdigit()):
        p = f"{root}/mfl_archive/{yr}/players.json"
        if not os.path.exists(p):
            continue
        players = {x["id"]: x for x in d.as_list(json.load(open(p))["players"]["player"])}
        for f in d.as_list(json.load(open(f"{root}/mfl_archive/{yr}/rosters.json"))["rosters"]["franchise"]):
            t = slot.get((yr, f["id"]))
            for pl in d.as_list(f.get("player")):
                x = players.get(pl["id"])
                if not t or not x or x["position"] == "Def" or x["position"].startswith("TM"):
                    continue
                total[t] = total.get(t, 0) + 1
                on[t] = on.get(t, 0) + (x["team"] == nfl)
    return {t: round(100 * on[t] / total[t], 1) for t in total}


def score(x):
    return f"{x:g}"


def playoff_games(me):
    """Every playoff game a franchise played: season, opponent, both seeds and both scores."""
    out = []
    for s in d.seasons():
        sd = d.seeds(s) or {}
        for g in d.postseason(s)[0]:
            if me in (g["team_a"], g["team_b"]):
                a = g["team_a"] == me
                opp = g["team_b"] if a else g["team_a"]
                mine, theirs = (g["score_a"], g["score_b"]) if a else (g["score_b"], g["score_a"])
                out.append({"season": s, "opp": opp, "seed": sd.get(me), "opp_seed": sd.get(opp),
                            "me": mine, "them": theirs, "won": mine > theirs})
    return out


def towels():
    """Da Funk's Terrible Towel row with one Dolphins flag, a <template> for assets/clip.js: the
    league's most Steelers roster against Da Funk's Dolphins share, and the Dolphins it drafted."""
    tw = config()["towels"]
    me = tw["team"]
    mia, pit = roster_share("MIA"), roster_share("PIT")
    ranked = sorted(mia, key=lambda t: -mia[t])
    above = [t for t in ranked if mia[t] > mia[me]]
    steel = max(pit, key=pit.get)
    picks = {}
    for r in d.all_drafts():
        if r["team"] == me and nfl_team(r) == "MIA":
            picks.setdefault(pick_name(r), []).append(r["season"])
    facts = {"team": me, "mia": mia[me], "mia_rank": ordinal(ranked.index(me) + 1), "steel": steel, "pit": pit[steel],
             "above": ", ".join(above[:-1]) + (" and " if len(above) > 1 else "") + above[-1] if above else "nobody",
             "fins": ", ".join(f"{n} ({' and '.join(ys)})" for n, ys in picks.items())}
    row = "".join("<span class='fins-flag'><b>" + E(tw["flag"]) + "</b></span>" if i == tw["count"] // 2 else
                  f"<span class='towel' style='--d:{(i * 37) % 9 / 10}s'></span>" for i in range(tw["count"]))
    lines = "".join(f"<p>{E(line.format(**facts))}</p>" for line in tw["lines"])
    return (f"<template id='pdl-towels'><aside class='towels' title='Click to close'>"
            f"<div class='towels-sign'><h3>{E(tw['title'])}</h3>{lines}</div>"
            f"<div class='towels-row' aria-hidden='true'>{row}</div></aside></template>")


def funk_chat():
    """Da Funk in the league chat, a <template> for assets/clip.js: it enters, types, thinks
    better of it and leaves, over its waiver adds and trades a season from the activity tables."""
    fc = config()["funk_chat"]
    me = fc["team"]
    adds = d.by_owner("transaction_owners.csv")
    fewest = sorted(adds, key=lambda t: float(adds[t]["adds_per_season"]))
    facts = {"team": me, "adds": adds[me]["adds_per_season"], "adds_rank": ordinal(fewest.index(me) + 1),
             "trades": d.by_owner("owner_activity.csv")[me]["per_season"]}
    s = fc["steps"]
    return (f"<template id='pdl-fchat'><aside class='fchat' title='Click to close'>"
            f"<div class='fchat-head'># {E(fc['channel'])}</div><div class='fchat-body'>"
            f"<p class='fchat-sys' style='--t:{s[0]}'>{E(fc['enter'].format(**facts))}</p>"
            f"<span class='sms-typing' style='--at:{s[1]};--wait:{s[2]}' aria-label='typing'><i></i><i></i><i></i></span>"
            f"<p class='fchat-sys' style='--t:{s[1] + s[2] + .2:g}'>{E(fc['leave'].format(**facts))}</p>"
            f"<p class='fchat-foot' style='--t:{s[1] + s[2] + .9:g}'>{E(fc['foot'].format(**facts))}</p>"
            f"</div></aside></template>")


def win_streaks():
    """Regular-season winning runs, carried across seasons: each franchise's current run and the
    longest run on record by anyone, {team: current}, longest."""
    now, longest = {}, 0
    for g in sorted(d.games(), key=lambda g: (g["season"], g["week"])):
        if g["stage"] != "regular":
            continue
        for t, mine, theirs in ((g["team_a"], g["score_a"], g["score_b"]), (g["team_b"], g["score_b"], g["score_a"])):
            now[t] = now.get(t, 0) + 1 if mine > theirs else 0
            longest = max(longest, now[t])
    return now, longest


def champagne():
    """Da Funk's bottle on ice, a <template> for assets/clip.js: this season's record and its
    regular-season winning run (if long), and, from
    the playoff brackets, its playoff record, the #1-seed exits, who knocked it out most and the
    seasons it led the league in points and still went out."""
    c = config()["champagne"]
    me = c["team"]
    now = next(r for r in d.standings(d.seasons()[-1]) if r["team"] == me)
    games = playoff_games(me)
    lost = [g for g in games if not g["won"]]
    knock = max({g["opp"] for g in lost}, key=lambda t: sum(g["opp"] == t for g in lost))
    led = []
    for s in d.seasons()[:-1]:
        st = d.standings(s)
        top = max(st, key=lambda r: r["pf"])
        if top["team"] == me and top["playoffs"] and d.champions().get(s) != me:
            led.append(str(s))
    titles = sum(t == me for t in d.champions().values())
    facts = {"team": me, "w": now["w"], "l": now["l"], "pw": len(games) - len(lost), "pl": len(lost),
             "titles": "no titles" if not titles else f"{titles} title" + "s" * (titles > 1),
             "top_exits": " and ".join(f"{g['season']}, to the {g['opp_seed']}-seed {g['opp']} ({score(g['me'])}-{score(g['them'])})"
                                       for g in lost if g["seed"] == 1),
             "knock": knock, "knock_n": sum(g["opp"] == knock for g in lost), "led": " and ".join(led)}
    run, longest = win_streaks()
    facts["streak"] = run[me]
    unbeaten = now["l"] == 0 and now["t"] == 0 and now["w"] > 0
    v = c["unbeaten"] if unbeaten else c["beaten"]
    lines = "".join(f"<p>{E(line.format(**facts))}</p>" for line in c["lines"] if "{led}" not in line or led)
    # the winning run, if it is a long one, and whether anyone has had a longer
    if run[me] >= c["streak_min"]:
        lines = f"<p>{E(c['streak' if run[me] == longest else 'streak_short'].format(**facts))}</p>" + lines
    bottle = ("<svg class='bubbly-art' viewBox='0 0 80 130' aria-hidden='true'>"
              "<g class='bubbly-cork'><rect x='33' y='4' width='14' height='12' rx='3' fill='#c9a36a'/></g>"
              "<path d='M34 14 H46 V36 C46 44 56 48 56 60 V96 H24 V60 C24 48 34 44 34 36 Z' fill='#1f5b3a'/>"
              "<path d='M33 12 H47 V30 H33 Z' fill='#d8b23c'/>"
              "<rect x='27' y='66' width='26' height='18' rx='2' fill='#f4ead2'/>"
              "<path d='M8 74 H72 L64 126 H16 Z' fill='#c9d1d6' stroke='#8d979e' stroke-width='2'/>"
              "<rect x='14' y='68' width='14' height='12' rx='2' fill='#e8f6fb' opacity='.9' transform='rotate(-12 21 74)'/>"
              "<rect x='50' y='67' width='15' height='13' rx='2' fill='#e8f6fb' opacity='.9' transform='rotate(10 57 73)'/>"
              "<rect x='36' y='70' width='12' height='10' rx='2' fill='#e8f6fb' opacity='.85'/></svg>")
    return (f"<template id='pdl-bubbly'><aside class='bubbly' title='Click to close'><div class='bubbly-head'>{E(c['title'])}</div>"
            f"<div class='bubbly-body'>{bottle}<div><span class='bubbly-tag'>{E(v['tag'].format(**facts))}</span>"
            f"<p>{E(v['intro'].format(**facts))}</p>{lines}<p class='bubbly-close'>{E(c['close'])}</p></div></div></aside></template>")


def scoreboard():
    """Carter's Commandos' scoreboard, a <template> for assets/clip.js: it flips between its
    lowest-scoring title game and its highest-scoring playoff loss, then the season it scored
    the most and still missed the playoffs, all from the record."""
    sb = config()["scoreboard"]
    me = sb["team"]
    finals = []
    for s, t in d.champions().items():
        f = d.final(s)
        if t == me and f:
            a = f["team_a"] == me
            finals.append((f["score_a"] if a else f["score_b"], s, f["team_b"] if a else f["team_a"], f["score_b"] if a else f["score_a"]))
    title = min(finals)
    loss = max((g for g in playoff_games(me) if not g["won"]), key=lambda g: g["me"])
    worst = max(min(g["score_a"], g["score_b"]) for s in d.seasons() for g in d.postseason(s)[0])
    seasons = []
    every = []
    for s in d.seasons()[:-1]:
        st = d.standings(s)
        by_pf = sorted(st, key=lambda r: -r["pf"])
        every += [r.get("luck") or 0 for r in st]
        r = next(r for r in st if r["team"] == me)
        if not r["playoffs"]:
            seasons.append((by_pf.index(r) + 1, r.get("luck") or 0, s, r))
    rank, luck, bad, r = min(seasons)
    facts = {"title_season": title[1], "title_score": score(title[0]), "loss_season": loss["season"],
             "loss_score": score(loss["me"]), "bad": bad, "bad_rank": ordinal(rank), "bad_record": f"{r['w']}-{r['l']}",
             "luck": f"{luck:+.1f}", "luck_rank": ordinal(sorted(every).index(luck) + 1)}

    def panel(label, opp, mine, theirs, result):
        return (f"<div class='board-panel'><p class='board-label'>{E(label)}</p>"
                f"<p class='board-row'><span>{E(sb['short'])}</span><b>{score(mine)}</b></p>"
                f"<p class='board-row'><span>{E(opp.upper())}</span><b>{score(theirs)}</b></p>"
                f"<p class='board-final board-{result.lower()}'>FINAL: {result}</p></div>")
    notes = "".join(f"<p>{E(line.format(**facts))}</p>" for line in sb["lines"])
    if loss["me"] == worst:
        notes += f"<p>{E(sb['record'])}</p>"
    return (f"<template id='pdl-board'><aside class='board' title='Click to close'><p class='board-title'>{E(sb['title'])}</p>"
            f"<div class='board-panels'>{panel(sb['title_label'].format(**facts), title[2], title[0], title[3], 'WIN')}"
            f"{panel(sb['loss_label'].format(**facts), loss['opp'], loss['me'], loss['them'], 'LOSS')}</div>"
            f"<div class='board-notes'><h3>{E(sb['headline'])}</h3>{notes}</div></aside></template>")


def giant_killer():
    """Carter's Commandos' trophy, on their page for good: every playoff win over a #1 seed
    from a lower seed, from the playoff brackets. Empty if there are none."""
    gk = config()["giant_killer"]
    wins = [g for g in playoff_games(gk["team"]) if g["won"] and g["opp_seed"] == 1 and (g["seed"] or 0) > 1]
    if not wins:
        return ""
    lines = "".join(f"<p>{E(gk['line'].format(season=g['season'], seed=g['seed'], opp=g['opp'], me=score(g['me']), them=score(g['them'])))}</p>"
                    for g in wins)
    cup = ("<svg viewBox='0 0 48 60' aria-hidden='true'><path d='M12 6 H36 V20 C36 30 30 35 24 35 C18 35 12 30 12 20 Z' fill='#d4a017'/>"
           "<path d='M12 10 H5 C5 20 9 24 13 25 M36 10 H43 C43 20 39 24 35 25' fill='none' stroke='#d4a017' stroke-width='3'/>"
           "<rect x='21' y='35' width='6' height='10' fill='#b8860b'/><rect x='13' y='45' width='22' height='8' rx='1' fill='#5a3a1a'/></svg>")
    return (f"<div class='trophy' title='{E(gk['hint'])}'>{cup}<div><b>{E(gk['title'])}</b>{lines}</div></div>")


def steeler_board():
    """Carter's Commandos' first-round draft board, a <template> for assets/clip.js: Steelers
    circled (the NFL team the season each was taken), first-rounders who never really started
    crossed out (finished drafts only), and the team's Steelers share of roster spots."""
    sb = config()["steeler_board"]
    me = sb["team"]
    busts = {(r["season"], r["overall"]): int(r["starts"]) for r in d.draft_value()
             if r["team"] == me and r["round"] == "1" and r["complete"] == "True" and int(r["starts"]) <= sb["bust_starts"]}
    pit = roster_share("PIT")
    items = ""
    for r in d.all_drafts():
        if r["team"] != me or r["round"] != "1":
            continue
        key = (r["season"], r["overall"])
        label = f"{r['season']}, {ordinal(int(r['overall']))} overall: {pick_name(r)}"
        if nfl_team(r) == "PIT":
            items += f"<li class='dpick-pit'><span>{E(label)}</span> {E(sb['pit_note'])}</li>"
        elif key in busts:
            items += f"<li class='dpick-bust'><s>{E(label)}</s> ({busts[key]} start{'s' * (busts[key] != 1)})</li>"
    facts = {"pit": pit[me], "pit_rank": ordinal(sorted(pit, key=lambda t: -pit[t]).index(me) + 1)}
    return (f"<template id='pdl-dboard'><aside class='dboard' title='Click to close'><div class='dboard-head'>{E(sb['title'])}</div>"
            f"<p class='dboard-key'>{E(sb['key'])}</p><ul>{items}</ul>"
            f"<p class='dboard-foot'>{E(sb['foot'].format(**facts))}</p></aside></template>")


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
    # the former co-manager's out-of-office reply, up top while Barney is below
    oo = config()["out_of_office"]
    arrive(dist, oo["team"], f"setTimeout(() => pdlCard('pdl-ooo', {oo['seconds']}), {oo['after_ms']})", ["clip.js"], out_of_office())
    # and once Barney has gone, the doctor's prescription
    rx_cfg = config()["rx"]
    arrive(dist, rx_cfg["team"], f"setTimeout(() => pdlCard('pdl-rx', {rx_cfg['seconds']}), {rx_cfg['after_ms']})", ["clip.js"], rx())
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
    # other teams' quotes, pinned under a franchise's facts for good, each with a check from the record
    for h in config()["page_heckles"]:
        p = f"{dist}/franchises/{slug(h['team'])}.html"
        if os.path.exists(p):
            html = open(p).read().replace("<h2>How it is run</h2>", page_heckle(h) + "<h2>How it is run</h2>", 1)
            open(p, "w").write(html)
    # the Iron City Pounders: the Autumn Bowl program on arrival, and the plaque on the wall
    ic = config()["iron_city"]
    arrive(dist, ic["team"], f"pdlCard('pdl-autumn', {ic['program_seconds']})", ["clip.js"], autumn())
    p = f"{dist}/franchises/{slug(ic['team'])}.html"
    if os.path.exists(p):
        html = open(p).read().replace("</h1>", "</h1>" + plaque(), 1)
        open(p, "w").write(html)
    # Scooter's Boozers: the draft card, once the clip has gone
    g = config()["draft_grade"]
    arrive(dist, g["team"], f"setTimeout(() => pdlCard('pdl-grade', {g['seconds']}), {g['after_ms']})", ["clip.js"], draft_grade())
    # Blitzkrieg: the texts nobody answers
    tx = config()["texts"]
    arrive(dist, tx["team"], f"setTimeout(() => pdlCard('pdl-texts', {tx['seconds']}), {tx['after_ms']})", ["clip.js"], texts())
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
    # Da Funk: the towels and the chat, then the champagne on ice
    tw, fc, ch = config()["towels"], config()["funk_chat"], config()["champagne"]
    arrive(dist, tw["team"], f"setTimeout(() => pdlCard('pdl-towels', {tw['seconds']}), {tw['after_ms']}); "
                             f"setTimeout(() => pdlCard('pdl-fchat', {fc['seconds']}), {fc['after_ms']}); "
                             f"setTimeout(() => pdlCard('pdl-bubbly', {ch['seconds']}), {ch['after_ms']})",
           ["clip.js"], towels() + funk_chat() + champagne())
    # Carter's Commandos: the scoreboard and the draft board once the clip has gone, and the trophy on the shelf
    sb, db = config()["scoreboard"], config()["steeler_board"]
    arrive(dist, sb["team"], f"setTimeout(() => pdlCard('pdl-board', {sb['seconds']}), {sb['after_ms']}); "
                             f"setTimeout(() => pdlCard('pdl-dboard', {db['seconds']}), {db['after_ms']})",
           ["clip.js"], scoreboard() + steeler_board())
    p = f"{dist}/franchises/{slug(config()['giant_killer']['team'])}.html"
    if os.path.exists(p):
        html = open(p).read().replace("</h1>", "</h1>" + giant_killer(), 1)
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
