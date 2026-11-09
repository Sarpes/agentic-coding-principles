# Stage 2: Plan

## Purpose

Turn the approved design into tasks small enough to check one at a time, and settle now everything a running build cannot stop to ask.

## Do

1. Write the plan as a file in `docs/plans/`. Every task has a definition of done: a statement someone can check.
2. Record the build method the owner chose, and log it in `DECISIONS.md` if that is not already done.
3. Check the interfaces between tasks: what one task hands to the next, written the same way in both.
4. Confirm test locations with the owner now, because a sub-agent run does not pause to ask. Explain each proposed location in one plain line.
5. Keep the four habits from Stage 1: state assumptions aloud, build the simplest thing that works, change only what the task needs, define how success will be checked.

## Companions

| Capability | Companion | If it is missing |
|---|---|---|
| Writing the plan | `superpowers:writing-plans` | the `docs/plans` format of this repository |
| Agent behaviour | `andrej-karpathy-skills:karpathy-guidelines` | the four habits in step 5 |

The planning companion's own default folder gives way to `docs/plans/`. When it finishes, return here; it does not decide how or when the build starts.

## Gate

A non-empty plan file in `docs/plans/`, named as `file:` evidence in `STAGES.md`, then `python checks/check_gates.py`.

## Small

A `PLAN.md` task list at the top of the project replaces the plan file. Each task still has a definition of done.
