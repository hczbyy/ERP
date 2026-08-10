/* ============================================================
 * 基础数据：商品 / 客户 / 供应商 / 仓库（配置式 CRUD）
 * ============================================================ */
(function () {
  window.Pages = window.Pages || {};

  /* 通用 CRUD 页面渲染器 */
  function crudPage(cfg) {
    const state = { page: 1, page_size: 10, keyword: "", status: "" };

    function buildForm(fields, data = {}, extra = {}) {
      const html = fields.map((f) => {
        const val = data[f.name] ?? f.default ?? "";
        const opts = f.options ? (typeof f.options === "function" ? "" : f.options) : "";
        let control = "";
        if (f.type === "select" && !(typeof f.options === "function")) {
          control = `<select name="${f.name}">${opts.split("|").map((o) => {
            const [v, t] = o.split(":");
            return `<option value="${v}" ${String(val) === v ? "selected" : ""}>${t || v}</option>`;
          }).join("")}</select>`;
        } else if (f.type === "select-dynamic") {
          control = `<select name="${f.name}" data-dynamic="1"><option value="">加载中...</option></select>`;
        } else if (f.type === "textarea") {
          control = `<textarea name="${f.name}">${UI.esc(val)}</textarea>`;
        } else if (f.type === "number") {
          control = `<input type="number" step="0.01" name="${f.name}" value="${val}">`;
        } else {
          control = `<input type="text" name="${f.name}" value="${UI.esc(val)}">`;
        }
        return `<div class="field ${f.span === 2 ? "" : ""}" style="${f.span === 2 ? "" : ""}">
          <label>${f.label}${f.required ? " *" : ""}</label>${control}</div>`;
      }).join("");

      const form = document.createElement("form");
      form.innerHTML = `<div class="field-row-3">${html}</div>`;
      form.onsubmit = (e) => e.preventDefault();

      // 动态下拉数据加载
      fields.filter((f) => f.type === "select-dynamic").forEach(async (f) => {
        const sel = form.querySelector(`[name="${f.name}"]`);
        const list = await f.options();
        sel.innerHTML = `<option value="">${f.placeholder || "请选择"}</option>` +
          list.map((o) => `<option value="${o.value}" ${String(data[f.name]) === String(o.value) ? "selected" : ""}>${UI.esc(o.label)}</option>`).join("");
        if (extra.onLoaded) extra.onLoaded(form);
      });
      return form;
    }

    function collect(form, fields) {
      const obj = {};
      fields.forEach((f) => {
        const el = form.querySelector(`[name="${f.name}"]`);
        if (el) obj[f.name] = f.type === "number" ? Number(el.value) : el.value;
      });
      return obj;
    }

    function render(el) {
      const canManage = ERP.hasPerm(cfg.permManage);
      el.innerHTML = `
        <div class="card">
          <div class="toolbar">
            <input type="text" placeholder="${cfg.searchPlaceholder}" id="kw">
            ${cfg.statusFilter ? `<select id="status-filter"><option value="">全部状态</option>
              <option value="active">启用</option><option value="disabled">停用</option></select>` : ""}
            <button class="btn btn-ghost" id="search-btn">查询</button>
            <div class="spacer"></div>
            ${canManage ? `<button class="btn btn-primary" id="add-btn">＋ 新增${cfg.itemName}</button>` : ""}
          </div>
          <div class="table-wrap">
            <table class="table">
              <thead><tr>${cfg.columns.map((c) => `<th class="${c.cls || ""}">${c.label}</th>`).join("")}
                <th class="actions">操作</th></tr></thead>
              <tbody id="tbody"><tr><td colspan="${cfg.columns.length + 1}"><div class="empty">加载中...</div></td></tr></tbody>
            </table>
          </div>
          <div class="pager" id="pager"></div>
        </div>`;

      el.querySelector("#search-btn").onclick = () => { state.keyword = el.querySelector("#kw").value.trim(); state.page = 1; load(); };
      el.querySelector("#kw").onkeydown = (e) => { if (e.key === "Enter") el.querySelector("#search-btn").click(); };
      const statusSel = el.querySelector("#status-filter");
      if (statusSel) statusSel.onchange = () => { state.status = statusSel.value; state.page = 1; load(); };
      if (canManage) el.querySelector("#add-btn").onclick = () => openForm(null);

      async function load() {
        try {
          const qs = new URLSearchParams({ page: state.page, page_size: state.page_size, keyword: state.keyword, status: state.status });
          const data = await API.get(`${cfg.apiBase}?${qs}`);
          // 兼容两种响应：分页结构 {items,total,...} 或全量数组（如仓库列表接口）
          const isArray = Array.isArray(data);
          let items = isArray ? data.slice() : data.items;
          if (isArray) {
            if (state.keyword) items = items.filter((r) => String(r.code).includes(state.keyword) || String(r.name).includes(state.keyword));
            if (state.status) items = items.filter((r) => r.status === state.status);
          }
          const tbody = el.querySelector("#tbody");
          tbody.innerHTML = items.length
            ? items.map((row) => `<tr>
                ${cfg.columns.map((c) => `<td class="${c.cls || ""}">${c.render ? c.render(row) : UI.esc(row[c.key])}</td>`).join("")}
                <td class="actions">
                  ${canManage ? `<button class="btn-link" data-act="edit" data-id="${row.id}">编辑</button>
                  <button class="btn-link danger" data-act="del" data-id="${row.id}">删除</button>` : "-"}
                </td></tr>`).join("")
            : `<tr><td colspan="${cfg.columns.length + 1}"><div class="empty">暂无数据</div></td></tr>`;
          tbody.querySelectorAll("[data-act]").forEach((b) => {
            b.onclick = () => {
              const row = items.find((r) => r.id === Number(b.dataset.id));
              b.dataset.act === "edit" ? openForm(row) : del(row);
            };
          });
          const pager = el.querySelector("#pager");
          if (isArray) pager.textContent = `共 ${items.length} 条`;
          else UI.pager(pager, { ...data, onChange: (p) => { state.page = p; load(); } });
        } catch (e) { UI.err(e); }
      }

      function openForm(row) {
        const isEdit = !!row;
        const form = buildForm(cfg.fields, row || {});
        const foot = document.createElement("div");
        foot.innerHTML = `<button class="btn btn-ghost" data-act="no">取消</button>
          <button class="btn btn-primary" data-act="yes">${isEdit ? "保存修改" : "创建"}</button>`;
        const m = UI.modal({ title: `${isEdit ? "编辑" : "新增"}${cfg.itemName}`, body: form, footer: foot });
        foot.querySelector('[data-act="no"]').onclick = m.close;
        foot.querySelector('[data-act="yes"]').onclick = async () => {
          const payload = collect(form, cfg.fields);
          for (const f of cfg.fields) {
            if (f.required && !payload[f.name] && payload[f.name] !== 0) {
              UI.toast(`请填写「${f.label}」`, "error"); return;
            }
          }
          try {
            if (isEdit) await API.put(`${cfg.apiBase}/${row.id}`, payload);
            else await API.post(cfg.apiBase, payload);
            UI.toast("保存成功");
            m.close(); load();
          } catch (e) { UI.err(e); }
        };
      }

      async function del(row) {
        const ok = await UI.confirm(`确定删除「${row[cfg.nameKey] || row.name || row.code}」吗？`);
        if (!ok) return;
        try {
          await API.del(`${cfg.apiBase}/${row.id}`);
          UI.toast("已删除");
          load();
        } catch (e) { UI.err(e); }
      }

      load();
    }

    return { render };
  }

  const statusBadge = (row) => UI.badge(row.status);

  /* ---------- 商品管理 ---------- */
  Pages.master = {
    product: crudPage({
      title: "商品管理", itemName: "商品", permManage: "master:product:manage",
      apiBase: "/api/master/products", searchPlaceholder: "搜索商品名称 / 编码",
      nameKey: "name",
      columns: [
        { key: "code", label: "编码" },
        { key: "name", label: "名称" },
        { key: "spec", label: "规格" },
        { key: "unit", label: "单位" },
        { key: "category_name", label: "分类" },
        { key: "purchase_price", label: "采购价", cls: "num", render: (r) => UI.money(r.purchase_price) },
        { key: "sale_price", label: "销售价", cls: "num", render: (r) => UI.money(r.sale_price) },
        { key: "safety_stock", label: "安全库存", cls: "num", render: (r) => UI.qty(r.safety_stock) },
        { key: "status", label: "状态", render: statusBadge },
      ],
      statusFilter: true,
      fields: [
        { name: "code", label: "商品编码", required: true },
        { name: "name", label: "商品名称", required: true },
        { name: "spec", label: "规格型号" },
        { name: "unit", label: "计量单位", default: "件" },
        { name: "barcode", label: "条码" },
        { name: "category_id", label: "商品分类", type: "select-dynamic",
          options: async () => (await API.get("/api/master/categories")).map((c) => ({ value: c.id, label: c.name })) },
        { name: "purchase_price", label: "采购价", type: "number", default: 0 },
        { name: "sale_price", label: "销售价", type: "number", default: 0 },
        { name: "safety_stock", label: "安全库存", type: "number", default: 0 },
        { name: "status", label: "状态", type: "select", options: "active:启用|disabled:停用", default: "active" },
        { name: "description", label: "备注", type: "textarea", span: 2 },
      ],
    }),

    /* ---------- 客户管理 ---------- */
    customer: crudPage({
      title: "客户管理", itemName: "客户", permManage: "master:customer:manage",
      apiBase: "/api/master/customers", searchPlaceholder: "搜索客户名称 / 编码",
      nameKey: "name",
      columns: [
        { key: "code", label: "编码" },
        { key: "name", label: "客户名称" },
        { key: "contact", label: "联系人" },
        { key: "phone", label: "电话" },
        { key: "address", label: "地址" },
        { key: "credit_limit", label: "信用额度", cls: "num", render: (r) => UI.money(r.credit_limit) },
        { key: "status", label: "状态", render: statusBadge },
      ],
      statusFilter: true,
      fields: [
        { name: "code", label: "客户编码", required: true },
        { name: "name", label: "客户名称", required: true },
        { name: "contact", label: "联系人" },
        { name: "phone", label: "联系电话" },
        { name: "address", label: "地址" },
        { name: "credit_limit", label: "信用额度", type: "number", default: 0 },
        { name: "status", label: "状态", type: "select", options: "active:启用|disabled:停用", default: "active" },
      ],
    }),

    /* ---------- 供应商管理 ---------- */
    supplier: crudPage({
      title: "供应商管理", itemName: "供应商", permManage: "master:supplier:manage",
      apiBase: "/api/master/suppliers", searchPlaceholder: "搜索供应商名称 / 编码",
      nameKey: "name",
      columns: [
        { key: "code", label: "编码" },
        { key: "name", label: "供应商名称" },
        { key: "contact", label: "联系人" },
        { key: "phone", label: "电话" },
        { key: "address", label: "地址" },
        { key: "status", label: "状态", render: statusBadge },
      ],
      statusFilter: true,
      fields: [
        { name: "code", label: "供应商编码", required: true },
        { name: "name", label: "供应商名称", required: true },
        { name: "contact", label: "联系人" },
        { name: "phone", label: "联系电话" },
        { name: "address", label: "地址" },
        { name: "status", label: "状态", type: "select", options: "active:启用|disabled:停用", default: "active" },
      ],
    }),

    /* ---------- 仓库管理 ---------- */
    warehouse: crudPage({
      title: "仓库管理", itemName: "仓库", permManage: "master:warehouse:manage",
      apiBase: "/api/master/warehouses", searchPlaceholder: "搜索仓库名称 / 编码",
      nameKey: "name",
      columns: [
        { key: "code", label: "编码" },
        { key: "name", label: "仓库名称" },
        { key: "manager", label: "负责人" },
        { key: "address", label: "地址" },
        { key: "status", label: "状态", render: statusBadge },
      ],
      statusFilter: true,
      fields: [
        { name: "code", label: "仓库编码", required: true },
        { name: "name", label: "仓库名称", required: true },
        { name: "manager", label: "负责人" },
        { name: "address", label: "地址" },
        { name: "status", label: "状态", type: "select", options: "active:启用|disabled:停用", default: "active" },
      ],
    }),
  };
})();