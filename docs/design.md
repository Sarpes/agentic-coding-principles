# Design: Agentic Coding Principles (v0.1)

Status: approved 2026-11-06 · Decision owner: the maintainer

## 1. Intent and why

A public, self-contained reference for building software with an AI coding agent (Claude Code) under strict, industry-standard rules: written decisions, stage gates, tests that prove the gates can fail, and an honest AI usage log. Every principle comes from a real incident in real projects, not from a generic best-practice list.

Who it serves:
- **Primary: the maintainer.** Every new project starts from this structure (templates, principles, the docs gate).
- **Secondary: readers evaluating the work**, who open the repository and should see within two minutes that it is rule-driven and test-backed.

Success: a new project can be carried end to end (intake → retro) with these principles; the repository applies them to itself; CI shows the docs gate green on every push and the tests show it can go red.

## 2. Goals, non-goals, anti-goals

Goals (v0.1, for the first release):
- An 8-stage framework with one gate per stage.
- Principles per stage, each with the incident behind it and how to check it.
- Copy-ready templates for the project documents.
- `check_docs.py`: a portable documentation gate (CLI) with tests, run in CI.
- The repository's own `DECISIONS.md` and `AI-Agents.md`, from the first commit.

Non-goals (v0.1): a tool-call guard hook (the owner's own tool-call hook, not public, does this), skill packaging, tempo modes (hackathon vs full), an installer.

Anti-goals (a failure even if it works):
- A long list of principles nobody applies.
- Rules without a stated incident ("best practices" invented to look complete).
- Anything tied to the owner's machine (paths, private projects) or naming or describing a specific project, company or case; incidents read as "lessons from projects built so far".
- A gate that only reads well: every check must have a test that makes it fire.

## 3. Constraints

- Python 3.11+, standard library only; `unittest` (no pytest dependency). Runs on Windows, macOS, Linux.
- English, MIT licence, public at `github.com/Sarpes/agentic-coding-principles`.
- Subject to the documentation rules below: `DECISIONS.md` and `AI-Agents.md` complete before every push.
- Handovers go to a private companion repo; public files never link to it.
- Git: one branch per task, PRs merged with merge commits after the owner's OK, decision entries in the same branch.

## 4. Layout

```
README.md                  what, why, the 8 stages, how to use it in a new project
LICENSE                    MIT
CHANGELOG.md
CLAUDE.md                  layout, commands, Never list (for agents working on this repo)
DECISIONS.md               this repository's decisions (format = templates/DECISIONS.md)
AI-Agents.md               this repository's AI usage log
principles/
  README.md                index: stage · gate · principle ids
  00-intake.md … 07-retro.md
templates/
  DECISIONS.md  AI-Agents.md  REQUIREMENTS.md  BUILD-LEDGER.md
  RESULTS.md  HANDOVER.md  GLOSSARY.md  PULL_REQUEST_TEMPLATE.md
checks/
  check_docs.py            the documentation gate (CLI)
tests/
  test_check_docs.py       red/green cases for every check
docs/
  design.md                this document, once approved
.github/workflows/ci.yml   tests + the gate on the repository itself
.gitignore  .gitattributes
```

## 5. The framework

| Stage | Gate (evidence needed to move on) |
|---|---|
| 0 Intake | Requirements matrix exists; facts (dates, quotas, prices) carry their source |
| 1 Design | Written design approved by the human; decisions logged with rejected options |
| 2 Plan | Every task has a definition of done |
| 3 Build | Each task red-first, green, reviewed by a separate reviewer |
| 4 Verify | Real integrations run end to end; a fresh clone starts with the documented commands |
| 5 Ship | Secret scan by value; PR shows goal, choices, measurements, how to check |
| 6 Own | The human can explain every module and has changed at least one by hand |
| 7 Retro | Every "where the AI was wrong" entry became a rule, a template change or a recorded "won't fix" |

## 6. Principle format

Each principle in `principles/NN-stage.md`:

```
### P3.2 Never silence a flaky test with retries
- **Rule:** one sentence, imperative.
- **Why (incident):** what happened and its measured effect, as a lesson from projects built so far; no project, company or domain named.
- **How to check:** a command, a file to read, or a question with a yes/no answer.
- **Enforced by:** template | check_docs | tool-call hook | CI | human gate
```

Principle set (lessons from projects built so far, reviewed 06.11): intake E1-E3, B10; design B1-B3, E4, E5, A1-A2, A7-A8, C3; plan E6, A5; build B5-B9, C1-C2, C4-C5, E7-E9; verify A6, E10, E11; ship D1-D4, E12, A3-A4; own E13; retro E14. Wording is the builder's, within the format above. (superseded: see DECISIONS.md D8 and principles/README.md for the final set)

## 7. Templates

Each template is a filled skeleton with one worked example entry and short guidance in HTML comments. `DECISIONS.md` and `AI-Agents.md` must pass `check_docs.py` as shipped (the example entry counts). `REQUIREMENTS.md` is a table: ID · Requirement (quoted from the brief) · Decision (Dn) · Test · Evidence · Status (open | met | not done).

## 8. `check_docs.py`

- Usage: `python checks/check_docs.py [REPO_DIR]` (default: current directory). Exit 0 = pass, 1 = problems found, 2 = usage error.
- Checks, each problem printed as `FILE:LINE: message`:
  - `DECISIONS.md`: same rules as the documentation rules above (7 fields, `None: <reason>` instead of blank, contiguous numbering, one decision per heading, Assumptions and Not done sections, at least one entry).
  - `AI-Agents.md`: 5 fields per entry, none blank, contiguous numbering, at least one entry.
  - `REQUIREMENTS.md` (only if present): every row has all six columns filled; a row marked `met` has a non-empty Test and Evidence.
- Missing `DECISIONS.md` or `AI-Agents.md` is a problem (the gate exists to require them).
- Tests: `python -m unittest` from the repository root; at least one case that must fire and one look-alike that must not, per rule; written and seen red before the implementation.

## 9. CI

GitHub Actions on push and pull request: matrix Python 3.11 and 3.13 on ubuntu-latest and windows-latest; steps: unit tests, then `python checks/check_docs.py .` on the repository itself.

## 10. Build order (one branch and PR each)

1. `chore/scaffold`: README skeleton, LICENSE, CHANGELOG, CLAUDE.md, .gitignore/.gitattributes, DECISIONS.md, AI-Agents.md, docs/design.md.
2. `feat/check-docs`: red tests, then the gate.
3. `docs/templates`: templates, each passing the gate where it applies.
4. `docs/principles`: the eight stage files and the index.
5. `ci/github-actions`: the workflow; README badges and "how to use".
Release: tag `v0.1.0`, CHANGELOG entry.

## 11. Decided vs left to the builder

Decided by the owner: new standalone public repo, name, English deliverable, its own DECISIONS.md public, the owner's existing decision-record format as the standard, v0.1 scope above, guard hook deferred.

Decided by the owner (06.11): incidents are described only as "lessons from projects built so far"; no project, company or case is named or described.

My calls (to check): standard library and `unittest` only; the rule logic is duplicated between `check_docs.py` and the owner's own tool-call hook (not public) for now (recorded under Not done: the hook should later import the public checker).

Left to the builder: principle wording, template guidance text, CI cosmetics.
