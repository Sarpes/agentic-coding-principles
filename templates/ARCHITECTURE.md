# Architecture

<!--
How the project is built, written stage by stage and finished before release. check_gates.py reads three of
its sections; keep the headings and the table columns exactly. The rows below are worked examples, marked
(EXAMPLE): replace them and remove the marker. check_gates.py refuses this file as evidence while the marker
remains.

When each check binds (once the stage is marked passed): the Tests section at stage 4 Verify; the File map and
Dependencies sections at stage 5 Ship.

Any checked section may carry a line "Override: O<n>" naming an open entry in OVERRIDES.md for that stage; the
check is then reported as overridden and not as failed.
-->

## Diagram

<!-- Show the parts and how they connect: a few boxes and arrows in a code block or a Mermaid diagram. -->

```
input file --> Parser --> Store --> exporter --> CSV file   (EXAMPLE)
```

## Components

<!--
One row per part of the system that does work. Each name here needs its own row in the Tests table.
-->

| Component | What it does |
|---|---|
| Parser | Reads an input file and returns records. (EXAMPLE) |
| Store | Keeps the records between restarts. (EXAMPLE) |

## File map

<!--
Every file git tracks, and what it does. A path ending in / covers everything below it, and may cover at most
10 files unless its description holds (bulk: <reason>). "/" alone is refused. Paths use forward slashes.
check_gates.py compares this table with `git ls-files` and fails when they differ.
-->

| Path | What it does |
|---|---|
| src/parser.py | Reads input files. (EXAMPLE) |
| tests/ | Automated tests for the parser and the store. (EXAMPLE) |

## Tech stack

<!-- Each language, framework or service, and why it was chosen over the alternative. -->

- Python 3.11, standard library only: nothing to install for a small tool. (EXAMPLE)

## Tests

<!--
One row per part: every component above, every REQ-n in REQUIREMENTS.md and every ATK-n in ATTACKS.md. The first
cell holds exactly one part, written as it appears there. The five rungs are the test ladder:
  1 Written first        a test failed before the code existed
  2 Catches breakage     removing the behaviour turns a test red
  3 Input range          generated, boundary and hostile inputs
  4 Real integration     a clean-clone start and a run with the real services
  5 Deliberate failure   kill, cut or corrupt something; the system recovers or fails visibly
Each rung cell holds a tracked test or results file (tests/test_a.py, or tests/test_a.py::test_name), or a
commit hash on the current history, or "n/a: <reason>". Small projects need rungs 1 and 2; Full projects need all
five; any attack also needs the rung its ATTACKS.md row names (3 or 5), on any size.
-->

| Part | 1 Written first | 2 Catches breakage | 3 Input range | 4 Real integration | 5 Deliberate failure |
|---|---|---|---|---|---|
| Parser (EXAMPLE) | tests/test_parser.py | tests/test_parser.py | tests/test_parser.py | n/a: no external service | n/a: reads a file only |
| REQ-1 (EXAMPLE) | tests/test_store.py | tests/test_store.py | n/a: one fixed input | RESULTS.md | tests/test_store.py |

## Complex problems

<!-- What went wrong, what was tried, what fixed it. One short entry per problem, newest last. -->

- (EXAMPLE) The store lost records on a crash. Tried: flushing on exit. Fixed: write to a temporary file, then rename.

## Dependencies

<!--
One row per direct dependency in the project's manifests: requirements*.txt, pyproject.toml, package.json.
A pinned version (==1.2 or "1.2.3") must match the Version cell exactly. For any other kind of manifest, or one
the check cannot read (Poetry, dependency groups, Pipfile, environment.yml, setup.py, go.mod and similar), add
the line "Manifests: manual: <reason>" under this heading and list the dependencies by hand.
A project with no dependencies keeps the header and leaves the table empty.
-->

| Name | Version | Why it is here | What breaks without it |
|---|---|---|---|
| requests (EXAMPLE) | 2.32.0 | Fetches the input over HTTP. | The tool cannot read remote input. |
