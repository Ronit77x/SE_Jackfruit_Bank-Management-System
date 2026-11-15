// Behaviour and unit checks for app/static/transfer.html and app/static/js/transfer.js.
// Run by pytest with Node (no browser required).
const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const htmlPath = path.join(__dirname, "..", "..", "app", "static", "transfer.html");
const jsPath = path.join(__dirname, "..", "..", "app", "static", "js", "transfer.js");
const apiJsPath = path.join(__dirname, "..", "..", "app", "static", "js", "api.js");
const cssPath = path.join(__dirname, "..", "..", "app", "static", "css", "transfer.css");

const html = fs.readFileSync(htmlPath, "utf8");
const transferJs = fs.readFileSync(jsPath, "utf8");
const apiJs = fs.readFileSync(apiJsPath, "utf8");
const css = fs.readFileSync(cssPath, "utf8");

// ==================== 1. Static HTML and CSS checks ====================
assert.ok(html.includes('name="viewport"'), "Page must have viewport meta tag");
assert.ok(html.includes('/ui/css/style.css'), "Page must load style.css");
assert.ok(html.includes('/ui/css/transfer.css'), "Page must load transfer.css");
assert.ok(html.includes('/ui/js/api.js'), "Page must load api.js");
assert.ok(html.includes('/ui/js/transfer.js'), "Page must load transfer.js");

// No duplicate inline event handlers
assert.ok(!html.includes('onclick="executeTransfer()"'), "HTML must not have inline onclick for executeTransfer");
assert.ok(!html.includes('onclick='), "HTML must not have inline onclick handlers");
assert.ok(!html.includes('onsubmit='), "HTML must not have inline onsubmit handlers");

// No avoidable inline styles
const customerHtml = fs.readFileSync(path.join(__dirname, "..", "..", "app", "static", "customer.html"), "utf8");
assert.ok(!html.includes('style='), "transfer.html must not contain avoidable inline styles");
assert.ok(!customerHtml.includes('style='), "customer.html must not contain avoidable inline styles");

// Header and main elements
assert.ok(html.includes('id="site-header"'), "Site header must be present");
assert.ok(html.includes('Transfer Money'), "Page must include title 'Transfer Money'");

// Step elements
assert.ok(html.includes('id="stepDetails"'), "Step 1 details section must be present");
assert.ok(html.includes('id="stepReview"'), "Step 2 review section must be present");
assert.ok(html.includes('id="stepResult"'), "Step 3 result section must be present");

// Form inputs
assert.ok(html.includes('id="fromAccountSelect"'), "From account select must be present");
assert.ok(html.includes('id="toAccountInput"'), "To account input must be present");
assert.ok(html.includes('id="amountInput"'), "Amount input must be present");
assert.ok(html.includes('id="btnReview"'), "Review button must be present");
assert.ok(html.includes('id="btnConfirmSend"'), "Confirm send button must be present");

// Review and receipt fields
assert.ok(html.includes('id="reviewFromAccount"'), "Review from account element must be present");
assert.ok(html.includes('id="reviewToAccount"'), "Review to account element must be present");
assert.ok(html.includes('id="reviewAmount"'), "Review amount element must be present");
assert.ok(html.includes('id="reviewTotal"'), "Review total element must be present");
assert.ok(html.includes('id="receiptReference"'), "Receipt reference element must be present");
assert.ok(html.includes('id="receiptAmount"'), "Receipt amount element must be present");
assert.ok(html.includes('id="receiptToAccount"'), "Receipt to account element must be present");
assert.ok(html.includes('id="receiptNewBalance"'), "Receipt new balance element must be present");

// CSS [hidden] rule check
assert.ok(css.includes("[hidden]"), "CSS must declare [hidden] rule");
assert.ok(css.includes("display: none !important"), "CSS [hidden] rule must specify display: none !important");

// ==================== 2. Safe DOM construction check ====================
const FORBIDDEN = [/\.innerHTML/, /\.outerHTML/, /insertAdjacentHTML/, /document\.write/, /\beval\(/, /new Function\(/];
FORBIDDEN.forEach((pattern) => {
  assert.ok(!pattern.test(html), "HTML must not contain forbidden pattern: " + pattern);
  assert.ok(!pattern.test(transferJs), "transfer.js must not contain forbidden pattern: " + pattern);
});

// ==================== 3. Controller Unit Checks in Simulated DOM ====================

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
    disabled: false,
    hidden: false,
    style: {},
    get textContent() {
      if (children.length > 0) {
        return children.map((c) => (c ? c.textContent || "" : "")).join("");
      }
      return _textContent;
    },
    set textContent(val) {
      children.length = 0;
      _textContent = String(val);
    },
    appendChild(child) {
      children.push(child);
      child.parentElement = el;
      return child;
    },
    replaceChildren(...newChildren) {
      children.length = 0;
      _textContent = "";
      newChildren.forEach((c) => el.appendChild(c));
    },
    addEventListener(evt, fn) {
      if (!listeners[evt]) listeners[evt] = [];
      listeners[evt].push(fn);
    },
    dispatchEvent(evt) {
      const fns = listeners[evt.type || evt] || [];
      fns.forEach((fn) => fn(evt));
    },
    setAttribute(name, val) {
      attrs[name] = String(val);
    },
    getAttribute(name) {
      return attrs[name] !== undefined ? attrs[name] : null;
    },
    querySelectorAll(selector) {
      return children.filter((c) => {
        if (selector.startsWith(".")) {
          return c.className && c.className.includes(selector.slice(1));
        }
        return false;
      });
    },
    get children() {
      return children;
    },
    get parentElement() {
      return el._parent || null;
    },
    set parentElement(p) {
      el._parent = p;
    },
    click() {
      el.dispatchEvent({ type: "click" });
    }
  };
  return el;
}

function buildFakeDocument() {
  const elementsById = {};
  const docListeners = {};
  const doc = {
    getElementById: (id) => elementsById[id] || null,
    createElement: (tag) => createFakeElement(tag),
    querySelectorAll: (selector) => {
      const results = [];
      Object.keys(elementsById).forEach((id) => {
        const el = elementsById[id];
        if (selector.startsWith(".") && el.className && el.className.includes(selector.slice(1))) {
          results.push(el);
        }
      });
      return results;
    },
    addEventListener: (evt, fn) => {
      if (!docListeners[evt]) docListeners[evt] = [];
      docListeners[evt].push(fn);
    },
    dispatchEvent: (evt) => {
      const fns = docListeners[evt.type || evt] || [];
      fns.forEach((fn) => fn(evt));
    }
  };

  const ids = [
    "site-header", "stepIndicator1", "stepIndicator2", "stepIndicator3",
    "globalAlert", "stepDetails", "stepReview", "stepResult", "transferForm",
    "fromAccountSelect", "fromAccountHelp", "balanceDisplay", "accountTypeDisplay",
    "minBalanceHelp", "accountBalanceDisplay", "toAccountInput", "toAccountHelp",
    "toAccountError", "amountInput", "amountHelp", "amountError", "btnReview",
    "reviewFromAccount", "reviewToAccount", "reviewAmount", "reviewTotal",
    "btnBackToEdit", "btnConfirmSend", "successContent", "failureContent",
    "receiptReference", "receiptAmount", "receiptToAccount", "receiptNewBalance",
    "btnPrintReceipt", "btnNewTransfer", "failureMessage", "btnFailureBack"
  ];

  ids.forEach((id) => {
    let tag = "div";
    if (id.endsWith("Select")) tag = "select";
    else if (id.endsWith("Input")) tag = "input";
    else if (id.startsWith("btn")) tag = "button";
    else if (id.endsWith("Form")) tag = "form";
    elementsById[id] = createFakeElement(tag, id);
  });

  return { doc, elementsById };
}

(async () => {
  const store = {
    bms_token: "cust_token_123",
    bms_role: "Customer",
    bms_must_change: "false",
    bms_username: "asha_customer"
  };

  const { doc, elementsById } = buildFakeDocument();
  const windowObj = {
    location: { href: "", pathname: "/ui/transfer.html" },
    sessionStorage: {
      getItem: (k) => store[k] || null,
      setItem: (k, v) => { store[k] = String(v); },
      removeItem: (k) => { delete store[k]; }
    },
    print: () => {}
  };

  let mockAccounts = [
    {
      id: 1,
      accountNumber: "1000000001",
      maskedAccountNumber: "******0001",
      type: "Savings",
      status: "Active",
      balance: "10000.00"
    },
    {
      id: 2,
      accountNumber: "1000000002",
      maskedAccountNumber: "******0002",
      type: "Current",
      status: "Active",
      balance: "25000.00"
    },
    {
      id: 3,
      accountNumber: "1000000099",
      maskedAccountNumber: "******0099",
      type: "Savings",
      status: "Frozen",
      balance: "1500.00"
    }
  ];

  let postTransferCall = null;
  let transferCallCount = 0;

  const context = {
    window: windowObj,
    sessionStorage: windowObj.sessionStorage,
    document: doc,
    console,
    URL,
    fetch: async (url, options) => {
      if (url === "/accounts/me") {
        return {
          ok: true,
          status: 200,
          headers: { get: () => "application/json" },
          json: async () => mockAccounts
        };
      }
      if (url === "/transactions/transfer") {
        transferCallCount++;
        postTransferCall = JSON.parse(options.body);
        if (postTransferCall.toAccount === "9999999999") {
          return {
            ok: false,
            status: 404,
            headers: { get: () => "application/json" },
            json: async () => ({ code: "ACCOUNT_NOT_FOUND", message: "Account not found" })
          };
        }
        return {
          ok: true,
          status: 200,
          headers: { get: () => "application/json" },
          json: async () => ({
            status: "SUCCESS",
            transactionId: 101,
            reference: "TRF-20261115-00101",
            balance: "9000.00"
          })
        };
      }
      return { ok: false, status: 404, headers: { get: () => "application/json" }, json: async () => ({}) };
    }
  };

  vm.createContext(context);
  vm.runInContext(apiJs, context);
  context.bms = context.window.bms;
  windowObj.bms = context.window.bms;

  // Run transfer.js
  vm.runInContext(transferJs, context);

  // 1. Verify eligibility helper
  const isEligible = windowObj.isEligibleStatus;
  assert.strictEqual(typeof isEligible, "function", "isEligibleStatus must be a function");
  assert.strictEqual(isEligible("Active"), true);
  assert.strictEqual(isEligible("active"), true);
  assert.strictEqual(isEligible(" ACTIVE "), true);
  assert.strictEqual(isEligible("Frozen"), false);
  assert.strictEqual(isEligible("Closed"), false);
  assert.strictEqual(isEligible(null), false);
  assert.strictEqual(isEligible(undefined), false);

  // 2. Trigger DOMContentLoaded to load accounts
  doc.dispatchEvent({ type: "DOMContentLoaded" });
  await new Promise((resolve) => setTimeout(resolve, 50));

  // The fromAccountSelect should have options: default placeholder, 2 active accounts, 1 disabled frozen account
  const fromSelect = elementsById["fromAccountSelect"];
  const options = fromSelect.children;
  assert.ok(options.length >= 3, "Select must contain loaded account options");
  const frozenOption = options.find((opt) => opt.value === "1000000099");
  assert.ok(frozenOption, "Frozen account should be present in options");
  assert.strictEqual(frozenOption.disabled, true, "Frozen account option must be disabled");

  // 3. Select source account
  fromSelect.value = "1000000001";
  fromSelect.dispatchEvent({ type: "change" });
  assert.strictEqual(elementsById["balanceDisplay"].hidden, false, "Balance display should be visible");
  assert.ok(elementsById["accountBalanceDisplay"].textContent.includes("10,000.00"), "Balance should show 10,000.00");

  // 4. Test validation: Self-transfer rejection
  const toInput = elementsById["toAccountInput"];
  toInput.value = "1000000001";
  toInput.dispatchEvent({ type: "input" });
  assert.strictEqual(elementsById["toAccountError"].hidden, false, "Self transfer should display error");
  assert.ok(elementsById["toAccountError"].textContent.includes("same as your source account"));

  // 5. Test validation: Amount exceeds limit or balance
  toInput.value = "1000000002";
  toInput.dispatchEvent({ type: "input" });
  const amountInput = elementsById["amountInput"];

  // Exceeds single transfer limit
  amountInput.value = "150000";
  amountInput.dispatchEvent({ type: "input" });
  assert.strictEqual(elementsById["amountError"].hidden, false);
  assert.ok(elementsById["amountError"].textContent.includes("exceeds the single transfer limit"));

  // Exceeds minimum balance (balance 10,000; min req 1,000; transfer 9,500 leaves 500)
  amountInput.value = "9500";
  amountInput.dispatchEvent({ type: "input" });
  assert.strictEqual(elementsById["amountError"].hidden, false);
  assert.ok(elementsById["amountError"].textContent.includes("Insufficient funds"));

  // Valid transfer amount
  amountInput.value = "1000.00";
  amountInput.dispatchEvent({ type: "input" });
  assert.strictEqual(elementsById["amountError"].hidden, true);

  // 6. Proceed to Review (Step 2)
  windowObj.proceedToReview();
  assert.strictEqual(elementsById["stepDetails"].hidden, true);
  assert.strictEqual(elementsById["stepReview"].hidden, false);
  assert.strictEqual(elementsById["reviewToAccount"].textContent, "1000000002");
  assert.ok(elementsById["reviewAmount"].textContent.includes("1,000.00"));

  // 7. Back to Edit
  windowObj.backToEdit();
  assert.strictEqual(elementsById["stepDetails"].hidden, false);
  assert.strictEqual(elementsById["stepReview"].hidden, true);

  // 8. Proceed to Review and Execute Transfer (Step 3)
  windowObj.proceedToReview();
  const confirmBtn = elementsById["btnConfirmSend"];
  assert.strictEqual(transferCallCount, 0, "No transfer API calls before clicking confirmation");

  // Single click on Confirm & send transfer button
  confirmBtn.click();
  // Rapid second click during active submission should be ignored by the submission guard
  confirmBtn.click();
  await new Promise((resolve) => setTimeout(resolve, 50));

  assert.strictEqual(transferCallCount, 1, "Exactly one transfer API call must be made for successful transfer");
  assert.strictEqual(elementsById["stepReview"].hidden, true);
  assert.strictEqual(elementsById["stepResult"].hidden, false);
  assert.strictEqual(elementsById["successContent"].hidden, false);
  assert.strictEqual(elementsById["failureContent"].hidden, true);
  assert.strictEqual(elementsById["receiptReference"].textContent, "TRF-20261115-00101");
  assert.strictEqual(elementsById["receiptToAccount"].textContent, "1000000002");
  assert.ok(elementsById["receiptNewBalance"].textContent.includes("9,000.00"));
  assert.deepStrictEqual(postTransferCall, {
    fromAccount: "1000000001",
    toAccount: "1000000002",
    amount: "1000.00"
  });

  // Verify Print receipt action listener
  let printCalled = false;
  windowObj.print = () => { printCalled = true; };
  elementsById["btnPrintReceipt"].click();
  assert.strictEqual(printCalled, true, "Print receipt button must call window.print via event listener");

  // 9. Error case: destination not found (tests failure handling with single click)
  toInput.value = "9999999999";
  windowObj.proceedToReview();
  transferCallCount = 0; // reset counter

  confirmBtn.click();
  await new Promise((resolve) => setTimeout(resolve, 50));

  assert.strictEqual(transferCallCount, 1, "Exactly one transfer API call must be made for failed transfer");
  assert.strictEqual(elementsById["successContent"].hidden, true);
  assert.strictEqual(elementsById["failureContent"].hidden, false);
  assert.ok(elementsById["failureMessage"].textContent.includes("recipient account was not found"));
  assert.strictEqual(confirmBtn.disabled, false, "Confirm button must be re-enabled after failure");

  console.log("transfer_check.js: Static and unit tests passed successfully!");
})().catch((err) => {
  console.error("transfer_check failed:", err);
  process.exit(1);
});
