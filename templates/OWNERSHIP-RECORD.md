# Ownership record

<!--
PRIVATE. This file lives in the project's private companion repo, at the path named by the 'Record:' line of the
project's OWNERSHIP.md (usually ../<project>-internal/ownership/OWNERSHIP.md). It holds the owner's own words about
how well they understand the system. It never goes into the project repo, which may be public: check_gates.py
refuses an '## Explain-back' or '## Full round' section in the project's OWNERSHIP.md at every stage. The session
that runs the explain-back writes the answers straight into this file.

check_gates.py reads two sections and one line; keep the headings, the table columns and the line label exactly.
Answers are the owner's own words, written down as they were said, with the documents closed. Do not tidy them: a
tidy answer hides what was not understood.

## Explain-back (checked when stage 5 Ship is marked passed)
One row for each of the three topics, in this order: what-it-does, how-it-breaks, how-to-recover. A separate
session, not the one that wrote the code or asked the questions, compares each answer with the code and writes the
Gap: what was missing or wrong, or "-" when there is none. Status is open while the gap stands and closed once the
owner can explain that point. An open row blocks release.

## Full round (checked when stage 6 Own is marked passed)
Questions drawn from ARCHITECTURE.md, answered closed-book: at least 3 on a Small project; on a Full project one
for each component and at least 3. Same Gap and Status rules as above. A gap keeps stage 6 open.

Either section may carry a line "Override: O<n>" naming an open entry in the project's OVERRIDES.md for that stage;
the check is then reported as overridden and not as failed.

The line, at stage 6:
  Graded by            the separate session that compared the answers with the code

The rows below are worked examples, marked (EXAMPLE): replace them and remove the marker. check_gates.py refuses
this file while the marker remains. The line is left empty on purpose and is refused until filled in.
-->

## Explain-back

| Topic | Question | Answer | Gap | Status |
|---|---|---|---|---|
| what-it-does | In your own words, what does this do, and for whom? (EXAMPLE) | It reads a spreadsheet of orders and writes a monthly summary for the shop owner. | - | closed |
| how-it-breaks | What is the most likely way it fails? (EXAMPLE) | If the spreadsheet has a blank date, the summary skips that order without saying so. | It also fails on a date written in another format. | closed |
| how-to-recover | If it stops working tonight, what do you do first? (EXAMPLE) | Run it again on the saved copy of the spreadsheet. | - | closed |

## Full round

| Question | Answer | Gap | Status |
|---|---|---|---|
| What does the Parser component do, and what does it hand to the next part? (EXAMPLE) | It turns each spreadsheet row into a record and passes the list to the exporter. | - | closed |
| Which file would you open first if a total were wrong, and why? (EXAMPLE) | The exporter, because it adds the totals. | The totals are added in the Parser; the exporter only formats them. | closed |
| Which third-party package could you remove, and what would stop working? (EXAMPLE) | The spreadsheet reader; nothing could be read. | - | closed |

Graded by:
