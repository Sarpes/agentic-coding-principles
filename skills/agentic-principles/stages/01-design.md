# Stage 1: Design

## Purpose

Settle what is being built, and what is deliberately not being built, before any code exists. A wrong decision costs a sentence here and a rewrite later.

## Do

1. Find out what is wanted in question rounds. A question may show a recommended answer, but the owner still answers in their own words: a bare yes does not accept the recommendation. Write no code until the owner has approved the written design (`principles/01-design.md`, P1.1).
2. Write goals, non-goals and anti-goals. An anti-goal is an outcome that counts as failure even if the software works.
3. Classify the data and the threats in the design, as P1.5 asks.
4. Keep product decisions with the owner. Record each in `DECISIONS.md` with its seven fields and the options rejected (P1.4, P1.6).
5. Test a costly assumption with a cheap throwaway experiment outside the repository (P1.2).
6. Start `ARCHITECTURE.md`: the parts and how they connect. It grows at every stage after this one.
7. Keep four habits through Stages 1 to 3: state assumptions aloud, build the simplest thing that works, change only what the task needs, and define how success will be checked.
8. When the design is approved, **grill the owner on it**, on every project, Small or Full: run the grilling companion, which challenges the design question by question. Write each challenge, the owner's own answer and what it changed (a `D` id, or `kept`) in `GRILLING.md`, section `## Design`, with the line `Grilled with:` naming the skill, or `fallback: written challenges` when it is not installed. At least 3 answered challenges. Then close this stage. The planning companion is called at Stage 2, by this skill and not by the design companion.

## Companions

| Capability | Companion | If it is missing |
|---|---|---|
| Finding out what is wanted | `superpowers:brainstorming` | question rounds from `principles/01-design.md` |
| Grilling the owner on the design (every project) | `mattpocock-skills:grilling` | written challenges, asked one at a time and answered by the owner |
| Terms and glossary | `mattpocock-skills:domain-modeling` | `templates/GLOSSARY.md` |
| Module boundaries | `mattpocock-skills:codebase-design` | an owner-readable note in the design |
| Cheap throwaway experiment | `mattpocock-skills:prototype` | a spike outside the repository |
| Agent behaviour | `andrej-karpathy-skills:karpathy-guidelines` | the four habits in step 7 |

On Full, do not accept the design companion's offer to skip its questions. On every project the owner answers the grilling in their own words: a one-word yes suits someone in a hurry too well. Decisions go in `DECISIONS.md`, not `docs/adr/`.

## Gate

`DECISIONS.md` with at least one complete entry, a design file under `docs/` approved by the owner, and `GRILLING.md` whose `## Design` section has its `Grilled with:` line and at least 3 answered challenges. Name `file:GRILLING.md` in the evidence. Approval rests on trust: record who approved and when, in the design file.

A design the agent writes from one sentence of the owner's, with no questions and no rejected options, does not meet this gate. If the owner does not want the questions, the honest record is an override.

## Small

A short note in `DECISIONS.md` replaces the written design. The grilling still runs, with the same minimum of 3 answered challenges.
