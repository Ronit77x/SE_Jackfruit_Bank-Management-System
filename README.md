# SE_Jackfruit — Bank Management System

A web-based **Bank Management System (BMS)** for a single bank, with three roles — **Customer**, **Teller** and **Admin**. The project covers customer/account management, deposits, withdrawals, internal fund transfers, transaction statements, audit logging and daily transaction reporting.

## Team

| Member | Responsibility | GitHub |
|---|---|---|
| Member 1 — Tarini Arora | SRS ownership and integration; authentication/security integration; US-07 documentation | |
| Member 2 — Vijay Kumar | Test plan, test cases and account-management work | `@vijaykumar-187` |
| Member 3 — Ronit Prasad | SAD, architecture and repository ownership | `@Ronit77x` |
| Member 4 — Vaibhava L | Security requirements, NFRs, traceability and audit-related work | `@Vaibhav-alt0246` |

## Technology

- Python 3 and FastAPI (REST/JSON)
- SQLite with SQLAlchemy
- HTML, CSS and JavaScript frontend
- pytest automated tests
- GitHub Actions CI
- bcrypt password hashing
- Fernet encryption for sensitive KYC data, configured through `BMS_DATA_KEY`

## Main documentation

| Document | Location | Current note |
|---|---|---|
| Software Requirements Specification | `docs/srs/` | Integrated v1.0 files are present; team approval is pending |
| Software Architecture and Design | `docs/sad/` | v1.0 DOCX and PDF are present |
| Test Plan | `docs/test-plan/` | v1.0 DOCX and supporting evidence are present |
| UML diagrams | `docs/diagrams/` | PlantUML sources and rendered diagrams are present |
| Sprint plan and backlog coverage | `docs/backlog/` | Planning and coverage records; live backlog acceptance remains a team check |
| Deviations log | `docs/deviations.md` | Sprint 1 and Sprint 2 deviations, delivery status and acceptance limitations are documented |
| Release notes | `docs/release/RELEASE_NOTES_v1.0.0.md` | Candidate baseline; release acceptance remains pending |

## Application setup

### Prerequisites

- Python 3.10 or later (Python 3.12 recommended)
- Git

### 1. Clone and enter the repository

```bash
git clone https://github.com/SEMiniProjectBMS/SE_Jackfruit_Bank-Management-System.git
cd SE_Jackfruit_Bank-Management-System
```

### 2. Create and activate a virtual environment

Windows CMD:

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure the sensitive-data encryption key

The application reads `BMS_DATA_KEY` from the process environment. It does **not** automatically load a `.env` file. Generate a new key and keep it private; do not commit it to the repository.

Windows CMD (run in the same terminal before starting the application):

```cmd
for /f %K in ('python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"') do set BMS_DATA_KEY=%K
```

Linux/macOS:

```bash
export BMS_DATA_KEY="$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")"
```

Keep the generated key safe. Data encrypted with one key cannot be decrypted using a different key.

### 5. Optional demo data

```bash
python -m scripts.seed
```

### 6. Start the application

```bash
uvicorn app.main:app --reload
```

Useful local endpoints:

- API documentation: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Health endpoint: `http://127.0.0.1:8000/health`
- Web interface: `http://127.0.0.1:8000/ui/`

The `/health` endpoint currently returns `{"status": "ok"}` to indicate that the application process responds. It does not query the database and must not be treated as proof of database readiness.

## Running tests

Run the complete automated suite from the repository root:

```bash
pytest -v
```

Do not copy a historical test count into this README. Record the count and result from the final integrated checkout when the release verification is performed.

## Database schema

`app/models.py` is the source of truth for the six SQLAlchemy models:

- `customers`
- `users`
- `accounts`
- `transactions`
- `audit_logs`
- `notifications`

The `transactions` model contains `id`, `account_id`, `type`, `amount`, `balance_after`, `receipt_no`, `reference` and `created_at`. The `notifications` model contains `id`, `customer_id`, `message`, `status` and `created_at`. Refer to `app/models.py` for the authoritative field definitions.

## Security and implementation notes

- Passwords are hashed with bcrypt; plaintext passwords must not be stored or logged.
- Sensitive KYC values use Fernet encryption configured by `BMS_DATA_KEY`.
- Account numbers are randomly generated 10-digit values with uniqueness enforced by the database; they are not sequential.
- Audit-log triggers reject row updates and deletes. This is database-level append-only enforcement, not cryptographic hash chaining or tamper-evident external storage.
- Sessions are held in application memory; restarting the server invalidates active sessions.
- Inter-bank payment rails are outside the implemented scope; transfers are internal to the bank.
- `/health` is a process-level response and does not verify database connectivity.

## Sprint demos and release status

- [Sprint 1 demo video](docs/demo/sprint1-demo.mp4)
- [Sprint 2 demo video](docs/demo/sprint2-demo.mp4), recorded by Vaibhava L. (Member 4). See the [demo record](docs/demo/sprint-2-demo-runbook.md) for the demonstrated workflows and verification limits.
- Release candidate: `v1.0.0-rc` (candidate label only; not a final release).
- Final release freeze, final integrated verification and four-member acceptance/sign-off remain **pending**.

The final release must not be declared complete until the team has reviewed the integrated implementation, recorded the final verification evidence, completed the Sprint 2 demonstration and approved the release baseline.