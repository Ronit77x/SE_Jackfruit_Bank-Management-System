# TC-UX-01 Usability Trial Observation Sheet & Facilitator Guide

- **Test Case ID:** `TC-UX-01`
- **User Story:** `US-14` (Fund transfer usability — Part of #12)
- **Requirement:** `BMS-NF-004` — First-time-user transfer usability
- **Standard Acceptance Target:** $\ge 90\%$ (5 out of 5 participants must pass for $n=5$)
- **Trial Status:** PREPARED / READY FOR EXECUTION (Empirical Results Pending)

---

## 1. Neutral Participant Instructions (Read Verbatim)

> *"Welcome. You are participating in a usability trial for Bank Management System (BMS). We are testing the software interface, not your ability. Please imagine you are an existing customer named Asha Rao logged into your web banking portal. Your task is to transfer ₹500 from your account to recipient account number 1000000003. Please complete this transfer as you normally would. I cannot answer questions or offer guidance once the timer starts. You may begin now."*

---

## 2. Facilitator & Administrator Checklist

Before each participant session:

- [ ] Confirm isolated environment: `$env:BMS_DATABASE_URL` points to an isolated SQLite test database.
- [ ] Reset database: execute `python -m scripts.seed`, and restart server.
- [ ] Confirm starting balances: Source `1000000001` = ₹10,000.00; Destination `1000000003` = ₹5,000.00.
- [ ] Open fresh incognito/private browser tab at `http://127.0.0.1:8000/ui/transfer.html` (or `http://127.0.0.1:8000/transfer`).
- [ ] Authenticate as Customer 1 (Username: `1`, Password: `Passw0rd!`).
- [ ] Verify stopwatch is ready.
- [ ] Confirm participant has NEVER seen or used this fund transfer workflow before.

During each session:

- [ ] Start stopwatch immediately upon finishing the verbatim instructions.
- [ ] Maintain silence. If participant asks for guidance: *"Please proceed as you think best."*
- [ ] Observe source account selection and comprehension of disabled/ineligible accounts.
- [ ] Observe recipient account and amount entry.
- [ ] Observe review screen and final submission.
- [ ] Stop stopwatch when the green "Transfer Successful!" screen appears.

After each session:

- [ ] Record exact elapsed seconds, accurate details, and whether assistance was requested/given.
- [ ] Interview participant for brief subjective feedback and note any points of confusion.
- [ ] Close the browser tab.
- [ ] Execute the reset procedure before inviting the next participant.

---

## 3. Objective Evaluation Criteria

- **PASS:**
  1. Completed transfer in $\le 120$ seconds (2 minutes).
  2. Zero assistance requested or given (`Assistance Received = No`).
  3. Correct destination account (`1000000003`) and amount (`₹500.00`) transferred.
  4. Reached final successful confirmation screen.
- **FAIL:**
  - Elapsed time exceeds 120 seconds.
  - Participant asks for and receives assistance or abandons the task.
  - Incorrect recipient account or wrong amount transferred.

---

## 4. Participant Trial Records (P1 – P5)

*(Status: NOT YET TESTED. All records remain unpopulated until genuine human trials are conducted. No simulated or fabricated data.)*

### Participant 1 (P1) — NOT YET TESTED
- **First-time-user confirmation:** `[ ] Yes / [ ] No`
- **Actual trial date and time:** 
- **Device and browser:** 
- **Task start time:** 
- **Task completion time:** 
- **Elapsed time (seconds):** 
- **Correct source account selected:** `[ ] Yes / [ ] No`
- **Correct recipient account entered (1000000003):** `[ ] Yes / [ ] No`
- **Correct amount entered (₹500):** `[ ] Yes / [ ] No`
- **Transfer completed successfully:** `[ ] Yes / [ ] No`
- **Assistance requested or received:** `[ ] None / [ ] Details:` 
- **Participant outcome:** `[ ] PASS / [ ] FAIL`
- **Actual participant feedback:** 
- **Observed usability problems:** 

---

### Participant 2 (P2) — NOT YET TESTED
- **First-time-user confirmation:** `[ ] Yes / [ ] No`
- **Actual trial date and time:** 
- **Device and browser:** 
- **Task start time:** 
- **Task completion time:** 
- **Elapsed time (seconds):** 
- **Correct source account selected:** `[ ] Yes / [ ] No`
- **Correct recipient account entered (1000000003):** `[ ] Yes / [ ] No`
- **Correct amount entered (₹500):** `[ ] Yes / [ ] No`
- **Transfer completed successfully:** `[ ] Yes / [ ] No`
- **Assistance requested or received:** `[ ] None / [ ] Details:` 
- **Participant outcome:** `[ ] PASS / [ ] FAIL`
- **Actual participant feedback:** 
- **Observed usability problems:** 

---

### Participant 3 (P3) — NOT YET TESTED
- **First-time-user confirmation:** `[ ] Yes / [ ] No`
- **Actual trial date and time:** 
- **Device and browser:** 
- **Task start time:** 
- **Task completion time:** 
- **Elapsed time (seconds):** 
- **Correct source account selected:** `[ ] Yes / [ ] No`
- **Correct recipient account entered (1000000003):** `[ ] Yes / [ ] No`
- **Correct amount entered (₹500):** `[ ] Yes / [ ] No`
- **Transfer completed successfully:** `[ ] Yes / [ ] No`
- **Assistance requested or received:** `[ ] None / [ ] Details:` 
- **Participant outcome:** `[ ] PASS / [ ] FAIL`
- **Actual participant feedback:** 
- **Observed usability problems:** 

---

### Participant 4 (P4) — NOT YET TESTED
- **First-time-user confirmation:** `[ ] Yes / [ ] No`
- **Actual trial date and time:** 
- **Device and browser:** 
- **Task start time:** 
- **Task completion time:** 
- **Elapsed time (seconds):** 
- **Correct source account selected:** `[ ] Yes / [ ] No`
- **Correct recipient account entered (1000000003):** `[ ] Yes / [ ] No`
- **Correct amount entered (₹500):** `[ ] Yes / [ ] No`
- **Transfer completed successfully:** `[ ] Yes / [ ] No`
- **Assistance requested or received:** `[ ] None / [ ] Details:` 
- **Participant outcome:** `[ ] PASS / [ ] FAIL`
- **Actual participant feedback:** 
- **Observed usability problems:** 

---

### Participant 5 (P5) — NOT YET TESTED
- **First-time-user confirmation:** `[ ] Yes / [ ] No`
- **Actual trial date and time:** 
- **Device and browser:** 
- **Task start time:** 
- **Task completion time:** 
- **Elapsed time (seconds):** 
- **Correct source account selected:** `[ ] Yes / [ ] No`
- **Correct recipient account entered (1000000003):** `[ ] Yes / [ ] No`
- **Correct amount entered (₹500):** `[ ] Yes / [ ] No`
- **Transfer completed successfully:** `[ ] Yes / [ ] No`
- **Assistance requested or received:** `[ ] None / [ ] Details:` 
- **Participant outcome:** `[ ] PASS / [ ] FAIL`
- **Actual participant feedback:** 
- **Observed usability problems:** 

---

## 5. Trial Summary & Acceptance Sign-Off

$$\text{Usability Pass Rate} = \left( \frac{\text{Passing Participants}}{5} \right) \times 100\%$$

- **Total Participants Tested:** `[ 0 / 5 ] (Pending Execution)`
- **Total Passing Participants:** `[ 0 / 5 ]`
- **Empirical Pass Rate:** `[ PENDING ]`
- **Sprint 2 Evidence Scope:** 2 of 5 participants (P1 and P2) will be conducted and documented as partial empirical evidence for PR #60; full 5/5 trials completed prior to release freeze.
- **Target ($\ge 90\%$):** Requires 5/5 passes for full acceptance sign-off.
- **BMS-NF-004 Status:** **PENDING EMPIRICAL TRIAL EXECUTION**
- **Evaluator Signature:** Member 2 (Vijay Kumar) — `[ Pending Execution ]`
