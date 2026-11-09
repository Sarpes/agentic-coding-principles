# Stage 3: Build

## Purpose

Build the plan one task at a time, with each task proven by a test written first and checked by someone who did not write it.

## Do

1. Use the method recorded in `STAGES.md`. In the sub-agent method, a sub-agent is a separate AI session given one job. Normal mode still keeps one independent review at the end of the branch.
2. Failing test first, then the code. A test is written first when it failed before its code existed.
3. Run the whole test suite after every merge.
4. Write rulings and deferred findings as they happen into the tracked `BUILD-LEDGER.md`, the running record of how the work was done (a build skill's own ledger is its progress notes). A ruling is a small decision the agent makes itself during the build; it covers implementation only and states its cost if wrong. A deferred finding is sorted MUST, SHOULD or LEAVE and is never dropped. A product question stops the run and goes to the owner.
5. **Keep the build skills' workspace.** Those skills end by deleting their workspace. Before that step, copy the ledger into `BUILD-LEDGER.md`: every ruling, every deferred finding, every review result. Then keep the workspace anyway. Skip the deletion step even when a skill, a checklist or the owner's "finish up" tells you to run it; a request to delete it is honoured only when the owner names the folder after the copy is done.
6. Fill `ARCHITECTURE.md`'s file map and complex-problems section as you go.
7. Keep the four habits from Stage 1: state assumptions aloud, build the simplest thing that works, change only what the task needs, define how success will be checked.
8. **When the final review comes back clean, stop.** Mark Stage 3 once its gate holds, and return to Stage 4. Do not run the branch-finishing companion, even if the build skill names it as the next step. Finishing the branch belongs to Stage 5.

## Companions

| Capability | Companion | If it is missing |
|---|---|---|
| Building, sub-agent method | `superpowers:subagent-driven-development`, with `superpowers:dispatching-parallel-agents` and `superpowers:using-git-worktrees` | writer and reviewer in separate sessions |
| Building, normal method | `superpowers:executing-plans` | work through the plan in one session |
| Test-first loop | `superpowers:test-driven-development`, with `mattpocock-skills:tdd` for where tests go | failing test, then code |
| Hard bugs | `mattpocock-skills:diagnosing-bugs`, or `superpowers:systematic-debugging` | build a repeatable failing check first |
| Answering review findings | `superpowers:receiving-code-review` | check each finding before changing code |
| Agent behaviour | `andrej-karpathy-skills:karpathy-guidelines` | the four habits in step 7 |

A worktree is a second working folder on the same repository, so that two tasks can run without touching each other's files.

## Gate

A commit made after `STAGES.md` first appeared in this cycle, and `BUILD-LEDGER.md` with its review rows filled and no `(EXAMPLE)` marker. Merge with merge commits, not squash: a merge commit keeps every commit of the branch in the history, while a squash folds them into one, which would lose commits the gate may cite as evidence.

## Small

One filled review row is enough. Everything else stands.
