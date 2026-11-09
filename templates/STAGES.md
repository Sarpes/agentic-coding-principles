# Stages

<!--
The record of where the project stands. check_gates.py reads this file; keep the layout exactly.

Size: small or full. Small is one script or module with no live users, no personal data and no paid calls.
Method: normal (one session works through the plan) or sub-agent (one writer and a separate reviewer per task).
Adopted-at: N (optional). For a project that already existed: stages below N may be marked "adopted", which means
"not done under this process", never "passed". N must be in this file's first commit, and at most 5.
Traits: a, b (optional). Traits no script can detect, such as personal-data. "Traits: none" is allowed.

Status of a stage is one of:
  open        not finished
  passed      finished; the Evidence column names what proves it
  overridden  skipped on purpose; the Override column names an open entry in OVERRIDES.md for this stage
  adopted     see Adopted-at above
  reopened    stage 6 only: a re-check found a gap after the stage had passed

Evidence is a comma-separated list of file:<path> (a tracked, non-empty file inside the project) and
commit:<hash> (a hexadecimal hash on the current branch). STAGES.md and OVERRIDES.md are never evidence.
A stage may be passed only when every earlier stage is closed.
-->

Size: small
Method: normal

| Stage | Status | Evidence | Override |
|---|---|---|---|
| 0 Intake | open | - | - |
| 1 Design | open | - | - |
| 2 Plan | open | - | - |
| 3 Build | open | - | - |
| 4 Verify | open | - | - |
| 5 Ship | open | - | - |
| 6 Own | open | - | - |
| 7 Retro | open | - | - |
