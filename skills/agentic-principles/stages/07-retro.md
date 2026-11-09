# Stage 7: Retro

## Purpose

Make the next project cheaper than this one, by turning each mistake into something that outlasts this session.

## Do

1. Read every "Where the AI was wrong" entry in `AI-Agents.md`.
2. Give each entry one outcome: a rule, a template change, or a recorded "won't fix" with its reason (`principles/07-retro.md`, P7.1).
3. Write the outcomes in a `## Retro` section of `AI-Agents.md`.
4. A rule that should hold every time becomes a check with a test, not a sentence. Ask the owner before adding one to the project's instructions.
5. List the overrides still open, and ask the owner whether to close any.

## Companions

| Capability | Companion | If it is missing |
|---|---|---|
| Updating agent instructions | `/claude-md-management:revise-claude-md` | edit the project's instructions by hand |

## Gate

`AI-Agents.md` with a filled `## Retro` section, named as `file:` evidence in `STAGES.md`, then `python checks/check_gates.py`.

## Small

A short retro: every entry still gets one outcome.
