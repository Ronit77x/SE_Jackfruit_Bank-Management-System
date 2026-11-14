# Transaction API integration (PR #64)

Opening an account now adds its opening-deposit notification inside the existing
US-08 database transaction. The customer, account, login (for a first account),
opening deposit, notification and account-opening audit record commit together.
A notification storage failure rolls all of them back. No independent commit is
introduced into the account service. This integration touches Vijay's US-08
service and should be reviewed with him; he does not need to implement a duplicate
notification call in his old branch.

Statement downloads use a fail-closed audit policy: the API returns the CSV only
after the masked `STATEMENT_DOWNLOAD` audit entry has committed. If audit storage
fails, the session is rolled back and the API returns HTTP 503 with code
`STATEMENT_AUDIT_UNAVAILABLE`, without a CSV or download header. A later retry can
succeed normally. A successful API response is audited; this cannot prove that a
client received every byte after a network disconnect.

The focused integration tests cover new Savings and Current accounts, another
account for an existing customer, atomic rollback for both new and existing
customers, and statement audit failure/retry. Existing large-history tests retain
the 1,500-row CSV/totals and pagination regressions. Current main's ASCII account
validation and rejection of extra money-request fields are preserved.

Customer-facing history and statement pages remain separate UI work. Notification
listing remains Vaibhav's part of US-29. This API PR alone does not establish that
those complete user stories are ready to close.
