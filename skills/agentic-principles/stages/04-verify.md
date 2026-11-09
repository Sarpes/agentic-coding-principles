# Stage 4: Verify

## Purpose

Find out whether the work holds up, by trying to break it. Green tests alone say little: a test that cannot fail proves nothing.

## Do

Each **part** climbs the ladder. A part is one component listed in `ARCHITECTURE.md`, plus every `REQ-n` and every `ATK-n`, each on its own row of the test table.

| Rung | Name | What it takes |
|---|---|---|
| 1 | Written first | A test failed before the code existed. |
| 2 | Proven to catch breakage | Remove the behaviour or protection and a test turns red. |
| 3 | Whole input range | Generated inputs, boundary values, and hostile inputs chosen to break it. |
| 4 | Real integration | Start from a clean clone using only the documented commands, then an end-to-end run with the real services. Do this early and repeat it. |
| 5 | Deliberate failure | Kill a process, break a key, cut the network, feed corrupt data. The system recovers, or fails visibly with a reason. |

1. Say plainly: **rung 2 is normally done by hand.** The mutation companion needs a separate tool (mewt or muton, programs that make small deliberate changes to the code and check whether a test notices) that is usually not installed, and its Python support is unconfirmed. By hand means: on a throwaway copy (a copy of the project made only for this check and discarded after), break each key rule and confirm a test goes red. A language-specific tool may be added as a development dependency with a decision entry.
2. Fill the test table in `ARCHITECTURE.md`. Each cell names a tracked test or results file, or a commit, or says `n/a: <reason>`. "ok" and "done" are refused. An attack must be tried at the rung its list entry names.
3. Run rung 4 early, not only at the end.
4. Write the results in `RESULTS.md` so the owner can check them without reading code, raw counts next to rates: "I removed the rule and 3 tests went red", "14 of 109 missed, then 109 of 109".
5. If an AI model is part of the project, evaluate its output on examples a person has checked. When the evaluation companion is missing, say so, use the fallback in the table below, and write that in `RESULTS.md`. "Skip it" is not the fallback, even when the owner offers it: the choice to skip is an override, with the risk stated first.

## Companions

| Capability | Companion | If it is missing |
|---|---|---|
| Whole-input testing | `property-based-testing:property-based-testing` | hand-picked boundary and hostile inputs |
| Proving tests catch breakage | `mutation-testing:mutation-testing` | break each key rule on a throwaway copy and confirm a test fails |
| Silent failures, test gaps | `pr-review-toolkit:silent-failure-hunter`, and `pr-review-toolkit:pr-test-analyzer` | reviewer checklist |
| Evaluating AI output (projects with an LLM) | `deepeval:deepeval` | labelled examples checked by a person, raw counts reported |
| Running the real thing | `run`, or `example-skills:webapp-testing` for browser apps | documented commands from a clean clone |
| Hard bugs | `mattpocock-skills:diagnosing-bugs`, or `superpowers:systematic-debugging` | build a repeatable failing check first |
| Claims need evidence | `superpowers:verification-before-completion` | a command and its output for every claim |

## Gate

`ARCHITECTURE.md` with a complete test table and `RESULTS.md`, named as `file:` evidence in `STAGES.md`, then `python checks/check_gates.py`. A deadline is not evidence. "It works, I ran it" is one run on one input: it is the start of rung 4, not the stage.

## Small

The test table needs rungs 1 and 2. An attack keeps the rung its entry names on any size. `RESULTS.md` is not required.
