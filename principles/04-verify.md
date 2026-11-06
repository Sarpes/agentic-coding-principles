# Stage 4: Verify

**Gate:** real integrations run end to end, and a fresh clone starts with the documented commands.

### P4.1 Measure the state again after cleaning up
- **Rule:** After deleting or stopping anything, measure the state again instead of trusting the command that did it.
- **Why (incident):** A background loop survived being stopped and silently recreated data volumes that had just been deleted; only a second measurement showed it.
- **How to check:** After a clean-up, list the processes, containers and volumes again: is everything that was removed still absent?
- **Enforced by:** human gate
