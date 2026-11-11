// Tiện ích dùng chung cho các trang
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const conf = (c) => c ? `<span class="conf conf-${esc(c[0])}">${esc(c)}</span>` : "";
const STATUS = { published: "Đã công bố", needs_review: "Chờ duyệt", rejected: "Từ chối", collected: "Mới thu", imported: "Đã nhập", validation_failed: "Lỗi kiểm tra", validated: "Không có số liệu", success: "Thành công", failed: "Lỗi", running: "Đang chạy" };
const status = (s) => `<span class="status st-${esc(s)}">${esc(STATUS[s] || s)}</span>`;
const fmt = (v, d = 4) => v == null ? "–" : Number(v).toLocaleString("vi-VN", { maximumFractionDigits: d });
const when = (t) => t ? new Date(t.endsWith("Z") || t.includes("+") ? t : t + "Z").toLocaleString("vi-VN") : "";

async function api(path, opt = {}) {
  const r = await fetch(path, opt);
  let body = null;
  try { body = await r.json(); } catch (_) { /* không phải JSON */ }
  if (!r.ok) throw new Error((body && (typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail))) || `HTTP ${r.status}`);
  return body;
}

function toast(msg, ms = 3500) {
  let t = $("toast");
  if (!t) { t = document.createElement("div"); t.id = "toast"; t.className = "toast"; document.body.appendChild(t); }
  t.textContent = msg; t.style.display = "block";
  clearTimeout(t._h); t._h = setTimeout(() => (t.style.display = "none"), ms);
}

function reviewerName() {
  let n = "";
  try { n = localStorage.getItem("reviewer") || ""; } catch (_) {}
  return n;
}
function setReviewerName(n) { try { localStorage.setItem("reviewer", n); } catch (_) {} }

// Thanh điều hướng chung
function renderHeader(active) {
  const pages = [["/", "Tổng quan"], ["/registry", "Registry"], ["/upload", "Nộp số liệu"], ["/connectors", "Thu thập tự động"], ["/review", "Duyệt dữ liệu"], ["/cases", "Đánh giá case"], ["/insights", "Đề xuất tiêu chí"]];
  const h = document.createElement("header");
  h.innerHTML = `
    <div><h1>Innovation Hub</h1><div class="sub">Bộ chỉ tiêu KH,CN, ĐMST &amp; CĐS — PoC</div></div>
    <nav class="tabs">${pages.map(([href, label]) => `<a href="${href}" class="${href === active ? "active" : ""}">${label}${href === "/review" ? '<span class="badge" id="navBadge" hidden></span>' : ""}</a>`).join("")}</nav>
    <div class="spacer"></div>
    <a class="btn" href="/docs" target="_blank">API docs</a>`;
  document.body.prepend(h);
  refreshBadge();
}

function refreshBadge(summary) {
  const show = (s) => {
    const n = s.by_status.needs_review || 0, b = $("navBadge");
    if (b) { b.textContent = n; b.hidden = !n; }
  };
  if (summary) show(summary); else api("/api/review/summary").then(show).catch(() => {});
}
