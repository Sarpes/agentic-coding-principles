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

### 5. Writing the templates (2026-11-06)

- **Prompt (or summary of it):** Write eight templates (decision log, AI log, requirements table, build ledger, results, handover, glossary, pull request), each with one worked example and guidance in HTML comments; the three gated ones must pass the documentation gate.
- **What the AI produced:** A test file written first (red: 11 errors, one per missing template), then the eight templates; the full suite then passed (52 tests) and the gate reported no problems. Decision D7 and this entry.
- **What I kept:** All of it.
- **What I changed or rejected, and why:** None: I have not reviewed the example wording yet; the owner reviews it at the pull request.
- **Where the AI was wrong, and how I noticed:** None found so far: the first run of the gate on the three templates was clean, so no correction was needed; the examples have not yet had an independent review.

### 6. Writing the principles (2026-11-06)

- **Prompt (or summary of it):** Write the principles as eight stage files and an index, one fixed four-field format per principle, telling every lesson only as a lesson from projects built so far, with a test written first.
- **What the AI produced:** A test file committed first (red: 9 failures and 11 errors because the files were missing, the name scan skipped), then a first draft of 40 principles in eight files and an index. After two review rounds: 20 principles (stages 0 to 7: 3, 7, 0, 5, 1, 2, 1, 1), two rules folded into a neighbour about the same document, 18 rules moved to "Not done (and why)" as candidates awaiting a real incident, and tests that refuse a principle without an incident and prove the private-name scan fires on a probe repository. Result: 61 tests pass, the gate reports no problems. Decision D8 and this entry.
- **What I kept:** The four-field format, the stage files and the index; the 20 principles that have a real incident behind them.
- **What I changed or rejected, and why:** The review rejected the 16 principles that only gave a rationale, because the framework promises a lesson behind every rule; it limited "Enforced by" to mechanisms that exist publicly, so the private hook now reads "contract hook (planned, v0.2)"; it asked for incidents that state what happened instead of a benefit or a result, more general wording, and checks that name a file or a command.
- **Where the AI was wrong, and how I noticed:** The first draft kept 16 rules without an incident, claimed "contract hook" and CI for rules that no public mechanism enforces, and left wording that hinted at the source domain; a separate reviewer found all of these. The AI also briefly created a stray empty file outside the repository with a mistyped shell command, noticed it from the hung command and deleted it.

### 7. Writing the CI workflow and the README (2026-11-06)

- **Prompt (or summary of it):** Add a GitHub Actions workflow that runs the tests and the documentation gate on two Python versions and two operating systems with read-only permissions, and write the final README (badge, the eight-stage table, how to use it in a new project, how it is tested) and the 0.1.0 changelog entry.
- **What the AI produced:** `.github/workflows/ci.yml` (four jobs), the README, the changelog section, decision D9 and this entry. Local result before the commit: 61 tests run, 1 skipped (the private-name scan, which needs a local environment variable), the gate exits 0, and the workflow file parses as YAML with the intended matrix. The CI runs themselves are started and checked by the owner's controller after the push, not by this task.
- **What I kept:** All of it.
- **What I changed or rejected, and why:** None: I have not reviewed the README wording yet; the owner reviews it at the pull request. The proof that the gate can fail is the existing test `test_cli_exit_1_on_broken_repo`, so no broken file is stored in the repository.
- **Where the AI was wrong, and how I noticed:** None found so far: the CI jobs have not run yet, so the matrix is untested on the real runners and the README claim that all four pass rests on the pull request's check results.
