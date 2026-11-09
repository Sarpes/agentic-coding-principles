# Decisions

<!--
Decision log. One entry per decision, numbered D1, D2, ... in order, no gaps.
Every entry has all seven fields, none blank. If a field does not apply, write
"None: <reason>". One decision per heading; never group ("D3-D4").
Write the entry in the same branch as the change it explains.
The example below is a worked example, marked (EXAMPLE) in its heading: replace it with your
first real decision and remove the marker. check_gates.py refuses evidence that still carries it.
-->

Decision log for <project>. Each decision has seven fields; none is left blank. Where a field does not apply, it says `None:` and gives the reason.

### D1. SQLite as the first database (EXAMPLE)

- **Context:** The service stores a few thousand records, runs on one machine, and has one writer at a time. The team has no database administrator.
- **Options considered:** (a) SQLite in a single file; (b) a hosted PostgreSQL server; (c) plain JSON files on disk.
- **Chosen:** (a) SQLite.
- **Why:** It needs no server, ships with the language's standard library, and the data fits comfortably in one file. Backup is a file copy. Measured: 10,000 inserts took 0.4 s on the development machine (command: `python bench_insert.py`).
- **Rejected:** (b) PostgreSQL, because running and securing a server is a cost with no benefit at this size; (c) JSON files, because concurrent writes can corrupt them and there is no query language.
- **Cost / trade-off:** Only one writer at a time, and no network access to the data. Moving to PostgreSQL later means a migration.
- **What would make you change it:** More than one process needing to write at once, or data growing past what one machine holds.

## Assumptions

<!-- List what you assumed without proof, one line each. An assumption nobody wrote down cannot be checked later. -->

- Traffic stays below 10 requests per second.

## Not done (and why)

<!-- List what was left out on purpose, with the reason. "Not done" is a decision too. -->

- User accounts: not needed until a second user exists.
