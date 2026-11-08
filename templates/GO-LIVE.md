# Go-live

<!--
The go-live review: what could go wrong once this is live, and the proof that it does not. check_gates.py reads this
table when stage 5 Ship is marked passed, so keep the columns exactly.

Run `python check_gates.py --go-live` to list what must be covered: it detects the project's traits (database, web,
paid-api, llm, container, scheduled) from its files and dependencies, adds the traits named on the Traits: line of
STAGES.md, and prints every checklist item those traits need plus every attack id from ATTACKS.md.

Columns, in this order:
  Risk        what could go wrong, in plain words
  Validation  the test or command that would show it
  Source      exactly one id (a checklist id such as C-SEC-1, or an attack id such as ATK-1), or free text such
              as "proposed for this project". Every required id needs one row of its own, with the id alone in
              this cell; two ids in one cell are refused.
  Status      proven, not applicable or overridden. Anything else (open, blank) is unresolved and blocks release.
  Evidence    proven: the command that was run and its result. not applicable: the reason. overridden: the
              override id (for example O2), an open entry in OVERRIDES.md for stage 5.

Add your own rows for risks the lists do not name. Typical findings from past projects: a container running as
root, a port open on every network interface, no graceful stop, documents that contradict the code.

The rows below are worked examples, marked (EXAMPLE): replace them and remove the marker. check_gates.py refuses
this file as evidence while the marker remains.
-->

| Risk | Validation | Source | Status | Evidence |
|---|---|---|---|---|
| The container runs as root. (EXAMPLE) | Start it and print the user it runs as. | C-SEC-1 | proven | ran `docker run image id -u`: printed 1000, not 0 |
| A record with quotes and newlines breaks the parser. (EXAMPLE) | Feed it the hostile record from the attack list. | ATK-1 | proven | ran tests/test_hostile.py: 6 of 6 passed, the record is stored unchanged |
| The service listens on every network interface. (EXAMPLE) | List the open ports from another machine. | proposed for this project | not applicable | it is a command line tool and opens no port |
