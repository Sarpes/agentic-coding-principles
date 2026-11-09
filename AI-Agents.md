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

### 13. Reviewing the design and plan before building (2026-11-09)

- **Prompt (or summary of it):** Before development starts, have fresh agents check the design and plan against the owner's own words, including by loading the installed skills to inspect them.
- **What the AI produced:** Three independent reviews. The first found 12 must-fix problems, among them gates that passed on setup files and installed skills whose next steps skipped stages. The second loaded 16 installed skills and found 8 more. A focused third pass confirmed most fixes and found 5 mistakes the fixes had introduced, all corrected. The owner added an explain-back that blocks release, a lighter Small path and re-confirmation of overrides.
- **What I kept:** All of the fixes, and the reduced list of dependency file types for this version.
- **What I changed or rejected, and why:** I kept the trust limit for this version, printed on every run, and kept the re-check at the next working session instead of a scheduled reminder.
- **Where the AI was wrong, and how I noticed:** The approved design let empty content pass most gates, which three independent readers exposed and the author had not seen. The first round of fixes also carried errors of its own, including a test that could not pass as written and a template that would have raised a false alarm on every full-size project.

### 14. Gate core: stages, evidence and overrides (2026-11-09)

- **Prompt (or summary of it):** Build the first part of the stage gate script: read the stage table, check the evidence each passed stage names, and check the override log, test-first, using real temporary git repositories and not mocks.
- **What the AI produced:** 130 tests written first against empty stubs (seen failing class by class), then the script, the stage and override templates and a marker on every worked example. D17 records the typed, per-stage evidence choice.
- **What I kept:** None: the owner reviews this at the pull request.
- **What I changed or rejected, and why:** None: the owner reviews this at the pull request.
- **Where the AI was wrong, and how I noticed:** A small edit to the test file, written through a shell here-document, turned a backslash-n into a real line break and broke the file; the first test run failed with a syntax error and the line was fixed with an editor call. The suite then passed on the first run, which proves little, so two rules were broken on purpose (any commit counts as history; the setup commit counts as after) and the matching tests went red.

### 15. Architecture checks: file map, dependencies, test table, attacks (2026-11-09)

- **Prompt (or summary of it):** Add the checks for the architecture document and the attack list to the stage gate script, test-first, one test class at a time against stubs that return nothing, with real temporary git repositories; write the two templates.
- **What the AI produced:** 83 failing tests across four classes (seen failing on their own assertions) in a first commit, then the checks, the manifest readers, the stage timing and two templates, with every worked example marked. D18 records why each check binds at its own stage.
- **What I kept:** None: the owner reviews this at the pull request.
- **What I changed or rejected, and why:** None: the owner reviews this at the pull request.
- **Where the AI was wrong, and how I noticed:** The whole suite passed on the first run, so eight rules were broken on purpose on a copy. Three survived: a row for ATK-1 was never tried against a part list holding only ATK-10, the test for a bare slash passed for the wrong reason (a different message also contained the slash), and one survivor changed nothing because table cells are already trimmed. The two real gaps got tests; the third was recorded as an equivalent change.

### 16. Go-live and ownership checks (2026-11-09)

- **Prompt (or summary of it):** Add trait detection, the Small size refusal, the go-live review table, the explain-back and the full round with the hand-changed commit and the 7-day re-check to the stage gate script, test-first, one test class at a time against stubs.
- **What the AI produced:** 168 failing tests across nine classes in a first commit, then the checks, the stage wiring (explain-back and go-live at stage 5, full round at stage 6, a re-check reminder that is only a note), the `--go-live` command and two templates with marked worked examples.
- **What I kept:** None: the owner reviews this at the pull request.
- **What I changed or rejected, and why:** None: the owner reviews this at the pull request.
- **Where the AI was wrong, and how I noticed:** A template test looked for the word "answer" and matched the AI's own message "compared the answers"; the check was loose, not the code. Of 43 rules broken on a throwaway copy, two survived (the manual-manifests path and a missing ownership file at stage 5) and got tests; one mutation matched two places and was rewritten to match one.

### 17. Companions mapping and installed-skill checker (2026-11-09)

- **Prompt (or summary of it):** Write the design's mapping of capabilities to installed skills, agents and commands as one data file, plus a checker that reports which of them are not installed or not enabled, test-first against stubs.
- **What the AI produced:** 39 tests (24 failing and 1 erroring against stubs) in a first commit, then `companions.json` with the 30 rows of the design table, and `check_companions.py`, which reads the enabled-plugin list, takes the newest version folder of each plugin and takes skill names from each `SKILL.md` frontmatter.
- **What I kept:** None: the owner reviews this at the pull request.
- **What I changed or rejected, and why:** None: the owner reviews this at the pull request.
- **Where the AI was wrong, and how I noticed:** The first real run listed `anthropic-skills:deep-research` as missing although the session lists it; that skill does not come from the plugin cache, so the checker cannot see it. The report is therefore a prompt to compare with the session's own skill list, as the design already says.

### 18. Engineering checklist and its builder (2026-11-09)

- **Prompt (or summary of it):** Write the engineering checklist of design section 8: items in plain words, each citing a page of one of six named primary sources read while the item is written, plus a builder that checks every item and generates `checklist/checklist.json` for the go-live review, test-first against a stub.
- **What the AI produced:** 42 tests (25 failing and 7 erroring against the stub) in a first commit, then 40 items in six area files, a README with the item format, traits and sources, and `build_checklist.py`, which takes its trait names from `check_gates.py` and refuses blank fields, sources without an `https://` address, unknown traits, unmapped companions and numbering gaps.
- **What I kept:** None: the owner reviews this at the pull request.
- **What I changed or rejected, and why:** None: the owner reviews this at the pull request.
- **Where the AI was wrong, and how I noticed:** The first drafts cited the NIST landing page although the text had been read from the PDF, and gave Google SRE book chapter numbers and a full chapter title that came from memory, not from the pages fetched. Both were found while checking each citation against the pages read, and replaced with the PDF address and the chapter names as fetched.

### 19. Project setup script (2026-11-09)

- **Prompt (or summary of it):** Write the script that starts or adopts a project under the skill: it copies the templates and gate scripts, writes a marked block into the project's instructions file, adds a continuous-integration workflow, refreshes the copied checks and archives the stage record for a new cycle, test-first against a stub, with real temporary git repositories.
- **What the AI produced:** 83 tests in a first commit (75 failing or erroring against the stub), then `init_project.py`, the workflow template and a Retro/workflow test in the template tests; the script opens every copied file in create-only mode and reports what it kept.
- **What I kept:** None: the owner reviews this at the pull request.
- **What I changed or rejected, and why:** None: the owner reviews this at the pull request.
- **Where the AI was wrong, and how I noticed:** All tests passed on the first run, so 42 rules were broken on a throwaway copy; 3 survived (two marker blocks, markers in the wrong order, a non-UTF-8 instructions file) and got tests, then all 3 went red. Also, a new cycle written in place shows git a modified file, not a new one, which would weaken the commit-evidence rule; the script now tells the owner to commit the removal and the new file separately.

### 20. Review round on the setup script: the Cycle line and linked destinations (2026-11-09)

- **Prompt (or summary of it):** Fix two review findings test-first: make the start of a work cycle a value the gate reads from the stage file instead of an instruction the owner must follow, and make the setup script refuse any destination that is a link or resolves outside the project.
- **What the AI produced:** 32 failing tests in a first commit (16 in the setup tests, 15 in the gate tests, 1 in the template tests), then a required `Cycle: N` line, a function that returns the oldest commit holding the current number, replacement of the old first-commit lookup, a guard on every destination with temporary-file replacement, and decision D20.
- **What I kept:** None: the owner reviews this at the pull request.
- **What I changed or rejected, and why:** None: the owner reviews this at the pull request.
- **Where the AI was wrong, and how I noticed:** The first version of the setup script handled the new-cycle risk with a printed note, which enforced nothing; the review caught it. Also, an existing test restarted the stage file with the same number and kept passing under the new rule only after I gave it a new number, and a heredoc turned a newline escape in a test into a real newline, which I saw when I read the file back.

### 21. The skill: router, stage files and plugin manifests (2026-11-09)

- **Prompt (or summary of it):** Write the skill that conducts a project through the eight stages, test-first and following the skill-writing method: failing file tests, pressure scenarios on fresh sub-agents without the skill, then the router, eight stage files and the plugin manifests, then the same scenarios with the skill.
- **What the AI produced:** 18 file tests in a first commit (1 failure and 37 errors against nothing), a router of 93 lines, eight stage files, two manifests at version 0.2.0, and a description worded around staged gates so it does not compete with the repository-starting skill. Scenario runs: 20 without the skill and 14 with it (7 scenarios, twice each); all 14 held. Raw output is kept out of this repository.
- **What I kept:** None: the owner reviews this at the pull request.
- **What I changed or rejected, and why:** None: the owner reviews this at the pull request.
- **Where the AI was wrong, and how I noticed:** The first scenario projects cited unfilled templates as evidence, so the gate failed and gave each test subject a second reason to stop; most of the first baseline therefore looked fine, and rebuilding three projects with adopted stages exposed the real failures. A draft of the go-live step listed the kinds of risk to look for and came close to giving away the acceptance test's answers; I saw that on rereading and removed it. One of 24 rules broken on a throwaway copy survived at first because my change missed a capitalised "By hand", so the fault was in the change and not the test. Scenario sub-agents were told to read the skill, so nothing here shows that the description or the project block loads it.

### 22. Review round on the skill (2026-11-09)

- **Prompt (or summary of it):** Fix seven review findings: treat the companion report as a hint, state the start order, make the trigger check's proof real, run the gate at session start, keep design answers in the owner's words, explain seven terms in plain words, and repeat the "just close it" scenario with a passing gate.
- **What the AI produced:** 5 failing tests in a first commit, then the router and stage file changes, and two new scenario runs on a project whose gate exits 0; both held.
- **What I kept:** None: the owner reviews this at the pull request.
- **What I changed or rejected, and why:** None: the owner reviews this at the pull request.
- **Where the AI was wrong, and how I noticed:** The test that was meant to prove the trigger check could fire compared a string with itself, so it proved nothing; the review caught it. The Stage 5 file said a Small project needs the go-live file only when traits are detected, but the gate also asks for it when no trait is detected, because some checklist items always apply; building the passing-gate project showed this, and the file now states what the gate does.

### 23. Second review round: the go-live template and the Small rule (2026-11-09)

- **Prompt (or summary of it):** Take the acceptance test's expected findings out of the go-live template by giving it an unrelated worked example, search the skill, templates and checklist for the same phrases, and make the gate stop requiring the go-live file on a Small project with no traits, as the design says.
- **What the AI produced:** 8 new gate tests in a first commit (4 red; the firing cases and the guard passed from the start, and 3 existing tests now declare a trait), then a single function deciding when the go-live file is needed, used by both the gate and the listing command, a new worked example in the template, and the matching Stage 5 line.
- **What I kept:** None: the owner reviews this at the pull request.
- **What I changed or rejected, and why:** None: the owner reviews this at the pull request.
- **Where the AI was wrong, and how I noticed:** The previous round changed the Stage 5 line to match the gate, although the design outranks the code; the review ruled the other way, so the gate changed and the line went back. The template still carried the acceptance test's expected findings until the previous round's report named them.

### 24. README, framework updates and release preparation (2026-11-09)

- **Prompt (or summary of it):** Rewrite the README as a front page for a reader who is not an engineer, state the known limits openly, add a section on the skills this one works with, rename the planned-hook enforcement kind, and update the layout, changelog and decision log, test-first.
- **What the AI produced:** A test file with a helper that compares the plugins in the mapping with the README section (9 failures and 2 errors on the real files in the first commit, helper cases passing), then the README, the renamed kind in the index, one principle and its test, the changelog list under "Unreleased", the layout and commands in the instructions file, and the two edits to the decision log and the design.
- **What I kept:** None: the owner reviews this at the pull request.
- **What I changed or rejected, and why:** None: the owner reviews this at the pull request.
- **Where the AI was wrong, and how I noticed:** The first commit attempt was refused by the secret gate because no working Python was on the path in that shell; I fixed the path and did not bypass the gate. The README table could not carry backticks on any word that is not a plugin, because the test reads every backticked name in that section as a plugin; the test caught this when I drafted the section.

### 25. The scripts climb their own test ladder (2026-11-09)

- **Prompt (or summary of it):** Apply the five-rung test ladder to the skill's own scripts: feed the gate generated garbage, remove each of its rules on a throwaway copy and demand a red test, run the suite from a clean clone, and add macOS to the continuous integration matrix.
- **What the AI produced:** A seeded garbage test over 15 file types (one hang found, in the comment removal of the gate, and two crashes in the companion check, each fixed after a red commit); a script outside the repository that applied 179 mutations one at a time to a copy of the gate, with 46 survivors out of 178 at the first pass; 44 new tests that close them; 2 survivors explained as equivalent; a clean-clone run (824 tests, 1 skipped, check_docs exit 0); the results file; macOS in the matrix with decision D21 superseding D9.
- **What I kept:** None: the owner reviews this at the pull request.
- **What I changed or rejected, and why:** None: the owner reviews this at the pull request.
- **Where the AI was wrong, and how I noticed:** The first garbage test ran 500 documents per type with a fresh repository check each time and took ten minutes without finishing, so I profiled it and found the hang in the comment removal and the cost of repeated disk reads; the default count is now 100 with an environment variable for 500. My first mutation list was written from the rules and missed the git helpers, which hid five survivors until I added them; one mutation of the command entry point survived because my new test asserted only the exit code, which two different branches share. A commit message says "180 mutations" where the count is 179, because one entry had a search text that matched twice and was replaced; RESULTS.md has the right number.

### 26. Final review fix wave: the templates against their own gate (2026-11-09)

- **Prompt (or summary of it):** Fix every finding of the whole-branch review in one wave, test-first: the template marker that made filled-in templates fail their own gate, adoption opened by a hand-raised Cycle number, rung cells that accepted the gate's own records, the remaining smaller findings, and the wording items; add an end-to-end test that sets up Small and Full projects and walks them through all eight stages.
- **What the AI produced:** An end-to-end walk that replaces only the example lines of the real templates (it failed at stage 0 on both sizes before the fix), 59 test methods (55 new, 4 existing ones rewritten under the new rulings), almost all in four red commits, each followed by its fix: the marker judged outside comments and per stage, adoption anchored to the first commit that added `STAGES.md` (R26, D22), refused rung evidence, the Components section, archived files, build commits that change only the gate's records, merge commits, tighter container names, the re-check day (D23); then the wording fixes and D21's corrected reason.
- **What I kept:** None: the owner reviews this at the pull request.
- **What I changed or rejected, and why:** None: the owner reviews this at the pull request.
- **Where the AI was wrong, and how I noticed:** The earlier rounds tested each check with hand-made fixtures and never ran the real templates through the gate, so the marker inside every template's own comment went unnoticed until a reviewer filled one in; the walk now does what an owner does. Two existing tests had written the old adoption anchor into the suite as correct behaviour and had to be inverted under the new ruling. One edit script written through a shell here-document lost its backslashes, as the owner's rules warn; it stopped on its own match check and wrote nothing, and the edit was redone with the editing tool.

### 27. Renaming to Agentic Engineering Principles and adding the logo (2026-11-09)

- **Prompt (or summary of it):** Use the supplied logo and rename the project to Agentic Engineering Principles, everywhere.
- **What the AI produced:** It asked how far the rename should reach and where the logo file was, then wrote failing tests for the new plugin and marketplace name, the repository address, the README title and logo, and the absence of the old name in the current files; then the changes, D24 and a changelog line.
- **What I kept:** The rename everywhere, the logo at the top of the README, and the short skill name `agentic-principles`.
- **What I changed or rejected, and why:** None: the owner reviews this at the pull request.
- **Where the AI was wrong, and how I noticed:** Its first edit of CLAUDE.md added a note "renamed from" the old name, which the new test immediately flagged; the history moved to D24, where it belongs.

### 28. Installing the plugin and writing how to use it (2026-11-09)

- **Prompt (or summary of it):** Install the skill; then, since others need clearer instructions, add to the README how the skill is used from one session to the next.
- **What the AI produced:** It installed the plugin from the marketplace and checked that the installed copy finds its own files. It then wrote failing tests for a quick start, a daily-use section and a current install note, followed by the two README sections, D25 and a changelog line.
- **What I kept:** The quick start before the stage table, the table of sentences the owner can say, the table of record files, and the list of things the agent never writes for the owner.
- **What I changed or rejected, and why:** None: the owner reviews this at the pull request.
- **Where the AI was wrong, and how I noticed:** No new error in this step. The README it had written earlier explained the stages but not the daily routine; the owner noticed that the instructions were not clear enough for others, which prompted this step.

### 29. Releasing 0.2.0 (2026-11-09)

- **Prompt (or summary of it):** Merge the README pull request and release 0.2.0.
- **What the AI produced:** After the merge, it changed the changelog test to ask for a dated 0.2.0 section and an empty Unreleased list, watched it fail, then moved the Unreleased list under the 0.2.0 heading. The tag and the GitHub release follow once CI on `main` is green.
- **What I kept:** The release now, as the owner decided, with the open limits stated in the release notes.
- **What I changed or rejected, and why:** The plan put two checks before the release: a new session confirming the skill loads on its own, and an acceptance run on a past project. The owner chose to release first; both checks stay open and are named in the release notes.
- **Where the AI was wrong, and how I noticed:** No new error in this step.

### 30. Moving the ownership answers into a private companion repo (2026-11-10)

- **Prompt (or summary of it):** Keep the owner's explain-back and full-round answers out of the project repo: they belong in the project's private internal companion, the gate must read them there and must not pass silently when it cannot, with red then green tests.
- **What the AI produced:** A `Record:` line and an `Explain-back done` line in the project's `OWNERSHIP.md`, a new template `OWNERSHIP-RECORD.md` for the private record, `private_record`, `project_ownership_problems`, `full_round_problems` and `answers_in_repo_problems` in `check_gates.py`, a `--private-unavailable` flag used by the project CI template, `init_project.py` filling in the record path and creating the record template in an existing companion, and the matching stage files, skill rule and README section (D26). Tests were written first and failed (commit facc614) before the code.
- **What I kept:** The CI flag, which the owner chose over a CI that fails forever or a CI without the stage gate. Only the ownership answers move now, also the owner's choice.
- **What I changed or rejected, and why:** The AI first asked where the record path should come from; the owner answered with the larger goal, a private companion for every repository, so the path became a fixed rule (`../<project>-internal/...`) and the companion is now made by repo-kickoff for every project.
- **Where the AI was wrong, and how I noticed:** One new test expected an `Override:` line to silence the explain-back, but the test helper puts that line under the full round. Noticed by reading the helper before writing the code; the test now writes the record with the explain-back helper and also checks that the gap fires without the override. The first full run then found two more: the new record reader caught only `OSError`, so a `Record:` path with a NUL byte crashed the gate with `ValueError` (found by the robustness fuzz, seed 20261109; now "could not be read", with its own test); and the 0.2.0 changelog test still demanded an empty Unreleased list, a release-time check, now narrowed to the lasting rule. The private-name scan also failed on the logo, which arrived earlier with the rename: three random bytes of the JPEG spelled a forbidden three-letter name. The scan now matches names in binary files only as whole words in readable text; its new test failed against the old scanner (exit 1) before the fix.

### 31. Grilling on every project, at Intake and Design (2026-11-10)

- **Prompt (or summary of it):** Grill-me must run in every project, Small or Full, at Stage 0 and Stage 1; implement the gate. Save the plan for installing the companion skills for later.
- **What the AI produced:** Failing tests first (commit ddf5600), then `templates/GRILLING.md`, `grilling_problems` and the Stage 0 and 1 evidence rule in `check_gates.py`, the companion row moved to Stages 0 and 1, the stage files, the skill's overlap table, the README and the design document (D27). The install plan went to its own document and pull request.
- **What I kept:** The owner's ruling as given: the same minimum of 3 answered challenges on Small and Full, at both stages.
- **What I changed or rejected, and why:** The AI had proposed grilling at Stage 1 for every project and at Stage 0 only for the requirements; the owner made both stages mandatory for every project. The bundle plugin and install commands were deferred by the owner and saved as a plan.
- **Where the AI was wrong, and how I noticed:** The test helper that fills a template line demanded exactly one empty line, but the grilling template has two (one per section); the walk test failed on it and the helper now fills a chosen one. Adding the new section names to the robustness test's vocabulary changed its random documents and exposed an older crash: a NUL in a commit value from `STAGES.md` reached `git` and raised. It is fixed in the shared git helper, with its own test.
