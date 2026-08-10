/* ============================================================
 * 轻量图表（Canvas 手绘，零依赖）
 * ============================================================ */
(function () {
  const charts = {};

  function setupCanvas(canvas) {
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);
    return { ctx, w: rect.width, h: rect.height };
  }

  /* 折线图：{labels:[], series:[{name,color,values:[]}]} */
  charts.line = function (canvas, { labels, series }) {
    const { ctx, w, h } = setupCanvas(canvas);
    const pad = { l: 46, r: 14, t: 14, b: 28 };
    const iw = w - pad.l - pad.r, ih = h - pad.t - pad.b;
    ctx.clearRect(0, 0, w, h);

    const all = series.flatMap((s) => s.values);
    const maxV = Math.max(1, ...all);
    const niceMax = Math.ceil(maxV * 1.15);
    const n = labels.length;

    // 网格 + Y 轴
    ctx.strokeStyle = "#eef0f3";
    ctx.fillStyle = "#94a3b8";
    ctx.font = "11px sans-serif";
    ctx.textAlign = "right";
    for (let i = 0; i <= 4; i++) {
      const y = pad.t + ih - (ih * i) / 4;
      const v = Math.round((niceMax * i) / 4);
      ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(w - pad.r, y); ctx.stroke();
      ctx.fillText(v, pad.l - 6, y + 4);
    }
    // X 轴标签
    ctx.textAlign = "center";
    labels.forEach((lb, i) => {
      if (n > 12 && i % 2 !== 0 && i !== n - 1) return;
      const x = pad.l + (n === 1 ? iw / 2 : (iw * i) / (n - 1));
      ctx.fillText(lb.slice(5), x, h - 8);
    });

    // 系列线
    series.forEach((s, si) => {
      ctx.strokeStyle = s.color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      labels.forEach((_, i) => {
        const x = pad.l + (n === 1 ? iw / 2 : (iw * i) / (n - 1));
        const y = pad.t + ih - (ih * (s.values[i] || 0)) / niceMax;
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      });
      ctx.stroke();
      // 数据点 + 数值
      labels.forEach((_, i) => {
        const x = pad.l + (n === 1 ? iw / 2 : (iw * i) / (n - 1));
        const y = pad.t + ih - (ih * (s.values[i] || 0)) / niceMax;
        ctx.fillStyle = "#fff";
        ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = s.color; ctx.lineWidth = 1.5;
        ctx.stroke();
        ctx.fillStyle = s.color;
        ctx.font = "10px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(String(Math.round(s.values[i] || 0)), x, y - 8);
      });
      // 图例
      ctx.font = "12px sans-serif";
      ctx.textAlign = "left";
      ctx.fillStyle = "#64748b";
      ctx.fillText("●", pad.l + si * 110, 10);
      ctx.fillStyle = s.color;
      ctx.fillText(s.name, pad.l + si * 110 + 12, 13);
    });
  };

  /* 横向条形图：{labels:[], values:[]} */
  charts.bar = function (canvas, { labels, values }) {
    const { ctx, w, h } = setupCanvas(canvas);
    const pad = { l: 12, r: 60, t: 12, b: 12 };
    const iw = w - pad.l - pad.r, ih = h - pad.t - pad.b;
    ctx.clearRect(0, 0, w, h);

    const maxV = Math.max(1, ...values);
    const rowH = Math.min(30, ih / Math.max(1, labels.length));
    const barH = Math.max(10, rowH - 10);

    labels.forEach((lb, i) => {
      const y = pad.t + i * rowH;
      const bw = (iw * (values[i] || 0)) / maxV;
      // 渐变条
      const grad = ctx.createLinearGradient(pad.l, 0, pad.l + bw, 0);
      grad.addColorStop(0, "#2f6fed");
      grad.addColorStop(1, "#22d3ee");
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.roundRect ? ctx.roundRect(pad.l, y, Math.max(2, bw), barH, 4) : ctx.rect(pad.l, y, Math.max(2, bw), barH);
      ctx.fill();
      // 名称（截断）
      ctx.fillStyle = "#334155";
      ctx.font = "12px sans-serif";
      ctx.textAlign = "left";
      const name = lb.length > 10 ? lb.slice(0, 10) + "…" : lb;
      ctx.fillText(name, pad.l + 8, y + barH / 2 + 4);
      // 数值
      ctx.fillStyle = "#64748b";
      ctx.textAlign = "right";
      ctx.fillText(String(Math.round(values[i] || 0)), pad.l + iw + 6, y + barH / 2 + 4);
    });
  };

  window.Charts = charts;
})();