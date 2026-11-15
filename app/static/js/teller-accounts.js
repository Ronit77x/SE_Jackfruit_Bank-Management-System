/* Bank Management System - Teller Accounts Management (US-08, US-10, US-13). Owner: Member 2 (Vijay). */
(function () {
  "use strict";

  if (!bms.requireRole(["Teller"])) {
    return;
  }

  bms.header("Accounts");

  var MIN_BALANCE = {
    Savings: 1000,
    Current: 5000
  };

  // Helper to append a <dt> and <dd> pair to a <dl>
  function appendDetail(dl, labelText, valueText) {
    dl.appendChild(bms.el("dt", labelText));
    dl.appendChild(bms.el("dd", valueText));
  }

  // =========================================================================
  // Section 1: Customer and Account Search (US-13)
  // =========================================================================
  var searchForm = document.getElementById("search-form");
  var searchQuery = document.getElementById("search-query");
  var searchSubmit = document.getElementById("search-submit");
  var searchClear = document.getElementById("search-clear");
  var searchMessage = document.getElementById("search-message");
  var searchSummary = document.getElementById("search-summary");
  var searchResultsWrap = document.getElementById("search-results-wrap");
  var searchRows = document.getElementById("search-rows");
  var isSearching = false;

  function clearSearchResults() {
    searchQuery.value = "";
    bms.clear(searchRows);
    bms.hide(searchMessage);
    searchSummary.textContent = "";
    searchResultsWrap.setAttribute("hidden", "");
  }

  searchClear.addEventListener("click", function () {
    clearSearchResults();
  });

  searchForm.addEventListener("submit", async function (event) {
    event.preventDefault();
    if (isSearching) { return; }

    var query = searchQuery.value.trim();
    if (!query) {
      bms.show(searchMessage, "Enter a name, phone number, or account number.", false);
      searchQuery.focus();
      return;
    }

    bms.hide(searchMessage);
    bms.clear(searchRows);
    searchSummary.textContent = "Searching customers and accounts…";
    searchResultsWrap.setAttribute("aria-busy", "true");
    isSearching = true;
    searchSubmit.disabled = true;

    var url = "/customers?q=" + encodeURIComponent(query);

    try {
      var results = await bms.get(url);
      isSearching = false;
      searchSubmit.disabled = false;
      searchResultsWrap.setAttribute("aria-busy", "false");

      if (!Array.isArray(results) || results.length === 0) {
        searchSummary.textContent = "No matching records found.";
        searchResultsWrap.removeAttribute("hidden");
        var emptyRow = bms.el("tr");
        var emptyCell = bms.el("td", "No matching records found.");
        emptyCell.colSpan = 9;
        emptyRow.appendChild(emptyCell);
        searchRows.appendChild(emptyRow);
        return;
      }

      searchSummary.textContent = "Found " + results.length + " matching customer" + (results.length === 1 ? "" : "s") + ".";
      searchResultsWrap.removeAttribute("hidden");

      results.forEach(function (customer) {
        var accounts = customer.accounts || [];
        if (accounts.length > 0) {
          accounts.forEach(function (acc) {
            var row = bms.el("tr");
            row.appendChild(bms.el("td", String(customer.id)));
            row.appendChild(bms.el("td", String(customer.name)));
            row.appendChild(bms.el("td", String(customer.phone)));
            row.appendChild(bms.el("td", String(customer.email)));
            row.appendChild(bms.el("td", String(acc.id)));
            row.appendChild(bms.el("td", String(acc.accountNumber)));
            row.appendChild(bms.el("td", String(acc.type)));
            row.appendChild(bms.el("td", String(acc.status)));
            row.appendChild(bms.el("td", bms.money(acc.balance), "num"));
            searchRows.appendChild(row);
          });
        } else {
          var noAccRow = bms.el("tr");
          noAccRow.appendChild(bms.el("td", String(customer.id)));
          noAccRow.appendChild(bms.el("td", String(customer.name)));
          noAccRow.appendChild(bms.el("td", String(customer.phone)));
          noAccRow.appendChild(bms.el("td", String(customer.email)));
          noAccRow.appendChild(bms.el("td", "—"));
          noAccRow.appendChild(bms.el("td", "No accounts"));
          noAccRow.appendChild(bms.el("td", "—"));
          noAccRow.appendChild(bms.el("td", "—"));
          noAccRow.appendChild(bms.el("td", "—", "num"));
          searchRows.appendChild(noAccRow);
        }
      });
    } catch (error) {
      isSearching = false;
      searchSubmit.disabled = false;
      searchResultsWrap.setAttribute("aria-busy", "false");
      if (error.status === 404 || error.code === "CUSTOMER_NOT_FOUND") {
        searchSummary.textContent = "No matching records found.";
        searchResultsWrap.removeAttribute("hidden");
        var emptyRow = bms.el("tr");
        var emptyCell = bms.el("td", "No matching records found.");
        emptyCell.colSpan = 9;
        emptyRow.appendChild(emptyCell);
        searchRows.appendChild(emptyRow);
      } else {
        searchResultsWrap.setAttribute("hidden", "");
        searchSummary.textContent = "";
        bms.show(searchMessage, error.message || "Search failed.", false);
      }
    }
  });

  // =========================================================================
  // Section 2: Open a Bank Account (US-08)
  // =========================================================================
  var modeNewRadio = document.getElementById("mode-new");
  var modeExistingRadio = document.getElementById("mode-existing");
  var newCustomerFields = document.getElementById("new-customer-fields");
  var existingCustomerFields = document.getElementById("existing-customer-fields");
  var existingCustomerId = document.getElementById("existing-customer-id");

  var openAccountForm = document.getElementById("open-account-form");
  var openAccountSubmit = document.getElementById("open-account-submit");
  var openAccountMessage = document.getElementById("open-account-message");
  var openAccountSuccess = document.getElementById("open-account-success");
  var openAccountDetailsList = document.getElementById("open-account-details-list");
  var tempPasswordBox = document.getElementById("temp-password-box");
  var tempPasswordValue = document.getElementById("temp-password-value");
  var openAccountDismiss = document.getElementById("open-account-dismiss");
  var isOpening = false;

  function updateCustomerMode() {
    var isExisting = modeExistingRadio.checked;
    if (isExisting) {
      newCustomerFields.setAttribute("hidden", "");
      existingCustomerFields.removeAttribute("hidden");
      existingCustomerId.required = true;
    } else {
      existingCustomerFields.setAttribute("hidden", "");
      newCustomerFields.removeAttribute("hidden");
      existingCustomerId.required = false;
    }
  }

  modeNewRadio.addEventListener("change", updateCustomerMode);
  modeExistingRadio.addEventListener("change", updateCustomerMode);

  function clearOpenAccountSuccess() {
    bms.clear(openAccountDetailsList);
    tempPasswordValue.textContent = "";
    tempPasswordBox.setAttribute("hidden", "");
    openAccountSuccess.setAttribute("hidden", "");
  }

  openAccountDismiss.addEventListener("click", function () {
    if (tempPasswordValue.textContent) {
      var ok = window.confirm("Has the customer recorded their temporary password? Once dismissed, it will not be shown again.");
      if (!ok) { return; }
    }
    clearOpenAccountSuccess();
    bms.hide(openAccountMessage);
  });

  openAccountForm.addEventListener("submit", async function (event) {
    event.preventDefault();
    if (isOpening) { return; }

    var isTempPwVisible = tempPasswordBox.getAttribute("hidden") === null && Boolean(tempPasswordValue.textContent.trim());
    if (isTempPwVisible) {
      var proceed = window.confirm("A temporary password is currently displayed. Have you recorded it and want to continue?");
      if (!proceed) {
        return;
      }
    }

    bms.hide(openAccountMessage);
    clearOpenAccountSuccess();

    var accountType = openAccountForm.accountType.value;
    var depositStr = openAccountForm.deposit.value.trim();
    var depositNum = Number(depositStr);

    if (!depositStr || isNaN(depositNum) || depositNum <= 0) {
      bms.show(openAccountMessage, "Opening deposit must be a positive number.", false);
      openAccountForm.deposit.focus();
      return;
    }

    var minReq = MIN_BALANCE[accountType] || 1000;
    if (depositNum < minReq) {
      bms.show(openAccountMessage, accountType + " accounts require an opening deposit of at least Rs " + minReq.toLocaleString("en-IN") + ".", false);
      openAccountForm.deposit.focus();
      return;
    }

    var payload = {
      account_type: accountType,
      deposit: depositStr
    };

    if (modeExistingRadio.checked) {
      var custIdVal = existingCustomerId.value.trim();
      if (!custIdVal || !/^[1-9]\d*$/.test(custIdVal)) {
        bms.show(openAccountMessage, "A valid positive Customer ID is required.", false);
        existingCustomerId.focus();
        return;
      }
      payload.customer_id = parseInt(custIdVal, 10);
    } else {
      var name = openAccountForm.name.value.trim();
      var dob = openAccountForm.dateOfBirth.value.trim();
      var address = openAccountForm.address.value.trim();
      var phone = openAccountForm.phone.value.trim();
      var email = openAccountForm.email.value.trim();
      var idProof = openAccountForm.idProofNumber.value.trim();

      if (!name || !dob || !address || !phone || !email || !idProof) {
        bms.show(openAccountMessage, "All customer fields are required for a new customer.", false);
        return;
      }

      if (!/^\+?[1-9]\d{9,14}$/.test(phone)) {
        bms.show(openAccountMessage, "Phone number must contain 10 to 15 digits and may start with '+'.", false);
        openAccountForm.phone.focus();
        return;
      }

      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        bms.show(openAccountMessage, "Please enter a valid email address.", false);
        openAccountForm.email.focus();
        return;
      }

      payload.name = name;
      payload.date_of_birth = dob;
      payload.address = address;
      payload.phone = phone;
      payload.email = email;
      payload.id_proof_number = idProof;
    }

    isOpening = true;
    openAccountSubmit.disabled = true;
    openAccountSubmit.textContent = "Opening account…";

    try {
      var result = await bms.post("/accounts", payload);
      isOpening = false;
      openAccountSubmit.disabled = false;
      openAccountSubmit.textContent = "Open account";

      // Clear form inputs
      if (modeExistingRadio.checked) {
        existingCustomerId.value = "";
      } else {
        openAccountForm.name.value = "";
        openAccountForm.dateOfBirth.value = "";
        openAccountForm.address.value = "";
        openAccountForm.phone.value = "";
        openAccountForm.email.value = "";
        openAccountForm.idProofNumber.value = "";
      }
      openAccountForm.deposit.value = "";

      // Populate success card
      bms.clear(openAccountDetailsList);
      appendDetail(openAccountDetailsList, "Customer ID:", String(result.customer_id));
      appendDetail(openAccountDetailsList, "Account ID:", String(result.account_id));
      appendDetail(openAccountDetailsList, "Account number:", String(result.account_number));
      appendDetail(openAccountDetailsList, "Account type:", String(result.account_type));
      appendDetail(openAccountDetailsList, "Opening balance:", bms.money(result.balance));
      appendDetail(openAccountDetailsList, "Account status:", String(result.status));

      if (result.temporary_password) {
        tempPasswordValue.textContent = String(result.temporary_password);
        tempPasswordBox.removeAttribute("hidden");
      } else {
        tempPasswordValue.textContent = "";
        tempPasswordBox.setAttribute("hidden", "");
      }

      openAccountSuccess.removeAttribute("hidden");
      bms.show(openAccountMessage, "Account successfully opened for Customer ID " + result.customer_id + ".", true);

    } catch (error) {
      isOpening = false;
      openAccountSubmit.disabled = false;
      openAccountSubmit.textContent = "Open account";
      clearOpenAccountSuccess();
      bms.show(openAccountMessage, error.message || "Failed to open account.", false);
    }
  });

  // =========================================================================
  // Section 3: Update Customer Contact Details (US-10)
  // =========================================================================
  var updateCustomerForm = document.getElementById("update-customer-form");
  var updateCustomerId = document.getElementById("update-customer-id");
  var updatePhone = document.getElementById("update-phone");
  var updateEmail = document.getElementById("update-email");
  var updateAddress = document.getElementById("update-address");
  var updateCustomerSubmit = document.getElementById("update-customer-submit");
  var updateCustomerClear = document.getElementById("update-customer-clear");
  var updateCustomerMessage = document.getElementById("update-customer-message");
  var updateCustomerSuccess = document.getElementById("update-customer-success");
  var updateCustomerDetailsList = document.getElementById("update-customer-details-list");
  var isUpdating = false;

  function clearCustomerUpdate() {
    updateCustomerId.value = "";
    updatePhone.value = "";
    updateEmail.value = "";
    updateAddress.value = "";
    bms.clear(updateCustomerDetailsList);
    updateCustomerSuccess.setAttribute("hidden", "");
    bms.hide(updateCustomerMessage);
  }

  updateCustomerClear.addEventListener("click", function () {
    clearCustomerUpdate();
  });

  updateCustomerForm.addEventListener("submit", async function (event) {
    event.preventDefault();
    if (isUpdating) { return; }

    bms.hide(updateCustomerMessage);
    bms.clear(updateCustomerDetailsList);
    updateCustomerSuccess.setAttribute("hidden", "");

    var custIdVal = updateCustomerId.value.trim();
    if (!custIdVal || !/^[1-9]\d*$/.test(custIdVal)) {
      bms.show(updateCustomerMessage, "A valid positive Customer ID is required.", false);
      updateCustomerId.focus();
      return;
    }

    var phoneVal = updatePhone.value.trim();
    var emailVal = updateEmail.value.trim();
    var addrVal = updateAddress.value.trim();

    if (!phoneVal && !emailVal && !addrVal) {
      bms.show(updateCustomerMessage, "At least one field (phone, email, or address) must be provided to update.", false);
      return;
    }

    var payload = {};

    if (phoneVal) {
      if (!/^\+?[1-9]\d{9,14}$/.test(phoneVal)) {
        bms.show(updateCustomerMessage, "Phone number must contain 10 to 15 digits and may start with '+'.", false);
        updatePhone.focus();
        return;
      }
      payload.phone = phoneVal;
    }

    if (emailVal) {
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailVal)) {
        bms.show(updateCustomerMessage, "Please enter a valid email address.", false);
        updateEmail.focus();
        return;
      }
      payload.email = emailVal;
    }

    if (addrVal) {
      if (addrVal.length > 255) {
        bms.show(updateCustomerMessage, "Address cannot exceed 255 characters.", false);
        updateAddress.focus();
        return;
      }
      payload.address = addrVal;
    }

    isUpdating = true;
    updateCustomerSubmit.disabled = true;
    updateCustomerSubmit.textContent = "Updating details…";

    try {
      var result = await bms.put("/customers/" + encodeURIComponent(custIdVal), payload);
      isUpdating = false;
      updateCustomerSubmit.disabled = false;
      updateCustomerSubmit.textContent = "Update contact details";

      // Clear input fields
      updatePhone.value = "";
      updateEmail.value = "";
      updateAddress.value = "";

      // Render updated details
      bms.clear(updateCustomerDetailsList);
      appendDetail(updateCustomerDetailsList, "Customer ID:", String(result.id));
      appendDetail(updateCustomerDetailsList, "Customer name:", String(result.name));
      appendDetail(updateCustomerDetailsList, "Date of birth:", String(result.date_of_birth));
      appendDetail(updateCustomerDetailsList, "Phone:", String(result.phone));
      appendDetail(updateCustomerDetailsList, "Email:", String(result.email));
      appendDetail(updateCustomerDetailsList, "Address:", String(result.address));

      updateCustomerSuccess.removeAttribute("hidden");
      bms.show(updateCustomerMessage, "Contact details successfully updated for Customer ID " + result.id + ".", true);

    } catch (error) {
      isUpdating = false;
      updateCustomerSubmit.disabled = false;
      updateCustomerSubmit.textContent = "Update contact details";
      updateCustomerSuccess.setAttribute("hidden", "");
      bms.show(updateCustomerMessage, error.message || "Failed to update customer details.", false);
    }
  });

})();
