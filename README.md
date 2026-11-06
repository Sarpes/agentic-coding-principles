# Agentic Coding Principles

[![CI](https://github.com/Sarpes/agentic-coding-principles/actions/workflows/ci.yml/badge.svg)](https://github.com/Sarpes/agentic-coding-principles/actions/workflows/ci.yml)

Rules, stage gates, templates and a tested documentation gate for building software with an AI coding agent. Every rule comes from a lesson in projects built so far: a rule without a real incident behind it is not added. A project moves through eight stages, and each stage ends at a gate, the evidence that must exist before the next stage starts. The repository holds 20 principles, eight templates, and a checker (`checks/check_docs.py`) that fails when a decision log, an AI log or a requirements table is incomplete.

## The eight stages

| Stage | Gate (evidence needed to move on) | Principles |
|---|---|---|
| 0 Intake | Requirements matrix exists; facts (dates, quotas, prices) carry their source | [00-intake.md](principles/00-intake.md) |
| 1 Design | Written design approved by the human; decisions logged with rejected options | [01-design.md](principles/01-design.md) |
| 2 Plan | Every task has a definition of done | [02-plan.md](principles/02-plan.md) |
| 3 Build | Each task red-first, green, reviewed by a separate reviewer | [03-build.md](principles/03-build.md) |
| 4 Verify | Real integrations run end to end; a fresh clone starts with the documented commands | [04-verify.md](principles/04-verify.md) |
| 5 Ship | Secret scan by value; PR shows goal, choices, measurements, how to check | [05-ship.md](principles/05-ship.md) |
| 6 Own | The human can explain every module and has changed at least one by hand | [06-own.md](principles/06-own.md) |
| 7 Retro | Every "where the AI was wrong" entry became a rule, a template change or a recorded "won't fix" | [07-retro.md](principles/07-retro.md) |

The index, with the four-part format of a principle and the kinds of enforcement, is in [principles/README.md](principles/README.md).

## Use it in a new project

1. Copy the files you need from [templates/](templates/) into the new repository, and copy `checks/check_docs.py` (the gate) too, so that step 3 works there.
2. Keep `DECISIONS.md` and `AI-Agents.md` at the repository root; fill every field, and replace the worked example entries with real ones.
3. Run the documentation gate: `python checks/check_docs.py .` (Python 3.11 or newer, standard library only). Exit code 0 means no problems; 1 lists them.
4. Add the same command as a step in your CI workflow, as in [.github/workflows/ci.yml](.github/workflows/ci.yml), so an incomplete log fails the build.
5. Work through the stages in order and close each one at its gate, using the principles file of that stage as the checklist.

## How it is tested

`python -m unittest -v` runs the tests in [tests/](tests/): the checker's functions, the templates (the three gated ones must pass the gate) and the principles (four fields each, contiguous ids, every id in the index, an incident for every rule). GitHub Actions runs the tests and then the gate on this repository, on Python 3.11 and 3.13, on Ubuntu and Windows.

The gate can fail. `test_cli_exit_1_on_broken_repo` in [tests/test_check_docs.py](tests/test_check_docs.py) builds a broken repository in a temporary directory at run time, runs the command-line tool on it and expects exit code 1; it runs in every CI job. No broken file is stored in the repository. The pre-commit secret gate in [.githooks/](.githooks/) is tested the same way: `tests/test_secret_gate.py` builds a temporary git repository, stages a key-like line made at run time and expects `git commit` to fail; it skips with a visible reason when git or a working Python is missing. One test that scans for private names is skipped in CI because it needs a local environment variable; this is expected.

## Layout

| Path | Content |
|---|---|
| `principles/` | The eight stage files and the index |
| `templates/` | Eight templates, each with one worked example |
| `checks/check_docs.py` | The documentation gate |
| `tests/` | Unit tests for the gate, templates, principles and the secret gate |
| `.githooks/` | Pre-commit secret gate; after cloning, enable it with `git config core.hooksPath .githooks` |
| `docs/design.md` | The design this repository was built from |
| `DECISIONS.md`, `AI-Agents.md` | This repository's own decision log and AI log |
| `.github/workflows/ci.yml` | The CI workflow |

## Licence

MIT. See [LICENSE](LICENSE).
