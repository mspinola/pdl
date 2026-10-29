"""Build the PDL site into site/dist/. Standard library only.

So far this builds the rule book:

    site/dist/rules/index.html      the rules in force now, with each change marked
    site/dist/rules/<season>.html   the rules in force for any season from 2006
    site/dist/rules/changes.html    every meeting from 2002: what passed, what failed, the sources

    python3 site/build.py

The text comes from rules/baseline.json with rules/amendments.json applied by
src/rulebook_build.py, so nothing here is written by hand. The build refuses to
run if an amendment fails to land or the ledger does not check.
"""
import json, os, re, shutil, sys
from collections import defaultdict

SITE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(SITE)
sys.path.insert(0, f"{BASE}/src")
sys.path.insert(0, SITE)
import rulebook_build as rb
import rulebook_ledger as rl
import rulebook_mfl_check as mc
from frame import E, page
import seasons_pages
import franchise_pages
import h2h_pages
import trades_pages
import drafts_pages
import records_page
import analysis_pages
import eggs

DIST = f"{SITE}/dist"

STATUS_LABEL = {"adopted": "Adopted", "in practice": "In practice", "one season": "One season", "open": "Unconfirmed"}
NOTE_LABEL = {"one season": "{season} only", "open": "Unconfirmed", "in practice": "In practice"}


# ---------------------------------------------------------------- the book

def fmt(v):
    if v is None:
        return "x"
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def render_block(b):
    if b["type"] == "p":
        return f"<p>{E(b['text'])}</p>"
    if b["type"] == "h":
        return f"<h4>{E(b['text'])}</h4>"
    if b["type"] == "list":
        if b["ordered"]:
            items = "".join(f'<li value="{it.get("n", i + 1)}">{E(it["text"])}</li>' for i, it in enumerate(b["items"]))
            return f"<ol>{items}</ol>"
        return "<ul>" + "".join(f"<li>{E(it['text'])}</li>" for it in b["items"]) + "</ul>"
    if b["type"] == "table":
        cols = b["columns"]
        head = f'<tr><th scope="col">{E(b["title"])}</th>' + "".join(f'<th scope="col">{E(c)}</th>' for c in cols) + "</tr>"
        rows = []
        for g in b["groups"]:
            if g["label"]:
                rows.append(f'<tr class="group"><th colspan="{len(cols) + 1}" scope="rowgroup">{E(g["label"])}</th></tr>')
            for r in g["rows"]:
                rows.append(f'<tr><th scope="row">{E(r["label"])}</th>'
                            + "".join(f'<td class="{"na" if v is None else ""}">{fmt(v)}</td>' for v in r["values"]) + "</tr>")
        return f'<div class="table-wrap"><table class="scoring"><thead>{head}</thead><tbody>{"".join(rows)}</tbody></table></div>'
    return ""


def edits_section(c, sid):
    """Whether a change edits a section's text, rather than only reaffirming it."""
    return any(op["op"] != "note" and (op.get("section") == sid or op.get("id") == sid) for op in c["ops"])


def anchor(sid):
    return "s" + sid.replace(".", "-")


def change_link(c, depth_prefix=""):
    return f'{depth_prefix}changes.html#{c["id"]}'


def render_book(season, current, seasons):
    b = rb.book(season)
    chapters = defaultdict(list)
    for s in b["sections"]:
        chapters[s["chapter"]].append(s)

    toc, body = [], []
    for ch, secs in chapters.items():
        head = next((s for s in secs if s["level"] == 1), secs[0])
        toc.append(f'<li><a href="#{anchor(head["id"])}">{E(head["id"].split(".")[0])}. {E(head["title"])}</a></li>')
        for s in secs:
            hist = [c for c in b["history"].get(s["id"], []) if c["status"] != "open" and rb.applies(c, season)]
            tag = "h2" if s["level"] == 1 else "h3"
            badge = ""
            edits = [c for c in hist if edits_section(c, s["id"])]
            if edits:
                links = ", ".join(f'<a href="{change_link(c)}">{c["effective"]}</a>' for c in
                                  sorted({c["effective"]: c for c in edits}.values(), key=lambda c: c["effective"]))
                badge = f' <span class="changed" title="Changed since the 2006 rule book">changed {links}</span>'
            out = [f'<section class="rule" id="{anchor(s["id"])}">',
                   f'<{tag}><span class="num">{E(s["id"])}</span> {E(s["title"])}{badge}</{tag}>']
            out += [render_block(bl) for bl in s["blocks"]]
            for c, text in b["notes"].get(s["id"], []):
                label = NOTE_LABEL[c["status"]].format(season=c.get("effective") or c["meeting"])
                out.append(f'<aside class="note note-{c["status"].replace(" ", "-")}"><strong>{E(label)}.</strong> '
                           f'{E(text)} <a href="{change_link(c)}">Record</a></aside>')
            if hist:
                items = "".join(
                    f'<li><a href="{change_link(c)}">{c["effective"]}</a>: {E(c["change"])}'
                    f'{"" if c["status"] == "adopted" else " <em>(" + STATUS_LABEL[c["status"]].lower() + ")</em>"}'
                    f'{"" if edits_section(c, s["id"]) else " <em>(reaffirmed, the text is unchanged)</em>"}</li>'
                    for c in hist)
                out.append(f'<details class="history"><summary>History of {E(s["id"])}</summary><ul>{items}</ul></details>')
            out.append("</section>")
            body.append("\n".join(out))

    picker = "".join(f'<option value="{y}.html"{" selected" if y == season else ""}>{y}</option>' for y in seasons)
    prev_next = []
    if season - 1 in seasons:
        prev_next.append(f'<a href="{season - 1}.html">{season - 1}</a>')
    if season + 1 in seasons:
        prev_next.append(f'<a href="{season + 1}.html">{season + 1}</a>')
    n_changed = sum(1 for s in b["sections"] if any(rb.applies(c, season) and edits_section(c, s["id"])
                                                     for c in b["history"].get(s["id"], [])))
    if current:
        intro = (f"<h1>The PDL rule book</h1>"
                 f'<p class="lede">The rules in force for the {season} season: the 2006 rule book with every change '
                 f'the league has adopted since. {n_changed} of {len(b["sections"])} sections have changed. Each change '
                 f'is marked with the season it took effect and links to its record.</p>')
    else:
        intro = (f"<h1>The rules for {season}</h1>"
                 f'<p class="lede">The 2006 rule book with every change in force by the {season} season. '
                 f'{n_changed} of {len(b["sections"])} sections differ from 2006. '
                 f'<a href="index.html">The current rules</a>.</p>')
    bar = (f'<div class="seasonbar"><label for="season">Rules as of</label>'
           f'<select id="season" onchange="location.href=this.value">{picker}</select>'
           f'<span class="pn">{" ".join(prev_next)}</span>'
           f'<a href="changes.html">Every change</a><button onclick="window.print()">Print</button></div>')
    return page(f"PDL rules {season}" if not current else "PDL rule book",
                f'<div class="book">{intro}{bar}<nav class="toc" aria-label="Contents"><h2>Contents</h2><ol>{"".join(toc)}</ol></nav>'
                f'<div class="text">{"".join(body)}</div></div>',
                description=f"The Premiere Dynasty League rules in force for {season}.")


# ---------------------------------------------------------------- the timeline

def words(t):
    return set(re.findall(r"[a-z0-9]+", t.lower())) - {"the", "a", "of", "to", "and", "or", "for", "in", "on", "is"}


def prose(t):
    """Source wording in the site's style: sentences, not semicolons."""
    return re.sub(r";\s+(\w)", lambda m: ". " + m.group(1).upper(), t)


def joined(parts):
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


def similar(a, b):
    wa, wb = words(a), words(b)
    return len(wa & wb) / max(1, len(wa | wb))


FAILED = re.compile(r"\b(failed|no change|rejected|not voted|deferred|dropped|unnecessary|not recorded|unknown"
                    r"|discussed|hoax|not in effect|result not)", re.I)


def other_proposals(meeting, src, ledger_changes):
    """Proposals from the sources that did not change the rules, without duplicates.

    The same proposal is often in two sources (an email and the poll it led to), so
    a candidate is dropped when an entry on the same topic says much the same, or
    when it only reports an unknown result that a poll or the board settles.
    """
    settled = []  # (topic, text, source) already shown, starting with the ledger's changes
    for c in ledger_changes:
        for ref in c["sources"]:
            entry, _ = rl.resolve(src, ref)
            settled.append((entry.get("topic"), entry.get("proposal", ""), "ledger"))
        settled.append((None, c["change"], "ledger"))
    voted_topics = {e.get("topic") for name in ("polls", "commissioner")
                    for e in src.get(name, []) if (e.get("meeting") or e.get("season")) == meeting}
    pool = []
    # drive.json is detail and evidence for the other sources, so it is not listed itself
    for name in ["polls", "commissioner", "message_board", "email", "changes_html"]:
        for e in src.get(name, []):
            if (e.get("meeting") or e.get("season")) != meeting or e.get("in_baseline"):
                continue
            outcome = str(e.get("outcome", ""))
            if not FAILED.search(outcome) and "tied" not in outcome:
                continue
            text, topic = e.get("proposal", ""), e.get("topic")
            vague = re.search(r"unknown|not recorded|result not|put to", outcome, re.I)
            if vague and name != "polls" and topic in voted_topics:
                continue
            # two entries in one source are two proposals, so only compare across sources
            if any(similar(text, t) > (0.25 if tp == topic else 0.15 if vague else 0.45)
                   for tp, t, origin in settled if origin != name):
                continue
            settled.append((topic, text, name))
            pool.append({"text": prose(text), "outcome": prose(outcome), "file": name, "entry": e})
    return pool


def render_changes(seasons):
    ledger = rl.load("ledger.json")
    src = rl.sources()
    cs = {c["id"]: c for c in rb.changes()}
    by_meeting = defaultdict(list)
    for c in ledger["changes"]:
        by_meeting[c["meeting"]].append(cs[c["id"]])
    baseline_passed = defaultdict(list)
    for e in src["changes_html"]:
        if e.get("in_baseline"):
            baseline_passed[e["meeting"]].append(e)

    meetings = sorted(set(by_meeting) | set(baseline_passed)
                      | {e.get("meeting") or e.get("season") for n in src for e in src[n]})
    nav, body = [], []
    for m in meetings:
        changes = by_meeting.get(m, [])
        others = other_proposals(m, src, changes)
        if not changes and not others and not baseline_passed.get(m):
            continue
        nav.append(f'<a href="#m{m}">{m}</a>')
        out = [f'<section class="meeting" id="m{m}"><h2>{m} meeting</h2>']
        if baseline_passed.get(m):
            items = "".join(f'<li>{E(e["proposal"])} <span class="where">In the 2006 rule book, section {E(e["in_baseline"])}.</span></li>'
                            for e in baseline_passed[m])
            out.append(f'<h3>Passed, and part of the 2006 rule book</h3><ul class="passed">{items}</ul>')
        if changes:
            out.append("<h3>Changes to the rules</h3><ul class='changes'>")
            for c in changes:
                eff = f", from {c['effective']}" if c.get("effective") and c["effective"] != m else ""
                refs = []
                for ref in c["sources"]:
                    entry, _ = rl.resolve(src, ref)
                    refs.append(E(rl.cite(ref, entry)))
                secs = ", ".join(f'<a href="index.html#{anchor(s)}">{E(s)}</a>' for s in c["sections"])
                ev = f'<p class="evidence"><strong>Checked:</strong> {E(c["evidence"])}</p>' if c.get("evidence") else ""
                out.append(f'<li id="{E(c["id"])}"><span class="status status-{c["status"].replace(" ", "-")}">'
                           f'{STATUS_LABEL[c["status"]]}{eff}</span> {E(c["change"])}'
                           f'<p class="meta">Section {secs}. Sources: {joined(refs)}.</p>{ev}</li>')
            out.append("</ul>")
        if others:
            items = "".join(f'<li>{E(p["text"])} <span class="outcome">{E(p["outcome"][:1].upper() + p["outcome"][1:])}.</span></li>'
                            for p in others)
            out.append(f'<h3>Also proposed</h3><ul class="others">{items}</ul>')
        out.append("</section>")
        body.append("\n".join(out))

    # the MFL check, summarised
    last = rb.latest_season()
    agree = differ = explained = 0
    for season in range(rb.FIRST, last + 1):
        for _, v, _ in mc.compare(rb.book(season)["facts"], mc.observed(season, current=(season == last))):
            agree += v == "agrees"
            differ += v == "DIFFERS"
    known = rb.load("amendments.json").get("mfl_known_differences", [])
    explained = sum(len(k["seasons"]) for k in known)
    differ -= explained
    check = (f'<section class="meeting" id="check"><h2>Checked against MyFantasyLeague</h2>'
             f"<p>For every season from {rb.FIRST}, the rules this book states are compared with what the league's "
             f"MyFantasyLeague site actually ran: roster size, starting lineup, injured reserve, regular-season and "
             f"playoff weeks, how the schedule splits, and the scoring for touchdowns, yardage, field goals and "
             f"receptions. {agree} comparisons agree, {explained} differ for a known reason, and {differ} differ "
             f"without one.</p>"
             + "".join(f"<p class='evidence'><strong>{', '.join(map(str, k['seasons']))}:</strong> {E(k['why'])}</p>" for k in known)
             + "</section>")

    intro = ("<h1>Every rule change</h1><p class='lede'>Each summer meeting from 2002: the changes that passed, with "
             "the sources that record them, and the proposals that did not. Changes are marked adopted, in practice "
             "(the working rule, with no recorded vote), one season, or unconfirmed (the record does not settle it). "
             "Proposals are paraphrased, and no owner is named.</p>")
    return page("PDL rule changes", f'<div class="timeline">{intro}<nav class="years">{" ".join(nav)}<a href="#check">MFL check</a></nav>'
                f'{"".join(body)}{check}</div>', description="Every PDL rule change since 2002, with its sources.")


# ---------------------------------------------------------------- home

def home():
    import league_data as d
    from frame import slug
    last = max(d.champions())
    champ = d.champions()[last]
    return (f"<div class='home'><h1>Premiere Dynasty League</h1><p class='lede'>A dynasty fantasy football league "
            f"since 2000. Sixteen franchises, the same league ever since, and one change of owner.</p>"
            f"<div class='banner'><span class='label'>{last} champion</span> <strong><a href='franchises/{slug(champ)}.html'>"
            f"{E(champ)}</a></strong> <a class='meta' href='seasons/{last}.html'>the {last} season</a></div>"
            "<ul class='doors'>"
            "<li><a href='seasons/index.html'>Seasons</a><span>Every season since 2000: standings, playoffs, the draft, "
            "trades, and the rules adopted that summer</span></li>"
            "<li><a href='franchises/index.html'>Franchises</a><span>Each team's record, titles, rivalries, and how it is "
            "run: trades, the waiver wire, lineups, luck and the draft</span></li>"
            "<li><a href='h2h/index.html'>Head to head</a><span>Every pairing's record, and every game they have "
            "played</span></li><li><a href='trades/index.html'>Trades</a><span>All of them since 2000: who trades, and "
            "with whom</span></li><li><a href='drafts/index.html'>Drafts</a><span>Every pick since 2008 and how it "
            "turned out</span></li><li><a href='records/index.html'>The record book</a><span>Highest scores, best "
            "seasons, streaks, title droughts</span></li><li><a href='analysis/index.html'>Analysis</a><span>The waiver "
            "wire, lineups and luck, the ones that got away, draft value</span></li>"
            "<li><a href='rules/index.html'>The rule book</a><span>The rules in force now, and as of any season since "
            "2006</span></li><li><a href='rules/changes.html'>Every rule change</a><span>Each summer meeting since 2002, "
            "with its sources</span></li><li><a href='https://mspinola.github.io/mspinola/'>The original site</a>"
            "<span>Seasons 2000 to 2020, as they were kept at the time</span></li></ul></div>")


# ---------------------------------------------------------------- build

def main():
    problems = rb.check() + rl.check(rl.load("ledger.json"), rl.load("baseline.json"), rl.sources())
    if problems:
        for p in problems:
            print("  PROBLEM", p)
        return 1
    if os.path.exists(DIST):
        shutil.rmtree(DIST)
    os.makedirs(f"{DIST}/rules")
    os.makedirs(f"{DIST}/assets")
    shutil.copy(f"{SITE}/site.css", f"{DIST}/assets/site.css")
    for name in os.listdir(f"{SITE}/assets"):   # the moose, and the script that sets it loose
        shutil.copy(f"{SITE}/assets/{name}", f"{DIST}/assets/{name}")
    last = rb.latest_season()
    seasons = list(range(rb.FIRST, last + 1))
    for y in seasons:
        with open(f"{DIST}/rules/{y}.html", "w") as f:
            f.write(render_book(y, current=False, seasons=seasons))
    with open(f"{DIST}/rules/index.html", "w") as f:
        f.write(render_book(last, current=True, seasons=seasons))
    with open(f"{DIST}/rules/changes.html", "w") as f:
        f.write(render_changes(seasons))
    n_seasons = seasons_pages.build(DIST)
    n_franchises = franchise_pages.build(DIST)
    n_other = sum(m.build(DIST) for m in (h2h_pages, trades_pages, drafts_pages, records_page, analysis_pages))
    with open(f"{DIST}/index.html", "w") as f:
        f.write(page("Premiere Dynasty League",
                     home(), depth=0, description="The Premiere Dynasty League."))
    eggs.build(DIST)   # last: the antlers go over every finished page
    n = len(os.listdir(f"{DIST}/rules"))
    print(f"built site/dist: {n} rule book pages, {n_seasons} season pages, {n_franchises} franchise pages, "
          f"{n_other} more (head to head, trades, drafts, records, analysis)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
