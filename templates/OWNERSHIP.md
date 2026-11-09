# Ownership

<!--
Where the owner's ownership record is and when it was made. The answers themselves are NOT here: they are the
owner's own words about how well they understand the system, and this repo may be public. They live in a private
record in the project's companion repo, named by the 'Record:' line (template: OWNERSHIP-RECORD.md).
check_gates.py refuses an '## Explain-back' or '## Full round' section in this file at every stage.

check_gates.py reads these lines; keep the labels exactly.

  Record               the private record, as a path relative to this project folder. init_project.py fills in
                       the project folder's name; repo-kickoff makes the companion repo next to the project. An
                       absolute path, or a path inside this project, is refused. From stage 5 on, a record that
                       cannot be read fails the gate; it is never treated as passed. In continuous integration,
                       where the companion never exists, the workflow runs check_gates.py --private-unavailable,
                       which prints a NOT CHECKED note for that one case instead.
  Explain-back done    the date of the explain-back (checked when stage 5 Ship is marked passed), like 2026-11-09

The lines, at stage 6:
  Hand-changed commit  the hash of the commit where the owner changed one module by hand; it must touch a source file
  Closed               the date stage 6 was closed, like 2026-11-09
  Re-check due         exactly 7 days after Closed
  Re-check done        "-" until the re-check has been made, then its date. When the due date has passed and this
                       is still "-", check_gates.py prints a reminder (a note, never a failure); the next working
                       session asks the questions again, and a new gap marks stage 6 as reopened.

The dated lines are left empty on purpose and are refused until filled in.
-->

Record: ../<project>-internal/ownership/OWNERSHIP.md
Explain-back done:
Hand-changed commit:
Closed:
Re-check due:
Re-check done:
