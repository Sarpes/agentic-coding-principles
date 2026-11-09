# Stage 5: Ship

## Purpose

Decide, with the owner understanding what they are approving, whether this is ready for real use.

## Do

Work in this order.

1. **Explain-back.** Before the go-live review, ask the owner three questions, one on each topic: what this does, how it can break, how to recover. Write the answers word for word in `OWNERSHIP.md`, section `## Explain-back`. A separate session, not the one that wrote the code or asked the questions, compares the answers with the code and writes each gap. An open gap blocks this stage unless the owner logs an override. Never write or tidy an answer for the owner.
2. **Go-live review.** Run `python checks/check_gates.py --go-live`. It detects the project's traits and lists every checklist id and attack id `GO-LIVE.md` must carry. Add one row for each, then add the project-specific risks you find yourself by reading every file the project ships and runs. Each row gets a risk in plain words, a validation (the test or command that would show it), a source, a status (`proven`, `not applicable` or `overridden`) and evidence.
3. **Reviews and audits.** Run the review, security, default-settings, documents-against-code and dependency checks in the table below, and write what each found. A finding not fixed is sorted MUST, SHOULD or LEAVE in `BUILD-LEDGER.md`.
4. **Secrets.** Scan the whole history for the real secret values before any push (`principles/05-ship.md`, P5.1).
5. **File map and dependency table.** Bring both in `ARCHITECTURE.md` in line with the repository. `check_gates.py` compares them with `git ls-files` and the manifests.
6. **Re-confirm overrides.** List each override still open. The owner re-confirms each one, one line each; write the date in `Re-confirmed for release`. You may not re-confirm for the owner, and an earlier message does not count.
7. **Pull request.** Use `templates/PULL_REQUEST_TEMPLATE.md`: Goal, Choices, Measurements, How to check. Merge with a merge commit, after the owner's OK for that merge.

## Companions

| Capability | Companion | If it is missing |
|---|---|---|
| Branch review against spec and standards | `mattpocock-skills:code-review`, or `superpowers:requesting-code-review` | a separate reviewer session |
| Security review | `security-review`, and `differential-review:differential-review` | the checklist's security items |
| Insecure default settings (needs the Workflow tool) | `/insecure-defaults:audit` | the checklist's configuration items |
| Documents checked against the code (needs the Workflow tool) | `spec-to-code-compliance:spec-to-code-compliance` | `check_gates.py` plus a reviewer reading each claim |
| Dependencies | `supply-chain-risk-auditor:supply-chain-risk-auditor` | run `npm audit` or `pip-audit` (through `uvx` if it is not installed) and record the result |
| Repository audit | `repo-kickoff` audit mode | `check_docs.py` and `check_gates.py` only |
| Claims need evidence | `superpowers:verification-before-completion` | a command and its output for every claim |
| Pull request text | `templates/PULL_REQUEST_TEMPLATE.md` | the same template |
| Finishing the branch | `superpowers:finishing-a-development-branch` | merge by hand after the owner's OK |

Give the code-review companion the base branch and the path of the design or plan.

## Gate

`OWNERSHIP.md` with its explain-back complete and no open gap, and `GO-LIVE.md` with a resolved row for every required id, named as `file:` evidence in `STAGES.md`, then `python checks/check_gates.py`. Every override still open must carry its re-confirmation.

## Small

The explain-back still has its three questions. `GO-LIVE.md` is required whenever `check_gates.py --go-live` lists a required id. Setup does not copy it on Small, so copy it from `templates/` when it is needed.
