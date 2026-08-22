/* ============================================================
 * 销售管理：销售订单（全生命周期）+ 发货出库单
 * ============================================================ */
(function () {
  window.Pages = window.Pages || {};

  const STATUS_OPTIONS = "|draft:草稿|approved:已审核|partially_shipped:部分发货|completed:已完成|cancelled:已取消";

  function orderDetailHtml(o) {
    return `
      <div class="desc-grid">
        <div class="desc-item"><span class="k">单号</span><span class="v">${UI.esc(o.order_no)}</span></div>
        <div class="desc-item"><span class="k">客户</span><span class="v">${UI.esc(o.customer_name || "-")}</span></div>
        <div class="desc-item"><span class="k">发货仓库</span><span class="v">${UI.esc(o.warehouse_name || "-")}</span></div>
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
          <th class="num">金额</th><th class="num">已发</th><th class="num">未发</th></tr></thead>
        <tbody>${o.items.map((it) => `<tr>
          <td>${UI.esc(it.product_name)}</td><td>${UI.esc(it.product_code)}</td>
          <td class="num">${UI.qty(it.qty)}</td><td class="num">${UI.money(it.price)}</td>
          <td class="num">${UI.money(it.amount)}</td><td class="num">${UI.qty(it.shipped_qty)}</td>
          <td class="num">${UI.qty(it.remain_qty)}</td></tr>`).join("")}</tbody>
      </table>`;
  }

  /* 获取指定仓库的库存映射 {product_id: qty} */
  async function stockMapFor(warehouseId) {
    const data = await API.get(`/api/inventory/stocks?warehouse_id=${warehouseId}&page_size=100`);
    const m = new Map();
    data.items.forEach((s) => m.set(s.product_id, s.qty));
    return m;
  }

  Pages.sales = {
    orders: {
      render(el) {
        const state = { page: 1, page_size: 10, status: "", keyword: "" };
        const canManage = ERP.hasPerm("sales:order:manage");
        const canShip = ERP.hasPerm("sales:ship:manage");

        el.innerHTML = `
          <div class="card">
            <div class="toolbar">
              <input type="text" placeholder="搜索单号" id="kw">
              <select id="status"><option value="">全部状态</option>${STATUS_OPTIONS.split("|").filter(Boolean).map((o) => { const [v, t] = o.split(":"); return `<option value="${v}">${t}</option>`; }).join("")}</select>
              <button class="btn btn-ghost" id="search-btn">查询</button>
              <div class="spacer"></div>
              ${canManage ? `<button class="btn btn-primary" id="add-btn">＋ 新建销售单</button>` : ""}
            </div>
            <div class="table-wrap"><table class="table">
              <thead><tr><th>单号</th><th>客户</th><th>仓库</th><th class="num">金额</th><th>状态</th><th>创建人</th><th>创建时间</th><th class="actions">操作</th></tr></thead>
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
            const data = await API.get(`/api/sales/orders?${qs}`);
            const tbody = el.querySelector("#tbody");
            tbody.innerHTML = data.items.length ? data.items.map((o) => `<tr>
              <td>${UI.esc(o.order_no)}</td><td>${UI.esc(o.customer_name || "-")}</td><td>${UI.esc(o.warehouse_name || "-")}</td>
              <td class="num">${UI.money(o.total_amount)}</td><td>${UI.badge(o.status)}</td>
              <td>${UI.esc(o.created_by)}</td><td>${UI.datetime(o.created_at)}</td>
              <td class="actions">
                <button class="btn-link" data-act="detail" data-id="${o.id}">详情</button>
                ${canManage && o.status === "draft" ? `<button class="btn-link" data-act="edit" data-id="${o.id}">编辑</button>` : ""}
                ${canManage && o.status === "draft" ? `<button class="btn-link" data-act="approve" data-id="${o.id}">审核</button>` : ""}
                ${canShip && (o.status === "approved" || o.status === "partially_shipped") ? `<button class="btn-link" data-act="ship" data-id="${o.id}">发货</button>` : ""}
                ${canManage && (o.status === "draft" || o.status === "approved") ? `<button class="btn-link danger" data-act="cancel" data-id="${o.id}">取消</button>` : ""}
                ${canManage && o.status === "draft" ? `<button class="btn-link danger" data-act="del" data-id="${o.id}">删除</button>` : ""}
              </td></tr>`).join("")
            : `<tr><td colspan="8"><div class="empty">暂无销售订单</div></td></tr>`;
            tbody.querySelectorAll("[data-act]").forEach((b) => {
              b.onclick = () => {
                const o = data.items.find((r) => r.id === Number(b.dataset.id));
                ({ detail: showDetail, edit: () => openForm(o), approve: () => approve(o), ship: () => ship(o), cancel: () => cancel(o), del: () => del(o) })[b.dataset.act]();
              };
            });
            UI.pager(el.querySelector("#pager"), { ...data, onChange: (p) => { state.page = p; load(); } });
          } catch (e) { UI.err(e); }
        }

        async function openForm(row) {
          const isEdit = !!row;
          const [customers, warehouses, products] = await Promise.all([
            API.get("/api/master/customers/all"),
            API.get("/api/master/warehouses"),
            API.get("/api/master/products/all"),
          ]);
          const form = document.createElement("div");
          form.innerHTML = `
            <div class="field-row">
              <div class="field"><label>客户 *</label><select id="f-customer"><option value="">请选择</option>
                ${customers.map((c) => `<option value="${c.id}" ${row && row.customer_id === c.id ? "selected" : ""}>${UI.esc(c.name)}</option>`).join("")}</select></div>
              <div class="field"><label>发货仓库 *</label><select id="f-wh"><option value="">请选择</option>
                ${warehouses.map((w) => `<option value="${w.id}" ${row && row.warehouse_id === w.id ? "selected" : ""}>${UI.esc(w.name)}</option>`).join("")}</select></div>
            </div>
            <div class="field"><label>备注</label><input type="text" id="f-remark" value="${UI.esc(row?.remark || "")}"></div>
            <div class="field"><label>商品明细</label></div>
            <div id="f-items"></div>`;

          // 选择仓库后显示库存提示
          const whSel = form.querySelector("#f-wh");
          let stockMap = null;
          async function refreshStockMap() {
            const wid = Number(whSel.value);
            stockMap = wid ? await stockMapFor(wid) : null;
            editor.replaceStockMap(stockMap);
          }
          const editor = OrderEditor.create({
            products, priceField: "sale_price",
            initialItems: row ? row.items.map((it) => ({ product_id: it.product_id, qty: it.qty, price: it.price })) : [],
          });
          form.querySelector("#f-items").appendChild(editor);
          whSel.onchange = refreshStockMap;
          if (row) refreshStockMap();

          const foot = document.createElement("div");
          foot.innerHTML = `<button class="btn btn-ghost" data-act="no">取消</button><button class="btn btn-primary" data-act="yes">${isEdit ? "保存修改" : "创建销售单"}</button>`;
          const m = UI.modal({ title: `${isEdit ? "编辑" : "新建"}销售订单`, body: form, footer: foot, size: "modal-lg" });
          foot.querySelector('[data-act="no"]').onclick = m.close;
          foot.querySelector('[data-act="yes"]').onclick = async () => {
            const cid = Number(form.querySelector("#f-customer").value);
            const wid = Number(form.querySelector("#f-wh").value);
            if (!cid || !wid) return UI.toast("请选择客户和仓库", "error");
            const chk = editor.isValid();
            if (!chk.ok) return UI.toast(chk.msg, "error");
            // 库存预检（仅提示，不强制）
            const items = editor.getItems();
            if (stockMap) {
              for (const it of items) {
                const av = stockMap.get(it.product_id) ?? 0;
                if (it.qty > av) UI.toast(`提示：商品 #${it.product_id} 当前库存 ${UI.qty(av)}，超出部分发货时会校验失败`, "info");
              }
            }
            const payload = { customer_id: cid, warehouse_id: wid, remark: form.querySelector("#f-remark").value, items };
            try {
              if (isEdit) await API.put(`/api/sales/orders/${row.id}`, payload);
              else await API.post("/api/sales/orders", payload);
              UI.toast("保存成功"); m.close(); load();
            } catch (e) { UI.err(e); }
          };
        }

        async function showDetail(o) {
          try {
            const detail = await API.get(`/api/sales/orders/${o.id}`);
            const foot = document.createElement("div");
            foot.innerHTML = `<button class="btn btn-ghost" data-act="close">关闭</button>`;
            const m = UI.modal({ title: `销售订单详情 ${detail.order_no}`, body: orderDetailHtml(detail), footer: foot, size: "modal-lg" });
            foot.querySelector('[data-act="close"]').onclick = m.close;
          } catch (e) { UI.err(e); }
        }

        async function approve(o) {
          if (!await UI.confirm(`确认审核销售单 ${o.order_no} ？`)) return;
          try { await API.post(`/api/sales/orders/${o.id}/approve`); UI.toast("审核成功"); load(); } catch (e) { UI.err(e); }
        }

        async function cancel(o) {
          const m = UI.modal({
            title: `取消销售单 ${o.order_no}`,
            body: `<div class="field"><label>取消原因</label><input type="text" id="cancel-reason" placeholder="必填"></div>`,
            size: "modal-sm",
            footer: (() => { const f = document.createElement("div"); f.innerHTML = `<button class="btn btn-ghost" data-act="no">再想想</button><button class="btn btn-danger" data-act="yes">确认取消</button>`; return f; })(),
          });
          m.el.querySelector('[data-act="no"]').onclick = m.close;
          m.el.querySelector('[data-act="yes"]').onclick = async () => {
            const reason = m.el.querySelector("#cancel-reason").value.trim();
            if (!reason) return UI.toast("请填写取消原因", "error");
            try { await API.post(`/api/sales/orders/${o.id}/cancel`, { reason }); UI.toast("已取消"); m.close(); load(); } catch (e) { UI.err(e); }
          };
        }

        async function ship(o) {
          const detail = await API.get(`/api/sales/orders/${o.id}`);
          const form = document.createElement("div");
          form.innerHTML = `<div class="field"><label>本次发货数量（默认全部剩余数量，超库存将校验失败）</label></div><div id="s-items"></div>
            <div class="field"><label>备注</label><input type="text" id="s-remark"></div>`;
          const editor = OrderEditor.create({
            products: detail.items.map((it) => ({ id: it.product_id, code: it.product_code, name: it.product_name, sale_price: it.price })),
            priceField: "sale_price",
            initialItems: detail.items.filter((it) => it.remain_qty > 0).map((it) => ({ product_id: it.product_id, qty: it.remain_qty, price: it.price })),
          });
          form.querySelector("#s-items").appendChild(editor);
          const foot = document.createElement("div");
          foot.innerHTML = `<button class="btn btn-ghost" data-act="no">取消</button><button class="btn btn-primary" data-act="yes">确认发货出库</button>`;
          const m = UI.modal({ title: `发货出库 - ${o.order_no}`, body: form, footer: foot, size: "modal-lg" });
          foot.querySelector('[data-act="no"]').onclick = m.close;
          foot.querySelector('[data-act="yes"]').onclick = async () => {
            const chk = editor.isValid();
            if (!chk.ok) return UI.toast(chk.msg, "error");
            try {
              const r = await API.post(`/api/sales/orders/${o.id}/ship`, { remark: form.querySelector("#s-remark").value, items: editor.getItems() });
              UI.toast(`发货成功：${r.stock_out_no}，金额 ¥${UI.money(r.total_amount)}`);
              m.close(); load();
            } catch (e) { UI.err(e); }
          };
        }

        async function del(o) {
          if (!await UI.confirm(`确定删除草稿销售单 ${o.order_no} ？`)) return;
          try { await API.del(`/api/sales/orders/${o.id}`); UI.toast("已删除"); load(); } catch (e) { UI.err(e); }
        }

        load();
      },
    },

    /* ---------- 发货出库单 ---------- */
    stockOuts: {
      render(el) {
        const state = { page: 1, page_size: 10, keyword: "" };
        el.innerHTML = `
          <div class="card">
            <div class="toolbar">
              <input type="text" placeholder="搜索出库单号 / 销售单号" id="kw">
              <button class="btn btn-ghost" id="search-btn">查询</button>
            </div>
            <div class="table-wrap"><table class="table">
              <thead><tr><th>出库单号</th><th>来源销售单</th><th>客户</th><th>仓库</th><th class="num">金额</th><th>操作人</th><th>时间</th><th class="actions">操作</th></tr></thead>
              <tbody id="tbody"></tbody></table></div>
            <div class="pager" id="pager"></div>
          </div>`;
        el.querySelector("#search-btn").onclick = () => { state.keyword = el.querySelector("#kw").value.trim(); state.page = 1; load(); };
        el.querySelector("#kw").onkeydown = (e) => { if (e.key === "Enter") el.querySelector("#search-btn").click(); };

        async function load() {
          try {
            const qs = new URLSearchParams(state);
            const data = await API.get(`/api/sales/stock-outs?${qs}`);
            const tbody = el.querySelector("#tbody");
            tbody.innerHTML = data.items.length ? data.items.map((so) => `<tr>
              <td>${UI.esc(so.stock_out_no)}</td><td>${UI.esc(so.so_no)}</td>
              <td>${UI.esc(so.customer_name || "-")}</td><td>${UI.esc(so.warehouse_name || "-")}</td>
              <td class="num">${UI.money(so.total_amount)}</td><td>${UI.esc(so.created_by)}</td>
              <td>${UI.datetime(so.created_at)}</td>
              <td class="actions"><button class="btn-link" data-id="${so.id}">详情</button></td></tr>`).join("")
            : `<tr><td colspan="8"><div class="empty">暂无出库单</div></td></tr>`;
            tbody.querySelectorAll(".btn-link").forEach((b) => b.onclick = async () => {
              const d = await API.get(`/api/sales/stock-outs/${b.dataset.id}`);
              const body = `
                <div class="desc-grid">
                  <div class="desc-item"><span class="k">出库单号</span><span class="v">${UI.esc(d.stock_out_no)}</span></div>
                  <div class="desc-item"><span class="k">销售单号</span><span class="v">${UI.esc(d.so_no)}</span></div>
                  <div class="desc-item"><span class="k">客户</span><span class="v">${UI.esc(d.customer_name || "-")}</span></div>
                  <div class="desc-item"><span class="k">仓库</span><span class="v">${UI.esc(d.warehouse_name || "-")}</span></div>
                  <div class="desc-item"><span class="k">金额</span><span class="v">¥${UI.money(d.total_amount)}</span></div>
                  <div class="desc-item"><span class="k">操作人</span><span class="v">${UI.esc(d.created_by)}</span></div>
                </div>
                <table class="table"><thead><tr><th>商品</th><th>编码</th><th class="num">数量</th><th class="num">单价</th><th class="num">金额</th></tr></thead>
                <tbody>${d.items.map((it) => `<tr><td>${UI.esc(it.product_name)}</td><td>${UI.esc(it.product_code)}</td>
                  <td class="num">${UI.qty(it.qty)}</td><td class="num">${UI.money(it.price)}</td><td class="num">${UI.money(it.amount)}</td></tr>`).join("")}</tbody></table>`;
              const foot = document.createElement("div");
              foot.innerHTML = `<button class="btn btn-ghost">关闭</button>`;
              const m = UI.modal({ title: "出库单详情", body, footer: foot, size: "modal-lg" });
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