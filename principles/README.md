# Principles

A project built with an AI coding agent moves through eight stages. Each stage ends at a gate: the evidence that must exist before the next stage starts. Every principle is a rule learned from a real incident in projects built so far; a rule without an incident is not added (candidates wait under "Not done (and why)" in `DECISIONS.md`). Each principle has four parts:

- **Rule:** one imperative sentence.
- **Why (incident):** what actually happened and its effect. Numbers were measured at the time; their sources are private projects and are not published.
- **How to check:** a command, a file to read, or a yes/no question about a named file or record.
- **Enforced by:** one or more of the kinds below, joined by `+`.

## Enforcement kinds

| Kind | Meaning |
|---|---|
| template | A file in `templates/` has a place for it, so leaving it out is visible. It does not check that the place is filled. |
| check_docs | `python checks/check_docs.py .` fails when it is missing or incomplete. |
| CI | A test that runs on every push and pull request fails when the rule is broken. |
| human gate | A person answers the "How to check" question before the stage closes. |
| contract hook (planned, v0.2) | A hook that refuses the tool call breaking the rule. Not public yet; until then the rule rests on the other kinds named with it. |

## Index

| Stage | Gate (evidence needed to move on) | Principles |
|---|---|---|
| [0 Intake](00-intake.md) | Requirements matrix exists; facts (dates, quotas, prices) carry their source | P0.1 · P0.2 · P0.3 |
| [1 Design](01-design.md) | Written design approved by the human; decisions logged with rejected options | P1.1 · P1.2 · P1.3 · P1.4 · P1.5 · P1.6 · P1.7 |
| [2 Plan](02-plan.md) | Every task has a definition of done | none yet (awaiting a real incident) |
| [3 Build](03-build.md) | Each task red-first, green, reviewed by a separate reviewer | P3.1 · P3.2 · P3.3 · P3.4 · P3.5 |
| [4 Verify](04-verify.md) | Real integrations run end to end; a fresh clone starts with the documented commands | P4.1 |
| [5 Ship](05-ship.md) | Secret scan by value; PR shows goal, choices, measurements, how to check | P5.1 · P5.2 |
| [6 Own](06-own.md) | The human can explain every module and has changed at least one by hand | P6.1 |
| [7 Retro](07-retro.md) | Every "where the AI was wrong" entry became a rule, a template change or a recorded "won't fix" | P7.1 |

20 principles in all.
