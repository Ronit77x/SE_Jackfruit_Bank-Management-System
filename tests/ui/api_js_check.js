// Behaviour checks for app/static/js/api.js, run by tests/test_ui_api_js.py with Node (no browser needed).
const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const store = {};
const sessionStorage = {
  getItem: (k) => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
  removeItem: (k) => { delete store[k]; },
};
const window = { location: { href: "", pathname: "/ui/customer.html" } };
let nextResponse = null;
const calls = [];

function jsonResponse(status, body) {
  return {
    ok: status < 400,
    status,
    headers: { get: (name) => (name.toLowerCase() === "content-type" ? "application/json" : null) },
    json: async () => body,
  };
}

const context = {
  window, sessionStorage, console, URL,
  document: { createElement: () => ({}), body: { appendChild() {} } },
  fetch: async (url, options) => { calls.push({ url, options }); return nextResponse; },
};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(__dirname, "..", "..", "app", "static", "js", "api.js"), "utf8"), context);
const bms = window.bms;

(async () => {
  // login stores the session and sends the credentials as JSON
  nextResponse = jsonResponse(200, { token: "tok123", role: "Teller", mustChangePassword: false });
  await bms.login("teller1", "Passw0rd!");
  assert.strictEqual(bms.token(), "tok123");
  assert.strictEqual(bms.role(), "Teller");
  assert.strictEqual(bms.mustChangePassword(), false);
  assert.strictEqual(bms.username(), "teller1");
  assert.strictEqual(calls[0].url, "/auth/login");
  assert.deepStrictEqual(JSON.parse(calls[0].options.body), { username: "teller1", password: "Passw0rd!" });

  // later requests carry the token
  nextResponse = jsonResponse(200, { ok: true });
  await bms.get("/auth/anything");
  assert.strictEqual(calls[1].options.headers["Authorization"], "Bearer tok123");

  // server errors surface the readable message and the code
  nextResponse = jsonResponse(422, { code: "INSUFFICIENT_FUNDS", message: "Not enough money." });
  await assert.rejects(() => bms.post("/transactions/withdraw", {}), (e) => e.message === "Not enough money." && e.code === "INSUFFICIENT_FUNDS" && e.status === 422);

  // an old-style FastAPI error body still produces a readable message
  nextResponse = jsonResponse(403, { detail: "Insufficient permissions" });
  await assert.rejects(() => bms.get("/x"), (e) => e.message === "Insufficient permissions");

  // 401 ends the session and sends the user to the login page
  nextResponse = jsonResponse(401, { code: "HTTP_401", message: "Invalid or expired session" });
  await assert.rejects(() => bms.get("/x"));
  assert.strictEqual(bms.isLoggedIn(), false);
  assert.ok(window.location.href.startsWith("/ui/index.html"));

  // a failed login does NOT redirect (the login form shows the message)
  window.location.href = "";
  nextResponse = jsonResponse(401, { code: "HTTP_401", message: "Invalid username or password" });
  await assert.rejects(() => bms.login("x", "y"), (e) => e.message === "Invalid username or password");
  assert.strictEqual(window.location.href, "");

  // role guard
  sessionStorage.setItem("bms_token", "t"); sessionStorage.setItem("bms_role", "Customer"); sessionStorage.setItem("bms_must_change", "false");
  assert.strictEqual(bms.requireRole(["Customer"]), true);
  assert.strictEqual(bms.requireRole(["Teller"]), false);
  assert.strictEqual(window.location.href, "/ui/index.html");

  // a user with a temporary password is sent to the change-password page
  sessionStorage.setItem("bms_must_change", "true");
  window.location.pathname = "/ui/customer.html";
  assert.strictEqual(bms.requireRole(["Customer"]), false);
  assert.strictEqual(window.location.href, "/ui/change-password.html");

  // DOM helpers use textContent, so markup in a value stays plain text
  const node = bms.el("p", "<img src=x onerror=alert(1)>");
  assert.strictEqual(node.textContent, "<img src=x onerror=alert(1)>");

  // money formatting
  assert.strictEqual(bms.money("1500"), "Rs 1,500.00");
  assert.strictEqual(bms.money("123456.5"), "Rs 1,23,456.50");

  console.log("api.js checks passed");
})().catch((error) => { console.error(error); process.exit(1); });
