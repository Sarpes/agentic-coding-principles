# Results

Measurements of this repository's own scripts (`check_gates.py`, `check_companions.py`, `init_project.py`, `build_checklist.py`), taken while applying to them the five-rung test ladder the skill asks of other projects (design section 6 and section 11, "The scripts climb the ladder themselves"). Three measurements: generated garbage input (rung 3, input range), rules removed on a throwaway copy (rung 2, catches breakage), and a clean clone (rung 4, real integration: the project works from nothing but its documented commands).

Terms. A *mutation* is one small deliberate change to the source (a rule removed, a comparison flipped, a constant changed). It is *killed* when the test suite fails against the changed copy and *survives* when every test still passes, which means the suite could not have noticed that change in a real defect either. An *equivalent* mutation changes nothing a caller can observe, so no test can or should kill it.

## Setup

- Machine and versions: one Windows 11 computer, Python 3.13 (the project supports 3.11 and newer), git 2.54.0 (the Windows build), standard library only. Date of the runs: 2026-11-09.
- Garbage input: `tests/test_gate_robustness.py`, fixed seed 20261109. The test builds one real temporary git repository holding a complete project (every stage passed, so every check is reached), then, for each of 15 file types, rewrites that one file with a generated document and calls `check_project`. Nine kinds of document, taken in turn: random bytes; a prefix cut at any byte (including inside a multi-byte character); truncated tables; very long lines (1,000 to 60,000 repeats); lines of only `|`; non-ASCII characters; CRLF, bare CR and a byte-order mark; shuffled and doubled lines; and random lines made from the rules' own vocabulary (`Size:`, `file:`, `### O1.`, `Override: O1`, and so on). A run passes when it returns `(problems, notes)` and nothing is raised, and when it finishes within 5 seconds. The same generator feeds `check_companions.py` with 100 generated settings files.
- Rules removed on a copy: a script kept outside this repository copies the repository into 12 to 14 working folders, applies one mutation to `check_gates.py` in a folder, runs `python -m unittest -f tests.test_check_gates` there, and restores the file. 179 mutations in all, over 94 functions and rule tables of `check_gates.py`: every function that makes a decision or reads a file, plus the rule tables (`REQUIRED`, `CONTENT_RULES`, `TRAIT_RULES` and the numeric limits). The kinds of change: a condition replaced by `False` or `True`, a branch removed, a comparison flipped (`==` to `!=`, `>` to `>=`), a character class or regular expression loosened, a constant changed by one, an entry removed from a table. The repository itself was never modified by this script.
- Clean clone: `git clone` of this repository from its local path into an empty folder, `git checkout` of the working branch, then only the commands the documentation names (`python -m unittest -v` from README.md and CLAUDE.md, `python checks/check_docs.py` from CLAUDE.md).

## Outcome versus expected

### 1. Garbage input (rung 3)

| Subject | Expected | Observed | Raw count |
|---------|----------|----------|-----------|
| `check_project` on 15 file types, 500 documents per type | no traceback, each run under 5 s | 0 tracebacks; 1 hang found and fixed (see below) | 7,500 of 7,500 runs returned a result after the fix (run with `ROBUSTNESS_PER_TYPE=500`, 161 s) |
| `check_project`, default count in the test suite | same | same | 1,500 of 1,500 runs (100 per type, about 35 s) |
| `check_companions.py` on generated settings files | exit 0 with a report, always | 2 defects found and fixed (see below) | 8 of 100 files crashed before the fix, 0 of 100 after |

Defects found by the garbage run, each fixed red-first (a failing test in its own commit, then the fix):

1. `clean_lines` removed HTML comments with the regular expression `<!--.*?-->`. On a long run of `<!--` with no `-->` each opener scans to the end, so the time grows with the square of the length. Measured on the real code: 20,000 openers (80 KB) took 8.2 s, and one 160 KB line made a single `check_project` run take 48 s because the text is cleaned 66 times per run. Fixed with a linear scan (`_blank_comments`); the replacement agrees with the old expression on 200,000 random strings over `<`, `!`, `-`, `>`, newline, `a`, `b`.
2. `check_companions.py`: a plugin key holding a NUL character made `Path.glob` raise `ValueError` outside any `try`, so the command ended with a traceback instead of exit 0.
3. `check_companions.py`: a settings file nested far past the JSON parser's limit raised `RecursionError`, which is not a `ValueError`, so the existing `except` did not catch it.

Not tested by generation: `init_project.py` and `build_checklist.py`. Both read only files that this repository ships or that the owner creates with the tool; their error paths are covered by the existing tests in `tests/test_init_project.py` and `tests/test_checklist.py`.

### 2. Rules removed on a copy (rung 2)

| Step | Expected | Observed | Raw count |
|------|----------|----------|-----------|
| First pass, existing tests | every mutation killed | 132 killed, 46 survived (one further entry had a bad search text and was run later) | 132 + 46 = 178 mutations |
| New tests written for the survivors | each survivor killed by a new test | 44 closed by a new test | 44 of 46 |
| Equivalent mutations | explained, not closed | 2 | 2 of 46 |
| Final state, all tests | no open survivor | 177 killed of 179, 2 equivalent, 0 open | 179 mutations: 177 killed, 2 equivalent, 0 open |

Totals for the table above: total 179, killed 177 (132 at the first pass, 44 after new tests, plus the 179th, a replacement for an entry whose search text did not match, run once after the new tests and killed), survivors closed 44, equivalent 2.

The 44 survivors that were closed point to behaviour the suite had not pinned. Examples, each now a named test in `tests/test_check_gates.py`: a comment keeps its line breaks so line numbers stay true; `section_lines` stops at a level-two heading; the first of a repeated `Closed:` line wins; the report lists ids in natural order (`C-SEC-2` before `C-SEC-10`); a deleted `OVERRIDES.md` is reported as vanished by `check_project`; `git log` without `--full-history` loses an override that a merge discarded (built with a real merge); an annotated tag of the setup commit must not count as a later commit; a hand-changed commit that touches only a non-ASCII source name is still source (this needed `core.quotepath=off`); a folder that is not a repository gives "not a git repository", not another message.

The 2 equivalent mutations:

- `tracked_files` without the `returncode != 0` check: a failed `git ls-files` prints nothing on standard output, so the split gives the same empty list.
- `_requirements_deps` without the skip of lines that start with `-`, `.` or `/`: `_pep508` only accepts a name that starts with a letter or digit, so such lines yield nothing either way.

One more near miss worth keeping: a mutation of `main` (removing the "not a directory" check) survived the first new test because it asserted only exit code 2, which a file path also produces through the "not a git repository" branch. The test now also asserts the message. A check that passes on the wrong path is a weak check.

### 3. Clean clone (rung 4)

| Command (run in the clone, from its top folder) | Expected | Observed | Raw count |
|---------|----------|----------|-----------|
| `python -m unittest -v` | all tests pass | OK, 1 skipped (the private-name scan needs a local environment variable, as in CI) | 824 tests run, 823 passed, 1 skipped, 217.6 s |
| `python checks/check_docs.py` | exit 0 | exit 0 | 1 of 1 |

The clone was made from the local repository path into an empty folder, then `git checkout test/gates-ladder` (commit `bfe32b7`, the last commit before this file); `git status` in the clone showed 0 changed files before the run. Nothing was installed and no file was copied in by hand.

## Observations

- Hangs, not tracebacks, were what generated text found in `check_gates.py`: 0 exceptions in 7,500 runs, but 1 input shape that made time grow with the square of the length. The garbage test therefore also times each run.
- The first mutation pass had 46 survivors in 178 (26%), so the 771 tests that existed before this work were thorough about the main rules and thin about the helpers (text splitting, git helpers, date parsing, ordering of output). Most survivors were in those helpers.
- Five of the survivors were in code that the first mutation list did not include at all (the git helpers); adding them found real gaps (a tag object counted as a later commit; non-ASCII source names). A mutation list written from the rules misses what the rules stand on.
- The mutation count is a measurement of this suite against these 179 changes, not a proof that no defect exists. The 179 are a sample chosen by the author of this measurement, and the list lives outside the repository, so someone else cannot rerun exactly the same list from the repository alone.
- At 100 documents per type the garbage test runs in about 35 s; at 500 per type, the number the design asks for, it runs in 161 s. The default is 100 so that the whole suite stays near 4 minutes; set `ROBUSTNESS_PER_TYPE=500` to run the full count.
- The sample is also bounded by the generator: documents are one file at a time against an otherwise valid project, so a defect that needs two files to be wrong in a specific combination is not searched for.

## How to reproduce

1. Garbage input: `python -m unittest -v tests.test_gate_robustness` (100 documents per type), or `ROBUSTNESS_PER_TYPE=500 python -m unittest -v tests.test_gate_robustness` (500 per type). The seed is fixed in the test file, so a failure names the file, the index and the kind of document and can be rebuilt.
2. Rules removed on a copy: copy the repository (without `.git`) to a scratch folder, change one rule in `skills/agentic-principles/scripts/check_gates.py` there, and run `python -m unittest tests.test_check_gates` in the copy; the run must fail. Repeat for each rule. The 179 changes of this measurement were applied by a script kept outside the repository.
3. Clean clone: `git clone <path or address of this repository> fresh`, check out the branch, then `python -m unittest -v` and `python checks/check_docs.py` from the clone's top folder.
