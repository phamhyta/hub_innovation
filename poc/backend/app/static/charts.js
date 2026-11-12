// Biểu đồ SVG tối giản, không phụ thuộc thư viện ngoài (máy chủ cơ quan có thể không ra Internet).
// Quy ước: tối đa 2 chuỗi/biểu đồ (màu --series-1, --series-2), một trục Y, đường 2px, điểm ≥ 8px,
// lưới mờ, có crosshair + tooltip khi rê chuột, có chú giải khi ≥ 2 chuỗi.

const SVGNS = "http://www.w3.org/2000/svg";
const SERIES_COLORS = ["var(--series-1)", "var(--series-2)"];

function el(tag, attrs = {}, parent) {
  const e = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}

function niceTicks(min, max, count = 4) {
  if (min === max) { const d = Math.abs(min) * 0.1 || 1; min -= d; max += d; }
  const span = max - min, step0 = span / count, mag = Math.pow(10, Math.floor(Math.log10(step0)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => span / s <= count) || 10 * mag;
  const lo = Math.floor(min / step) * step, hi = Math.ceil(max / step) * step, ticks = [];
  for (let v = lo; v <= hi + step / 2; v += step) ticks.push(+v.toFixed(10));
  return ticks;
}

const fmtNum = (v, d = 2) => v == null ? "–" : Number(v).toLocaleString("vi-VN", { maximumFractionDigits: Math.abs(v) >= 100 ? 0 : d });

/**
 * lineChart(container, {series: [{name, points: [{x, y}]}], unit, invert, target, height})
 * invert=true cho thứ hạng (số nhỏ = tốt, nằm trên cùng).
 */
function lineChart(container, opt) {
  container.innerHTML = "";
  container.classList.add("chart");
  // điểm y = null: kỳ thiếu số liệu → đường bị ngắt, không nối liền
  const series = (opt.series || []).slice(0, 2).filter((s) => s.points.some((p) => p.y != null));
  if (!series.length) { container.innerHTML = '<div class="muted small">Chưa có số liệu đã công bố.</div>'; return; }
  if (series.length > 1) {
    const lg = document.createElement("div"); lg.className = "legend";
    lg.innerHTML = series.map((s, i) => `<span><span class="sw" style="background:${SERIES_COLORS[i]}"></span>${esc(s.name)}</span>`).join("");
    container.appendChild(lg);
  }
  const W = Math.max(280, container.clientWidth || 600), H = opt.height || 220;
  const m = { l: 52, r: 16, t: 10, b: 26 };
  const xs = [...new Set(series.flatMap((s) => s.points.map((p) => p.x)))].sort();
  const ys = series.flatMap((s) => s.points.filter((p) => p.y != null).map((p) => p.y)).concat(opt.target != null ? [opt.target] : []);
  const ticks = niceTicks(Math.min(...ys), Math.max(...ys));
  const y0 = ticks[0], y1 = ticks[ticks.length - 1];
  const X = (x) => m.l + (xs.length === 1 ? (W - m.l - m.r) / 2 : xs.indexOf(x) * (W - m.l - m.r) / (xs.length - 1));
  const Y = (v) => { const t = (v - y0) / (y1 - y0 || 1); return opt.invert ? m.t + t * (H - m.t - m.b) : H - m.b - t * (H - m.t - m.b); };

  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img",
    "aria-label": `${series.map((s) => s.name).join(", ")} theo ${opt.periodLabel || "năm"}` });
  const grid = el("g", { class: "grid" }, svg), axis = el("g", { class: "axis" }, svg);
  ticks.forEach((t) => {
    el("line", { x1: m.l, x2: W - m.r, y1: Y(t), y2: Y(t) }, grid);
    el("text", { x: m.l - 8, y: Y(t) + 4, "text-anchor": "end" }, axis).textContent = fmtNum(t);
  });
  const every = Math.ceil(xs.length / Math.max(2, Math.floor((W - m.l - m.r) / 46)));
  xs.forEach((x, i) => {
    if (i % every === 0 || i === xs.length - 1)
      el("text", { x: X(x), y: H - 6, "text-anchor": "middle" }, axis).textContent = x;
  });
  if (opt.target != null) {
    el("line", { x1: m.l, x2: W - m.r, y1: Y(opt.target), y2: Y(opt.target), stroke: "var(--muted)", "stroke-width": 1.5, "stroke-dasharray": "5 4" }, svg);
    el("text", { x: W - m.r, y: Y(opt.target) - 5, "text-anchor": "end", fill: "var(--muted)", "font-size": 11 }, svg).textContent = `Mục tiêu ${fmtNum(opt.target)}`;
  }
  const cross = el("line", { y1: m.t, y2: H - m.b, stroke: "var(--muted)", "stroke-width": 1, visibility: "hidden" }, svg);
  series.forEach((s, i) => {
    const pts = [...s.points].sort((a, b) => a.x.localeCompare(b.x));
    let pen = false;
    const d = pts.map((p) => { if (p.y == null) { pen = false; return ""; } const c = `${pen ? "L" : "M"}${X(p.x)},${Y(p.y)}`; pen = true; return c; }).join("");
    el("path", { d, fill: "none",
      stroke: SERIES_COLORS[i], "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round",
      ...(s.dashed ? { "stroke-dasharray": "6 4" } : {}) }, svg);
    // chuỗi minh hoạ (giả lập): nét đứt, điểm rỗng
    pts.filter((p) => p.y != null).forEach((p) => el("circle", { cx: X(p.x), cy: Y(p.y), r: 4, fill: s.dashed ? "var(--panel)" : SERIES_COLORS[i],
      stroke: s.dashed ? SERIES_COLORS[i] : "var(--panel)", "stroke-width": 2 }, svg));
  });
  container.appendChild(svg);

  // tooltip + crosshair
  const tip = document.createElement("div"); tip.className = "tip"; container.appendChild(tip);
  const hit = el("rect", { x: m.l - 10, y: 0, width: W - m.l - m.r + 20, height: H, fill: "transparent" }, svg);
  const show = (evt) => {
    const r = svg.getBoundingClientRect(), px = (evt.clientX - r.left) * (W / r.width);
    const x = xs.reduce((a, b) => Math.abs(X(b) - px) < Math.abs(X(a) - px) ? b : a, xs[0]);
    cross.setAttribute("x1", X(x)); cross.setAttribute("x2", X(x)); cross.setAttribute("visibility", "visible");
    tip.innerHTML = `<b>${esc(x)}</b>` + series.map((s, i) => {
      const p = s.points.find((q) => q.x === x);
      return `<div><span class="sw" style="background:${SERIES_COLORS[i]}"></span>${esc(s.name)}: <b>${p && p.y != null ? fmtNum(p.y, 4) : "chưa có số liệu"}</b> ${esc(p && p.y != null && p.unit || (p && p.y != null ? opt.unit : "") || "")}</div>`;
    }).join("");
    tip.style.display = "block";
    const left = X(x) * (r.width / W);
    tip.style.left = Math.min(Math.max(0, left + 12), r.width - tip.offsetWidth) + "px";
    tip.style.top = (container.querySelector(".legend") ? 24 : 0) + "px";
  };
  hit.addEventListener("mousemove", show);
  hit.addEventListener("mouseleave", () => { tip.style.display = "none"; cross.setAttribute("visibility", "hidden"); });
}

/** sparkline(container, [{x, y}], {invert}) – đường nhỏ trong thẻ số liệu */
function sparkline(container, points, opt = {}) {
  container.innerHTML = "";
  if (points.length < 2) return;
  const W = 120, H = 32, ys = points.map((p) => p.y), lo = Math.min(...ys), hi = Math.max(...ys);
  const X = (i) => 2 + i * (W - 4) / (points.length - 1);
  const Y = (v) => { const t = hi === lo ? 0.5 : (v - lo) / (hi - lo); return opt.invert ? 3 + t * (H - 6) : H - 3 - t * (H - 6); };
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H, "aria-hidden": "true" });
  el("path", { d: points.map((p, i) => `${i ? "L" : "M"}${X(i)},${Y(p.y)}`).join(""), fill: "none", stroke: "var(--series-1)", "stroke-width": 2, "stroke-linejoin": "round", ...(opt.dashed ? { "stroke-dasharray": "4 3" } : {}) }, svg);
  el("circle", { cx: X(points.length - 1), cy: Y(ys[ys.length - 1]), r: 3, fill: "var(--series-1)" }, svg);
  el("title", {}, svg).textContent = points.map((p) => `${p.x}: ${fmtNum(p.y, 4)}`).join(" · ");
  container.appendChild(svg);
}

/* =====================================================================
   Biểu đồ cho trang Phân tích (GĐ 4). Màu theo thứ tự cố định --series-1…6 (đã kiểm định CVD,
   cặp liền kề); mọi biểu đồ đều có bảng số liệu thay thế nên màu tương phản thấp vẫn đọc được.
   ===================================================================== */
const CAT_COLORS = ["var(--series-1)", "var(--series-2)", "var(--series-3)", "var(--series-4)", "var(--series-5)", "var(--series-6)"];
const NEUTRAL = "var(--neutral-mark)";

/** Tooltip cho từng phần tử có data-tip (rê chuột hoặc focus bằng bàn phím). */
function bindTips(container) {
  container.classList.add("chart");
  let tip = container.querySelector(":scope > .tip");
  if (!tip) { tip = document.createElement("div"); tip.className = "tip"; container.appendChild(tip); }
  if (container._tips) return;
  container._tips = true;
  const place = (x, y) => {
    const w = container.clientWidth;
    tip.style.left = Math.max(0, Math.min(x + 12, w - tip.offsetWidth)) + "px";
    tip.style.top = (y + 14) + "px";
  };
  container.addEventListener("pointermove", (e) => {
    const t = e.target.closest && e.target.closest("[data-tip]");
    if (!t || !container.contains(t)) { tip.style.display = "none"; return; }
    tip.innerHTML = t.getAttribute("data-tip"); tip.style.display = "block";
    const r = container.getBoundingClientRect(); place(e.clientX - r.left, e.clientY - r.top);
  });
  container.addEventListener("pointerleave", () => tip.style.display = "none");
  container.addEventListener("focusin", (e) => {
    const t = e.target.closest("[data-tip]"); if (!t) return;
    tip.innerHTML = t.getAttribute("data-tip"); tip.style.display = "block";
    const r = container.getBoundingClientRect(), b = t.getBoundingClientRect(); place(b.left - r.left, b.bottom - r.top - 8);
  });
  container.addEventListener("focusout", () => tip.style.display = "none");
}
const tipHtml = (title, lines) => `<b>${esc(title)}</b>` + lines.map((l) => `<div>${l}</div>`).join("");
const tipAttr = (title, lines) => `data-tip="${esc(tipHtml(title, lines))}" tabindex="0"`;
const legendHtml = (items) => `<div class="legend">${items.map(([name, color, kind]) =>
  `<span><span class="sw ${kind || ""}" style="background:${color}"></span>${esc(name)}</span>`).join("")}</div>`;
// tách đơn vị trong ngoặc ở cuối nhãn: "Phủ sóng 5G (%)" → ["Phủ sóng 5G", "%"]; "(2024)" là năm, giữ nguyên
const UNIT_RE = /^(%|[^,]*(USD|đồng|TWh|MtCO2e|triệu|tỷ|lần)[^,]*)$/;
function splitUnit(label) {
  const m = String(label || "").match(/^(.*?)\s*\(([^()]*)\)\s*$/);
  if (!m) return [String(label || ""), ""];
  const parts = m[2].split(/,\s*/);
  if (!UNIT_RE.test(parts[0])) return [String(label), ""];
  return [parts.length > 1 ? `${m[1]} (${parts.slice(1).join(", ")})` : m[1], parts[0]];
}
const withUnit = (v, u) => v == null ? "–" : `${fmtNum(v, 3)}${u === "%" ? "%" : u ? " " + u : ""}`;

/** Thanh ngang sắp xếp giảm dần, nhãn giá trị ở đầu thanh. rows: [{label, value}] */
function hbarChart(container, opt) {
  const rows = (opt.rows || []).filter((r) => r.value != null || opt.keepEmpty);
  const list = opt.sort === false ? rows : [...rows].sort((a, b) => (b.value ?? -Infinity) - (a.value ?? -Infinity));
  const max = opt.max || Math.max(...list.map((r) => r.value || 0), 0) || 1;
  container.innerHTML = `<div class="hb">${list.map((r) => {
    const w = r.value == null ? 0 : Math.max(0.4, r.value / max * 100);
    return `<div class="hb-row" ${tipAttr(r.label, [`<b>${withUnit(r.value, opt.unit)}</b>${r.share != null ? ` · ${fmtNum(r.share, 1)}%` : ""}`])}>
      <span class="hb-l">${esc(r.label)}</span>
      <span class="hb-t"><i style="width:${w}%;background:${r.color || CAT_COLORS[0]}"></i></span>
      <span class="hb-v">${r.value == null ? '<span class="muted">–</span>' : fmtNum(r.value, 3)}</span></div>`;
  }).join("")}</div>`;
  bindTips(container);
}

/** Dot plot: mỗi hàng một hạng mục, mỗi chuỗi một chấm trên cùng một trục. */
function dotPlot(container, opt) {
  const series = opt.series.slice(0, 3), rows = opt.rows;
  const vals = series.flatMap((s) => s.values).filter((v) => v != null);
  const ticks = niceTicks(Math.min(0, ...vals), Math.max(...vals));
  const lo = ticks[0], hi = ticks[ticks.length - 1], P = (v) => (v - lo) / (hi - lo || 1) * 100;
  const labelAll = series.length === 1 || !opt.highlight;
  let html = series.length > 1 ? legendHtml(series.map((s, i) => [s.name, CAT_COLORS[i], "dot"])) : "";
  html += `<div class="dp">` + rows.map((r, ri) => {
    const hl = opt.highlight && String(r).startsWith(opt.highlight);
    const pts = series.map((s, i) => ({ v: s.values[ri], i, name: s.name })).filter((p) => p.v != null);
    const span = pts.length > 1 ? `<span class="dp-span" style="left:${P(Math.min(...pts.map((p) => p.v)))}%;width:${P(Math.max(...pts.map((p) => p.v))) - P(Math.min(...pts.map((p) => p.v)))}%"></span>` : "";
    return `<div class="dp-row ${hl ? "hl" : ""}"><span class="dp-l">${esc(r)}</span><span class="dp-t">${ticks.map((t) => `<i class="g" style="left:${P(t)}%"></i>`).join("")}${span}
      ${pts.map((p) => `<span class="dp-d" style="left:${P(p.v)}%;background:${CAT_COLORS[p.i]}" ${tipAttr(r, [`${series.length > 1 ? esc(p.name) + ": " : ""}<b>${withUnit(p.v, opt.unit)}</b>`])}></span>
        ${(labelAll ? p.i === 0 || series.length === 1 : hl) ? `<span class="dp-n ${p.i ? "below" : ""}" style="left:${P(p.v)}%">${fmtNum(p.v, 3)}</span>` : ""}`).join("")}</span></div>`;
  }).join("") + `<div class="dp-row axis"><span class="dp-l"></span><span class="dp-t">${ticks.map((t) => `<b style="left:${P(t)}%">${fmtNum(t)}</b>`).join("")}</span></div></div>`;
  container.innerHTML = html;
  bindTips(container);
}

function roundedBar(x, y, w, h, up) {
  // bo 4px ở đầu dữ liệu (xa đường gốc), góc phẳng ở đường gốc
  const r = Math.min(4, w / 2, h);
  if (h <= 0) return "";
  return up ? `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`
    : `M${x},${y}V${y + h - r}Q${x},${y + h} ${x + r},${y + h}H${x + w - r}Q${x + w},${y + h} ${x + w},${y + h - r}V${y}Z`;
}

/** Cột: một chuỗi, hoặc xếp chồng (có giá trị âm) + điểm tổng. */
function columnChart(container, opt) {
  container.innerHTML = "";
  const cats = opt.cats, series = opt.series, stacked = !!opt.stacked;
  const W = Math.max(280, container.clientWidth || 600), H = opt.height || 230, m = { l: 44, r: 12, t: 18, b: 28 };
  let lo = 0, hi = 0;
  cats.forEach((_, ci) => {
    if (stacked) {
      let p = 0, n = 0; series.forEach((s) => { const v = s.values[ci] || 0; if (v > 0) p += v; else n += v; });
      hi = Math.max(hi, p); lo = Math.min(lo, n);
    } else series.forEach((s) => { const v = s.values[ci]; if (v != null) { hi = Math.max(hi, v); lo = Math.min(lo, v); } });
    if (opt.total) { const t = opt.total.values[ci]; if (t != null) { hi = Math.max(hi, t); lo = Math.min(lo, t); } }
  });
  const ticks = niceTicks(lo, hi), y0 = ticks[0], y1 = ticks[ticks.length - 1];
  const Y = (v) => H - m.b - (v - y0) / (y1 - y0 || 1) * (H - m.t - m.b);
  const band = (W - m.l - m.r) / cats.length, bw = Math.min(56, band * (stacked ? 0.5 : 0.46));
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img", "aria-label": opt.label || "Biểu đồ cột" });
  const grid = el("g", { class: "grid" }, svg), axis = el("g", { class: "axis" }, svg);
  ticks.forEach((t) => {
    el("line", { x1: m.l, x2: W - m.r, y1: Y(t), y2: Y(t) }, grid);
    el("text", { x: m.l - 8, y: Y(t) + 4, "text-anchor": "end" }, axis).textContent = fmtNum(t);
  });
  cats.forEach((c, ci) => {
    const cx = m.l + band * ci + band / 2;
    el("text", { x: cx, y: H - 8, "text-anchor": "middle" }, axis).textContent = c;
    let pos = 0, neg = 0;
    series.forEach((s, si) => {
      const v = s.values[ci]; if (v == null) return;
      let a, b;
      if (stacked) { if (v >= 0) { a = pos; b = pos + v; pos = b; } else { a = neg; b = neg + v; neg = b; } } else { a = 0; b = v; }
      const top = Math.min(Y(a), Y(b)), h = Math.abs(Y(a) - Y(b));
      const isEnd = !stacked || (v >= 0 ? !series.slice(si + 1).some((t) => (t.values[ci] || 0) > 0) : !series.slice(si + 1).some((t) => (t.values[ci] || 0) < 0));
      // khe 2px giữa các đoạn xếp chồng
      const g = stacked && h > 3 ? 1 : 0;
      const d = isEnd ? roundedBar(cx - bw / 2, top + (v >= 0 ? 0 : g), bw, h - g, v >= 0) : `M${cx - bw / 2},${top + g}h${bw}v${Math.max(0, h - 2 * g)}h${-bw}Z`;
      const p = el("path", { d, fill: CAT_COLORS[stacked ? si : 0], tabindex: 0 }, svg);
      p.setAttribute("data-tip", tipHtml(c, [`${series.length > 1 ? esc(s.name) + ": " : ""}<b>${withUnit(v, opt.unit)}</b>`]));
      if (!stacked && cats.length <= 6)
        el("text", { x: cx, y: v >= 0 ? top - 6 : top + h + 14, "text-anchor": "middle", class: "vlab" }, svg).textContent = fmtNum(v, 3);
    });
    if (opt.total && opt.total.values[ci] != null) {
      const t = opt.total.values[ci], ty = Y(t);
      el("line", { x1: cx - bw / 2 - 5, x2: cx + bw / 2 + 5, y1: ty, y2: ty, stroke: "var(--text)", "stroke-width": 2 }, svg);
      const dot = el("circle", { cx, cy: ty, r: 4, fill: "var(--text)", stroke: "var(--surface)", "stroke-width": 2, tabindex: 0 }, svg);
      dot.setAttribute("data-tip", tipHtml(c, [`${esc(opt.total.name)}: <b>${withUnit(t, opt.unit)}</b>`]));
      el("text", { x: cx + bw / 2 + 8, y: ty + 4, class: "vlab" }, svg).textContent = fmtNum(t, 3);
    }
  });
  el("line", { x1: m.l, x2: W - m.r, y1: Y(0), y2: Y(0), stroke: "var(--border-strong)", "stroke-width": 1 }, svg);
  if (series.length > 1 || opt.total)
    container.insertAdjacentHTML("beforeend", legendHtml([...series.map((s, i) => [s.name, CAT_COLORS[i]]), ...(opt.total ? [[opt.total.name, "var(--text)", "dot"]] : [])]));
  container.appendChild(svg);
  bindTips(container);
}

/** Thanh phân đoạn 100% (phần trong tổng). parts: [{label, value, neutral}] */
function segBar(container, opt) {
  const parts = opt.parts.filter((p) => p.value != null && p.value > 0), total = parts.reduce((a, p) => a + p.value, 0) || 1;
  let ci = 0;
  const col = parts.map((p) => p.neutral ? NEUTRAL : CAT_COLORS[ci++]);
  container.innerHTML = `<div class="sgb" role="img" aria-label="${esc(parts.map((p) => `${p.label}: ${fmtNum(p.value / total * 100, 1)}%`).join("; "))}">${parts.map((p, i) => {
    const pct = p.value / total * 100;
    return `<span style="width:${pct}%;background:${col[i]}" class="${p.neutral ? "neu" : ""}" ${tipAttr(p.label, [`<b>${withUnit(p.value, opt.unit)}</b> · ${fmtNum(pct, 1)}%`])}>${pct >= 12 ? `<em>${fmtNum(pct, 1)}%</em>` : ""}</span>`;
  }).join("")}</div>
  <div class="sgb-lg">${parts.map((p, i) => `<span><span class="sw dot" style="background:${col[i]}"></span>${esc(p.label)} <b>${withUnit(p.value, opt.unit)}</b> <span class="muted">${fmtNum(p.value / total * 100, 1)}%</span></span>`).join("")}</div>`;
  bindTips(container);
}

/** Slope chart: hai mốc thời gian, mỗi chuỗi một đường. series: [{name, a, b}] */
function slopeChart(container, opt) {
  container.innerHTML = "";
  const series = opt.series.slice(0, 6), W = Math.max(300, container.clientWidth || 600), H = opt.height || 240;
  const lw = Math.min(64, W * 0.16), rw = Math.min(230, W * 0.46), m = { t: 26, b: 14 };
  const x1 = lw, x2 = W - rw;
  const vals = series.flatMap((s) => [s.a, s.b]), lo = Math.min(...vals), hi = Math.max(...vals), pad = (hi - lo) * 0.08 || 1;
  const Y = (v) => m.t + (1 - (v - lo + pad) / (hi - lo + 2 * pad)) * (H - m.t - m.b);
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img", "aria-label": `${opt.from} – ${opt.to}` });
  const axis = el("g", { class: "axis" }, svg);
  [[x1, opt.from], [x2, opt.to]].forEach(([x, t]) => {
    el("line", { x1: x, x2: x, y1: m.t - 6, y2: H - m.b, stroke: "var(--grid)" }, svg);
    el("text", { x, y: 12, "text-anchor": "middle" }, axis).textContent = t;
  });
  // tránh chồng nhãn: dàn đều tối thiểu 15px
  const spread = (ys) => { const o = ys.map((y, i) => ({ y, i })).sort((a, b) => a.y - b.y); for (let k = 1; k < o.length; k++) o[k].y = Math.max(o[k].y, o[k - 1].y + 15); return o.sort((a, b) => a.i - b.i).map((x) => x.y); };
  const ly = spread(series.map((s) => Y(s.a))), ry = spread(series.map((s) => Y(s.b)));
  series.forEach((s, i) => {
    const c = CAT_COLORS[i];
    const g = el("g", { tabindex: 0 }, svg);
    g.setAttribute("data-tip", tipHtml(s.name, [`${esc(opt.from)}: <b>${withUnit(s.a, opt.unit)}</b>`, `${esc(opt.to)}: <b>${withUnit(s.b, opt.unit)}</b>`, `Chênh lệch: <b>${s.b - s.a > 0 ? "+" : ""}${fmtNum(s.b - s.a, 2)}</b> điểm`]));
    el("line", { x1, x2, y1: Y(s.a), y2: Y(s.b), stroke: c, "stroke-width": 2, "stroke-linecap": "round" }, g);
    el("line", { x1, x2, y1: Y(s.a), y2: Y(s.b), stroke: "transparent", "stroke-width": 14 }, g);
    [[x1, s.a], [x2, s.b]].forEach(([x, v]) => el("circle", { cx: x, cy: Y(v), r: 4.5, fill: c, stroke: "var(--surface)", "stroke-width": 2 }, g));
    el("text", { x: x1 - 10, y: ly[i] + 4, "text-anchor": "end", class: "vlab" }, svg).textContent = fmtNum(s.a, 2);
    const t = el("text", { x: x2 + 10, y: ry[i] + 4, class: "vlab" }, svg);
    t.textContent = `${fmtNum(s.b, 2)}  `;
    el("tspan", { class: "slab" }, t).textContent = s.name;
  });
  container.appendChild(svg);
  bindTips(container);
}

/** Bubble: x, y theo trục, diện tích bong bóng theo r; nhận diện bằng nhãn trực tiếp (một màu). */
function bubbleChart(container, opt) {
  container.innerHTML = "";
  const pts = opt.points.filter((p) => p.x != null && p.y != null);
  const W = Math.max(300, container.clientWidth || 600), H = opt.height || 270, m = { l: 48, r: 18, t: 30, b: 44 };
  const tx = niceTicks(Math.min(...pts.map((p) => p.x)) * 0.85, Math.max(...pts.map((p) => p.x)) * 1.08);
  const ty = niceTicks(Math.min(...pts.map((p) => p.y)) * 0.96, Math.max(...pts.map((p) => p.y)) * 1.03);
  const X = (v) => m.l + (v - tx[0]) / (tx[tx.length - 1] - tx[0]) * (W - m.l - m.r);
  const Y = (v) => H - m.b - (v - ty[0]) / (ty[ty.length - 1] - ty[0]) * (H - m.t - m.b);
  const rmax = Math.max(...pts.map((p) => p.r || 0)) || 1, R = (v) => 6 + Math.sqrt((v || 0) / rmax) * 16;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img", "aria-label": `${opt.xLabel} và ${opt.yLabel}` });
  const grid = el("g", { class: "grid" }, svg), axis = el("g", { class: "axis" }, svg);
  ty.forEach((t) => { el("line", { x1: m.l, x2: W - m.r, y1: Y(t), y2: Y(t) }, grid); el("text", { x: m.l - 8, y: Y(t) + 4, "text-anchor": "end" }, axis).textContent = fmtNum(t); });
  tx.forEach((t) => el("text", { x: X(t), y: H - m.b + 16, "text-anchor": "middle" }, axis).textContent = fmtNum(t));
  el("text", { x: (m.l + W - m.r) / 2, y: H - 6, "text-anchor": "middle", class: "atitle" }, svg).textContent = opt.xLabel;
  el("text", { x: 4, y: 11, class: "atitle" }, svg).textContent = "↑ " + opt.yLabel;
  // nhãn trực tiếp: tránh chồng nhau (dời xuống/lên từng 15px)
  const placed = [];
  const spot = (x, y, w, right) => {
    for (const dy of [0, 15, -15, 30, -30, 45]) {
      const box = { x0: right ? x : x - w, x1: right ? x + w : x, y0: y + dy - 11, y1: y + dy + 4 };
      if (!placed.some((b) => box.x0 < b.x1 && box.x1 > b.x0 && box.y0 < b.y1 && box.y1 > b.y0)) { placed.push(box); return y + dy; }
    }
    return y;
  };
  [...pts].sort((a, b) => (b.r || 0) - (a.r || 0)).forEach((p) => {
    const g = el("g", { tabindex: 0 }, svg);
    g.setAttribute("data-tip", tipHtml(p.name, [`${esc(opt.xLabel)}: <b>${fmtNum(p.x, 2)}</b>`, `${esc(opt.yLabel)}: <b>${fmtNum(p.y, 2)}</b>`, `${esc(opt.rLabel)}: <b>${fmtNum(p.r, 2)}</b>`]));
    el("circle", { cx: X(p.x), cy: Y(p.y), r: R(p.r), fill: CAT_COLORS[0], "fill-opacity": 0.22, stroke: CAT_COLORS[0], "stroke-width": 2 }, g);
    el("circle", { cx: X(p.x), cy: Y(p.y), r: 2.5, fill: CAT_COLORS[0] }, g);
  });
  pts.forEach((p) => {
    const right = X(p.x) < W * 0.62, x = X(p.x) + (right ? 1 : -1) * (R(p.r) + 6);
    const y = spot(x, Y(p.y) + 4, String(p.name).length * 6.6, right);
    el("text", { x, y, "text-anchor": right ? "start" : "end", class: "vlab", "pointer-events": "none" }, svg).textContent = p.name;
  });
  container.appendChild(svg);
  container.insertAdjacentHTML("beforeend", `<div class="small muted">Diện tích bong bóng: ${esc(opt.rLabel)}</div>`);
  bindTips(container);
}

const noYear = (s) => String(s).replace(/\s*\(\d{4}\)\s*$/, "").trim();
/** Chuỗi các bước (tri thức → giá trị, chính phủ số). steps: [{label, items: [{label, value}]}] */
function chainFlow(container, opt) {
  container.innerHTML = `<ol class="flow">${opt.steps.map((s, i) => {
    const [num, name] = String(s.label).match(/^\d+\.\s*/) ? [String(s.label).match(/^(\d+)\./)[1], String(s.label).replace(/^\d+\.\s*/, "")] : [i + 1, s.label];
    const empty = s.items.every((x) => x.value == null);
    return `<li class="${empty ? "empty" : ""}"><div class="fh"><span class="n">${num}</span>${esc(name)}</div>${s.items.map((x) => {
      const [lab, u] = splitUnit(String(x.label).replace(/^\d+\.\s*/, ""));
      return x.value == null ? `<div class="fv na">${ic("clock")}<span>Chưa đo<small>${esc(lab)}</small></span></div>`
        : `<div class="fv" ${tipAttr(lab, [`<b>${withUnit(x.value, u)}</b>`])}><b>${fmtNum(x.value, 3)}${u ? `<small>${esc(u === "%" ? "%" : " " + u)}</small>` : ""}</b>${noYear(lab) === noYear(name) ? "" : `<span>${esc(lab)}</span>`}</div>`;
    }).join("")}</li>`;
  }).join("")}</ol>`;
  bindTips(container);
}

/** Thẻ số (một con số là đủ, không cần biểu đồ). tiles: [{label, value, unit, sub}] */
function statTiles(container, tiles, opt = {}) {
  container.innerHTML = `${opt.heading ? `<div class="mt-h">${esc(opt.heading)}</div>` : ""}<div class="mtiles">${tiles.map((t) =>
    `<div class="mt"><div class="v">${t.value == null ? "–" : fmtNum(t.value, 3)}${t.unit ? `<small>${esc(t.unit === "%" ? "%" : " " + t.unit)}</small>` : ""}</div><div class="l">${esc(t.label)}</div>${t.sub ? `<div class="s">${esc(t.sub)}</div>` : ""}</div>`).join("")}</div>`;
}

/** Thẻ xếp hạng: điểm, hạng/tổng số, vị trí trên thang (hạng 1 ở bên trái). */
function rankTiles(container, items) {
  container.innerHTML = `<div class="rk">${items.map((x) => {
    const pos = x.rank != null && x.total ? (x.rank - 1) / Math.max(1, x.total - 1) * 100 : null;
    return `<div class="rk-i"><div class="rk-h"><b>${esc(x.name)}</b>${x.score != null ? `<span>Điểm ${fmtNum(x.score, 4)}</span>` : ""}</div>
      <div class="rk-v">${x.rank != null ? `Hạng <b>${fmtNum(x.rank, 0)}</b><small>/${fmtNum(x.total, 0)}</small>` : "–"}</div>
      ${pos != null ? `<div class="rk-t" ${tipAttr(x.name, [`Hạng <b>${x.rank}/${x.total}</b>`, `Nằm trong nhóm ${fmtNum(x.rank / x.total * 100, 0)}% đứng đầu`])}><i style="left:${pos}%"></i></div><div class="rk-s"><span>1</span><span>${fmtNum(x.total, 0)}</span></div>` : ""}</div>`;
  }).join("")}</div>`;
  bindTips(container);
}
