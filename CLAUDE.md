# CLAUDE.md

Agentic Engineering Principles: rules, stage gates, templates and a tested documentation gate for building software with an AI coding agent.

## Layout

```
README.md  LICENSE  CHANGELOG.md  CLAUDE.md
CREDITS.md             every outside project, format and source used: author, source, licence (tests/test_credits.py)
DECISIONS.md           this repository's decisions (seven fields each)
AI-Agents.md           this repository's AI usage log (five fields each)
RESULTS.md             measurements of this repository's own scripts: rules removed on a copy, clean clone
principles/            index plus one file per stage (00-intake ... 07-retro)
templates/             DECISIONS, AI-Agents, REQUIREMENTS, BUILD-LEDGER, RESULTS, HANDOVER, GLOSSARY, PR template
checks/check_docs.py   the documentation gate (CLI)
skills/agentic-principles/   the skill: SKILL.md, stages/, companions.json, scripts/ (init_project, check_gates, check_companions, build_checklist, mutate)
checklist/             engineering checklist, each item with a cited source; checklist.json is generated
.claude-plugin/        plugin and marketplace manifests
docs/design-skill.md   the approved design of the skill
.githooks/             pre-commit secret gate (enable after cloning: git config core.hooksPath .githooks)
tests/                 red/green cases for every check
docs/design.md         the approved design
docs/plans/            implementation plans
.github/workflows/     CI: tests and the gate on this repository
```

## Commands

- Tests: `python -m unittest -v`
- Documentation gate: `python checks/check_docs.py` (checks the current directory; or pass a folder)
- Stage gate (in a project under the skill): `python checks/check_gates.py` (`--go-live` lists the go-live rows)
- Installed-skill report: `python skills/agentic-principles/scripts/check_companions.py`
- Private-name scan: set `ACP_FORBIDDEN_NAMES` (comma-separated) before the tests, or that test is skipped
- Enable the pre-commit secret gate after cloning: `git config core.hooksPath .githooks`

Python 3.11+, standard library only.

## Never

- Name or describe a project, company, client or domain.
- Write machine-specific paths.
- Add a rule without a test that makes it fire.
- Squash merges: use merge commits so the history reads as the development story.
- Leave a decision or log field blank.
- Commit straight to `main`: one branch per task.
- Use anyone else's work without credit: a new companion, format or source gets its row in `CREDITS.md` (author, https source, licence) in the same branch. Copy text or code from another project only as its licence allows, credited in `CREDITS.md`; Trail of Bits skills are CC BY-SA 4.0, so a copied part would have to stay under that licence. Public open-source projects named for credit are not the private projects the first rule protects.
