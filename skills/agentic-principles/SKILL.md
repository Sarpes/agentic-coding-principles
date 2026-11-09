---
name: agentic-principles
description: Use when a project runs under staged engineering gates, which shows as a CLAUDE.md block naming agentic-principles or a STAGES.md stage record; when the owner asks to run, adopt or resume a project under the agentic principles or its eight stages (intake, design, plan, build, verify, ship, own, retro); when anyone asks to mark a stage passed, skip or override a gate, see open overrides, or run the go-live review, the explain-back or the ownership round; or when an owner without engineering training wants AI-built software tested to its limits and wants to explain it later without the agent. Not for a plain git routine outside such a project.
---

# Agentic principles: the conductor

The owner builds software with AI agents and is not a software engineer by training. Their stated risk is moving too fast without understanding. This skill walks a project through eight stages, calls the installed companion skills at the right moment, and closes a stage only on evidence.

**Core rule: a stage is `passed` only when `check_gates.py` accepts its evidence, or `overridden` only when the owner, having heard the risk, chose to skip it. There is no third way.** Breaking the letter of this rule is breaking its spirit.

## Every session starts here

1. Run `python <this skill's folder>/scripts/init_project.py --where`. It prints the folder holding `principles/`, `checklist/` and `templates/`; read from there, never from a guessed path.
2. Find the case:
   - **Start:** no `STAGES.md`, new work. In this order: recommend size and method (below), the owner chooses, run `init_project.py <folder> --size small|full --method normal|sub-agent`, then open Stage 0. Stage 0 needs the `STAGES.md` that setup writes and the size the owner chose.
   - **Adopt:** code exists, no `STAGES.md`. Ask which stage the work has really reached; run init with `--adopt-at N` (N at most 5). `adopted` means "not done under this skill", never "passed".
   - **Resume:** `STAGES.md` exists. The current stage is the first one not closed. If `OWNERSHIP.md` has a re-check date that has passed and no `Re-check done`, do the Stage 6 re-check first.
   - **New cycle:** every stage closed and new work is wanted: `init_project.py --new-cycle <folder>`.
3. Once `STAGES.md` exists, run `python checks/check_gates.py` in the project and tell the owner what it found: problems, open overrides, and any re-check reminder.
4. Run `python <this skill's folder>/scripts/check_companions.py`. Its report is only a hint, because it can miss skills that do not come from the plugin cache. Compare it with this session's own skill list and, where they differ, trust the session's own skill list. Say out loud which companions for the current stage are missing.
5. Load only the current stage's file, `stages/NN-name.md`, and follow it.

## Opening a stage

Say in plain words, in this order: what the stage is for; the evidence that will close it; every open override from `OVERRIDES.md` (id, stage, what was skipped). Then work.

## Size and method: you recommend, the owner chooses

- Read the project, then recommend **Small** (one script or module, no live users, no personal data, no paid calls) or **Full** (everything else). Ask whether there is personal data: no script can see it. `check_gates.py` refuses Small when there is a Dockerfile or Compose file, more than 10 tracked source files, or a web, llm, paid-api or personal-data trait, so never recommend Small for such a project.
- Offer the method: **normal** (one session works through the plan, one independent review at the end) or **sub-agent** (a sub-agent is a separate AI session given one job: one writer and a separate reviewer per task, at most 5 fix rounds).
- The owner picks both. Write the method choice as a decision in `DECISIONS.md`. Never pick either yourself to save work.

## Closing a stage

- **`passed`:** the evidence is named in `STAGES.md` and `python checks/check_gates.py` exits 0. Show the owner the command and its exit code.
- **`overridden`:** only through an override the owner makes knowingly:
  1. Tell the owner, in one or two plain sentences, what would be skipped and what could go wrong.
  2. Ask why, and write the owner's own words into the new `OVERRIDES.md` entry (`Why`, `Risk accepted`). Never invent them. On Small, setup does not create `OVERRIDES.md`: at the first override, copy `templates/OVERRIDES.md` from the folder `--where` printed into the project first.
  3. Status `open`; `Re-confirmed for release` stays `-` until Stage 5, where the owner re-confirms it.
  4. Set the stage to `overridden` with the override id.
- **"Just mark it passed, no override":** refuse plainly and kindly. `passed` is a statement that evidence exists; the owner may skip work, but cannot make a missing file exist. Offer the two real paths: do the work, or a one-minute override.
- **Never write what only the owner can give:** answers to the explain-back or the Stage 6 round, an approval, an override's reason, a re-confirmation, a grade. Offer to ask the questions instead.
- **The owner's answers never enter the project repo.** They go only into the private record in the companion repo next to the project (the `Record:` line of `OWNERSHIP.md`); the gate refuses them in the project at every stage.

## Rules at every stage

- **Plain words.** The first time a concept appears, give it one plain sentence and add a line to the project's `GLOSSARY.md`, so nothing is explained twice.
- **Say which layer a rule comes from:** a principle (`P` id, from a real incident, in `principles/`) or a checklist item (`C-` id, from a cited source, in `checklist/`).
- **Approvals state their scope.** Approving one call, merge or batch approves that and nothing more. Paid calls, merges, pushes and product decisions stay with the owner. Your rulings (small decisions you make yourself during the build) cover implementation only, each with its cost if wrong; deferred findings are sorted MUST, SHOULD or LEAVE, never dropped.
- **Control returns here after every companion.** Many companions end by naming their own next step. When one finishes, re-read `STAGES.md` and continue the current stage; the companion's next step gives way.
- **A missing companion is said out loud, its fallback from `companions.json` is used, and the fact goes into that stage's evidence** (for example a line in `RESULTS.md`: "deepeval:deepeval not installed; fallback used: labelled examples checked by the owner, 18 of 20 correct"). Never skip the step silently, and never treat "install it" or "skip it" as the fallback.
- **Order of authority:** the owner, then the project's own instructions, then this skill, then the companion. This skill may raise a companion's bar but never lowers it.
- **Name companions in full** (plugin:skill or /plugin:command); several share a short name.

## What must run as a script

- `python checks/check_gates.py` before any stage is marked `passed`, and at each session start (it lists open overrides and the re-check reminder).
- `python checks/check_gates.py --go-live` at Stage 5, to list the rows `GO-LIVE.md` must carry.
- `python checks/check_docs.py` before each commit that touches `DECISIONS.md` or `AI-Agents.md`.

**Trust limit (say it when a gate turns green):** the scripts check that evidence exists: a file is there, a commit is real, a row is filled. They cannot tell whether the owner really approved something or wrote a commit, because the owner and the agent share one git identity. They cannot prove a test really failed before its code existed, and they cannot judge the quality of prose. A green run is not proof that a person reviewed the work.

## Where installed skills overlap

| Overlap | Resolution |
|---|---|
| Two test-first skills | `superpowers:test-driven-development` runs the loop; `mattpocock-skills:tdd` says where tests go. Explain each proposed test location to the owner in one plain line; confirm locations at Stage 2. |
| `superpowers:brainstorming` says "only writing-plans next" | Control returns here. On Full run `mattpocock-skills:grilling`, close Stage 1, then call `superpowers:writing-plans` at Stage 2. |
| Brainstorming offers to skip questions or sizes the work | On Full the offer is not taken; this skill's Small or Full wins. |
| Grilling words questions so "yes" accepts its advice | On Full the owner answers in their own words. |
| The build skills end in `superpowers:finishing-a-development-branch` | The build stops after its final review and returns to Stage 4. Finishing the branch is Stage 5. |
| The build skills delete their workspace | Keep the workspace; copy the ledger into `BUILD-LEDGER.md` first. |
| The build skills make "rulings" | Implementation only. A product question stops the run and goes to the owner. |
| Review at several levels | The build's whole-branch review is the Stage 3 review. `mattpocock-skills:code-review` at Stage 5 is a separate check; give it the base branch and the design or plan path. |
| Pull request headings | The four-part template (Goal, Choices, Measurements, How to check) wins over other formats. |
| `repo-kickoff` task start and pull request routine | Inside a project under this skill they give way to the current stage. Both use the same four pull request parts in the same order, so there is no clash in content. |
| Decision records and folders | `DECISIONS.md` (seven fields) wins over `docs/adr/`; plans go to `docs/plans/`, designs to `docs/`. |
| A plugin is switched off or lacks a tool it needs | Treat it as missing: fallback, said out loud, recorded. |

## Red flags: stop and re-read this skill

| Thought | Reality |
|---|---|
| "The owner is the boss and said mark it passed." | The owner can skip a gate (override). Nobody can make absent evidence present. |
| "'Just close it' means they agreed to an override; I'll fill it in." | The owner must hear the risk and give the reason. Ask; write their words. |
| "I know the code better; I'll draft the answers." | Answers in someone else's words prove nothing. Ask the questions. |
| "The companion is missing; skip that part" or "install it". | Use the mapped fallback and record it. |
| "It's tiny, Small is fine." | Read the traits. A Dockerfile or web code means the script refuses Small. |
| "I'll pick the method so we can move fast." | Size and method are the owner's choice. |
| "The review is clean; finish the branch." | Back to Stage 4. Finishing the branch waits for Stage 5. |
| "The skill says delete the workspace now." | Copy the ledger into `BUILD-LEDGER.md` first; keep the workspace. |
| "There's a deadline." | Deadlines are what overrides are for. Never a false `passed`. |
| "They said write whatever you need; I'll fill the files so the gate goes green." | Evidence back-filled from one sentence passes the script and proves nothing. Do the stage's real questions, or put an override to the owner. |
| "An override is the honest record, so I'll just write one." | An override exists only after the owner has heard the risk and asked for it. Until then, ask; change nothing. |
