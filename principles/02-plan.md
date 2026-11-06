# Stage 2: Plan

**Gate:** every task has a definition of done.

### P2.1 Give every task the same definition of done
- **Rule:** Treat a task as done only when a test was seen failing first, then passing, the work was reviewed, the decision and ruling entries are current and the requirement row is updated.
- **Why (incident):** No single measured incident; in projects built so far, tasks declared done without one of these steps were the ones that came back later.
- **How to check:** For the last finished task, ask: is there a red test commit before the implementation commit, a review, and an updated requirement row?
- **Enforced by:** template + human gate

### P2.2 Keep a build ledger and never drop a deferred finding
- **Rule:** Record every implementation ruling with its cost if wrong in `BUILD-LEDGER.md`, list minor findings that are deferred, and sort them into MUST, SHOULD and LEAVE at the end of the build.
- **Why (incident):** No single measured incident; a minor finding that is deferred without being written down is forgotten, and the end-of-build triage is the only point where all of them are seen together.
- **How to check:** Read the "Deferred findings" section of `BUILD-LEDGER.md`: does every entry carry MUST, SHOULD or LEAVE before shipping?
- **Enforced by:** template
