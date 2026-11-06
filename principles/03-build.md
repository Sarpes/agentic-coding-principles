# Stage 3: Build

**Gate:** each task is written test-first, passes, and is reviewed by a separate reviewer.

### P3.1 Separate the author of a task from its reviewer
- **Rule:** Let one agent write a task and a different agent review it from the brief, the report and the diff only, with at most five fix rounds, each followed by a re-review limited to the fix.
- **Why (incident):** Separate review caught 61 defects (measured at the time) before delivery in one project, among them a silent data-loss path, a record written twice by two workers and a leak of sensitive data.
- **How to check:** Open each merged pull request: is there a review written by an agent or person other than the author?
- **Enforced by:** human gate

### P3.2 Name the risks in the review brief and make reviewers run probe inputs
- **Rule:** List the known risks in every review brief and require the reviewer to run crafted inputs against the code, not only to read it.
- **Why (incident):** A leak through a protection gate was found only by a reviewer who ran crafted inputs; earlier reviews that only read the code had passed it.
- **How to check:** Open the review of the last merged pull request: does it list the inputs it ran and their results?
- **Enforced by:** human gate

### P3.3 Never silence a flaky test with retries
- **Rule:** Reproduce a test that fails only sometimes and fix its cause instead of adding retries.
- **Why (incident):** One of five full test runs (measured at the time) failed in one project; the cause was a timing assumption in the code, fixed at the root instead of hidden behind a retry.
- **How to check:** Search the tests for retry decorators or loops around assertions: is the answer none?
- **Enforced by:** human gate

### P3.4 Prove that every gate can fail
- **Rule:** For every protection the project claims, write a test that turns red when the protection is removed, and watch it turn red once.
- **Why (incident):** A row-level access control gate and a protection gate for sensitive data were each shown failing with the protection removed before they were trusted.
- **How to check:** Remove the protection on a scratch branch and run the tests: does at least one test fail?
- **Enforced by:** human gate

### P3.5 Build a walking skeleton with the real integrations early
- **Rule:** Run one end-to-end pass through every real external service within the first days of the build.
- **Why (incident):** In one project the first real end-to-end run came last; it is the only test that exercises all integrations together, so problems between them could surface only at the end.
- **How to check:** Read `RESULTS.md`: is the first end-to-end run with real services dated within the first days of the build?
- **Enforced by:** human gate

### P3.6 Save state at every task boundary and write a dated handover at session end
- **Rule:** Update the build ledger and commit at the end of every task, and write a dated handover document when a session ends.
- **Why (incident):** In one project work was cut off by usage limits three times (measured at the time) and resumed each time without loss, because the last task boundary was always committed.
- **How to check:** Run `git status` at a task boundary: is the working tree clean, and is there a handover file dated today?
- **Enforced by:** template + human gate
