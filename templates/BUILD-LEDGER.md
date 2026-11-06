# Build ledger

<!--
The ledger records HOW the work is being done: the method, the rulings made along
the way and the findings you chose to defer. Write it while building, not afterwards.
Rulings: R1, R2, ... in order. Each states the question, the ruling, and what it
costs if the ruling is wrong, so a later reader can judge how much to worry.
Deferred findings are triaged: MUST (fix before release), SHOULD (fix soon),
LEAVE (accept, with the reason). The entries below are worked examples.
-->

## Method

One branch per task, tests written first, a review after each task, a merge only after the checks pass.

## Rulings

### R1. Test file name

- **Question:** Should the tests for the export feature live in `test_export.py` or in the existing `test_storage.py`?
- **Ruling:** A new file, `test_export.py`.
- **Cost if wrong:** Low. Moving tests between files takes minutes and changes no behaviour.

## Deferred findings

| ID | Finding | Triage | Reason |
|----|---------|--------|--------|
| F1 | The export function reads the whole table into memory. | SHOULD | Fine for 10,000 rows; revisit before the data grows 10-fold. |
| F2 | A comment in the storage module has an outdated example. | LEAVE | No effect on behaviour; fix when the file is next touched. |
