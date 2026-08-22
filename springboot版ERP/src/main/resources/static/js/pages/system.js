/* ============================================================
 * 系统管理：用户 / 角色权限 / 部门 / 员工 / 审计日志
 * ============================================================ */
(function () {
  window.Pages = window.Pages || {};

  const MODULE_NAMES = {
    dashboard: "仪表盘", master: "基础数据", purchase: "采购管理", sales: "销售管理",
    inventory: "库存管理", finance: "财务管理", system: "系统管理", auth: "认证",
  };
  const ACTION_NAMES = {
    login: "登录", create: "创建", update: "修改", delete: "删除", approve: "审核",
    receive: "收货", ship: "发货", check: "盘点", transfer: "调拨", pay: "收付款", cancel: "取消",
  };

  /* ---------- 用户管理 ---------- */
  Pages.system = {
    users: {
      render(el) {
        const state = { page: 1, page_size: 10, keyword: "" };
        el.innerHTML = `
          <div class="card">
            <div class="toolbar">
              <input type="text" placeholder="搜索用户名 / 姓名" id="kw">
              <button class="btn btn-ghost" id="search-btn">查询</button>
              <div class="spacer"></div>
              <button class="btn btn-primary" id="add-btn">＋ 新增用户</button>
            </div>
            <div class="table-wrap"><table class="table">
              <thead><tr><th>ID</th><th>用户名</th><th>姓名</th><th>邮箱</th><th>手机</th><th>角色</th><th>状态</th><th>创建时间</th><th class="actions">操作</th></tr></thead>
              <tbody id="tbody"></tbody></table></div>
            <div class="pager" id="pager"></div>
          </div>`;
        el.querySelector("#search-btn").onclick = () => { state.keyword = el.querySelector("#kw").value.trim(); state.page = 1; load(); };
        el.querySelector("#kw").onkeydown = (e) => { if (e.key === "Enter") el.querySelector("#search-btn").click(); };
        el.querySelector("#add-btn").onclick = () => openForm(null);

        async function load() {
          try {
            const qs = new URLSearchParams(state);
            const data = await API.get(`/api/system/users?${qs}`);
            const tbody = el.querySelector("#tbody");
            tbody.innerHTML = data.items.length ? data.items.map((u) => `<tr>
              <td>${u.id}</td><td>${UI.esc(u.username)}${u.is_superuser ? ' <span class="badge badge-red">超管</span>' : ""}</td>
              <td>${UI.esc(u.display_name)}</td><td>${UI.esc(u.email || "-")}</td><td>${UI.esc(u.phone || "-")}</td>
              <td>${u.roles.map((r) => `<span class="badge badge-blue">${UI.esc(r.name)}</span>`).join(" ") || "-"}</td>
              <td>${u.is_active ? '<span class="badge badge-green">启用</span>' : '<span class="badge badge-gray">禁用</span>'}</td>
              <td>${UI.datetime(u.created_at)}</td>
              <td class="actions">
                <button class="btn-link" data-act="edit" data-id="${u.id}">编辑</button>
                ${!u.is_superuser ? `<button class="btn-link" data-act="toggle" data-id="${u.id}">${u.is_active ? "禁用" : "启用"}</button>` : ""}
                ${!u.is_superuser ? `<button class="btn-link danger" data-act="del" data-id="${u.id}">删除</button>` : ""}
              </td></tr>`).join("")
            : `<tr><td colspan="9"><div class="empty">暂无用户</div></td></tr>`;
            tbody.querySelectorAll("[data-act]").forEach((b) => {
              b.onclick = () => {
                const u = data.items.find((r) => r.id === Number(b.dataset.id));
                if (!u) { UI.toast("数据已刷新，请重试", "error"); load(); return; }
                ({ edit: () => openForm(u), toggle: () => toggle(u), del: () => del(u) })[b.dataset.act]();
              };
            });
            UI.pager(el.querySelector("#pager"), { ...data, onChange: (p) => { state.page = p; load(); } });
          } catch (e) { UI.err(e); }
        }

        async function openForm(u) {
          const isEdit = !!u;
          const roles = await API.get("/api/system/roles");
          const form = document.createElement("div");
          form.innerHTML = `
            <div class="field-row">
              <div class="field"><label>用户名 *</label><input type="text" id="u-name" value="${UI.esc(u?.username || "")}"></div>
              <div class="field"><label>姓名 *</label><input type="text" id="u-display" value="${UI.esc(u?.display_name || "")}"></div>
            </div>
            <div class="field-row">
              <div class="field"><label>${isEdit ? "密码（留空不修改）" : "密码 *"}</label><input type="password" id="u-pwd" placeholder="${isEdit ? "留空保持不变" : "至少6位"}"></div>
              <div class="field"><label>手机号</label><input type="text" id="u-phone" value="${UI.esc(u?.phone || "")}"></div>
            </div>
            <div class="field"><label>邮箱</label><input type="email" id="u-email" value="${UI.esc(u?.email || "")}"></div>
            <div class="field"><label>角色</label><div id="u-roles" style="display:flex;flex-wrap:wrap;gap:8px">
              ${roles.map((r) => `<label style="display:flex;align-items:center;gap:6px;font-size:13px;cursor:pointer">
                <input type="checkbox" value="${r.id}" ${u && u.roles.some((ur) => ur.id === r.id) ? "checked" : ""}> ${UI.esc(r.name)}</label>`).join("")}
            </div></div>`;
            const foot = document.createElement("div");
            foot.innerHTML = `<button class="btn btn-ghost" data-act="no">取消</button><button class="btn btn-primary" data-act="yes">${isEdit ? "保存修改" : "创建用户"}</button>`;
            const m = UI.modal({ title: `${isEdit ? "编辑" : "新增"}用户`, body: form, footer: foot });
            foot.querySelector('[data-act="no"]').onclick = m.close;
            foot.querySelector('[data-act="yes"]').onclick = async () => {
              const payload = {
                username: form.querySelector("#u-name").value.trim(),
                display_name: form.querySelector("#u-display").value.trim(),
                email: form.querySelector("#u-email").value.trim() || null,
                phone: form.querySelector("#u-phone").value.trim() || null,
                role_ids: [...form.querySelectorAll("#u-roles input:checked")].map((i) => Number(i.value)),
              };
              if (!payload.username || !payload.display_name) return UI.toast("用户名和姓名必填", "error");
              if (!isEdit) {
                const pwd = form.querySelector("#u-pwd").value;
                if (pwd.length < 6) return UI.toast("密码至少 6 位", "error");
                payload.password = pwd;
              } else {
                const pwd = form.querySelector("#u-pwd").value;
                if (pwd) payload.password = pwd;
              }
              try {
                if (isEdit) await API.put(`/api/system/users/${u.id}`, payload);
                else await API.post("/api/system/users", payload);
                UI.toast("保存成功"); m.close(); load();
              } catch (e) { UI.err(e); }
            };
        }

        async function toggle(u) {
          if (!await UI.confirm(`确定${u.is_active ? "禁用" : "启用"}用户「${u.display_name}」？`)) return;
          try { await API.post(`/api/system/users/${u.id}/toggle-active`); UI.toast("操作成功"); load(); } catch (e) { UI.err(e); }
        }

        async function del(u) {
          if (!await UI.confirm(`确定删除用户「${u.display_name}」？`)) return;
          try { await API.del(`/api/system/users/${u.id}`); UI.toast("已删除"); load(); } catch (e) { UI.err(e); }
        }

        load();
      },
    },

    /* ---------- 角色权限 ---------- */
    roles: {
      render(el) {
        el.innerHTML = `
          <div class="card">
            <div class="toolbar">
              <div class="spacer"></div>
              <button class="btn btn-primary" id="add-btn">＋ 新增角色</button>
            </div>
            <div class="table-wrap"><table class="table">
              <thead><tr><th>编码</th><th>名称</th><th>描述</th><th>权限数</th><th>类型</th><th class="actions">操作</th></tr></thead>
              <tbody id="tbody"></tbody></table></div>
          </div>`;
        el.querySelector("#add-btn").onclick = () => openForm(null);
        load();

        async function load() {
          try {
            const roles = await API.get("/api/system/roles");
            const tbody = el.querySelector("#tbody");
            tbody.innerHTML = roles.length ? roles.map((r) => `<tr>
              <td>${UI.esc(r.code)}</td><td>${UI.esc(r.name)}</td><td>${UI.esc(r.description || "-")}</td>
              <td>${r.permission_ids.length}</td>
              <td>${r.is_builtin ? '<span class="badge badge-gray">内置</span>' : '<span class="badge badge-cyan">自定义</span>'}</td>
              <td class="actions">
                <button class="btn-link" data-act="edit" data-id="${r.id}">编辑</button>
                ${r.is_builtin ? "" : `<button class="btn-link danger" data-act="del" data-id="${r.id}">删除</button>`}
              </td></tr>`).join("")
            : `<tr><td colspan="6"><div class="empty">暂无角色</div></td></tr>`;
            tbody.querySelectorAll("[data-act]").forEach((b) => {
              b.onclick = () => {
                const r = roles.find((x) => x.id === Number(b.dataset.id));
                if (!r) { UI.toast("数据已刷新，请重试", "error"); load(); return; }
                b.dataset.act === "edit" ? openForm(r) : del(r);
              };
            });
          } catch (e) { UI.err(e); }
        }

        async function openForm(r) {
          const isEdit = !!r;
          const perms = await API.get("/api/system/permissions");
          const form = document.createElement("div");
          form.innerHTML = `
            <div class="field-row">
              <div class="field"><label>角色编码 *</label><input type="text" id="r-code" value="${UI.esc(r?.code || "")}" ${r?.is_builtin ? "disabled style='background:#f3f4f6'" : ""}></div>
              <div class="field"><label>角色名称 *</label><input type="text" id="r-name" value="${UI.esc(r?.name || "")}"></div>
            </div>
            <div class="field"><label>描述</label><input type="text" id="r-desc" value="${UI.esc(r?.description || "")}"></div>
            <div class="field"><label>权限点</label>
              <div style="border:1px solid var(--border);border-radius:8px;padding:10px;max-height:300px;overflow-y:auto">
                ${Object.entries(perms.groups).map(([mod, list]) => `
                  <div style="margin-bottom:10px">
                    <div style="font-weight:600;font-size:13px;margin-bottom:4px">${MODULE_NAMES[mod] || mod}</div>
                    <div style="display:flex;flex-wrap:wrap;gap:8px">
                      ${list.map((p) => `<label style="display:flex;align-items:center;gap:5px;font-size:12px;cursor:pointer">
                        <input type="checkbox" value="${p.id}" data-code="${p.code}" ${r && r.permission_ids.includes(p.id) ? "checked" : ""}> ${UI.esc(p.name)}</label>`).join("")}
                    </div>
                  </div>`).join("")}
              </div>
            </div>`;
            const foot = document.createElement("div");
            foot.innerHTML = `<button class="btn btn-ghost" data-act="no">取消</button><button class="btn btn-primary" data-act="yes">${isEdit ? "保存修改" : "创建角色"}</button>`;
            const m = UI.modal({ title: `${isEdit ? "编辑" : "新增"}角色`, body: form, footer: foot, size: "modal-lg" });
            foot.querySelector('[data-act="no"]').onclick = m.close;
            foot.querySelector('[data-act="yes"]').onclick = async () => {
              const payload = {
                code: form.querySelector("#r-code").value.trim(),
                name: form.querySelector("#r-name").value.trim(),
                description: form.querySelector("#r-desc").value.trim() || null,
                permission_ids: [...form.querySelectorAll("input[type=checkbox]:checked")].map((i) => Number(i.value)),
              };
              if (!payload.code || !payload.name) return UI.toast("编码和名称必填", "error");
              try {
                if (isEdit) await API.put(`/api/system/roles/${r.id}`, payload);
                else await API.post("/api/system/roles", payload);
                UI.toast("保存成功"); m.close(); load();
              } catch (e) { UI.err(e); }
            };
        }

        async function del(r) {
          if (!await UI.confirm(`确定删除角色「${r.name}」？`)) return;
          try { await API.del(`/api/system/roles/${r.id}`); UI.toast("已删除"); load(); } catch (e) { UI.err(e); }
        }
      },
    },

    /* ---------- 组织架构（部门） ---------- */
    departments: {
      render(el) {
        el.innerHTML = `
          <div class="card">
            <div class="toolbar"><div class="spacer"></div><button class="btn btn-primary" id="add-btn">＋ 新增部门</button></div>
            <div class="table-wrap"><table class="table">
              <thead><tr><th>编码</th><th>名称</th><th>负责人</th><th>电话</th><th>备注</th><th class="actions">操作</th></tr></thead>
              <tbody id="tbody"></tbody></table></div>
          </div>`;
        el.querySelector("#add-btn").onclick = () => openForm(null);
        load();

        async function load() {
          try {
            const depts = await API.get("/api/system/departments");
            const tbody = el.querySelector("#tbody");
            tbody.innerHTML = depts.length ? depts.map((d) => `<tr>
              <td>${UI.esc(d.code)}</td><td>${UI.esc(d.name)}</td><td>${UI.esc(d.leader || "-")}</td>
              <td>${UI.esc(d.phone || "-")}</td><td>${UI.esc(d.remark || "-")}</td>
              <td class="actions"><button class="btn-link" data-act="edit" data-id="${d.id}">编辑</button>
              <button class="btn-link danger" data-act="del" data-id="${d.id}">删除</button></td></tr>`).join("")
            : `<tr><td colspan="6"><div class="empty">暂无部门</div></td></tr>`;
            tbody.querySelectorAll("[data-act]").forEach((b) => {
              b.onclick = () => {
                const d = depts.find((x) => x.id === Number(b.dataset.id));
                if (!d) { UI.toast("数据已刷新，请重试", "error"); load(); return; }
                b.dataset.act === "edit" ? openForm(d) : del(d);
              };
            });
          } catch (e) { UI.err(e); }
        }

        function openForm(d) {
          const isEdit = !!d;
          const form = document.createElement("div");
          form.innerHTML = `
            <div class="field-row">
              <div class="field"><label>部门编码 *</label><input type="text" id="d-code" value="${UI.esc(d?.code || "")}"></div>
              <div class="field"><label>部门名称 *</label><input type="text" id="d-name" value="${UI.esc(d?.name || "")}"></div>
            </div>
            <div class="field-row">
              <div class="field"><label>负责人</label><input type="text" id="d-leader" value="${UI.esc(d?.leader || "")}"></div>
              <div class="field"><label>电话</label><input type="text" id="d-phone" value="${UI.esc(d?.phone || "")}"></div>
            </div>
            <div class="field"><label>备注</label><input type="text" id="d-remark" value="${UI.esc(d?.remark || "")}"></div>`;
          const foot = document.createElement("div");
          foot.innerHTML = `<button class="btn btn-ghost" data-act="no">取消</button><button class="btn btn-primary" data-act="yes">${isEdit ? "保存" : "创建"}</button>`;
          const m = UI.modal({ title: `${isEdit ? "编辑" : "新增"}部门`, body: form, footer: foot });
          foot.querySelector('[data-act="no"]').onclick = m.close;
          foot.querySelector('[data-act="yes"]').onclick = async () => {
            const payload = {
              code: form.querySelector("#d-code").value.trim(),
              name: form.querySelector("#d-name").value.trim(),
              leader: form.querySelector("#d-leader").value.trim() || null,
              phone: form.querySelector("#d-phone").value.trim() || null,
              remark: form.querySelector("#d-remark").value.trim() || null,
            };
            if (!payload.code || !payload.name) return UI.toast("编码和名称必填", "error");
            try {
              if (isEdit) await API.put(`/api/system/departments/${d.id}`, payload);
              else await API.post("/api/system/departments", payload);
              UI.toast("保存成功"); m.close(); load();
            } catch (e) { UI.err(e); }
          };
        }

        async function del(d) {
          if (!await UI.confirm(`确定删除部门「${d.name}」？`)) return;
          try { await API.del(`/api/system/departments/${d.id}`); UI.toast("已删除"); load(); } catch (e) { UI.err(e); }
        }
      },
    },

    /* ---------- 员工管理 ---------- */
    employees: {
      render(el) {
        const state = { page: 1, page_size: 10, keyword: "" };
        el.innerHTML = `
          <div class="card">
            <div class="toolbar">
              <input type="text" placeholder="搜索姓名 / 工号" id="kw">
              <button class="btn btn-ghost" id="search-btn">查询</button>
              <div class="spacer"></div>
              <button class="btn btn-primary" id="add-btn">＋ 新增员工</button>
            </div>
            <div class="table-wrap"><table class="table">
              <thead><tr><th>工号</th><th>姓名</th><th>性别</th><th>部门</th><th>职位</th><th>电话</th><th>入职日期</th><th>状态</th><th class="actions">操作</th></tr></thead>
              <tbody id="tbody"></tbody></table></div>
            <div class="pager" id="pager"></div>
          </div>`;
        el.querySelector("#search-btn").onclick = () => { state.keyword = el.querySelector("#kw").value.trim(); state.page = 1; load(); };
        el.querySelector("#kw").onkeydown = (e) => { if (e.key === "Enter") el.querySelector("#search-btn").click(); };
        el.querySelector("#add-btn").onclick = () => openForm(null);

        async function load() {
          try {
            const qs = new URLSearchParams(state);
            const data = await API.get(`/api/system/employees?${qs}`);
            const tbody = el.querySelector("#tbody");
            tbody.innerHTML = data.items.length ? data.items.map((e) => `<tr>
              <td>${UI.esc(e.emp_no)}</td><td>${UI.esc(e.name)}</td><td>${UI.esc(e.gender || "-")}</td>
              <td>${UI.esc(e.department_name || "-")}</td><td>${UI.esc(e.position || "-")}</td>
              <td>${UI.esc(e.phone || "-")}</td><td>${UI.date(e.hire_date)}</td>
              <td>${UI.badge(e.status)}</td>
              <td class="actions"><button class="btn-link" data-act="edit" data-id="${e.id}">编辑</button>
              <button class="btn-link danger" data-act="del" data-id="${e.id}">删除</button></td></tr>`).join("")
            : `<tr><td colspan="9"><div class="empty">暂无员工</div></td></tr>`;
            tbody.querySelectorAll("[data-act]").forEach((b) => {
              b.onclick = () => {
                const e = data.items.find((x) => x.id === Number(b.dataset.id));
                if (!e) { UI.toast("数据已刷新，请重试", "error"); load(); return; }
                b.dataset.act === "edit" ? openForm(e) : del(e);
              };
            });
            UI.pager(el.querySelector("#pager"), { ...data, onChange: (p) => { state.page = p; load(); } });
          } catch (e) { UI.err(e); }
        }

        async function openForm(e) {
          const isEdit = !!e;
          const depts = await API.get("/api/system/departments");
          const form = document.createElement("div");
          form.innerHTML = `
            <div class="field-row">
              <div class="field"><label>工号 *</label><input type="text" id="e-no" value="${UI.esc(e?.emp_no || "")}"></div>
              <div class="field"><label>姓名 *</label><input type="text" id="e-name" value="${UI.esc(e?.name || "")}"></div>
            </div>
            <div class="field-row">
              <div class="field"><label>性别</label><select id="e-gender"><option value="">请选择</option>
                <option value="男" ${e?.gender === "男" ? "selected" : ""}>男</option>
                <option value="女" ${e?.gender === "女" ? "selected" : ""}>女</option></select></div>
              <div class="field"><label>部门</label><select id="e-dept"><option value="">请选择</option>
                ${depts.map((d) => `<option value="${d.id}" ${e && e.department_id === d.id ? "selected" : ""}>${UI.esc(d.name)}</option>`).join("")}</select></div>
            </div>
            <div class="field-row">
              <div class="field"><label>职位</label><input type="text" id="e-pos" value="${UI.esc(e?.position || "")}"></div>
              <div class="field"><label>入职日期</label><input type="date" id="e-hire" value="${e?.hire_date || ""}"></div>
            </div>
            <div class="field-row">
              <div class="field"><label>手机号</label><input type="text" id="e-phone" value="${UI.esc(e?.phone || "")}"></div>
              <div class="field"><label>邮箱</label><input type="email" id="e-email" value="${UI.esc(e?.email || "")}"></div>
            </div>
            <div class="field"><label>状态</label><select id="e-status">
              <option value="active" ${e?.status !== "left" ? "selected" : ""}>在职</option>
              <option value="left" ${e?.status === "left" ? "selected" : ""}>离职</option></select></div>`;
          const foot = document.createElement("div");
          foot.innerHTML = `<button class="btn btn-ghost" data-act="no">取消</button><button class="btn btn-primary" data-act="yes">${isEdit ? "保存" : "创建"}</button>`;
          const m = UI.modal({ title: `${isEdit ? "编辑" : "新增"}员工`, body: form, footer: foot, size: "modal-lg" });
          foot.querySelector('[data-act="no"]').onclick = m.close;
          foot.querySelector('[data-act="yes"]').onclick = async () => {
            const payload = {
              emp_no: form.querySelector("#e-no").value.trim(),
              name: form.querySelector("#e-name").value.trim(),
              gender: form.querySelector("#e-gender").value || null,
              department_id: Number(form.querySelector("#e-dept").value) || null,
              position: form.querySelector("#e-pos").value.trim() || null,
              hire_date: form.querySelector("#e-hire").value || null,
              phone: form.querySelector("#e-phone").value.trim() || null,
              email: form.querySelector("#e-email").value.trim() || null,
              status: form.querySelector("#e-status").value,
            };
            if (!payload.emp_no || !payload.name) return UI.toast("工号和姓名必填", "error");
            try {
              if (isEdit) await API.put(`/api/system/employees/${e.id}`, payload);
              else await API.post("/api/system/employees", payload);
              UI.toast("保存成功"); m.close(); load();
            } catch (err) { UI.err(err); }
          };
        }

        async function del(e) {
          if (!await UI.confirm(`确定删除员工「${e.name}」？`)) return;
          try { await API.del(`/api/system/employees/${e.id}`); UI.toast("已删除"); load(); } catch (err) { UI.err(err); }
        }

        load();
      },
    },

    /* ---------- 审计日志 ---------- */
    auditLogs: {
      render(el) {
        const state = { page: 1, page_size: 15, keyword: "", action: "" };
        el.innerHTML = `
          <div class="card">
            <div class="toolbar">
              <input type="text" placeholder="搜索操作对象（单号/名称）" id="kw">
              <select id="action"><option value="">全部动作</option>
                ${Object.entries(ACTION_NAMES).map(([v, t]) => `<option value="${v}">${t}</option>`).join("")}</select>
              <button class="btn btn-ghost" id="search-btn">查询</button>
            </div>
            <div class="table-wrap"><table class="table">
              <thead><tr><th>时间</th><th>操作人</th><th>动作</th><th>模块</th><th>对象</th><th>详情</th><th>IP</th></tr></thead>
              <tbody id="tbody"></tbody></table></div>
            <div class="pager" id="pager"></div>
          </div>`;
        const doSearch = () => {
          state.keyword = el.querySelector("#kw").value.trim();
          state.action = el.querySelector("#action").value;
          state.page = 1; load();
        };
        el.querySelector("#search-btn").onclick = doSearch;
        el.querySelector("#kw").onkeydown = (e) => { if (e.key === "Enter") doSearch(); };
        el.querySelector("#action").onchange = doSearch;

        async function load() {
          try {
            const qs = new URLSearchParams(state);
            const data = await API.get(`/api/system/audit-logs?${qs}`);
            const tbody = el.querySelector("#tbody");
            tbody.innerHTML = data.items.length ? data.items.map((l) => `<tr>
              <td>${UI.esc(l.created_at)}</td><td>${UI.esc(l.username)}</td>
              <td><span class="badge badge-blue">${ACTION_NAMES[l.action] || UI.esc(l.action)}</span></td>
              <td>${MODULE_NAMES[l.module] || UI.esc(l.module)}</td>
              <td>${UI.esc(l.target || "-")}</td>
              <td class="log-detail" title="${UI.esc(l.detail || "")}">${UI.esc(l.detail || "-")}</td>
              <td>${UI.esc(l.ip || "-")}</td></tr>`).join("")
            : `<tr><td colspan="7"><div class="empty">暂无审计日志</div></td></tr>`;
            UI.pager(el.querySelector("#pager"), { ...data, onChange: (p) => { state.page = p; load(); } });
          } catch (e) { UI.err(e); }
        }
        load();
      },
    },
  };
})();
