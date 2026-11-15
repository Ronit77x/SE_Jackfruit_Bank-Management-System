/* Customer-owned accounts, history and audited CSV download. Owner: Ronit. */
(function () {
  "use strict";
  if (!bms.requireRole(["Customer"])) { return; }
  bms.header("My accounts");
  var ids = ["account", "account-summary", "account-message", "retry-accounts", "activity", "history-form",
    "date-from", "date-to", "range-button", "latest-button", "download-button", "history-message",
    "history-summary", "history-results", "history-rows", "pagination", "previous-button", "next-button"];
  var ui = {};
  ids.forEach(function (id) { ui[id] = document.getElementById(id); });
  var accounts = [], generation = 0, busy = false, mode = "latest", offset = 0, range = null;
  var pageSize = 25, current = null;

  function controls(working) {
    busy = working;
    ["range-button", "latest-button", "download-button", "previous-button", "next-button"].forEach(function (id) {
      ui[id].disabled = working;
    });
    ui["history-results"].setAttribute("aria-busy", String(working));
  }
  function clearResults() {
    bms.clear(ui["history-rows"]);
    ui.pagination.hidden = true;
    ui["history-summary"].textContent = "";
  }
  function selected() { return accounts.find(function (a) { return String(a.account_id) === ui.account.value; }); }
  function endpoint(account, suffix) { return "/accounts/by-id/" + encodeURIComponent(account.account_id) + "/" + suffix; }
  function dates() {
    var from = ui["date-from"].value, to = ui["date-to"].value;
    if (!ui["history-form"].reportValidity()) { return null; }
    if (from > to) { bms.show(ui["history-message"], "From date must be on or before To date.", false); return null; }
    return { from: from, to: to };
  }
  function formatTime(value) {
    var date = new Date(value);
    return isNaN(date.getTime()) ? String(value) : date.toLocaleString("en-IN", {
      timeZone: "Asia/Kolkata", year: "numeric", month: "short", day: "2-digit",
      hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false
    });
  }
  function render(data) {
    bms.clear(ui["history-rows"]);
    data.transactions.forEach(function (txn) {
      var row = bms.el("tr");
      [formatTime(txn.createdAt), txn.type, bms.money(txn.amount), bms.money(txn.balanceAfter),
        [txn.receiptNo, txn.reference].filter(Boolean).join(" / ") || "—"].forEach(function (text, index) {
        row.appendChild(bms.el("td", text, index === 2 || index === 3 ? "num" : ""));
      });
      ui["history-rows"].appendChild(row);
    });
    if (!data.count) {
      var row = bms.el("tr"), cell = bms.el("td", "No transactions found.");
      cell.colSpan = 5; row.appendChild(cell); ui["history-rows"].appendChild(row);
    }
    ui["history-summary"].textContent = data.miniStatement ?
      "Latest " + data.count + " of " + data.total + " transactions. Use a date range to see more." :
      (data.count ? "Showing " + (offset + 1) + "–" + (offset + data.count) : "Showing 0") +
      " of " + data.total + " transactions, " + range.from + " to " + range.to + " (IST).";
    ui.pagination.hidden = data.miniStatement || (!offset && !data.hasMore);
    ui["previous-button"].disabled = offset === 0;
    ui["next-button"].disabled = !data.hasMore;
  }
  async function loadHistory() {
    var account = selected();
    if (!account) { return; }
    var ticket = ++generation;
    bms.hide(ui["history-message"]); clearResults(); controls(true);
    ui["history-summary"].textContent = "Loading transactions…";
    var params = new URLSearchParams();
    if (mode === "range") {
      params.set("from", range.from); params.set("to", range.to);
      params.set("limit", String(pageSize)); params.set("offset", String(offset));
    }
    try {
      var data = await bms.get(endpoint(account, "transactions") + (params.size ? "?" + params.toString() : ""));
      if (ticket !== generation) { return; }
      controls(false); current = data; render(data);
    } catch (error) {
      if (ticket !== generation) { return; }
      controls(false); current = null; clearResults();
      ui["previous-button"].disabled = true; ui["next-button"].disabled = true;
      bms.show(ui["history-message"], error.message, false);
    }
  }
  function chooseAccount() {
    ++generation; current = null; clearResults(); bms.hide(ui["history-message"]);
    var account = selected();
    ui.activity.hidden = !account;
    if (!account) { ui["account-summary"].textContent = ""; return; }
    ui["account-summary"].textContent = account.account_type + " · " + account.account_number +
      " · " + account.status + " · Balance: " + bms.money(account.balance);
    mode = "latest"; offset = 0; range = null;
    loadHistory();
  }
  async function loadAccounts() {
    ui.account.disabled = true; ui["retry-accounts"].hidden = true;
    bms.hide(ui["account-message"]);
    try {
      var data = await bms.get("/accounts"); accounts = data.accounts;
      bms.clear(ui.account);
      accounts.forEach(function (account, index) {
        // The internal ID distinguishes accounts even if their last four digits match.
        var option = bms.el("option", "Account " + (index + 1) + " · " + account.account_number + " · " + account.account_type);
        option.value = String(account.account_id); ui.account.appendChild(option);
      });
      if (!accounts.length) {
        ui.account.appendChild(bms.el("option", "No accounts available"));
        bms.show(ui["account-message"], "You have no accounts yet. Contact a Teller for help.", true);
        ui.activity.hidden = true; return;
      }
      ui.account.disabled = false; ui.account.value = String(accounts[0].account_id); chooseAccount();
    } catch (error) {
      bms.clear(ui.account); ui.account.appendChild(bms.el("option", "Accounts unavailable"));
      bms.show(ui["account-message"], error.message, false); ui["retry-accounts"].hidden = false;
    }
  }
  ui.account.addEventListener("change", chooseAccount);
  ui["retry-accounts"].addEventListener("click", loadAccounts);
  ui["history-form"].addEventListener("submit", function (event) {
    event.preventDefault(); if (busy) { return; }
    bms.hide(ui["history-message"]); var value = dates(); if (!value) { return; }
    mode = "range"; range = value; offset = 0; loadHistory();
  });
  ui["latest-button"].addEventListener("click", function () {
    if (busy) { return; } mode = "latest"; offset = 0; range = null; loadHistory();
  });
  ui["next-button"].addEventListener("click", function () {
    if (busy || !current || !current.hasMore || mode !== "range") { return; }
    offset += pageSize; loadHistory();
  });
  ui["previous-button"].addEventListener("click", function () {
    if (busy || !offset || mode !== "range") { return; } offset = Math.max(0, offset - pageSize); loadHistory();
  });
  ui["download-button"].addEventListener("click", async function () {
    if (busy) { return; } bms.hide(ui["history-message"]);
    var value = dates(), account = selected(); if (!value || !account) { return; }
    var ticket = generation; controls(true);
    ui["history-message"].textContent = "";
    try {
      await bms.download(endpoint(account, "statement") + "?" + new URLSearchParams({ from: value.from, to: value.to, format: "csv" }), "statement.csv");
      if (ticket === generation) { bms.show(ui["history-message"], "CSV downloaded for " + value.from + " to " + value.to + " (IST).", true); }
    } catch (error) {
      if (ticket === generation) { bms.show(ui["history-message"], error.message, false); }
    } finally {
      if (ticket === generation) { controls(false); if (current) { render(current); } }
    }
  });
  loadAccounts();
})();
