# CLAUDE.md

Agentic Coding Principles: rules, stage gates, templates and a tested documentation gate for building software with an AI coding agent.

## Layout

```
README.md  LICENSE  CHANGELOG.md  CLAUDE.md
DECISIONS.md           this repository's decisions (seven fields each)
AI-Agents.md           this repository's AI usage log (five fields each)
principles/            index plus one file per stage (00-intake ... 07-retro)
templates/             DECISIONS, AI-Agents, REQUIREMENTS, BUILD-LEDGER, RESULTS, HANDOVER, GLOSSARY, PR template
checks/check_docs.py   the documentation gate (CLI)
tests/                 red/green cases for every check
docs/design.md         the approved design
docs/plans/            implementation plans
.github/workflows/     CI: tests and the gate on this repository
```

Not every folder exists yet; v0.1 is built task by task (see `docs/plans/`).

## Commands

- Tests: `python -m unittest -v`
- Documentation gate: `python checks/check_docs.py .`

Python 3.11+, standard library only.

## Never

- Name or describe a project, company, client or domain.
- Write machine-specific paths.
- Add a rule without a test that makes it fire.
- Squash merges: use merge commits so the history reads as the development story.
- Leave a decision or log field blank.
- Commit straight to `main`: one branch per task.
