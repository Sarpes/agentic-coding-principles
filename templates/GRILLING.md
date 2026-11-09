# Grilling

<!--
The record of the owner being grilled: challenged question by question until the requirements (stage 0) and the
design (stage 1) hold up. It runs on every project, Small or Full. check_gates.py reads two sections; keep the
headings, the table columns and the line label exactly.

Each section starts with the line
  Grilled with: <the skill that ran it, such as mattpocock-skills:grilling>
or, when that skill is not installed:
  Grilled with: fallback: written challenges
In the fallback the agent writes the challenges itself, one at a time, and the owner answers each.

Columns:
  Challenge         the question that pushed on a weak spot
  Owner's answer    the owner's own words, as they were said; never the agent's suggestion accepted with "yes"
  Outcome           what the answer changed: a REQ, ATK or D id that was added or changed, or "kept"

## Intake (checked when stage 0 Intake is marked passed)
At least 3 answered challenges on what "done" means and how it could break, on every project.

## Design (checked when stage 1 Design is marked passed)
At least 3 answered challenges on the chosen design, on every project.

The rows below are worked examples, marked (EXAMPLE): replace them and remove the marker. check_gates.py refuses a
section while its marker remains. The 'Grilled with:' lines are left empty on purpose and are refused until filled.
-->

## Intake

Grilled with:

| Challenge | Owner's answer | Outcome |
|---|---|---|
| Who reads the monthly summary, and what do they do with it? (EXAMPLE) | Only the shop owner, to decide what to reorder. | REQ-2 added |
| What happens when an order has no date? (EXAMPLE) | It should be listed as a problem, not skipped. | REQ-3 added |
| What would make you stop trusting the totals? (EXAMPLE) | A total that differs from the bank statement. | ATK-4 added |

## Design

Grilled with:

| Challenge | Owner's answer | Outcome |
|---|---|---|
| Why a spreadsheet and not a database? (EXAMPLE) | The owner already keeps one, and it is small. | D1 |
| Where are the totals computed, in one place or two? (EXAMPLE) | In the parser only. | D2 |
| What breaks if the spreadsheet layout changes? (EXAMPLE) | The parser; it should stop with a clear message. | kept |
