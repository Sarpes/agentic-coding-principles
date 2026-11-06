<!--
Copy this into every pull request description (on GitHub, a file with this name in
.github/ fills it in automatically). Four parts: Goal, Choices, Measurements,
How to check. Measurements give before and after, with the source command.
The text below is a worked example: replace it.
-->

## Goal

Let users export their records as a CSV file.

## Choices

- Used the standard-library `csv` module (D3). Rejected: a spreadsheet library, which adds an install step for one feature.
- Export streams row by row. Rejected: building the whole file in memory, which fails for large tables.

## Measurements

| Measure | Before | After | Source |
|---------|--------|-------|--------|
| Tests passing | 14 of 14 | 17 of 17 | `python -m unittest` |
| Export of 10,000 rows | not possible | 0.3 s | `python bench_export.py` |

## How to check

1. Check out the branch.
2. Run `python -m unittest` and confirm 17 tests pass.
3. Run `python export.py records.csv` and open the file.
