# AI Agents log

<!--
Log of AI use, written entry by entry during the work, not afterwards.
One entry per task, numbered 1, 2, ... in order, no gaps. Five fields, none blank.
Prompts are summarised as neutral task statements: no secrets, no private names.
Be honest in the last field: it is the one that makes the log useful.
Decision numbers (Dn) refer to DECISIONS.md.
The example below is a worked example, marked (EXAMPLE) in its heading: replace it with your
first real entry and remove the marker. check_gates.py refuses evidence that still carries it.
At the end of the project, write the "## Retro" section below: what each "where the AI was wrong"
entry became (a rule, a template change, or a recorded "won't fix").
-->

This log was written entry by entry during the work. Decision numbers (Dn) refer to DECISIONS.md.

### 1. Choosing a test framework (2026-01-15) (EXAMPLE)

- **Prompt (or summary of it):** Compare three test frameworks for a small command-line tool and recommend one, listing the install cost of each.
- **What the AI produced:** A table of three frameworks with install steps, a recommendation for the standard-library one, and a sample test of 12 lines.
- **What I kept:** The recommendation and the sample test.
- **What I changed or rejected, and why:** I dropped the second framework from the table because its latest release no longer supports our minimum language version.
- **Where the AI was wrong, and how I noticed:** It stated that the third framework needs no install; running `pip install` in a clean environment showed it does. I now check install claims in a clean environment (D1 records the related database choice).

## Retro

<!-- Write this at the end of the project, not before. One line per "where the AI was wrong" entry: what it became. -->

