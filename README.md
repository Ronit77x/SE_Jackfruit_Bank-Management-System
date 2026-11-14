# SE_Jackfruit — Bank Management System

Software Engineering mini-project: a web-based **Bank Management System (BMS)** for one bank, with three roles — **Customer**, **Teller** and **Admin** — covering account opening, deposits, withdrawals, fund transfers, statements, audit logging and daily reports.

## Team

| Member | Role in documents | GitHub |
|---|---|---|
| Member 1 | SRS owner & integration | @ |
| Member 2 | Test Plan & test cases | @vijaykumar-187 |
| Member 3 | Architecture & design (SAD), repo owner | @Ronit77x |
| Member 4 | Security, NFRs, traceability (RTM), backlog check | @ |

## Technology stack (fixed baseline)

Python 3 + FastAPI (REST/JSON) · SQLite via SQLAlchemy · simple HTML/CSS/JavaScript web UI · pytest · GitHub Actions · layered architecture.

## Repository structure

```
docs/
  srs/          Final integrated SRS (Member 1)
  srs-parts/    SRS section files that feed the final SRS (Members 2, 3, 4)
  test-plan/    Test Plan with test cases (Member 2)
  sad/          Software Architecture & Design Specification (Member 3)
  diagrams/     UML diagrams (PNG + source files)
  backlog/      Sprint plan and backlog coverage check (Member 4)
app/ Application code (FastAPI backend).
tests/          Automated tests
.github/        Issue and pull request templates (CI workflow added in Sprint 1)
```

## Deliverables status

| Deliverable | Location | Status |
|---|---|---|
| SRS | `docs/srs/` | In progress |
| Test Plan (with test cases) | `docs/test-plan/` | In progress |
| Software Architecture & Design Specification | `docs/sad/` | In progress |
| Backlog (GitHub Project) | Projects tab | In progress |

## Sprint plan

| Sprint | Dates |
|---|---|
| Dry run | 12–16 Oct 2026 |
| Sprint 1 | 19–23 Oct 2026 |
| Sprint 2 | 26–30 Oct 2026 |

## Working agreement

- One branch per piece of work, e.g. `docs/m3-sad`; never commit directly to `main` after the initial setup.
- Small commits with clear messages (`docs(sad): add component diagram`).
- Every change goes through a pull request with at least one review by a teammate.
- Merge pull requests with **"Create a merge commit"** so every member's individual commits are preserved.
- Backlog items are GitHub Issues titled `[US-xx] …`, assigned to their owner, tracked in the GitHub Project.
