# Stage 0: Intake

**Gate:** a requirements matrix exists, and every fact (date, quota, price) carries its source.

Intake turns a brief into something the build can be checked against. A requirements matrix is a table with one row per requirement, linking it to the decision, the test and the evidence that cover it (see `templates/REQUIREMENTS.md`).

### P0.1 Take every fact from its source and write dates as absolute dates
- **Rule:** Write each date, quota and price with the source it came from, and write dates as calendar dates instead of "in two weeks".
- **Why (incident):** A deadline was first estimated from memory and came out three days too late; the real date was in the original message all along.
- **How to check:** Read the intake notes: does every date, quota and price name its source, and is every date a calendar date?
- **Enforced by:** human gate

### P0.2 Read the templates the brief provides before writing your own
- **Rule:** Use any template or format the brief provides in place of your own format.
- **Why (incident):** An AI agent wrote a document in its own format although the brief shipped a template for it; a human question caught the mismatch before delivery.
- **How to check:** List the files the brief provides: is each provided template used for the document it describes?
- **Enforced by:** human gate

### P0.3 Let the requester's stated expectations win over your personal workflow rules
- **Rule:** Follow the requester's explicit instructions where they conflict with your own working rules, and apply your own rules only where the brief is silent.
- **Why (incident):** A personal habit of one file per decision was dropped in one project because the brief asked for a single decision file; the switch was recorded as a decision so the reason stayed visible.
- **How to check:** Read `DECISIONS.md`: where a personal rule was set aside, is there a decision entry that quotes the brief?
- **Enforced by:** human gate
