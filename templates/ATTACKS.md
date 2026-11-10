# Attacks

<!--
Ways the project could be broken on purpose, drafted in a session separate from the one that writes the code, so
the author's blind spots are not copied into the list. check_gates.py reads this table at stage 0 Intake.

Columns, in this order:
  ID           ATK-1, ATK-2, ... in order, no gaps
  Attack       what is done to the system, in plain words
  Rung         the test rung the attack must be tried at: 3 (hostile or generated input) or 5 (deliberate
               failure); "-" when it needs no particular rung; "n/a: <reason>" when the attack cannot happen
               in this project (it is then exempt from the test-link check)
From stage 4 on, each attack's id (ATK-1, ...) must appear in a test file that tries it.
  Drafted by   who or what drafted the row (for example "fresh session")
A Small project needs at least 3 rows and a Full project at least 5. This list lives in its own file because
check_docs.py reads every table row of REQUIREMENTS.md as a requirement.

The rows below are worked examples, marked (EXAMPLE): replace them and remove the marker. check_gates.py refuses
this file while the marker remains.
-->

| ID | Attack | Rung | Drafted by |
|---|---|---|---|
| ATK-1 | Feed the parser a file that is empty, huge or not UTF-8. (EXAMPLE) | 3 | fresh session |
| ATK-2 | Kill the process in the middle of a write and restart it. (EXAMPLE) | 5 | fresh session |
| ATK-3 | Send a record whose fields hold quotes, newlines and very long text. (EXAMPLE) | 3 | fresh session |
| ATK-4 | Remove the network while a remote file is being read. (EXAMPLE) | 5 | fresh session |
| ATK-5 | Run two copies at once on the same data file. (EXAMPLE) | - | fresh session |
