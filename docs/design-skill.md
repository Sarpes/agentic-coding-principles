# Design: the agentic-principles skill

Status: approved 2026-11-09. Decision owner: the owner.

Terms: a **skill** is a packaged set of instructions an AI coding agent loads for a kind of task. A **companion** is another installed skill this one calls. A **gate** is the evidence needed before work moves to the next stage. An **override** is the owner's recorded choice to move on without that evidence.

## 1. Intent and why

The owner builds software with AI coding agents and is not a software engineer by training. The work must go beyond "vibe coding" (accepting whatever the agent produces because it seems to run) and follow core software engineering practice.

The repository already holds the knowledge: eight stages with gates, incident-backed principles, templates and a documentation gate. All of it is passive, because it assumes the reader already knows when something is wrong. The skill makes it active. It guides the owner through a project, calls the right installed skill at each stage, refuses to call a stage done without evidence, and brings up practices the owner has never heard of.

A past project run this way produced the pattern to repeat: decisions settled before code, one writer and a separate reviewer per task, 61 defects caught before submission, reviewers running probe inputs, a gate with a measured floor, and live runs that deliberately broke things. That result depended on an external brief naming the attacks and on graders who would run them. Ordinary projects have neither, so the skill must supply both roles.

Who it serves: first the owner; second, anyone building with an agent who lacks engineering training.

Success, in the owner's words: every piece of work is "tested to its limits", and a month later the owner can explain, without the agent, the entire architecture, what each file does, how the files connect, the tech stack, how each part was tested, how complex problems were approached, and the third-party dependencies.

## 2. Goals, non-goals, anti-goals

Goals:
- Conduct a project through the eight stages, at a chosen size and with a chosen build method.
- Work hand in hand with the third-party skills already installed (section 5).
- Require evidence per stage that a person without engineering training can check.
- Test each part up a defined ladder (section 6).
- Keep one living document from which the owner can explain the project (section 7).
- Bring up practices the owner does not know, at the right stage, in plain words (section 8).
- Run a go-live review that suggests validations and names likely problems before anything goes live (section 9).
- Allow any gate to be overridden, and keep every override so it can be revisited at any time (section 10).

Non-goals (this version): an installer beyond the plugin format the owner already uses; a tool-call hook that blocks the agent; support for agents other than Claude Code.

Anti-goals (a failure even if it works):
- The owner passes every gate and still cannot explain the project.
- A rule appears with neither an incident nor a cited source.
- The process outweighs the project.
- A check says "done" and cannot actually fail.
- The skill rewrites or copies what a companion already does well.

## 3. Constraints

- Python 3.11+, standard library only, `unittest`; runs on Windows, macOS and Linux.
- Public repository: no project, company, client or domain named or described; no machine-specific paths. Incidents read as lessons from projects built so far.
- Every rule, gate and check has a test that makes it fire (repository rule).
- A skill is only instructions, and an agent can ignore them. Anything that must hold is therefore a script with a test. Everything else is a question put to the owner.
- Decisions and the AI log are written in the same branch as the change.
- **Known limit, stated openly in the skill and the README.** The scripts verify that evidence exists: a named file is present, a named commit is real, a table row is filled. They cannot tell whether the owner really approved something or wrote a commit, because the owner and the agent share one git identity. Approvals rest on trust until a tool-call hook exists.

## 4. How a project runs

At the start the owner picks, and the skill records in `STAGES.md`:

- **Size.** The skill recommends one from what it reads about the project; the owner decides.
  - **Small:** one script or module, no live users, no personal data, no paid calls.
  - **Full:** everything else.
- **Build method.** The owner chooses by complexity: **normal** (the agent works through the plan in one session) or **sub-agent** (one writer and a separate reviewer per task, at most 5 fix rounds). The choice is logged as a decision. Normal mode still keeps one independent review at the end of the branch.

| Stage | What the skill makes happen | Evidence for the gate | Small | Full |
|---|---|---|---|---|
| 0 Intake | Owner states acceptance criteria and an **attack list** (how could this be broken or misused?); facts carry their source | `REQUIREMENTS.md`, attack list | one paragraph each | full table |
| 1 Design | Questions before code; goals, non-goals, anti-goals; data and threats classified | approved design, decisions with rejected options | a short note in `DECISIONS.md` | written design |
| 2 Plan | Tasks with a definition of done; method recorded; interfaces between tasks checked | plan file | a task list | full plan |
| 3 Build | Failing test first; independent review; suite run after every merge | red and green commits, review result | one final review | per-task review |
| 4 Verify | The test ladder; real end-to-end run done early, not only at the end | ladder table in `ARCHITECTURE.md`, `RESULTS.md` | rungs 1-2 | all rungs |
| 5 Ship | Go-live review; documents checked against the code; secrets and dependencies audited; pull request with goal, choices, measurements, how to check | `GO-LIVE.md` | applicable rows | all rows |
| 6 Own | Owner explains the project and changes a module by hand | answers in `OWNERSHIP.md` | 3 questions | full round |
| 7 Retro | Every "where the AI was wrong" entry becomes a rule, a template change or a recorded "won't fix" | retro section of the AI log | short | full |

Approvals state their scope: approving one call, merge or batch approves that and nothing further. Paid calls, merges, pushes and product decisions stay with the owner. The agent may make implementation rulings only with a stated cost if wrong, and deferred findings are sorted MUST, SHOULD or LEAVE, never dropped.

At each stage opening the skill says in plain words what the stage is for, what evidence will close it, and lists open overrides.

**Adopting an existing project.** The skill can start on a project that already exists, at whatever stage it has reached. Earlier stages are marked `adopted`, which `check_gates.py` accepts and which reads as "not done under this skill", never as passed. Adoption is optional for previous projects, with one exception: the past project the owner has chosen to understand from A to Z must be adopted, including a full Stage 6.

## 5. Working with installed skills

This is a core requirement: the skill is a conductor. It decides which companion runs when, and adds gates, evidence and plain-language guidance around them. It does not restate their instructions and never copies their text.

**Rules**
1. Companions are always called by full name (`plugin:skill`), because several installed skills share a short name such as `code-review` or `tdd`.
2. Order of authority: the owner, then the project's own instructions, then this skill, then the companion.
3. This skill may add to a companion's bar but never lowers it. An approval or gate a companion requires still holds.
4. At each stage the agent compares the table below with the skills actually listed in its session. A missing companion is said out loud, the fallback is used, and the fact goes into that stage's evidence. A missing companion never silently skips a step.
5. The mapping lives in one data file, `companions.json`, so a renamed or new skill is a one-line change.

**Mapping**

| Stage | Capability | Primary | Also / alternate | Fallback if none is installed |
|---|---|---|---|---|
| 0 | Starting the repository | `repo-kickoff` | | the repository's templates |
| 0 | Researching facts from primary sources | `mattpocock-skills:research` | `anthropic-skills:deep-research` | agent reads the provider's own documents |
| 1 | Finding out what is wanted | `superpowers:brainstorming` | | question rounds from `principles/01-design.md` |
| 1 | Stress-testing a design (Full) | `mattpocock-skills:grilling` | | a written list of challenges |
| 1 | Terms and glossary | `mattpocock-skills:domain-modeling` | | `templates/GLOSSARY.md` |
| 1 | Module boundaries | `mattpocock-skills:codebase-design` | | owner-readable note in the design |
| 1 | Cheap throwaway experiment | `mattpocock-skills:prototype` | | a spike outside the repository |
| 1-3 | Agent behaviour: assumptions, simplicity, surgical changes | `andrej-karpathy-skills:karpathy-guidelines` | | the four habits stated in the stage file |
| 2 | Writing the plan | `superpowers:writing-plans` | | `docs/plans` format of this repository |
| 3 | Building, sub-agent method | `superpowers:subagent-driven-development` | `superpowers:dispatching-parallel-agents`, `superpowers:using-git-worktrees` | writer and reviewer in separate sessions |
| 3 | Building, normal method | `superpowers:executing-plans` | | work through the plan in one session |
| 3 | Test-first loop | `superpowers:test-driven-development` | `mattpocock-skills:tdd` for where tests go and test anti-patterns | failing test, then code |
| 3-4 | Hard bugs | `mattpocock-skills:diagnosing-bugs` | `superpowers:systematic-debugging` | build a repeatable failing check first |
| 3 | Answering review findings | `superpowers:receiving-code-review` | | check each finding before changing code |
| 4 | Whole-input testing | `property-based-testing:property-based-testing` | | hand-picked boundary and hostile inputs |
| 4 | Proving tests catch breakage | `mutation-testing:mutation-testing` | | break each key rule on a throwaway copy and confirm a test fails |
| 4 | Silent failures, test gaps | `pr-review-toolkit:silent-failure-hunter` | `pr-review-toolkit:pr-test-analyzer` | reviewer checklist |
| 4 | Evaluating AI output (projects with an LLM) | `deepeval:deepeval` | | labelled examples checked by a person, raw counts reported |
| 4 | Running the real thing | `run` | `example-skills:webapp-testing` for browser apps | documented commands from a clean clone |
| 4-5 | Claims need evidence | `superpowers:verification-before-completion` | | a command and its output for every claim |
| 5 | Branch review against spec and standards | `mattpocock-skills:code-review` | `superpowers:requesting-code-review` | a separate reviewer session |
| 5 | Security review | `security-review` | `differential-review:differential-review` | section 8 checklist, security items |
| 5 | Insecure default settings | `/insecure-defaults:audit` command | | section 8 checklist, configuration items |
| 5 | Documents checked against the code | `spec-to-code-compliance:spec-to-code-compliance` | | `check_gates.py` plus a reviewer reading each claim |
| 5 | Dependencies | `supply-chain-risk-auditor:supply-chain-risk-auditor` | | the owner reads the dependency table |
| 5 | Repository audit | `repo-kickoff` audit mode | | `check_docs.py` and `check_gates.py` only |
| 5 | Pull request and finish | `mattpocock-skills:pr` | `superpowers:finishing-a-development-branch` | `templates/PULL_REQUEST_TEMPLATE.md` |
| 6 | Reading an existing codebase function by function (adoption) | `audit-context-building:audit-context-building` | | the agent walks the file map with the owner |
| 7 | Updating agent instructions | `claude-md-management:revise-claude-md` | | edit the project's instructions by hand |

**Where installed skills overlap or disagree**

| Overlap | Resolution |
|---|---|
| Two test-first skills | `test-driven-development` governs the loop; `tdd` supplies where tests go. The skill explains each proposed test location to the owner in one plain line before it is confirmed. |
| `brainstorming` and `grilling` | Brainstorming first, grilling afterwards on Full only. |
| Review at several levels | Task level comes from the sub-agent method; branch level from `code-review`. The same level is not run twice. |
| Decision records | `domain-modeling` proposes `docs/adr/`; this framework uses `DECISIONS.md` with seven fields. `DECISIONS.md` wins; `GLOSSARY.md` stays as it is. |
| Plan and design locations | Companions' default folders give way to `docs/plans/` and `docs/`, so the repository documents the work and not the tooling. |
| `mutation-testing` tool | It needs the mewt or muton tool, which is not installed on the owner's machine, and Python support is unconfirmed. If the tool does not cover the project's language, use the fallback, or a language-specific tool added as a development dependency with a decision entry. |

## 6. The test ladder

"Tested to its limits" means each part climbs these rungs. A rung that cannot apply is marked not applicable with a reason.

1. **Written first.** A test failed before the code existed.
2. **Proven to catch breakage.** Removing the behaviour or protection turns a test red, by mutation testing or by hand on a throwaway copy. Green tests alone are not evidence.
3. **Whole input range.** Generated inputs, boundary values, and hostile probe inputs chosen to break it.
4. **Real integration.** A start from a clean clone using only the documented commands, and an end-to-end run with the real services, done early and repeated.
5. **Deliberate failure.** Kill a process, break a key, cut the network, feed corrupt data; the system recovers or fails visibly with a reason.

A **part** is one component in the architecture diagram, plus every protection or rule named in `REQUIREMENTS.md` or the attack list. Each part has one row in the test table, so untested behaviour cannot hide inside a large component.

Evidence is written so the owner can check it without reading code, with raw counts next to rates: "I removed the rule and 3 tests went red", "14 of 109 missed, then 109 of 109".

## 7. Understanding the project

`ARCHITECTURE.md` is built stage by stage, not written at the end. It holds:

- a diagram of the parts and how they connect;
- a file map: every tracked file or folder and what it does;
- the tech stack and why each piece was chosen;
- a test table: each part, each ladder rung, the evidence;
- complex problems: what went wrong, what was tried, what fixed it;
- dependencies: name, version, why it is here, what breaks without it.

`check_gates.py` compares the file map with `git ls-files` and the dependency table with the project's manifests, and fails when they differ.

At Stage 6 the agent asks the owner to explain the project in their own words, using questions drawn from `ARCHITECTURE.md`. The agent compares the answers with the code and names the gaps; answers and gaps go in `OWNERSHIP.md`. The owner also changes at least one module by hand and names the commit.

The owner's stated risk is moving too fast without understanding, so this stage is deliberately slow:
- **A gap keeps Stage 6 open** until the owner can explain that point, or logs an override.
- **A re-check follows within the week.** `OWNERSHIP.md` holds a due date 7 days after Stage 6 closes. The first time the owner works in the project after that date, the agent asks again, and a new gap reopens the stage. A date passing is reported as a reminder, not as a script failure, so a build does not go red merely because time passed.

Each engineering concept gets one plain sentence the first time it appears, with a line in the project's `GLOSSARY.md`, so nothing is explained twice.

## 8. Rules the owner does not know yet

There are two separate layers, and the skill always says which one a rule comes from:

- **Principles** (`principles/`): as now, each rests on a real incident.
- **Engineering checklist** (`checklist/`, new): recognised practices the owner has not personally met. Each item has an id, the rule in plain words, why it matters, when it applies (project traits), how to validate it, the companion that helps, and a **cited source** such as OWASP (Open Worldwide Application Security Project) or NIST (the US National Institute of Standards and Technology). A test refuses an item with no source.

Areas covered: testing techniques (integration, contract, property-based, mutation, fuzz, load, failure injection, clean-clone start), security (threat modelling, access control, input handling, secrets), dependencies, logging and monitoring, error handling, safe retries, data migrations, rollback, backups, and for AI systems prompt injection, cost limits and output evaluation.

Sources are read from their primary documents when each item is written. The design's earlier anti-goal, "rules without a stated incident", is narrowed to principles, and a decision entry records it.

## 9. Go-live review

Before anything goes live the skill reads the project, identifies its traits (database, web exposure, paid APIs, personal data, an LLM, containers, scheduled jobs), and builds `GO-LIVE.md` from the checklist, the attack list and the principles. It also proposes project-specific risks of its own.

| Column | Meaning |
|---|---|
| Risk | what could go wrong, in plain words |
| Validation | the test or command that would show it |
| Source | checklist id, principle id, attack list entry, or "proposed for this project" |
| Status | `proven`, `not applicable` or `overridden` |
| Evidence | command and result, the reason it does not apply, or the override id |

A row that is not resolved blocks the release unless an override is logged. Typical findings from past projects: containers running as root, ports open on all interfaces, no graceful stop, documents that contradict the code.

## 10. Overrides

The owner may override any gate. `OVERRIDES.md` keeps one entry per override: id (`O1`, `O2`, ...), date, stage, what was skipped, why, the risk accepted, how to close it, status (`open` or `closed`), and closing evidence. Entries are never deleted; closing one records how.

Open overrides are listed at every stage opening and in the go-live review. The owner can ask at any time to see them or to go back to one.

## 11. Parts and checks

Added to this repository:

```
skills/agentic-principles/
  SKILL.md                short router: start, adopt, resume, current stage
  stages/                 one file per stage, loaded only when needed
  companions.json         the section 5 mapping
  scripts/                init_project.py, check_gates.py
checklist/                the engineering checklist
templates/                STAGES, OVERRIDES, ARCHITECTURE, GO-LIVE, OWNERSHIP
.claude-plugin/           plugin manifest, same format as the owner's other skill
```

**README.** The repository's `README.md` is rewritten as a proper front page: what this is and who it is for, the eight stages, how to install and start, what a run looks like, the known limit from section 3, and a section on the third-party skills it works with. That section names each plugin (among them `andrej-karpathy-skills`, `mattpocock-skills`, `superpowers` and the Trail of Bits plugins), says what it does at which stage, how to install it, and that the skill still runs without it through its fallback. A test compares the plugins named in the README with `companions.json`.

`init_project.py` copies the templates and checks into a project and adds them to its continuous integration workflow. The checks run in the project itself, so they work without the agent.

`check_gates.py` follows the conventions of `check_docs.py` (exit 0, 1 or 2; problems as `FILE:LINE: message`) and fails when:

- a stage is `passed` without evidence, or `overridden` without an existing override id;
- a stage is closed while an earlier one is still open;
- an override entry is incomplete (an open override is listed but is not a failure);
- a file map or dependency table disagrees with the repository;
- a `GO-LIVE.md` row is unresolved or a `proven` row has no evidence;
- a test-table row has a missing rung, or a rung marked not applicable with no reason.

**Timing.** The script reads the current stage from `STAGES.md`, and each check binds when its stage closes: the test table at Stage 4, the file map and dependency table and `GO-LIVE.md` at Stage 5. Continuous integration stays green while a project is being built, and documents are forced back in line at the stage that needs them.

**Overriding a check.** Each checked section may carry a line `Override: O<n>` naming an existing override; the script then reports it as overridden, not as failed. Every gate is therefore overridable, as section 10 promises.

**Manifests.** Version 0.2 reads `requirements*.txt`, `pyproject.toml` and `package.json`, direct dependencies only. Container images and workflow actions are listed by hand. For any other ecosystem the owner writes `Manifests: manual: <reason>`, and the table is then taken as stated. A manifest type the script cannot read, with no such line, is a problem and is never skipped.

Tests: every check has a case that must fire and a look-alike that must not. A test validates `companions.json` (every stage covered, every entry has a fallback), and a checker reports companions that are not installed. The skill's instructions are tested the way `superpowers:writing-skills` prescribes, with scenarios that pressure an agent to skip a gate.

Acceptance, required before release: the skill adopts the past project named in section 4; its go-live review, run at the commit before that project's final review, and finds all the known problems listed in section 9. Details that would identify the project are recorded only in the private companion repository. The owner's full Stage 6 on that project follows the release, in its own session, so that no deadline rushes the understanding; the first new project run from intake to retro also follows the release.

## 12. Decided and left to the builder

Decided by the owner: the purpose and audience; overrides allowed and always saved; a choice of normal or sub-agent method per project; a sized-down path; working hand in hand with installed skills; two rule layers with cited sources; a go-live review; what the owner must be able to explain; a gap keeps Stage 6 open and a re-check follows within the week; the trust limit in section 3 is accepted for this version; adoption of existing projects, optional except for the one past project to be understood from A to Z; publishing does not wait for that A-to-Z round; a proper README that names the third-party skills.

The designer's calls, open to correction:
- the skill name `agentic-principles`, and the location in this repository, linked into the skills folder as the owner's other skill is;
- the file names in sections 7, 9, 10 and 11;
- the Small and Full definitions and the per-size table in section 4;
- `diagnosing-bugs` as primary over `systematic-debugging`, for its stricter definition of a usable failing check;
- one independent review kept in normal mode;
- the definition of a part, the timing of each check, the override line, and the manifest list in sections 6 and 11;
- the go-live acceptance run uses that past project at the commit before its final review, must find all four known problems, and is recorded only in the private companion repository;
- a passed re-check date is a reminder and not a script failure;
- release as v0.2.0, moving the portable guard hook to a later version and renaming the enforcement kind "contract hook (planned, v0.2)" to "contract hook (planned)".

Left to the builder: wording of the stage files, the checklist's item count and order, the exact traits list, the format of `companions.json`.
