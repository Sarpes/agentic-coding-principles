# Plan: installing the companion skills

Status: saved for later, not started (owner's decision, 2026-11-10). Build option B first, then option A after the sandbox test in step A1.

## Problem

The skill names 30 capabilities in `skills/agentic-principles/companions.json`, each with a primary skill, alternatives and a fallback. A new user has to install the helper plugins one by one, from four marketplaces. Today `check_companions.py` only reports `MISSING <name>`.

## What Claude Code offers (read 2026-11-10 from the plugin documentation)

- `plugin.json` has a `dependencies` field: `"name"`, `"name@marketplace"` or `{ "name", "marketplace", "version" }`. Installing the plugin installs its dependencies.
- A dependency from another marketplace installs only when the hosting marketplace lists that marketplace in `allowCrossMarketplaceDependenciesOn` in `marketplace.json`.
- Dependencies are hard: when one declared in `plugin.json` cannot be installed, "the install completes without the dependency and your plugin then fails to load".
- A plugin whose manifest holds only `name` and `dependencies` is valid: a bundle ("Bundle plugins for a team").
- No marketplace field installs a plugin without the user asking.

Not verified: whether the user must add the other marketplaces (trailofbits and the rest) by hand before a cross-marketplace dependency installs.

## Rejected: dependencies on the skill itself

Declaring the helpers as dependencies of `agentic-engineering-principles` would switch the whole skill off when any one helper fails to install. That breaks the design: every capability has a fallback, so the skill must load with none of them.

## Option B (first): install commands from the checker

- `check_companions.py --install-commands` prints, for each missing companion that a marketplace provides, the `/plugin marketplace add <owner/repo>` line (once per marketplace) and the `/plugin install <plugin>@<marketplace>` line.
- Companions that cannot be installed this way are listed as such, with the fallback that applies: `repo-kickoff` (local skill), `anthropic-skills` (provided with some Claude accounts), built-in commands (`run`, `security-review`).
- `--stage N` limits the list to the companions that stage uses, so the session start can offer only what the current stage needs.
- Nothing is installed by the script. The agent shows the lines; the owner runs them with the `!` prefix, or the agent runs them after the owner's OK.
- Needs: a marketplace source for each plugin (a new field in `companions.json`, or a table in the script checked by a test against the README's marketplace list).
- Tests: a fixture plugin cache with some companions present; the output names exactly the missing ones; one `marketplace add` per marketplace; the non-installable ones are never printed as install lines.

## Option A (after B): a bundle plugin

- A second plugin in this repository's marketplace, `agentic-engineering-principles-full`, whose `plugin.json` holds only `name`, `version`, `description` and `dependencies`: the core plugin plus every installable companion plugin.
- `marketplace.json` gains `allowCrossMarketplaceDependenciesOn`: `claude-plugins-official`, `trailofbits`, `karpathy-skills`, `anthropic-agent-skills`.
- The core plugin keeps no dependencies, so a failed bundle install never disables the skill.
- A test keeps the bundle's list equal to the installable plugins in `companions.json`.

Steps:
- A1. Sandbox test before any code: a throwaway marketplace with a bundle that depends on one plugin from another marketplace. Measure whether the install succeeds without adding that marketplace first, and what the user sees when it fails.
- A2. Add the bundle and the allowlist; `claude plugin validate` on both manifests.
- A3. README: the two install commands (core alone, or the full set) and what each gives.

Cost: the bundle installs every helper, including ones a project never uses (an LLM evaluator on a project with no LLM), and a new companion needs a new bundle version.

## Order and status

| Step | Status |
|---|---|
| B: `--install-commands` and `--stage` | not started |
| A1: sandbox test of cross-marketplace bundle install | not started |
| A2, A3: bundle plugin and README | not started, depends on A1 |
