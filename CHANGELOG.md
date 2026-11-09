# Changelog

All notable changes to this project are recorded here.

## Unreleased

- `skills/agentic-principles/`: a skill that conducts a project through the eight stages (router, one file per stage), with `companions.json` mapping capabilities to installed skills, `init_project.py`, `check_gates.py`, `check_companions.py` and `build_checklist.py`.
- `.claude-plugin/`: plugin and marketplace manifests.
- `checklist/`: 40 engineering checklist items, each citing a recognised source, and the generated `checklist.json`.
- `templates/`: STAGES, OVERRIDES, ATTACKS, ARCHITECTURE, GO-LIVE and OWNERSHIP templates, and a continuous integration workflow for projects.
- `README.md`: rewritten as a front page, with the limits stated openly and a section on the skills this one works with.
- `principles/`: the enforcement kind "contract hook (planned, v0.2)" is now "contract hook (planned)".
- `tests/test_readme.py`: the README must name exactly the plugins in `companions.json`.
- `docs/design.md`: the anti-goal about rules without an incident is marked as narrowed to principles (D16).

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
