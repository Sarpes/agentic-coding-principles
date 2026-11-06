# Stage 4: Verify

**Gate:** real integrations run end to end, and a fresh clone starts with the documented commands.

### P4.1 Record every live run in RESULTS.md
- **Rule:** Write each live run into `RESULTS.md` with its setup, the outcome against the expectation with raw counts, open observations and the steps to reproduce it.
- **Why (incident):** No single measured incident; a live run that is not written down cannot be repeated or compared, and its numbers are later quoted from memory.
- **How to check:** Read `RESULTS.md`: does each run have setup, outcome with raw counts, observations and how to reproduce?
- **Enforced by:** template

### P4.2 Start a fresh clone with the documented commands only
- **Rule:** Clone the repository into an empty folder, follow only the commands in the README, and require the tests to pass.
- **Why (incident):** No single measured incident; a working copy hides files, settings and installed packages that a new user does not have, and only a fresh clone shows them.
- **How to check:** Run `git clone <repository> fresh`, follow the README, then run the test command: does it pass?
- **Enforced by:** CI + human gate

### P4.3 Measure the state again after cleaning up
- **Rule:** After deleting or stopping anything, measure the state again instead of trusting the command that did it.
- **Why (incident):** A background loop survived being stopped and silently recreated data volumes that had just been deleted; only a second measurement showed it.
- **How to check:** After a clean-up, list the processes, containers and volumes again: is everything that was removed still absent?
- **Enforced by:** human gate
