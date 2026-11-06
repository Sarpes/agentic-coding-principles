# Stage 6: Own

**Gate:** the human can explain every module and has changed at least one by hand.

### P6.1 Make sure the human can explain every module and has changed one by hand
- **Rule:** Before calling the project finished, have the human explain each module aloud and make at least one change to the code by hand, with the agent only guiding.
- **Why (incident):** After a build done mostly by AI, the owner could defend every decision but had not yet changed the code by hand, which is exactly what a live coding session tests.
- **How to check:** Ask the human: can you explain each module without notes, and which commit did you write by hand?
- **Enforced by:** human gate
