# Credits

This project stands on other people's work. Every outside project, format and source it relies on is named here with its author, where it comes from and its licence.

No text or code from these projects is copied into this repository. The skill names the companion skills and calls them when they are installed; their instructions stay in their own repositories, under their own licences. If text or code from another project is ever copied in, it must follow that project's licence and be credited on this page in the same change.

The facts below were read on 2026-11-10 from each project's own manifest, licence file or page. A licence named for a whole repository applies to the plugin inside it unless the plugin states otherwise.

## Companion skills

| Plugin | Author | Source | Licence | Used here |
|---|---|---|---|---|
| `superpowers` | Jesse Vincent | https://github.com/obra/superpowers | MIT ("Copyright (c) 2025 Jesse Vincent") | Brainstorming, plans, the build methods, the test-first loop, answering review, verification before claims, finishing a branch |
| `mattpocock-skills` | Matt Pocock | https://github.com/mattpocock/skills | MIT ("Copyright (c) 2026 Matt Pocock") | Research, grilling the owner at Stages 0 and 1, glossary, module boundaries, prototypes, test placement, hard-bug diagnosis, branch review |
| `andrej-karpathy-skills` | forrestchang, from Andrej Karpathy's observations on the pitfalls of coding with language models | https://github.com/forrestchang/andrej-karpathy-skills | MIT (its plugin manifest) | The agent's habits: state assumptions, keep it simple, change only what is needed |
| `anthropic-skills` | Anthropic | https://claude.ai (provided with some Claude accounts; no public repository) | No licence published with it | Deep research across sources |
| `property-based-testing` | Henrik Brodin, Trail of Bits | https://github.com/trailofbits/skills/tree/main/plugins/property-based-testing | CC BY-SA 4.0 (the repository's licence) | Generated inputs over the whole input range |
| `mutation-testing` | Trail of Bits | https://github.com/trailofbits/skills/tree/main/plugins/mutation-testing | CC BY-SA 4.0 (the repository's licence) | Proving the tests catch breakage |
| `differential-review` | Omar Inuwa, Trail of Bits | https://github.com/trailofbits/skills/tree/main/plugins/differential-review | CC BY-SA 4.0 (the repository's licence) | Security-focused review of what changed |
| `insecure-defaults` | Trail of Bits | https://github.com/trailofbits/skills/tree/main/plugins/insecure-defaults | CC BY-SA 4.0 (the repository's licence) | Finding insecure default settings |
| `spec-to-code-compliance` | Omar Inuwa, Trail of Bits | https://github.com/trailofbits/skills/tree/main/plugins/spec-to-code-compliance | CC BY-SA 4.0 (the repository's licence) | Checking documents against the code |
| `supply-chain-risk-auditor` | Eric Quintero, in the Trail of Bits skills repository | https://github.com/trailofbits/skills/tree/main/plugins/supply-chain-risk-auditor | CC BY-SA 4.0 (the repository's licence) | Auditing dependencies for supply-chain risk |
| `audit-context-building` | Omar Inuwa, Trail of Bits | https://github.com/trailofbits/skills/tree/main/plugins/audit-context-building | CC BY-SA 4.0 (the repository's licence) | Preparing the agent to read an existing codebase |
| `pr-review-toolkit` | Anthropic | https://github.com/anthropics/claude-plugins-official/tree/main/plugins/pr-review-toolkit | Apache 2.0 (its licence file) | Agents that hunt silent failures and gaps in tests |
| `claude-md-management` | Anthropic | https://github.com/anthropics/claude-plugins-official/tree/main/plugins/claude-md-management | Apache 2.0 (its licence file) | Updating the agent's project instructions after the retro |
| `deepeval` | Confident AI | https://github.com/confident-ai/deepeval | Apache 2.0 (its licence file) | Evaluating the output of a language model |
| `example-skills` | Anthropic | https://github.com/anthropics/skills | Apache 2.0 for the `webapp-testing` skill used here (its licence file); each skill carries its own | Browser-app testing |
| `repo-kickoff` | Sarp Esenyel, the author of this project | https://github.com/Sarpes/repo-kickoff | MIT | Starting a repository, its private companion, and auditing documents against code |
| `run` | Anthropic, built into Claude Code | https://code.claude.com/docs | Part of Claude Code; no separate licence | Running the real thing |
| `security-review` | Anthropic, built into Claude Code | https://code.claude.com/docs | Part of Claude Code; no separate licence | Security review |

## Formats and ideas

| What | Author | Source | Licence | Used here |
|---|---|---|---|---|
| Keep a Changelog 1.1.0 | Olivier Lacan (created and maintained), designed by Tyler Fortune | https://keepachangelog.com/en/1.1.0/ | MIT | The layout of `CHANGELOG.md`: an Unreleased list and dated version sections |
| Documenting Architecture Decisions (Architecture Decision Records), 2011-11-15 | Michael Nygard | https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions | Not stated on the page | The idea behind `DECISIONS.md`: one record per decision with its context. This project's seven fields (options, rejected, cost, what would change it) extend it |
| Claude Code plugin documentation | Anthropic | https://code.claude.com/docs/en/plugins-reference | Not stated on the page | The plugin and marketplace manifests, and the facts quoted in `docs/plans/2026-11-10-companion-install.md` |

## Checklist sources

Every item in `checklist/` cites the published source it rests on, with the address of the page that was read: OWASP, NIST, the Google SRE book and The Twelve-Factor App. The full list of sources and the reason they were chosen are in [checklist/README.md](checklist/README.md) and decision D19.

## Principles

The principles in `principles/` rest on incidents in the author's own projects. They name no outside project.
