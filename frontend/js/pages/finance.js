/* ============================================================
 * 财务管理：应收 / 应付 / 收款单 / 付款单
 * ============================================================ */
(function () {
  window.Pages = window.Pages || {};

  const STATUS_OPTIONS = "|open:未核销|partial:部分核销|settled:已核销";
  const PAY_METHODS = { cash: "现金", bank: "银行转账", transfer: "线上支付" };

  /* ---------- 通用核销（收款/付款）弹窗 ---------- */
  function openSettle({ title, apiPath, row, statusText, noLabel }) {
    const balance = row.balance;
    const form = document.createElement("div");
    form.innerHTML = `
      <div class="desc-grid">
        <div class="desc-item"><span class="k">单号</span><span class="v">${UI.esc(row[noLabel])}</span></div>
        <div class="desc-item"><span class="k">总额</span><span class="v">¥${UI.money(row.total_amount)}</span></div>
        <div class="desc-item"><span class="k">已${statusText}</span><span class="v">¥${UI.money(row.received_amount ?? row.paid_amount)}</span></div>
        <div class="desc-item"><span class="k">余额</span><span class="v" style="color:${balance > 0 ? "var(--warning)" : "var(--success)"}">¥${UI.money(balance)}</span></div>
      </div>
      <div class="field-row">
        <div class="field"><label>本次${statusText}金额 *</label>
          <input type="number" min="0.01" step="0.01" id="s-amount" placeholder="不超过余额"></div>
        <div class="field"><label>方式</label><select id="s-method">
          ${Object.entries(PAY_METHODS).map(([v, t]) => `<option value="${v}">${t}</option>`).join("")}
        </select></div>
      </div>
      <div class="field"><label>日期</label><input type="date" id="s-date" value="${new Date().toISOString().slice(0, 10)}"></div>
      <div class="field"><label>备注</label><input type="text" id="s-remark" placeholder="选填"></div>`;
    const foot = document.createElement("div");
    foot.innerHTML = `<button class="btn btn-ghost" data-act="no">取消</button><button class="btn btn-primary" data-act="yes">确认${statusText}</button>`;
    const m = UI.modal({ title, body: form, footer: foot, size: "modal-sm" });
    foot.querySelector('[data-act="no"]').onclick = m.close;
    foot.querySelector('[data-act="yes"]').onclick = async () => {
      const amount = Number(form.querySelector("#s-amount").value);
      if (!(amount > 0)) return UI.toast("请输入大于 0 的金额", "error");
      if (amount > balance) return UI.toast(`金额不能超过余额 ¥${UI.money(balance)}`, "error");
      try {
        const r = await API.post(apiPath, {
          [row.receivable_id !== undefined ? "receivable_id" : "payable_id"]: row.id,
          amount,
          pay_method: form.querySelector("#s-method").value,
          [row.receivable_id !== undefined ? "received_at" : "paid_at"]: form.querySelector("#s-date").value,
          remark: form.querySelector("#s-remark").value,
        });
        UI.toast(`登记成功：${r.receipt_no || r.payment_no}`);
        m.close();
        if (m._reload) m._reload();
      } catch (e) { UI.err(e); }
    };
    return m;
  }

  /* ---------- 应收 ---------- */
  Pages.finance = {
    receivables: {
      render(el) {
        const state = { page: 1, page_size: 10, status: "", keyword: "" };
        const canManage = ERP.hasPerm("finance:manage");
        el.innerHTML = `
          <div class="card">
            <div class="toolbar">
              <input type="text" placeholder="搜索应收单号 / 来源单号" id="kw">
              <select id="status"><option value="">全部状态</option>${STATUS_OPTIONS.split("|").filter(Boolean).map((o) => { const [v, t] = o.split(":"); return `<option value="${v}">${t}</option>`; }).join("")}</select>
              <button class="btn btn-ghost" id="search-btn">查询</button>
              <div class="spacer"></div>
              ${canManage ? `<span class="badge badge-cyan">应收余额合计 <b id="sum-balance">-</b></span>` : ""}
            </div>
            <div class="table-wrap"><table class="table">
              <thead><tr><th>应收单号</th><th>来源单据</th><th>客户</th><th class="num">总额</th><th class="num">已收</th><th class="num">余额</th><th>状态</th><th>到期日</th><th class="actions">操作</th></tr></thead>
              <tbody id="tbody"></tbody></table></div>
            <div class="pager" id="pager"></div>
          </div>`;
        el.querySelector("#search-btn").onclick = () => { state.keyword = el.querySelector("#kw").value.trim(); state.page = 1; load(); };
        el.querySelector("#kw").onkeydown = (e) => { if (e.key === "Enter") el.querySelector("#search-btn").click(); };
        el.querySelector("#status").onchange = () => { state.status = el.querySelector("#status").value; state.page = 1; load(); };

        async function load() {
          try {
            const qs = new URLSearchParams(state);
            const data = await API.get(`/api/finance/receivables?${qs}`);
            const sumEl = el.querySelector("#sum-balance");
            if (sumEl) sumEl.textContent = UI.money(data.items.reduce((s, r) => s + r.balance, 0));
            const tbody = el.querySelector("#tbody");
            tbody.innerHTML = data.items.length ? data.items.map((r) => `<tr>
              <td>${UI.esc(r.receivable_no)}</td><td>${UI.esc(r.source_no)}</td><td>${UI.esc(r.customer_name || "-")}</td>
              <td class="num">${UI.money(r.total_amount)}</td><td class="num">${UI.money(r.received_amount)}</td>
              <td class="num" style="${r.balance > 0 ? "color:var(--warning);font-weight:600" : ""}">${UI.money(r.balance)}</td>
              <td>${UI.badge(r.status)}</td><td>${UI.date(r.due_date)}</td>
              <td class="actions">${canManage && r.status !== "settled" ? `<button class="btn-link" data-id="${r.id}">收款</button>` : "-"}</td></tr>`).join("")
            : `<tr><td colspan="9"><div class="empty">暂无应收记录，销售发货后自动生成</div></td></tr>`;
            tbody.querySelectorAll(".btn-link").forEach((b) => b.onclick = () => {
              const row = data.items.find((r) => r.id === Number(b.dataset.id));
              const m = openSettle({ title: `收款核销 - ${row.receivable_no}`, apiPath: "/api/finance/receipts", row, statusText: "收款", noLabel: "receivable_no" });
              m._reload = load;
            });
            UI.pager(el.querySelector("#pager"), { ...data, onChange: (p) => { state.page = p; load(); } });
          } catch (e) { UI.err(e); }
        }
        load();
      },
    },

    /* ---------- 应付 ---------- */
    payables: {
      render(el) {
        const state = { page: 1, page_size: 10, status: "", keyword: "" };
        const canManage = ERP.hasPerm("finance:manage");
        el.innerHTML = `
          <div class="card">
            <div class="toolbar">
              <input type="text" placeholder="搜索应付单号 / 来源单号" id="kw">
              <select id="status"><option value="">全部状态</option>${STATUS_OPTIONS.split("|").filter(Boolean).map((o) => { const [v, t] = o.split(":"); return `<option value="${v}">${t}</option>`; }).join("")}</select>
              <button class="btn btn-ghost" id="search-btn">查询</button>
              <div class="spacer"></div>
              ${canManage ? `<span class="badge badge-cyan">应付余额合计 <b id="sum-balance">-</b></span>` : ""}
            </div>
            <div class="table-wrap"><table class="table">
              <thead><tr><th>应付单号</th><th>来源单据</th><th>供应商</th><th class="num">总额</th><th class="num">已付</th><th class="num">余额</th><th>状态</th><th>到期日</th><th class="actions">操作</th></tr></thead>
              <tbody id="tbody"></tbody></table></div>
            <div class="pager" id="pager"></div>
          </div>`;
        el.querySelector("#search-btn").onclick = () => { state.keyword = el.querySelector("#kw").value.trim(); state.page = 1; load(); };
        el.querySelector("#kw").onkeydown = (e) => { if (e.key === "Enter") el.querySelector("#search-btn").click(); };
        el.querySelector("#status").onchange = () => { state.status = el.querySelector("#status").value; state.page = 1; load(); };

        async function load() {
          try {
            const qs = new URLSearchParams(state);
            const data = await API.get(`/api/finance/payables?${qs}`);
            const sumEl = el.querySelector("#sum-balance");
            if (sumEl) sumEl.textContent = UI.money(data.items.reduce((s, p) => s + p.balance, 0));
            const tbody = el.querySelector("#tbody");
            tbody.innerHTML = data.items.length ? data.items.map((p) => `<tr>
              <td>${UI.esc(p.payable_no)}</td><td>${UI.esc(p.source_no)}</td><td>${UI.esc(p.supplier_name || "-")}</td>
              <td class="num">${UI.money(p.total_amount)}</td><td class="num">${UI.money(p.paid_amount)}</td>
              <td class="num" style="${p.balance > 0 ? "color:var(--warning);font-weight:600" : ""}">${UI.money(p.balance)}</td>
              <td>${UI.badge(p.status)}</td><td>${UI.date(p.due_date)}</td>
              <td class="actions">${canManage && p.status !== "settled" ? `<button class="btn-link" data-id="${p.id}">付款</button>` : "-"}</td></tr>`).join("")
            : `<tr><td colspan="9"><div class="empty">暂无应付记录，采购收货后自动生成</div></td></tr>`;
            tbody.querySelectorAll(".btn-link").forEach((b) => b.onclick = () => {
              const row = data.items.find((r) => r.id === Number(b.dataset.id));
              const m = openSettle({ title: `付款核销 - ${row.payable_no}`, apiPath: "/api/finance/payments", row, statusText: "付款", noLabel: "payable_no" });
              m._reload = load;
            });
            UI.pager(el.querySelector("#pager"), { ...data, onChange: (p) => { state.page = p; load(); } });
          } catch (e) { UI.err(e); }
        }
        load();
      },
    },

    /* ---------- 收款单 ---------- */
    receipts: {
      render(el) {
        const state = { page: 1, page_size: 10, keyword: "" };
        el.innerHTML = `
          <div class="card">
            <div class="toolbar">
              <input type="text" placeholder="搜索收款单号" id="kw">
              <button class="btn btn-ghost" id="search-btn">查询</button>
            </div>
            <div class="table-wrap"><table class="table">
              <thead><tr><th>收款单号</th><th>应收单号</th><th>客户</th><th class="num">金额</th><th>方式</th><th>收款日期</th><th>操作人</th><th>时间</th></tr></thead>
              <tbody id="tbody"></tbody></table></div>
            <div class="pager" id="pager"></div>
          </div>`;
        el.querySelector("#search-btn").onclick = () => { state.keyword = el.querySelector("#kw").value.trim(); state.page = 1; load(); };
        el.querySelector("#kw").onkeydown = (e) => { if (e.key === "Enter") el.querySelector("#search-btn").click(); };

        async function load() {
          try {
            const qs = new URLSearchParams(state);
            const data = await API.get(`/api/finance/receipts?${qs}`);
            const tbody = el.querySelector("#tbody");
            tbody.innerHTML = data.items.length ? data.items.map((r) => `<tr>
              <td>${UI.esc(r.receipt_no)}</td><td>${UI.esc(r.receivable_no)}</td><td>${UI.esc(r.customer_name || "-")}</td>
              <td class="num" style="color:var(--success);font-weight:600">${UI.money(r.amount)}</td>
              <td>${UI.payMethod(r.pay_method)}</td><td>${UI.date(r.received_at)}</td>
              <td>${UI.esc(r.created_by)}</td><td>${UI.datetime(r.created_at)}</td></tr>`).join("")
            : `<tr><td colspan="8"><div class="empty">暂无收款记录</div></td></tr>`;
            UI.pager(el.querySelector("#pager"), { ...data, onChange: (p) => { state.page = p; load(); } });
          } catch (e) { UI.err(e); }
        }
        load();
      },
    },

    /* ---------- 付款单 ---------- */
    payments: {
      render(el) {
        const state = { page: 1, page_size: 10, keyword: "" };
        el.innerHTML = `
          <div class="card">
            <div class="toolbar">
              <input type="text" placeholder="搜索付款单号" id="kw">
              <button class="btn btn-ghost" id="search-btn">查询</button>
            </div>
            <div class="table-wrap"><table class="table">
              <thead><tr><th>付款单号</th><th>应付单号</th><th>供应商</th><th class="num">金额</th><th>方式</th><th>付款日期</th><th>操作人</th><th>时间</th></tr></thead>
              <tbody id="tbody"></tbody></table></div>
            <div class="pager" id="pager"></div>
          </div>`;
        el.querySelector("#search-btn").onclick = () => { state.keyword = el.querySelector("#kw").value.trim(); state.page = 1; load(); };
        el.querySelector("#kw").onkeydown = (e) => { if (e.key === "Enter") el.querySelector("#search-btn").click(); };

        async function load() {
          try {
            const qs = new URLSearchParams(state);
            const data = await API.get(`/api/finance/payments?${qs}`);
            const tbody = el.querySelector("#tbody");
            tbody.innerHTML = data.items.length ? data.items.map((p) => `<tr>
              <td>${UI.esc(p.payment_no)}</td><td>${UI.esc(p.payable_no)}</td><td>${UI.esc(p.supplier_name || "-")}</td>
              <td class="num" style="color:var(--danger);font-weight:600">${UI.money(p.amount)}</td>
              <td>${UI.payMethod(p.pay_method)}</td><td>${UI.date(p.paid_at)}</td>
              <td>${UI.esc(p.created_by)}</td><td>${UI.datetime(p.created_at)}</td></tr>`).join("")
            : `<tr><td colspan="8"><div class="empty">暂无付款记录</div></td></tr>`;
            UI.pager(el.querySelector("#pager"), { ...data, onChange: (p) => { state.page = p; load(); } });
          } catch (e) { UI.err(e); }
        }
        load();
      },
    },
  };
})();