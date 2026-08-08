/* ============================================================
 * 仪表盘：统计卡片 + 销售趋势 + TOP商品 + 库存预警 + 最近订单
 * ============================================================ */
(function () {
  window.Pages = window.Pages || {};

  const ICONS = {
    sales: "💰", orders: "📦", approve: "🕐", warn: "⚠️",
    receivable: "💳", payable: "🧾",
  };

  Pages.dashboard = {
    async render(el) {
      el.innerHTML = `
        <div class="stat-grid" id="stat-grid">
          ${[["sales", "今日销售额", "-", "var(--primary-light)", "var(--primary)"],
             ["orders", "今日订单数", "-", "var(--success-light)", "var(--success)"],
             ["approve", "待审核单据", "-", "var(--warning-light)", "var(--warning)"],
             ["warn", "库存预警", "-", "var(--danger-light)", "var(--danger)"],
             ["receivable", "应收余额", "-", "var(--cyan, #e0f7fa)", "var(--info)"],
             ["payable", "应付余额", "-", "#f3e8ff", "#7c3aed"]]
            .map(([k, label, v, bg, color]) => `
              <div class="stat-card">
                <div class="stat-ico" style="background:${bg}">${ICONS[k]}</div>
                <div><div class="stat-value" id="stat-${k}" style="color:${color}">${v}</div>
                <div class="stat-label">${label}</div></div>
              </div>`).join("")}
        </div>
        <div class="dash-grid">
          <div>
            <div class="card">
              <div class="card-title">近 7 天销售趋势（金额 ¥）</div>
              <div class="chart-box"><canvas id="trend-chart"></canvas></div>
            </div>
            <div class="card">
              <div class="card-title">最近销售订单</div>
              <div id="recent-orders"></div>
            </div>
          </div>
          <div>
            <div class="card">
              <div class="card-title">销量 TOP 5 商品</div>
              <div class="chart-box"><canvas id="top-chart"></canvas></div>
            </div>
            <div class="card">
              <div class="card-title">库存预警</div>
              <div id="low-stocks"></div>
            </div>
          </div>
        </div>`;

      // 统计卡片
      const s = await API.get("/api/dashboard/summary");
      const fmt = (v) => "¥" + UI.money(v);
      document.getElementById("stat-sales").textContent = fmt(s.today_sales);
      document.getElementById("stat-orders").textContent = s.today_orders;
      document.getElementById("stat-approve").textContent = s.pending_approve;
      document.getElementById("stat-warn").textContent = s.low_stocks;
      document.getElementById("stat-receivable").textContent = fmt(s.receivable_balance);
      document.getElementById("stat-payable").textContent = fmt(s.payable_balance);

      // 趋势图
      const trend = await API.get("/api/dashboard/sales-trend?days=7");
      Charts.line(document.getElementById("trend-chart"), {
        labels: trend.labels,
        series: [{ name: "销售金额", color: "#2f6fed", values: trend.amounts }],
      });

      // TOP 商品
      const top = await API.get("/api/dashboard/top-products?limit=5");
      Charts.bar(document.getElementById("top-chart"), {
        labels: top.map((t) => t.name),
        values: top.map((t) => t.qty),
      });

      // 库存预警
      const lows = await API.get("/api/dashboard/low-stocks?limit=8");
      document.getElementById("low-stocks").innerHTML = lows.length
        ? `<table class="table"><tbody>
             ${lows.map((l) => `<tr><td>${UI.esc(l.name)}</td><td class="num" style="color:var(--danger)">${UI.qty(l.qty)}</td><td class="num">/ ${UI.qty(l.safety_stock)}</td></tr>`).join("")}
           </tbody></table>`
        : `<div class="empty">库存充足，暂无预警 🎉</div>`;

      // 最近订单
      const recent = await API.get("/api/dashboard/recent-orders?limit=8");
      document.getElementById("recent-orders").innerHTML = recent.length
        ? `<table class="table"><thead><tr><th>单号</th><th>客户</th><th class="num">金额</th><th>状态</th></tr></thead><tbody>
             ${recent.map((o) => `<tr>
               <td>${UI.esc(o.order_no)}</td>
               <td>${UI.esc(o.customer_name || "-")}</td>
               <td class="num">${UI.money(o.total_amount)}</td>
               <td>${UI.badge(o.status)}</td></tr>`).join("")}
           </tbody></table>`
        : `<div class="empty">暂无销售订单，去「销售订单」页创建一单吧</div>`;
    },
  };
})();