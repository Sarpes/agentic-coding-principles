# Changelog

All notable changes to this project are recorded here.

## Unreleased

- `scripts/mutate.py`: rung 2 for Python from a script in this repository, on a throwaway copy, with five kinds of change and a table ready for `RESULTS.md`; the fallback for proving tests catch breakage (D31). First run on `checks/check_docs.py`: 145 mutants, 131 then 133 killed in two runs.
- `check_companions.py`: each MISSING line names the fallback to use, and `stage_table_problems` checks that every stage file names each of its companions with a fallback; tests prove the skill runs with none installed.
- `check_gates.py`: from Stage 4 on, every `REQ-n` and `ATK-n` must be named in a test file (a problem on Full, a note on Small; a note from Stage 3 on). An attack whose Rung is `n/a: <reason>` is exempt (D30).
- `STAGES.md` records the skill version (`Skill-version:`, written by `init_project.py`). `check_gates.py` lists, as notes, each migration a project set up with an earlier version still has to make (all of them when the line is missing), and refuses a project newer than its copied gate script (D29).
- `CREDITS.md`: every companion project the skill names (18), with its author, source and licence, and the formats and sources this project follows (Keep a Changelog, Architecture Decision Records, the Claude Code plugin documentation, the checklist sources). `tests/test_credits.py` fails when a companion has no credit (D28).

## [0.3.0] - 2026-11-10

Two breaking changes for projects already under the skill: move the ownership answers to the private record and add the `Record:` and `Explain-back done` lines to `OWNERSHIP.md`; add `GRILLING.md` for Stages 0 and 1 already passed, or log an override.

- Breaking: the owner's explain-back and full-round answers move out of the project repo into a private record in the companion repo next to it (`../<project>-internal/ownership/OWNERSHIP.md`, new template `templates/OWNERSHIP-RECORD.md`). The project's `OWNERSHIP.md` keeps a `Record:` line, a new `Explain-back done` date, the hand-changed commit and the re-check dates (D26). A project already under the skill must move its answers and add the two lines.
- `check_gates.py`: reads the answers from the private record, fail-closed. From Stage 5 on, a record that cannot be read (missing, a folder, not UTF-8) fails and is reported as "could not be read", apart from a readable record without answers. An absolute `Record:` path, or one inside the project, is refused. An answer section in the project's `OWNERSHIP.md` is refused at every stage.
- `check_gates.py --private-unavailable`: for CI, where the companion is never present; only the unreadable case becomes a printed `NOT CHECKED` note. The project CI template runs the stage gate with it.
- `init_project.py`: fills the `Record:` line with the project folder's name, creates the record template in the companion repo when it exists (never overwriting), and otherwise says how to make the companion with repo-kickoff.
- Stage 5 and Stage 6 instructions, the skill's rules and the README: the session that asks the questions writes the answers straight into the private record.
- Grilling runs on every project, Small or Full, at Stage 0 Intake and Stage 1 Design (D27). New template `templates/GRILLING.md` (copied by `init_project.py`) with an `## Intake` and a `## Design` section: a `Grilled with:` line naming the skill or the fallback, and at least 3 answered rows of challenge, owner's answer and outcome.
- `check_gates.py`: Stages 0 and 1 need `file:GRILLING.md` in their evidence on both sizes; Stage 0 judges only the Intake section, Stage 1 only the Design section. A project already past those stages must add the record or log an override.
- `companions.json` and the stage files: `mattpocock-skills:grilling` maps to Stages 0 and 1 for every project, with written challenges as the fallback.
- `check_gates.py`: a git argument holding a NUL character (a commit value in `STAGES.md`, found by the robustness test) is a failed lookup instead of a crash.

## [0.2.0] - 2026-11-09

- Renamed to Agentic Engineering Principles (D24): README title and logo, the GitHub repository, and the plugin and marketplace name `agentic-engineering-principles`; the skill keeps the name `agentic-principles`.
- `README.md`: a quick start before the stage table and a "Using it day to day" section: what each session starts with, what the owner can say, where the records live, and what the agent never writes for the owner (D25).

- `skills/agentic-principles/`: a skill that conducts a project through the eight stages (router, one file per stage), with `companions.json` mapping capabilities to installed skills, `init_project.py`, `check_gates.py`, `check_companions.py` and `build_checklist.py`.
- `.claude-plugin/`: plugin and marketplace manifests.
- `checklist/`: 40 engineering checklist items, each citing a recognised source, and the generated `checklist.json`.
- `templates/`: STAGES, OVERRIDES, ATTACKS, ARCHITECTURE, GO-LIVE and OWNERSHIP templates, and a continuous integration workflow for projects.
- `README.md`: rewritten as a front page, with the limits stated openly and a section on the skills this one works with.
- `principles/`: the enforcement kind "contract hook (planned, v0.2)" is now "contract hook (planned)".
- `tests/test_readme.py`: the README must name exactly the plugins in `companions.json`.
- `docs/design.md`: the anti-goal about rules without an incident is marked as narrowed to principles (D16).
- GitHub Actions: macOS joins the test matrix, so the tests run on Ubuntu, Windows and macOS (D21).

## [0.1.1] - 2026-11-08

- `checks/check_docs.py`: a file that is not valid UTF-8 is reported at the line of the bad byte instead of crashing the gate.
- `checks/check_docs.py`: backtick fences follow the renderer's rules, and an unclosed fence is reported at its opening line.
- `checks/check_docs.py`: a value written on the line below its label gets a message that says so.
- `principles/`: new enforcement kind "pre-commit hook"; P5.2 names it instead of a planned hook.
- `tests/`: the five ungated templates are checked for their parts, the stated total of principles is compared with the stage files, and a file named `*.env` must be refused by the secret gate.
- `docs/design.md`: one name for the owner throughout.

## [0.1.0] - 2026-11-06

- Repository scaffold: licence, ignore rules, design, decision log and AI log.
- `checks/check_docs.py`: documentation gate for the decision log, the AI log and the requirements table, with exit codes and tests.
- `templates/`: eight templates, each with one worked example.
- `principles/`: eight stage files and an index with 20 principles, each backed by a real incident.
- GitHub Actions: tests and the documentation gate on Python 3.11 and 3.13, Ubuntu and Windows.
- README: the eight-stage table and how to use the repository in a new project.
- `checks/check_docs.py`: reports misformed entry headings (for example `### D3 Title` or `## 3.`) instead of skipping them; with no argument it checks the current directory.
- `tests/test_secret_gate.py`: runs the pre-commit secret gate as a subprocess in a temporary repository and expects a key-like line to be refused.
