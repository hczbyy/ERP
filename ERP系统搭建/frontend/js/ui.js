/* ============================================================
 * UI 组件：toast / 确认框 / 模态框 / 分页 / 状态徽标 / 格式化
 * ============================================================ */
(function () {
  const ui = {};

  /* ---------- Toast ---------- */
  ui.toast = function (msg, type = "success") {
    const root = document.getElementById("toast-root");
    const el = document.createElement("div");
    el.className = `toast toast-${type}`;
    el.textContent = msg;
    root.appendChild(el);
    setTimeout(() => {
      el.style.transition = "opacity .3s";
      el.style.opacity = "0";
      setTimeout(() => el.remove(), 300);
    }, 2600);
  };

  ui.err = (e) => ui.toast(e.message || String(e), "error");

  /* ---------- 模态框 ---------- */
  ui.modal = function ({ title, body, footer, size = "", onMount }) {
    const root = document.getElementById("modal-root");
    const mask = document.createElement("div");
    mask.className = "modal-mask";
    mask.innerHTML = `
      <div class="modal ${size}">
        <div class="modal-head">
          <span class="modal-title"></span>
          <button class="modal-close">&times;</button>
        </div>
        <div class="modal-body"></div>
        <div class="modal-foot"></div>
      </div>`;
    mask.querySelector(".modal-title").textContent = title;
    const bodyEl = mask.querySelector(".modal-body");
    const footEl = mask.querySelector(".modal-foot");
    if (typeof body === "string") bodyEl.innerHTML = body;
    else if (body instanceof HTMLElement) bodyEl.appendChild(body);
    if (footer) footEl.appendChild(footer);
    else footEl.remove();
    const close = () => mask.remove();
    mask.querySelector(".modal-close").onclick = close;
    mask.addEventListener("click", (e) => { if (e.target === mask) close(); });
    root.appendChild(mask);
    if (onMount) onMount(bodyEl, close);
    return { el: mask, bodyEl, close };
  };

  /* ---------- 确认框 ---------- */
  ui.confirm = function (msg, title = "操作确认") {
    return new Promise((resolve) => {
      const foot = document.createElement("div");
      foot.innerHTML = `
        <button class="btn btn-ghost" data-act="no">取消</button>
        <button class="btn btn-primary" data-act="yes">确定</button>`;
      const m = ui.modal({ title, body: `<p style="font-size:14px">${ui.esc(msg)}</p>`, footer: foot, size: "modal-sm" });
      foot.querySelector('[data-act="no"]').onclick = () => { m.close(); resolve(false); };
      foot.querySelector('[data-act="yes"]').onclick = () => { m.close(); resolve(true); };
    });
  };

  /* ---------- 分页 ---------- */
  ui.pager = function (container, { page, page_size, total, onChange }) {
    const pages = Math.max(1, Math.ceil(total / page_size));
    const maxShow = 7;
    let start = Math.max(1, page - 3);
    let end = Math.min(pages, start + maxShow - 1);
    start = Math.max(1, end - maxShow + 1);

    let html = `<span>共 ${total} 条</span>`;
    html += `<button ${page <= 1 ? "disabled" : ""} data-p="${page - 1}">‹</button>`;
    if (start > 1) html += `<button data-p="1">1</button>${start > 2 ? "<span>…</span>" : ""}`;
    for (let i = start; i <= end; i++) {
      html += `<button class="${i === page ? "active" : ""}" data-p="${i}">${i}</button>`;
    }
    if (end < pages) html += `${end < pages - 1 ? "<span>…</span>" : ""}<button data-p="${pages}">${pages}</button>`;
    html += `<button ${page >= pages ? "disabled" : ""} data-p="${page + 1}">›</button>`;

    container.innerHTML = html;
    container.querySelectorAll("button[data-p]").forEach((b) => {
      b.onclick = () => { if (!b.disabled) onChange(parseInt(b.dataset.p, 10)); };
    });
  };

  /* ---------- 状态徽标 ---------- */
  const ORDER_STATUS = {
    draft: ["badge-gray", "草稿"],
    approved: ["badge-blue", "已审核"],
    partially_received: ["badge-orange", "部分收货"],
    partially_shipped: ["badge-orange", "部分发货"],
    completed: ["badge-green", "已完成"],
    cancelled: ["badge-red", "已取消"],
  };
  const FIN_STATUS = {
    open: ["badge-gray", "未核销"],
    partial: ["badge-orange", "部分核销"],
    settled: ["badge-green", "已核销"],
  };
  const SIMPLE_STATUS = {
    active: ["badge-green", "启用"],
    disabled: ["badge-gray", "停用"],
    left: ["badge-gray", "离职"],
    draft: ["badge-gray", "草稿"],
    done: ["badge-green", "已完成"],
  };

  ui.badge = function (status) {
    const map = ORDER_STATUS[status] || FIN_STATUS[status] || SIMPLE_STATUS[status];
    if (!map) return ui.esc(status);
    return `<span class="badge ${map[0]}">${map[1]}</span>`;
  };

  /* ---------- 格式化 ---------- */
  ui.money = (n) => (Number(n) || 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  ui.qty = (n) => {
    const v = Number(n) || 0;
    return Number.isInteger(v) ? String(v) : v.toFixed(2);
  };
  ui.esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  ui.datetime = (s) => (s ? String(s).replace("T", " ").slice(0, 19) : "-");
  ui.date = (s) => (s ? String(s).slice(0, 10) : "-");
  ui.payMethod = (m) => ({ cash: "现金", bank: "银行转账", transfer: "线上支付" }[m] || m);

  window.UI = ui;
})();