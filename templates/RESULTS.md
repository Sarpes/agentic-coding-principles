# Results

<!--
Results of one experiment or measurement. Keep four parts: setup, outcome versus
expected (with raw counts next to rates), observations, how to reproduce.
Numbers come from a run, not from memory: name the command or file they came from.
With small samples, show the raw counts (for example 3 of 20), not only a percentage.
The content below is a worked example: replace it.
-->

## Setup

Compared two sorting approaches on 20 generated lists of 1,000 numbers each. Same machine, same Python version, one run per list.

## Outcome versus expected

| Approach | Expected | Observed | Raw count |
|----------|----------|----------|-----------|
| Built-in sort | all 20 lists sorted correctly | 20 of 20 correct | 20/20 |
| Hand-written sort | all 20 lists sorted correctly | 18 of 20 correct (90%) | 18/20 |

Source: `python compare_sorts.py --seed 7` printed the table above.

## Observations

- The two failures both involved lists with repeated values.
- With 20 lists, 90% could be a real defect rate or chance; the failing cases are the evidence, not the rate.

## How to reproduce

1. Run `python compare_sorts.py --seed 7`.
2. Compare the printed counts with the table above.
