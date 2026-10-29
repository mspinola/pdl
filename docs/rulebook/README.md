# The rule book

A current, HTML rule book: the 2006 text with every change since layered in,
and the rules as of any season from 2006. All seven steps of the plan in
[../site-plan.md](../site-plan.md) are done, and the pages are online.

```bash
python3 src/rulebook_editions.py   # compare the editions  -> docs/rulebook/editions.md
python3 src/rulebook_baseline.py   # parse the baseline    -> rules/baseline.json, checked
python3 src/rulebook_ledger.py     # check the ledger      -> docs/rulebook/ledger.md
python3 src/rulebook_build.py      # apply every change, check each edit lands
python3 src/rulebook_mfl_check.py  # compare with MFL      -> docs/rulebook/mfl-check.md
python3 site/build.py              # the pages            -> site/dist/rules/
```

## 1. The baseline is the 2006 edition

The legacy site kept four copies of the rules. They hold two texts, not four
([editions.md](editions.md)):

- **2004**: the web page (`PDL_Rules.htm`, saved from Word on 2004-06-30) and
  the old Word file. 0.998 of their words are the same, and what differs is
  layout.
- **2006**: the Word file and the PDF (created 2006-09-24, modified
  2006-10-17). Word for word identical. The PDF is the Word file printed.

The 2006 text contains every change `changes.html` records as passed at the
2002 to 2006 meetings: no tied games, the tanking penalty, the Governing Board
as the last five champions, draft availability by July 4, the $25 playoff
payout, conditional picks, the trophy handoff, the $60 fee, and a forfeiting
team's opponent playing the league average. The 2004 text contains none of the
2004 to 2006 ones. So 2006 is the baseline, and the ledger starts at the 2007
meeting.

One leftover from 2002 survives in the baseline: the playoff tie-break list in
6.2 is numbered 1, 2, 5, because the 2002 meeting removed items 3 and 4 and the
list was never renumbered.

The rule text names no owner. The two personal names in it, in the trophy's name
and the nickname of the appeal clause (10.1), are not owners.

## 2. The baseline as data

[`rules/baseline.json`](../../rules/baseline.json): 52 sections, 3,581 words,
parsed from the PDF because its text keeps the scoring tables' rows intact.
Blocks are paragraphs, sub-headings, numbered or bulleted lists, and the six
scoring tables (one value per position, `null` where the book prints `x`). The
parser checks its own output: every section's words match the PDF's, and every
table row has six values.

## 3 and 4. The ledger

[`rules/ledger.json`](../../rules/ledger.json): 45 changes from 2008 to 2026,
each with the sections it touches, the season it took effect, and the sources
that establish it. The readable view is [ledger.md](ledger.md).

The ledger holds what changed the rules. Every proposal, including the ones that
failed, stays in `rules/sources/`:

| Source | Covers |
|---|---|
| `changes_html.json` | the legacy rule-change page, 2002 to 2017 (72 proposals) |
| `email.json` | the summer meeting emails, 2018 to 2026 |
| `polls.json` | the league polls with their tallies, 2018 to 2026 |
| `message_board.json` | the MFL board, 2008, 2025 and 2026 |
| `commissioner.json` | outcomes the commissioner confirmed where the record was silent |

`rulebook_ledger.py` refuses a ledger entry that names a section the baseline
lacks, or a source that does not resolve to exactly one entry.

### Checked against what MFL ran

The archive holds MFL's scoring rules and schedules for every season, and they
confirm the ledger where they can see it:

- Yardage scoring changes exactly in 2010 and 2018, as recorded. 2010 is the
  QB passing threshold at 200 and the 50-yard thresholds, 2018 fractional
  yardage from zero and 0.5 per reception.
- Field goals go from 3, 5 and 10 to 3, 5, 7 and 10 in 2018.
- The regular season goes from 13 weeks to 14, with the playoffs a week later,
  in 2021.
- Divisions, compared by franchise, are unchanged 2007 to 2014, realigned for
  2015, and back to the 2007 alignment in 2019.
- The 2013 plan to scrap divisions for two flights with relegation, written up
  as passed but labelled a hoax on the page, never ran: 2014 still has 16 teams
  in 4 divisions.

MFL encodes RB rushing from 2010 as 5 points for 50 to 59 yards and 1 per 10
from 60, which scores exactly as 1 per 10 from 50, so it is not a separate rule.

### What only the league can answer

The record left five outcomes unsettled. The commissioner confirmed four on
2026-10-29 (`rules/sources/commissioner.json`): the 2019 draft clock and the
2021 extra retainment slots failed, so they are not in the ledger, and the 2023
multi-team tiebreaker and the 2026 rotating organizer passed.

One remains, listed in [ledger.md](ledger.md): the 2023 poll on the hybrid
QB/TE player, tied 4 to 4. Until it is answered, the layered rule book shows it
as unconfirmed and does not change the text.

## 5. Layering

[`rules/amendments.json`](../../rules/amendments.json) holds the exact edit each
ledger change makes to the text: replace this sentence, add that paragraph,
rewrite this scoring row, add section 2.4 Toilet Bowl. `src/rulebook_build.py`
applies them in order of the season they took effect, so the book can be read as
of any season. Every edit must find its target exactly once, so a change applied
out of order, or to text an earlier change already replaced, stops the build
rather than being skipped. A one-season rule (the 2011 lockout, the 2020 COVID
reserve, the hybrid player rulings) and the one unconfirmed question appear as
notes beside the text and never change it. 22 of the 53 sections have changed
by 2026.

Where the record says what changed but not the new wording, the amendment
writes the rule in the book's own terms. Two of those rest on MFL rather than a
written source: the 2021 schedule (the fourteenth game is a fourth one against
the alternating non-conference division, which is what every 2021 to 2025
schedule shows) and the 2020 reserve list (MFL gave each team 5 spots).

## 6. Checked against MFL

Each change also states the facts MFL can confirm: roster size, the starting
lineup, injured reserve spots, regular-season and playoff weeks, how the
schedule splits between division and other opponents, and the scoring for
touchdowns, yardage, field goals and receptions. `src/rulebook_mfl_check.py`
compares them with MFL's archive for every season from 2006
([mfl-check.md](mfl-check.md)): 224 comparisons agree, 2 differ for a recorded
reason, and none differ otherwise. The recorded reason is 2006 and 2007, when
MFL's yardage rules are in an older encoding that cannot be read as the book's
bonus table. From 2008 MFL spells the tiers out and they match.

It also found one rule the ledger had only as a note: the 2020 COVID reserve
list, which MFL shows as 5 reserve spots that season.

The retainment spreadsheets (2010 to 2018, `rules/sources/drive.json`) agree
with section 4.3: every team uses 12 slots or fewer through 2017, and most
seasons have exactly 9 three-slot players. Two to check: 2016 lists 11 three-slot
players, and 2018 has one team at 13 slots.

## 7. The pages

`python3 site/build.py` writes the rule book to `site/dist/rules/`: the rules in
force now, the rules as of each season from 2006, and every meeting from 2002
with what passed, what failed and the sources. Each changed section is marked
with the seasons it changed and links to the record. Pages print cleanly and
read in light or dark mode. To look at them locally:

```bash
python3 -m http.server 8010 --directory site/dist
```

They are published at <https://mspinola.github.io/pdl/> by the workflow in
`.github/workflows/pages.yml`, which runs the owner-name check, verifies the
archive, builds the site and deploys it, on every push to `main` that touches
the rules, the archive, the code or the site.
