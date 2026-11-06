# Requirements

<!--
Traceability table: one row per requirement, copied word for word from the brief.
Columns, in this order: ID (REQ-1, REQ-2, ...; "R<n>" is for rulings in BUILD-LEDGER.md), Requirement, Decision (a DECISIONS.md number, or "-"),
Test (the test or check that proves it, or "-"), Evidence (the command and its
result, or "-"), Status.
Status is one of: open, met, not done.
A row marked "met" must have a Test and an Evidence; "-" is not allowed there.
No cell may be empty. The rows below are worked examples: replace them.
-->

| ID | Requirement | Decision | Test | Evidence | Status |
|----|-------------|----------|------|----------|--------|
| REQ-1 | The service stores records between restarts. | D1 | tests/test_storage.py::test_survives_restart | `python -m unittest` -> 14 tests, 0 failures | met |
| REQ-2 | Records can be exported as CSV. | - | - | - | open |
| REQ-3 | Users can sign in with a password. | - | - | Out of scope for this release (see Not done in DECISIONS.md). | not done |
