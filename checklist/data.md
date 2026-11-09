# Data: migrations, backups and personal data

How stored data is changed, protected against loss, and kept to what is needed. Each item says when it applies, using the traits in [README.md](README.md).

### C-DATA-1 Ship database migrations with the code and run them against the release

- **Rule:** A *migration* (a script that changes the structure of the database, such as adding a column) lives in the repository with the code, and is run as a one-off command using the same code and settings as the release it belongs to.
- **Why it matters:** A database changed by hand, or by a script that is not part of the release, drifts away from what the code expects, and the next deployment breaks.
- **Applies when:** database
- **How to validate:** Create an empty database, run all migrations with the documented command, then run the tests against it; record that they pass.
- **Companion:** none
- **Source:** The Twelve-Factor App, XII. Admin processes ("Admin code must ship with application code"), https://12factor.net/admin-processes

### C-DATA-2 Test restores, not only backups, and keep backups apart from replicas

- **Rule:** Restore a backup into a separate place on a schedule and check that the data is complete. A *replica* (a live copy kept in sync) does not count as a backup, because it copies mistakes and deletions too.
- **Why it matters:** Nobody wants backups; what people want are restores. A backup that has never been restored may be empty, incomplete or too slow to use.
- **Applies when:** database
- **How to validate:** Record the date of the last restore test, how long it took, and a check that the restored data matched (for example row counts).
- **Companion:** none
- **Source:** Google SRE book, chapter "Data Integrity" ("what people really want are restores"), https://sre.google/sre-book/data-integrity/

### C-DATA-3 Return and keep only the personal data the feature needs

- **Rule:** Each feature returns only the personal data it needs, and shows sensitive values masked (for example the last four digits of a card) unless the user asks to see them.
- **Why it matters:** Data that is never sent cannot leak; every extra field in a reply is something an attacker or a log can pick up.
- **Applies when:** personal-data
- **How to validate:** For each reply that holds personal data, list its fields and the reason each is needed; remove any without a reason.
- **Companion:** none
- **Source:** OWASP ASVS 5.0.0, V14 Data Protection, requirement 14.2.6 (return only the minimum required sensitive data), https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x23-V14-Data-Protection.md

### C-DATA-4 Keep sensitive data out of web addresses and browser storage

- **Rule:** API keys, session tokens (the value a site gives a browser after login, so later requests count as that user) and personal data never travel in the web address (*URL*) or its query string (the part of a web address after the question mark), and are not kept in browser storage (data a site saves inside the browser, such as local storage, which scripts on the page can read), apart from the session token.
- **Why it matters:** Web addresses are saved in browser history, server logs and shared links; browser storage can be read by any script that runs on the page.
- **Applies when:** web
- **How to validate:** Use the main flows with the browser's developer tools open and record that no key, token or personal value appears in any address or in local storage.
- **Companion:** none
- **Source:** OWASP ASVS 5.0.0, V14 Data Protection, requirements 14.2.1 and 14.3.3, https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x23-V14-Data-Protection.md
