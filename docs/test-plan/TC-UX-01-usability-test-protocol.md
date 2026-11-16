# Usability Test Protocol: TC-UX-01 (Fund Transfer Flow)

- **Test Case ID:** `TC-UX-01`
- **User Story:** `[US-14] Usability of fund transfer flow` (Part of #12)
- **Requirement:** `BMS-NF-004` — First-time-user transfer usability
- **Component:** `DS-UI` (Customer Web Interface)
- **Assigned Member:** Member 2 (Vijay Kumar)
- **Sprint:** Sprint 2
- **Protocol Status:** READY FOR EXECUTION (Empirical Validation Pending)
- **Automated Contract Status:** PASS (Automated UI & API regression tests)
- **Human Participant Status:** PENDING (0 of 5 trials completed; awaiting genuine independent human participant testing)

---

## 1. Test Objective & Acceptance Criteria

Verify that the customer-facing fund transfer interface is intuitive, transparent, and easy to complete for first-time users without guidance or training.

### Official Acceptance Criteria
1. Test with at least five first-time users.
2. At least 90% of participants must complete a valid fund transfer within **two minutes (120 seconds)** without assistance.
   - *Note:* With exactly 5 participants, **5 out of 5 (100%)** must pass to meet the $\ge 90\%$ threshold.
3. Testing must use synthetic demo accounts and amounts, never real banking or customer data.

> [!IMPORTANT]
> Automated tests (`pytest`) verify API contracts, session security, and UI route availability, but **do not prove human usability**. This human usability test protocol must be executed with representative users to validate `BMS-NF-004`.

---

## 2. Test Environment & Participant Setup

- **Platform:** Web browser (Chrome, Edge, or Firefox) at desktop or mobile resolution ($\ge 360\text{ px}$).
- **URL:** `http://127.0.0.1:8000/ui/transfer.html` (or `http://127.0.0.1:8000/transfer`)
- **Isolated Participant Database Procedure:**
  > [!NOTE]
  > Rerunning `python -m scripts.seed` on an existing database is idempotent: it preserves existing customer accounts and **does not reset modified account balances**. To guarantee that each participant begins with the exact documented fresh starting balances, each trial session must be provisioned with its own separate, fresh SQLite database file. Never alter or delete the shared development database (`bms.db`).

  1. **Clean Stale Participant Database (If Needed):**
     If the participant-specific database file already exists from an interrupted or prior trial run, delete only that exact participant database file before provisioning. Never touch `bms.db`.
     - PowerShell:
       ```powershell
       Remove-Item ./bms_p1.db -ErrorAction SilentlyContinue
       ```
     - Bash / POSIX:
       ```bash
       rm -f ./bms_p1.db
       ```

  2. **Generate and Export Encryption Key:**
     Generate a valid 32-byte Fernet key once per participant session and keep the identical key active in the terminal session for both database seeding and application runtime:
     - Key Generation:
       ```bash
       python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
       ```
     - PowerShell:
       ```powershell
       $env:BMS_DATABASE_URL = "sqlite:///./bms_p1.db"
       $env:BMS_DATA_KEY = "<generated_key>"
       ```
     - Bash / POSIX:
       ```bash
       export BMS_DATABASE_URL="sqlite:///./bms_p1.db"
       export BMS_DATA_KEY="<generated_key>"
       ```

  3. **Initialize Schema & Fresh Seed Data:**
     Execute the project seed script against the fresh participant database (creates schema tables and demo accounts):
     ```powershell
     python -m scripts.seed
     ```

  4. **Pre-Flight Verification of Starting Balances:**
     Confirm the participant database is fresh before seating the user:
     ```powershell
     python -c "from app.database import SessionLocal; from app.models import Account; s=SessionLocal(); a1=s.query(Account).filter_by(account_number='1000000001').first(); a3=s.query(Account).filter_by(account_number='1000000003').first(); print(f'1000000001: {a1.balance}, 1000000003: {a3.balance}'); assert a1.balance == 10000 and a3.balance == 20000, 'Not fresh!'; s.close()"
     ```

  5. **Launch Application Server:**
     Start the server in the configured environment (inheriting `BMS_DATABASE_URL` and `BMS_DATA_KEY`):
     ```powershell
     uvicorn app.main:app --port 8000
     ```

  6. **Participant Isolation:**
     For subsequent participants (P2 through P5), repeat the procedure using a unique database file for each user (`bms_p2.db`, `bms_p3.db`, etc.). A participant's transfer actions can never alter or contaminate another participant's test dataset.

- **Test Dataset & Account State:**
  - Participant logs in as Customer 1 (**Asha Rao**, username `1`, demo password `Passw0rd!`).
  - Active source account: Savings Account `1000000001` (Balance: ₹10,000.00, Status: Active).
  - Secondary source account: Current Account `1000000002` (Balance: ₹25,000.00, Status: Active).
  - Source-account selector behavior: Only Active accounts remain enabled. Inactive, Frozen, or Closed accounts are disabled with descriptive status tags.
  - Target destination account: Customer 2 (**Ravi Kumar**, Account `1000000003`) (Savings starting balance: ₹20,000.00).

---

## 3. Facilitator Protocol

1. **Pre-test briefing:**
   - Welcome the participant.
   - Explain that the **software** is being tested, not the user.
   - Inform the participant that the session will be timed.
   - Open `http://127.0.0.1:8000/ui/transfer.html` with Customer 1 session active.
2. **Neutral Task Instruction (read verbatim):**
   > *"You are an account holder at Jackfruit Bank. You have logged into your web banking portal. Please transfer ₹500 from your account to recipient account number 1000000003. You may begin now."*
3. **Observation Rules:**
   - The facilitator must remain silent and take observational notes.
   - **No assistance** may be provided during the attempt. If the participant asks for help, the facilitator responds: *"Please proceed as you think best."*
   - Start stopwatch immediately upon finishing the neutral instruction.
   - Stop stopwatch when the participant reaches the green **"Transfer Successful!"** receipt screen.

---

## 4. Evaluation & Pass/Fail Criteria

- **PASS:**
  - Completed transfer in $\le 120$ seconds (2 minutes).
  - Zero assistance provided (`Assistance Required = No`).
  - Correct destination account (`1000000003`) and amount (`₹500.00`) transferred.
- **FAIL:**
  - Elapsed time exceeds 120 seconds.
  - Participant requires assistance or abandons task.
  - Incorrect recipient account or amount transferred.

---

## 5. Usability Test Results Sheet (Blank Template)

*To be completed by the team during actual participant trials:*

| Participant ID | Date & Time | Device / Browser | Elapsed Time (seconds) | Assistance Required? (Yes/No) | Accurate Details? (Yes/No) | Result (PASS / FAIL) | Observations & Feedback |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **P1** | *[Date]* | *[Browser/OS]* | *[e.g. 45s]* | No | Yes | *[PASS]* | *[Notes]* |
| **P2** | *[Date]* | *[Browser/OS]* | *[e.g. 62s]* | No | Yes | *[PASS]* | *[Notes]* |
| **P3** | *[Date]* | *[Browser/OS]* | *[e.g. 38s]* | No | Yes | *[PASS]* | *[Notes]* |
| **P4** | *[Date]* | *[Browser/OS]* | *[e.g. 54s]* | No | Yes | *[PASS]* | *[Notes]* |
| **P5** | *[Date]* | *[Browser/OS]* | *[e.g. 49s]* | No | Yes | *[PASS]* | *[Notes]* |

---

## 6. Success Rate Calculation

$$\text{Usability Pass Rate} = \left( \frac{\text{Number of Passing Participants}}{\text{Total Participants}} \right) \times 100\%$$

- **Target:** $\ge 90\%$ (requires at least 5/5 passes for a 5-user trial).
- **Final Result:** `[ Pending Physical Trial Execution ]`
- **Validation Note:** Under course software engineering standards, test results must reflect genuine human trials and must never be fabricated. Automated regression tests verify all UI, API, and error handling contracts, but BMS-NF-004 will remain marked as pending empirical completion until actual physical participant trials are conducted and signed off.
- **Evaluator Signature:** Member 2 (Vijay Kumar) — `[ Pending ]`
