# Principles

A project built with an AI coding agent moves through eight stages. Each stage ends at a gate: the evidence that must exist before the next stage starts. Every principle is a rule learned from projects built so far, written in the same four parts:

- **Rule:** one imperative sentence.
- **Why (incident):** what happened and its measured effect. Where no single measured incident exists, the principle says so and gives the reasoning instead.
- **How to check:** a command, a file to read, or a question with a yes/no answer.
- **Enforced by:** one or more of the five kinds below.

## Enforcement kinds

| Kind | Meaning |
|---|---|
| template | A file in `templates/` has a place for it, so leaving it out is visible. |
| check_docs | `python checks/check_docs.py .` fails when it is missing or incomplete. |
| contract hook | A hook refuses the tool call or commit that would break the rule. |
| CI | A test that runs on every push and pull request fails when the rule is broken. |
| human gate | A person answers the "How to check" question before the stage closes. |

## Index

| Stage | Gate (evidence needed to move on) | Principles |
|---|---|---|
| [0 Intake](00-intake.md) | Requirements matrix exists; facts (dates, quotas, prices) carry their source | P0.1 · P0.2 · P0.3 · P0.4 |
| [1 Design](01-design.md) | Written design approved by the human; decisions logged with rejected options | P1.1 · P1.2 · P1.3 · P1.4 · P1.5 · P1.6 · P1.7 · P1.8 · P1.9 · P1.10 |
| [2 Plan](02-plan.md) | Every task has a definition of done | P2.1 · P2.2 |
| [3 Build](03-build.md) | Each task red-first, green, reviewed by a separate reviewer | P3.1 · P3.2 · P3.3 · P3.4 · P3.5 · P3.6 · P3.7 · P3.8 · P3.9 · P3.10 · P3.11 · P3.12 |
| [4 Verify](04-verify.md) | Real integrations run end to end; a fresh clone starts with the documented commands | P4.1 · P4.2 · P4.3 |
| [5 Ship](05-ship.md) | Secret scan by value; PR shows goal, choices, measurements, how to check | P5.1 · P5.2 · P5.3 · P5.4 · P5.5 · P5.6 · P5.7 |
| [6 Own](06-own.md) | The human can explain every module and has changed at least one by hand | P6.1 |
| [7 Retro](07-retro.md) | Every "where the AI was wrong" entry became a rule, a template change or a recorded "won't fix" | P7.1 |

40 principles in all.
