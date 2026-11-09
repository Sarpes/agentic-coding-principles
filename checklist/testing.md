# Testing techniques

Ways of testing that catch what simple tests miss. A *test* is a small program that runs your code and checks the result automatically. Each item says when it applies, using the traits in [README.md](README.md).

### C-TEST-1 Write integration tests for the parts that talk to each other

- **Rule:** Besides tests of single functions, write *integration tests*: tests that run several parts together (for example the code and its database) and check the combined result.
- **Why it matters:** Each part can pass its own tests while the parts still disagree with each other, for example about a field name or a date format.
- **Applies when:** always
- **How to validate:** List the places where two parts hand data to each other; for each, name the test that runs both parts together and show it passing.
- **Companion:** run
- **Source:** Google SRE book, chapter "Testing for Reliability" (integration tests), https://sre.google/sre-book/testing-reliability/

### C-TEST-2 Turn every fixed bug into a regression test

- **Rule:** When a bug is fixed, add a test that fails on the old code and passes on the fixed code, and keep it in the test suite (the full set of tests).
- **Why it matters:** A *regression* is an old bug coming back after a later change. Without a test that remembers it, nothing notices.
- **Applies when:** always
- **How to validate:** For each bug fixed since the last release, name its test; check out the commit before the fix, run that test, and see it fail.
- **Companion:** superpowers:test-driven-development
- **Source:** NIST SP 800-218 (SSDF 1.1), task PW.8.2, example 3 "Incorporate tests for previously reported vulnerabilities", https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-218.pdf

### C-TEST-3 Fuzz test the input handling

- **Rule:** Feed the code that reads outside input large amounts of generated, malformed and random input (*fuzz testing*) and check that it never crashes or misbehaves.
- **Why it matters:** People write tests for the inputs they expect; attackers and broken clients send the ones nobody expected.
- **Applies when:** web
- **How to validate:** Run a fuzz or property-based test (a test that generates many inputs from a rule) against each input handler; record the number of inputs tried and that none crashed.
- **Companion:** property-based-testing:property-based-testing
- **Source:** NIST SP 800-218 (SSDF 1.1), task PW.8.2, example 5 "Use fuzz testing tools to find issues with input handling", https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-218.pdf

### C-TEST-4 Load test each part until it breaks

- **Rule:** Send more and more requests to each part (*load testing*) until it fails, and watch how it fails and whether it recovers on its own when the load drops.
- **Why it matters:** Without this you learn the limit of your service from real users on its worst day, and a part that crashes instead of slowing down can take others with it.
- **Applies when:** web
- **How to validate:** Record, for each part, the request rate at which it started failing, what the failure looked like, and whether it recovered without a person stepping in.
- **Companion:** none
- **Source:** Google SRE book, chapter "Addressing Cascading Failures", section "Load test components until they break", https://sre.google/sre-book/addressing-cascading-failures/

### C-TEST-5 Inject failures on purpose and record how to repeat them

- **Rule:** Make the things your program depends on fail on purpose (stop the database, cut the network, make an outside service slow) and check that your program behaves as designed. Record the random seed or steps of each run so a failure can be repeated.
- **Why it matters:** Every outside service fails sometimes; code that has never seen the failure usually handles it badly, and a failure you cannot repeat cannot be fixed with confidence.
- **Applies when:** database+paid-api+llm
- **How to validate:** For each outside dependency, record one run with that dependency failing, the program's behaviour, and the seed or steps that reproduce it.
- **Companion:** none
- **Source:** Google SRE book, chapter "Testing for Reliability", statistical tests (fuzzing, Chaos Monkey) and logging the seed, https://sre.google/sre-book/testing-reliability/

### C-TEST-6 Start the project from a clean clone with the documented commands only

- **Rule:** On a machine or folder that has never run the project, clone the repository and set it up using only the commands written in the README; every dependency must come from the project's own list, not from what happens to be installed.
- **Why it matters:** A project that only runs on the machine it was built on will fail for the next person, and for the server it is deployed to.
- **Applies when:** always
- **How to validate:** Clone into an empty folder (or a fresh container), run the documented commands in order, and record that the tests pass with no extra steps.
- **Companion:** run
- **Source:** The Twelve-Factor App, II. Dependencies ("never relies on implicit existence of system-wide packages"), https://12factor.net/dependencies

### C-TEST-7 Test against the same kind of backing services as production

- **Rule:** Run tests against the same type and version of database, queue or cache (*backing services*) as production, not a lighter stand-in.
- **Why it matters:** Small differences between two databases make code that passed every test fail in production.
- **Applies when:** database
- **How to validate:** Compare the database name and version used by the tests with the one in production and record that they match.
- **Companion:** none
- **Source:** The Twelve-Factor App, X. Dev/prod parity ("the same type and version of each of the backing services"), https://12factor.net/dev-prod-parity
