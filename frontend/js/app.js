/* ============================================================
 * 应用入口：菜单 / 路由 / 权限 / 启动流程
 * ============================================================ */
(function () {
  /* 菜单定义（按权限码过滤显示） */
  const MENU = [
    { group: "工作台", items: [
      { key: "dashboard", title: "仪表盘", icon: "📊", hash: "#/dashboard", perm: "dashboard:view" },
    ]},
    { group: "基础数据", items: [
      { key: "products", title: "商品管理", icon: "📦", hash: "#/products", perm: "master:product:read" },
      { key: "customers", title: "客户管理", icon: "🤝", hash: "#/customers", perm: "master:customer:read" },
      { key: "suppliers", title: "供应商管理", icon: "🏭", hash: "#/suppliers", perm: "master:supplier:read" },
      { key: "warehouses", title: "仓库管理", icon: "🏬", hash: "#/warehouses", perm: "master:warehouse:read" },
    ]},
    { group: "采购管理", items: [
      { key: "purchase-orders", title: "采购订单", icon: "📥", hash: "#/purchase-orders", perm: "purchase:order:read" },
      { key: "stock-ins", title: "收货入库", icon: "📋", hash: "#/stock-ins", perm: "purchase:order:read" },
    ]},
    { group: "销售管理", items: [
      { key: "sales-orders", title: "销售订单", icon: "📤", hash: "#/sales-orders", perm: "sales:order:read" },
      { key: "stock-outs", title: "发货出库", icon: "🚚", hash: "#/stock-outs", perm: "sales:order:read" },
    ]},
    { group: "库存管理", items: [
      { key: "stocks", title: "库存查询", icon: "🗃️", hash: "#/stocks", perm: "inventory:stock:read" },
      { key: "stock-logs", title: "库存流水", icon: "📜", hash: "#/stock-logs", perm: "inventory:stock:read" },
      { key: "checks", title: "盘点管理", icon: "🔍", hash: "#/checks", perm: "inventory:manage" },
      { key: "transfers", title: "库存调拨", icon: "🔁", hash: "#/transfers", perm: "inventory:manage" },
    ]},
    { group: "财务管理", items: [
      { key: "receivables", title: "应收账款", icon: "💳", hash: "#/receivables", perm: "finance:read" },
      { key: "payables", title: "应付账款", icon: "🧾", hash: "#/payables", perm: "finance:read" },
      { key: "receipts", title: "收款单", icon: "💰", hash: "#/receipts", perm: "finance:read" },
      { key: "payments", title: "付款单", icon: "💸", hash: "#/payments", perm: "finance:read" },
    ]},
    { group: "系统管理", items: [
      { key: "users", title: "用户管理", icon: "👤", hash: "#/users", perm: "system:user:manage" },
      { key: "roles", title: "角色权限", icon: "🛡️", hash: "#/roles", perm: "system:role:manage" },
      { key: "departments", title: "部门管理", icon: "🏢", hash: "#/departments", perm: "system:org:manage" },
      { key: "employees", title: "员工管理", icon: "👥", hash: "#/employees", perm: "system:org:manage" },
      { key: "audit-logs", title: "审计日志", icon: "📝", hash: "#/audit-logs", perm: "system:audit:read" },
    ]},
  ];

  /* 路由表 */
  const ROUTES = {
    "/dashboard": { title: "仪表盘", page: () => Pages.dashboard },
    "/products": { title: "商品管理", page: () => Pages.master.product },
    "/customers": { title: "客户管理", page: () => Pages.master.customer },
    "/suppliers": { title: "供应商管理", page: () => Pages.master.supplier },
    "/warehouses": { title: "仓库管理", page: () => Pages.master.warehouse },
    "/purchase-orders": { title: "采购订单", page: () => Pages.purchase.orders },
    "/stock-ins": { title: "收货入库", page: () => Pages.purchase.stockIns },
    "/sales-orders": { title: "销售订单", page: () => Pages.sales.orders },
    "/stock-outs": { title: "发货出库", page: () => Pages.sales.stockOuts },
    "/stocks": { title: "库存查询", page: () => Pages.inventory.stocks },
    "/stock-logs": { title: "库存流水", page: () => Pages.inventory.logs },
    "/checks": { title: "盘点管理", page: () => Pages.inventory.checks },
    "/transfers": { title: "库存调拨", page: () => Pages.inventory.transfers },
    "/receivables": { title: "应收账款", page: () => Pages.finance.receivables },
    "/payables": { title: "应付账款", page: () => Pages.finance.payables },
    "/receipts": { title: "收款单", page: () => Pages.finance.receipts },
    "/payments": { title: "付款单", page: () => Pages.finance.payments },
    "/users": { title: "用户管理", page: () => Pages.system.users },
    "/roles": { title: "角色权限", page: () => Pages.system.roles },
    "/departments": { title: "部门管理", page: () => Pages.system.departments },
    "/employees": { title: "员工管理", page: () => Pages.system.employees },
    "/audit-logs": { title: "审计日志", page: () => Pages.system.auditLogs },
  };

  const ERP = {
    state: { user: null, perms: [] },

    hasPerm(code) {
      if (!this.state.user) return false;
      return this.state.perms.includes("*") || this.state.perms.includes(code);
    },

    /* 启动：有 token 则进主界面，否则登录页 */
    async bootstrap() {
      if (!API.hasToken()) return this.showLogin();
      try {
        const data = await API.get("/api/auth/me");
        this.state.user = data.user;
        this.state.perms = data.permissions;
        this.showApp();
        this.renderMenu();
        this.route();
      } catch {
        this.showLogin();
      }
    },

    showLogin() {
      document.getElementById("login-view").classList.remove("hidden");
      document.getElementById("app-view").classList.add("hidden");
    },

    showApp() {
      document.getElementById("login-view").classList.add("hidden");
      document.getElementById("app-view").classList.remove("hidden");
      const u = this.state.user;
      document.getElementById("topbar-user").textContent =
        `${u.display_name}（${u.username}）${u.is_superuser ? " · 超级管理员" : ""}`;
    },

    renderMenu() {
      const nav = document.getElementById("menu");
      nav.innerHTML = MENU.map((g) => {
        const items = g.items.filter((it) => this.hasPerm(it.perm));
        if (!items.length) return "";
        return `<div class="menu-group-title">${g.group}</div>` +
          items.map((it) => `<div class="menu-item" data-hash="${it.hash}"><span class="ico">${it.icon}</span><span class="txt">${it.title}</span></div>`).join("");
      }).join("");
      nav.querySelectorAll(".menu-item").forEach((el) => {
        el.onclick = () => { location.hash = el.dataset.hash; };
      });
    },

    /* hash 路由 */
    route() {
      const hash = location.hash || "#/dashboard";
      const path = hash.replace(/^#/, "");
      const route = ROUTES[path];
      if (!route || !this.hasPerm(route.perm)) {
        document.getElementById("content").innerHTML = `<div class="card"><div class="empty">页面不存在或无权访问</div></div>`;
        document.getElementById("page-title").textContent = "404";
        return;
      }
      if (route.perm && !this.hasPerm(route.perm)) return;
      document.getElementById("page-title").textContent = route.title;
      document.querySelectorAll(".menu-item").forEach((el) => {
        el.classList.toggle("active", el.dataset.hash === `#${path}`);
      });
      const content = document.getElementById("content");
      content.innerHTML = "";
      route.page().render(content);
    },

    logout() {
      API.clearToken();
      this.state.user = null;
      this.state.perms = [];
      location.hash = "#/login";
      this.showLogin();
    },

    changePassword() {
      const form = document.createElement("div");
      form.innerHTML = `
        <div class="field"><label>原密码</label><input type="password" id="p-old"></div>
        <div class="field"><label>新密码（至少6位）</label><input type="password" id="p-new"></div>
        <div class="field"><label>确认新密码</label><input type="password" id="p-new2"></div>`;
      const foot = document.createElement("div");
      foot.innerHTML = `<button class="btn btn-ghost" data-act="no">取消</button><button class="btn btn-primary" data-act="yes">确认修改</button>`;
      const m = UI.modal({ title: "修改密码", body: form, footer: foot, size: "modal-sm" });
      foot.querySelector('[data-act="no"]').onclick = m.close;
      foot.querySelector('[data-act="yes"]').onclick = async () => {
        const oldP = form.querySelector("#p-old").value;
        const newP = form.querySelector("#p-new").value;
        const newP2 = form.querySelector("#p-new2").value;
        if (!oldP) return UI.toast("请输入原密码", "error");
        if (newP.length < 6) return UI.toast("新密码至少 6 位", "error");
        if (newP !== newP2) return UI.toast("两次输入的新密码不一致", "error");
        try {
          await API.post("/api/auth/change-password", { old_password: oldP, new_password: newP });
          UI.toast("密码修改成功，下次登录请使用新密码");
          m.close();
        } catch (e) { UI.err(e); }
      };
    },
  };

  window.ERP = ERP;

  /* 启动 */
  Pages.login.init();
  window.addEventListener("hashchange", () => {
    if (API.hasToken() && ERP.state.user) ERP.route();
  });
  ERP.bootstrap();
})();