# Decisions

Decision log for Agentic Coding Principles. Each decision has seven fields; none is left blank. Where a field does not apply, it says `None:` and gives the reason.

### D1. Standalone public repository

- **Context:** The framework (rules, stage gates, templates, a documentation gate) needs a home that anyone can clone, read and reuse.
- **Options considered:** (a) put it inside a private repository of the owner's own rules; (b) extend the owner's existing public repo-setup skill; (c) create a new standalone public repository.
- **Chosen:** (c) a new standalone public repository.
- **Why:** That private repository holds machine-specific paths and private project rules and cannot be published without a long clean-up. The framework is broader than repo setup. A standalone repository can become a skill later.
- **Rejected:** (a) it is private and bound to one machine; (b) it is the wrong scope, because the framework covers a whole project life cycle and not only repository setup.
- **Cost / trade-off:** The rule logic exists in two places for now (see D4).
- **What would make you change it:** If a skill version replaces this repository, this repository becomes its source or is retired.

### D2. Python standard library and unittest only

- **Context:** The documentation checker and its tests must run on any machine that has Python, with nothing to install first.
- **Options considered:** pytest; the standard library `unittest`.
- **Chosen:** `unittest` and the standard library only.
- **Why:** Anyone can clone and run the checks with no install step. It matches the Python 3.11+ floor.
- **Rejected:** pytest, because it adds a dependency for a small suite.
- **Cost / trade-off:** Tests are more verbose than they would be with pytest.
- **What would make you change it:** If the suite grows past what `unittest` keeps readable.

### D3. Incidents are told as lessons from projects built so far

- **Context:** Every rule is justified by an incident, but the source projects are private and must not be revealed.
- **Options considered:** name the projects; describe them anonymously; describe only the lesson.
- **Chosen:** describe only the lesson.
- **Why:** The owner decided this on 2026-11-06: public files must not reveal private projects, companies or their domain.
- **Rejected:** naming them (privacy, and no permission); anonymous descriptions (the domain itself identifies the project).
- **Cost / trade-off:** Incidents read less concretely.
- **What would make you change it:** If a project owner agrees to be named.

### D4. Rule logic duplicated with a private hook for now

- **Context:** The owner already enforces the same documentation format through their own tool-call hook, which is not public, while this repository ships its own public checker.
- **Options considered:** the hook imports the public checker; keep two copies.
- **Chosen:** two copies in v0.1.
- **Why:** Making a private tool depend on a public repository's file layout adds a coupling risk with no user benefit yet.
- **Rejected:** importing the public checker into the hook now.
- **Cost / trade-off:** The two copies can drift apart. This is mitigated because both are tested against the same field lists.
- **What would make you change it:** When v0.2 packages the checker, the hook should import it.

### D5. CLI exit codes 0, 1, 2 and plain-text output

- **Context:** The documentation gate runs in a terminal, in CI and, later, from a hook, so callers need a result they can branch on and a message a person can act on.
- **Options considered:** (a) exit 0 for pass, 1 for problems, 2 for usage errors, with one `FILE:LINE: message` line per problem; (b) the same codes with JSON output; (c) exit 1 for every failure.
- **Chosen:** (a) three exit codes and `FILE:LINE: message` lines.
- **Why:** The `FILE:LINE: message` form is the common compiler format, which editors and CI log viewers already turn into clickable links. Separating exit 1 (the documents are wrong) from exit 2 (the command was misused) stops a typing mistake from looking like a documentation failure.
- **Rejected:** (b) JSON output, because nothing consumes it yet and it is harder to read in a terminal; (c) a single failure code, because it hides the difference between a bad document and a bad command.
- **Cost / trade-off:** A program that wants structured results must parse text, or import the functions, which return `Problem` tuples.
- **What would make you change it:** If a tool needs machine-readable output, add a `--json` option while keeping the default text format.

### D6. Fenced code blocks are ignored by blanking their lines

- **Context:** Templates and principles show example entries inside fenced code blocks. Those examples must not count as real entries, fields or table rows, and a reported line number must still point at the right line of the original file.
- **Options considered:** (a) blank each line of a fenced block and keep the line count; (b) remove the blocks from the text before parsing; (c) parse the Markdown structure with a library.
- **Chosen:** (a) blanking the lines.
- **Why:** The text keeps exactly the same number of lines, so every problem carries the true line number of the original file. It needs only a few lines of standard-library code.
- **Rejected:** (b) removing the blocks, because every line after a block would shift and the reported numbers would be wrong; (c) a Markdown library, because it breaks the standard-library-only rule (D2).
- **Cost / trade-off:** Only fences written with three backticks are recognised; a fence written with tildes is read as ordinary text.
- **What would make you change it:** If a document in this repository starts using tilde fences, the fence pattern must be extended.

### D7. Templates carry one worked example and guidance in HTML comments

- **Context:** The repository ships templates for the decision log, the AI log, the requirements table and five other documents. A new user must see what a good entry looks like, and the documentation gate must accept the templates as shipped.
- **Options considered:** (a) blank skeletons with empty fields; (b) one worked example entry plus short guidance in HTML comments; (c) guidance in a separate document only.
- **Chosen:** (b) a worked example and HTML-comment guidance in each template.
- **Why:** A filled example teaches the expected depth faster than a description. HTML comments do not render, so the guidance disappears from the finished document. A test (`tests/test_templates.py`) runs the three gated templates through the gate: 0 problems.
- **Rejected:** (a) blank skeletons, because they teach nothing and fail the gate (empty fields); (c) a separate guide, because people copy the template and never open the guide.
- **Cost / trade-off:** The example must be replaced, and a user who forgets keeps a neutral example entry in their log. The gate cannot tell an example from a real entry. Format examples inside comments must not use heading or field syntax, because the gate does not skip comments.
- **What would make you change it:** If users keep the example entries in real projects, mark the example with a visible tag and make the gate warn about it.

### D8. Principles in a fixed four-field format, each backed by a real incident

- **Context:** The principles must be readable by someone who has never seen the source projects, checkable by a test, and honest about why each rule exists and how it is enforced.
- **Options considered:** (a) free prose per stage; (b) a fixed format per principle: a heading `P<stage>.<n> <title>` and four fields (Rule, Why (incident), How to check, Enforced by), "Enforced by" limited to template, check_docs, CI, human gate and "contract hook (planned, v0.2)", and a principle only where a real incident exists; (c) the fixed format with a free-text "Enforced by"; (d) the fixed format, also keeping rules that have only a rationale.
- **Chosen:** (b), checked by `tests/test_principles.py`: 20 principles (stages 0 to 7: 3, 7, 0, 5, 1, 2, 1, 1). The test refuses a principle whose incident is missing and a stage without principles unless it says it awaits one.
- **Why:** A fixed format lets a test check every principle (four fields, contiguous ids, every id in the index). A closed list of kinds stops vague answers such as "process", and it names only mechanisms that exist publicly in this repository; the private hook is marked as planned. Requiring an incident keeps the promise that every rule comes from a lesson, not from opinion.
- **Rejected:** (a) free prose, because a rule hidden in a paragraph cannot be checked and readers skim past it; (c) free-text enforcement, because the source notes used "process" and "review", which do not say who or what refuses a breach; (d) rationale-only rules, because they are the opinions the framework exists to replace; the first draft had 16 of them out of 40.
- **Cost / trade-off:** Useful rules without an incident are left out for now (listed under "Not done (and why)"), and stage 2 has no principle yet. Most principles rest on a human gate, which is the weakest kind.
- **What would make you change it:** A real incident for a candidate rule brings it in; a rule that needs an enforcement none of the kinds describes gets a new kind with a definition and a test instead of stretching an existing one.

### D9. CI matrix of two Python versions and two operating systems, read-only permissions

- **Context:** The tests and the documentation gate must run on every push and pull request, on the systems the users have, and the workflow must not hold more rights than it needs.
- **Options considered:** (a) one job on Ubuntu with one Python version; (b) a matrix of Python 3.11 and 3.13 on ubuntu-latest and windows-latest, with `permissions: contents: read` and no secrets; (c) a larger matrix with macOS and every Python version from 3.11 to 3.13.
- **Chosen:** (b), four jobs, each running `python -m unittest -v` and then `python checks/check_docs.py .`.
- **Why:** 3.11 is the oldest supported version (see Assumptions) and 3.13 the newest in use; Windows is a common developer system and the one where line endings and path separators differ. The workflow only reads the code, so a read-only token is enough, and no secret is configured.
- **Rejected:** (a) a single job, because it would miss Windows line-ending and path problems; (c) macOS and the middle version, because they add jobs without a failure mode that the two chosen systems do not already cover.
- **Cost / trade-off:** Four jobs run per push, and a problem specific to macOS or to Python 3.12 would not be caught. One test (the private-name scan) is skipped in CI because it needs a local environment variable.
- **What would make you change it:** A user report of a failure on macOS or on another Python version adds that cell to the matrix.

### D10. No argument means the current directory

- **Context:** The design (section 8) says the gate takes `[REPO_DIR]`, defaulting to the current directory. The first implementation returned exit 2 when no argument was given, and a test locked that in.
- **Options considered:** (a) keep exit 2 for no argument and require a folder; (b) default to the current directory; exit 2 only for more than one argument or a path that is not a directory.
- **Chosen:** (b).
- **Why:** The design is binding, and a new project runs the gate from its root, so `python checks/check_docs.py` with no argument is the shortest correct call and matches how CI and the README use it.
- **Rejected:** (a) exit 2 for no argument, because it contradicted the design and forced users to type a `.` that carries no information.
- **Cost / trade-off:** Running the gate in the wrong directory now reports "file is missing" problems (exit 1) instead of a usage error.
- **What would make you change it:** A report that people run the gate from the wrong folder and are confused by the output would bring back an explicit argument or a clearer message for a folder that has neither log.

### D11. Backtick fences follow the renderer's rules, and an unclosed fence is a problem

- **Context:** The gate blanks fenced code so that examples are not checked. It toggled on any line starting with three backticks, so a longer fence showing a shorter one exposed its example, inline triple backticks hid the rest of the file, and an unclosed fence silently switched off every check after it.
- **Options considered:** (a) keep the toggle and only report an odd number of fence lines; (b) apply the renderer's rules for backtick fences (a closing line has at least as many backticks and no text after them, an opening line has no further backtick) and report an unclosed fence at its opening line; (c) use a full Markdown parser.
- **Chosen:** (b).
- **Why:** The gate must blank exactly what a reader sees as code. An unclosed fence keeps blanking to the end of the file, as it renders, and the problem at its opening line says why later entries were not checked.
- **Rejected:** (a), because a longer fence would still expose its example and an even count can hide two wrong lines; (c), because the design allows the standard library only.
- **Cost / trade-off:** Tilde fences (`~~~`) are still not treated as fences, so an example inside one is checked like normal text. That failure is loud, not silent.
- **What would make you change it:** A real log that uses tilde fences for examples adds them to the same rule.

### D12. The public pre-commit hook is its own enforcement kind

- **Context:** P5.2 named "contract hook (planned, v0.2)" as its enforcer, although a pre-commit secret gate is public in `.githooks/` and refuses both cases the principle describes.
- **Options considered:** (a) keep the planned hook until v0.2; (b) add a kind "pre-commit hook", defined in the index and accepted by the test; (c) count the hook as "CI" or "human gate".
- **Chosen:** (b), with a test that every kind is defined in the index and a new test that a file named `*.env` is refused.
- **Why:** D8 says a mechanism that no kind describes gets a new kind with a definition and a test. The hook exists and is tested, so calling it planned understated what the repository enforces.
- **Rejected:** (a), because it describes a real mechanism as future work; (c), because CI runs after the push and a human gate is a person, while the hook refuses the commit itself.
- **Cost / trade-off:** The hook works only after each clone enables it with `git config core.hooksPath .githooks`, so the human gate stays named beside it.
- **What would make you change it:** A portable tool-call hook in v0.2 may replace this kind for rules that a commit cannot see.

### D13. The ungated templates are checked by tests, not by the gate

- **Context:** The gate reads three kinds of document. The other five templates were tested only for length and a comment, so a deleted section would have gone unnoticed.
- **Options considered:** (a) test the shipped templates for the parts their guidance promises; (b) extend `check_docs.py` to require those documents in every project.
- **Chosen:** (a).
- **Why:** The defect is a broken template in this repository, and a test finds it. Build ledgers, results and handovers are not required in every project, and a handover changes shape as work goes on.
- **Rejected:** (b), because it would fail projects for leaving out documents that the framework does not require.
- **Cost / trade-off:** A project's own copies of these five documents can drift from the template without any check.
- **What would make you change it:** A real project losing work because one of these documents lacked a section would justify a gate rule for that document.

### D14. A principle may state a real event without a measured effect

- **Context:** The final review of v0.1 asked for a measured effect on P3.4, P1.3 and P1.7. Their events are on record, but no number is, and the owner no longer remembers one.
- **Options considered:** (a) keep the three principles as they stand and stop tracking the request; (b) remove them and list them as candidates; (c) keep the request open until a number turns up.
- **Chosen:** (a), by the owner.
- **Why:** The anti-goal forbids rules without an incident, and these three have one. A number would add weight, but it cannot be recovered and must not be invented.
- **Rejected:** (b), because it would drop rules backed by real events, including P3.4, the idea this repository rests on; (c), because nobody can ever close that item.
- **Cost / trade-off:** These three principles carry less evidence than the others, so a reader takes the event on trust.
- **What would make you change it:** A recovered number goes into the principle.

### D15. The skill is a conductor over installed skills

- **Context:** The repository's knowledge is passive and assumes the reader already knows when something is wrong. The owner is not a software engineer by training and already has capable third-party skills installed, none of which decides what runs when or stops the work.
- **Options considered:** (a) leave the repository as a reference; (b) a skill that writes its own guidance for every technique; (c) a conductor that calls installed skills at each stage and adds gates, evidence and plain-language guidance, with a fallback for a missing skill.
- **Chosen:** (c), described in `docs/design-skill.md`.
- **Why:** The owner asked for the skill to work hand in hand with the installed skills. The techniques already exist and are maintained by others; what is missing is sequence, evidence and refusal to move on without proof.
- **Rejected:** (a), because it needs the engineering judgement the owner is still building; (b), because it would duplicate others' work and drift from it.
- **Cost / trade-off:** The skill depends on names it does not control, so a renamed skill breaks a mapping until `companions.json` is updated. Its instructions can be ignored by an agent, so approvals rest on trust until a tool-call hook exists.
- **What would make you change it:** A companion that disappears or is repeatedly misused would be replaced by this repository's own guidance for that step.

### D16. Two rule layers: incident-backed principles and a cited checklist

- **Context:** The design's anti-goal forbids rules without an incident, but the owner needs the skill to bring up practices never personally met, which by definition have no incident.
- **Options considered:** (a) keep incidents as the only source and accept the blind spots; (b) drop the incident requirement; (c) keep principles incident-backed and add a separate checklist in which every item cites a recognised source.
- **Chosen:** (c), by the owner. The anti-goal now applies to principles only.
- **Why:** It covers what the owner does not know without weakening the promise behind the principles, and a reader can always tell which kind of rule is in front of them.
- **Rejected:** (a), because the rules the owner most needs are the ones not yet learned the hard way; (b), because it invites invented best practices.
- **Cost / trade-off:** Two lists to maintain, and each checklist source has to be read and cited when the item is written.
- **What would make you change it:** A checklist item later backed by a real incident moves to the principles.

### D17. Evidence is typed and checked per stage

- **Context:** A gate that accepts any text as evidence passes a stage whenever someone writes a plausible word. Review of the design found that setup files and empty files were enough to pass most gates.
- **Options considered:** (a) free-text evidence with a non-empty check; (b) one shared rule for every stage ("a tracked file exists"); (c) typed evidence, `file:<path>` or `commit:<hash>`, with a table of what each stage and size must name, and a content rule for the files that matter.
- **Chosen:** (c). The table is the data structure `REQUIRED` in `check_gates.py`, and each content rule runs only at the stage that needs its file.
- **Why:** A file is checked as tracked, inside the project, non-empty, not a folder and free of the template marker; a commit is checked as a real hash on the current history and, for Build, as made after `STAGES.md` first appeared. Each rule was seen failing on a real temporary git repository before it was written.
- **Rejected:** (a), because "done" would be a word and not a fact; (b), because Build needs a commit and Retro needs a filled section, which one rule cannot express.
- **Cost / trade-off:** The evidence format is strict, so a typo costs a re-run. A commit proves a commit exists, not that the owner reviewed it, because the owner and the agent share one git identity (design section 3). "One review row per task" on Full size is enforced only as at least one filled review row, because the gate cannot know the task count.
- **What would make you change it:** A stage whose real evidence is neither a file nor a commit, such as a running service, would need a third evidence type.

### D18. Architecture checks bind at the stage that needs the document

- **Context:** `ARCHITECTURE.md` has a file map, a dependency table and a test table, and `ATTACKS.md` has the attack list. A file map can only agree with `git ls-files` once the files exist, but the evidence for stage 4 already names `ARCHITECTURE.md`. Checking everything as soon as the file exists would turn continuous integration red during the build.
- **Options considered:** (a) check every section whenever the file exists; (b) check every section when stage 4 is passed; (c) bind each check to the stage that needs it: the attack list at stage 0, the test table at stage 4, the file map and dependency table at stage 5.
- **Chosen:** (c), implemented in `architecture_problems`, called from `check_project`. A missing `ARCHITECTURE.md` is reported only when stage 5 is passed, because stage 4 already reports it as missing evidence.
- **Why:** The attack list is written at intake, the test table is filled while verifying, and the file map and dependencies are final only at shipping. Each section is judged exactly when its stage is marked passed, so a build in progress stays green and a closed stage cannot keep a stale document. A section may carry `Override: O<n>`; it counts only while that override is open and names the same stage.
- **Rejected:** (a), because every commit during the build would fail on a half-written map; (b), because the map would then be judged a stage before the files are final and a later file would slip past, or be flagged twice.
- **Cost / trade-off:** A wrong file map is not reported until stage 5, so an owner who keeps the document current is not warned earlier. Manifests the script cannot read (Poetry, `Pipfile`, `go.mod` and others) force a manual line, so those projects get a weaker dependency check; a manifest the script cannot read is reported and never skipped. Duplicate problems from two checks are reported once.
- **What would make you change it:** A real project where a stale map at stage 4 caused a wrong decision would justify checking the map from stage 4.

### D19. Six primary sources for the engineering checklist, each read before its item

- **Context:** D16 allows checklist items without an incident as long as each cites a recognised source. Without a fixed set of sources, items would cite blog posts or nothing more than the agent's memory, and the owner cannot judge which is which.
- **Options considered:** (a) any source the writer finds convincing; (b) one source only, such as the OWASP Top 10; (c) a fixed set of six primary documents, each covering a different part: OWASP Top 10:2025, OWASP ASVS 5.0.0, OWASP Top 10 for LLM Applications 2025, NIST SP 800-218 (SSDF 1.1), the Google SRE book and the Twelve-Factor App, with every item citing the exact page it was taken from.
- **Chosen:** (c). The 40 items in `checklist/` cite those pages, and `build_checklist.py` refuses an item whose source has no `https://` address or no name.
- **Why:** Together the six cover security, dependencies, operations, data and AI systems, they are maintained by recognised bodies, and each page was fetched and read while its item was written, so a reader can open the same page and check the claim.
- **Rejected:** (a), because a source nobody vetted gives the owner no way to tell a recognised practice from an opinion; (b), because the OWASP Top 10 says nothing about retries, backups, rollback or model cost.
- **Cost / trade-off:** Contract testing and mutation testing, which the design names, appear in none of the six, so they have no item yet. Sources change edition (the OWASP Top 10 moved from 2021 to 2025 during this work), so cited pages need re-reading when a new edition appears. The builder checks that an address is present, not that the page says what the item claims; that rests on the reviewer opening the page.
- **What would make you change it:** A needed practice that none of the six describes, such as contract testing, would justify adding a seventh primary source with its own decision entry.

### D20. A Cycle line marks where a cycle of work starts

- **Context:** The Stage 3 rule asks for a commit made after `STAGES.md` first appeared, and the Adopted-at rules read the first commit of the file. A second cycle archives the old `STAGES.md` and writes a new one. When the owner does that in one commit, git records a modification of the same path, so "first commit of the file" still named the first cycle and its commits kept satisfying the rule. The first version only printed an instruction to commit in two steps.
- **Options considered:** (a) print the two-commit instruction and rely on the owner; (b) look for the newest commit that added the file; (c) a `Cycle: N` line in `STAGES.md`, where the start of the cycle is the oldest commit whose committed `STAGES.md` holds the current number; (d) compare content to detect a restart.
- **Chosen:** (c). `init` writes `Cycle: 1`, `--new-cycle` archives the file and writes the next number, and `check_gates.py` reports a missing or malformed line at its line.
- **Why:** The rule now rests on a value that is in the file and in history, so it holds whether the new cycle is one commit or two, and a missing line is a visible problem instead of a quiet gap.
- **Rejected:** (a), because nothing enforced it and a single commit weakened the Stage 3 rule without any message; (b), because a one-commit restart is a modification, not an add; (d), because content such as an all-open table also appears legitimately in the middle of a cycle.
- **Cost / trade-off:** Every `STAGES.md` needs one more line, and existing files without it now fail until `Cycle: 1` is added. The owner can still reuse or lower a number by hand: reusing a number makes the gate measure from the older start, which is the stricter reading, but nothing stops it.
- **What would make you change it:** A project where several cycles run at once on different branches, because one number per file could no longer say which start applies.

## Assumptions

- Users run Python 3.11 or newer.
- An AI agent writes most files and a human approves them.
- "Flawless documentation" is the owner's standard: every field is filled.

## Not done (and why)

- Tool-call guard hook: planned for v0.2; the owner already has one (not public).
- Skill packaging: later, by the owner's choice.
- Tempo modes for short events: deferred, not needed for v0.1.
- Installer: copying the templates is enough for v0.1.
- Checklist items for contract testing and mutation testing: none of the six chosen sources describes them (D19).
- Write a requirements matrix on day one: candidate principle awaiting a real incident (the requirement check that came late still passed).
- Keep a glossary of domain terms and a diagram of how the parts talk: candidate principle awaiting a real incident.
- Compute dates and rules in deterministic code, not in a language model: candidate principle awaiting a real incident (only a benefit is recorded).
- Give every task the same definition of done: candidate principle awaiting a real incident.
- Run the full suite after every merge and settle every "cannot verify" by reading the code: candidate principle awaiting a real incident.
- Give parallel working copies separate container project names: candidate principle awaiting a real incident.
- Have a human check every evaluation label and report raw counts: candidate principle awaiting a real incident.
- Keep raw sensitive data out of test fixtures: candidate principle awaiting a real incident.
- Build a walking skeleton with the real integrations in the first days: candidate principle awaiting a real incident (the late end-to-end run is recorded, but not what it found).
- Record the intent before every write to an external service, with an idempotency key: candidate principle awaiting a real incident (only a result is recorded).
- Approve every paid call first and record its cost: candidate principle awaiting a real incident.
- Record every live run in RESULTS.md: candidate principle awaiting a real incident.
- Start a fresh clone with the documented commands only: candidate principle awaiting a real incident.
- Keep keys out of chat, logs and git: candidate principle awaiting a real incident.
- Merge with merge commits and never squash: candidate principle awaiting a real incident.
- Describe every pull request with goal, choices, measurements and how to check: candidate principle awaiting a real incident.
- Log AI usage while working, five fields per entry: candidate principle awaiting a real incident.
- End with a list of defects caught by review and a reflection: candidate principle awaiting a real incident.
