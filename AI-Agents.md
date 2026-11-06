# AI Agents log

This log was written entry by entry during the work. Decision numbers (Dn) refer to DECISIONS.md. Prompts are summarised as neutral task statements.

### 1. Deriving rules from a finished project (2026-11-06)

- **Prompt (or summary of it):** Scan a finished past project's repository for practices worth turning into enforced rules (decision log format, AI usage log) and list them.
- **What the AI produced:** 27 candidate rules in four groups (documents, process, engineering, security), each with its source and whether a tool-call detector could enforce it; then 14 additions covering the whole life cycle, from intake to retrospective.
- **What I kept:** All of it, and the 8-stage framework.
- **What I changed or rejected, and why:** I set the goal wider: a structure for any agent-built project, not only documents.
- **Where the AI was wrong, and how I noticed:** Its first proposal conflicted with my earlier decision-record format. The AI flagged the conflict itself, and I chose the new format for new projects.

### 2. Enforcing the documentation format with a hook (2026-11-06)

- **Prompt (or summary of it):** Add the decision log rule (seven fields) and the AI log rule to a contract enforced by a hook so they work now.
- **What the AI produced:** A contract with three blocking rules, tests written first (20 failing), then the rules. Result: 86 of 86 tests passing; 0 false alarms when replayed over 11,049 past tool calls; a live check in which an incomplete write and an edit deleting a field were both refused.
- **What I kept:** All of it.
- **What I changed or rejected, and why:** I moved the start date of the rule one day earlier so that this repository is covered by it.
- **Where the AI was wrong, and how I noticed:** The first version did not see a grouped heading ("D58-D60") and let three decisions escape every check; I found it by running the rule on a real past document. Adding Edit to the fail-closed hook would have removed the repair path; the AI found this by re-reading its own earlier decision record.

### 3. Designing this repository (2026-11-06)

- **Prompt (or summary of it):** Create a standalone public repository, "Agentic Coding Principles", that lets me run a new project end to end under these principles; a skill can come later.
- **What the AI produced:** A design (8 stages with gates, principles, templates, a documentation gate, CI) and a 5-task plan.
- **What I kept:** The v0.1 scope with the guard hook deferred (D1, D4).
- **What I changed or rejected, and why:** I removed every description of the source projects; incidents read only as lessons from projects built so far (D3).
- **Where the AI was wrong, and how I noticed:** The first plan would have written the list of private names into a public test file, and would have pushed a deliberately broken DECISIONS.md to prove CI can fail, which the new contract refuses. Both were caught in the AI's self-review of the plan.

### 4. Writing the documentation gate (2026-11-06)

- **Prompt (or summary of it):** Implement the documentation gate test-first: pure functions for the decision log, the AI log and the requirements table, plus a command-line interface with exit codes, following the field lists of the existing contract.
- **What the AI produced:** 50 tests committed first (red: the module did not exist), then `checks/check_docs.py`; the first full run passed all 50. Two decision records (D5, D6) and this entry.
- **What I kept:** All of it.
- **What I changed or rejected, and why:** I made fenced code blocks blank their lines instead of being removed, so problem line numbers match the original file (D6).
- **Where the AI was wrong, and how I noticed:** The first draft of the implementation contained a leftover dead expression in the return of the decision check, and one test computed a line number with a convoluted expression. Both were found on re-reading the code before the final run, not by a failing test.
