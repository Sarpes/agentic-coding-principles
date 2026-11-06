# Handover 2026-01-15

<!--
A handover lets someone with no memory of the work (a colleague, an AI agent in a
new session, yourself in a month) continue it. Put it in docs/ with the date in the
file name. It holds STATUS; rules and decisions live in their own files and are only
pointed to. Keep three parts: status block, resume order, open items.
The content below is a worked example: replace it.
-->

## Status

- **Branch:** `feat/export`, 3 commits ahead of `main`.
- **Tests:** `python -m unittest` -> 14 tests, 0 failures.
- **Last verified:** 2026-01-15, on the development machine.

## Resume order

1. Read `README.md` and `DECISIONS.md` (D1 explains the storage choice).
2. Run `python -m unittest` and confirm 14 tests pass.
3. Open the first item under Open items.

## Open items

- Export to CSV is half done: the header row is written, the data rows are not.
- Deferred finding F1 in BUILD-LEDGER.md (memory use of the export).
