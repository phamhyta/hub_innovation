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
  const series = (opt.series || []).slice(0, 2).filter((s) => s.points.length);
  if (!series.length) { container.innerHTML = '<div class="muted small">Chưa có số liệu đã công bố.</div>'; return; }
  if (series.length > 1) {
    const lg = document.createElement("div"); lg.className = "legend";
    lg.innerHTML = series.map((s, i) => `<span><span class="sw" style="background:${SERIES_COLORS[i]}"></span>${esc(s.name)}</span>`).join("");
    container.appendChild(lg);
  }
  const W = Math.max(280, container.clientWidth || 600), H = opt.height || 220;
  const m = { l: 52, r: 16, t: 10, b: 26 };
  const xs = [...new Set(series.flatMap((s) => s.points.map((p) => p.x)))].sort();
  const ys = series.flatMap((s) => s.points.map((p) => p.y)).concat(opt.target != null ? [opt.target] : []);
  const ticks = niceTicks(Math.min(...ys), Math.max(...ys));
  const y0 = ticks[0], y1 = ticks[ticks.length - 1];
  const X = (x) => m.l + (xs.length === 1 ? (W - m.l - m.r) / 2 : xs.indexOf(x) * (W - m.l - m.r) / (xs.length - 1));
  const Y = (v) => { const t = (v - y0) / (y1 - y0 || 1); return opt.invert ? m.t + t * (H - m.t - m.b) : H - m.b - t * (H - m.t - m.b); };

  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img",
    "aria-label": `${series.map((s) => s.name).join(", ")} theo năm` });
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
    el("path", { d: pts.map((p, j) => `${j ? "L" : "M"}${X(p.x)},${Y(p.y)}`).join(""), fill: "none",
      stroke: SERIES_COLORS[i], "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
    pts.forEach((p) => el("circle", { cx: X(p.x), cy: Y(p.y), r: 4, fill: SERIES_COLORS[i], stroke: "var(--panel)", "stroke-width": 2 }, svg));
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
      return `<div><span class="sw" style="background:${SERIES_COLORS[i]}"></span>${esc(s.name)}: <b>${p ? fmtNum(p.y, 4) : "–"}</b> ${esc(p && p.unit || opt.unit || "")}</div>`;
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
  el("path", { d: points.map((p, i) => `${i ? "L" : "M"}${X(i)},${Y(p.y)}`).join(""), fill: "none", stroke: "var(--series-1)", "stroke-width": 2, "stroke-linejoin": "round" }, svg);
  el("circle", { cx: X(points.length - 1), cy: Y(ys[ys.length - 1]), r: 3, fill: "var(--series-1)" }, svg);
  el("title", {}, svg).textContent = points.map((p) => `${p.x}: ${fmtNum(p.y, 4)}`).join(" · ");
  container.appendChild(svg);
}
