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

## Assumptions

- Users run Python 3.11 or newer.
- An AI agent writes most files and a human approves them.
- "Flawless documentation" is the owner's standard: every field is filled.

## Not done (and why)

- Tool-call guard hook: planned for v0.2; the owner already has one (not public).
- Skill packaging: later, by the owner's choice.
- Tempo modes for short events: deferred, not needed for v0.1.
- Installer: copying the templates is enough for v0.1.
