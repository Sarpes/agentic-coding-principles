# Stage 1: Design

**Gate:** the written design is approved by the human, and every decision is logged with its rejected options.

### P1.1 Settle the design in question rounds before writing any code
- **Rule:** Run design rounds in which the agent asks sets of questions, each with a recommended answer, and write no code until the human has approved the written design.
- **Why (incident):** In one project 73 decisions (measured at the time) were made in rounds before the first line of code; during the build the agent then needed rulings only for implementation details, not for product questions.
- **How to check:** Run `git log --reverse --format="%ad %s" --date=short` and read the design document: is the first code commit dated after the design's approval?
- **Enforced by:** human gate

### P1.2 Test a costly assumption with a cheap spike outside the repository
- **Rule:** Before building on an assumption about an external service, run one small throwaway experiment (a spike) outside the repository, record what it showed as a decision, and delete its raw output.
- **Why (incident):** A single run against a real external service showed how its output was structured and how sensitive data appeared in it; both facts changed the design before anything was built on the wrong guess.
- **How to check:** Read `DECISIONS.md`: does each assumption about an external service cite a spike or primary documentation, and is no raw spike output tracked in git?
- **Enforced by:** human gate

### P1.3 Take provider facts from the provider's own documentation
- **Rule:** Read quotas, prices and limits of a service from the provider's primary documentation, not from third-party pages.
- **Why (incident):** A provider was recommended on the basis of a quota figure from a third-party page; the figure was wrong.
- **How to check:** Read the design: does every provider fact link to the provider's own documentation?
- **Enforced by:** human gate

### P1.4 Keep product decisions with the human and log the agent's rulings with their cost
- **Rule:** Leave product decisions (Dn in `DECISIONS.md`) to the human, let the agent make implementation rulings (Rn in `BUILD-LEDGER.md`) only with a stated cost if wrong, and sort every deferred finding in that ledger into MUST, SHOULD or LEAVE before shipping.
- **Why (incident):** In one build the agent made 60 rulings (measured at the time), each with its cost if wrong; none had to be reversed, and the human reviewed them in one pass.
- **How to check:** Read `BUILD-LEDGER.md`: does every ruling have a cost if wrong, does none decide a product question, and does every deferred finding carry MUST, SHOULD or LEAVE?
- **Enforced by:** template + human gate

### P1.5 Classify data and threats while designing
- **Rule:** Record in the design which data is sensitive, who can read what, where secrets live and with which privileges each process runs.
- **Why (incident):** Containers running as the root user and a weak secret key format were found only in the final review, when fixing them cost more than it would have at design time.
- **How to check:** Read the design: does it have a section on data classification, access and secrets?
- **Enforced by:** human gate

### P1.6 Record every decision with seven fields, plus assumptions and what was not done
- **Rule:** Write each decision in `DECISIONS.md` with all seven fields, number decisions without gaps, change an old decision only by an "Update" note or a superseding decision, and keep the "Assumptions" and "Not done (and why)" sections.
- **Why (incident):** In one finished log, 70 of 73 decisions (measured at the time) lacked at least one field, 69 of them the rejected options, and one heading that grouped three decisions hid them from every check.
- **How to check:** Run `python checks/check_docs.py .` and confirm exit 0.
- **Enforced by:** check_docs + contract hook (planned)

### P1.7 Keep the human's answers verbatim, with the decision each produced
- **Rule:** Store the human's answers to design questions word for word, in a separate file, each linked to the decision it produced.
- **Why (incident):** In one project a later disagreement about what had been decided was settled by reading the stored verbatim answer.
- **How to check:** Pick three decisions in `DECISIONS.md`: does each link to a verbatim answer in the answers file?
- **Enforced by:** human gate
