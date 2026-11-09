# Ownership

<!--
The record that the owner can explain the project without the agent. check_gates.py reads two sections and five
lines; keep the headings, the table columns and the line labels exactly. Answers are the owner's own words, written
down as they were said, with the document closed. Do not tidy them: a tidy answer hides what was not understood.

## Explain-back (checked when stage 5 Ship is marked passed)
One row for each of the three topics, in this order: what-it-does, how-it-breaks, how-to-recover. A separate
session, not the one that wrote the code or asked the questions, compares each answer with the code and writes the
Gap: what was missing or wrong, or "-" when there is none. Status is open while the gap stands and closed once the
owner can explain that point. An open row blocks release.

## Full round (checked when stage 6 Own is marked passed)
Questions drawn from ARCHITECTURE.md, answered closed-book: at least 3 on a Small project; on a Full project one
for each component and at least 3. Same Gap and Status rules as above. A gap keeps stage 6 open.

Either section may carry a line "Override: O<n>" naming an open entry in OVERRIDES.md for that stage; the check is
then reported as overridden and not as failed. The five lines below are always checked.

The lines, at stage 6:
  Hand-changed commit  the hash of the commit where the owner changed one module by hand; it must touch a source file
  Closed               the date stage 6 was closed, like 2026-11-09
  Re-check due         exactly 7 days after Closed
  Re-check done        "-" until the re-check has been made, then its date. When the due date has passed and this
                       is still "-", check_gates.py prints a reminder (a note, never a failure); the next working
                       session asks the questions again, and a new gap marks stage 6 as reopened.
  Graded by            the separate session that compared the answers with the code

The rows below are worked examples, marked (EXAMPLE): replace them and remove the marker. check_gates.py refuses
this file while the marker remains. The five lines are left empty on purpose and are refused until filled in.
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

Hand-changed commit:
Closed:
Re-check due:
Re-check done:
Graded by:
