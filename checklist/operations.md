# Operations: logging, monitoring, errors, retries and rollback

What keeps a running program understandable and recoverable once real people use it. Each item says when it applies, using the traits in [README.md](README.md).

### C-OPS-1 Write logs as an event stream to standard output

- **Rule:** The program writes its *log* (the running record of what it did) to standard output, one event per line, without buffering, and leaves storing and routing the log to the environment it runs in.
- **Why it matters:** A program that manages its own log files fills disks, loses records when a container is replaced, and hides its history in a place nobody looks.
- **Applies when:** container+web+scheduled
- **How to validate:** Start the program, perform one action, and record the matching log line appearing at once on standard output (for example in `docker logs`).
- **Companion:** none
- **Source:** The Twelve-Factor App, XI. Logs ("each running process writes its event stream, unbuffered, to stdout"), https://12factor.net/logs

### C-OPS-2 Keep secrets and personal data out of the logs

- **Rule:** Never write passwords, keys, payment details or other sensitive data to the log; data such as session tokens may appear only masked or hashed (turned into an unreadable fingerprint).
- **Why it matters:** Logs are copied to many places and read by many people, and they are rarely protected as carefully as the database.
- **Applies when:** always
- **How to validate:** Run the main flows with recognisable test values (a fake key, a fake e-mail address), then search the log output for those values; expect none.
- **Companion:** none
- **Source:** OWASP ASVS 5.0.0, V16 Security Logging and Error Handling, requirement 16.2.5 (logging by the data's protection level), https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x25-V16-Security-Logging-and-Error-Handling.md

### C-OPS-3 Log failed logins and refused access

- **Rule:** Record every failed login, every refused access and every rejected input with enough context (when, which user, what was attempted) to investigate later, and remove or escape line breaks in the logged values, so a user cannot add fake lines to the log.
- **Why it matters:** Attacks show up first as a run of failures; without these records you cannot tell that an attack happened or what it reached.
- **Applies when:** web
- **How to validate:** Make a failed login and a refused request, and record the two log lines they produced.
- **Companion:** none
- **Source:** OWASP Top 10:2025, A09 Security Logging and Alerting Failures, https://top10.owasp.org/2025/A09_2025-Security_Logging_and_Alerting_Failures/

### C-OPS-4 Monitor latency, traffic, errors and saturation, and alert on symptoms

- **Rule:** Measure the four *golden signals*: latency (how long requests take), traffic (how much is asked of the system), errors (how many requests fail) and saturation (how full the system is). Alert a person only for symptoms users feel and a person must act on.
- **Why it matters:** Without measurements you hear about an outage from users; with too many alerts people learn to ignore them, including the real one.
- **Applies when:** web+scheduled
- **How to validate:** Show where each of the four signals can be seen, and for each alert, the action a person takes when it fires. Trigger one alert on purpose and record that it arrived.
- **Companion:** none
- **Source:** Google SRE book, chapter "Monitoring Distributed Systems" (the four golden signals; "Every page should be actionable"), https://sre.google/sre-book/monitoring-distributed-systems/

### C-OPS-5 Fail closed and undo a half-finished change on error

- **Rule:** When an operation with several steps fails part-way, undo all of it (roll back the *transaction*, the group of changes that must succeed or fail together) and refuse the request, instead of continuing or patching it half-way.
- **Why it matters:** A change left half done (money taken but no order, a record half written) is harder to repair than a clean failure, and recovering part-way is where unrecoverable mistakes are made.
- **Applies when:** database
- **How to validate:** Make the last step of a multi-step operation fail on purpose in a test, and record that none of the earlier changes remain.
- **Companion:** pr-review-toolkit:silent-failure-hunter
- **Source:** OWASP Top 10:2025, A10 Mishandling of Exceptional Conditions (fail closed, roll back the whole transaction), https://top10.owasp.org/2025/A10_2025-Mishandling_of_Exceptional_Conditions/

### C-OPS-6 Catch every unhandled error in a last-resort handler

- **Rule:** Have one *last-resort error handler*: code that catches any error nothing else caught, logs it, and keeps the program running or stops it cleanly.
- **Why it matters:** An uncaught error either kills the whole process or disappears without a trace; both are worse than a logged, handled failure.
- **Applies when:** always
- **How to validate:** Raise an error on purpose in a place without its own handling and record the log line and what the program did next.
- **Companion:** pr-review-toolkit:silent-failure-hunter
- **Source:** OWASP ASVS 5.0.0, V16 Security Logging and Error Handling, requirement 16.5.4 (a "last resort" error handler), https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x25-V16-Security-Logging-and-Error-Handling.md

### C-OPS-7 Put a time limit on every call to another service

- **Rule:** Every call to a database, an outside API or another service has a *timeout* (a limit after which the program stops waiting), and a request that has run out of time stops doing further work.
- **Why it matters:** A call without a time limit can wait forever; enough of them use up every worker and the whole program stops answering.
- **Applies when:** paid-api+llm+database
- **How to validate:** List every outgoing call with its timeout value; point one at a service that never answers and record that the program gives up in time.
- **Companion:** none
- **Source:** Google SRE book, chapter "Addressing Cascading Failures", section on deadlines, https://sre.google/sre-book/addressing-cascading-failures/

### C-OPS-8 Retry with random backoff, a cap, and at one layer only

- **Rule:** When a call fails, retry only errors that can succeed later, wait longer each time with a random spread (*randomised exponential backoff*), stop after a fixed number of tries, and retry at one layer only.
- **Why it matters:** Retries without these limits multiply: three retries at each of three layers means 64 attempts, which can turn a short blip into an outage you cause yourself.
- **Applies when:** paid-api+llm+database
- **How to validate:** Show the retry settings for each outgoing call; make a dependency fail in a test and record the number and spacing of the attempts.
- **Companion:** none
- **Source:** Google SRE book, chapter "Addressing Cascading Failures" ("Always use randomized exponential backoff when scheduling retries"), https://sre.google/sre-book/addressing-cascading-failures/

### C-OPS-9 Make jobs safe to run twice

- **Rule:** Any job that may be retried after an interruption must give the same result when run twice (*idempotent*), for example by doing its work inside one transaction or by recording a unique key for each job before acting.
- **Why it matters:** Retries and restarts happen; a job that is not safe to repeat sends the e-mail twice, charges the card twice or writes the row twice.
- **Applies when:** scheduled+paid-api
- **How to validate:** Run the same job twice with the same input in a test and record that the outcome (rows, messages, charges) is the same as one run.
- **Companion:** none
- **Source:** The Twelve-Factor App, IX. Disposability ("all jobs are reentrant", "making the operation idempotent"), https://12factor.net/disposability

### C-OPS-10 Stop gracefully when asked to stop

- **Rule:** When the program receives the stop signal (SIGTERM, which servers and container platforms send before shutting down), it stops taking new work, finishes or hands back the work in progress, and exits.
- **Why it matters:** Every deployment and restart stops the program; without a graceful stop each one cuts off users mid-request and can leave work half done.
- **Applies when:** container+web+scheduled
- **How to validate:** Send the stop signal while a request or job is in progress (for example `docker stop`) and record that it completed or was returned to the queue.
- **Companion:** none
- **Source:** The Twelve-Factor App, IX. Disposability ("Processes shut down gracefully when they receive a SIGTERM signal"), https://12factor.net/disposability

### C-OPS-11 Be able to roll back to the previous release

- **Rule:** Every *release* (the built code plus its settings) has its own unique id and is never changed after it is made, so the previous one can be put back quickly when a new one misbehaves.
- **Why it matters:** When a release breaks production, going back to the last good one is the fastest repair, but only if that release still exists unchanged.
- **Applies when:** container+web+scheduled
- **How to validate:** Name the id of the current and the previous release, perform a rollback once (in a test environment if need be), and record how long it took.
- **Companion:** none
- **Source:** The Twelve-Factor App, V. Build, release, run ("Every release should always have a unique release ID", roll back to a previous release), https://12factor.net/build-release-run
