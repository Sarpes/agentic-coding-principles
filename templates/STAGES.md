# Stages

<!--
The record of where the project stands. check_gates.py reads this file; keep the layout exactly.

Size: small or full. Small is one script or module with no live users, no personal data and no paid calls.
Method: normal (one session works through the plan) or sub-agent (one writer and a separate reviewer per task).
Cycle: N. The first cycle of work is 1. Starting another cycle (init_project.py --new-cycle) archives this
file and adds one; the gate measures commit evidence from the oldest commit whose STAGES.md holds the current
number, so never reuse or lower a number.
Skill-version: the version of the agentic-principles skill this project's layout follows, written by
init_project.py. When the skill changes the layout in a later release, check_gates.py lists what to change as
notes; after making the changes, raise this number to the new version.
Adopted-at: N (optional). For a project that already existed: stages below N may be marked "adopted", which means
"not done under this process", never "passed". Allowed in cycle 1 only. N must be in the first commit that ever
added this file, and at most 5.
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
Cycle: 1
Skill-version: 0.3.0

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
