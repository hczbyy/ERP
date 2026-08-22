/* ============================================================
 * 库存管理：库存查询 / 库存流水 / 盘点 / 调拨
 * ============================================================ */
(function () {
  window.Pages = window.Pages || {};

  const LOG_TYPE_OPTIONS = "|purchase_in:采购入库|sale_out:销售出库|transfer_in:调拨入库|transfer_out:调拨出库|check_in:盘盈调整|check_out:盘亏调整|initial:期初建账";

  /* ---------- 库存查询 ---------- */
  Pages.inventory = {
    stocks: {
      render(el) {
        const state = { page: 1, page_size: 10, keyword: "", warehouse_id: "", low_stock_only: false };
        el.innerHTML = `
          <div class="card">
            <div class="toolbar">
              <input type="text" placeholder="搜索商品名称 / 编码" id="kw">
              <select id="wh"><option value="">全部仓库</option></select>
              <label style="display:flex;align-items:center;gap:6px;font-size:13px;color:var(--text-2)">
                <input type="checkbox" id="low-only"> 仅看库存预警</label>
              <button class="btn btn-ghost" id="search-btn">查询</button>
            </div>
            <div class="table-wrap"><table class="table">
              <thead><tr><th>商品编码</th><th>商品名称</th><th>仓库</th><th class="num">当前库存</th><th class="num">安全库存</th><th>状态</th></tr></thead>
              <tbody id="tbody"></tbody></table></div>
            <div class="pager" id="pager"></div>
          </div>`;
        (async () => {
          const whs = await API.get("/api/master/warehouses");
          el.querySelector("#wh").innerHTML = `<option value="">全部仓库</option>` +
            whs.map((w) => `<option value="${w.id}">${UI.esc(w.name)}</option>`).join("");
        })();

        const doSearch = () => {
          state.keyword = el.querySelector("#kw").value.trim();
          state.warehouse_id = el.querySelector("#wh").value;
          state.low_stock_only = el.querySelector("#low-only").checked;
          state.page = 1; load();
        };
        el.querySelector("#search-btn").onclick = doSearch;
        el.querySelector("#kw").onkeydown = (e) => { if (e.key === "Enter") doSearch(); };
        el.querySelector("#wh").onchange = doSearch;
        el.querySelector("#low-only").onchange = doSearch;

        async function load() {
          try {
            const qs = new URLSearchParams({ ...state, low_stock_only: state.low_stock_only });
            // 空筛选值不传给后端（int 参数收到空串会 422）
            for (const k of [...qs.keys()]) if (qs.get(k) === "") qs.delete(k);
            const data = await API.get(`/api/inventory/stocks?${qs}`);
            const tbody = el.querySelector("#tbody");
            tbody.innerHTML = data.items.length ? data.items.map((s) => `<tr>
              <td>${UI.esc(s.product_code)}</td><td>${UI.esc(s.product_name)}</td>
              <td>${UI.esc(s.warehouse_name || "-")}</td>
              <td class="num" style="${s.is_low ? "color:var(--danger);font-weight:600" : ""}">${UI.qty(s.qty)} ${UI.esc(s.unit)}</td>
              <td class="num">${UI.qty(s.safety_stock)}</td>
              <td>${s.is_low ? `<span class="badge badge-red">库存不足</span>` : `<span class="badge badge-green">正常</span>`}</td></tr>`).join("")
            : `<tr><td colspan="6"><div class="empty">暂无库存数据</div></td></tr>`;
            UI.pager(el.querySelector("#pager"), { ...data, onChange: (p) => { state.page = p; load(); } });
          } catch (e) { UI.err(e); }
        }
        load();
      },
    },

    /* ---------- 库存流水 ---------- */
    logs: {
      render(el) {
        const state = { page: 1, page_size: 10, product_id: "", warehouse_id: "", log_type: "" };
        el.innerHTML = `
          <div class="card">
            <div class="toolbar">
              <select id="type"><option value="">全部类型</option>${LOG_TYPE_OPTIONS.split("|").filter(Boolean).map((o) => { const [v, t] = o.split(":"); return `<option value="${v}">${t}</option>`; }).join("")}</select>
              <select id="wh"><option value="">全部仓库</option></select>
              <button class="btn btn-ghost" id="search-btn">查询</button>
            </div>
            <div class="table-wrap"><table class="table">
              <thead><tr><th>时间</th><th>商品</th><th>仓库</th><th>类型</th><th class="num">变动</th><th class="num">变动前</th><th class="num">变动后</th><th>关联单号</th><th>操作人</th></tr></thead>
              <tbody id="tbody"></tbody></table></div>
            <div class="pager" id="pager"></div>
          </div>`;
        (async () => {
          const whs = await API.get("/api/master/warehouses");
          el.querySelector("#wh").innerHTML = `<option value="">全部仓库</option>` +
            whs.map((w) => `<option value="${w.id}">${UI.esc(w.name)}</option>`).join("");
        })();
        const doSearch = () => {
          state.log_type = el.querySelector("#type").value;
          state.warehouse_id = el.querySelector("#wh").value;
          state.page = 1; load();
        };
        el.querySelector("#search-btn").onclick = doSearch;
        el.querySelector("#type").onchange = doSearch;
        el.querySelector("#wh").onchange = doSearch;

        async function load() {
          try {
            const qs = new URLSearchParams(state);
            // 空筛选值不传给后端（int 参数收到空串会 422）
            for (const k of [...qs.keys()]) if (qs.get(k) === "") qs.delete(k);
            const data = await API.get(`/api/inventory/logs?${qs}`);
            const tbody = el.querySelector("#tbody");
            tbody.innerHTML = data.items.length ? data.items.map((l) => `<tr>
              <td>${UI.datetime(l.created_at)}</td><td>${UI.esc(l.product_name || "-")}</td>
              <td>${UI.esc(l.warehouse_name || "-")}</td>
              <td><span class="badge badge-cyan">${UI.esc(l.log_type_text)}</span></td>
              <td class="num" style="color:${l.change_qty >= 0 ? "var(--success)" : "var(--danger)"}">${l.change_qty >= 0 ? "+" : ""}${UI.qty(l.change_qty)}</td>
              <td class="num">${UI.qty(l.before_qty)}</td><td class="num">${UI.qty(l.after_qty)}</td>
              <td>${UI.esc(l.ref_no || "-")}</td><td>${UI.esc(l.created_by)}</td></tr>`).join("")
            : `<tr><td colspan="9"><div class="empty">暂无库存流水</div></td></tr>`;
            UI.pager(el.querySelector("#pager"), { ...data, onChange: (p) => { state.page = p; load(); } });
          } catch (e) { UI.err(e); }
        }
        load();
      },
    },

    /* ---------- 盘点管理 ---------- */
    checks: {
      render(el) {
        const state = { page: 1, page_size: 10, status: "" };
        const canManage = ERP.hasPerm("inventory:manage");
        el.innerHTML = `
          <div class="card">
            <div class="toolbar">
              <select id="status"><option value="">全部状态</option><option value="draft">草稿</option><option value="done">已完成</option></select>
              <button class="btn btn-ghost" id="search-btn">查询</button>
              <div class="spacer"></div>
              ${canManage ? `<button class="btn btn-primary" id="add-btn">＋ 新建盘点单</button>` : ""}
            </div>
            <div class="table-wrap"><table class="table">
              <thead><tr><th>盘点单号</th><th>仓库</th><th>状态</th><th>创建人</th><th>完成人</th><th>创建时间</th><th class="actions">操作</th></tr></thead>
              <tbody id="tbody"></tbody></table></div>
            <div class="pager" id="pager"></div>
          </div>`;
        el.querySelector("#search-btn").onclick = () => { state.status = el.querySelector("#status").value; state.page = 1; load(); };
        el.querySelector("#status").onchange = () => el.querySelector("#search-btn").click();
        if (canManage) el.querySelector("#add-btn").onclick = openCreate;

        async function load() {
          try {
            const qs = new URLSearchParams(state);
            const data = await API.get(`/api/inventory/checks?${qs}`);
            const tbody = el.querySelector("#tbody");
            tbody.innerHTML = data.items.length ? data.items.map((c) => `<tr>
              <td>${UI.esc(c.check_no)}</td><td>${UI.esc(c.warehouse_name || "-")}</td>
              <td>${UI.badge(c.status)}</td><td>${UI.esc(c.created_by)}</td><td>${UI.esc(c.done_by || "-")}</td>
              <td>${UI.datetime(c.created_at)}</td>
              <td class="actions">
                <button class="btn-link" data-act="detail" data-id="${c.id}">详情</button>
                ${canManage && c.status === "draft" ? `<button class="btn-link" data-act="edit" data-id="${c.id}">录入实盘</button>` : ""}
                ${canManage && c.status === "draft" ? `<button class="btn-link" data-act="done" data-id="${c.id}">提交盘点</button>` : ""}
              </td></tr>`).join("")
            : `<tr><td colspan="7"><div class="empty">暂无盘点单</div></td></tr>`;
            tbody.querySelectorAll("[data-act]").forEach((b) => {
              b.onclick = () => {
                const c = data.items.find((r) => r.id === Number(b.dataset.id));
                if (!c) { UI.toast("数据已刷新，请重试", "error"); load(); return; }
                ({ detail: () => showDetail(c), edit: () => editItems(c), done: () => submit(c) })[b.dataset.act]();
              };
            });
            UI.pager(el.querySelector("#pager"), { ...data, onChange: (p) => { state.page = p; load(); } });
          } catch (e) { UI.err(e); }
        }

        function openCreate() {
          (async () => {
            const [whs, products] = await Promise.all([
              API.get("/api/master/warehouses"),
              API.get("/api/master/products/all"),
            ]);
            const form = document.createElement("div");
            form.innerHTML = `
              <div class="field"><label>盘点仓库 *</label><select id="c-wh"><option value="">请选择</option>
                ${whs.map((w) => `<option value="${w.id}">${UI.esc(w.name)}</option>`).join("")}</select></div>
              <div class="field"><label>选择盘点商品 *</label><div id="c-prods" style="max-height:220px;overflow-y:auto;border:1px solid var(--border);border-radius:8px;padding:8px">
                ${products.map((p) => `<label style="display:flex;align-items:center;gap:8px;padding:5px 6px;font-size:13px;cursor:pointer">
                  <input type="checkbox" value="${p.id}"> ${UI.esc(p.code)} ${UI.esc(p.name)}</label>`).join("")}
              </div></div>
              <div class="field"><label>备注</label><input type="text" id="c-remark"></div>`;
            const foot = document.createElement("div");
            foot.innerHTML = `<button class="btn btn-ghost" data-act="no">取消</button><button class="btn btn-primary" data-act="yes">创建</button>`;
            const m = UI.modal({ title: "新建盘点单", body: form, footer: foot, size: "modal-lg" });
            foot.querySelector('[data-act="no"]').onclick = m.close;
            foot.querySelector('[data-act="yes"]').onclick = async () => {
              const wid = Number(form.querySelector("#c-wh").value);
              const ids = [...form.querySelectorAll("#c-prods input:checked")].map((i) => Number(i.value));
              if (!wid) return UI.toast("请选择盘点仓库", "error");
              if (!ids.length) return UI.toast("请至少选择一个商品", "error");
              try {
                const r = await API.post("/api/inventory/checks", { warehouse_id: wid, remark: form.querySelector("#c-remark").value, product_ids: ids });
                UI.toast(`盘点单 ${r.check_no} 创建成功`);
                m.close(); load();
              } catch (e) { UI.err(e); }
            };
          })();
        }

        async function showDetail(c) {
          const d = await API.get(`/api/inventory/checks/${c.id}`);
          const diffTotal = d.items.reduce((s, it) => s + it.diff_qty, 0);
          const body = `
            <div class="desc-grid">
              <div class="desc-item"><span class="k">盘点单号</span><span class="v">${UI.esc(d.check_no)}</span></div>
              <div class="desc-item"><span class="k">仓库</span><span class="v">${UI.esc(d.warehouse_name || "-")}</span></div>
              <div class="desc-item"><span class="k">状态</span><span class="v">${UI.badge(d.status)}</span></div>
              <div class="desc-item"><span class="k">差异合计</span><span class="v" style="color:${diffTotal ? "var(--warning)" : "var(--success)"}">${diffTotal > 0 ? "+" : ""}${UI.qty(diffTotal)}</span></div>
            </div>
            <table class="table"><thead><tr><th>商品</th><th class="num">账面数量</th><th class="num">实盘数量</th><th class="num">差异</th></tr></thead>
            <tbody>${d.items.map((it) => `<tr>
              <td>${UI.esc(it.product_name)}（${UI.esc(it.product_code)}）</td>
              <td class="num">${UI.qty(it.book_qty)}</td><td class="num">${UI.qty(it.actual_qty)}</td>
              <td class="num" style="color:${it.diff_qty > 0 ? "var(--success)" : it.diff_qty < 0 ? "var(--danger)" : "var(--gray)"}">${it.diff_qty > 0 ? "+" : ""}${UI.qty(it.diff_qty)}</td></tr>`).join("")}</tbody></table>`;
          const foot = document.createElement("div");
          foot.innerHTML = `<button class="btn btn-ghost">关闭</button>`;
          const m = UI.modal({ title: "盘点单详情", body, footer: foot, size: "modal-lg" });
          foot.querySelector("button").onclick = m.close;
        }

        async function editItems(c) {
          const d = await API.get(`/api/inventory/checks/${c.id}`);
          const form = document.createElement("div");
          form.innerHTML = d.items.map((it) => `
            <div class="field-row">
              <div class="field"><label>${UI.esc(it.product_name)}（账面 ${UI.qty(it.book_qty)}）</label>
                <input type="number" min="0" step="1" data-pid="${it.product_id}" value="${it.actual_qty}"></div>
            </div>`).join("");
          const foot = document.createElement("div");
          foot.innerHTML = `<button class="btn btn-ghost" data-act="no">取消</button><button class="btn btn-primary" data-act="yes">保存实盘数量</button>`;
          const m = UI.modal({ title: `录入实盘 - ${c.check_no}`, body: form, footer: foot, size: "modal-lg" });
          foot.querySelector('[data-act="no"]').onclick = m.close;
          foot.querySelector('[data-act="yes"]').onclick = async () => {
            const inputs = [...form.querySelectorAll("input[data-pid]")];
            const items = [];
            for (const i of inputs) {
              const v = Number(i.value);
              if (!Number.isInteger(v) || v < 0) return UI.toast("实盘数量必须为大于等于 0 的整数", "error");
              items.push({ product_id: Number(i.dataset.pid), actual_qty: v });
            }
            try { await API.put(`/api/inventory/checks/${c.id}`, { items }); UI.toast("实盘数量已保存"); m.close(); load(); } catch (e) { UI.err(e); }
          };
        }

        async function submit(c) {
          if (!await UI.confirm(`提交盘点单 ${c.check_no} 后将按差异调整库存，确定？`)) return;
          try { await API.post(`/api/inventory/checks/${c.id}/done`); UI.toast("盘点完成，库存已调整"); load(); } catch (e) { UI.err(e); }
        }

        load();
      },
    },

    /* ---------- 库存调拨 ---------- */
    transfers: {
      render(el) {
        const state = { page: 1, page_size: 10 };
        const canManage = ERP.hasPerm("inventory:manage");
        el.innerHTML = `
          <div class="card">
            <div class="toolbar">
              <div class="spacer"></div>
              ${canManage ? `<button class="btn btn-primary" id="add-btn">＋ 新建调拨单</button>` : ""}
            </div>
            <div class="table-wrap"><table class="table">
              <thead><tr><th>调拨单号</th><th>调出仓库</th><th>调入仓库</th><th>操作人</th><th>时间</th><th>备注</th></tr></thead>
              <tbody id="tbody"></tbody></table></div>
            <div class="pager" id="pager"></div>
          </div>`;
        if (canManage) el.querySelector("#add-btn").onclick = openCreate;

        async function load() {
          try {
            const qs = new URLSearchParams(state);
            const data = await API.get(`/api/inventory/transfers?${qs}`);
            const tbody = el.querySelector("#tbody");
            tbody.innerHTML = data.items.length ? data.items.map((t) => `<tr>
              <td>${UI.esc(t.transfer_no)}</td><td>${UI.esc(t.from_warehouse_name || "-")}</td>
              <td>${UI.esc(t.to_warehouse_name || "-")}</td><td>${UI.esc(t.created_by)}</td>
              <td>${UI.datetime(t.created_at)}</td><td>${UI.esc(t.remark || "-")}</td></tr>`).join("")
            : `<tr><td colspan="6"><div class="empty">暂无调拨单</div></td></tr>`;
            UI.pager(el.querySelector("#pager"), { ...data, onChange: (p) => { state.page = p; load(); } });
          } catch (e) { UI.err(e); }
        }

        function openCreate() {
          (async () => {
            const [whs, products] = await Promise.all([
              API.get("/api/master/warehouses"),
              API.get("/api/master/products/all"),
            ]);
            const form = document.createElement("div");
            form.innerHTML = `
              <div class="field-row">
                <div class="field"><label>调出仓库 *</label><select id="t-from"><option value="">请选择</option>
                  ${whs.map((w) => `<option value="${w.id}">${UI.esc(w.name)}</option>`).join("")}</select></div>
                <div class="field"><label>调入仓库 *</label><select id="t-to"><option value="">请选择</option>
                  ${whs.map((w) => `<option value="${w.id}">${UI.esc(w.name)}</option>`).join("")}</select></div>
              </div>
              <div class="field"><label>备注</label><input type="text" id="t-remark"></div>
              <div class="field"><label>调拨明细</label></div><div id="t-items"></div>`;
            const editor = OrderEditor.create({ products, priceField: "purchase_price" });
            form.querySelector("#t-items").appendChild(editor);
            const foot = document.createElement("div");
            foot.innerHTML = `<button class="btn btn-ghost" data-act="no">取消</button><button class="btn btn-primary" data-act="yes">确认调拨</button>`;
            const m = UI.modal({ title: "新建调拨单", body: form, footer: foot, size: "modal-lg" });
            foot.querySelector('[data-act="no"]').onclick = m.close;
            foot.querySelector('[data-act="yes"]').onclick = async () => {
              const from = Number(form.querySelector("#t-from").value);
              const to = Number(form.querySelector("#t-to").value);
              if (!from || !to) return UI.toast("请选择调出和调入仓库", "error");
              if (from === to) return UI.toast("调出与调入仓库不能相同", "error");
              const chk = editor.isValid();
              if (!chk.ok) return UI.toast(chk.msg, "error");
              const items = editor.getItems().map((it) => ({ product_id: it.product_id, qty: it.qty }));
              try {
                const r = await API.post("/api/inventory/transfers", { from_warehouse_id: from, to_warehouse_id: to, remark: form.querySelector("#t-remark").value, items });
                UI.toast(`调拨成功：${r.transfer_no}`);
                m.close(); load();
              } catch (e) { UI.err(e); }
            };
          })();
        }

        load();
      },
    },
  };
})();
