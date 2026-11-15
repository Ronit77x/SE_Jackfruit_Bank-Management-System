/* Admin UI for Teller management, audit filtering and daily reports. */
(function () {
  "use strict";
  if (!bms.requireRole(["Admin"])) { return; }
  bms.header("Administration");

  var tellerMessage = document.getElementById("teller-message");
  var auditMessage = document.getElementById("audit-message");
  var reportMessage = document.getElementById("report-message");
  var auditBody = document.querySelector("#audit-table tbody");
  var reportResults = document.getElementById("report-results");

  function showError(node, error) { bms.show(node, error.message || "Request failed.", false); }
  function addCell(row, value, className) { row.appendChild(bms.el("td", value, className)); }
  function queryFromForm(form) {
    var params = new URLSearchParams();
    Array.prototype.forEach.call(form.elements, function (field) {
      if (field.name && field.value.trim()) { params.set(field.name, field.value.trim()); }
    });
    return params;
  }

  document.getElementById("create-teller-form").addEventListener("submit", async function (event) {
    event.preventDefault();
    bms.hide(tellerMessage);
    var form = event.currentTarget;
    try {
      var user = await bms.post("/admin/users", { username: form.username.value.trim(), password: form.password.value });
      bms.show(tellerMessage, "Teller created. User ID: " + user.id + ".", true);
      form.reset();
    } catch (error) { showError(tellerMessage, error); }
  });

  document.getElementById("teller-action-form").addEventListener("submit", async function (event) {
    event.preventDefault();
    bms.hide(tellerMessage);
    var form = event.currentTarget;
    try {
      var action = form.elements.namedItem("action").value;
      var user = await bms.patch("/admin/users/" + encodeURIComponent(form.userId.value.trim()), { action: action });
      bms.show(tellerMessage, "Teller " + user.id + " is now " + user.status + ".", true);
    } catch (error) { showError(tellerMessage, error); }
  });

  document.getElementById("audit-form").addEventListener("submit", async function (event) {
    event.preventDefault();
    bms.hide(auditMessage);
    bms.clear(auditBody);
    try {
      var entries = await bms.get("/admin/audit-logs?" + queryFromForm(event.currentTarget).toString());
      entries.forEach(function (entry) {
        var row = bms.el("tr");
        addCell(row, new Date(entry.timestamp).toLocaleString());
        addCell(row, entry.user_id === null ? "System" : entry.user_id);
        addCell(row, entry.action);
        addCell(row, entry.outcome);
        addCell(row, entry.details);
        auditBody.appendChild(row);
      });
      bms.show(auditMessage, entries.length + " audit entr" + (entries.length === 1 ? "y" : "ies") + " loaded.", true);
    } catch (error) { showError(auditMessage, error); }
  });

  function reportCard(title, summary) {
    var card = bms.el("article", undefined, "report-card");
    card.appendChild(bms.el("h3", title));
    card.appendChild(bms.el("p", summary.count + " transaction" + (summary.count === 1 ? "" : "s")));
    card.appendChild(bms.el("strong", bms.money(summary.total_amount)));
    return card;
  }

  function localDate(value) {
    var year = value.getFullYear();
    var month = String(value.getMonth() + 1).padStart(2, "0");
    var day = String(value.getDate()).padStart(2, "0");
    return year + "-" + month + "-" + day;
  }
  document.getElementById("report-date").value = localDate(new Date());
  document.getElementById("report-form").addEventListener("submit", async function (event) {
    event.preventDefault();
    bms.hide(reportMessage);
    reportResults.setAttribute("hidden", "");
    try {
      var date = event.currentTarget.date.value;
      var report = await bms.get("/admin/reports/daily?date=" + encodeURIComponent(date));
      bms.clear(reportResults);
      reportResults.appendChild(reportCard("Deposits", report.deposits));
      reportResults.appendChild(reportCard("Withdrawals", report.withdrawals));
      reportResults.appendChild(reportCard("Transfers", report.transfers));
      reportResults.appendChild(bms.el("p", "Report date: " + report.report_date + " (" + report.timezone + ")", "muted"));
      reportResults.removeAttribute("hidden");
      bms.show(reportMessage, "Daily report generated.", true);
    } catch (error) { showError(reportMessage, error); }
  });
})();
