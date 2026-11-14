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
- **Database & ORM:** SQLite 3 via SQLAlchemy 2.0 ORM
- **Password Security:** bcrypt hashing with unique salt per user
- **Frontend:** Static HTML5 / CSS3 / Vanilla JavaScript web UI
- **Testing Framework:** pytest (automated test suite)
- **Continuous Integration:** GitHub Actions (`.github/workflows/ci.yml`)
- **Architecture Pattern:** Multi-tier layered architecture (Routers → Services → CRUD/Data Access → Database)

---

## Implemented Features & User Stories

### Authentication & Security (M1 / M4)
- **US-01 / BMS-F-001:** User login with bearer token session authentication and 10-minute idle session timeout.
- **US-02 / BMS-F-002:** Account lockout after 3 consecutive failed login attempts (BR-07); administrator unlock endpoint.
- **US-03 / BMS-F-003:** Role-Based Access Control (RBAC) strictly enforcing Customer, Teller, and Admin role boundaries.
- **US-04 / BMS-F-004:** Secure password change (`POST /auth/change-password`) with strict password complexity enforcement (≥8 chars, uppercase, lowercase, digit) and mandatory first-login password replacement for temporary credentials.
- **US-05 / BMS-SR-002:** Encryption of sensitive data at rest and bcrypt password hashing.

### Account Management (M2)
- **US-08 / BMS-F-010:** Open Savings and Current accounts with sequential 10-digit account numbers and minimum opening deposits (Savings: ₹1,000; Current: ₹5,000). First account automatically provisions Customer login credentials with a temporary password.
- **US-09 / BMS-F-013:** View account details and balances with ownership isolation (customers can only view their own accounts).
- **US-10 / BMS-F-011:** Update customer contact details (phone, email, address) with full audit logging of before/after values.
- **US-12 / BMS-F-012:** Account status transitions (`Active`, `Frozen`, `Closed`), preventing transactions on frozen accounts and enforcing zero-balance closure.
- **US-13 / BMS-F-014:** Search customers and accounts by ID, account number, or customer name.

### Transactions (M3)
- **US-17 / BMS-F-020:** Cash deposits with single-transaction limit of ₹200,000 (BR-03) and receipt generation.
- **US-18 / BMS-F-021:** Cash withdrawals with daily withdrawal limit of ₹50,000 (BR-02) and minimum balance enforcement (Savings: ₹1,000; Current: ₹5,000).
- **US-19 / BMS-F-022:** Customer fund transfers between active accounts with transaction limits, atomic rollback on partial failure, and balance conservation.
- **US-20 / US-21 / BMS-F-023:** Mini-statement and transaction history export.

### Platform, DevOps & Auditing (M4 / M1 / M2)
- **US-06:** Automated continuous integration pipeline using GitHub Actions.
- **US-11:** Reusable pytest fixtures and test data factories.
- **US-25 / US-31 / BMS-SR-006:** Tamper-evident, append-only audit logging recording all security-critical operations without sensitive credentials.
- **US-30 / BMS-NF-002:** System health and availability monitoring endpoint (`GET /health`).

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

### Database Schema Overview
1. **`customers`:** Primary customer record (`id`, `name`, `date_of_birth`, `address`, `phone`, `email`, `id_proof_number`, `created_at`).
2. **`users`:** Authentication principals (`id`, `username`, `password_hash`, `role`, `status`, `failed_attempts`, `must_change_password`, `customer_id`, `created_at`).
3. **`accounts`:** Bank accounts (`account_number` [10 digits], `customer_id`, `account_type` [Savings/Current], `balance`, `status` [Active/Frozen/Closed], `created_at`).
4. **`transactions`:** Transaction ledger (`id`, `account_number`, `transaction_type`, `amount`, `balance_after`, `timestamp`, `performed_by`, `receipt_no`, `reference_account`).
5. **`audit_logs`:** Tamper-evident operational audit trail (`id`, `timestamp`, `user_id`, `action`, `outcome`, `details`).
6. **`notifications`:** Customer alerts (`id`, `customer_id`, `type`, `channel`, `recipient`, `message`, `status`, `created_at`).

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

### 4. Environment Configuration
Create a `.env` file in the root directory (optional, default fallback provided):
```ini
BMS_ENCRYPTION_KEY=ygQp88oRbWVKGWo-ZK5CsOOAK8F5yYEC3xYHFkrAaRM=
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
- **Health Check Endpoint:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## Running Automated Tests

Run the full pytest suite:
```bash
pytest -v
```

Run focused test suites:
- Authentication & password management: `pytest tests/test_auth.py tests/test_auth_hardening.py -v`
- Role-based access control: `pytest tests/test_rbac.py -v`
- Transaction operations & concurrency: `pytest tests/test_transactions_*.py -v`

---

## Repository Structure & Documentation Index

```
docs/
  srs/          Software Requirements Specification
  srs-parts/    Modular SRS contributions from team members
  test-plan/    Integrated Test Plan and Test Cases (v1.0)
  sad/          Software Architecture and Design Document (v1.0)
  diagrams/     UML Architecture Diagrams (PlantUML & PNG)
  backlog/      Sprint plans, user stories, and backlog coverage matrices
  release/      Release notes, changelog, and release freeze criteria
app/
  routers/      API endpoints (auth, accounts, transactions, admin)
  services/     Core banking business logic and services
  crud.py       Database CRUD helper functions
  models.py     SQLAlchemy database models
  security.py   Security, bcrypt hashing, and password policy helpers
  deps.py       FastAPI dependency injectors (auth, roles)
  errors.py     Standardized error format handling
  constants.py  System-wide business rule constants
tests/          Automated regression and functional test suite
.github/        Workflows (ci.yml) and PR/issue templates
```

---

## Known Limitations & Considerations

1. **In-Memory Session Storage:** Active sessions are maintained in an in-memory session registry (`app/sessions.py`). A server restart invalidates active bearer tokens, requiring users to log in again.
2. **Single Bank Deployment:** Designed for a single financial institution; inter-bank external clearing protocols (such as NEFT/RTGS gateways) are simulated via internal account transfers.
3. **Local Database Engine:** SQLite 3 is utilized for development and testing simplicity; concurrent write scaling is optimized via connection pooling and WAL mode in production configurations.

---

## Release Baseline & Version Freeze

- **Release Version:** `v1.0.0`
- **Release Date:** October 30, 2026
- **Status:** Release Freeze baseline agreed by Team BMS_PES.
