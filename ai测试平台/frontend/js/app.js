/* AI 接口测试平台前端逻辑 */

const state = {
  tab: "dashboard",
  ops: [],
  cases: [],
  runs: [],
  settings: null,
  selectedOps: new Set(),
  selectedCases: new Set(),
  opFilters: { search: "", module: "" },
  caseFilters: { search: "", module: "", status: "" },
  aiOpIds: null,
  editingCaseId: null,
  editingFlowId: null,
  flowSteps: [],
  pickerCases: [],
  editingInFlow: false,
  flowEditingIdx: -1,
  confirmCb: null,
  watchingRuns: false,
};

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

async function api(path, options = {}) {
  const opts = { ...options };
  if (opts.body && typeof opts.body !== "string" && !(opts.body instanceof FormData)) {
    opts.body = JSON.stringify(opts.body);
    opts.headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  }
  const res = await fetch(path, opts);
  let data = null;
  try { data = await res.json(); } catch (e) { /* 非 JSON */ }
  if (!res.ok) {
    let msg = `请求失败（HTTP ${res.status}）`;
    if (data && Array.isArray(data.detail)) {
      msg = data.detail.map((d) => d.msg || JSON.stringify(d)).join("；");
    } else if (data && data.detail) {
      msg = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    }
    throw new Error(msg);
  }
  return data;
}

function esc(value) {
  return String(value ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function toast(message, type = "") {
  const wrap = $("#toastWrap");
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  wrap.appendChild(el);
  setTimeout(() => el.remove(), 4200);
}

function openModal(id) { document.getElementById(id).hidden = false; }
function closeModal(id) {
  document.getElementById(id).hidden = true;
  if (id === "caseModal") {
    state.editingInFlow = false;
    state.flowEditingIdx = -1;
  }
}

function fmtTime(value) {
  if (!value) return "-";
  const t = new Date(String(value).replace(" ", "T"));
  if (Number.isNaN(t.getTime())) return String(value);
  return t.toLocaleString("zh-CN", { hour12: false });
}

function fmtDur(ms) {
  if (ms == null) return "-";
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

function methodClass(m) { return "m-" + String(m || "GET").toUpperCase(); }

function statusBadge(status) {
  const map = { passed: ["passed", "通过"], failed: ["failed", "失败"], error: ["error", "错误"], running: ["running", "执行中"] };
  const [cls, text] = map[status] || ["", status || "-"];
  return `<span class="badge ${cls}">${esc(text)}</span>`;
}

function priorityBadge(p) {
  const cls = String(p || "").toLowerCase();
  return `<span class="badge ${cls === "p1" ? "p1" : cls === "p2" ? "p2" : "p3"}">${esc(p || "P2")}</span>`;
}

function emptyRow(text, colspan = 6) {
  return `<tr><td colspan="${colspan}"><div class="empty">${esc(text)}</div></td></tr>`;
}

function kvRow(key = "", value = "", container) {
  const row = document.createElement("div");
  row.className = "kv-row";
  const k = document.createElement("input");
  k.placeholder = "名称";
  k.value = key;
  const v = document.createElement("input");
  v.placeholder = "值（支持 {{变量}}）";
  v.value = value;
  const del = document.createElement("button");
  del.className = "btn danger small";
  del.textContent = "×";
  del.addEventListener("click", () => row.remove());
  row.append(k, v, del);
  container.appendChild(row);
  return row;
}

function addKvRows(container, obj) {
  container.innerHTML = "";
  if (obj && typeof obj === "object") {
    for (const [k, v] of Object.entries(obj)) kvRow(k, v, container);
  }
}

function readKv(container) {
  const result = {};
  container.querySelectorAll(".kv-row").forEach((row) => {
    const k = row.querySelector("input:first-of-type").value.trim();
    const v = row.querySelector("input:nth-of-type(2)").value;
    if (k) result[k] = v;
  });
  return result;
}

function requestParamRows(req) {
  const rows = [];
  if (req && req.params) {
    Object.entries(req.params).forEach(([k, v]) => rows.push(["查询参数", k, v]));
  }
  if (req && req.headers) {
    Object.entries(req.headers).forEach(([k, v]) => rows.push(["请求头", k, v]));
  }
  let data = req ? req.data : null;
  if (typeof data === "string") {
    try { data = JSON.parse(data); } catch (e) { /* 保持原文 */ }
  }
  if (data && typeof data === "object" && !Array.isArray(data)) {
    Object.entries(data).forEach(([k, v]) => {
      rows.push(["请求体", k, typeof v === "object" ? JSON.stringify(v) : v]);
    });
  } else if (data !== null && data !== undefined && data !== "") {
    rows.push(["请求体", "(原始)", String(data)]);
  }
  if (!rows.length) return `<tr><td colspan="3" class="kv-detail">无参数</td></tr>`;
  return rows.map(([cat, k, v]) =>
    `<tr><td>${esc(cat)}</td><td class="mono">${esc(k)}</td><td class="mono" style="word-break:break-all">${esc(v)}</td></tr>`
  ).join("");
}

/* ---------------- 标签页 ---------------- */

const TABS = {
  dashboard: { title: "工作台", desc: "平台概览与最近执行情况" },
  operations: { title: "接口管理", desc: "导入接口文档，查看接口定义" },
  cases: { title: "用例管理", desc: "AI 生成、编辑与维护测试用例" },
  flows: { title: "业务流程", desc: "手工编排用例顺序，形成完整业务链路" },
  runs: { title: "执行与报告", desc: "执行测试用例并自动生成测试报告" },
  settings: { title: "系统设置", desc: "AI 模型、执行环境与全局参数" },
};

function switchTab(tab) {
  state.tab = tab;
  $$(".nav-item").forEach((btn) => btn.classList.toggle("active", btn.dataset.tab === tab));
  const meta = TABS[tab];
  $("#pageTitle").textContent = meta.title;
  $("#pageDesc").textContent = meta.desc;
  render();
}

async function render() {
  const content = $("#content");
  content.innerHTML = `<div class="empty">加载中...</div>`;
  try {
    if (state.tab === "dashboard") await renderDashboard();
    else if (state.tab === "operations") await renderOperations();
    else if (state.tab === "cases") await renderCases();
    else if (state.tab === "flows") await renderFlows();
    else if (state.tab === "runs") await renderRuns();
    else if (state.tab === "settings") renderSettings();
  } catch (err) {
    content.innerHTML = `<div class="empty">${esc(err.message)}</div>`;
  }
}

/* ---------------- 工作台 ---------------- */

async function renderDashboard() {
  const data = await api("/api/stats");
  state.runs = data.recent_runs || [];
  const last = data.last_run;
  $("#content").innerHTML = `
    <div class="stats-grid">
      <div class="stat"><div class="label">已导入接口</div><div class="num blue">${data.operations}</div><div class="sub">来自 OpenAPI / Postman</div></div>
      <div class="stat"><div class="label">测试用例</div><div class="num">${data.cases}</div><div class="sub">启用中 ${data.enabled_cases} 条</div></div>
      <div class="stat"><div class="label">执行次数</div><div class="num">${data.runs}</div><div class="sub">含历史执行</div></div>
      <div class="stat"><div class="label">最近一次通过率</div><div class="num ${last && last.success_rate >= 90 ? "green" : last && last.success_rate >= 60 ? "orange" : "red"}">${last ? last.success_rate + "%" : "-"}</div><div class="sub">${last ? `${last.passed}/${last.total} 条通过` : "还没有执行记录"}</div></div>
    </div>
    <div class="panel">
      <div class="panel-head"><h2>最近执行</h2><button class="btn primary small" data-action="run-open">＋ 新建执行</button></div>
      <div class="panel-body">
        <table>
          <thead><tr><th>#</th><th>名称</th><th>环境</th><th>结果</th><th>耗时</th><th>开始时间</th><th>操作</th></tr></thead>
          <tbody>
            ${state.runs.length ? state.runs.map(runRow).join("") : emptyRow("还没有执行记录，先在“用例管理”中创建用例吧", 7)}
          </tbody>
        </table>
      </div>
    </div>
    <div class="tip">工作流程：导入接口文档 → 选择接口 AI 生成用例 → 人工校验编辑 → 执行用例 → 自动生成 HTML 测试报告。</div>`;
}

function runRow(run) {
  const total = run.total || 0;
  const done = (run.passed || 0) + (run.failed || 0) + (run.error || 0);
  const pct = total ? Math.round(done / total * 100) : 0;
  return `<tr>
    <td>${run.id}</td>
    <td><b>${esc(run.name)}</b></td>
    <td>${esc(run.env)}</td>
    <td>${statusBadge(run.status)}
      <div class="run-summary"><span>通过 <b>${run.passed || 0}</b></span><span>失败 <b>${run.failed || 0}</b></span><span>错误 <b>${run.error || 0}</b></span></div>
    </td>
    <td>${fmtDur(run.duration_ms)}</td>
    <td>${fmtTime(run.started_at)}</td>
    <td>
      ${run.status !== "running" ? `<a class="link" data-action="run-detail" data-id="${run.id}">明细</a>
      ${run.report_path ? `<span>｜</span><a class="link" data-action="run-report" data-id="${run.id}">报告</a>` : ""}
      <span>｜</span><a class="link" data-action="run-del" data-id="${run.id}">删除</a>` : `<span class="kv-detail">执行中...</span>`}
    </td>
  </tr>`;
}

/* ---------------- 接口管理 ---------------- */

async function renderOperations() {
  const params = new URLSearchParams();
  if (state.opFilters.search) params.set("search", state.opFilters.search);
  if (state.opFilters.module) params.set("module", state.opFilters.module);
  state.ops = await api("/api/operations?" + params.toString());
  const modules = Array.from(new Set(state.ops.map((o) => o.module))).sort();
  const selectedCount = state.selectedOps.size;
  $("#content").innerHTML = `
    <div class="panel">
      <div class="toolbar">
        <input class="input" style="width:260px" placeholder="搜索接口名称 / 路径 / 说明" data-op-search value="${esc(state.opFilters.search)}">
        <select class="input" style="width:160px" data-op-module>
          <option value="">全部模块</option>
          ${modules.map((m) => `<option value="${esc(m)}" ${m === state.opFilters.module ? "selected" : ""}>${esc(m)}</option>`).join("")}
        </select>
        <select class="input" style="width:140px" data-op-env>
          ${(state.settings?.envs || []).map((e) => `<option>${esc(e.name)}</option>`).join("")}
        </select>
        <span class="spacer"></span>
        <button class="btn" data-action="import-open">⇪ 导入接口文档</button>
        <button class="btn" data-action="probe-contract">探测接口契约</button>
        <button class="btn primary" data-action="ai-open" ${selectedCount ? "" : "disabled"} data-scope="selected">AI 生成用例（已选 ${selectedCount}）</button>
      </div>
      <div class="panel-body">
        <table>
          <thead><tr>
            <th style="width:34px"><input type="checkbox" data-action="select-all-ops"></th>
            <th>接口名称</th><th>模块</th><th>方法</th><th>路径</th><th>鉴权</th><th>来源</th><th>操作</th>
          </tr></thead>
          <tbody>
            ${state.ops.length ? state.ops.map((op) => `
              <tr>
                <td><input type="checkbox" data-action="toggle-op" data-id="${op.id}" ${state.selectedOps.has(op.id) ? "checked" : ""}></td>
                <td><b>${esc(op.name)}</b><div class="kv-detail">${esc((op.description || "").slice(0, 80))}</div></td>
                <td>${esc(op.module)}</td>
                <td><span class="method ${methodClass(op.method)}">${esc(op.method)}</span></td>
                <td class="mono" style="word-break:break-all">${esc(op.path)}</td>
                <td>${esc(op.security || "无")}</td>
                <td>${esc(op.source)}</td>
                <td>
                  <a class="link" data-action="op-detail" data-id="${op.id}">详情</a>
                  <span>｜</span><a class="link" data-action="op-gen" data-id="${op.id}">AI 生成</a>
                  <span>｜</span><a class="link" data-action="op-del" data-id="${op.id}">删除</a>
                </td>
              </tr>`).join("") : emptyRow("还没有接口，先点击“导入接口文档”导入 OpenAPI / Swagger / Postman", 8)}
          </tbody>
        </table>
      </div>
    </div>`;
}

/* ---------------- 用例管理 ---------------- */

async function renderCases() {
  const params = new URLSearchParams();
  if (state.caseFilters.search) params.set("search", state.caseFilters.search);
  if (state.caseFilters.module) params.set("module", state.caseFilters.module);
  if (state.caseFilters.status) params.set("status", state.caseFilters.status);
  state.cases = await api("/api/cases?" + params.toString());
  const modules = Array.from(new Set(state.cases.map((c) => c.module))).sort();
  const selectedCount = state.selectedCases.size;
  $("#content").innerHTML = `
    <div class="panel">
      <div class="toolbar">
        <input class="input" style="width:230px" placeholder="搜索用例名称 / 地址 / 描述" data-case-search value="${esc(state.caseFilters.search)}">
        <select class="input" style="width:140px" data-case-module>
          <option value="">全部模块</option>
          ${modules.map((m) => `<option value="${esc(m)}" ${m === state.caseFilters.module ? "selected" : ""}>${esc(m)}</option>`).join("")}
        </select>
        <select class="input" style="width:120px" data-case-status>
          <option value="">全部状态</option>
          <option value="enabled" ${state.caseFilters.status === "enabled" ? "selected" : ""}>启用中</option>
          <option value="disabled" ${state.caseFilters.status === "disabled" ? "selected" : ""}>已停用</option>
        </select>
        <span class="spacer"></span>
        <button class="btn" data-action="case-new">＋ 新增用例</button>
        <button class="btn" data-action="ai-open" data-scope="all">AI 生成</button>
        <button class="btn primary" data-action="run-open" ${selectedCount ? "" : ""}>执行选中（${selectedCount}）</button>
        <button class="btn danger" data-action="case-batch-del" ${selectedCount ? "" : "disabled"}>批量删除</button>
      </div>
      <div class="panel-body">
        <table>
          <thead><tr>
            <th style="width:34px"><input type="checkbox" data-action="select-all-cases"></th>
            <th>用例名称</th><th>模块</th><th>优先级</th><th>方法</th><th>地址</th><th>状态</th><th>来源</th><th>更新时间</th><th>操作</th>
          </tr></thead>
          <tbody>
            ${state.cases.length ? state.cases.map((c) => `
              <tr>
                <td><input type="checkbox" data-action="toggle-case" data-id="${c.id}" ${state.selectedCases.has(c.id) ? "checked" : ""}></td>
                <td><b>${esc(c.name)}</b><div class="kv-detail">${esc((c.description || "").slice(0, 70))}</div></td>
                <td>${esc(c.module)}</td>
                <td>${priorityBadge(c.priority)}</td>
                <td><span class="method ${methodClass(c.method)}">${esc(c.method)}</span></td>
                <td class="mono" style="word-break:break-all;max-width:260px">${esc(c.url)}</td>
                <td>${c.enabled ? `<span class="badge passed">启用</span>` : `<span class="badge error">停用</span>`}</td>
                <td>${esc(c.source === "ai" ? "AI 生成" : c.source === "manual" ? "手工" : c.source)}</td>
                <td>${fmtTime(c.updated_at)}</td>
                <td>
                  <a class="link" data-action="case-edit" data-id="${c.id}">编辑</a>
                  <span>｜</span><a class="link" data-action="case-copy" data-id="${c.id}">复制</a>
                  <span>｜</span><a class="link" data-action="case-del" data-id="${c.id}">删除</a>
                </td>
              </tr>`).join("") : emptyRow("还没有用例：可以在“接口管理”选择接口 AI 生成，也可以手动新增", 10)}
          </tbody>
        </table>
      </div>
    </div>`;
}

/* ---------------- 业务流程 ---------------- */

async function renderFlows() {
  const flows = await api("/api/flows");
  $("#content").innerHTML = `
    <div class="panel">
      <div class="toolbar">
        <span style="color:var(--muted)">共 ${flows.length} 个业务流程</span>
        <span class="spacer"></span>
        <button class="btn primary" data-action="flow-new">＋ 新建流程</button>
      </div>
      <div class="panel-body">
        <table>
          <thead><tr><th>#</th><th>流程名称</th><th>说明</th><th>环境</th><th>步骤数</th><th>更新时间</th><th>操作</th></tr></thead>
          <tbody>
            ${flows.length ? flows.map((f) => `<tr>
              <td>${f.id}</td>
              <td><b>${esc(f.name)}</b></td>
              <td class="kv-detail">${esc(f.description || "")}</td>
              <td>${esc(f.env)}</td>
              <td>${f.case_count}</td>
              <td>${fmtTime(f.updated_at)}</td>
              <td>
                <a class="link" data-action="flow-edit" data-id="${f.id}">编辑</a>
                <span>｜</span><a class="link" data-action="flow-run" data-id="${f.id}">执行</a>
                <span>｜</span><a class="link" data-action="flow-del" data-id="${f.id}">删除</a>
              </td>
            </tr>`).join("") : emptyRow("还没有业务流程，点击“新建流程”手工编排用例", 7)}
          </tbody>
        </table>
      </div>
    </div>`;
}

function renderFlowSteps() {
  const wrap = $("#flowSteps");
  wrap.innerHTML = "";
  state.flowSteps.forEach((step, idx) => {
    const row = document.createElement("div");
    row.className = "kv-row";
    row.style.gridTemplateColumns = "36px 1fr auto";
    const no = document.createElement("span");
    no.textContent = idx + 1;
    no.style.cssText = "display:flex;align-items:center;justify-content:center;font-weight:700;color:var(--muted)";
    const name = document.createElement("div");
    name.innerHTML = `<b>${esc(step.name)}</b><div class="kv-detail">${step.case_id ? `用例 #${step.case_id}` : "流程内置用例"}</div>`;
    const btns = document.createElement("div");
    btns.style.display = "flex";
    btns.style.gap = "6px";
    const editBtn = document.createElement("button");
    editBtn.className = "btn small primary";
    editBtn.textContent = "编辑用例";
    editBtn.dataset.flowEditCase = idx;
    btns.appendChild(editBtn);
    [["up", "↑"], ["down", "↓"], ["del", "移除"]].forEach(([op, label]) => {
      const b = document.createElement("button");
      b.className = "btn small" + (op === "del" ? " danger" : "");
      b.textContent = label;
      b.dataset.flowStep = op;
      b.dataset.idx = idx;
      btns.appendChild(b);
    });
    row.append(no, name, btns);
    wrap.appendChild(row);
  });
}

async function openFlowEditor(flowId) {
  state.editingFlowId = flowId || null;
  state.flowSteps = [];
  $("#flowModalTitle").textContent = flowId ? "编辑业务流程" : "新建业务流程";
  $("#flowName").value = "";
  $("#flowDesc").value = "";
  $("#flowEnv").innerHTML = (state.settings?.envs || []).map((e) => `<option>${esc(e.name)}</option>`).join("");
  if (flowId) {
    const flow = await api(`/api/flows/${flowId}`);
    $("#flowName").value = flow.name;
    $("#flowDesc").value = flow.description || "";
    $("#flowEnv").value = flow.env;
    state.flowSteps = (flow.steps || []).map((s) => ({
      case_id: s.case_id,
      name: s.name,
      override: s.override || null,
      definition: s.definition || null,
    }));
  }
  renderFlowSteps();
  openModal("flowModal");
}

async function openCasePicker() {
  state.pickerCases = await api("/api/cases");
  $("#pickerSearch").value = "";
  renderPicker("");
  openModal("casePickerModal");
}

function renderPicker(keyword) {
  const list = state.pickerCases.filter((c) =>
    !keyword || c.name.includes(keyword) || String(c.id) === keyword || (c.url || "").includes(keyword)
  );
  $("#pickerList").innerHTML = list.length ? list.map((c) => `
    <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 10px;border-bottom:1px solid var(--border)">
      <div><b>${esc(c.name)}</b> <span class="kv-detail">#${c.id} ${esc(c.url || "")}</span> ${c.enabled ? "" : `<span class="badge error">停用</span>`}</div>
      <button class="btn small primary" data-action="picker-add" data-id="${c.id}" data-name="${esc(c.name)}">添加</button>
    </div>`).join("") : `<div class="empty">没有匹配的用例</div>`;
}

function flowStepMove(idx, delta) {
  const arr = state.flowSteps;
  const target = idx + delta;
  if (target < 0 || target >= arr.length) return;
  [arr[idx], arr[target]] = [arr[target], arr[idx]];
  renderFlowSteps();
}

async function saveFlow() {
  const name = $("#flowName").value.trim();
  if (!name) { toast("请填写流程名称", "err"); return; }
  const payload = {
    name,
    description: $("#flowDesc").value.trim(),
    env: $("#flowEnv").value,
    case_ids: state.flowSteps.filter((s) => s.case_id).map((s) => s.case_id),
    steps: state.flowSteps.map((s) => ({
      case_id: s.case_id,
      override: s.override || null,
      definition: s.definition || null,
    })),
  };
  try {
    if (state.editingFlowId) {
      await api(`/api/flows/${state.editingFlowId}`, { method: "PUT", body: payload });
    } else {
      await api("/api/flows", { method: "POST", body: payload });
    }
    toast("流程已保存", "ok");
    closeModal("flowModal");
    renderFlows();
  } catch (err) {
    toast(err.message, "err");
  }
}

async function openFlowCaseEditor(idx) {
  const step = state.flowSteps[idx];
  let base;
  if (step.definition) {
    base = step.definition;
  } else if (step.case_id) {
    const lib = await api(`/api/cases/${step.case_id}`);
    base = { ...lib, ...(step.override || {}) };
  } else {
    base = emptyCase();
  }
  state.editingInFlow = true;
  state.flowEditingIdx = idx;
  await openCaseEditor(step.case_id || null, base);
  $("#caseModalTitle").textContent = "编辑流程步骤用例（仅本流程生效）";
}

/* ---------------- 执行与报告 ---------------- */

async function renderRuns(quiet = false) {
  state.runs = await api("/api/runs");
  const content = $("#content");
  content.innerHTML = `
    <div class="panel">
      <div class="toolbar">
        <span style="color:var(--muted)">共 ${state.runs.length} 次执行</span>
        <span class="spacer"></span>
        <button class="btn primary" data-action="run-open">＋ 新建执行</button>
      </div>
      <div class="panel-body">
        <table>
          <thead><tr><th>#</th><th>名称</th><th>环境</th><th>结果</th><th>通过率</th><th>耗时</th><th>开始时间</th><th>操作</th></tr></thead>
          <tbody>
            ${state.runs.length ? state.runs.map(runRow).join("") : emptyRow("还没有执行记录", 8)}
          </tbody>
        </table>
      </div>
    </div>`;
  if (!quiet && state.runs.some((r) => r.status === "running")) watchRuns();
}

async function watchRuns() {
  if (state.watchingRuns) return;
  state.watchingRuns = true;
  try {
    while (true) {
      await new Promise((r) => setTimeout(r, 2000));
      const runs = await api("/api/runs");
      state.runs = runs;
      if (state.tab === "runs") renderRuns(true);
      const active = runs.filter((r) => r.status === "running");
      if (!active.length) {
        const latest = runs[0];
        if (latest && latest.status === "finished") {
          const rate = latest.total ? Math.round((latest.passed || 0) / latest.total * 100) : 0;
          toast(`「${latest.name}」执行完成：通过 ${latest.passed}/${latest.total}（${rate}%），报告已生成`, "ok");
        }
        break;
      }
    }
  } catch (e) {
    /* 轮询失败不阻塞 */
  } finally {
    state.watchingRuns = false;
  }
}

/* ---------------- 系统设置 ---------------- */

function envKvRow(key = "", value = "") {
  const row = document.createElement("div");
  row.className = "kv-row";
  const k = document.createElement("input");
  k.placeholder = "名称"; k.value = key;
  const v = document.createElement("input");
  v.placeholder = "值"; v.value = value;
  const del = document.createElement("button");
  del.className = "btn danger small"; del.textContent = "×";
  del.addEventListener("click", () => row.remove());
  row.append(k, v, del);
  return row;
}

function renderSettings() {
  const settings = state.settings;
  const envs = (settings.envs || []).length ? settings.envs : [{ name: "默认环境", base_url: "", headers: {}, variables: {} }];
  const envHtml = envs.map((env, idx) => `
    <div class="env-card" data-env-idx="${idx}">
      <div class="env-head">
        <input class="env-name" placeholder="环境名称" value="${esc(env.name)}" style="flex:1">
        <input class="env-base mono" placeholder="Base URL，例如 http://10.0.0.8:8080" value="${esc(env.base_url)}" style="flex:2">
        <button class="btn danger small" data-action="env-del">删除</button>
      </div>
      <div style="font-size:12px;color:var(--muted);margin:10px 0 6px">全局请求头（自动附加到该环境的每个请求）</div>
      <div class="kv-wrap" data-kv="env-headers">${Object.entries(env.headers || {}).map(([k, v]) => `<div class="kv-row"><input placeholder="名称" value="${esc(k)}"><input placeholder="值" value="${esc(v)}"><button class="btn danger small" data-action="env-kv-del">×</button></div>`).join("")}</div>
      <button class="btn ghost small" data-action="env-kv-add" data-target="env-headers">＋ 添加请求头</button>
      <div style="font-size:12px;color:var(--muted);margin:12px 0 6px">环境变量（用例中可用 {{变量名}} 引用）</div>
      <div class="kv-wrap" data-kv="env-vars">${Object.entries(env.variables || {}).map(([k, v]) => `<div class="kv-row"><input placeholder="名称" value="${esc(k)}"><input placeholder="值" value="${esc(v)}"><button class="btn danger small" data-action="env-kv-del">×</button></div>`).join("")}</div>
      <button class="btn ghost small" data-action="env-kv-add" data-target="env-vars">＋ 添加环境变量</button>
    </div>`).join("");

  $("#content").innerHTML = `
    <div class="panel">
      <div class="panel-head"><h2>AI 模型配置</h2><button class="btn" data-action="settings-test-ai">测试连接</button></div>
      <div class="panel-body" style="padding:20px">
        <div class="form-row half">
          <div><label>API 服务地址（OpenAI 兼容）</label><input id="setAiBaseUrl" class="input mono" value="${esc(settings.ai_base_url)}" placeholder="https://api.deepseek.com/v1"></div>
          <div><label>API Key</label><input id="setAiKey" class="input mono" type="password" value="${esc(settings.ai_api_key)}" placeholder="sk-..."></div>
        </div>
        <div class="form-row half">
          <div><label>模型名称</label><input id="setAiModel" class="input" value="${esc(settings.ai_model)}" placeholder="deepseek-chat / gpt-4o / qwen-max"></div>
          <div><label>温度（0~1，越低越稳定）</label><input id="setAiTemp" class="input" type="number" step="0.1" min="0" max="1" value="${esc(settings.ai_temperature)}"></div>
        </div>
        <div class="form-row half">
          <div><label>AI 超时（秒）</label><input id="setAiTimeout" class="input" type="number" value="${esc(settings.ai_timeout)}"></div>
          <div><label>执行超时（秒）</label><input id="setRunTimeout" class="input" type="number" value="${esc(settings.run_timeout)}"></div>
        </div>
        <div class="form-row">
          <label class="check-line"><input type="checkbox" id="setMock" ${settings.mock_mode ? "checked" : ""}> 未配置 API Key 时使用“规则模式”生成用例</label>
          <label class="check-line" style="margin-top:8px"><input type="checkbox" id="setVerifySsl" ${settings.verify_ssl ? "checked" : ""}> 校验目标接口的 HTTPS 证书（内网自签名可关闭）</label>
          <label class="check-line" style="margin-top:8px"><input type="checkbox" id="setAutoCleanup" ${settings.auto_cleanup ? "checked" : ""}> 测试结束后自动清理测试数据（默认关闭）</label>
        </div>
      </div>
    </div>
    <div class="panel">
      <div class="panel-head"><h2>执行环境</h2><button class="btn ghost small" data-action="env-add">＋ 添加环境</button></div>
      <div class="panel-body" style="padding:20px">${envHtml}</div>
    </div>
    <div style="display:flex;justify-content:flex-end;margin-top:14px">
      <button class="btn primary" data-action="settings-save" style="min-width:140px">保存设置</button>
    </div>`;
}

function readEnvCards() {
  return $$("#content .env-card").map((card) => ({
    name: card.querySelector(".env-name").value.trim() || "未命名环境",
    base_url: card.querySelector(".env-base").value.trim(),
    headers: readKv(card.querySelector('[data-kv="env-headers"]')),
    variables: readKv(card.querySelector('[data-kv="env-vars"]')),
  }));
}

/* ---------------- 导入弹窗 ---------------- */

function openImportModal() {
  state.importMode = "file";
  $("#importFilePanel").hidden = false;
  $("#importPastePanel").hidden = true;
  $$("#importSeg .seg-item").forEach((b) => b.classList.toggle("active", b.dataset.importMode === "file"));
  $("#importFileInput").value = "";
  $("#fileName").textContent = "";
  $("#importText").value = "";
  openModal("importModal");
}

/* ---------------- AI 弹窗 ---------------- */

function openAiModal(opIds) {
  state.aiOpIds = opIds && opIds.length ? opIds : null;
  const scopeText = state.aiOpIds ? `已选 ${state.aiOpIds.length} 个接口` : "全部接口";
  $("#aiScopeText").textContent = scopeText;
  const toolbarEnv = document.querySelector("[data-op-env]")?.value;
  $("#aiEnv").innerHTML = (state.settings?.envs || []).map((e) =>
    `<option ${e.name === (toolbarEnv || "默认环境") ? "selected" : ""}>${esc(e.name)}</option>`
  ).join("");
  const checked = $('input[name="aiMode"]:checked');
  $("#freeRow").hidden = !checked || checked.value !== "free";
  $("#aiFreeText").value = "";
  $("#aiExtra").value = "";
  openModal("aiModal");
}

/* ---------------- 用例编辑弹窗 ---------------- */

function emptyCase() {
  return {
    operation_id: null, name: "", module: "", method: "GET", url: "{{base_url}}/", env: "默认环境",
    headers: {}, query: {}, path_params: {}, body: "", body_type: "json",
    expected_status: 200, assertions: [{ type: "status_code", path: "", operator: "==", expected: "200" }],
    description: "", priority: "P1", enabled: true, source: "manual",
  };
}

function assertionRow(a = {}) {
  const row = document.createElement("div");
  row.className = "assertion-row";
  row.innerHTML = `
    <select class="as-type">
      <option value="status_code">状态码</option><option value="json">JSON 字段</option>
      <option value="text">响应文本</option><option value="time">响应时间</option>
    </select>
    <input class="as-path mono" placeholder="字段路径，如 data.id">
    <select class="as-op">
      <option value="==">==</option><option value="!=">!=</option><option value=">">&gt;</option>
      <option value=">=">&gt;=</option><option value="<">&lt;</option><option value="<=">&lt;=</option>
      <option value="contains">包含</option><option value="not_contains">不包含</option>
      <option value="exists">存在</option><option value="not_exists">不存在</option>
      <option value="type">类型</option><option value="regex">正则</option>
      <option value="is_object">是对象</option><option value="is_array">是数组</option>
      <option value="is_string">是字符串</option><option value="is_number">是数字</option>
      <option value="is_integer">是整数</option><option value="is_boolean">是布尔</option>
      <option value="is_null">是空</option><option value="length">长度</option>
    </select>
    <input class="as-expected" placeholder="期望值，如 200">
    <button class="btn danger small">×</button>`;
  row.querySelector(".as-type").value = a.type || "status_code";
  row.querySelector(".as-path").value = a.path || "";
  const opSel = row.querySelector(".as-op");
  if (a.operator && !Array.from(opSel.options).some((o) => o.value === a.operator)) {
    const opt = document.createElement("option");
    opt.value = a.operator;
    opt.textContent = a.operator;
    opSel.appendChild(opt);
  }
  opSel.value = a.operator || "==";
  row.querySelector(".as-expected").value = a.expected != null ? a.expected : "";
  row.querySelector("button").addEventListener("click", () => row.remove());
  row.querySelector(".as-type").addEventListener("change", () => {
    const type = row.querySelector(".as-type").value;
    row.querySelector(".as-path").style.display = type === "json" ? "" : "none";
    if (type === "status_code") { row.querySelector(".as-op").value = "=="; row.querySelector(".as-expected").value = "200"; }
  });
  row.querySelector(".as-path").style.display = (a.type || "status_code") === "json" ? "" : "none";
  return row;
}

async function openCaseEditor(caseId, presetCase) {
  state.editingCaseId = caseId || null;
  let c = presetCase || state.cases.find((x) => x.id === caseId) || null;
  if (!c) c = emptyCase();
  $("#caseModalTitle").textContent = caseId ? "编辑用例" : "新增用例";
  $("#cName").value = c.name || "";
  $("#cModule").value = c.module || "";
  $("#cPriority").value = c.priority || "P2";
  $("#cMethod").value = c.method || "GET";
  $("#cUrl").value = c.url || "";
  $("#cDesc").value = c.description || "";
  $("#cBodyType").value = c.body_type || "json";
  $("#cBody").value = c.body && typeof c.body === "object" ? JSON.stringify(c.body, null, 2) : (c.body ?? "");
  $("#cEnabled").checked = c.enabled !== false;
  const envs = (state.settings?.envs || []).map((e) => e.name);
  $("#cEnv").innerHTML = envs.map((n) => `<option ${n === c.env ? "selected" : ""}>${esc(n)}</option>`).join("");
  const allCases = await api("/api/cases");
  $("#cSetupCase").innerHTML =
    `<option value="">无</option>` +
    allCases
      .filter((x) => x.id !== (caseId || 0))
      .map((x) => `<option value="${x.id}" ${c.setup_case_id === x.id ? "selected" : ""}>#${x.id} ${esc(x.name)}</option>`)
      .join("");
  addKvRows($("#cHeaders"), c.headers || {});
  addKvRows($("#cQuery"), c.query || {});
  addKvRows($("#cPathParams"), c.path_params || {});
  const extWrap = $("#cExtracts");
  extWrap.innerHTML = "";
  (c.extract_rules || []).forEach((r) => addExtractRow(extWrap, r.name, r.path));
  const cleanupWrap = $("#cCleanup");
  cleanupWrap.innerHTML = "";
  (c.cleanup_rules || []).forEach((r) => addCleanupRow(cleanupWrap, r.method, r.url));
  const asWrap = $("#cAssertions");
  asWrap.innerHTML = "";
  (c.assertions && c.assertions.length ? c.assertions : [{ type: "status_code", path: "", operator: "==", expected: "200" }])
    .forEach((a) => asWrap.appendChild(assertionRow(a)));
  openModal("caseModal");
}

function collectCaseFromEditor() {
  let body = $("#cBody").value;
  const bodyType = $("#cBodyType").value;
  if (bodyType === "json" && body.trim()) {
    try { body = JSON.parse(body); } catch (e) { throw new Error("请求体不是合法 JSON：" + e.message); }
  }
  const assertions = $$("#cAssertions .assertion-row").map((row) => ({
    type: row.querySelector(".as-type").value,
    path: row.querySelector(".as-path").value.trim(),
    operator: row.querySelector(".as-op").value,
    expected: row.querySelector(".as-expected").value,
  })).filter((a) => a.type === "status_code" ? a.expected !== "" : true);
  if (!assertions.some((a) => a.type === "status_code")) {
    assertions.unshift({ type: "status_code", path: "", operator: "==", expected: String($("#cMethod").value === "GET" ? 200 : 200) });
  }
  return {
    operation_id: null,
    name: $("#cName").value.trim(),
    module: $("#cModule").value.trim() || "默认",
    method: $("#cMethod").value,
    url: $("#cUrl").value.trim(),
    env: $("#cEnv").value,
    headers: readKv($("#cHeaders")),
    query: readKv($("#cQuery")),
    path_params: readKv($("#cPathParams")),
    body,
    body_type: bodyType,
    expected_status: Number($$("#cAssertions .assertion-row").find((row) => row.querySelector(".as-type").value === "status_code")?.querySelector(".as-expected").value || 200),
    assertions,
    description: $("#cDesc").value.trim(),
    priority: $("#cPriority").value,
    enabled: $("#cEnabled").checked,
    source: "manual",
    setup_case_id: $("#cSetupCase").value ? Number($("#cSetupCase").value) : null,
    extract_rules: $$("#cExtracts .kv-row").map((row) => ({
      name: row.querySelector("input:first-of-type").value.trim(),
      path: row.querySelector("input:nth-of-type(2)").value.trim(),
    })).filter((r) => r.name && r.path),
    cleanup_rules: $$("#cCleanup .cleanup-row").map((row) => ({
      method: row.querySelector("select").value,
      url: row.querySelector("input").value.trim(),
    })).filter((r) => r.url),
  };
}

function addExtractRow(container, name = "", path = "") {
  const row = document.createElement("div");
  row.className = "kv-row";
  const n = document.createElement("input");
  n.placeholder = "变量名，如 order_id";
  n.value = name;
  const p = document.createElement("input");
  p.placeholder = "JSON 路径，如 data.id";
  p.value = path;
  const del = document.createElement("button");
  del.className = "btn danger small";
  del.textContent = "×";
  del.addEventListener("click", () => row.remove());
  row.append(n, p, del);
  container.appendChild(row);
}

function addCleanupRow(container, method = "DELETE", url = "") {
  const row = document.createElement("div");
  row.className = "kv-row cleanup-row";
  const sel = document.createElement("select");
  sel.innerHTML = `<option>DELETE</option><option>POST</option><option>PUT</option>`;
  sel.value = method || "DELETE";
  const u = document.createElement("input");
  u.placeholder = "清理地址，如 {{base_url}}/api/novels/{{novel_id}}";
  u.value = url;
  const del = document.createElement("button");
  del.className = "btn danger small";
  del.textContent = "×";
  del.addEventListener("click", () => row.remove());
  row.append(sel, u, del);
  container.appendChild(row);
}

/* ---------------- 执行弹窗 ---------------- */

function openRunModal() {
  const envs = (state.settings?.envs || []).map((e) => e.name);
  $("#runEnv").innerHTML = envs.map((n) => `<option>${esc(n)}</option>`).join("");
  $("#runName").value = "";
  $("#runSelectedCount").textContent = state.selectedCases.size;
  openModal("runModal");
}

/* ---------------- 事件绑定 ---------------- */

document.addEventListener("click", async (e) => {
  const addAssertBtn = e.target.closest("[data-add-assertion]");
  if (addAssertBtn) {
    $("#cAssertions").appendChild(assertionRow());
    return;
  }
  const addKvBtn = e.target.closest("[data-add-kv]");
  if (addKvBtn) {
    const wrap = document.getElementById(addKvBtn.dataset.addKv);
    if (wrap) kvRow("", "", wrap);
    return;
  }
  const stepBtn = e.target.closest("[data-flow-step]");
  if (stepBtn) {
    const idx = Number(stepBtn.dataset.idx);
    const op = stepBtn.dataset.flowStep;
    if (op === "up") flowStepMove(idx, -1);
    else if (op === "down") flowStepMove(idx, 1);
    else { state.flowSteps.splice(idx, 1); renderFlowSteps(); }
    return;
  }
  const flowEditBtn = e.target.closest("[data-flow-edit-case]");
  if (flowEditBtn) {
    openFlowCaseEditor(Number(flowEditBtn.dataset.flowEditCase));
    return;
  }
  const closeBtn = e.target.closest("[data-close]");
  if (closeBtn) { closeModal(closeBtn.dataset.close); return; }

  const nav = e.target.closest(".nav-item");
  if (nav) { switchTab(nav.dataset.tab); return; }

  const seg = e.target.closest("[data-import-mode]");
  if (seg) {
    state.importMode = seg.dataset.importMode;
    $$("#importSeg .seg-item").forEach((b) => b.classList.toggle("active", b === seg));
    $("#importFilePanel").hidden = seg.dataset.importMode !== "file";
    $("#importPastePanel").hidden = seg.dataset.importMode !== "paste";
    return;
  }

  const actionEl = e.target.closest("[data-action]");
  if (!actionEl) return;
  const action = actionEl.dataset.action;
  const id = Number(actionEl.dataset.id || 0);

  switch (action) {
    case "import-open": openImportModal(); break;
    case "ai-open": {
      let ids = [];
      if (actionEl.dataset.scope === "selected") {
        ids = state.tab === "cases" ? Array.from(state.selectedCases) : Array.from(state.selectedOps);
      }
      openAiModal(ids.length ? ids : null);
      break;
    }
    case "op-gen": openAiModal([id]); break;
    case "probe-contract": {
      const env = document.querySelector('[data-op-env]').value || "默认环境";
      const ids = state.selectedOps.size ? Array.from(state.selectedOps) : state.ops.map((o) => o.id);
      const btn = actionEl;
      btn.disabled = true;
      btn.textContent = "探测中...";
      try {
        const res = await api("/api/operations/probe", { method: "POST", body: { operation_ids: ids, env } });
        toast(`契约探测完成：成功 ${res.probed} 个，跳过写接口 ${res.skipped} 个，失败 ${res.failed} 个`, res.failed ? "err" : "ok");
        renderOperations();
      } catch (err) {
        toast(err.message, "err");
      } finally {
        btn.disabled = false;
        btn.textContent = "探测接口契约";
      }
      break;
    }
    case "op-detail": openOpDetail(id); break;
    case "op-del":
      confirmAction(`确定删除接口「${state.ops.find((o) => o.id === id)?.name || id}」吗？已生成的用例会保留。`, async () => {
        await api(`/api/operations/${id}`, { method: "DELETE" });
        toast("接口已删除", "ok");
        renderOperations();
      });
      break;
    case "toggle-op":
      if (actionEl.checked) state.selectedOps.add(id); else state.selectedOps.delete(id);
      refreshTopButtons();
      break;
    case "select-all-ops":
      state.selectedOps = actionEl.checked ? new Set(state.ops.map((o) => o.id)) : new Set();
      renderOperations();
      break;
    case "case-new": openCaseEditor(null); break;
    case "case-edit": openCaseEditor(id); break;
    case "case-copy": {
      const src = state.cases.find((c) => c.id === id);
      if (src) {
        await api("/api/cases", { method: "POST", body: { ...src, id: undefined, name: src.name + "（副本）", source: "manual" } });
        toast("已复制为新用例", "ok");
        renderCases();
      }
      break;
    }
    case "case-del":
      confirmAction(`确定删除用例「${state.cases.find((c) => c.id === id)?.name || id}」吗？`, async () => {
        await api(`/api/cases/${id}`, { method: "DELETE" });
        state.selectedCases.delete(id);
        toast("用例已删除", "ok");
        renderCases();
      });
      break;
    case "toggle-case":
      if (actionEl.checked) state.selectedCases.add(id); else state.selectedCases.delete(id);
      refreshTopButtons();
      break;
    case "select-all-cases":
      state.selectedCases = actionEl.checked ? new Set(state.cases.map((c) => c.id)) : new Set();
      renderCases();
      break;
    case "case-batch-del":
      if (!state.selectedCases.size) return;
      confirmAction(`确定删除选中的 ${state.selectedCases.size} 条用例吗？`, async () => {
        await api("/api/cases/batch-delete", { method: "POST", body: { ids: Array.from(state.selectedCases) } });
        state.selectedCases.clear();
        toast("已批量删除", "ok");
        renderCases();
      });
      break;
    case "run-open": openRunModal(); break;
    case "run-detail": openRunDetail(id); break;
    case "run-report": {
      const run = state.runs.find((r) => r.id === id);
      if (run?.report_path) window.open(`/reports/${run.report_path}`, "_blank");
      break;
    }
    case "run-del":
      confirmAction("确定删除这条执行记录吗？对应报告文件会保留在 reports 目录。", async () => {
        await api(`/api/runs/${id}`, { method: "DELETE" });
        toast("执行记录已删除", "ok");
        renderRuns();
      });
      break;
    case "env-add": {
      const card = document.createElement("div");
      card.className = "env-card";
      card.innerHTML = `
        <div class="env-head">
          <input class="env-name" placeholder="环境名称" value="新环境" style="flex:1">
          <input class="env-base mono" placeholder="Base URL" value="" style="flex:2">
          <button class="btn danger small" data-action="env-del">删除</button>
        </div>
        <div style="font-size:12px;color:var(--muted);margin:10px 0 6px">全局请求头</div>
        <div class="kv-wrap" data-kv="env-headers"></div>
        <button class="btn ghost small" data-action="env-kv-add" data-target="env-headers">＋ 添加请求头</button>
        <div style="font-size:12px;color:var(--muted);margin:12px 0 6px">环境变量</div>
        <div class="kv-wrap" data-kv="env-vars"></div>
        <button class="btn ghost small" data-action="env-kv-add" data-target="env-vars">＋ 添加环境变量</button>`;
      $("#content .panel:last-of-type .panel-body").appendChild(card);
      break;
    }
    case "env-del": {
      const card = actionEl.closest(".env-card");
      const cards = $$("#content .env-card");
      if (cards.length <= 1) { toast("至少保留一个环境", "err"); return; }
      card.remove();
      break;
    }
    case "env-kv-add": {
      const card = actionEl.closest(".env-card");
      const target = card.querySelector(`[data-kv="${actionEl.dataset.target}"]`);
      target.appendChild(envKvRow());
      break;
    }
    case "env-kv-del": actionEl.closest(".kv-row").remove(); break;
    case "settings-save": saveSettings(); break;
    case "settings-test-ai": testAiConnection(); break;
    case "import-submit": submitImport(); break;
    case "ai-submit": submitAi(); break;
    case "case-save": submitCase(); break;
    case "add-extract": addExtractRow($("#cExtracts")); break;
    case "add-cleanup": addCleanupRow($("#cCleanup")); break;
    case "flow-new": openFlowEditor(null); break;
    case "flow-edit": openFlowEditor(id); break;
    case "flow-run": {
      try {
        const res = await api(`/api/flows/${id}/run`, { method: "POST" });
        toast(`流程执行已开始（#${res.run_id}）`, "ok");
        switchTab("runs");
      } catch (err) { toast(err.message, "err"); }
      break;
    }
    case "flow-del":
      confirmAction("确定删除这个业务流程吗？", async () => {
        await api(`/api/flows/${id}`, { method: "DELETE" });
        toast("流程已删除", "ok");
        renderFlows();
      });
      break;
    case "flow-add-case": openCasePicker(); break;
    case "flow-new-case": {
      state.flowSteps.push({ case_id: null, name: "新流程用例", override: null, definition: null });
      renderFlowSteps();
      openFlowCaseEditor(state.flowSteps.length - 1);
      break;
    }
    case "flow-save": saveFlow(); break;
    case "picker-add": {
      const cid = Number(actionEl.dataset.id);
      const cname = actionEl.dataset.name;
      if (!state.flowSteps.some((s) => s.case_id === cid)) {
        state.flowSteps.push({ case_id: cid, name: cname, override: null, definition: null });
        renderFlowSteps();
      }
      break;
    }
    case "run-submit": submitRun(); break;
  }
});

document.addEventListener("change", (e) => {
  const opSearch = e.target.closest("[data-op-search]");
  if (opSearch) { state.opFilters.search = opSearch.value.trim(); renderOperations(); return; }
  const opModule = e.target.closest("[data-op-module]");
  if (opModule) { state.opFilters.module = opModule.value; renderOperations(); return; }
  const caseSearch = e.target.closest("[data-case-search]");
  if (caseSearch) { state.caseFilters.search = caseSearch.value.trim(); renderCases(); return; }
  const caseModule = e.target.closest("[data-case-module]");
  if (caseModule) { state.caseFilters.module = caseModule.value; renderCases(); return; }
  const caseStatus = e.target.closest("[data-case-status]");
  if (caseStatus) { state.caseFilters.status = caseStatus.value; renderCases(); return; }
  const aiMode = e.target.closest('input[name="aiMode"]');
  if (aiMode) { $("#freeRow").hidden = aiMode.value !== "free"; return; }
  const runScope = e.target.closest('input[name="runScope"]');
  if (runScope) { $("#runSelectedCount").textContent = state.selectedCases.size; return; }
  const pickerSearch = e.target.closest("#pickerSearch");
  if (pickerSearch) { renderPicker(pickerSearch.value.trim()); return; }
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    $$(".modal-mask:not([hidden])").forEach((m) => { m.hidden = true; });
  }
});

$("#importFileInput").addEventListener("change", () => {
  const file = $("#importFileInput").files[0];
  $("#fileName").textContent = file ? `${file.name}（${(file.size / 1024).toFixed(1)} KB）` : "";
});

const dropzone = $("#dropzone");
dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.classList.add("dragover"); });
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  const file = e.dataTransfer.files[0];
  if (file) {
    const dt = new DataTransfer();
    dt.items.add(file);
    $("#importFileInput").files = dt.files;
    $("#fileName").textContent = `${file.name}（${(file.size / 1024).toFixed(1)} KB）`;
  }
});

async function testAiConnection() {
  const btn = document.querySelector("#testAiBtn");
  if (!btn) return;
  btn.disabled = true; btn.textContent = "测试中...";
  try {
    const res = await api("/api/settings/test-ai", {
      method: "POST",
      body: {
        ai_base_url: $("#setAiBaseUrl").value.trim(),
        ai_api_key: $("#setAiKey").value.trim(),
        ai_model: $("#setAiModel").value.trim(),
        ai_temperature: Number($("#setAiTemp").value),
        ai_timeout: Number($("#setAiTimeout").value),
      },
    });
    toast(`AI 连接正常：${res.reply}`, "ok");
  } catch (err) {
    toast(err.message, "err");
  } finally {
    btn.disabled = false; btn.textContent = "测试连接";
  }
}

function refreshTopButtons() {
  const aiBtns = $$('[data-action="ai-open"]');
  aiBtns.forEach((b) => {
    if (b.dataset.scope === "selected") {
      const count = state.tab === "cases" ? state.selectedCases.size : state.selectedOps.size;
      b.disabled = !count;
      b.textContent = state.tab === "cases" ? `AI 生成` : `AI 生成用例（已选 ${count}）`;
    }
  });
}

function confirmAction(message, cb) {
  $("#confirmText").textContent = message;
  state.confirmCb = cb;
  openModal("confirmModal");
}

$("#confirmOk").addEventListener("click", async () => {
  closeModal("confirmModal");
  if (state.confirmCb) {
    const cb = state.confirmCb;
    state.confirmCb = null;
    try { await cb(); } catch (err) { toast(err.message, "err"); }
  }
});

/* ---------------- 提交动作 ---------------- */

async function submitImport() {
  const btn = $("#importSubmit");
  btn.disabled = true;
  try {
    let result;
    if (state.importMode === "file") {
      const file = $("#importFileInput").files[0];
      if (!file) throw new Error("请先选择接口文档文件");
      const fd = new FormData();
      fd.append("file", file);
      result = await api("/api/import/file", { method: "POST", body: fd });
    } else {
      const text = $("#importText").value;
      if (!text.trim()) throw new Error("请粘贴接口文档内容");
      result = await api("/api/import/text", { method: "POST", body: { content: text, source_name: "粘贴的接口文档" } });
    }
    toast(`导入成功：${result.name || "接口文档"}，共 ${result.imported} 个接口`, "ok");
    closeModal("importModal");
    state.opFilters = { search: "", module: "" };
    state.selectedOps.clear();
    switchTab("operations");
  } catch (err) {
    toast(err.message, "err");
  } finally {
    btn.disabled = false;
  }
}

async function submitAi() {
  const btn = $("#aiSubmit");
  btn.disabled = true;
  btn.textContent = "生成中...";
  try {
    const mode = $('input[name="aiMode"]:checked').value;
    const result = await api("/api/cases/ai-generate", {
      method: "POST",
      body: {
        operation_ids: state.aiOpIds || [],
        mode,
        extra_prompt: $("#aiExtra").value.trim(),
        free_text: $("#aiFreeText").value.trim(),
        env: $("#aiEnv").value,
      },
    });
    closeModal("aiModal");
    toast(`生成完成：AI 生成 ${result.generated} 条，成功保存 ${result.saved} 条`, "ok");
    if (result.errors && result.errors.length) {
      result.errors.slice(0, 3).forEach((msg) => toast("生成失败：" + msg, "err"));
    }
    state.caseFilters = { search: "", module: "", status: "" };
    switchTab("cases");
  } catch (err) {
    toast(err.message, "err");
  } finally {
    btn.disabled = false;
    btn.textContent = "开始生成";
  }
}

async function submitCase() {
  let payload;
  try {
    payload = collectCaseFromEditor();
  } catch (err) {
    toast(err.message, "err");
    return;
  }
  if (!payload.name) { toast("请填写用例名称", "err"); return; }
  if (state.editingInFlow) {
    const idx = state.flowEditingIdx;
    if (idx >= 0 && state.flowSteps[idx]) {
      const step = state.flowSteps[idx];
      if (step.case_id) {
        step.override = payload;
        step.definition = null;
      } else {
        step.definition = payload;
        step.override = null;
      }
      step.name = payload.name || step.name;
      renderFlowSteps();
      toast("已保存到流程步骤（不影响用例库）", "ok");
      closeModal("caseModal");
      state.editingInFlow = false;
      state.flowEditingIdx = -1;
      return;
    }
  }
  try {
    if (state.editingCaseId) {
      await api(`/api/cases/${state.editingCaseId}`, { method: "PUT", body: payload });
      toast("用例已更新", "ok");
    } else {
      await api("/api/cases", { method: "POST", body: payload });
      toast("用例已创建", "ok");
    }
    closeModal("caseModal");
    renderCases();
  } catch (err) {
    toast(err.message, "err");
  }
}

async function submitRun() {
  const scope = $('input[name="runScope"]:checked').value;
  const btn = $("#runSubmit");
  btn.disabled = true;
  try {
    const result = await api("/api/runs", {
      method: "POST",
      body: {
        name: $("#runName").value.trim(),
        env: $("#runEnv").value,
        case_ids: scope === "selected" ? Array.from(state.selectedCases) : [],
      },
    });
    closeModal("runModal");
    toast(`执行已开始（#${result.run_id}），完成后自动生成测试报告`, "ok");
    switchTab("runs");
  } catch (err) {
    toast(err.message, "err");
  } finally {
    btn.disabled = false;
  }
}

async function saveSettings() {
  const settings = {
    ai_base_url: $("#setAiBaseUrl").value.trim(),
    ai_api_key: $("#setAiKey").value.trim(),
    ai_model: $("#setAiModel").value.trim(),
    ai_temperature: Number($("#setAiTemp").value || 0.2),
    ai_timeout: Number($("#setAiTimeout").value || 120),
    run_timeout: Number($("#setRunTimeout").value || 30),
    verify_ssl: $("#setVerifySsl").checked,
    auto_cleanup: $("#setAutoCleanup").checked,
    mock_mode: $("#setMock").checked,
    envs: readEnvCards(),
  };
  try {
    state.settings = await api("/api/settings", { method: "PUT", body: settings });
    toast("设置已保存", "ok");
  } catch (err) {
    toast(err.message, "err");
  }
}

/* ---------------- 详情弹窗 ---------------- */

async function openOpDetail(id) {
  const op = await api(`/api/operations/${id}`);
  $("#opDetail").innerHTML = `
    <div class="detail-block">
      <h4>基本信息</h4>
      <table>
        <tr><td style="width:90px;color:var(--muted)">名称</td><td><b>${esc(op.name)}</b></td></tr>
        <tr><td style="color:var(--muted)">请求</td><td><span class="method ${methodClass(op.method)}">${esc(op.method)}</span> <span class="mono">${esc(op.path)}</span></td></tr>
        <tr><td style="color:var(--muted)">模块</td><td>${esc(op.module)}</td></tr>
        <tr><td style="color:var(--muted)">鉴权</td><td>${esc(op.security || "无")}</td></tr>
        <tr><td style="color:var(--muted)">说明</td><td>${esc(op.description || "-")}</td></tr>
      </table>
    </div>
    <div class="detail-block"><h4>参数定义</h4><pre>${esc(JSON.stringify(op.params || [], null, 2))}</pre></div>
    <div class="detail-block"><h4>请求体 Schema</h4><pre>${esc(JSON.stringify(op.body_schema || {}, null, 2))}</pre></div>
    <div class="detail-block"><h4>请求体示例</h4><pre>${esc(JSON.stringify(op.body_example ?? "", null, 2))}</pre></div>
    <div class="detail-block"><h4>响应示例</h4><pre>${esc(JSON.stringify(op.response_example ?? "", null, 2))}</pre></div>
    ${op.contract && op.contract.probed ? `<div class="detail-block"><h4>实测契约（探测结果）</h4><pre>${esc(JSON.stringify(op.contract, null, 2))}</pre></div>` : ""}`;
  $("#opGenBtn").dataset.id = id;
  openModal("opModal");
}

$("#opGenBtn").addEventListener("click", () => {
  const id = Number($("#opGenBtn").dataset.id || 0);
  closeModal("opModal");
  openAiModal(id ? [id] : null);
});

async function openRunDetail(id) {
  const run = await api(`/api/runs/${id}`);
  const total = run.total || 0;
  const rate = total ? Math.round((run.passed || 0) / total * 100) : 0;
  const items = run.items || [];
  const modStats = {};
  items.forEach((item) => {
    const mod = item.module || "未分类";
    if (!modStats[mod]) modStats[mod] = { name: mod, total: 0, passed: 0, failed: 0, errors: 0 };
    modStats[mod].total += 1;
    if (item.status === "passed") modStats[mod].passed += 1;
    else if (item.status === "failed") modStats[mod].failed += 1;
    else modStats[mod].errors += 1;
  });
  const modRows = Object.values(modStats).map((m) => {
    const r = m.total ? Math.round(m.passed / m.total * 100) : 0;
    return `<tr><td><b>${esc(m.name)}</b></td><td>${m.total}</td><td class="green">${m.passed}</td><td class="red">${m.failed}</td><td class="orange">${m.errors}</td><td>${r}%</td></tr>`;
  }).join("");
  const modOptions = Object.keys(modStats).map((m) => `<option value="${esc(m)}">${esc(m)}</option>`).join("");
  const cleanupRows = (run.cleanup || []).map((c) => `
    <tr>
      <td>${esc(c.case_name)}</td><td>${esc(c.method)}</td>
      <td class="mono" style="word-break:break-all">${esc(c.url)}</td>
      <td>${c.status_code ?? "-"}</td>
      <td>${c.ok ? `<span class="badge passed">已清理/不存在</span>` : `<span class="badge failed">清理失败</span>`}${c.error ? `<div class="kv-detail">${esc(c.error)}</div>` : ""}</td>
    </tr>`).join("");
  $("#runDetail").innerHTML = `
    <div class="stats-grid" style="margin-bottom:14px">
      <div class="stat"><div class="label">用例总数</div><div class="num">${total}</div></div>
      <div class="stat"><div class="label">通过</div><div class="num green">${run.passed || 0}</div></div>
      <div class="stat"><div class="label">失败</div><div class="num red">${run.failed || 0}</div></div>
      <div class="stat"><div class="label">错误</div><div class="num orange">${run.error || 0}</div></div>
      <div class="stat"><div class="label">通过率</div><div class="num">${rate}%</div></div>
    </div>
    ${run.cleanup && run.cleanup.length ? `
    <div class="detail-block">
      <h4 style="margin:0 0 8px">数据清理（测试后自动删除创建的数据）</h4>
      <table>
        <thead><tr><th>来源用例</th><th>方法</th><th>地址</th><th>状态码</th><th>结果</th></tr></thead>
        <tbody>${cleanupRows}</tbody>
      </table>
    </div>` : ""}
    <div class="detail-block" style="padding:14px">
      <h4 style="margin:0 0 10px">模块统计</h4>
      <table>
        <thead><tr><th>模块</th><th>总数</th><th>通过</th><th>失败</th><th>错误</th><th>通过率</th></tr></thead>
        <tbody>${modRows || `<tr><td colspan="6" class="kv-detail">暂无数据</td></tr>`}</tbody>
      </table>
    </div>
    <div class="filter-bar">
      <button class="btn small filter-btn active" data-run-filter="all">全部</button>
      <button class="btn small filter-btn" data-run-filter="passed">仅通过</button>
      <button class="btn small filter-btn" data-run-filter="failed">仅失败</button>
      <button class="btn small filter-btn" data-run-filter="error">仅错误</button>
      <select class="input" id="runModuleFilter" style="width:170px"><option value="">全部模块</option>${modOptions}</select>
      <span class="kv-detail" id="runFilterCount"></span>
    </div>
    ${items.map((item, idx) => `
      <div class="detail-block case-group" data-module="${esc(item.module || "未分类")}" data-status="${esc(item.status)}">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <h4>${idx + 1}. ${esc(item.case_name)} <span class="kv-detail">[${esc(item.module || "未分类")}]</span> ${statusBadge(item.status)} <span style="color:var(--muted);font-size:12px">${fmtDur(item.duration_ms)}</span></h4>
        </div>
        ${item.error_message ? `<div style="color:var(--fail);font-size:12px;white-space:pre-wrap;margin-bottom:8px">${esc(item.error_message)}</div>` : ""}
        ${item.setup_case_name ? `<div class="kv-detail" style="margin-bottom:4px"><b>前置条件：</b>${esc(item.setup_case_name)}</div>` : ""}
        ${item.extracts && Object.keys(item.extracts).length ? `<div class="kv-detail" style="margin-bottom:6px"><b>提取变量：</b>${Object.entries(item.extracts).map(([k, v]) => `${esc(k)} = ${esc(v)}`).join("，")}</div>` : ""}
        <h4 style="margin:10px 0 6px">参数清单（需要传入的参数）</h4>
        <table style="width:100%;border-collapse:collapse;margin-bottom:10px">
          <thead><tr><th style="text-align:left;width:80px;padding:6px 10px;border:1px solid var(--border);background:#f8fafc">分类</th><th style="text-align:left;padding:6px 10px;border:1px solid var(--border);background:#f8fafc">名称</th><th style="text-align:left;padding:6px 10px;border:1px solid var(--border);background:#f8fafc">值</th></tr></thead>
          <tbody>${requestParamRows(item.request)}</tbody>
        </table>
        <details ${item.status === "failed" ? "open" : ""}>
          <summary style="cursor:pointer;font-size:13px">请求 / 响应 / 断言明细</summary>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:10px">
            <div><h4>请求</h4><pre>${esc(JSON.stringify(item.request || {}, null, 2))}</pre></div>
            <div><h4>响应</h4><pre>${esc(JSON.stringify(item.response || {}, null, 2))}</pre></div>
          </div>
          <h4 style="margin-top:10px">断言结果</h4>
          ${(item.assertions || []).map((a) => `<div class="assertion-item"><span class="${a.passed ? "pass" : "fail"}">${a.passed ? "✓" : "✗"}</span> [${esc(a.type)}] ${esc(a.path || "-")} ${esc(a.operator)} ${esc(a.expected)} → 实际：${esc(a.actual)}</div>`).join("") || `<div class="kv-detail">无断言</div>`}
        </details>
      </div>`).join("") || `<div class="empty">还没有执行明细</div>`}`;
  const groups = $$("#runDetail .case-group");
  let runFilter = "all";
  const applyRunFilter = () => {
    const mod = $("#runModuleFilter").value;
    let shown = 0;
    groups.forEach((g) => {
      const okStatus = runFilter === "all" || g.dataset.status === runFilter;
      const okModule = !mod || g.dataset.module === mod;
      const show = okStatus && okModule;
      g.hidden = !show;
      if (show) shown += 1;
    });
    $("#runFilterCount").textContent = `当前显示 ${shown} / ${groups.length} 条`;
  };
  $$('#runDetail [data-run-filter]').forEach((btn) => {
    btn.addEventListener("click", () => {
      $$('#runDetail [data-run-filter]').forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      runFilter = btn.dataset.runFilter;
      applyRunFilter();
    });
  });
  $("#runModuleFilter").addEventListener("change", applyRunFilter);
  applyRunFilter();
  openModal("runDetailModal");
}

/* ---------------- 初始化 ---------------- */

async function init() {
  try {
    state.settings = await api("/api/settings");
  } catch (e) { /* 后端未启动时会提示 */ }
  switchTab("dashboard");
}

init();
