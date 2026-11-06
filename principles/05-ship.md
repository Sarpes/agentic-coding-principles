# Stage 5: Ship

**Gate:** a secret scan by value passed, and the pull request shows goal, choices, measurements and how to check.

### P5.1 Scan the whole history for the real secret values before pushing
- **Rule:** Before the first push, search every commit of the history for each real secret value, not only for patterns that look like secrets.
- **Why (incident):** In one project every secret value was verified absent from all commits before delivery; a pattern scan alone cannot prove that, because a real value need not match any pattern.
- **How to check:** Run a script that reads each value from `.env` and searches `git log -p --all` for it without printing it: are there 0 hits?
- **Enforced by:** human gate

### P5.2 Extend the stock secret gate where it is blind
- **Rule:** Add checks to the stock secret gate for the cases it misses, and prove each with a test that makes it fire.
- **Why (incident):** On a throwaway repository, an unquoted `NAME_API_KEY=` assignment and a file named `*.env` both passed a stock secret gate unnoticed.
- **How to check:** Commit a fake unquoted key and a fake `*.env` file on a throwaway branch: is each commit refused?
- **Enforced by:** contract hook + CI

### P5.3 Keep keys out of chat, logs and git
- **Rule:** Let the human create `.env` and type the keys, and never let a key pass through the agent's conversation, a log or a commit.
- **Why (incident):** No single measured incident; a key that has appeared in a conversation or a log must be treated as leaked and rotated.
- **How to check:** Ask: was every key in `.env` typed by the human, and does `.gitignore` exclude `.env`?
- **Enforced by:** contract hook + human gate

### P5.4 Merge with merge commits and never squash
- **Rule:** Merge pull requests with a merge commit from the command line, so the history keeps every step of the work.
- **Why (incident):** No single measured incident; a squash merge replaces the red-test commit, the implementation and the fixes with one commit, so the history no longer shows that a test failed first.
- **How to check:** Run `git log --merges --oneline`: does every merged pull request appear as a merge commit?
- **Enforced by:** human gate

### P5.5 Describe every pull request with goal, choices, measurements and how to check
- **Rule:** Write each pull request description with four sections: Goal, Choices (with the rejected alternatives), Measurements (before and after, with their source) and How to check.
- **Why (incident):** No single measured incident; a reviewer who sees only the diff cannot tell what was rejected or how the result was measured.
- **How to check:** Open the pull request: does it have the four sections of `templates/PULL_REQUEST_TEMPLATE.md`, each filled?
- **Enforced by:** template

### P5.6 Log AI usage while working, five fields per entry
- **Rule:** Write each entry of `AI-Agents.md` during the work, with all five fields filled and the prompt summarised as a neutral task statement.
- **Why (incident):** No single measured incident; an AI log written from memory at the end loses the corrections, which are the part a reader most needs.
- **How to check:** Run `python checks/check_docs.py .` and confirm exit 0.
- **Enforced by:** check_docs + contract hook

### P5.7 End with a list of defects caught by review and a reflection
- **Rule:** Close the project with an appendix of the defects that review caught and a reflection on what worked, where the AI needed control and what you would change.
- **Why (incident):** No single measured incident; the defects caught by review are the evidence that review was needed, and they are lost once the branches are merged.
- **How to check:** Ask: does the delivered documentation contain a defect appendix and a reflection with those three questions answered?
- **Enforced by:** human gate
