/* 前端文件加载自检：模拟浏览器最小环境，检查全部 JS 顶层执行是否抛错 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const root = path.join(__dirname, "..", "..", "frontend", "js");

// 最小浏览器环境 stub
const elStub = () => {
  const el = {
    style: {},
    dataset: {},
    onclick: null,
    disabled: false,
    classList: { add() {}, remove() {}, toggle() {}, contains: () => false },
    addEventListener: () => {},
    querySelector: () => null,
    querySelectorAll: () => [],
    appendChild: () => {},
    remove: () => {},
    setAttribute: () => {},
    getAttribute: () => null,
    getContext: () => new Proxy({}, { get: () => () => {} }),
    getBoundingClientRect: () => ({ width: 800, height: 300 }),
    value: "",
    checked: false,
    textContent: "",
    innerHTML: "",
    set innerHTML(v) { this._html = v; },
    get innerHTML() { return this._html || ""; },
    set textContent(v) { this._text = v; },
    get textContent() { return this._text || ""; },
  };
  return el;
};
const documentStub = {
  getElementById: () => elStub(),
  createElement: () => elStub(),
  querySelector: () => null,
  querySelectorAll: () => [],
  addEventListener: () => {},
};
const sandbox = {
  window: {},
  document: documentStub,
  localStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
  fetch: async () => ({ status: 200, json: async () => ({ code: 0, data: {} }) }),
  location: { hash: "", href: "" },
  console,
  setTimeout,
  clearTimeout,
  devicePixelRatio: 1,
  addEventListener: () => {},
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;

const files = [
  "api.js", "ui.js", "charts.js",
  "pages/login.js", "pages/dashboard.js", "pages/master.js",
  "pages/purchase.js", "pages/sales.js", "pages/inventory.js",
  "pages/finance.js", "pages/system.js", "app.js",
];
let failed = 0;
for (const f of files) {
  try {
    const code = fs.readFileSync(path.join(root, f), "utf8");
    vm.runInNewContext(code, sandbox, { filename: f });
    console.log(`PASS  ${f}`);
  } catch (e) {
    failed++;
    console.log(`FAIL  ${f}: ${e.message}`);
  }
}
console.log(failed ? `\n${failed} file(s) failed` : "\nall 12 files load OK");
process.exit(failed ? 1 : 0);