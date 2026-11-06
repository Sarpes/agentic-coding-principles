# Stage 3: Build

**Gate:** each task is written test-first, passes, and is reviewed by a separate reviewer.

### P3.1 Separate the author of a task from its reviewer
- **Rule:** Let one agent write a task and a different agent review it from the brief, the report and the diff only, with at most five fix rounds, each followed by a re-review limited to the fix.
- **Why (incident):** Separate review caught 61 defects before delivery in one project, among them a silent data-loss path, a race condition that could write the same record twice and a leak of personal data.
- **How to check:** Ask: for every merged task, is there a review written by someone other than the author?
- **Enforced by:** human gate

### P3.2 Name the risks in the review brief and make reviewers run probe inputs
- **Rule:** List the known risks in every review brief and require the reviewer to run crafted inputs against the code, not only to read it.
- **Why (incident):** A leak through a data-protection gate was found only by a reviewer who ran crafted inputs; reading the code had not revealed it.
- **How to check:** Read the last review: does it list the inputs it ran and their results?
- **Enforced by:** human gate

### P3.3 Run the full test suite after every merge and verify instead of trusting
- **Rule:** Run the whole test suite after every merge, and settle every "cannot verify" item in a report by reading the code.
- **Why (incident):** No single measured incident; a report that says "cannot verify" is an open question, and in projects built so far reading the code settled each one within minutes.
- **How to check:** Run `python -m unittest` (or the project's test command) on the merged branch: does it pass, and does any report still contain an unresolved "cannot verify"?
- **Enforced by:** CI + human gate

### P3.4 Never silence a flaky test with retries
- **Rule:** Reproduce a test that fails only sometimes and fix its cause instead of adding retries.
- **Why (incident):** One of five full test runs failed in one project; the cause was a timing assumption in the code, fixed at the root instead of hidden behind a retry.
- **How to check:** Search the tests for retry decorators or loops around assertions: is the answer none?
- **Enforced by:** human gate

### P3.5 Give parallel workspaces separate container project names
- **Rule:** When several working copies of the repository run tests at the same time, give each its own container project name so their test databases cannot collide.
- **Why (incident):** No single measured incident; two working copies that share one container project name share one test database, and their tests then fail or pass for reasons unrelated to the code.
- **How to check:** Ask: does each parallel working copy set its own container project name before starting containers?
- **Enforced by:** human gate

### P3.6 Prove that every gate can fail
- **Rule:** For every protection the project claims, write a test that turns red when the protection is removed, and watch it turn red once.
- **Why (incident):** A row-level access control gate and a data-protection gate were each shown failing with the protection removed before they were trusted.
- **How to check:** Remove the protection on a scratch branch and run the tests: does at least one test fail?
- **Enforced by:** CI

### P3.7 Record the intent before every write to an external system
- **Rule:** Before writing to an external system, store the intent with a frozen request body and a deterministic idempotency key, retry only with the same key, and reconcile open intents before creating a new one.
- **Why (incident):** With this pattern, two full runs with injected failures produced 0 duplicate records in the external system.
- **How to check:** Run the test suite with failure injection switched on: is the duplicate count 0?
- **Enforced by:** CI

### P3.8 Have a human check every benchmark label
- **Rule:** Let a human check every label in an evaluation set, and report results as raw counts next to rates.
- **Why (incident):** No single measured incident; labels made only by the AI that is being evaluated make the benchmark circular, because the model is then graded against its own answers.
- **How to check:** Ask: is each label in the evaluation set marked as checked by a human, and does every reported rate show its raw count?
- **Enforced by:** human gate

### P3.9 Keep raw personal data out of test fixtures
- **Rule:** Use invented data in test fixtures, and allow marked excerpts of real data only in the test set of a data-protection gate, with a header that says why.
- **Why (incident):** No single measured incident; a fixture is copied, shared and committed far more freely than production data, so real personal data in it leaks by default.
- **How to check:** Read the fixtures folder: does any file other than the data-protection test set contain real personal data?
- **Enforced by:** human gate

### P3.10 Build a walking skeleton with the real integrations early
- **Rule:** Run one end-to-end pass through every real external service within the first days of the build.
- **Why (incident):** In one project the first real end-to-end run came last; it is the only test that exercises all integrations together, so problems between them surfaced at the latest possible moment.
- **How to check:** Ask: is there a dated record of an end-to-end run with real services from the first days of the build?
- **Enforced by:** human gate

### P3.11 Approve every paid call first and record its cost
- **Rule:** Get the human's approval before each paid call to an external service, and record its estimated and actual cost in a cost ledger.
- **Why (incident):** No single measured incident; an agent that can spend money without approval has no limit except the account's.
- **How to check:** Compare the provider's billing page with the cost ledger: is every charge listed with an approval?
- **Enforced by:** human gate

### P3.12 Save state at every task boundary and write a dated handover at session end
- **Rule:** Update the build ledger and commit at the end of every task, and write a dated handover document when a session ends.
- **Why (incident):** In one project work was cut off by usage limits three times and resumed each time without loss, because the last task boundary was always committed.
- **How to check:** Run `git status`: is the working tree clean at each task boundary, and is there a handover dated today?
- **Enforced by:** template + human gate
