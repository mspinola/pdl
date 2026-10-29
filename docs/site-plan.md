# PDL site plan

The new site lives in this repository and publishes to `mspinola.github.io/pdl`.
It covers every season, 2000 to 2026, and it is generated entirely from
`mfl_archive/`, so it never depends on MyFantasyLeague being up. The legacy site
at `mspinola.github.io/mspinola` is frozen as a historical artifact and gets one
change at launch: a notice pointing here.

Status: **plan, for review.** Nothing below is built yet except where marked.

## What matters most: the rule book

The rules record is the hardest thing to replace, so it gets its own workstream
and goes first.

### What exists, measured

| Source | What it is | State |
|---|---|---|
| `PDL_Rules.pdf` | the rule book every season page from 2006 to 2020 links | made Sep 2006, last modified Oct 2006, 17 pages |
| `PDL_Rules.doc` | the Word edition | about the same text as the PDF |
| `PDL_Rules.htm` | Word's HTML export | saved 2004-06-30 |
| `old_PDL_Rules.doc` | an earlier edition | shorter, 3,849 words against 4,159 |
| `changes.html` | the proposals log | the 2002 to 2023 summer meetings |
| `changes2002.html` | the 2002 proposals | |
| Drive, "2011 Summer Meeting" | meeting notes | covers 2011 |
| your email | the rest | not yet searched |

The `2019-07-28` date in git on the rule book files is when they were moved
into the repository ("transferring in"), not when the rules were last edited.
The rule book itself dates from 2006 at the latest. So everything passed at the
2007 to 2026 meetings has probably never been written into it.

The rule text names no owners. The only names in those files were in their
author metadata, which is why the archive keeps their extracted text rather
than the files.

### Where the proposals log is thin

| Meetings | State in `changes.html` |
|---|---|
| 2002, 2003, 2004, 2006, 2008, 2013, 2014, 2018 | proposals with outcomes |
| 2005, 2007, 2009, 2010, 2011, 2012, 2015, 2019, 2020, 2021, 2022, 2023 | proposals only, no outcome |
| 2016, 2017 | heading with nothing under it |
| 2024, 2025, 2026 | no section at all |

That is 12 meetings missing outcomes, 2 empty, and 3 absent. The email search
fills these.

### Steps

Steps 1 to 7 are done, and the rule book is online at <https://mspinola.github.io/pdl/>. What they found, and
how to re-run them, is in [rulebook/README.md](rulebook/README.md).

1. **Settle the baseline edition.** *(Done: the 2006 edition.)* Diff the 2004, 2006 and older editions
   section by section, and check which of the changes recorded as passed (2002
   to 2006) each one already contains. The newest edition that contains them
   all is the baseline. The expectation is the 2006 PDF.
2. **Turn the baseline into data.** *(Done: `rules/baseline.json`, 52 sections.)* The book is numbered (1.0 Introduction, 1.1
   Purpose, and on through about 70 sections, around 4,100 words). Store it as
   `rules/baseline.json`, one record per section with its number, title and
   text, so every page is generated from it rather than hand-edited.
3. **Build the change ledger from `changes.html`.** *(Done: `rules/ledger.json`, with failed proposals kept in `rules/sources/`.)* One record per proposal:
   meeting year, the proposal as written, outcome (passed, failed, tabled or
   unknown), the vote where recorded, the sections it touches, the season it
   took effect, and its source.
4. **Fill the gaps from email and Drive.** *(Done for email, polls and the board.)* Each record added this way cites its
   source by date and subject line, never by sender, since the site is public.
5. **Layer the passed changes onto the baseline, in order.** The output is the
   rule book as of any season. A changed section shows when it changed and
   links to the proposal that changed it. A proposal with an unknown outcome
   never changes the text. It shows as unconfirmed until its outcome is found.
6. **Check it against what MFL actually ran.** The archive holds every season's
   MFL rules (`rules.json`): roster size, starters, scoring. Where a rule is
   visible there, the layered book must agree with it for that season. This is
   an independent test, and it already has a known target: the jump in scoring
   from 78 to 116 points a game in 2018 is a scoring change, so the ledger
   should hold a passed proposal for it at the 2017 or 2018 meeting. If it
   doesn't, a record is missing.
7. **Publish** the current rule book, a "rules as of" view for each season, and
   a change timeline, all printable.

Section numbers stay stable. An added rule takes the next free number in its
section instead of renumbering the rest, so old references still land.

## Pages

| Page | Content | Source |
|---|---|---|
| Home | the current season, the latest champion, entry points | archive |
| Seasons, 2000 to 2026 | standings, results by week, playoff bracket, champion, draft, that season's trades, the rules adopted that summer | archive, ledger |
| Franchises | each franchise's record, titles, trades, name history, best and worst matchups. Team names only. | archive |
| Head to head | the matrix, plus a page per pairing | games |
| Trades | the log, partners, pick flow | trades |
| Drafts | by season and by franchise. 2008 on from MFL, earlier from the archived draft boards. | archive |
| Records | the record book for every season, computed from the games and checked against the hand-kept one for 2000 to 2015. The MVP list likewise, from player scores, checked against 2001 to 2013. | games, player scores |
| Rule book | as above | ledger |
| Archive | links to the 96 weekly recaps from 2003 to 2008 on the legacy site, and the original rule book editions | legacy |
| About | sources, coverage, and the caveats already documented in the README | |

The trade dashboard stays as a working view. Its content moves into the Trades
and Head to head pages.

## Moose easter eggs

Everyone secretly loves the Manic Moose, America's Team. They just won't admit
it. The site admits it for them, quietly. Built in Phase 1.

All eggs live in one file, `site/eggs.json`, mapping a trigger (team, season,
pairing, route) to its effect, so they are easy to add each season and easy for
anyone to audit. None of them changes a number or a rule: the rule book and the
values in data tables stay authoritative. Team names only, as everywhere.

**Quiet, triggered by the data**

- **Antlers on hover.** Wherever "Manic Moose" appears in a table, a small
  antler SVG fades in above the name. Pure CSS on a class the build adds.
- **Rivalry footnotes.** One-line captions on the pairing pages where the data
  says something, chosen by the build: the Blitzkrieg series (Moose lead 37-13)
  and, in fairness, the series the Moose lose.
- **Title seasons.** On the 2007, 2012 and 2023 season pages, the champion
  banner carries a moose silhouette watermark.
- **"The Year of the Moose."** A tooltip on the 2017 season page, after the
  subject line of that summer's commissioner email.

**Hidden, found by poking around**

- **The 404 page.** "This page has been retained by the Moose," with the
  running moose.
- **The console.** Dev tools open to an ASCII moose and `Moose are loose!`
- **`/moose`.** An unlinked franchise museum: America's Team, the best all-time
  win rate in the league (.630), three titles, a trophy case.
- **Moose mode.** The Konami code (up up down down left right left right B A)
  turns the accent color moose brown, sends the running moose across the
  screen, and briefly renames every team in the standings "Moose" before it
  snaps back. About 20 lines of plain JavaScript.

**The running moose.** A redesign of the animated GIF from twenty years of
league-wide emails: `site/assets/manic-moose.svg`, drawn for the site. A
lowered, charging head with a glowing red eye under a heavy brow, a muscled
dark hide over a big shoulder hump, the bell under the throat, wide palmate
antlers, flared steaming nostrils, long galloping legs and kicked-up dust. Pure SVG
and CSS, so it is sharp at any size, has no licensing question, and stops
moving for readers who ask their system for reduced motion.

## How it is built

- **A standard-library Python build script** (`site/build.py`) reads
  `datasets/`, `mfl_archive/` and the rules data, and writes static HTML to
  `site/dist/`. No framework and no dependencies, which matches the archive:
  nothing that can disappear.
- **Charts are SVG drawn at build time.** Small amounts of plain JavaScript for
  sorting and searching tables, nothing loaded from a CDN.
- **A GitHub Actions workflow publishes `site/dist/` to Pages**, which keeps
  `docs/` free for documents like this one.
- **Each season's update**: run `archive_mfl.py`, add that summer's meeting to
  the ledger, rebuild, commit. The publish check runs before every commit.

## Phases

0. **Capture** (mostly done): the rules record is archived. Still open:
   recovering the 2016, 2017 and 2024 to 2026 meetings and the missing
   outcomes from email, and committing `retainment-values-2025.html`, which
   exists only in the older local checkout of the legacy site (that checkout is
   one commit behind GitHub, so pull before committing there).
1. **Skeleton and the rule book**: site structure, styling, the baseline, the
   ledger, the layered rule book, and the Moose easter eggs.
2. **Seasons and franchises.**
3. **Trades, head to head, drafts, records.**
4. **Launch**: the notice on the legacy home page, and the link from the MFL
   league home page.

## What the email pass found

`rules/sources/email.json` holds 39 entries for the 2018 to 2026 meetings,
paraphrased and cited by date and subject, never by sender. 16 are confirmed by
the MFL archive, which is the rule book's step 6 check working early:

- **2018 scoring.** Yardage from the first yard, fractional yardage, kicker
  distance brackets, and 0.5 points per reception (passed 10 to 6) together
  account for the jump from 78 to 116 points a game.
- **No flex, ever.** Every flex and kicker or defense proposal from 2018 to
  2021 failed or was dropped, and MFL's lineup is QB1 RB2 WR3 TE1 PK1 Def1 in
  every season from 2003 to 2026.
- **2019 divisions.** The reversion passed 11 to 3, and MFL's alignment from
  2019 on matches 2007 to 2014 team for team.
- **2021 season length.** Fourteen regular-season weeks from 2021, matching
  the 18-week NFL schedule decision.
- **2021 toilet bowl pick.** Passed 10 to 3, and the draft gains a 17th
  first-round pick from 2023.
- **2020 COVID reserve list.** 2020 is the only season with 5 reserve slots.

Still unknown from email: the 2025 proposals (the meeting was cancelled and
they went to a website vote), the 2026 meeting's contents, the 2023 tiebreaker
and entry-fee polls, the 2021 extra-retainment-slot proposal, and the 2020
flex vote (though MFL shows it did not take effect).

### The message board

The boards for the league's current MFL id are readable as a guest, and
`src/fetch_message_board.py` captures them. **MFL deletes old boards.** As of
October 2026 the 2016 to 2024 boards report that they don't exist, and a 2020
topic linked from a 2021 email reports the same. Only 2025 and 2026 remain,
and both are captured. Run the capture every season, before the previous one
goes.

`rules/sources/message_board.json` holds 16 entries. It settles the 2025 votes
that email left open: dropped players become free agents immediately (two
waiver changes passed), the hybrid QB/TE player was made ineligible for the
season, and waiver priority by record and a cap on defenses both failed. It also
shows the 2026 IR spot passing, set up on Sep 8 with MFL showing 1 reserve slot,
and documents the current playoff format and seeding tiebreakers as practiced.

The raw board pages stay out of this repository, in a git-ignored `private/`
folder, because posts can carry personal names. They are the only copy once MFL
purges a season, so they need a private backup of their own.

### Where the rules record now stands

Four sources, each covering what the others miss:

| Source | Covers |
|---|---|
| `changes.html` | the 2002 to 2023 proposals |
| email | 2018 to 2026 results, announced |
| league polls | 2018 to 2026 tallies as cast on the site |
| message board | 2008 rules, 2025 and 2026 results and current practice |

Every meeting from 2018 to 2026 now has outcomes. The gaps that remain are
older, and every place that could hold them has been checked:

- **Outcomes for 2005, 2007, 2009 to 2012 and 2015.** Email reaches back only
  to about 2011, the boards for 2007, 2009, 2010 and 2012 to 2014 are switched
  off even for the commissioner, there are no polls before 2018, and the
  Internet Archive holds 7 pages of the old site and no changes page.
- **2016 and 2017.** No meeting record anywhere, and the 2017 polls page is
  empty, which fits no meeting being held.
- **Open items:** none. The commissioner settled the last five on 2026-10-29
  (the 2019 draft clock and the 2021 extra retainment slots failed, the 2023
  multi-team tiebreaker and the 2026 rotating organizer passed, and the 2023
  hybrid player was listed as a TE), recorded in
  `rules/sources/commissioner.json`.

These go to the league to confirm, rather than further searching.

## Decisions needed

1. ~~The baseline edition.~~ Settled: the 2006 edition (the Word file and the PDF are the same text).
2. Whether the rule book should come before or after the season pages. The
   recommendation is first, since it is the one thing that cannot be rebuilt
   from data.
3. Whether to search your Gmail for meeting threads. Read only, quoting
   proposal text and outcomes, never names.
4. The look. The current dashboard's style, or something new.

## Tasks

- [x] **Create the new rule book**: an HTML rule book built from the baseline
      edition, with each year's changes from `changes.html` layered in, and the
      gaps filled from email (steps 1 to 7 above)
- [x] Email pass: 39 entries for the 2018 to 2026 meetings in
      `rules/sources/email.json`, 16 of them checked against the MFL archive
- [x] Message board pass for 2025 and 2026: 16 entries in
      `rules/sources/message_board.json`, resolving the 2025 outcomes
- [x] League polls with a commissioner session: 34 rule polls, 2018 to 2026,
      with tallies, in `rules/sources/polls.json`
- [x] Old board archives with a commissioner session: 2008, 2011 and 2015.
      Three 2008 posts describe rules. 2016 to 2024 are deleted by MFL.
- [ ] Recover what neither source has: 2005 to 2012 predates the mailbox,
      and 2022 left nothing in it
- [x] Commit `retainment-values-2025.html` to the legacy site
- [x] Archive the rules record: `changes.html`, `changes2002.html`, the 2004
      HTML edition, and text extracted from the three Word and PDF editions
- [x] Site skeleton and build script (`site/build.py`, published by `.github/workflows/pages.yml`)
- [x] Moose easter eggs (all in `site/eggs.json`, built by `site/eggs.py`): `site/eggs.json`, antler hover, rivalry footnotes,
      title-season watermark, 2017 tooltip, 404 page, console moose ("Moose
      are loose!"), `/moose` museum, Moose mode
- [x] Draw the new running moose (`site/assets/manic-moose.svg`)
- [x] Season pages: standings with all-play and luck, playoffs, every week's scores, the draft's first round, trades, pickups, and that summer's rule changes
- [x] Franchise pages: record, titles, name history, how it is run (trades, waiver wire, lineups, luck, draft), season by season, head to head
- [x] Trades, head to head (matrix and a page per pairing), drafts (every pick from 2008, the original boards before), the record book, and the analysis reports as pages
- [x] Legacy-site notice at launch (the home page and the link bar)
