// Behaviour and unit checks for app/static/teller-accounts.html and app/static/js/teller-accounts.js.
// Run by pytest with Node (no browser required).
const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const htmlPath = path.join(__dirname, "..", "..", "app", "static", "teller-accounts.html");
const jsPath = path.join(__dirname, "..", "..", "app", "static", "js", "teller-accounts.js");
const apiJsPath = path.join(__dirname, "..", "..", "app", "static", "js", "api.js");
const cssPath = path.join(__dirname, "..", "..", "app", "static", "css", "teller-accounts.css");

const html = fs.readFileSync(htmlPath, "utf8");
const tellerJs = fs.readFileSync(jsPath, "utf8");
const apiJs = fs.readFileSync(apiJsPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");

// 1. Static HTML and CSS checks
assert.ok(html.includes('name="viewport"'), "Page must have viewport meta tag");
assert.ok(html.includes('/ui/css/style.css'), "Page must load style.css");
assert.ok(html.includes('/ui/css/teller-accounts.css'), "Page must load teller-accounts.css");
assert.ok(html.includes('/ui/js/api.js'), "Page must load api.js");
assert.ok(html.includes('/ui/js/teller-accounts.js'), "Page must load teller-accounts.js");

// Structural sections check
assert.ok(html.includes('id="search-section"'), "Page must have search section");
assert.ok(html.includes('id="open-account-section"'), "Page must have open account section");
assert.ok(html.includes('id="update-customer-section"'), "Page must have update customer section");

// Search elements check
assert.ok(html.includes('id="search-form"'), "Search form must be present");
assert.ok(html.includes('id="search-query"'), "Search input must be present");
assert.ok(html.includes('id="search-submit"'), "Search submit button must be present");
assert.ok(html.includes('id="search-clear"'), "Search clear button must be present");
assert.ok(html.includes('id="search-results-wrap"'), "Search results wrap must be present");
assert.ok(html.includes('id="search-rows"'), "Search rows tbody must be present");

// Open account elements check
assert.ok(html.includes('id="mode-new"'), "New customer mode radio must be present");
assert.ok(html.includes('id="mode-existing"'), "Existing customer mode radio must be present");
assert.ok(html.includes('id="existing-customer-fields"'), "Existing customer fields container must be present");
assert.ok(html.includes('id="new-customer-fields"'), "New customer fields container must be present");
assert.ok(html.includes('id="existing-customer-id"'), "Existing customer ID input must be present");
assert.ok(html.includes('id="new-customer-name"'), "New customer name input must be present");
assert.ok(html.includes('id="new-customer-dob"'), "New customer DOB input must be present");
assert.ok(html.includes('id="new-customer-address"'), "New customer address input must be present");
assert.ok(html.includes('id="new-customer-phone"'), "New customer phone input must be present");
assert.ok(html.includes('id="new-customer-email"'), "New customer email input must be present");
assert.ok(html.includes('id="new-customer-idproof"'), "New customer ID proof input must be present");
assert.ok(html.includes('id="open-account-type"'), "Account type select must be present");
assert.ok(html.includes('id="open-deposit"'), "Deposit input must be present");
assert.ok(html.includes('id="open-account-submit"'), "Open account submit button must be present");
assert.ok(html.includes('id="open-account-success"'), "Open account success container must be present");
assert.ok(html.includes('id="open-account-details-list"'), "Open account details list must be present");
assert.ok(html.includes('id="temp-password-box"'), "Temporary password callout must be present");
assert.ok(html.includes('id="temp-password-value"'), "Temporary password value element must be present");
assert.ok(html.includes('id="open-account-dismiss"'), "Open account dismiss button must be present");

// Update customer elements check
assert.ok(html.includes('id="update-customer-form"'), "Update customer form must be present");
assert.ok(html.includes('id="update-customer-id"'), "Update customer ID input must be present");
assert.ok(html.includes('id="update-phone"'), "Update phone input must be present");
assert.ok(html.includes('id="update-email"'), "Update email input must be present");
assert.ok(html.includes('id="update-address"'), "Update address input must be present");
assert.ok(html.includes('id="update-customer-submit"'), "Update submit button must be present");
assert.ok(html.includes('id="update-customer-clear"'), "Update clear button must be present");
assert.ok(html.includes('id="update-customer-success"'), "Update success container must be present");
assert.ok(html.includes('id="update-customer-details-list"'), "Update details list must be present");

// CSS [hidden] rule check
assert.ok(css.includes("[hidden]"), "CSS must declare [hidden] rule");
assert.ok(css.includes("display: none !important"), "CSS [hidden] rule must specify display: none !important");

// 2. Safe DOM construction check (no forbidden HTML insertion)
const FORBIDDEN = [/\.innerHTML/, /\.outerHTML/, /insertAdjacentHTML/, /document\.write/, /\beval\(/, /new Function\(/];
FORBIDDEN.forEach((pattern) => {
  assert.ok(!pattern.test(html), "HTML must not contain forbidden pattern: " + pattern);
  assert.ok(!pattern.test(tellerJs), "teller-accounts.js must not contain forbidden pattern: " + pattern);
});

// Helper to create simulated DOM elements
function createFakeElement(tagName, id = "", className = "") {
  const listeners = {};
  const attrs = {};
  const children = [];
  let _textContent = "";
  const el = {
    tagName: tagName.toUpperCase(),
    id,
    className,
    value: "",
    type: tagName.toLowerCase() === "input" ? "text" : "",
    checked: false,
    get textContent() {
      if (children.length > 0) {
        return children.map((c) => (c ? c.textContent || "" : "")).join("");
      }
      return _textContent;
    },
    set textContent(val) {
      _textContent = String(val);
      if (val === "") {
        children.length = 0;
      }
    },
    disabled: false,
    required: false,
    style: {},
    children,
    addEventListener(evt, fn) {
      if (!listeners[evt]) listeners[evt] = [];
      listeners[evt].push(fn);
    },
    async dispatch(evt, eventObj = {}) {
      if (listeners[evt]) {
        for (const fn of listeners[evt]) {
          await fn({ preventDefault() {}, stopPropagation() {}, target: el, ...eventObj });
        }
      }
    },
    setAttribute(name, val) { attrs[name] = String(val); },
    getAttribute(name) { return Object.prototype.hasOwnProperty.call(attrs, name) ? attrs[name] : null; },
    hasAttribute(name) { return Object.prototype.hasOwnProperty.call(attrs, name); },
    removeAttribute(name) { delete attrs[name]; },
    focus() { this.focused = true; },
    appendChild(child) { children.push(child); child.parentNode = el; },
    removeChild(child) {
      const idx = children.indexOf(child);
      if (idx !== -1) children.splice(idx, 1);
    },
    replaceChildren(...newChildren) {
      children.length = 0;
      newChildren.forEach((c) => { children.push(c); c.parentNode = el; });
    },
    get firstChild() { return children[0] || null; },
  };
  el.classList = {
    add: (...tokens) => {
      const parts = new Set((el.className || "").split(/\s+/).filter(Boolean));
      tokens.forEach((t) => parts.add(t));
      el.className = Array.from(parts).join(" ");
    },
    remove: (...tokens) => {
      const parts = new Set((el.className || "").split(/\s+/).filter(Boolean));
      tokens.forEach((t) => parts.delete(t));
      el.className = Array.from(parts).join(" ");
    },
    contains: (token) => (el.className || "").split(/\s+/).includes(token),
  };
  return el;
}

// Environment factory
function setupPageContext({ token = "teller-token", role = "Teller", mustChange = "false", username = "teller1" } = {}) {
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

  const confirmCalls = [];
  let confirmResponse = true;
  const window = {
    location: { href: "/ui/teller-accounts.html", pathname: "/ui/teller-accounts.html" },
    confirm: (msg) => {
      confirmCalls.push(msg);
      return typeof window._confirmHandler === "function" ? window._confirmHandler(msg) : confirmResponse;
    },
    confirmCalls,
    setConfirmResponse: (val) => { confirmResponse = Boolean(val); },
  };

  const siteHeader = createFakeElement("header", "site-header");

  // Section 1: Search
  const searchForm = createFakeElement("form", "search-form");
  const searchQuery = createFakeElement("input", "search-query");
  searchQuery.type = "search";
  const searchSubmit = createFakeElement("button", "search-submit");
  const searchClear = createFakeElement("button", "search-clear");
  const searchMessage = createFakeElement("div", "search-message", "message");
  const searchSummary = createFakeElement("p", "search-summary");
  const searchResultsWrap = createFakeElement("div", "search-results-wrap");
  searchResultsWrap.setAttribute("hidden", "");
  const searchRows = createFakeElement("tbody", "search-rows");

  // Section 2: Open account
  const modeNew = createFakeElement("input", "mode-new");
  modeNew.type = "radio";
  modeNew.name = "customerMode";
  modeNew.value = "new";
  modeNew.checked = true;

  const modeExisting = createFakeElement("input", "mode-existing");
  modeExisting.type = "radio";
  modeExisting.name = "customerMode";
  modeExisting.value = "existing";
  modeExisting.checked = false;

  const existingCustomerFields = createFakeElement("div", "existing-customer-fields");
  existingCustomerFields.setAttribute("hidden", "");
  const existingCustomerId = createFakeElement("input", "existing-customer-id");
  existingCustomerId.name = "customerId";

  const newCustomerFields = createFakeElement("div", "new-customer-fields");
  const newCustomerName = createFakeElement("input", "new-customer-name");
  newCustomerName.name = "name";
  const newCustomerDob = createFakeElement("input", "new-customer-dob");
  newCustomerDob.name = "dateOfBirth";
  const newCustomerAddress = createFakeElement("input", "new-customer-address");
  newCustomerAddress.name = "address";
  const newCustomerPhone = createFakeElement("input", "new-customer-phone");
  newCustomerPhone.name = "phone";
  const newCustomerEmail = createFakeElement("input", "new-customer-email");
  newCustomerEmail.name = "email";
  const newCustomerIdProof = createFakeElement("input", "new-customer-idproof");
  newCustomerIdProof.name = "idProofNumber";

  const openAccountType = createFakeElement("select", "open-account-type");
  openAccountType.name = "accountType";
  openAccountType.value = "Savings";

  const openDeposit = createFakeElement("input", "open-deposit");
  openDeposit.name = "deposit";

  const openAccountForm = createFakeElement("form", "open-account-form");
  openAccountForm.accountType = openAccountType;
  openAccountForm.deposit = openDeposit;
  openAccountForm.customerId = existingCustomerId;
  openAccountForm.name = newCustomerName;
  openAccountForm.dateOfBirth = newCustomerDob;
  openAccountForm.address = newCustomerAddress;
  openAccountForm.phone = newCustomerPhone;
  openAccountForm.email = newCustomerEmail;
  openAccountForm.idProofNumber = newCustomerIdProof;

  const openAccountSubmit = createFakeElement("button", "open-account-submit");
  const openAccountMessage = createFakeElement("div", "open-account-message", "message");
  const openAccountSuccess = createFakeElement("div", "open-account-success");
  openAccountSuccess.setAttribute("hidden", "");
  const openAccountDetailsList = createFakeElement("dl", "open-account-details-list");
  const tempPasswordBox = createFakeElement("div", "temp-password-box");
  tempPasswordBox.setAttribute("hidden", "");
  const tempPasswordValue = createFakeElement("span", "temp-password-value");
  const openAccountDismiss = createFakeElement("button", "open-account-dismiss");

  // Section 3: Update customer
  const updateCustomerForm = createFakeElement("form", "update-customer-form");
  const updateCustomerId = createFakeElement("input", "update-customer-id");
  updateCustomerId.name = "customerId";
  const updatePhone = createFakeElement("input", "update-phone");
  updatePhone.name = "phone";
  const updateEmail = createFakeElement("input", "update-email");
  updateEmail.name = "email";
  const updateAddress = createFakeElement("input", "update-address");
  updateAddress.name = "address";

  updateCustomerForm.customerId = updateCustomerId;
  updateCustomerForm.phone = updatePhone;
  updateCustomerForm.email = updateEmail;
  updateCustomerForm.address = updateAddress;

  const updateCustomerSubmit = createFakeElement("button", "update-customer-submit");
  const updateCustomerClear = createFakeElement("button", "update-customer-clear");
  const updateCustomerMessage = createFakeElement("div", "update-customer-message", "message");
  const updateCustomerSuccess = createFakeElement("div", "update-customer-success");
  updateCustomerSuccess.setAttribute("hidden", "");
  const updateCustomerDetailsList = createFakeElement("dl", "update-customer-details-list");

  const elementsById = {
    "site-header": siteHeader,
    "search-form": searchForm,
    "search-query": searchQuery,
    "search-submit": searchSubmit,
    "search-clear": searchClear,
    "search-message": searchMessage,
    "search-summary": searchSummary,
    "search-results-wrap": searchResultsWrap,
    "search-rows": searchRows,

    "mode-new": modeNew,
    "mode-existing": modeExisting,
    "existing-customer-fields": existingCustomerFields,
    "existing-customer-id": existingCustomerId,
    "new-customer-fields": newCustomerFields,
    "new-customer-name": newCustomerName,
    "new-customer-dob": newCustomerDob,
    "new-customer-address": newCustomerAddress,
    "new-customer-phone": newCustomerPhone,
    "new-customer-email": newCustomerEmail,
    "new-customer-idproof": newCustomerIdProof,
    "open-account-form": openAccountForm,
    "open-account-type": openAccountType,
    "open-deposit": openDeposit,
    "open-account-submit": openAccountSubmit,
    "open-account-message": openAccountMessage,
    "open-account-success": openAccountSuccess,
    "open-account-details-list": openAccountDetailsList,
    "temp-password-box": tempPasswordBox,
    "temp-password-value": tempPasswordValue,
    "open-account-dismiss": openAccountDismiss,

    "update-customer-form": updateCustomerForm,
    "update-customer-id": updateCustomerId,
    "update-phone": updatePhone,
    "update-email": updateEmail,
    "update-address": updateAddress,
    "update-customer-submit": updateCustomerSubmit,
    "update-customer-clear": updateCustomerClear,
    "update-customer-message": updateCustomerMessage,
    "update-customer-success": updateCustomerSuccess,
    "update-customer-details-list": updateCustomerDetailsList,
  };

  const document = {
    getElementById(id) { return elementsById[id] || null; },
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
    setTimeout: (fn) => { fn(); },
    document,
    fetch,
  };

  vm.createContext(context);
  vm.runInContext(apiJs, context);
  context.bms = context.window.bms;

  function runScript() {
    vm.runInContext(tellerJs, context);
  }

  return {
    context,
    window,
    store,
    elementsById,
    calls,
    confirmCalls,
    setConfirmResponse: (val) => { confirmResponse = Boolean(val); },
    setNextResponse: (r) => { nextResponse = r; },
    runScript,
    // Direct element references
    searchForm,
    searchQuery,
    searchSubmit,
    searchClear,
    searchMessage,
    searchSummary,
    searchResultsWrap,
    searchRows,
    modeNew,
    modeExisting,
    existingCustomerFields,
    existingCustomerId,
    newCustomerFields,
    newCustomerName,
    newCustomerDob,
    newCustomerAddress,
    newCustomerPhone,
    newCustomerEmail,
    newCustomerIdProof,
    openAccountForm,
    openAccountType,
    openDeposit,
    openAccountSubmit,
    openAccountMessage,
    openAccountSuccess,
    openAccountDetailsList,
    tempPasswordBox,
    tempPasswordValue,
    openAccountDismiss,
    updateCustomerForm,
    updateCustomerId,
    updatePhone,
    updateEmail,
    updateAddress,
    updateCustomerSubmit,
    updateCustomerClear,
    updateCustomerMessage,
    updateCustomerSuccess,
    updateCustomerDetailsList,
  };
}

(async () => {
  // Test 1: Non-Teller access rejection (Unauthenticated)
  {
    const page = setupPageContext({ token: null });
    page.runScript();
    assert.strictEqual(page.window.location.href, "/ui/index.html");
  }

  // Test 2: Non-Teller access rejection (Customer role)
  {
    const page = setupPageContext({ role: "Customer" });
    page.runScript();
    assert.strictEqual(page.window.location.href, "/ui/index.html");
  }

  // Test 3: Teller access allowed & header rendered
  {
    const page = setupPageContext({ role: "Teller" });
    page.runScript();
    assert.strictEqual(page.window.location.href, "/ui/teller-accounts.html");
    const header = page.elementsById["site-header"];
    assert.ok(header.children.length > 0, "Header must be populated by bms.header");
  }

  // Test 4: Open account - mode toggling
  {
    const page = setupPageContext();
    page.runScript();

    // Default is new customer
    assert.strictEqual(page.existingCustomerFields.getAttribute("hidden"), "");
    assert.strictEqual(page.newCustomerFields.getAttribute("hidden"), null);

    // Toggle to existing customer
    page.modeExisting.checked = true;
    page.modeNew.checked = false;
    await page.modeExisting.dispatch("change");

    assert.strictEqual(page.existingCustomerFields.getAttribute("hidden"), null);
    assert.strictEqual(page.newCustomerFields.getAttribute("hidden"), "");

    // Toggle back to new customer
    page.modeNew.checked = true;
    page.modeExisting.checked = false;
    await page.modeNew.dispatch("change");

    assert.strictEqual(page.existingCustomerFields.getAttribute("hidden"), "");
    assert.strictEqual(page.newCustomerFields.getAttribute("hidden"), null);
  }

  // Test 5: Open account - deposit validation (negative, zero, or below minimum)
  {
    const page = setupPageContext();
    page.runScript();

    // Zero deposit
    page.openDeposit.value = "0";
    await page.openAccountForm.dispatch("submit");
    assert.ok(page.openAccountMessage.textContent.includes("positive number"));

    // Savings below 1000
    page.openAccountType.value = "Savings";
    page.openDeposit.value = "500";
    await page.openAccountForm.dispatch("submit");
    assert.ok(page.openAccountMessage.textContent.includes("at least Rs 1,000"));

    // Current below 5000
    page.openAccountType.value = "Current";
    page.openDeposit.value = "3000";
    await page.openAccountForm.dispatch("submit");
    assert.ok(page.openAccountMessage.textContent.includes("at least Rs 5,000"));
  }

  // Test 6: Open account - New customer missing fields
  {
    const page = setupPageContext();
    page.runScript();

    page.openAccountType.value = "Savings";
    page.openDeposit.value = "1500";
    page.newCustomerName.value = "";
    await page.openAccountForm.dispatch("submit");
    assert.ok(page.openAccountMessage.textContent.includes("All customer fields are required"));
  }

  // Test 7: Open account - New customer invalid phone or email
  {
    const page = setupPageContext();
    page.runScript();

    page.openAccountType.value = "Savings";
    page.openDeposit.value = "1500";
    page.newCustomerName.value = "Arun";
    page.newCustomerDob.value = "1990-01-01";
    page.newCustomerAddress.value = "Bangalore";
    page.newCustomerIdProof.value = "PAN123";

    // Invalid phone
    page.newCustomerPhone.value = "abc12";
    page.newCustomerEmail.value = "arun@example.com";
    await page.openAccountForm.dispatch("submit");
    assert.ok(page.openAccountMessage.textContent.includes("Phone number must contain 10 to 15 digits"));

    // Invalid email
    page.newCustomerPhone.value = "9876543210";
    page.newCustomerEmail.value = "notanemail";
    await page.openAccountForm.dispatch("submit");
    assert.ok(page.openAccountMessage.textContent.includes("valid email address"));
  }

  // Test 8: Open account - New customer successful submission with temporary password
  {
    const page = setupPageContext();
    page.setNextResponse({
      ok: true,
      status: 201,
      headers: { get: () => "application/json" },
      json: async () => ({
        customer_id: 42,
        account_id: 105,
        account_number: "1000000042",
        account_type: "Savings",
        balance: "1500.00",
        status: "Active",
        transaction_id: 201,
        temporary_password: "TempSecretPassword123!",
      }),
    });
    page.runScript();

    page.openAccountType.value = "Savings";
    page.openDeposit.value = "1500";
    page.newCustomerName.value = "Arun Sharma";
    page.newCustomerDob.value = "1990-01-01";
    page.newCustomerAddress.value = "123 MG Road";
    page.newCustomerPhone.value = "9876543210";
    page.newCustomerEmail.value = "arun@example.com";
    page.newCustomerIdProof.value = "PAN1234567";

    await page.openAccountForm.dispatch("submit");

    assert.strictEqual(page.calls.length, 1);
    assert.strictEqual(page.calls[0].url, "/accounts");
    assert.strictEqual(page.calls[0].options.method, "POST");
    const sentBody = JSON.parse(page.calls[0].options.body);
    assert.strictEqual(sentBody.account_type, "Savings");
    assert.strictEqual(sentBody.deposit, "1500");
    assert.strictEqual(sentBody.name, "Arun Sharma");

    // Success card is visible
    assert.strictEqual(page.openAccountSuccess.getAttribute("hidden"), null);
    assert.ok(page.openAccountMessage.textContent.includes("Customer ID 42"));

    // Details are rendered
    const listText = page.openAccountDetailsList.children.map((c) => c.textContent).join(" ");
    assert.ok(listText.includes("42"));
    assert.ok(listText.includes("105"));
    assert.ok(listText.includes("1000000042"));
    assert.ok(listText.includes("Savings"));
    assert.ok(listText.includes("Rs 1,500.00"));

    // Temporary password callout is shown
    assert.strictEqual(page.tempPasswordBox.getAttribute("hidden"), null);
    assert.strictEqual(page.tempPasswordValue.textContent, "TempSecretPassword123!");

    // Dismiss cancel preserves sensitive data
    page.setConfirmResponse(false);
    await page.openAccountDismiss.dispatch("click");
    assert.strictEqual(page.tempPasswordValue.textContent, "TempSecretPassword123!");
    assert.strictEqual(page.tempPasswordBox.getAttribute("hidden"), null);
    assert.strictEqual(page.openAccountSuccess.getAttribute("hidden"), null);

    // Dismiss confirm clears sensitive data
    page.setConfirmResponse(true);
    await page.openAccountDismiss.dispatch("click");
    assert.strictEqual(page.tempPasswordValue.textContent, "");
    assert.strictEqual(page.tempPasswordBox.getAttribute("hidden"), "");
    assert.strictEqual(page.openAccountSuccess.getAttribute("hidden"), "");
  }

  // Test 8b: Protect existing temporary password on subsequent submission - Teller cancels confirm
  {
    const page = setupPageContext();
    page.setNextResponse({
      ok: true,
      status: 201,
      headers: { get: () => "application/json" },
      json: async () => ({
        customer_id: 42,
        account_id: 105,
        account_number: "1000000042",
        account_type: "Savings",
        balance: "1500.00",
        status: "Active",
        transaction_id: 201,
        temporary_password: "InitialTempPassword123!",
      }),
    });
    page.runScript();

    // First account opened
    page.openAccountType.value = "Savings";
    page.openDeposit.value = "1500";
    page.newCustomerName.value = "First Customer";
    page.newCustomerDob.value = "1990-01-01";
    page.newCustomerAddress.value = "123 Street";
    page.newCustomerPhone.value = "9876543210";
    page.newCustomerEmail.value = "first@example.com";
    page.newCustomerIdProof.value = "PAN1234567";
    await page.openAccountForm.dispatch("submit");

    assert.strictEqual(page.calls.length, 1);
    assert.strictEqual(page.tempPasswordValue.textContent, "InitialTempPassword123!");
    assert.strictEqual(page.tempPasswordBox.getAttribute("hidden"), null);
    assert.strictEqual(page.openAccountSuccess.getAttribute("hidden"), null);

    // Prepare second account opening form
    page.modeExisting.checked = true;
    page.modeNew.checked = false;
    await page.modeExisting.dispatch("change");
    page.existingCustomerId.value = "99";
    page.openAccountType.value = "Current";
    page.openDeposit.value = "5000";

    // Teller cancels the confirmation
    page.setConfirmResponse(false);
    page.confirmCalls.length = 0;

    await page.openAccountForm.dispatch("submit");

    // 1. Confirm dialog was prompted
    assert.strictEqual(page.confirmCalls.length, 1, "Confirmation must be requested when temp password is displayed");
    assert.ok(page.confirmCalls[0].includes("temporary password"));

    // 2. Submission aborted: no new API request sent
    assert.strictEqual(page.calls.length, 1, "API call count must not increase when cancelled");

    // 3. Old temporary password and previous success details remain visible
    assert.strictEqual(page.tempPasswordValue.textContent, "InitialTempPassword123!", "Old temporary password must remain visible");
    assert.strictEqual(page.tempPasswordBox.getAttribute("hidden"), null, "Temp password callout must remain visible");
    assert.strictEqual(page.openAccountSuccess.getAttribute("hidden"), null, "Success container must remain visible");
    const listText = page.openAccountDetailsList.children.map((c) => c.textContent).join(" ");
    assert.ok(listText.includes("1000000042"), "Previous account details must remain in list");
  }

  // Test 8c: Protect existing temporary password on subsequent submission - Teller confirms
  {
    const page = setupPageContext();
    page.setNextResponse({
      ok: true,
      status: 201,
      headers: { get: () => "application/json" },
      json: async () => ({
        customer_id: 42,
        account_id: 105,
        account_number: "1000000042",
        account_type: "Savings",
        balance: "1500.00",
        status: "Active",
        transaction_id: 201,
        temporary_password: "InitialTempPassword123!",
      }),
    });
    page.runScript();

    // First account opened
    page.openAccountType.value = "Savings";
    page.openDeposit.value = "1500";
    page.newCustomerName.value = "First Customer";
    page.newCustomerDob.value = "1990-01-01";
    page.newCustomerAddress.value = "123 Street";
    page.newCustomerPhone.value = "9876543210";
    page.newCustomerEmail.value = "first@example.com";
    page.newCustomerIdProof.value = "PAN1234567";
    await page.openAccountForm.dispatch("submit");

    assert.strictEqual(page.calls.length, 1);
    assert.strictEqual(page.tempPasswordValue.textContent, "InitialTempPassword123!");

    // Setup second response
    page.setNextResponse({
      ok: true,
      status: 201,
      headers: { get: () => "application/json" },
      json: async () => ({
        customer_id: 99,
        account_id: 106,
        account_number: "1000000099",
        account_type: "Current",
        balance: "5000.00",
        status: "Active",
        transaction_id: 202,
      }),
    });

    // Prepare second account opening form
    page.modeExisting.checked = true;
    page.modeNew.checked = false;
    await page.modeExisting.dispatch("change");
    page.existingCustomerId.value = "99";
    page.openAccountType.value = "Current";
    page.openDeposit.value = "5000";

    // Teller confirms the prompt
    page.setConfirmResponse(true);
    page.confirmCalls.length = 0;

    await page.openAccountForm.dispatch("submit");

    // 1. Confirm dialog was prompted
    assert.strictEqual(page.confirmCalls.length, 1, "Confirmation must be requested when temp password is displayed");
    assert.ok(page.confirmCalls[0].includes("temporary password"));

    // 2. Submission proceeded: second API request sent
    assert.strictEqual(page.calls.length, 2, "Second API call should be sent when confirmed");
    assert.strictEqual(page.calls[1].url, "/accounts");

    // 3. New success details displayed; previous temporary password cleared (since second account has none)
    assert.strictEqual(page.openAccountSuccess.getAttribute("hidden"), null);
    assert.strictEqual(page.tempPasswordValue.textContent, "", "Old temporary password must be cleared");
    assert.strictEqual(page.tempPasswordBox.getAttribute("hidden"), "", "Temp password box must be hidden");
    const listText = page.openAccountDetailsList.children.map((c) => c.textContent).join(" ");
    assert.ok(listText.includes("1000000099"), "New account details must be displayed");
  }

  // Test 9: Open account - Existing customer successful submission (no temporary password)
  {
    const page = setupPageContext();
    page.setNextResponse({
      ok: true,
      status: 201,
      headers: { get: () => "application/json" },
      json: async () => ({
        customer_id: 1,
        account_id: 106,
        account_number: "1000000043",
        account_type: "Current",
        balance: "6000.00",
        status: "Active",
        transaction_id: 202,
      }),
    });
    page.runScript();

    page.modeExisting.checked = true;
    page.modeNew.checked = false;
    await page.modeExisting.dispatch("change");

    page.existingCustomerId.value = "1";
    page.openAccountType.value = "Current";
    page.openDeposit.value = "6000";

    await page.openAccountForm.dispatch("submit");

    assert.strictEqual(page.calls.length, 1);
    const sentBody = JSON.parse(page.calls[0].options.body);
    assert.strictEqual(sentBody.customer_id, 1);
    assert.strictEqual(sentBody.account_type, "Current");
    assert.strictEqual(sentBody.deposit, "6000");

    // Success displayed
    assert.strictEqual(page.openAccountSuccess.getAttribute("hidden"), null);
    // Temporary password box MUST remain hidden for existing customer
    assert.strictEqual(page.tempPasswordBox.getAttribute("hidden"), "");
    assert.strictEqual(page.tempPasswordValue.textContent, "");
  }

  // Test 10: Open account - Existing customer validation (missing/invalid customer ID)
  {
    const page = setupPageContext();
    page.runScript();

    page.modeExisting.checked = true;
    page.modeNew.checked = false;
    await page.modeExisting.dispatch("change");

    page.existingCustomerId.value = "";
    page.openDeposit.value = "1500";
    await page.openAccountForm.dispatch("submit");
    assert.ok(page.openAccountMessage.textContent.includes("valid positive Customer ID"));

    page.existingCustomerId.value = "-5";
    await page.openAccountForm.dispatch("submit");
    assert.ok(page.openAccountMessage.textContent.includes("valid positive Customer ID"));
  }

  // Test 11: Update customer - validation (invalid ID, no fields, invalid phone/email)
  {
    const page = setupPageContext();
    page.runScript();

    // Invalid customer ID
    page.updateCustomerId.value = "0";
    page.updatePhone.value = "9876543210";
    await page.updateCustomerForm.dispatch("submit");
    assert.ok(page.updateCustomerMessage.textContent.includes("valid positive Customer ID"));

    // No update fields provided
    page.updateCustomerId.value = "5";
    page.updatePhone.value = "";
    page.updateEmail.value = "";
    page.updateAddress.value = "";
    await page.updateCustomerForm.dispatch("submit");
    assert.ok(page.updateCustomerMessage.textContent.includes("At least one field"));

    // Invalid phone
    page.updatePhone.value = "123";
    await page.updateCustomerForm.dispatch("submit");
    assert.ok(page.updateCustomerMessage.textContent.includes("Phone number must contain 10 to 15 digits"));

    // Invalid email
    page.updatePhone.value = "";
    page.updateEmail.value = "bademail";
    await page.updateCustomerForm.dispatch("submit");
    assert.ok(page.updateCustomerMessage.textContent.includes("valid email address"));
  }

  // Test 12: Update customer - success only sends non-empty fields and renders returned details
  {
    const page = setupPageContext();
    page.setNextResponse({
      ok: true,
      status: 200,
      headers: { get: () => "application/json" },
      json: async () => ({
        id: 5,
        name: "Vijay Kumar",
        date_of_birth: "1988-12-04",
        address: "789 New Colony, Bengaluru",
        phone: "+919876543210",
        email: "vijay.updated@example.com",
        created_at: "2026-01-01T10:00:00",
      }),
    });
    page.runScript();

    page.updateCustomerId.value = "5";
    page.updatePhone.value = "+919876543210";
    page.updateEmail.value = "vijay.updated@example.com";
    page.updateAddress.value = ""; // Omitted address

    await page.updateCustomerForm.dispatch("submit");

    assert.strictEqual(page.calls.length, 1);
    assert.strictEqual(page.calls[0].url, "/customers/5");
    assert.strictEqual(page.calls[0].options.method, "PUT");
    const sentBody = JSON.parse(page.calls[0].options.body);
    assert.strictEqual(sentBody.phone, "+919876543210");
    assert.strictEqual(sentBody.email, "vijay.updated@example.com");
    // Ensure omitted fields are NOT sent as null!
    assert.strictEqual(Object.prototype.hasOwnProperty.call(sentBody, "address"), false);

    // Success card rendered
    assert.strictEqual(page.updateCustomerSuccess.getAttribute("hidden"), null);
    assert.ok(page.updateCustomerMessage.textContent.includes("Customer ID 5"));
    const details = page.updateCustomerDetailsList.children.map((c) => c.textContent).join(" ");
    assert.ok(details.includes("Vijay Kumar"));
    assert.ok(details.includes("+919876543210"));
    assert.ok(details.includes("vijay.updated@example.com"));
  }

  // Test 13: Search customers - empty or whitespace-only query rejected without sending an API request
  {
    const page = setupPageContext();
    page.runScript();

    // 1. Empty query
    page.searchQuery.value = "";
    await page.searchForm.dispatch("submit");

    assert.strictEqual(page.calls.length, 0, "No API call should be sent for empty query");
    assert.strictEqual(page.searchMessage.textContent, "Enter a name, phone number, or account number.");
    assert.ok(page.searchMessage.classList.contains("show"));
    assert.ok(page.searchMessage.classList.contains("error"));
    assert.strictEqual(page.searchQuery.focused, true);

    // 2. Whitespace-only query
    page.searchQuery.focused = false;
    page.searchQuery.value = "     ";
    await page.searchForm.dispatch("submit");

    assert.strictEqual(page.calls.length, 0, "No API call should be sent for whitespace-only query");
    assert.strictEqual(page.searchMessage.textContent, "Enter a name, phone number, or account number.");
    assert.ok(page.searchMessage.classList.contains("show"));
    assert.ok(page.searchMessage.classList.contains("error"));
    assert.strictEqual(page.searchQuery.focused, true);
  }

  // Test 14: Search customers - customer with multiple accounts and customer with zero accounts
  {
    const page = setupPageContext();
    page.setNextResponse({
      ok: true,
      status: 200,
      headers: { get: () => "application/json" },
      json: async () => [
        {
          id: 1,
          name: "Customer One",
          phone: "9876543211",
          email: "c1@example.com",
          accounts: [
            { id: 101, accountNumber: "******0001", type: "Savings", status: "Active", balance: "2500.00" },
            { id: 102, accountNumber: "******0002", type: "Current", status: "Active", balance: "8000.00" },
          ],
        },
        {
          id: 2,
          name: "Customer Two",
          phone: "9876543212",
          email: "c2@example.com",
          accounts: [],
        },
      ],
    });
    page.runScript();

    page.searchQuery.value = "Customer";
    await page.searchForm.dispatch("submit");

    assert.strictEqual(page.calls.length, 1);
    assert.strictEqual(page.calls[0].url, "/customers?q=Customer");
    // Customer 1 has 2 accounts -> 2 rows; Customer 2 has 0 accounts -> 1 row. Total = 3 rows.
    assert.strictEqual(page.searchRows.children.length, 3);
    const row0 = page.searchRows.children[0].children.map((c) => c.textContent).join(" ");
    const row1 = page.searchRows.children[1].children.map((c) => c.textContent).join(" ");
    const row2 = page.searchRows.children[2].children.map((c) => c.textContent).join(" ");
    assert.ok(row0.includes("******0001"));
    assert.ok(row1.includes("******0002"));
    assert.ok(row2.includes("No accounts"));
  }

  // Test 15: Search customers - empty results
  {
    const page = setupPageContext();
    page.setNextResponse({
      ok: true,
      status: 200,
      headers: { get: () => "application/json" },
      json: async () => [],
    });
    page.runScript();

    page.searchQuery.value = "Nonexistent";
    await page.searchForm.dispatch("submit");

    assert.ok(page.searchSummary.textContent.includes("No matching records found"));
    assert.strictEqual(page.searchRows.children.length, 1);
    assert.ok(page.searchRows.children[0].textContent.includes("No matching records found"));
  }

  // Test 16: API error handling on search, open account, and update customer
  {
    const page = setupPageContext();
    page.runScript();

    // 1. Search failure
    page.setNextResponse({
      ok: false,
      status: 500,
      headers: { get: () => "application/json" },
      json: async () => ({ message: "Search database error" }),
    });
    page.searchQuery.value = "test";
    await page.searchForm.dispatch("submit");
    assert.ok(page.searchMessage.textContent.includes("Search database error"));
    assert.strictEqual(page.searchSubmit.disabled, false);

    // 2. Open account failure (e.g. 404 Customer not found)
    page.modeExisting.checked = true;
    page.modeNew.checked = false;
    await page.modeExisting.dispatch("change");
    page.existingCustomerId.value = "999";
    page.openDeposit.value = "1000";
    page.setNextResponse({
      ok: false,
      status: 400,
      headers: { get: () => "application/json" },
      json: async () => ({ detail: "Customer not found." }),
    });
    await page.openAccountForm.dispatch("submit");
    assert.ok(page.openAccountMessage.textContent.includes("Customer not found"));
    assert.strictEqual(page.openAccountSubmit.disabled, false);

    // 3. Update customer failure (e.g. 404)
    page.updateCustomerId.value = "999";
    page.updatePhone.value = "9876543210";
    page.setNextResponse({
      ok: false,
      status: 404,
      headers: { get: () => "application/json" },
      json: async () => ({ message: "Customer with ID 999 not found." }),
    });
    await page.updateCustomerForm.dispatch("submit");
    assert.ok(page.updateCustomerMessage.textContent.includes("not found"));
    assert.strictEqual(page.updateCustomerSubmit.disabled, false);
  }

  console.log("teller-accounts UI checks passed");
})().catch((err) => {
  console.error("Test failure:", err);
  process.exit(1);
});
