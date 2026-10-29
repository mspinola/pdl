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

1. **Settle the baseline edition.** Diff the 2004, 2006 and older editions
   section by section, and check which of the changes recorded as passed (2002
   to 2006) each one already contains. The newest edition that contains them
   all is the baseline. The expectation is the 2006 PDF.
2. **Turn the baseline into data.** The book is numbered (1.0 Introduction, 1.1
   Purpose, and on through about 70 sections, around 4,100 words). Store it as
   `rules/baseline.json`, one record per section with its number, title and
   text, so every page is generated from it rather than hand-edited.
3. **Build the change ledger from `changes.html`.** One record per proposal:
   meeting year, the proposal as written, outcome (passed, failed, tabled or
   unknown), the vote where recorded, the sections it touches, the season it
   took effect, and its source.
4. **Fill the gaps from email and Drive.** Each record added this way cites its
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
   ledger, and the layered rule book.
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

The message board is the next source. It is behind a login: the API refuses
it, and so do the pages.

## Decisions needed

1. The baseline edition. The recommendation is the 2006 PDF, confirmed by step 1.
2. Whether the rule book should come before or after the season pages. The
   recommendation is first, since it is the one thing that cannot be rebuilt
   from data.
3. Whether to search your Gmail for meeting threads. Read only, quoting
   proposal text and outcomes, never names.
4. The look. The current dashboard's style, or something new.

## Tasks

- [ ] **Create the new rule book**: an HTML rule book built from the baseline
      edition, with each year's changes from `changes.html` layered in, and the
      gaps filled from email (steps 1 to 7 above)
- [x] Email pass: 39 entries for the 2018 to 2026 meetings in
      `rules/sources/email.json`, 16 of them checked against the MFL archive
- [ ] Message board pass, which needs a commissioner sign-in (see below)
- [ ] Recover what neither source has: 2005 to 2012 predates the mailbox,
      and 2022 left nothing in it
- [ ] Commit `retainment-values-2025.html` to the legacy site
- [x] Archive the rules record: `changes.html`, `changes2002.html`, the 2004
      HTML edition, and text extracted from the three Word and PDF editions
- [ ] Site skeleton and build script
- [ ] Season pages
- [ ] Franchise pages
- [ ] Trades, head to head, drafts, records
- [ ] Legacy-site notice at launch
