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
- **What I changed or rejected, and why:** None: the owner made no changes to the example wording.
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
- **What I changed or rejected, and why:** None: the owner made no changes to the README wording. The proof that the gate can fail is the existing test `test_cli_exit_1_on_broken_repo`, so no broken file is stored in the repository.
- **Where the AI was wrong, and how I noticed:** None found so far: the CI jobs have not run yet, so the matrix is untested on the real runners and the README claim that all four pass rests on the pull request's check results.

### 8. Final review of v0.1 and its fix wave (2026-11-06)

- **Prompt (or summary of it):** Review the finished v0.1 as a whole against the design and fix every finding: four must-fix items and a set of public-wording changes.
- **What the AI produced:** The four must-fix findings. First, the gate skipped misformed entry headings such as `### D3 Title` or `## 3.`, so those entries were never checked. Second, running the gate with no argument returned exit 2, against the design. Third, the README's "use it in a new project" steps did not copy the gate. Fourth, the pre-commit secret gate had no test. The fix wave added tests first (red: 9 failures, then 1 failure, then a mutated gate that failed the new subprocess test), then the changes; D10 and this entry record it.
- **What I kept:** All four fixes and the neutral wording changes. I also corrected entry 7: it said the CI jobs had not run yet, but CI later ran green on 4 of 4 jobs (run 42291444559), so that entry's claim was out of date.
- **What I changed or rejected, and why:** I ruled that the no-argument default is the current directory (D10) rather than keeping exit 2, because the design is binding; I also ruled that public files carry no owner-specific phrasing.
- **Where the AI was wrong, and how I noticed:** The gate's earlier tests locked in the wrong exit code for no arguments, so a passing suite hid a design violation; the whole-repository review against the design found it, not a failing test. The first pattern for AI-log headings would also have flagged a heading such as "### 2026 plans"; I noticed it while writing the test for unrelated headings, before the first run.

### 9. Working through the v0.1.1 backlog (2026-11-08)

- **Prompt (or summary of it):** Sync `main`, then work through the SHOULD items left from the final review of v0.1.
- **What the AI produced:** Failing tests first, then the fixes: invalid UTF-8 reported as a problem at its line, backtick fences handled by the renderer's rules with unclosed fences reported, a clear message for a value written below its label, section checks for the ungated templates, the stated total of principles compared with the stage files, the pre-commit hook as an enforcement kind for P5.2, one voice in the design, and D11 to D13. Results: 13 red then 83 passing, 7 red then 99 passing (1 skipped), and the gate exits 0.
- **What I kept:** All of it: the owner merged the work as proposed.
- **What I changed or rejected, and why:** None: the owner made no changes. The AI left P3.4, P1.3 and P1.7 unchanged, because the records it could read hold no measured effect for them (see D14).
- **Where the AI was wrong, and how I noticed:** The AI tried to search an archived notes folder for the missing numbers and a local rule refused the command; it did not work around the refusal. Its first test edit declared a list with a needless inline assignment, which it noticed and removed before committing. One script it wrote through a shell heredoc printed a warning about a backslash; the run's assertion still passed, but a file should have been used.

### 10. Releasing v0.1.1 (2026-11-08)

- **Prompt (or summary of it):** Merge the backlog pull request and release 0.1.1 now.
- **What the AI produced:** The merge of pull request 8, the changelog section for 0.1.1 and this entry, then the annotated tag and the GitHub release once CI on the release commit was green.
- **What I kept:** All of it: the owner asked for the release and it shipped as proposed.
- **What I changed or rejected, and why:** None: the owner decided to release now, with P3.4, P1.3 and P1.7 still lacking a measured effect.
- **Where the AI was wrong, and how I noticed:** Its first wait for CI after the merge picked up the run of the previous merge, because the new run had not registered yet, and reported success. The old run number and the blank conclusion of the new commit showed it; after that, runs were matched to the exact commit.

### 11. Closing the open requests (2026-11-08)

- **Prompt (or summary of it):** The owner does not remember the details the open notes asked for, so drop those notes and delete the merged branches.
- **What the AI produced:** It asked whether "delete them" meant the notes or the three principles. After the owner chose the notes: D14, the removal of the "Not done" line, reworded review fields in entries 5, 7, 9 and 10, and this entry.
- **What I kept:** The scope I chose from the two options the AI offered: the notes go and all 20 principles stay.
- **What I changed or rejected, and why:** I rejected removing the three principles.
- **Where the AI was wrong, and how I noticed:** The AI told the owner that entries 5 to 7 were waiting for review, but entry 6 was already filled; it had copied the range from a handover and noticed when it opened the entries.

### 12. Designing the skill (2026-11-09)

- **Prompt (or summary of it):** Turn this repository into a skill that guides a person without engineering training through strict software engineering practice, working hand in hand with the installed third-party skills.
- **What the AI produced:** A design reached in question rounds after reading the installed skills and a past project: a conductor over eight stages, a size and method choice, a test ladder, a living architecture document, a cited checklist, a go-live review and saved overrides. An independent reviewer read it cold and raised six questions; three were settled as the designer's calls and three went to the owner. D15, D16 and `docs/design-skill.md`.
- **What I kept:** The conductor shape, the two rule layers, the ladder and the installed-skill mapping.
- **What I changed or rejected, and why:** I shortened the re-check of my understanding from about 30 days to within the week, asked for a proper README naming the third-party skills, made adoption optional for earlier projects except one, and ruled that publishing does not wait for my full explanation round on that project.
- **Where the AI was wrong, and how I noticed:** Its first draft left open what counts as evidence and let a gap in understanding go unblocked, which would have allowed the anti-goal of passing every gate without understanding the project; the independent reviewer found both. It also proposed that the release wait for the owner's full explanation round, and I rejected that.
