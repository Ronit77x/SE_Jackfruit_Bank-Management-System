/* Customer Fund Transfer Controller (US-14 / BMS-NF-004).
 * Owner: Member 2 (Vijay).
 *
 * SAFETY RULE (BMS-SR-005): Never insert unescaped strings as markup.
 * Only use textContent, bms.el, bms.clear, bms.show, bms.hide.
 */
(function () {
  "use strict";

  // Role guard
  if (!bms.requireRole(["Customer"])) {
    return;
  }

  // Render navigation header
  bms.header("Transfer money");

  // State
  var customerAccounts = [];
  var currentTransferData = null;

  var MIN_BALANCE = {
    Savings: 1000.0,
    Current: 5000.0
  };
  var MAX_TRANSFER_LIMIT = 100000.0;

  function isEligibleStatus(status) {
    return typeof status === "string" && status.trim().toLowerCase() === "active";
  }

  function showAlert(msg, ok) {
    var el = document.getElementById("globalAlert");
    if (!el) return;
    bms.show(el, msg, !!ok);
  }

  function hideAlert() {
    var el = document.getElementById("globalAlert");
    if (!el) return;
    bms.hide(el);
  }

  function setStepActive(stepNum) {
    var s1 = document.getElementById("stepIndicator1");
    var s2 = document.getElementById("stepIndicator2");
    var s3 = document.getElementById("stepIndicator3");
    if (s1) s1.className = stepNum >= 1 ? "step-item active" : "step-item";
    if (s2) s2.className = stepNum >= 2 ? "step-item active" : "step-item";
    if (s3) s3.className = stepNum >= 3 ? "step-item active" : "step-item";
  }

  async function loadCustomerAccounts() {
    var select = document.getElementById("fromAccountSelect");
    if (!select) return;
    bms.clear(select);
    select.appendChild(bms.el("option", "Loading accounts…"));

    try {
      var accounts = await bms.get("/accounts/me");
      customerAccounts = accounts || [];

      bms.clear(select);

      if (!customerAccounts || customerAccounts.length === 0) {
        select.appendChild(bms.el("option", "No bank accounts found"));
        showAlert("You do not have any active bank accounts with Jackfruit Bank.", false);
        return;
      }

      var eligibleAccounts = customerAccounts.filter(function (acc) {
        return acc && isEligibleStatus(acc.status);
      });
      var ineligibleAccounts = customerAccounts.filter(function (acc) {
        return !acc || !isEligibleStatus(acc.status);
      });

      if (eligibleAccounts.length === 0) {
        select.appendChild(bms.el("option", "No eligible active accounts available"));
      } else {
        var defaultOpt = bms.el("option", "-- Choose source account --");
        defaultOpt.value = "";
        select.appendChild(defaultOpt);

        eligibleAccounts.forEach(function (acc) {
          var opt = bms.el(
            "option",
            acc.type + " — " + acc.maskedAccountNumber + " (" + bms.money(acc.balance || 0) + ")"
          );
          opt.value = acc.accountNumber;
          select.appendChild(opt);
        });

        // Also list ineligible accounts as disabled so customer can see why they cannot be selected
        ineligibleAccounts.forEach(function (acc) {
          if (!acc) return;
          var statusLabel = acc.status ? String(acc.status).trim() : "Unknown status";
          var opt = bms.el(
            "option",
            acc.type + " — " + (acc.maskedAccountNumber || "") + " [" + statusLabel + " - Ineligible]"
          );
          opt.value = acc.accountNumber;
          opt.disabled = true;
          select.appendChild(opt);
        });
      }

      var ineligibleSummary = ineligibleAccounts
        .filter(Boolean)
        .map(function (acc) {
          return (acc.type || "Account") + " " + (acc.maskedAccountNumber || "") + " (" + (acc.status ? String(acc.status).trim() : "Unknown status") + ")";
        })
        .join(", ");

      var helpEl = document.getElementById("fromAccountHelp");
      if (eligibleAccounts.length === 0) {
        if (helpEl) {
          helpEl.textContent = ineligibleSummary
            ? "No accounts can be used for transfers right now. Excluded accounts: " + ineligibleSummary + "."
            : "All your accounts are currently frozen, closed, or inactive. Fund transfers cannot be initiated.";
          helpEl.style.color = "var(--danger)";
        }
        showAlert("You do not have any active accounts eligible for fund transfers. Frozen, closed, or inactive accounts cannot initiate transfers.", false);
      } else if (ineligibleAccounts.length > 0 && helpEl) {
        helpEl.textContent = "Excluded unavailable accounts: " + ineligibleSummary + ". Only Active accounts can initiate transfers.";
        helpEl.style.color = "";
      } else if (helpEl) {
        helpEl.textContent = "Select the account you want to send money from.";
        helpEl.style.color = "";
      }

      if (eligibleAccounts.length === 1) {
        select.value = eligibleAccounts[0].accountNumber;
        onSourceAccountChange();
      }
    } catch (err) {
      bms.clear(select);
      select.appendChild(bms.el("option", "Error loading accounts"));
      showAlert("Could not load your accounts: " + (err.message || "Unknown error"), false);
    }
  }

  function onSourceAccountChange() {
    var select = document.getElementById("fromAccountSelect");
    var selectedAccNo = select ? select.value : "";
    var acc = customerAccounts.find(function (a) { return a.accountNumber === selectedAccNo; });
    var display = document.getElementById("balanceDisplay");

    if (acc && display) {
      display.hidden = false;
      var isEligible = isEligibleStatus(acc.status);
      var typeEl = document.getElementById("accountTypeDisplay");
      var balanceEl = document.getElementById("accountBalanceDisplay");
      var minHelpEl = document.getElementById("minBalanceHelp");

      if (typeEl) {
        typeEl.textContent = acc.type + " Account (" + acc.maskedAccountNumber + ")" + (!isEligible ? " — " + acc.status : "");
      }
      if (balanceEl) {
        balanceEl.textContent = bms.money(acc.balance || 0);
      }
      var minReq = MIN_BALANCE[acc.type] || 0;
      if (minHelpEl) {
        if (!isEligible) {
          minHelpEl.textContent = "Account status is " + acc.status + ". Transactions cannot be performed from this account.";
          minHelpEl.style.color = "var(--danger)";
        } else {
          minHelpEl.textContent = "Minimum balance required: " + bms.money(minReq);
          minHelpEl.style.color = "";
        }
      }
    } else if (display) {
      display.hidden = true;
    }

    validateDestinationAccount();
    validateAmount();
  }

  function validateDestinationAccount() {
    var toInput = document.getElementById("toAccountInput");
    var toAcc = toInput ? toInput.value.trim() : "";
    var fromSelect = document.getElementById("fromAccountSelect");
    var fromAcc = fromSelect ? fromSelect.value : "";
    var errEl = document.getElementById("toAccountError");

    if (errEl) {
      errEl.hidden = true;
      errEl.textContent = "";
    }
    if (!toAcc) return false;

    if (!/^\d{1,10}$/.test(toAcc)) {
      if (errEl) {
        errEl.textContent = "Account number must contain only numbers.";
        errEl.hidden = false;
      }
      return false;
    }

    if (toAcc.length === 10 && fromAcc && toAcc === fromAcc) {
      if (errEl) {
        errEl.textContent = "Destination account cannot be the same as your source account.";
        errEl.hidden = false;
      }
      return false;
    }

    if (toAcc.length > 0 && toAcc.length < 10) {
      if (errEl) {
        errEl.textContent = "Please enter all 10 digits (" + toAcc.length + "/10 entered).";
        errEl.hidden = false;
      }
      return false;
    }

    return true;
  }

  function validateAmount() {
    var amountInput = document.getElementById("amountInput");
    var amountVal = amountInput ? parseFloat(amountInput.value) : NaN;
    var errEl = document.getElementById("amountError");
    var fromSelect = document.getElementById("fromAccountSelect");
    var fromAccNo = fromSelect ? fromSelect.value : "";
    var acc = customerAccounts.find(function (a) { return a.accountNumber === fromAccNo; });

    if (errEl) {
      errEl.hidden = true;
      errEl.textContent = "";
    }

    if (isNaN(amountVal) || amountVal <= 0) {
      return false;
    }

    if (amountVal > MAX_TRANSFER_LIMIT) {
      if (errEl) {
        errEl.textContent = "Amount exceeds the single transfer limit of " + bms.money(MAX_TRANSFER_LIMIT) + ".";
        errEl.hidden = false;
      }
      return false;
    }

    if (acc) {
      if (!isEligibleStatus(acc.status)) {
        if (errEl) {
          errEl.textContent = "Selected account is " + (acc.status || "unavailable") + " and cannot perform transfers.";
          errEl.hidden = false;
        }
        return false;
      }
      var currentBal = parseFloat(acc.balance);
      var minReq = MIN_BALANCE[acc.type] || 0;
      if (currentBal - amountVal < minReq) {
        if (errEl) {
          errEl.textContent = "Insufficient funds: balance after transfer (" + bms.money((currentBal - amountVal).toFixed(2)) + ") would fall below required minimum of " + bms.money(minReq) + ".";
          errEl.hidden = false;
        }
        return false;
      }
    }

    return true;
  }

  function proceedToReview() {
    hideAlert();

    var fromSelect = document.getElementById("fromAccountSelect");
    var toInput = document.getElementById("toAccountInput");
    var amountInput = document.getElementById("amountInput");

    var fromAccNo = fromSelect ? fromSelect.value : "";
    var toAccNo = toInput ? toInput.value.trim() : "";
    var amount = amountInput ? parseFloat(amountInput.value) : NaN;

    if (!fromAccNo) {
      showAlert("Please select a source account.", false);
      return;
    }

    if (!validateDestinationAccount() || toAccNo.length !== 10) {
      showAlert("Please enter a valid 10-digit recipient account number.", false);
      return;
    }

    if (!validateAmount() || isNaN(amount) || amount <= 0) {
      showAlert("Please enter a valid transfer amount.", false);
      return;
    }

    var sourceAcc = customerAccounts.find(function (a) { return a.accountNumber === fromAccNo; });
    if (!sourceAcc || !isEligibleStatus(sourceAcc.status)) {
      var statusText = sourceAcc && sourceAcc.status ? String(sourceAcc.status).trim().toLowerCase() : "unavailable";
      showAlert("The selected source account is " + (sourceAcc ? statusText : "invalid") + " and cannot perform transfers.", false);
      return;
    }

    currentTransferData = {
      fromAccount: fromAccNo,
      toAccount: toAccNo,
      amount: amount.toFixed(2),
      sourceAccObj: sourceAcc
    };

    var revFrom = document.getElementById("reviewFromAccount");
    var revTo = document.getElementById("reviewToAccount");
    var revAmt = document.getElementById("reviewAmount");
    var revTot = document.getElementById("reviewTotal");

    if (revFrom) revFrom.textContent = sourceAcc.type + " (" + sourceAcc.maskedAccountNumber + ")";
    if (revTo) revTo.textContent = toAccNo;
    if (revAmt) revAmt.textContent = bms.money(amount.toFixed(2));
    if (revTot) revTot.textContent = bms.money(amount.toFixed(2));

    var stepDetails = document.getElementById("stepDetails");
    var stepReview = document.getElementById("stepReview");
    var stepResult = document.getElementById("stepResult");

    if (stepDetails) stepDetails.hidden = true;
    if (stepReview) stepReview.hidden = false;
    if (stepResult) stepResult.hidden = true;

    setStepActive(2);
  }

  function backToEdit() {
    hideAlert();
    var stepDetails = document.getElementById("stepDetails");
    var stepReview = document.getElementById("stepReview");
    var stepResult = document.getElementById("stepResult");

    if (stepDetails) stepDetails.hidden = false;
    if (stepReview) stepReview.hidden = true;
    if (stepResult) stepResult.hidden = true;

    setStepActive(1);
  }

  var isSubmitting = false;

  async function executeTransfer() {
    if (!currentTransferData || isSubmitting) return;
    isSubmitting = true;

    var btn = document.getElementById("btnConfirmSend");
    if (btn) {
      btn.disabled = true;
      btn.textContent = "Processing transfer…";
    }

    var stepDetails = document.getElementById("stepDetails");
    var stepReview = document.getElementById("stepReview");
    var stepResult = document.getElementById("stepResult");
    var successContent = document.getElementById("successContent");
    var failureContent = document.getElementById("failureContent");

    try {
      var data = await bms.post("/transactions/transfer", {
        fromAccount: currentTransferData.fromAccount,
        toAccount: currentTransferData.toAccount,
        amount: currentTransferData.amount
      });

      if (stepDetails) stepDetails.hidden = true;
      if (stepReview) stepReview.hidden = true;
      if (stepResult) stepResult.hidden = false;
      if (successContent) successContent.hidden = false;
      if (failureContent) failureContent.hidden = true;

      setStepActive(3);

      var recRef = document.getElementById("receiptReference");
      var recAmt = document.getElementById("receiptAmount");
      var recTo = document.getElementById("receiptToAccount");
      var recBal = document.getElementById("receiptNewBalance");

      if (recRef) recRef.textContent = data.reference || ("TXN-" + data.transactionId);
      if (recAmt) recAmt.textContent = bms.money(currentTransferData.amount);
      if (recTo) recTo.textContent = currentTransferData.toAccount;
      if (recBal) recBal.textContent = bms.money(data.balance);

      loadCustomerAccounts();
    } catch (err) {
      if (stepDetails) stepDetails.hidden = true;
      if (stepReview) stepReview.hidden = true;
      if (stepResult) stepResult.hidden = false;
      if (successContent) successContent.hidden = true;
      if (failureContent) failureContent.hidden = false;

      setStepActive(3);

      var friendlyMsg = err.message || "The transfer could not be completed.";
      if (err.code === "ACCOUNT_NOT_FOUND") {
        friendlyMsg = "The recipient account was not found. Please double-check the 10-digit account number.";
      } else if (err.code === "ACCOUNT_NOT_ACTIVE") {
        friendlyMsg = "The recipient or source account is currently frozen or closed and cannot complete transactions.";
      } else if (err.code === "INSUFFICIENT_FUNDS") {
        friendlyMsg = "Insufficient funds in your account to complete this transfer and maintain the minimum balance.";
      } else if (err.code === "TRANSFER_LIMIT_EXCEEDED") {
        friendlyMsg = "The transfer amount exceeds the single transaction limit of " + bms.money(MAX_TRANSFER_LIMIT) + ".";
      }

      var failMsgEl = document.getElementById("failureMessage");
      if (failMsgEl) {
        failMsgEl.textContent = friendlyMsg;
      }
    } finally {
      isSubmitting = false;
      if (btn) {
        btn.disabled = false;
        btn.textContent = "Confirm & send transfer";
      }
    }
  }

  function resetFormForNewTransfer() {
    var toInput = document.getElementById("toAccountInput");
    var amountInput = document.getElementById("amountInput");
    if (toInput) toInput.value = "";
    if (amountInput) amountInput.value = "";

    var successContent = document.getElementById("successContent");
    var failureContent = document.getElementById("failureContent");
    if (successContent) successContent.hidden = true;
    if (failureContent) failureContent.hidden = true;

    backToEdit();
  }

  // Setup DOM event listeners and initial load
  function init() {
    loadCustomerAccounts();

    var fromSelect = document.getElementById("fromAccountSelect");
    if (fromSelect) {
      fromSelect.addEventListener("change", onSourceAccountChange);
    }

    var toInput = document.getElementById("toAccountInput");
    if (toInput) {
      toInput.addEventListener("input", validateDestinationAccount);
    }

    var amountInput = document.getElementById("amountInput");
    if (amountInput) {
      amountInput.addEventListener("input", validateAmount);
    }

    var form = document.getElementById("transferForm");
    if (form) {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        proceedToReview();
      });
    }

    var quickBtns = document.querySelectorAll(".quick-amount-btn");
    quickBtns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var amt = btn.getAttribute("data-amount");
        if (amountInput && amt) {
          amountInput.value = parseFloat(amt).toFixed(2);
          validateAmount();
        }
      });
    });

    var backBtn = document.getElementById("btnBackToEdit");
    if (backBtn) {
      backBtn.addEventListener("click", backToEdit);
    }

    var confirmBtn = document.getElementById("btnConfirmSend");
    if (confirmBtn) {
      confirmBtn.addEventListener("click", executeTransfer);
    }

    var newTransferBtn = document.getElementById("btnNewTransfer");
    if (newTransferBtn) {
      newTransferBtn.addEventListener("click", resetFormForNewTransfer);
    }

    var printBtn = document.getElementById("btnPrintReceipt");
    if (printBtn) {
      printBtn.addEventListener("click", function () {
        window.print();
      });
    }

    var failureBackBtn = document.getElementById("btnFailureBack");
    if (failureBackBtn) {
      failureBackBtn.addEventListener("click", backToEdit);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Expose for compatibility and test access
  window.executeTransfer = executeTransfer;
  window.proceedToReview = proceedToReview;
  window.backToEdit = backToEdit;
  window.isEligibleStatus = isEligibleStatus;
})();
