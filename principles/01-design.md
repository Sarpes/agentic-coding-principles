# Stage 1: Design

**Gate:** the written design is approved by the human, and every decision is logged with its rejected options.

### P1.1 Settle the design in question rounds before writing any code
- **Rule:** Run design rounds in which the agent asks sets of questions, each with a recommended answer, and write no code until the human has approved the written design.
- **Why (incident):** In one project 73 decisions were made in rounds before the first line of code; during the build the agent then needed rulings only for implementation details, not for product questions.
- **How to check:** Ask: is there an approved design document, and is the first code commit dated after its approval?
- **Enforced by:** human gate

### P1.2 Test a costly assumption with a cheap spike outside the repository
- **Rule:** Before building on an assumption about an external service, run one small throwaway experiment (a spike) outside the repository, record what it showed as a decision, and delete its raw output.
- **Why (incident):** A single run against a real external service showed how its output was structured and how personal data appeared in it; both facts changed the design before anything was built on the wrong guess.
- **How to check:** Read `DECISIONS.md`: does each assumption about an external service cite a spike or primary documentation, and is no raw spike output tracked in git?
- **Enforced by:** human gate

### P1.3 Take provider facts from the provider's own documentation
- **Rule:** Read quotas, prices and limits of a service from the provider's primary documentation, not from third-party pages.
- **Why (incident):** A provider was recommended on the basis of a quota figure from a third-party page; the figure was wrong.
- **How to check:** Ask: does every provider fact in the design link to the provider's own documentation?
- **Enforced by:** human gate

### P1.4 Keep two layers of decisions: product decisions and implementation rulings
- **Rule:** Leave product decisions (Dn in `DECISIONS.md`) to the human, and let the agent make implementation rulings (Rn in `BUILD-LEDGER.md`) only when each ruling states what it costs if it is wrong.
- **Why (incident):** In one build the agent made 60 rulings, each with its cost if wrong; none had to be reversed, and the human could review them in one pass.
- **How to check:** Read `BUILD-LEDGER.md`: does every ruling have a "cost if wrong" line, and does none of them decide a product question?
- **Enforced by:** template + human gate

### P1.5 Classify data and threats while designing
- **Rule:** Record in the design which data is personal, who can read what, where secrets live and with which privileges each process runs.
- **Why (incident):** Containers running as the root user and a weak secret key format were found only in the final review, when fixing them was more expensive than at design time.
- **How to check:** Read the design: does it have a section on data classification, access and secrets, and was it approved before the build?
- **Enforced by:** human gate

### P1.6 Record every decision with seven fields, numbered in order and never deleted
- **Rule:** Write each decision in `DECISIONS.md` with all seven fields, number decisions without gaps, and change an old decision only by an "Update" note or a new decision that supersedes it.
- **Why (incident):** In one finished log, 70 of 73 decisions lacked at least one field (69 lacked the rejected options), and one heading that grouped three decisions hid them from every check.
- **How to check:** Run `python checks/check_docs.py .` and confirm exit 0.
- **Enforced by:** check_docs + contract hook

### P1.7 Mark assumptions and record what was not done, and why
- **Rule:** Keep an "Assumptions" section in `DECISIONS.md` for guesses marked as such and a "Not done (and why)" section for ideas considered and dropped.
- **Why (incident):** No single measured incident; the lesson from projects built so far is that an unmarked guess reads as a fact, and a dropped idea that is not written down gets proposed again.
- **How to check:** Run `python checks/check_docs.py .`; it fails when either section is missing.
- **Enforced by:** check_docs

### P1.8 Keep a glossary of domain terms and a diagram of how the parts talk
- **Rule:** Define every domain term in `GLOSSARY.md` and include in the approved design a diagram that shows which parts exchange which data.
- **Why (incident):** No single measured incident; in projects built so far, the human and the agent used the same word for different things until the terms were written down.
- **How to check:** Ask: does every domain term used in the design appear in `GLOSSARY.md`, and does the design contain a diagram?
- **Enforced by:** template + human gate

### P1.9 Keep the human's answers verbatim, with the decision each produced
- **Rule:** Store the human's answers to design questions word for word, in a separate file, each linked to the decision it produced.
- **Why (incident):** Verbatim answers settled later disagreements about what had actually been decided; a summary would have carried the agent's interpretation instead.
- **How to check:** Ask: can each decision be traced to a verbatim answer?
- **Enforced by:** human gate

### P1.10 Compute dates and rules in deterministic code and let a language model return only structured fields
- **Rule:** Keep date arithmetic and business rules in ordinary code, and use a language model only to fill structured fields that the code then checks.
- **Why (incident):** Moving date arithmetic out of the model turned every scheduling result into something a unit test could check.
- **How to check:** Search the code for prompts that ask the model to compute a date or apply a rule: is the answer none?
- **Enforced by:** CI
