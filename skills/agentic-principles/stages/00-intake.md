# Stage 0: Intake

## Purpose

Write down what "done" means before anything is built, and how this could be broken or misused, while it is still cheap to change course.

## Do

This stage opens after `init_project.py` has run, so `STAGES.md` exists and the owner has chosen the size.

1. Ask the owner for the acceptance criteria and write them in `REQUIREMENTS.md` as `REQ-1`, `REQ-2`, ... An acceptance criterion is a statement that can be checked as true or false.
2. Ask whether the project will hold personal data (names, addresses, emails, anything that points to a person). No script can detect this. If yes, add `Traits: personal-data` to `STAGES.md`.
3. Have a **separate session** draft the attack list. A fresh agent or a new conversation, one that has not discussed the solution, receives `REQUIREMENTS.md` and is asked: "How could this be broken or misused?" It writes `ATTACKS.md` as `ATK-1`, `ATK-2`, ... and names for each the ladder rung it must be tried at, 3 or 5 (rungs are in the Stage 4 file). An attacker who helped build the thing shares its blind spots, so never draft this list in the working session.
4. Give the owner the list to read and add to. Keep what the owner adds in the owner's words.
5. Give every fact a source: dates as absolute dates, and quotas, prices and limits from the provider's own documents (`principles/00-intake.md`, P0.1).
6. **Grill the owner on the requirements**, on every project, Small or Full: run the grilling companion on `REQUIREMENTS.md` and `ATTACKS.md`, one challenge at a time. Write each challenge, the owner's own answer and what it changed (a `REQ` or `ATK` id added or changed, or `kept`) in `GRILLING.md`, section `## Intake`, with the line `Grilled with:` naming the skill, or `fallback: written challenges` when it is not installed. At least 3 answered challenges. Never accept a bare "yes" to a suggested answer.

## Companions

| Capability | Companion | If it is missing |
|---|---|---|
| Starting the repository | `repo-kickoff` | the repository's templates |
| Researching facts from primary sources | `mattpocock-skills:research`, or `anthropic-skills:deep-research` | the agent reads the provider's own documents |
| Grilling the owner on the requirements (every project) | `mattpocock-skills:grilling` | written challenges, asked one at a time and answered by the owner |

When the companion finishes, return to the step list above.

## Gate

`REQUIREMENTS.md` with at least one `REQ-n`, `ATTACKS.md` with at least 5 attacks, neither still holding the template marker `(EXAMPLE)`, and `GRILLING.md` whose `## Intake` section has its `Grilled with:` line and at least 3 answered challenges. Name all three as `file:` evidence in `STAGES.md`, then run `python checks/check_gates.py`.

## Small

At least 3 attacks. The separate session, the owner's reading and the grilling (at least 3 answered challenges) are still required.
