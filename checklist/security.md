# Security

Practices that keep other people from reading, changing or breaking what they should not. Each item says when it applies, using the traits in [README.md](README.md).

### C-SEC-1 Threat model the critical flows and test the misuse cases

- **Rule:** For the critical flows (logging in, deciding who may do what, payments, anything that changes data), write down how someone could abuse each one (*threat modelling*), as a misuse case next to each use case, and write a test for each misuse case.
- **Why it matters:** A design that only describes what honest users do leaves the dishonest paths untested, and those are the ones attackers take.
- **Applies when:** always
- **How to validate:** Show the list of misuse cases for each critical flow and, for each, the test that tries it and the result.
- **Companion:** security-review
- **Source:** OWASP Top 10:2025, A06 Insecure Design ("Write unit and integration tests to validate that all critical flows are resistant to the threat model"), https://top10.owasp.org/2025/A06_2025-Insecure_Design/

### C-SEC-2 Deny access by default and decide it on the server

- **Rule:** Everything that is not public is refused unless a rule allows it (*deny by default*), and the decision is made in server code, never only in the browser or app.
- **Why it matters:** Checks done in the browser can be skipped by anyone who sends requests directly; a forgotten rule should lock a door, not leave it open.
- **Applies when:** web
- **How to validate:** Call each non-public address without logging in and as a user without the right role; record that every call is refused. Keep these calls as tests.
- **Companion:** security-review
- **Source:** OWASP Top 10:2025, A01 Broken Access Control ("Except for public resources, deny by default"), https://top10.owasp.org/2025/A01_2025-Broken_Access_Control/

### C-SEC-3 Let each user reach only their own records

- **Rule:** When a request names a record (for example an order number in the address), check that the logged-in user may see that particular record, not only that they are logged in.
- **Why it matters:** Changing a number in the address to read someone else's data is one of the most common attacks; it is called IDOR (insecure direct object reference).
- **Applies when:** web+personal-data
- **How to validate:** Log in as user A and request a record that belongs to user B; record that it is refused. Keep this as a test.
- **Companion:** security-review
- **Source:** OWASP ASVS 5.0.0, V8 Authorization, requirement 8.2.2 (data-specific access, IDOR and BOLA), https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x17-V8-Authorization.md

### C-SEC-4 Keep user input out of database and shell commands

- **Rule:** Never build a database query or a shell command by pasting user input into text. Use *parameterised queries* (the input is passed separately from the command) or a library that does this for you.
- **Why it matters:** Pasted input can carry commands of its own (*injection*), which the database or shell then runs.
- **Applies when:** database+web
- **How to validate:** Search the code for queries or commands built with string joining or formatting; expect none. Send a value such as a single quote to each input and record that nothing breaks.
- **Companion:** security-review
- **Source:** OWASP Top 10:2025, A05 Injection (safe API, parameterised interface), https://top10.owasp.org/2025/A05_2025-Injection/

### C-SEC-5 Validate input against what is allowed

- **Rule:** Check every input against what it is allowed to be (an *allow list* of values, patterns, lengths and ranges), and reject the rest, instead of trying to list what is forbidden.
- **Why it matters:** A list of forbidden inputs is never complete; a list of allowed ones is short and can be tested.
- **Applies when:** web
- **How to validate:** For each input, name the rule that checks it, and show a test sending a value just outside the allowed range being rejected.
- **Companion:** security-review
- **Source:** OWASP ASVS 5.0.0, V2 Validation and Business Logic, requirement 2.2.1 (positive validation against an allow list), https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x11-V2-Validation-and-Business-Logic.md

### C-SEC-6 Keep secrets out of the code

- **Rule:** Passwords, API keys and other *secrets* live in the environment the program runs in (for example environment variables or a secrets store), never in the code or in files tracked by git.
- **Why it matters:** Code is copied, shared and published; a secret inside it leaks with it and stays in the git history even after it is deleted.
- **Applies when:** always
- **How to validate:** Ask the test the source gives: could the repository be made public right now without giving away any credential? Run a secret scan over the history and record that it finds nothing.
- **Companion:** security-review
- **Source:** The Twelve-Factor App, III. Config ("whether the codebase could be made open source at any moment, without compromising any credentials"), https://12factor.net/config

### C-SEC-7 Keep secrets out of build artefacts and container images

- **Rule:** Secrets are given to the program when it starts, never copied into what the build produces (*build artefacts*, such as a container image or a package).
- **Why it matters:** Images and packages are stored and shared; anyone who can pull one can read every file inside it.
- **Applies when:** container
- **How to validate:** Build the image, list its files and environment settings, and record that no key, password or secret file is in it.
- **Companion:** security-review
- **Source:** OWASP ASVS 5.0.0, V13 Configuration, requirement 13.3.1 ("Secrets must not be included in application source code or included in build artifacts"), https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x22-V13-Configuration.md

### C-SEC-8 Turn off debug output and default accounts before going live

- **Rule:** In production, debug modes are off, errors show users a plain message without technical detail (no *stack trace*, the list of code lines that led to the error), default accounts and passwords are removed or changed, and unused features are switched off.
- **Why it matters:** Default passwords are public knowledge, and error details tell an attacker what software you run and where it is weak.
- **Applies when:** web+container+database
- **How to validate:** Start the production configuration, trigger an error and record what the user sees; list every account and record that none has a default password.
- **Companion:** /insecure-defaults:audit
- **Source:** OWASP Top 10:2025, A02 Security Misconfiguration (hardening, minimal platform, default accounts, error messages), https://top10.owasp.org/2025/A02_2025-Security_Misconfiguration/
