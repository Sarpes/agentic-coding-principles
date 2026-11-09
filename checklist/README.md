# Engineering checklist

Recognised engineering practices that a project owner without engineering training may not have met yet. They sit beside the principles in `principles/`, and the two are kept apart on purpose:

- A **principle** rests on a real incident that happened on a project.
- A **checklist item** rests on a recognised published source, cited with the address of the page it was taken from. No incident is claimed.

Decision D16 in `DECISIONS.md` records why there are two layers; decision D19 records which sources were chosen.

## Files

| File | Area | Id prefix |
|---|---|---|
| `testing.md` | Testing techniques | `C-TEST-` |
| `security.md` | Security | `C-SEC-` |
| `dependencies.md` | Dependencies | `C-DEP-` |
| `operations.md` | Logging, monitoring, error handling, retries, rollback | `C-OPS-` |
| `data.md` | Data migrations, backups, personal data | `C-DATA-` |
| `ai-systems.md` | Systems that use a large language model | `C-AI-` |
| `checklist.json` | Generated: each item's id and the traits it applies to | |

## Item format

Each item is a heading `### C-<AREA>-<n> <title>`, numbered from 1 without gaps in its file, followed by six fields:

- **Rule:** what to do, in plain words.
- **Why it matters:** what goes wrong without it.
- **Applies when:** `always`, or one or more traits joined with `+`. The item applies when the project has **any** of the listed traits.
- **How to validate:** the test, command or look that shows the rule is met.
- **Companion:** an installed skill, agent or command from `skills/agentic-principles/companions.json` that helps, or `none`.
- **Source:** the name and section of the source, and the `https://` address of the page that was read.

## Traits

A *trait* is a property of the project that decides which items apply. `check_gates.py --go-live` detects the first six from the project's files; the owner declares `personal-data` in the `Traits:` line of `STAGES.md`, because no script can see it.

| Trait | Meaning |
|---|---|
| `database` | the project stores data in a database |
| `web` | the project answers requests over a network (a website or an API) |
| `paid-api` | the project calls a service that charges per use |
| `llm` | the project calls a large language model |
| `container` | the project runs in a container (for example Docker) |
| `scheduled` | the project runs jobs on a timer or a queue |
| `personal-data` | the project handles information about people |

## How the go-live review uses it

Before release, `check_gates.py --go-live` lists every item whose `Applies when` is `always` or names one of the project's traits. `GO-LIVE.md` needs one row for each listed id, resolved as `proven` (with the command and its result), `not applicable` (with the reason) or `overridden` (with the override id).

## Changing an item

Edit the item, then regenerate `checklist.json` and run the tests:

```
python skills/agentic-principles/scripts/build_checklist.py
python -m unittest tests.test_checklist
```

`build_checklist.py --check` fails when `checklist.json` is out of date. The builder refuses an item with a blank field, a source without an `https://` address, an unknown trait or a companion that is not in the mapping. A new item's source is read from its primary document before the item is written; a source known only from memory is not cited.

## Sources

| Source | Pages read |
|---|---|
| OWASP Top 10:2025 | https://top10.owasp.org/2025/ (categories A01, A02, A03, A05, A06, A09, A10) |
| OWASP Application Security Verification Standard (ASVS) 5.0.0 | https://github.com/OWASP/ASVS/tree/v5.0.0/5.0/en (chapters V2, V8, V13, V14, V16) |
| OWASP Top 10 for LLM Applications 2025 | https://genai.owasp.org/llm-top-10/ (LLM01, LLM02, LLM05, LLM06, LLM09, LLM10) |
| NIST SP 800-218, Secure Software Development Framework 1.1 | https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-218.pdf (tasks PW.4.4, PW.8.2) |
| Google SRE book | https://sre.google/sre-book/ (Testing for Reliability, Addressing Cascading Failures, Monitoring Distributed Systems, Data Integrity) |
| The Twelve-Factor App | https://12factor.net/ (II, III, V, IX, X, XI, XII) |

## Not covered yet

Contract testing (checking that two services agree on the shape of the messages they exchange) and mutation testing (changing the code on purpose to see whether a test notices) are named in the design but are not described in any of the six sources above, so they have no item. Mutation testing is still reached through the stage 4 companion in `companions.json`. Property-based testing appears only as the way to run C-TEST-3.
