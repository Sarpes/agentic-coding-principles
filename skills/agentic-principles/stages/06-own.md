# Stage 6: Own

## Purpose

Prove that the owner can explain and change this project without the agent. This stage is slow on purpose: the owner's stated risk is moving too fast without understanding.

## Do

1. Draw the questions from `ARCHITECTURE.md`, one per component and at least 3 in all.
2. Run the **closed-book** round: the owner has the documents shut and answers without help. Write each answer word for word in `OWNERSHIP.md`, section `## Full round`. Do not tidy, complete or suggest answers: a tidy answer hides what was not understood.
3. Have a **separate session**, not the one that wrote the code or asked the questions, compare the answers with the code and name the gaps. Record that session in `Graded by`.
4. **A gap keeps this stage open** until the owner can explain that point in a later answer, or logs an override after hearing the risk. Teaching the point is welcome; writing the answer is not.
5. The owner changes at least one module by hand and names the commit in `Hand-changed commit`. It must touch a source file. The agent may suggest a change and must not make it.
6. Write `Closed` with the date, and `Re-check due` exactly 7 days later.
7. **The re-check.** The first time the owner works in the project after the due date, ask again, before other work. A new gap marks the stage `reopened`, which is allowed even after Stage 7 has passed. Write the date in `Re-check done`. A date passing is a reminder and never a failure.

If the owner says "you know it better, fill it in", say no plainly, and offer to ask the questions now, one at a time.

## Companions

| Capability | Companion | If it is missing |
|---|---|---|
| Reading an existing codebase function by function, for the agent's preparation (adoption; needs the Workflow tool) | `audit-context-building:audit-context-building` | the agent walks the file map with the owner |

That companion prepares the agent; it does not teach the owner, who still does this round. It writes an `audit-context/` folder: add `audit-context/` to the project's `.gitignore` before running it, so its notes are not committed.

## Gate

`OWNERSHIP.md` with enough answers, no open gap, `Graded by` filled, a hand-changed commit touching a source file, and a `Re-check due` exactly 7 days after `Closed`. Named as `file:` evidence in `STAGES.md`, then `python checks/check_gates.py`.

## Small

3 questions in all. Everything else stands, including the separate grading, the hand change and the 7-day re-check.
