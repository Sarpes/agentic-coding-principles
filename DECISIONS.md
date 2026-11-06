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

## Assumptions

- Users run Python 3.11 or newer.
- An AI agent writes most files and a human approves them.
- "Flawless documentation" is the owner's standard: every field is filled.

## Not done (and why)

- Tool-call guard hook: planned for v0.2; the owner already has one (not public).
- Skill packaging: later, by the owner's choice.
- Tempo modes for short events: deferred, not needed for v0.1.
- Installer: copying the templates is enough for v0.1.
