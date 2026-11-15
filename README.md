# SE_Jackfruit — Bank Management System

A web-based **Bank Management System (BMS)** for a retail bank, supporting three user roles — **Customer**, **Teller**, and **Administrator**. The system provides core banking operations including account opening, cash deposits, withdrawals, fund transfers, statements, audit logging, and daily transaction reports.

---

## Team Members & Responsibilities

| Member | Role in Project | GitHub Username | Primary Document / Component Ownership |
|---|---|---|---|
| Member 1: Tarini Arora | SRS Owner & Integration | `@TariniArora` | SRS Integration, Auth Service, Security, GitHub Actions CI |
| Member 2: Vijay Kumar | Test Plan & Verification | `@vijaykumar-187` | Test Plan, Test Cases, Accounts Service, Account Management |
| Member 3: Ronit Prasad | Architecture & Design, Repo Owner | `@Ronit77x` | SAD, Architecture, Transaction Engine, Data Access Layer |
| Member 4: Vaibhava L | Security, NFRs & Auditing | `@Vaibhav-alt0246` | Security Requirements, Audit Logging, Administration, Reports |

---

## Technology Stack

- **Backend Framework:** Python 3.12 + FastAPI (REST / JSON API)
- **Database & ORM:** SQLite 3 via SQLAlchemy 2.0 ORM (with WAL mode & connection pooling)
- **Password Security:** bcrypt hashing with unique salt per user
- **Sensitive Data Encryption at Rest:** AES-128 via Fernet (`cryptography` package) using `BMS_DATA_KEY`
- **Frontend:** Static HTML5 / CSS3 / Vanilla JavaScript web UI
- **Testing Framework:** pytest (automated test suite)
- **Continuous Integration:** GitHub Actions (`.github/workflows/ci.yml`)
- **Architecture Pattern:** Multi-tier layered architecture (Routers → Services → Data Access/CRUD → Database)

---

## Implemented Features & User Stories

### Authentication & Security (M1 / M4)
- **US-01 / BMS-F-001:** User login with bearer token session authentication and 10-minute idle session timeout.
- **US-02 / BMS-F-002:** Account lockout after 3 consecutive failed login attempts (BR-07); administrator unlock endpoint.
- **US-03 / BMS-F-003:** Role-Based Access Control (RBAC) strictly enforcing Customer, Teller, and Admin role boundaries.
- **US-04 / BMS-F-004:** Secure password change (`POST /auth/change-password`) with strict password complexity enforcement (≥8 chars, uppercase, lowercase, digit, maximum 72 bytes) and mandatory first-login password replacement for temporary credentials.
- **US-05 / BMS-SR-002:** Encryption of sensitive KYC data at rest (`id_proof_number` encrypted via Fernet AES-128) and bcrypt password hashing.

### Account Management (M2)
- **US-08 / BMS-F-010:** Open Savings and Current accounts with randomly generated 10-digit account numbers (collision-retried via unique constraint, BR-06) and minimum opening deposits (Savings: ₹1,000; Current: ₹5,000). First account automatically provisions Customer login credentials with a temporary password and dispatches opening-deposit notification.
- **US-09 / BMS-F-013:** View account details and balances with ownership isolation (`GET /accounts`, customers can only view their own accounts with masked account numbers).
- **US-10 / BMS-F-011:** Update customer contact details (phone, email, address) with full audit logging of before/after values (`PUT /customers/{customer_id}`, Teller only).
- **US-12 / BMS-F-012:** Account status transitions (`Active`, `Frozen`, `Closed`), preventing transactions on frozen accounts, enforcing exact zero-balance closure, masking account numbers in audit details, and atomicity protection.
- **US-13 / BMS-F-014:** Search customers and associated accounts by full/partial customer name, normalized phone number (handling country codes, spaces, hyphens), or exact 10-digit account number (`GET /customers?q=...[&limit=...]`, Teller only) with account number masking (`******XXXX`).

### Transactions (M3)
- **US-17 / BMS-F-020:** Cash deposits with single-transaction limit of ₹200,000 (BR-03) and receipt generation.
- **US-18 / BMS-F-021:** Cash withdrawals with daily withdrawal limit of ₹50,000 (BR-02) and minimum balance enforcement (Savings: ₹1,000; Current: ₹5,000).
- **US-19 / BMS-F-022:** Customer fund transfers between active accounts with transaction limits, atomic rollback on partial failure, balance conservation, and dual notification dispatch.
- **US-20 / BMS-F-023:** Mini-statement listing the 10 most recent transactions (`GET /accounts/{id}/statement/mini`).
- **US-21 / BMS-F-024:** Transaction history statement export in CSV format (`GET /accounts/{id}/statement/download`) with date range filtering, masked account numbers, and formula injection protection.

### Platform, DevOps & Auditing (M4 / M1 / M2)
- **US-06:** Automated continuous integration pipeline using GitHub Actions.
- **US-11:** Reusable pytest fixtures and test data factories.
- **US-25 / US-31 / BMS-SR-006:** Append-only audit logging recording security-critical operations without sensitive credentials. SQLite engine-level triggers enforce table immutability by aborting UPDATE and DELETE operations. *(Note: trigger enforcement provides relational immutability against database mutations; it does not provide cryptographic hash chaining).*
- **US-30 / BMS-NF-002:** System health check endpoint (`GET /health`) verifying HTTP API service availability. *(Note: `/health` returns static process availability `{"status": "ok"}`; it does not probe database connectivity).*

---

## Application Architecture & Database Schema

### Layered Architecture
```
┌─────────────────────────────────────────────────────────┐
│              Presentation Layer (Frontend / Docs)        │
│          HTML5/CSS3/JS Web UI  &  FastAPI OpenAPI Docs  │
└────────────────────────────┬────────────────────────────┘
                             │ HTTP / JSON (Bearer Token)
┌────────────────────────────▼────────────────────────────┐
│              API Routing Layer (app/routers/)           │
│    auth.py  ·  accounts.py  ·  transactions.py  · admin.py│
└────────────────────────────┬────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│            Business Logic Layer (app/services/)         │
│  account_service.py · transaction_service.py · audit.py │
└────────────────────────────┬────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│            Data Access Layer (app/crud.py & models.py)  │
│         SQLAlchemy ORM Models & Database Abstractions   │
└────────────────────────────┬────────────────────────────┘
                             │ SQLite Dialect / SQL
┌────────────────────────────▼────────────────────────────┐
│                    Database Layer (bms.db)              │
│       Tables: customers, users, accounts, transactions, │
│               audit_logs, notifications                 │
└─────────────────────────────────────────────────────────┘
```

### Database Schema Overview (Source of Truth: `app/models.py`)

1. **`customers`:** Primary customer records and contact details.
   - `id`: Integer, primary key
   - `name`: String(120), full customer name
   - `date_of_birth`: Date
   - `address`: String(255)
   - `phone`: String(20)
   - `email`: String(120)
   - `id_proof_number`: String(255), encrypted at rest via Fernet (`BMS_DATA_KEY`)
   - `created_at`: DateTime(timezone=True)
   - Relationships: `accounts` (`relationship(back_populates="customer")`)

2. **`users`:** Authentication principals and credentials.
   - `id`: Integer, primary key
   - `username`: String(60), unique, indexed
   - `password_hash`: String(255), bcrypt hash
   - `role`: String(20), `Customer` / `Teller` / `Admin`
   - `status`: String(20), `Active` / `Locked` / `Inactive`
   - `failed_attempts`: Integer, consecutive failed login counter
   - `must_change_password`: Boolean, forced password update flag
   - `customer_id`: Integer, ForeignKey(`customers.id`), nullable
   - `created_at`: DateTime(timezone=True)

3. **`accounts`:** Bank accounts.
   - `id`: Integer, primary key
   - `account_number`: String(10), unique, indexed (randomly generated 10 digits)
   - `customer_id`: Integer, ForeignKey(`customers.id`)
   - `type`: String(20), `Savings` / `Current`
   - `balance`: Numeric(14, 2), current balance
   - `status`: String(20), `Active` / `Frozen` / `Closed`
   - `opened_at`: DateTime(timezone=True)
   - Relationships: `customer` (`relationship(back_populates="accounts")`), `transactions` (`relationship(back_populates="account")`)

4. **`transactions`:** Double-entry ledger records.
   - `id`: Integer, primary key
   - `account_id`: Integer, ForeignKey(`accounts.id`), indexed
   - `type`: String(20), transaction type (`DEPOSIT`, `WITHDRAWAL`, `TRANSFER_OUT`, `TRANSFER_IN`, `OPENING_DEPOSIT`)
   - `amount`: Numeric(14, 2)
   - `balance_after`: Numeric(14, 2)
   - `receipt_no`: String(40), unique, nullable
   - `reference`: String(60), nullable (correlation identifier for transfer legs)
   - `created_at`: DateTime(timezone=True), indexed
   - Relationships: `account` (`relationship(back_populates="transactions")`)

5. **`audit_logs`:** Append-only operational audit trail.
   - `id`: Integer, primary key
   - `timestamp`: DateTime(timezone=True), indexed
   - `user_id`: Integer, nullable (actor ID)
   - `action`: String(60), indexed
   - `outcome`: String(20), `SUCCESS` / `FAILURE` / `DENIED`
   - `details`: Text, event description (masked account numbers, no plaintext credentials)

6. **`notifications`:** Simulated customer alerts.
   - `id`: Integer, primary key
   - `customer_id`: Integer, ForeignKey(`customers.id`)
   - `message`: Text, alert message body
   - `status`: String(20), default `LOGGED`
   - `created_at`: DateTime(timezone=True)

---

## Installation and Setup

### Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/Ronit77x/SE_Jackfruit_Bank-Management-System.git
cd SE_Jackfruit_Bank-Management-System
```

### 2. Set Up Virtual Environment
On Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```
On Linux / macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Encryption Key (`BMS_DATA_KEY`)

The application uses Fernet symmetric encryption to encrypt sensitive KYC fields (`id_proof_number`) at rest. The encryption key must be provided via the `BMS_DATA_KEY` environment variable.

> **Important:** The application reads `os.environ.get("BMS_DATA_KEY")` and does **not** automatically load `.env` files. You must set the environment variable in your shell session before starting the application. Never hardcode or commit encryption keys to version control.

**Step A: Generate a new Fernet key:**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Step B: Set the environment variable:**

On Windows PowerShell:
```powershell
$env:BMS_DATA_KEY = (python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

On Linux / macOS / Git Bash:
```bash
export BMS_DATA_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

### 5. Seed Initial Data (Optional)
To populate synthetic demo users, customers, and accounts:
```bash
python -m scripts.seed
```

---

## Running the Application

Start the FastAPI application using Uvicorn:
```bash
uvicorn app.main:app --reload
```

Once running:
- **Interactive API Documentation (Swagger UI):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative API Documentation (ReDoc):** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Customer Web Interface:** [http://127.0.0.1:8000/ui/customer.html](http://127.0.0.1:8000/ui/customer.html)
- **Teller Web Interface:** [http://127.0.0.1:8000/ui/teller-cash.html](http://127.0.0.1:8000/ui/teller-cash.html)
- **Health Check Endpoint:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## Running Automated Tests

Run the full pytest suite:
```bash
pytest -v
```

Run focused test suites:
- Authentication & password management: `pytest tests/test_auth.py -v`
- Customer search: `pytest tests/test_customer_search.py -v`
- Account lifecycle & integration: `pytest tests/test_accounts.py tests/test_account_integration.py -v`
- Transactions & concurrency: `pytest tests/test_transactions_*.py -v`

---

## Repository Structure & Documentation Index

```
docs/
  srs/          Software Requirements Specification (v1.0 integrated)
  srs-parts/    Modular SRS contributions from team members
  test-plan/    Integrated Test Plan and Test Cases (v1.0)
  sad/          Software Architecture and Design Document (v1.0)
  diagrams/     UML Architecture Diagrams (PlantUML & PNG)
  backlog/      Sprint plans, user stories, and backlog coverage matrices
  release/      Release notes, changelog, and release freeze criteria
  deviations.md Log of deviations from submitted design documents
app/
  routers/      API endpoints (auth, accounts, transactions, admin)
  services/     Core banking business logic and services
  crud.py       Database CRUD helper functions
  models.py     SQLAlchemy database models (source of truth for schema)
  security.py   Security, bcrypt hashing, Fernet encryption, and password policy
  deps.py       FastAPI dependency injectors (auth, roles)
  errors.py     Standardized error format handling
  constants.py  System-wide business rule constants
tests/          Automated regression and functional test suite
.github/        Workflows (ci.yml) and PR/issue templates
```

---

## Deliverables Status

| Deliverable | Location | Status |
|---|---|---|
| SRS | `docs/srs/` | Baseline v1.0 integrated (Part of #36) |
| Test Plan (with test cases) | `docs/test-plan/` | Baseline v1.0 integrated |
| Software Architecture & Design Specification | `docs/sad/` | Baseline v1.0 integrated |
| Backlog (GitHub Project) | Projects tab | In progress (Part of #36) |
| Deviations Document | `docs/deviations.md` | Maintained for evaluation review |

---

## Working Agreement

- One branch per piece of work, e.g. `docs/m3-sad`; never commit directly to `main` after the initial setup.
- Small commits with clear messages (`docs(sad): add component diagram`).
- Every change goes through a pull request with at least one review by a teammate.
- Merge pull requests with **"Create a merge commit"** so every member's individual commits are preserved.
- Backlog items are GitHub Issues titled `[US-xx] …`, assigned to their owner, tracked in the GitHub Project.

---

## Sprint Demos & Evidence

- **Sprint 1 Demo Video:** [Sprint 1 demo video](docs/demo/sprint1-demo.mp4) (47 seconds, silent): deposit, withdrawal, minimum-balance rejection, transfer, Teller creation, and the passing pytest summary.
- **Sprint 2 Demo Recording:** Pending recording and final integration.
- **Deviations Log:** [docs/deviations.md](docs/deviations.md) captures implementation adjustments against baseline documents for grading presentation.

---

## Known Limitations & Considerations

1. **In-Memory Session Storage:** Active sessions are maintained in an in-memory session registry (`app/routers/auth.py`). A server restart invalidates active bearer tokens, requiring users to log in again.
2. **Single Bank Deployment:** Designed for a single financial institution; inter-bank external clearing protocols (such as NEFT/RTGS gateways) are simulated via internal account transfers.
3. **Local Database Engine:** SQLite 3 is utilized for development and testing simplicity; concurrent write scaling is optimized via connection pooling and WAL mode in production configurations.
4. **Health Check Scope:** The `/health` endpoint checks application process readiness and returns `{"status": "ok"}`; it does not query database tables.

---

## Release Status & Tracking

- **Current Release Baseline:** `v1.0.0-rc` (Release Candidate)
- **Tracking Issue:** Part of #36
- **Status:** Documentation and feature integration baseline. Formal release freeze, final verification sign-off, and four-member acceptance remain **pending** until final demo recordings and evaluations are completed.
