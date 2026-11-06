# Stage 6: Own

**Gate:** the human can explain every module and has changed at least one by hand.

### P6.1 Make sure the human can explain every module and has changed one by hand
- **Rule:** Before calling the project finished, have the human explain each module aloud and make at least one change to the code by hand, with the agent only guiding.
- **Why (incident):** After a build done mostly by AI, the owner could explain every decision but had not yet changed any of the code by hand.
- **How to check:** Run `git log --author="<the human's name>"`: is there at least one commit the human wrote by hand, and can the human explain each module without notes?
- **Enforced by:** human gate
