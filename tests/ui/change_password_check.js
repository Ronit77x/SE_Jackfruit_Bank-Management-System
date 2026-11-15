// Unit and behaviour checks for app/static/change-password.html, run by pytest with Node.
const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const htmlPath = path.join(__dirname, "..", "..", "app", "static", "change-password.html");
const apiJsPath = path.join(__dirname, "..", "..", "app", "static", "js", "api.js");
const html = fs.readFileSync(htmlPath, "utf8");
const apiJs = fs.readFileSync(apiJsPath, "utf8");

// 1. Static HTML structure checks
assert.ok(html.includes('name="viewport"'), "Page must have viewport meta tag");
assert.ok(html.includes('/ui/css/style.css'), "Page must load style.css");
assert.ok(html.includes('/ui/js/api.js'), "Page must load api.js");
assert.ok(html.includes('id="change-password-form"'), "Page must have change-password-form");
assert.ok(html.includes('id="current-password"'), "Page must have current-password field");
assert.ok(html.includes('id="new-password"'), "Page must have new-password field");
assert.ok(html.includes('id="confirm-password"'), "Page must have confirm-password field");
assert.ok(html.includes('id="mandatory-notice"'), "Page must have mandatory-notice banner");
assert.ok(html.includes('id="change-message"'), "Page must have change-message element");
assert.ok(html.includes('id="submit-btn"'), "Page must have submit-btn");
assert.ok(html.includes('toggle-password'), "Page must have show/hide toggle buttons");

// Helper to create simulated DOM elements
function createFakeElement(tagName, id = "", className = "") {
  const listeners = {};
  const attrs = {};
  const children = [];
  return {
    tagName: tagName.toUpperCase(),
    id,
    className,
    value: "",
    type: tagName.toLowerCase() === "input" ? "password" : "",
    textContent: "",
    disabled: false,
    style: {},
    children,
    addEventListener(evt, fn) {
      if (!listeners[evt]) listeners[evt] = [];
      listeners[evt].push(fn);
    },
    async dispatch(evt, eventObj = {}) {
      if (listeners[evt]) {
        for (const fn of listeners[evt]) {
          await fn({ preventDefault() {}, ...eventObj });
        }
      }
    },
    setAttribute(name, val) { attrs[name] = String(val); },
    getAttribute(name) { return Object.prototype.hasOwnProperty.call(attrs, name) ? attrs[name] : null; },
    removeAttribute(name) { delete attrs[name]; },
    focus() { this.focused = true; },
    appendChild(child) { children.push(child); },
    replaceChildren() { children.length = 0; },
  };
}

// Helper to simulate the page environment
function setupPageContext({ token = "test-token", role = "Customer", mustChange = "false", username = "cust1" } = {}) {
  const store = {
    bms_token: token,
    bms_role: role,
    bms_must_change: mustChange,
    bms_username: username,
  };
  if (!token) delete store.bms_token;

  const sessionStorage = {
    getItem: (k) => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
    removeItem: (k) => { delete store[k]; },
  };

  const window = {
    location: { href: "/ui/change-password.html", pathname: "/ui/change-password.html" },
  };

  const siteHeader = createFakeElement("header", "site-header");
  const form = createFakeElement("form", "change-password-form");
  const currentInput = createFakeElement("input", "current-password");
  currentInput.name = "currentPassword";
  currentInput.type = "password";

  const newInput = createFakeElement("input", "new-password");
  newInput.name = "newPassword";
  newInput.type = "password";

  const confirmInput = createFakeElement("input", "confirm-password");
  confirmInput.name = "confirmPassword";
  confirmInput.type = "password";

  form.currentPassword = currentInput;
  form.newPassword = newInput;
  form.confirmPassword = confirmInput;

  const toggleCurrent = createFakeElement("button", "toggle-curr", "secondary toggle-password");
  toggleCurrent.setAttribute("data-target", "current-password");

  const toggleNew = createFakeElement("button", "toggle-new", "secondary toggle-password");
  toggleNew.setAttribute("data-target", "new-password");

  const toggleConfirm = createFakeElement("button", "toggle-conf", "secondary toggle-password");
  toggleConfirm.setAttribute("data-target", "confirm-password");

  const mandatoryNotice = createFakeElement("div", "mandatory-notice", "message show error");
  mandatoryNotice.setAttribute("hidden", "");

  const changeMessage = createFakeElement("div", "change-message", "message");
  const submitBtn = createFakeElement("button", "submit-btn");
  const successActions = createFakeElement("div", "success-actions");
  successActions.setAttribute("hidden", "");
  const continueBtn = createFakeElement("button", "continue-btn");

  const elementsById = {
    "site-header": siteHeader,
    "change-password-form": form,
    "current-password": currentInput,
    "new-password": newInput,
    "confirm-password": confirmInput,
    "mandatory-notice": mandatoryNotice,
    "change-message": changeMessage,
    "submit-btn": submitBtn,
    "success-actions": successActions,
    "continue-btn": continueBtn,
  };

  const allToggles = [toggleCurrent, toggleNew, toggleConfirm];

  const document = {
    getElementById(id) { return elementsById[id] || null; },
    querySelectorAll(selector) {
      if (selector === ".toggle-password") return allToggles;
      if (selector === "#site-header nav a") return siteHeader.children;
      return [];
    },
    createElement(tag) { return createFakeElement(tag); },
    body: { appendChild() {} },
  };

  let nextResponse = null;
  const calls = [];
  const fetch = async (url, options) => {
    calls.push({ url, options });
    return nextResponse;
  };

  const context = {
    window,
    sessionStorage,
    console,
    URL,
    TextEncoder,
    setTimeout: (fn, delay) => { fn(); },
    document,
    fetch,
  };

  vm.createContext(context);
  vm.runInContext(apiJs, context);
  context.bms = context.window.bms;

  // Extract the inline script from change-password.html
  const scriptMatch = /<script>([\s\S]*?)<\/script>[\s\S]*?<\/body>/i.exec(html);
  assert.ok(scriptMatch, "Inline script must be present in change-password.html");
  const scriptContent = scriptMatch[1];

  function runScript() {
    vm.runInContext(scriptContent, context);
  }

  return {
    context,
    window,
    store,
    form,
    currentInput,
    newInput,
    confirmInput,
    allToggles,
    toggleCurrent,
    mandatoryNotice,
    changeMessage,
    submitBtn,
    continueBtn,
    calls,
    setNextResponse: (r) => { nextResponse = r; },
    runScript,
  };
}

(async () => {
  // 1. Unauthenticated visitor redirects to /ui/index.html
  {
    const page = setupPageContext({ token: null });
    page.runScript();
    assert.strictEqual(page.window.location.href, "/ui/index.html");
  }

  // 2. Normal authenticated customer loads page without mandatory notice
  {
    const page = setupPageContext({ mustChange: "false" });
    page.runScript();
    assert.strictEqual(page.window.location.href, "/ui/change-password.html");
    assert.ok(page.mandatoryNotice.getAttribute("hidden") !== null);
  }

  // 3. User with mandatory password change shows notice banner
  {
    const page = setupPageContext({ mustChange: "true" });
    page.runScript();
    assert.strictEqual(page.window.location.href, "/ui/change-password.html");
    assert.strictEqual(page.mandatoryNotice.getAttribute("hidden"), null);
  }

  // 4. Show/hide toggle button toggles input type
  {
    const page = setupPageContext();
    page.runScript();
    assert.strictEqual(page.currentInput.type, "password");
    await page.toggleCurrent.dispatch("click");
    assert.strictEqual(page.currentInput.type, "text");
    assert.strictEqual(page.toggleCurrent.textContent, "Hide");
    assert.strictEqual(page.toggleCurrent.getAttribute("aria-pressed"), "true");
    await page.toggleCurrent.dispatch("click");
    assert.strictEqual(page.currentInput.type, "password");
    assert.strictEqual(page.toggleCurrent.textContent, "Show");
    assert.strictEqual(page.toggleCurrent.getAttribute("aria-pressed"), "false");
  }

  // 5. Client-side validation: empty current password
  {
    const page = setupPageContext();
    page.runScript();
    page.form.currentPassword.value = "";
    page.form.newPassword.value = "NewStrong1!";
    page.form.confirmPassword.value = "NewStrong1!";
    await page.form.dispatch("submit");
    assert.ok(page.changeMessage.textContent.includes("Current password is required"));
  }

  // 6. Client-side validation: empty new password
  {
    const page = setupPageContext();
    page.runScript();
    page.form.currentPassword.value = "OldPass1!";
    page.form.newPassword.value = "";
    page.form.confirmPassword.value = "NewStrong1!";
    await page.form.dispatch("submit");
    assert.ok(page.changeMessage.textContent.includes("New password is required"));
  }

  // 7. Client-side validation: empty confirm password
  {
    const page = setupPageContext();
    page.runScript();
    page.form.currentPassword.value = "OldPass1!";
    page.form.newPassword.value = "NewStrong1!";
    page.form.confirmPassword.value = "";
    await page.form.dispatch("submit");
    assert.ok(page.changeMessage.textContent.includes("confirm your new password"));
  }

  // 8. Client-side validation: new and confirm password mismatch
  {
    const page = setupPageContext();
    page.runScript();
    page.form.currentPassword.value = "OldPass1!";
    page.form.newPassword.value = "NewStrong1!";
    page.form.confirmPassword.value = "Mismatch2@";
    await page.form.dispatch("submit");
    assert.ok(page.changeMessage.textContent.includes("do not match"));
  }

  // 9. Client-side validation: new password identical to current password
  {
    const page = setupPageContext();
    page.runScript();
    page.form.currentPassword.value = "SamePass1!";
    page.form.newPassword.value = "SamePass1!";
    page.form.confirmPassword.value = "SamePass1!";
    await page.form.dispatch("submit");
    assert.ok(page.changeMessage.textContent.includes("different from current password"));
  }

  // 10. Client-side validation: complexity failures
  {
    const page = setupPageContext();
    page.runScript();

    // Too short (< 8 chars)
    page.form.currentPassword.value = "OldPass1!";
    page.form.newPassword.value = "Short1!";
    page.form.confirmPassword.value = "Short1!";
    await page.form.dispatch("submit");
    assert.ok(page.changeMessage.textContent.includes("at least 8 characters"));

    // Missing uppercase
    page.form.newPassword.value = "lowercase123!";
    page.form.confirmPassword.value = "lowercase123!";
    await page.form.dispatch("submit");
    assert.ok(page.changeMessage.textContent.includes("uppercase"));

    // Missing lowercase
    page.form.newPassword.value = "UPPERCASE123!";
    page.form.confirmPassword.value = "UPPERCASE123!";
    await page.form.dispatch("submit");
    assert.ok(page.changeMessage.textContent.includes("lowercase"));

    // Missing digit
    page.form.newPassword.value = "NoDigitsAllowed!";
    page.form.confirmPassword.value = "NoDigitsAllowed!";
    await page.form.dispatch("submit");
    assert.ok(page.changeMessage.textContent.includes("digit"));

    // Exceeds 72 bytes
    page.form.newPassword.value = "A1a" + "x".repeat(70);
    page.form.confirmPassword.value = "A1a" + "x".repeat(70);
    await page.form.dispatch("submit");
    assert.ok(page.changeMessage.textContent.includes("72 bytes"));
  }

  // 11. Backend rejection (e.g. incorrect current password - 400 Bad Request)
  {
    const page = setupPageContext();
    page.setNextResponse({
      ok: false,
      status: 400,
      headers: { get: () => "application/json" },
      json: async () => ({ detail: "Incorrect current password" }),
    });
    page.runScript();
    page.form.currentPassword.value = "WrongCurrent1!";
    page.form.newPassword.value = "NewStrongPass1!";
    page.form.confirmPassword.value = "NewStrongPass1!";
    await page.form.dispatch("submit");

    assert.strictEqual(page.calls.length, 1);
    assert.strictEqual(page.calls[0].url, "/auth/change-password");
    assert.ok(page.changeMessage.textContent.includes("Incorrect current password"));
    assert.strictEqual(page.submitBtn.disabled, false);
    assert.strictEqual(page.form.newPassword.value, "");
    assert.strictEqual(page.form.confirmPassword.value, "");
  }

  // 12. Successful password change for Customer
  {
    const page = setupPageContext({ role: "Customer", mustChange: "true" });
    page.setNextResponse({
      ok: true,
      status: 200,
      headers: { get: () => "application/json" },
      json: async () => ({ message: "Password changed successfully" }),
    });
    page.runScript();
    page.form.currentPassword.value = "OldTempPass1!";
    page.form.newPassword.value = "NewStrongPass1!";
    page.form.confirmPassword.value = "NewStrongPass1!";
    await page.form.dispatch("submit");

    assert.strictEqual(page.calls.length, 1);
    assert.strictEqual(page.calls[0].url, "/auth/change-password");
    assert.deepStrictEqual(JSON.parse(page.calls[0].options.body), {
      currentPassword: "OldTempPass1!",
      newPassword: "NewStrongPass1!",
    });
    // Password fields are wiped
    assert.strictEqual(page.form.currentPassword.value, "");
    assert.strictEqual(page.form.newPassword.value, "");
    assert.strictEqual(page.form.confirmPassword.value, "");
    // Form is locked
    assert.strictEqual(page.form.currentPassword.disabled, true);
    assert.strictEqual(page.form.newPassword.disabled, true);
    // Success feedback is shown
    assert.ok(page.changeMessage.textContent.includes("Password changed successfully"));
    // must_change session flag is updated to false
    assert.strictEqual(page.store.bms_must_change, "false");
    // Destination is customer dashboard
    assert.strictEqual(page.window.location.href, "/ui/customer.html");
  }

  // 13. Successful password change for Teller navigates to teller-cash.html
  {
    const page = setupPageContext({ role: "Teller", mustChange: "false" });
    page.setNextResponse({
      ok: true,
      status: 200,
      headers: { get: () => "application/json" },
      json: async () => ({ message: "Password changed successfully" }),
    });
    page.runScript();
    page.form.currentPassword.value = "OldTeller1!";
    page.form.newPassword.value = "NewTeller2@";
    page.form.confirmPassword.value = "NewTeller2@";
    await page.form.dispatch("submit");

    assert.strictEqual(page.window.location.href, "/ui/teller-cash.html");
  }

  console.log("change-password UI checks passed");
})().catch((err) => {
  console.error("Test failure:", err);
  process.exit(1);
});
