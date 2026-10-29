# The rule book

Work toward a current, HTML rule book: the 2006 text with every change since
layered in. Steps 1 to 4 of the plan in [../site-plan.md](../site-plan.md) are
done. Layering (5), the MFL check (6) and publishing (7) are next.

```bash
python3 src/rulebook_editions.py   # compare the editions  -> docs/rulebook/editions.md
python3 src/rulebook_baseline.py   # parse the baseline    -> rules/baseline.json, checked
python3 src/rulebook_ledger.py     # check the ledger      -> docs/rulebook/ledger.md
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

[`rules/ledger.json`](../../rules/ledger.json): 47 changes from 2008 to 2026,
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

MFL also shows one thing no written source mentions: from 2010, RBs score a
5-point step at 50 rushing yards, then 1 per 10 from 60, where everyone else
scores 1 per 10 from 50. Step 6 should decide whether the rule book states it.

### What only the league can answer

Five changes the record does not settle, listed in [ledger.md](ledger.md):
the 2019 draft clock, the 2021 extra retainment slots, the 2023 multi-team
tiebreaker and hybrid-player polls, and the 2026 rotating organizer. Until the
league answers, the layered rule book shows them as unconfirmed and does not
change the text.
