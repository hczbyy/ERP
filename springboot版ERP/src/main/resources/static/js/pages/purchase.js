/* ============================================================
 * 采购管理：采购订单（全生命周期）+ 收货入库单
 * 同时提供订单明细行编辑器 OrderEditor（销售模块复用）
 * ============================================================ */
(function () {
  window.Pages = window.Pages || {};

  /* ---------- 订单明细行编辑器（通用） ---------- */
  window.OrderEditor = {
    create({ products, priceField, initialItems = [], stockMap = null }) {
      const pMap = new Map(products.map((p) => [p.id, p]));
      let rows = initialItems.map((it) => ({ ...it }));
      let stock = stockMap; // 可变：仓库切换后刷新

      const optionHtml = (cur) => products.map((p) =>
        `<option value="${p.id}" ${String(p.id) === String(cur) ? "selected" : ""}>${UI.esc(p.code)} ${UI.esc(p.name)}${stock && stock.has(p.id) ? `（库存 ${UI.qty(stock.get(p.id))}）` : ""}</option>`).join("");

      const el = document.createElement("div");
      el.innerHTML = `
        <table class="item-editor">
          <thead><tr><th style="width:38%">商品</th><th style="width:16%">数量</th>
            <th style="width:16%">单价</th><th style="width:16%">金额</th><th style="width:8%"></th></tr></thead>
          <tbody></tbody>
          <tfoot><tr><td colspan="3" style="text-align:right;padding:8px">合计：</td>
            <td class="item-amount" id="total">¥0.00</td><td></td></tr></tfoot>
        </table>
        <button class="btn btn-ghost btn-sm" id="add-row" style="margin-top:8px">＋ 添加明细行</button>`;

      const tbody = el.querySelector("tbody");
      const totalEl = el.querySelector("#total");

      function renderRow(it, idx) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><select>
            <option value="">请选择商品</option>
            ${optionHtml(it.product_id)}
          </select></td>
          <td><input type="number" min="1" step="1" class="num" value="${it.qty ?? ""}" placeholder="数量"></td>
          <td><input type="number" min="0" step="0.01" class="num" value="${it.price ?? ""}" placeholder="单价"></td>
          <td class="item-amount amt">¥0.00</td>
          <td style="text-align:center"><button class="btn-link danger" type="button">✕</button></td>`;
        const sel = tr.querySelector("select");
        const qtyInput = tr.querySelectorAll("input")[0];
        const priceInput = tr.querySelectorAll("input")[1];
        const amtEl = tr.querySelector(".amt");

        function calc() {
          const p = pMap.get(Number(sel.value));
          const q = Number(qtyInput.value) || 0;
          const price = Number(priceInput.value) || (p ? Number(p[priceField]) : 0);
          if (p && !priceInput.value) priceInput.value = p[priceField]; // 选商品自动带价
          amtEl.textContent = "¥" + UI.money(q * price);
          total();
        }
        sel.onchange = () => { const p = pMap.get(Number(sel.value)); if (p && !priceInput.value) priceInput.value = p[priceField]; calc(); };
        qtyInput.oninput = calc;
        priceInput.oninput = calc;
        tr.querySelector(".btn-link").onclick = () => { tr.remove(); rows.splice(idx, 1); total(); };
        calc();
        return tr;
      }

      function total() {
        let sum = 0;
        tbody.querySelectorAll("tr").forEach((tr) => {
          const q = Number(tr.querySelectorAll("input")[0].value) || 0;
          const p = Number(tr.querySelectorAll("input")[1].value) || 0;
          sum += q * p;
        });
        totalEl.textContent = "¥" + UI.money(sum);
      }

      el.querySelector("#add-row").onclick = () => {
        rows.push({ product_id: "", qty: "", price: "" });
        tbody.appendChild(renderRow(rows[rows.length - 1], rows.length - 1));
      };

      rows.forEach((it, i) => tbody.appendChild(renderRow(it, i)));
      if (!rows.length) el.querySelector("#add-row").click();

      el.getItems = () => {
        const items = [];
        tbody.querySelectorAll("tr").forEach((tr) => {
          const pid = Number(tr.querySelector("select").value);
          const qty = Number(tr.querySelectorAll("input")[0].value);
          const price = Number(tr.querySelectorAll("input")[1].value);
          if (pid) items.push({ product_id: pid, qty, price });
        });
        return items;
      };
      /* 切换仓库后刷新每行的库存提示（仅影响下拉文本，不丢失已选值） */
      el.replaceStockMap = (map) => {
        stock = map;
        tbody.querySelectorAll("tr").forEach((tr) => {
          const sel = tr.querySelector("select");
          const cur = sel.value;
          sel.innerHTML = `<option value="">请选择商品</option>${optionHtml(cur)}`;
        });
      };
      el.isValid = () => {
        const items = el.getItems();
        if (!items.length) return { ok: false, msg: "请至少添加一条商品明细" };
        for (const it of items) {
          if (!(Number.isInteger(it.qty) && it.qty >= 1)) return { ok: false, msg: "商品数量必须为大于等于 1 的整数" };
          if (it.price < 0) return { ok: false, msg: "单价不能为负" };
        }
        return { ok: true };
      };
      return el;
    },
  };

  /* ---------- 采购订单 ---------- */
  const STATUS_OPTIONS = "|draft:草稿|approved:已审核|partially_received:部分收货|completed:已完成|cancelled:已取消";

  function orderDetailHtml(o) {
    return `
      <div class="desc-grid">
        <div class="desc-item"><span class="k">单号</span><span class="v">${UI.esc(o.order_no)}</span></div>
        <div class="desc-item"><span class="k">供应商</span><span class="v">${UI.esc(o.supplier_name || "-")}</span></div>
        <div class="desc-item"><span class="k">收货仓库</span><span class="v">${UI.esc(o.warehouse_name || "-")}</span></div>
        <div class="desc-item"><span class="k">状态</span><span class="v">${UI.badge(o.status)}</span></div>
        <div class="desc-item"><span class="k">订单金额</span><span class="v">¥${UI.money(o.total_amount)}</span></div>
        <div class="desc-item"><span class="k">创建人</span><span class="v">${UI.esc(o.created_by)}</span></div>
        <div class="desc-item"><span class="k">审核人</span><span class="v">${UI.esc(o.approved_by || "-")}${o.approved_at ? " / " + o.approved_at : ""}</span></div>
        <div class="desc-item"><span class="k">创建时间</span><span class="v">${UI.datetime(o.created_at)}</span></div>
        ${o.cancel_reason ? `<div class="desc-item"><span class="k">取消原因</span><span class="v">${UI.esc(o.cancel_reason)}</span></div>` : ""}
        ${o.remark ? `<div class="desc-item"><span class="k">备注</span><span class="v">${UI.esc(o.remark)}</span></div>` : ""}
      </div>
      <table class="table">
        <thead><tr><th>商品</th><th>编码</th><th class="num">数量</th><th class="num">单价</th>
          <th class="num">金额</th><th class="num">已收</th><th class="num">未收</th></tr></thead>
        <tbody>${o.items.map((it) => `<tr>
          <td>${UI.esc(it.product_name)}</td><td>${UI.esc(it.product_code)}</td>
          <td class="num">${UI.qty(it.qty)}</td><td class="num">${UI.money(it.price)}</td>
          <td class="num">${UI.money(it.amount)}</td><td class="num">${UI.qty(it.received_qty)}</td>
          <td class="num">${UI.qty(it.remain_qty)}</td></tr>`).join("")}</tbody>
      </table>`;
  }

  Pages.purchase = {
    orders: {
      render(el) {
        const state = { page: 1, page_size: 10, status: "", keyword: "" };
        const canManage = ERP.hasPerm("purchase:order:manage");
        const canReceive = ERP.hasPerm("purchase:receive:manage");

        el.innerHTML = `
          <div class="card">
            <div class="toolbar">
              <input type="text" placeholder="搜索单号" id="kw">
              <select id="status"><option value="">全部状态</option>${STATUS_OPTIONS.split("|").filter(Boolean).map((o) => { const [v, t] = o.split(":"); return `<option value="${v}">${t}</option>`; }).join("")}</select>
              <button class="btn btn-ghost" id="search-btn">查询</button>
              <div class="spacer"></div>
              ${canManage ? `<button class="btn btn-primary" id="add-btn">＋ 新建采购单</button>` : ""}
            </div>
            <div class="table-wrap"><table class="table">
              <thead><tr><th>单号</th><th>供应商</th><th>仓库</th><th class="num">金额</th><th>状态</th><th>创建人</th><th>创建时间</th><th class="actions">操作</th></tr></thead>
              <tbody id="tbody"></tbody></table></div>
            <div class="pager" id="pager"></div>
          </div>`;

        el.querySelector("#search-btn").onclick = () => { state.keyword = el.querySelector("#kw").value.trim(); state.page = 1; load(); };
        el.querySelector("#kw").onkeydown = (e) => { if (e.key === "Enter") el.querySelector("#search-btn").click(); };
        el.querySelector("#status").onchange = () => { state.status = el.querySelector("#status").value; state.page = 1; load(); };
        if (canManage) el.querySelector("#add-btn").onclick = () => openForm(null);

        async function load() {
          try {
            const qs = new URLSearchParams(state);
            const data = await API.get(`/api/purchase/orders?${qs}`);
            const tbody = el.querySelector("#tbody");
            tbody.innerHTML = data.items.length ? data.items.map((o) => `<tr>
              <td>${UI.esc(o.order_no)}</td><td>${UI.esc(o.supplier_name || "-")}</td><td>${UI.esc(o.warehouse_name || "-")}</td>
              <td class="num">${UI.money(o.total_amount)}</td><td>${UI.badge(o.status)}</td>
              <td>${UI.esc(o.created_by)}</td><td>${UI.datetime(o.created_at)}</td>
              <td class="actions">
                <button class="btn-link" data-act="detail" data-id="${o.id}">详情</button>
                ${canManage && o.status === "draft" ? `<button class="btn-link" data-act="edit" data-id="${o.id}">编辑</button>` : ""}
                ${canManage && o.status === "draft" ? `<button class="btn-link" data-act="approve" data-id="${o.id}">审核</button>` : ""}
                ${canReceive && (o.status === "approved" || o.status === "partially_received") ? `<button class="btn-link" data-act="receive" data-id="${o.id}">收货</button>` : ""}
                ${canManage && (o.status === "draft" || o.status === "approved") ? `<button class="btn-link danger" data-act="cancel" data-id="${o.id}">取消</button>` : ""}
                ${canManage && o.status === "draft" ? `<button class="btn-link danger" data-act="del" data-id="${o.id}">删除</button>` : ""}
              </td></tr>`).join("")
            : `<tr><td colspan="8"><div class="empty">暂无采购订单</div></td></tr>`;
            tbody.querySelectorAll("[data-act]").forEach((b) => {
              b.onclick = () => {
                const o = data.items.find((r) => r.id === Number(b.dataset.id));
                if (!o) { UI.toast("数据已刷新，请重试", "error"); load(); return; }
                ({ detail: () => showDetail(o.id), edit: () => openForm(o), approve: () => approve(o), receive: () => receive(o), cancel: () => cancel(o), del: () => del(o) })[b.dataset.act]();
              };
            });
            UI.pager(el.querySelector("#pager"), { ...data, onChange: (p) => { state.page = p; load(); } });
          } catch (e) { UI.err(e); }
        }

        async function openForm(row) {
          // 编辑时列表行不含明细，需拉取完整详情（含 items）
          if (row) {
            try { row = await API.get(`/api/purchase/orders/${row.id}`); }
            catch (e) { UI.err(e); return; }
          }
          const isEdit = !!row;
          const [suppliers, warehouses, products] = await Promise.all([
            API.get("/api/master/suppliers/all"),
            API.get("/api/master/warehouses"),
            API.get("/api/master/products/all"),
          ]);
          const form = document.createElement("div");
          form.innerHTML = `
            <div class="field-row">
              <div class="field"><label>供应商 *</label><select id="f-supplier"><option value="">请选择</option>
                ${suppliers.map((s) => `<option value="${s.id}" ${row && row.supplier_id === s.id ? "selected" : ""}>${UI.esc(s.name)}</option>`).join("")}</select></div>
              <div class="field"><label>收货仓库 *</label><select id="f-wh"><option value="">请选择</option>
                ${warehouses.map((w) => `<option value="${w.id}" ${row && row.warehouse_id === w.id ? "selected" : ""}>${UI.esc(w.name)}</option>`).join("")}</select></div>
            </div>
            <div class="field"><label>备注</label><input type="text" id="f-remark" value="${UI.esc(row?.remark || "")}"></div>
            <div class="field"><label>商品明细</label></div>
            <div id="f-items"></div>`;
          const editor = OrderEditor.create({
            products, priceField: "purchase_price",
            initialItems: row ? row.items.map((it) => ({ product_id: it.product_id, qty: it.qty, price: it.price })) : [],
          });
          form.querySelector("#f-items").appendChild(editor);

          const foot = document.createElement("div");
          foot.innerHTML = `<button class="btn btn-ghost" data-act="no">取消</button><button class="btn btn-primary" data-act="yes">${isEdit ? "保存修改" : "创建采购单"}</button>`;
          const m = UI.modal({ title: `${isEdit ? "编辑" : "新建"}采购订单`, body: form, footer: foot, size: "modal-lg" });
          foot.querySelector('[data-act="no"]').onclick = m.close;
          foot.querySelector('[data-act="yes"]').onclick = async () => {
            const sid = Number(form.querySelector("#f-supplier").value);
            const wid = Number(form.querySelector("#f-wh").value);
            if (!sid || !wid) return UI.toast("请选择供应商和仓库", "error");
            const chk = editor.isValid();
            if (!chk.ok) return UI.toast(chk.msg, "error");
            const payload = { supplier_id: sid, warehouse_id: wid, remark: form.querySelector("#f-remark").value, items: editor.getItems() };
            try {
              if (isEdit) await API.put(`/api/purchase/orders/${row.id}`, payload);
              else await API.post("/api/purchase/orders", payload);
              UI.toast("保存成功"); m.close(); load();
            } catch (e) { UI.err(e); }
          };
        }

        async function showDetail(orderId) {
          try {
            const detail = await API.get(`/api/purchase/orders/${orderId}`);
            const foot = document.createElement("div");
            foot.innerHTML = `<button class="btn btn-ghost" data-act="close">关闭</button>`;
            const m = UI.modal({ title: `采购订单详情 ${detail.order_no}`, body: orderDetailHtml(detail), footer: foot, size: "modal-lg" });
            foot.querySelector('[data-act="close"]').onclick = m.close;
          } catch (e) { UI.err(e); }
        }

        async function approve(o) {
          if (!await UI.confirm(`确认审核采购单 ${o.order_no} ？`)) return;
          try { await API.post(`/api/purchase/orders/${o.id}/approve`); UI.toast("审核成功"); load(); } catch (e) { UI.err(e); }
        }

        async function cancel(o) {
          const m = UI.modal({
            title: `取消采购单 ${o.order_no}`,
            body: `<div class="field"><label>取消原因</label><input type="text" id="cancel-reason" placeholder="必填"></div>`,
            size: "modal-sm",
            footer: (() => { const f = document.createElement("div"); f.innerHTML = `<button class="btn btn-ghost" data-act="no">再想想</button><button class="btn btn-danger" data-act="yes">确认取消</button>`; return f; })(),
          });
          m.el.querySelector('[data-act="no"]').onclick = m.close;
          m.el.querySelector('[data-act="yes"]').onclick = async () => {
            const reason = m.el.querySelector("#cancel-reason").value.trim();
            if (!reason) return UI.toast("请填写取消原因", "error");
            try { await API.post(`/api/purchase/orders/${o.id}/cancel`, { reason }); UI.toast("已取消"); m.close(); load(); } catch (e) { UI.err(e); }
          };
        }

        async function receive(o) {
          const detail = await API.get(`/api/purchase/orders/${o.id}`);
          const form = document.createElement("div");
          form.innerHTML = `<div class="field"><label>本次收货数量（默认全部剩余数量）</label></div><div id="r-items"></div>
            <div class="field"><label>备注</label><input type="text" id="r-remark"></div>`;
          const editor = OrderEditor.create({
            products: detail.items.map((it) => ({ id: it.product_id, code: it.product_code, name: it.product_name, purchase_price: it.price })),
            priceField: "purchase_price",
            initialItems: detail.items.filter((it) => it.remain_qty > 0).map((it) => ({ product_id: it.product_id, qty: it.remain_qty, price: it.price })),
          });
          form.querySelector("#r-items").appendChild(editor);
          const foot = document.createElement("div");
          foot.innerHTML = `<button class="btn btn-ghost" data-act="no">取消</button><button class="btn btn-primary" data-act="yes">确认收货入库</button>`;
          const m = UI.modal({ title: `收货入库 - ${o.order_no}`, body: form, footer: foot, size: "modal-lg" });
          foot.querySelector('[data-act="no"]').onclick = m.close;
          foot.querySelector('[data-act="yes"]').onclick = async () => {
            const chk = editor.isValid();
            if (!chk.ok) return UI.toast(chk.msg, "error");
            try {
              const r = await API.post(`/api/purchase/orders/${o.id}/receive`, { remark: form.querySelector("#r-remark").value, items: editor.getItems() });
              UI.toast(`收货成功：${r.stock_in_no}，金额 ¥${UI.money(r.total_amount)}`);
              m.close(); load();
            } catch (e) { UI.err(e); }
          };
        }

        async function del(o) {
          if (!await UI.confirm(`确定删除草稿采购单 ${o.order_no} ？`)) return;
          try { await API.del(`/api/purchase/orders/${o.id}`); UI.toast("已删除"); load(); } catch (e) { UI.err(e); }
        }

        load();
      },
    },

    /* ---------- 收货入库单 ---------- */
    stockIns: {
      render(el) {
        const state = { page: 1, page_size: 10, keyword: "" };
        el.innerHTML = `
          <div class="card">
            <div class="toolbar">
              <input type="text" placeholder="搜索入库单号 / 采购单号" id="kw">
              <button class="btn btn-ghost" id="search-btn">查询</button>
            </div>
            <div class="table-wrap"><table class="table">
              <thead><tr><th>入库单号</th><th>来源采购单</th><th>供应商</th><th>仓库</th><th class="num">金额</th><th>操作人</th><th>时间</th><th class="actions">操作</th></tr></thead>
              <tbody id="tbody"></tbody></table></div>
            <div class="pager" id="pager"></div>
          </div>`;
        el.querySelector("#search-btn").onclick = () => { state.keyword = el.querySelector("#kw").value.trim(); state.page = 1; load(); };
        el.querySelector("#kw").onkeydown = (e) => { if (e.key === "Enter") el.querySelector("#search-btn").click(); };

        async function load() {
          try {
            const qs = new URLSearchParams(state);
            const data = await API.get(`/api/purchase/stock-ins?${qs}`);
            const tbody = el.querySelector("#tbody");
            tbody.innerHTML = data.items.length ? data.items.map((si) => `<tr>
              <td>${UI.esc(si.stock_in_no)}</td><td>${UI.esc(si.po_no)}</td>
              <td>${UI.esc(si.supplier_name || "-")}</td><td>${UI.esc(si.warehouse_name || "-")}</td>
              <td class="num">${UI.money(si.total_amount)}</td><td>${UI.esc(si.created_by)}</td>
              <td>${UI.datetime(si.created_at)}</td>
              <td class="actions"><button class="btn-link" data-id="${si.id}">详情</button></td></tr>`).join("")
            : `<tr><td colspan="8"><div class="empty">暂无入库单</div></td></tr>`;
            tbody.querySelectorAll(".btn-link").forEach((b) => b.onclick = async () => {
              const d = await API.get(`/api/purchase/stock-ins/${b.dataset.id}`);
              const body = `
                <div class="desc-grid">
                  <div class="desc-item"><span class="k">入库单号</span><span class="v">${UI.esc(d.stock_in_no)}</span></div>
                  <div class="desc-item"><span class="k">采购单号</span><span class="v">${UI.esc(d.po_no)}</span></div>
                  <div class="desc-item"><span class="k">供应商</span><span class="v">${UI.esc(d.supplier_name || "-")}</span></div>
                  <div class="desc-item"><span class="k">仓库</span><span class="v">${UI.esc(d.warehouse_name || "-")}</span></div>
                  <div class="desc-item"><span class="k">金额</span><span class="v">¥${UI.money(d.total_amount)}</span></div>
                  <div class="desc-item"><span class="k">操作人</span><span class="v">${UI.esc(d.created_by)}</span></div>
                </div>
                <table class="table"><thead><tr><th>商品</th><th>编码</th><th class="num">数量</th><th class="num">单价</th><th class="num">金额</th></tr></thead>
                <tbody>${d.items.map((it) => `<tr><td>${UI.esc(it.product_name)}</td><td>${UI.esc(it.product_code)}</td>
                  <td class="num">${UI.qty(it.qty)}</td><td class="num">${UI.money(it.price)}</td><td class="num">${UI.money(it.amount)}</td></tr>`).join("")}</tbody></table>`;
              const foot = document.createElement("div");
              foot.innerHTML = `<button class="btn btn-ghost">关闭</button>`;
              const m = UI.modal({ title: "入库单详情", body, footer: foot, size: "modal-lg" });
              foot.querySelector("button").onclick = m.close;
            });
            UI.pager(el.querySelector("#pager"), { ...data, onChange: (p) => { state.page = p; load(); } });
          } catch (e) { UI.err(e); }
        }
        load();
      },
    },
  };
})();
