# Deviations from the submitted documents

This log records implementation differences from the SRS, SAD or Test Plan. The entries below are the historical Sprint 1 deviations already recorded by the team. Add new entries only after confirming the difference against the submitted baseline and current implementation.

| Date | Story | Document and section | What the document says | What we did instead | Reason |
|---|---|---|---|---|---|
| 22-10-2026 | Sprint 1 (all) | SRS 3.1 User interface; SAD 4.5 UX design | A browser-based HTML/CSS/JavaScript interface for Customer, Teller and Admin | Sprint 1 was demonstrated through the FastAPI interactive API page (`/docs`); the browser UI was deferred to Sprint 2 | Sprint 1 stories focused on backend services; UI work was planned under US-14 and US-15 |
| 22-10-2026 | US-17, US-18 | SAD 4.3 API design | Request field `accountId` for deposit and withdrawal, with no type stated | `accountId` is the 10-digit account number represented as a string; `fromAccount` and `toAccount` use the same convention | The account number is unique (BR-06) and is the identifier users know |
| 22-10-2026 | US-17, US-18, US-19 | SAD 4.3 and 4.4 | An error list per endpoint (for example 400, 403, 409 and 422) | Additional responses include `404 ACCOUNT_NOT_FOUND`, `400 VALIDATION_ERROR` for malformed requests and `400 INVALID_TRANSFER` for same-account transfers; errors use the standard JSON format | The SAD list is not exhaustive; the additional codes make failures explicit |
| 22-10-2026 | US-17, US-18, US-19 | SAD 4.3 API design | Responses return balance, with no type stated | Money amounts are returned as decimal strings, for example `1500.00` | Avoids floating-point rounding errors |
