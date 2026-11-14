/* Shared browser helpers. Owner: Ronit.
 *
 * Every page loads this file first:   <script src="/ui/js/api.js"></script>
 * and then uses the global object `bms`.
 *
 * SAFETY RULE (BMS-SR-005): never put text that came from the server (or from a user) into the page as HTML.
 * That means none of the browser's HTML-insertion APIs (the ones whose names end in "HTML", and document-write).
 * Use textContent, or the helpers bms.el(...) and bms.clear(...). A test (tests/test_ui_safety.py) fails if
 * those APIs appear in any file under app/static.
 */
(function () {
  "use strict";

  var KEYS = { token: "bms_token", role: "bms_role", must: "bms_must_change", user: "bms_username" };

  function store(key, value) {
    if (value === null || value === undefined) { sessionStorage.removeItem(key); }
    else { sessionStorage.setItem(key, value); }
  }

  var bms = {
    // ---- session state (kept per browser tab) ----
    token: function () { return sessionStorage.getItem(KEYS.token); },
    role: function () { return sessionStorage.getItem(KEYS.role); },
    username: function () { return sessionStorage.getItem(KEYS.user); },
    mustChangePassword: function () { return sessionStorage.getItem(KEYS.must) === "true"; },
    isLoggedIn: function () { return !!sessionStorage.getItem(KEYS.token); },

    forget: function () { Object.keys(KEYS).forEach(function (k) { store(KEYS[k], null); }); },

    // ---- API calls ----
    request: async function (method, path, body) {
      var headers = { "Accept": "application/json" };
      if (body !== undefined) { headers["Content-Type"] = "application/json"; }
      if (bms.token()) { headers["Authorization"] = "Bearer " + bms.token(); }

      var response;
      try {
        response = await fetch(path, {
          method: method,
          headers: headers,
          body: body === undefined ? undefined : JSON.stringify(body)
        });
      } catch (networkError) {
        throw bms.makeError(0, "NETWORK_ERROR", "Cannot reach the server. Is it running?");
      }

      var data = null;
      var type = response.headers.get("content-type") || "";
      if (type.indexOf("application/json") !== -1) { data = await response.json(); }

      if (!response.ok) {
        var message = (data && (data.message || data.detail)) || ("Request failed (" + response.status + ")");
        if (response.status === 401 && path !== "/auth/login") {
          bms.forget();                      // session ended or invalid: back to the login page
          window.location.href = "/ui/index.html?expired=1";
        }
        throw bms.makeError(response.status, (data && data.code) || "ERROR", String(message));
      }
      return data;
    },

    makeError: function (status, code, message) {
      var error = new Error(message);
      error.status = status;
      error.code = code;
      return error;
    },

    get: function (path) { return bms.request("GET", path); },
    post: function (path, body) { return bms.request("POST", path, body === undefined ? {} : body); },
    put: function (path, body) { return bms.request("PUT", path, body); },
    patch: function (path, body) { return bms.request("PATCH", path, body); },

    // Downloads a file with the login token and saves it (a plain link cannot send the Authorization header).
    download: async function (path, fallbackName) {
      var response = await fetch(path, { headers: { "Authorization": "Bearer " + bms.token() } });
      if (!response.ok) {
        var message = "Download failed (" + response.status + ")";
        try { var data = await response.json(); message = data.message || message; } catch (ignore) { /* keep message */ }
        if (response.status === 401) { bms.forget(); window.location.href = "/ui/index.html?expired=1"; }
        throw bms.makeError(response.status, "DOWNLOAD_FAILED", message);
      }
      var blob = await response.blob();
      var name = fallbackName || "download";
      var disposition = response.headers.get("content-disposition") || "";
      var match = /filename="?([^";]+)"?/i.exec(disposition);
      if (match) { name = match[1]; }
      var link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = name;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(link.href);
    },

    // ---- login / logout ----
    login: async function (username, password) {
      var result = await bms.post("/auth/login", { username: username, password: password });
      store(KEYS.token, result.token);
      store(KEYS.role, result.role);
      store(KEYS.must, String(result.mustChangePassword));
      store(KEYS.user, username);
      return result;
    },

    logout: async function () {
      try { if (bms.token()) { await bms.request("POST", "/auth/logout"); } } catch (ignore) { /* leave anyway */ }
      bms.forget();
      window.location.href = "/ui/index.html";
    },

    // Call at the top of a page: sends the visitor to the login page unless a user with one of `roles` is logged in.
    // A user who must still change a temporary password is sent to the change-password page.
    requireRole: function (roles) {
      if (!bms.isLoggedIn()) { window.location.href = "/ui/index.html"; return false; }
      if (bms.mustChangePassword() && window.location.pathname.indexOf("change-password") === -1) {
        window.location.href = "/ui/change-password.html"; return false;
      }
      if (roles && roles.indexOf(bms.role()) === -1) { window.location.href = "/ui/index.html"; return false; }
      return true;
    },

    // ---- safe DOM helpers (textContent only) ----
    el: function (tag, text, className) {
      var node = document.createElement(tag);
      if (text !== undefined && text !== null) { node.textContent = String(text); }
      if (className) { node.className = className; }
      return node;
    },
    clear: function (node) { node.replaceChildren(); },

    // Shows a message in an element with class "message".
    show: function (node, text, ok) {
      node.textContent = String(text);
      node.className = "message show " + (ok ? "ok" : "error");
    },
    hide: function (node) { node.textContent = ""; node.className = "message"; },

    money: function (value) {
      var number = Number(value);
      return isNaN(number) ? String(value) : "Rs " + number.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    },

    // Header with the page links for the logged-in role. Call bms.header("Page title") once the body exists.
    header: function (title) {
      var host = document.getElementById("site-header");
      if (!host) { return; }
      bms.clear(host);
      host.className = "site";
      host.appendChild(bms.el("h1", "Bank Management System - " + title));
      var nav = bms.el("nav");
      var links = {
        Customer: [["customer.html", "My accounts"], ["change-password.html", "Change password"]],
        Teller: [["teller-accounts.html", "Accounts"], ["teller-cash.html", "Cash"], ["change-password.html", "Change password"]],
        Admin: [["admin.html", "Administration"], ["change-password.html", "Change password"]]
      }[bms.role()] || [];
      links.forEach(function (item) {
        var a = bms.el("a", item[1]);
        a.href = "/ui/" + item[0];
        nav.appendChild(a);
      });
      if (bms.isLoggedIn()) {
        var out = bms.el("a", "Log out (" + bms.username() + ")");
        out.href = "#";
        out.addEventListener("click", function (event) { event.preventDefault(); bms.logout(); });
        nav.appendChild(out);
      }
      host.appendChild(nav);
    }
  };

  window.bms = bms;
})();
