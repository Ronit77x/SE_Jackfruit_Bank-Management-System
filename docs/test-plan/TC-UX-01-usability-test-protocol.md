# Usability Test Protocol: TC-UX-01 (Fund Transfer Flow)

- **Test Case ID:** `TC-UX-01`
- **User Story:** `[US-14] Usability of fund transfer flow` (GitHub Issue #12)
- **Requirement:** `BMS-NF-004` — First-time-user transfer usability
- **Component:** `DS-UI` (Customer Web Interface)
- **Assigned Member:** Member 2 (Vijay Kumar)
- **Sprint:** Sprint 2

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
- **URL:** `http://127.0.0.1:8000/transfer`
- **Test Dataset:**
  - Seeded database via `python -m scripts.seed`.
  - Participant is logged in as Customer 1 (**Asha Rao**, username `1`, demo password `Passw0rd!`), with accounts:
    - Savings Account `1000000001` (Balance: ₹10,000.00).
  - Target destination account: Customer 2 (**Ravi Kumar**, Account `1000000003`).

---

## 3. Facilitator Protocol

1. **Pre-test briefing:**
   - Welcome the participant.
   - Explain that the **software** is being tested, not the user.
   - Inform the participant that the session will be timed.
   - Open `http://127.0.0.1:8000/transfer` with Customer 1 session active.
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
- **Final Result:** `[ Pending Trial Execution ]`
- **Evaluator Signature:** Member 2 (Vijay Kumar) — `[ Pending ]`
