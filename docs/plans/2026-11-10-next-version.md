# Plan: the next version

Status: saved for the next version, not started (owner's decision, 2026-11-10). Each item is one branch and one pull request, red tests first, merged by the owner. Items are in the order agreed; an item marked **OWNER DECIDES** waits for that decision.

Already merged in this round (Unreleased in `CHANGELOG.md`): credits (D28), the skill version and migration notes (D29), requirement-to-test links (D30), the no-companions proof, the mutation runner (D31).

## 1. Owner-signed approvals (roadmap Task 2)

**OWNER DECIDES:** SSH or GPG, and opt-in (a `Signing:` line in `STAGES.md`) or required on Full. Recommended: SSH, opt-in.

- Why: the gate's printed limit is that owner and agent share one git identity. A commit signed with the owner's key is one the agent cannot make.
- Scope: `check_gates.py` checks with `git log --format=%G?` (or `git verify-commit`) that the commits which added `OVERRIDES.md` reasons, ownership answers and approval rows are signed by an allowed signer; the allowed signers come from a file the owner commits (`gpg.ssh.allowedSignersFile`). An unsigned or wrongly signed commit is a problem in plain words.
- Tests: a temporary repository, a throwaway key made at test time, signed / unsigned / wrong-key cases; skipped with a clear message when `ssh-keygen` is missing. README: a setup section in plain words.

## 2. Ownership drift re-check (roadmap Task 5)

Decided by the owner: a reminder for each module in the file map that is **new since the last ownership round, or with 30% or more of its lines changed**.

- `OWNERSHIP.md` records the commit of the last round (`Round commit:`). `check_gates.py` compares it with `HEAD` and adds a re-check note naming the modules, like the 7-day re-check: a note, never a failure, done first at the next session.
- Tests: no change, a small change, a large change, a new module, a missing or unknown commit.

## 3. A `workflow` trait for exported n8n workflows (roadmap Task 6)

Decided by the owner: the trait **refuses Small**.

- Detection: a tracked JSON file with a top-level `nodes` list and `connections` object. A JSON file with `nodes` alone does not fire.
- Checklist items, each from an n8n documentation page fetched and read before the item is written: no credentials or tokens inside exported workflow JSON; an error workflow for every production workflow; webhook-triggered workflows safe to run twice (with C-OPS-9); workflows exported and versioned in git after every change. The n8n project is credited in `CREDITS.md`.
- Tests: detection fires and its look-alike does not; the checklist builder accepts the items; `--go-live` lists them for a workflow project.

## 4. Checklist items from roadmap Task 0

The prepared patch files were not available. Rewrite from fetched primary sources: C-TEST-8 (linter and type checker in CI) and C-OPS-12 (semantic versioning). The checklist count bound in `tests/test_checklist.py` moves from 40 to 45.

## 5. Open findings from this round

- `scripts/mutate.py` on `checks/check_docs.py`: 12 to 14 survivors to sort into missing tests or equivalent mutations, and two mutants whose outcome changed between identical runs, which points to a timing-dependent test in `tests/test_check_docs.py` (P3.3: fix the cause, never retry).
- D30 starts the test-link note at Stage 3 passed instead of before every Stage 4 run, as the roadmap asked: confirm with the owner.

## 6. To re-evaluate after the owner's end-to-end run

These wait for evidence from one real project run under the skill (time per stage, overrides and their reasons, every drift from the rules, what the reviewer caught):

| Item | Question the run answers |
|---|---|
| With/without benchmark (10 to 20 tasks, two conditions) | Which measures matter enough to pay for many agent runs? |
| A Lite path (three gates) | Is Small still too heavy for one-person work? |
| Moving back a stage (Verify to Build, Build to Design) | How often does a later stage reopen an earlier one? Only Stage 6 can be `reopened` today. |
| Prompt-injection threat model for the agent itself | Did any outside text steer the agent? A checklist item from the OWASP Top 10 for LLM Applications if so. |

## Not planned

Recorded so they are not proposed again without new evidence: a hash-and-id layer per evidence file (git already records content, commit and time; signing answers the identity question); a computed risk score (Small/Full plus traits already does this); per-stage token metrics (after real runs exist); adapters for other agent platforms (no user yet); the cross-model reviewer option (only if a second provider is used).
