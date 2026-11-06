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
- **Why:** 3.11 is the oldest supported version (see Assumptions) and 3.13 the newest in use; Windows is the owner's own system and the one where line endings and path separators differ. The workflow only reads the code, so a read-only token is enough, and no secret is configured.
- **Rejected:** (a) a single job, because it would miss Windows line-ending and path problems; (c) macOS and the middle version, because they add jobs without a failure mode that the two chosen systems do not already cover.
- **Cost / trade-off:** Four jobs run per push, and a problem specific to macOS or to Python 3.12 would not be caught. One test (the private-name scan) is skipped in CI because it needs a local environment variable.
- **What would make you change it:** A user report of a failure on macOS or on another Python version adds that cell to the matrix.

## Assumptions

- Users run Python 3.11 or newer.
- An AI agent writes most files and a human approves them.
- "Flawless documentation" is the owner's standard: every field is filled.

## Not done (and why)

- Tool-call guard hook: planned for v0.2; the owner already has one (not public).
- Skill packaging: later, by the owner's choice.
- Tempo modes for short events: deferred, not needed for v0.1.
- Installer: copying the templates is enough for v0.1.
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
