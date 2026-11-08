# Stage 5: Ship

**Gate:** a secret scan by value passed, and the pull request shows goal, choices, measurements and how to check.

### P5.1 Scan the whole history for the real secret values before pushing
- **Rule:** Before the first push, search every commit of the history for each real secret value, not only for patterns that look like secrets.
- **Why (incident):** In one project every secret value was verified absent from all commits before delivery; a pattern scan alone could not have shown that, because a real value need not match any pattern.
- **How to check:** Run a script that reads each value from `.env` and searches `git log -p --all` for it without printing it: are there 0 hits?
- **Enforced by:** human gate

### P5.2 Extend the stock secret gate where it is blind
- **Rule:** Add checks to the stock secret gate for the cases it misses, and prove each with a commit that it refuses.
- **Why (incident):** On a throwaway repository, an unquoted `NAME_API_KEY=` assignment and a file named `*.env` both passed a stock secret gate unnoticed.
- **How to check:** With the pre-commit hook in `.githooks/` enabled, stage a fake unquoted key and a fake `*.env` file on a throwaway branch: is each commit refused?
- **Enforced by:** human gate + pre-commit hook
