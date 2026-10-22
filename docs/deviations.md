# Deviations from the submitted documents

Log every place where the implementation differs from the SRS, SAD or Test Plan. These are explained at the final demo.

| Date | Story | Document and section | What the document says | What we did instead | Reason |
|---|---|---|---|---|---|
| 22-10-2026 | Sprint 1 (all) | SRS 3.1 User interface; SAD 4.5 UX design | A browser-based HTML/CSS/JavaScript interface for Customer, Teller and Admin | Sprint 1 is demonstrated through the FastAPI interactive API page (/docs); there are no HTML screens yet | Sprint 1 stories cover the backend services; the UI is planned for Sprint 2 (US-14, US-15) |
| 22-10-2026 | US-17, US-18 | SAD 4.3 API design | Request field accountId for deposit and withdrawal, with no type stated | accountId is the 10-digit account number (a string); fromAccount and toAccount follow the same convention | The account number is unique (BR-06) and is the identifier users know |
| 22-10-2026 | US-18 | SRS BMS-F-021, BR-02 | Maximum withdrawal of Rs 50,000 per account per day | The day is the UTC calendar day, not the local (IST) day | Simplest consistent definition; a local-time boundary can be added later |
| 22-10-2026 | US-17, US-18, US-19 | SAD 4.3 and 4.4 | An error list per endpoint (for example 400, 403, 409, 422) | Extra codes are also returned: 404 ACCOUNT_NOT_FOUND, 400 VALIDATION_ERROR for malformed requests and 400 INVALID_TRANSFER for same-account transfers. All errors use the standard JSON format (code, message, timestamp, traceId) | The SAD list is not exhaustive; the extra codes make failures explicit |
| 22-10-2026 | US-17, US-18, US-19 | SAD 4.3 API design | Responses return balance, with no type stated | Money amounts are returned as decimal strings, for example "1500.00" | Avoids the rounding errors floating-point numbers can cause |
| 22-10-2026 | US-01, US-03 (pending) | SRS BMS-F-003, BMS-SR-004 | The server enforces the caller's role on every request | Until Member 1's login and role checks are merged, a temporary stub accepts requests (role taken from an optional header) | Lets the team build in parallel. Delete this row if US-01 and US-03 are merged before the demo |