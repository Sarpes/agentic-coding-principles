# Dependencies

A *dependency* is code written by someone else that your project uses, such as a library installed with pip or npm. Each item says when it applies, using the traits in [README.md](README.md).

### C-DEP-1 Declare every dependency exactly in one list

- **Rule:** List every dependency, with its exact version, in the project's dependency file (the *manifest*, such as `requirements.txt`, `pyproject.toml` or `package.json`), and install it in an isolated environment so nothing leaks in from the machine.
- **Why it matters:** A dependency that is only installed on your machine makes the project fail everywhere else, and an unpinned version can change under you overnight.
- **Applies when:** always
- **How to validate:** Install into a fresh isolated environment from the manifest alone and run the tests; record that they pass.
- **Companion:** none
- **Source:** The Twelve-Factor App, II. Dependencies ("declares all dependencies, completely and exactly"), https://12factor.net/dependencies

### C-DEP-2 Keep an inventory of all dependencies, including indirect ones, and remove the unused

- **Rule:** Keep a current list of every component the project contains, including the dependencies your dependencies pull in (*transitive dependencies*), for example a lock file or an SBOM (software bill of materials). Remove dependencies that are not used.
- **Why it matters:** Most of the code you ship is indirect; you cannot react to a vulnerability in a component you do not know you have, and every unused one is attack surface for nothing.
- **Applies when:** always
- **How to validate:** Show the lock file or SBOM and the date it was generated; for each direct dependency, name the code that uses it.
- **Companion:** supply-chain-risk-auditor:supply-chain-risk-auditor
- **Source:** OWASP Top 10:2025, A03 Software Supply Chain Failures (SBOM, transitive dependencies, "removing unused dependencies"), https://top10.owasp.org/2025/A03_2025-Software_Supply_Chain_Failures/

### C-DEP-3 Check dependencies for known vulnerabilities automatically

- **Rule:** Run a tool that compares your dependencies with public lists of known security holes (*vulnerabilities*) on every change, and fix or record each finding.
- **Why it matters:** New vulnerabilities are published every day in code you did not write; a check that runs by itself catches them without anyone remembering to look.
- **Applies when:** always
- **How to validate:** Record the command (for example `pip-audit` or `npm audit`), its date and its result, and the decision for each finding.
- **Companion:** supply-chain-risk-auditor:supply-chain-risk-auditor
- **Source:** NIST SP 800-218 (SSDF 1.1), task PW.4.4, examples 1 and 2 ("Build into the toolchain automatic detection of known vulnerabilities"), https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-218.pdf

### C-DEP-4 Replace dependencies that are no longer maintained

- **Rule:** Check that each dependency is still maintained and has not reached its end of life (the date after which its makers stop releasing fixes for it); for any that is abandoned, write down a plan (replace it, or own the risk).
- **Why it matters:** An abandoned library never gets security fixes, so its next vulnerability stays open for good.
- **Applies when:** always
- **How to validate:** For each direct dependency, record the date of its last release; list those that look abandoned (for example, no release in the past year) and the plan for each.
- **Companion:** supply-chain-risk-auditor:supply-chain-risk-auditor
- **Source:** NIST SP 800-218 (SSDF 1.1), task PW.4.4, examples 4 and 5 (actively maintained, plan for components no longer maintained), https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-218.pdf
