// =====================================================================
// Tiện ích + khung trang dùng chung (design system "tech-art, ít chữ")
// =====================================================================
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (v, d = 4) => v == null ? "–" : Number(v).toLocaleString("vi-VN", { maximumFractionDigits: d });
const when = (t) => t ? new Date(t.endsWith("Z") || t.includes("+") ? t : t + "Z").toLocaleString("vi-VN") : "";
const CONF_TIP = { A: "A – nguồn chuẩn, chính thức", B: "B – chính thức, cần xử lý", C: "C – dữ liệu hành chính", D: "D – khảo sát/đánh giá" };
const conf = (c) => c ? `<span class="conf conf-${esc(c[0])}" title="Độ tin cậy ${esc(CONF_TIP[c[0]] || c)}">${esc(c)}</span>` : "";

// ---------- icon SVG (nét mảnh, kiểu Lucide) ----------
const ICONS = {
  home: '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/><path d="M10 21v-6h4v6"/>',
  list: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9h10M7 13h10M7 17h6"/>',
  upload: '<path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/>',
  review: '<rect x="3" y="3" width="18" height="18" rx="3"/><path d="m8 12 3 3 5-6"/>',
  zap: '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
  star: '<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>',
  spark: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
  chart: '<path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 5-6"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  bell: '<path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10 21a2 2 0 0 0 4 0"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6v.6M12 17h.01"/>',
  code: '<path d="m8 7-5 5 5 5M16 7l5 5-5 5"/>',
  download: '<path d="M12 4v12"/><path d="m7 11 5 5 5-5"/><path d="M4 20h16"/>',
  alert: '<path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17h.01"/>',
  ok: '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
  xc: '<circle cx="12" cy="12" r="9"/><path d="m9 9 6 6M15 9l-6 6"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  check: '<path d="m5 12 5 5 9-10"/>',
  x: '<path d="M6 6l12 12M18 6 6 18"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  file: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h4"/>',
  ext: '<path d="M14 4h6v6M20 4l-9 9"/><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
  refresh: '<path d="M20 11a8 8 0 0 0-14.9-3M4 4v4h4M4 13a8 8 0 0 0 14.9 3M20 20v-4h-4"/>',
  hex: '<path d="M12 2.5 20.5 7.3v9.4L12 21.5l-8.5-4.8V7.3z"/><path d="M12 8v8M8.5 10l7 4M15.5 10l-7 4"/>',
  play: '<path d="M7 4v16l13-8z"/>',
  printer: '<path d="M6 9V3h12v6"/><rect x="3" y="9" width="18" height="8" rx="2"/><path d="M6 14h12v7H6z"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5h.01"/>',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  bars: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  heat: '<path d="M3 3h18v18H3z"/><path d="M3 9h18M3 15h18M9 3v18M15 3v18"/>',
  map: '<path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2z"/><path d="M9 4v14M15 6v14"/>',
  table: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M3 15h18M9 10v10"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  login: '<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><path d="m10 17 5-5-5-5M15 12H3"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5M21 12H9"/>',
  lock: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
  trash: '<path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  inbox: '<path d="M3 13h5l2 3h4l2-3h5"/><path d="M5 5h14l2 8v6H3v-6z"/>',
};
const ic = (name, cls = "") => `<svg class="i ${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ""}</svg>`;

// ---------- trạng thái (luôn icon + chữ) ----------
const STATUS = { published: "Đã công bố", needs_review: "Chờ duyệt", rejected: "Từ chối", collected: "Mới thu", imported: "Đã nhận", validation_failed: "Có lỗi", validated: "Không có số liệu", success: "Thành công", failed: "Lỗi", running: "Đang chạy", verified: "Đã xác nhận", proposed: "Chờ chuyên gia", accepted: "Đã chấp nhận" };
const STATUS_IC = { published: "ok", success: "ok", imported: "ok", verified: "ok", accepted: "ok", needs_review: "clock", running: "clock", proposed: "clock", validated: "info", rejected: "xc", failed: "xc", validation_failed: "xc" };
const status = (s) => `<span class="status st-${esc(s)}">${ic(STATUS_IC[s] || "info")}${esc(STATUS[s] || s)}</span>`;

// ---------- trạng thái dữ liệu theo phân loại của Cục (khác trạng thái duyệt) ----------
const DQ = {
  official: ["Chính thức", "ok", "Số liệu chính thức đã được công bố"],
  official_caveat: ["Chính thức, có lưu ý", "ok2", "Số liệu chính thức; phạm vi hoặc phương pháp có lưu ý"],
  estimate: ["Ước tính", "est", "Số ước tính, có thể điều chỉnh khi có số chính thức"],
  method_adjustment: ["Điều chỉnh phương pháp", "est", "Chỉ tiêu tính theo phương pháp điều chỉnh hoặc chỉ tiêu thay thế"],
  updating: ["Đang cập nhật", "warn", "Số liệu đang được cập nhật"],
  incomplete: ["Chưa đầy đủ", "warn", "Số liệu chưa bao quát đủ phạm vi định nghĩa"],
  under_review: ["Đang rà soát", "warn", "Số liệu đang được rà soát, chưa xác nhận"],
  not_calculable: ["Chưa tính được", "none", "Chưa có phương pháp hoặc dữ liệu đầu vào để tính"],
  not_available: ["Chưa có số liệu", "none", "Chưa có số liệu cho kỳ báo cáo"],
  no_info: ["Chưa có thông tin", "none", "Chưa nhận được thông tin tại thời điểm tổng hợp"],
  reported_unvalidated: ["Tỉnh báo cáo, chưa kiểm chứng", "prov", "Số do tỉnh tự báo cáo, chưa chuẩn hoá; không dùng để xếp hạng"],
  simulated: ["Dữ liệu minh hoạ", "sim", "Số liệu giả lập phục vụ trình diễn, không phải số liệu thật"],
  reference: ["Số đối chiếu", "none", "Số từ cơ sở dữ liệu bên ngoài, dùng để đối chiếu; không phải số thống kê chính thức"],
};
const dataStatus = (s) => s && DQ[s] ? `<span class="dq dq-${DQ[s][1]}" title="${esc(DQ[s][2])}">${esc(DQ[s][0])}</span>` : "";
const simBadge = () => dataStatus("simulated");
// mức thay đổi %: ▲/▼ có màu; null → "–"
const pctTag = (v, title = "") => v == null ? '<span class="delta flat">–</span>'
  : `<span class="delta ${Math.abs(v) < 0.05 ? "flat" : v > 0 ? "up" : "down"}" title="${esc(title)}">${v > 0 ? "▲" : v < 0 ? "▼" : "■"} ${Math.abs(v).toLocaleString("vi-VN", { maximumFractionDigits: 1 })}%</span>`;
const RES_NAME = { M: "Tháng", Q: "Quý", Y: "Năm" };
// nút chọn dạng phân đoạn: segHtml(id, [[giá trị, nhãn]], chọn)
const segHtml = (id, opts, cur, label = "") => `<div class="seg" role="tablist" id="${id}" aria-label="${esc(label)}">${opts.map(([v, l, dis]) =>
  `<button type="button" data-v="${esc(v)}" class="${String(v) === String(cur) ? "on" : ""}" ${dis ? "disabled" : ""}>${esc(l)}</button>`).join("")}</div>`;
function onSeg(id, fn) {
  $(id).addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b || b.disabled) return;
    $(id).querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b)); fn(b.dataset.v); });
}

// ---------- nhãn nguồn thuần Việt ----------
const SOURCE_NAMES = { gii: "WIPO – GII", egdi: "UN – EGDI", hdi: "UNDP – HDI", ipvn: "Cục SHTT", openalex: "OpenAlex", worldbank: "World Bank", neac: "NEAC", api_dinh: "API thống kê – bộ 137" };
const SEED_NAMES = { S_RPT: "Báo cáo 2244 (15/09)", S_XLS: "Bảng kết quả của Cục (01/09)", S_SIM: "Dữ liệu minh hoạ", CUC: "Số liệu tổng hợp của Cục" };
const SOURCE_KIND = { seed: ["Số liệu của Cục", "var(--primary)"], agency: ["Đơn vị nộp", "var(--series-3)"], crawler: ["Tự động", "var(--series-1)"], doc: ["Tài liệu", "var(--series-2)"], external: ["Dữ liệu ngoài", "#7C3AED"], calc: ["Tự tính", "#98A2B3"] };
function originLabel(o) {
  const [kind, ...rest] = String(o || "").split(":"), r = rest.join(":");
  if (kind === "crawler") return SOURCE_NAMES[r] || r;
  if (kind === "agency") return r;
  if (kind === "doc") return `Tài liệu #${r}`;
  if (kind === "external") return "Dữ liệu ngoài";
  if (kind === "calc") return "Tự tính";
  if (kind === "seed") return SEED_NAMES[r] || r;
  return o;
}
const originKind = (o) => String(o || "").split(":")[0];
const originDot = (o) => `<span class="src"><span class="dotc" style="background:${(SOURCE_KIND[originKind(o)] || ["", "#98A2B3"])[1]}"></span>${esc(originLabel(o))}</span>`;

async function api(path, opt = {}) {
  const r = await fetch(path, opt);
  let body = null;
  try { body = await r.json(); } catch (_) { /* không phải JSON */ }
  if (!r.ok) throw new Error((body && (typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail))) || `HTTP ${r.status}`);
  return body;
}

// ---------- toast (có nút hành động, lỗi không tự tắt nhanh) ----------
function toast(msg, opt = {}) {
  if (typeof opt === "number") opt = { ms: opt };
  let t = $("toast");
  if (!t) { t = document.createElement("div"); t.id = "toast"; t.className = "toast"; t.setAttribute("role", "status"); t.setAttribute("aria-live", "polite"); document.body.appendChild(t); }
  const err = opt.type === "err";
  t.innerHTML = `${ic(err ? "xc" : "ok", err ? "ic-err" : "ic-ok")}<span>${esc(msg)}</span>${opt.action ? `<button class="btn sm ghost" style="color:var(--primary)">${esc(opt.action.label)}</button>` : ""}`;
  if (opt.action) t.querySelector("button").onclick = () => { t.classList.remove("on"); opt.action.fn(); };
  t.classList.add("on");
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("on"), opt.ms || (err ? 9000 : 5000));
}

// ---------- hộp thoại (thay prompt/confirm của trình duyệt) ----------
function dialog({ title, message = "", tone = "primary", icon = "info", chips = [], input = null, required = false, placeholder = "", okLabel = "Đồng ý", value = "" }) {
  return new Promise((resolve) => {
    const m = document.createElement("div");
    m.className = "modal"; m.setAttribute("role", "dialog"); m.setAttribute("aria-modal", "true");
    const toneBg = tone === "danger" ? "var(--err-soft);color:var(--err)" : tone === "ok" ? "var(--ok-soft);color:var(--ok)" : "var(--primary-soft);color:var(--primary)";
    m.innerHTML = `<span class="big-ic" style="background:${toneBg};width:44px;height:44px;border-radius:12px">${ic(icon)}</span>
      <h3>${esc(title)}</h3>${message ? `<div class="small muted">${esc(message)}</div>` : ""}
      ${chips.length ? `<div class="chips">${chips.map((c) => `<button type="button" class="chip">${esc(c)}</button>`).join("")}</div>` : ""}
      ${input === "textarea" ? `<textarea placeholder="${esc(placeholder)}">${esc(value)}</textarea>` : input === "text" ? `<input class="field" style="width:100%;margin-top:12px" placeholder="${esc(placeholder)}" value="${esc(value)}">` : ""}
      <div class="row"><button type="button" class="btn" data-x>Huỷ</button><button type="button" class="btn ${tone === "danger" ? "danger" : "primary"}" data-ok>${esc(okLabel)}</button></div>`;
    const scrim = document.createElement("div"); scrim.className = "scrim";
    document.body.append(scrim, m);
    const field = m.querySelector("textarea, input"), ok = m.querySelector("[data-ok]");
    const sync = () => { ok.disabled = required && field && !field.value.trim(); };
    if (field) field.addEventListener("input", sync);
    m.querySelectorAll(".chip").forEach((c) => c.onclick = () => {
      c.classList.toggle("on");
      if (field) { field.value = [...m.querySelectorAll(".chip.on")].map((x) => x.textContent).join("; "); sync(); }
    });
    const prev = document.activeElement;
    const close = (v) => { m.classList.remove("on"); scrim.classList.remove("on"); setTimeout(() => { m.remove(); scrim.remove(); }, 200); document.removeEventListener("keydown", onKey, true); if (prev && prev.focus) prev.focus(); resolve(v); };
    const onKey = (e) => { if (e.key === "Escape") { e.stopPropagation(); close(null); } if (e.key === "Enter" && !e.shiftKey && field?.tagName !== "TEXTAREA" && !ok.disabled) { e.preventDefault(); ok.click(); } };
    document.addEventListener("keydown", onKey, true);
    m.querySelector("[data-x]").onclick = () => close(null);
    scrim.onclick = () => close(null);
    ok.onclick = () => close(field ? field.value.trim() : true);
    sync();
    requestAnimationFrame(() => { m.classList.add("on"); scrim.classList.add("on"); (field || ok).focus(); });
  });
}

// ---------- người dùng hiện tại ----------
// Cookie hub_ui chỉ để giao diện hiện đúng menu ngay khi tải trang; máy chủ tự kiểm tra quyền ở mọi API.
const ROLE_RANK = { public: 0, analyst: 1, admin: 2 };
const ROLE_LABEL = { public: "Công chúng", analyst: "Chuyên viên phân tích", admin: "Quản trị dữ liệu" };
const ME = (() => {
  try {
    const m = document.cookie.match(/(?:^|;\s*)hub_ui=([^;]*)/);
    if (m) { const [role, ...n] = decodeURIComponent(m[1]).split("|"); if (ROLE_RANK[role]) return { role, name: n.join("|") }; }
  } catch (_) { /* cookie hỏng → coi như khách */ }
  return { role: "public", name: "" };
})();
const can = (role) => ROLE_RANK[ME.role] >= ROLE_RANK[role || "public"];
const loginUrl = (need) => `/login?next=${encodeURIComponent(location.pathname + location.search)}${need ? "&need=" + need : ""}`;
// người thao tác được lấy từ phiên đăng nhập (máy chủ ghi vào nhật ký); chưa đăng nhập → sang trang đăng nhập
async function ensureReviewer() {
  if (can("analyst")) return ME.name;
  location.href = loginUrl("analyst");
  return null;
}
const reviewerName = () => ME.name;
function renderAvatar() {
  const a = $("avatar"); if (!a) return;
  a.innerHTML = ME.role === "public" ? ic("user") : esc(ME.name.replace(/\(.*?\)/g, "").trim().split(/\s+/).slice(-2).map((w) => w[0]).join("").toUpperCase() || "?");
  a.title = ME.role === "public" ? "Đăng nhập" : `${ME.name} · ${ROLE_LABEL[ME.role]}`;
  a.classList.toggle("anon", ME.role === "public");
}
async function userMenu() {
  let m = $("umenu");
  if (m) { m.remove(); return; }
  m = document.createElement("div"); m.id = "umenu"; m.className = "umenu"; m.setAttribute("role", "menu");
  const head = ME.role === "public" ? `<div class="uh"><b>Công chúng</b><span>Chưa đăng nhập · chỉ xem số liệu đã công bố</span></div>`
    : `<div class="uh"><b>${esc(ME.name)}</b><span>${ROLE_LABEL[ME.role]}</span></div>`;
  m.innerHTML = head + `<div class="ub" id="umDemo"></div>` + (ME.role === "public"
    ? `<a class="ui" href="${loginUrl()}">${ic("login")}Đăng nhập</a>`
    : `<button class="ui" id="umOut">${ic("logout")}Đăng xuất</button>`);
  $("avatar").after(m);
  const close = (e) => { if (!m.contains(e.target) && e.target !== $("avatar") && !$("avatar").contains(e.target)) { m.remove(); document.removeEventListener("click", close); } };
  setTimeout(() => document.addEventListener("click", close));
  if ($("umOut")) $("umOut").onclick = async () => { await api("/api/auth/logout", { method: "POST" }).catch(() => {}); location.href = "/"; };
  try {
    const me = await api("/api/auth/me");
    if (me.demo_mode) {
      $("umDemo").innerHTML = `<div class="ul">Xem với vai trò (bản demo)</div>` + me.roles.map((r) =>
        `<button class="ui ${r.role === me.role ? "on" : ""}" data-role="${r.role}">${ic(r.role === me.role ? "check" : "user")}${esc(r.label)}</button>`).join("");
      $("umDemo").querySelectorAll("[data-role]").forEach((b) => b.onclick = async () => {
        await api("/api/auth/switch", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ role: b.dataset.role }) });
        location.reload();
      });
    }
  } catch (_) { /* không hiện phần demo */ }
}

// ---------- khung trang ----------
// [href, nhãn, biểu tượng, vai trò tối thiểu]; nhóm không còn mục nào thì ẩn
const NAV = [
  [null, [["/", "Tổng quan", "home"], ["/s2244", "Chỉ tiêu 2244", "list"], ["/s137", "Chỉ tiêu thống kê", "chart"]]],
  ["Phân tích", [["/analysis", "Phân tích", "bars"], ["/scorecard", "Đánh giá tổng hợp", "grid"], ["/readiness", "Sẵn sàng dữ liệu", "heat"], ["/provinces", "Địa phương", "map"], ["/compare", "So sánh chỉ tiêu", "refresh", "analyst"]]],
  ["Nội bộ", [["/registry", "Bộ chỉ tiêu", "file", "analyst"], ["/cases", "Đánh giá chương trình", "star", "analyst"], ["/insights", "Đề xuất tiêu chí", "spark", "analyst"], ["/report", "Báo cáo", "printer", "analyst"]]],
  ["Quản trị dữ liệu", [["/upload", "Nhập dữ liệu", "upload", "admin"], ["/review", "Hàng chờ duyệt", "review", "admin"], ["/connectors", "Nguồn dữ liệu", "zap", "admin"], ["/reconcile", "Đối soát", "check", "admin"], ["/admin", "Quản trị", "settings", "admin"], ["/audit", "Nhật ký", "clock", "admin"]]],
].map(([g, items]) => [g, items.filter((it) => can(it[3]))]).filter(([, items]) => items.length);
const PAGE_META = {
  "/registry": ["Bộ chỉ tiêu", "Danh mục chỉ tiêu và tiêu chí đánh giá", "Nội bộ"],
  "/upload": ["Nhập dữ liệu", "File tổng hợp của Cục và biểu mẫu theo chỉ tiêu", "Quản trị dữ liệu"],
  "/review": ["Hàng chờ duyệt", "Kiểm định số liệu trước khi công bố", "Quản trị dữ liệu"],
  "/connectors": ["Nguồn dữ liệu", "API hệ thống thống kê và nguồn quốc tế, thu thập định kỳ", "Quản trị dữ liệu"],
  "/admin": ["Quản trị", "Cờ hiển thị, trạng thái dữ liệu, ánh xạ 2244 ↔ 137 và nội dung trang chủ", "Quản trị dữ liệu"],
  "/audit": ["Nhật ký", "Lưu vết thao tác: người thực hiện, thời điểm, giá trị cũ → mới, lý do", "Quản trị dữ liệu"],
  "/s2244": ["Chỉ tiêu 2244", "46 chỉ tiêu theo QĐ 2244/QĐ-TTg, theo quý hoặc năm", null],
  "/s137": ["Chỉ tiêu thống kê", "Bộ 137 chỉ tiêu thống kê, theo tháng, quý hoặc năm", null],
  "/compare": ["So sánh chỉ tiêu", "Đặt 2–4 chỉ tiêu cạnh nhau, mỗi chỉ tiêu một trục", "Phân tích"],
  "/reconcile": ["Đối soát", "Chỉ tiêu trùng 2244 ↔ 137 và chênh lệch giữa các nguồn của Cục", "Quản trị dữ liệu"],
  "/cases": ["Đánh giá chương trình", "Đánh giá theo 50 tiêu chí", "Nội bộ"],
  "/insights": ["Đề xuất tiêu chí", "Đề xuất từ dữ liệu bổ sung ngoài bộ chỉ tiêu", "Nội bộ"],
  "/analysis": ["Phân tích", "21 biểu đồ dựng lại từ báo cáo 2244, theo khung Đầu vào – Đầu ra – Hiệu quả – Tác động", "Phân tích"],
  "/scorecard": ["Đánh giá tổng hợp", "Chẩn đoán, mức bằng chứng và hàm ý chính sách theo 4 chiều", "Phân tích"],
  "/readiness": ["Sẵn sàng dữ liệu", "Mức sẵn sàng của 46 chỉ tiêu theo 8 chiều chất lượng dữ liệu", "Phân tích"],
  "/provinces": ["Địa phương", "Số liệu do 34 tỉnh, thành phố báo cáo năm 2025", "Phân tích"],
};

function renderHeader(active, opts = {}) {
  document.body.insertAdjacentHTML("afterbegin", '<a class="skip" href="#main">Bỏ qua tới nội dung</a><div class="aurora" aria-hidden="true"><i></i><i></i><i></i></div>');
  const main = document.querySelector("main");
  main.id = main.id || "main";
  const shell = document.createElement("div");
  shell.className = "shell";
  shell.innerHTML = `
    <aside class="side" id="side" aria-label="Điều hướng chính">
      <a class="logo" href="/"><span class="mark">${ic("hex")}</span><span>Dữ liệu ĐMST<small>QĐ 2244 · Bộ KH&amp;CN</small></span></a>
      ${NAV.map(([group, items]) => `${group ? `<div class="group">${group}</div>` : ""}${items.map(([href, label, icon]) =>
        `<a class="nav ${href === active ? "active" : ""}" href="${href}" ${href === active ? 'aria-current="page"' : ""}>${ic(icon)}${label}${href === "/review" ? '<span class="badge" id="navBadge" hidden></span>' : ""}</a>`).join("")}`).join("")}
      <div class="fill"></div>
      <a class="nav" href="/docs" target="_blank" rel="noopener">${ic("code")}Dành cho kỹ thuật</a>
    </aside>
    <div class="app-main">
      <div class="topbar">
        <button class="icon-btn burger" id="burger" aria-label="Mở menu">${ic("menu")}</button>
        <div class="gsearch"><label>${ic("search")}<input id="gq" placeholder="Tìm chỉ tiêu…" autocomplete="off" aria-label="Tìm chỉ tiêu"><span class="kbd">Ctrl K</span></label><div class="results" id="gres" role="listbox"></div></div>
        <span class="grow"></span>
        ${can("admin") ? `<a class="icon-btn bell" href="/review" aria-label="Việc chờ duyệt" title="Việc chờ duyệt">${ic("bell")}<span class="dot" id="bellDot" hidden></span></a>` : ""}
        ${ME.role === "public" ? `<a class="btn sm hide-sm" href="${loginUrl()}">${ic("login")}Đăng nhập</a>` : `<span class="rolechip hide-sm">${ROLE_LABEL[ME.role]}</span>`}
        <span class="uwrap"><button class="avatar" id="avatar" type="button" aria-haspopup="menu"></button></span>
      </div>
    </div>`;
  main.replaceWith(shell);
  shell.querySelector(".app-main").appendChild(main);
  const scrim = document.createElement("div"); scrim.className = "scrim"; scrim.id = "navScrim"; document.body.appendChild(scrim);
  const side = $("side");
  $("burger").onclick = () => { side.classList.add("on"); scrim.classList.add("on"); };
  scrim.onclick = () => { side.classList.remove("on"); scrim.classList.remove("on"); };
  $("avatar").onclick = userMenu;
  renderAvatar();

  // tiêu đề trang chuẩn (tối đa 4 chữ + 1 câu); các nút có class "ph-actions" được đưa lên
  const meta = opts.header === false ? null : PAGE_META[active];
  if (meta) {
    const ph = document.createElement("div"); ph.className = "ph";
    ph.innerHTML = `<div>${meta[2] ? `<div class="crumb">${meta[2]} › ${meta[0]}</div>` : ""}<h1>${meta[0]}</h1><p>${meta[1]}</p></div><div class="acts"></div>`;
    main.prepend(ph);
    main.querySelectorAll(".ph-actions").forEach((el) => ph.querySelector(".acts").appendChild(el));
  }
  initSearch();
  refreshBadge();
}

function refreshBadge(summary) {
  const show = (s) => {
    const n = s.by_status.needs_review || 0;
    const b = $("navBadge"), d = $("bellDot");
    if (b) { b.textContent = n.toLocaleString("vi-VN"); b.hidden = !n; }
    if (d) { d.textContent = n > 99 ? "99+" : n; d.hidden = !n; }
  };
  if (summary) show(summary); else if (can("admin")) api("/api/review/summary").then(show).catch(() => {});
}

// ---------- tìm kiếm toàn cục (Ctrl/⌘ K) ----------
function initSearch() {
  const q = $("gq"), box = $("gres");
  let items = [], hl = -1, timer;
  const pages = NAV.flatMap(([, it]) => it);
  const fold = (s) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d");
  const render = () => {
    box.innerHTML = items.map((it, i) => `<a href="${it.href}" class="${i === hl ? "hl" : ""}" role="option">${it.html}</a>`).join("") || '<div class="small muted" style="padding:10px">Không tìm thấy</div>';
    box.classList.toggle("on", !!q.value.trim());
  };
  q.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      const term = q.value.trim(); hl = -1;
      if (!term) { items = []; render(); return; }
      const pg = pages.filter(([, label]) => fold(label).includes(fold(term))).map(([href, label, icon]) => ({ href, html: `${ic(icon)}${esc(label)}` }));
      let inds = [];
      try { inds = (await api("/api/indicators?q=" + encodeURIComponent(term))).slice(0, 7); } catch (_) {}
      items = [...pg, ...inds.map((i) => ({ href: `/indicator?code=${encodeURIComponent(i.code)}`, html: `<span class="code">${esc(i.code)}</span><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(i.name)}</span>` }))];
      render();
    }, 150);
  });
  q.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { hl = Math.min(items.length - 1, hl + 1); render(); e.preventDefault(); }
    else if (e.key === "ArrowUp") { hl = Math.max(0, hl - 1); render(); e.preventDefault(); }
    else if (e.key === "Enter" && items.length) { location.href = items[Math.max(0, hl)].href; }
    else if (e.key === "Escape") { q.value = ""; items = []; render(); q.blur(); }
  });
  q.addEventListener("blur", () => setTimeout(() => box.classList.remove("on"), 150));
  q.addEventListener("focus", () => { if (q.value.trim()) box.classList.add("on"); });
  document.addEventListener("keydown", (e) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); q.focus(); q.select(); } });
}

// ---------- trạng thái trống / đang tải ----------
const emptyState = (msg, icon = "inbox", action = "") => {
  const art = typeof ILLUS === "undefined" ? `<span class="big-ic">${ic(icon)}</span>`
    : icon === "ok" ? ILLUS.done({ w: 150 }) : icon === "xc" ? `<span class="big-ic">${ic(icon)}</span>` : ILLUS.empty({ w: 150 });
  return `<div class="empty">${art}<div style="margin-top:6px;font-weight:600;color:var(--text-2)">${esc(msg)}</div>${action ? `<div style="margin-top:12px">${action}</div>` : ""}</div>`;
};
const skeletonRows = (n = 5, cols = 5) => Array.from({ length: n }, () => `<tr>${Array.from({ length: cols }, () => '<td><div class="skel"></div></td>').join("")}</tr>`).join("");

// ---------- dùng chung cho trang chủ và trang Mức sẵn sàng ----------
function statusBarsHtml(groups) {
  return (groups || []).map((g) => `
    <section class="card sbar"><h3>${esc(g.classification)}</h3><div class="sub">${g.total} chỉ tiêu</div>
      <div class="stack" role="img" aria-label="${esc(g.items.map((x) => `${x.label}: ${x.count}`).join("; "))}">
        ${g.items.map((x) => `<span class="tn-${x.tone}" style="width:${x.count / g.total * 100}%" title="${esc(x.label)}: ${x.count} (${fmt(x.share_pct, 1)}%)"></span>`).join("")}</div>
      <div class="legend">${g.items.map((x) => `<span><i class="tn-${x.tone}"></i>${esc(x.label)}<b>${x.count}</b></span>`).join("")}</div>
    </section>`).join("") || '<div class="muted">Chưa có tóm tắt trạng thái.</div>';
}

// Tải CSV (UTF-8 có BOM để Excel đọc đúng tiếng Việt)
function downloadCsv(filename, head, rows) {
  const cell = (v) => v == null ? "" : /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v);
  const text = [head, ...rows].map((r) => r.map(cell).join(",")).join("\n");
  const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(new Blob(["\ufeff" + text], { type: "text/csv;charset=utf-8" })), download: filename });
  document.body.appendChild(a); a.click(); a.remove();
}

// Hộp thoại nhiều trường: fields = [{name, label, type: text|number|textarea|select, options: [[v, nhãn]], required, value, placeholder, hint}]
// → trả về {name: giá trị} hoặc null khi huỷ
function formDialog({ title, message = "", icon = "edit", okLabel = "Lưu", fields = [] }) {
  return new Promise((resolve) => {
    const m = document.createElement("div");
    m.className = "modal fdlg"; m.setAttribute("role", "dialog"); m.setAttribute("aria-modal", "true");
    m.innerHTML = `<span class="big-ic" style="background:var(--primary-soft);color:var(--primary);width:44px;height:44px;border-radius:12px">${ic(icon)}</span>
      <h3>${esc(title)}</h3>${message ? `<div class="small muted">${message}</div>` : ""}
      <form novalidate>${fields.map((f) => `<label class="ff"><span>${esc(f.label)}${f.required ? ' <b class="req">*</b>' : ""}</span>${
        f.type === "textarea" ? `<textarea name="${f.name}" placeholder="${esc(f.placeholder || "")}">${esc(f.value ?? "")}</textarea>`
        : f.type === "select" ? `<select class="field" name="${f.name}">${f.options.map(([v, l]) => `<option value="${esc(v)}" ${String(v) === String(f.value ?? "") ? "selected" : ""}>${esc(l)}</option>`).join("")}</select>`
        : `<input class="field" name="${f.name}" type="${f.type === "number" ? "text" : "text"}" ${f.type === "number" ? 'inputmode="decimal"' : ""} value="${esc(f.value ?? "")}" placeholder="${esc(f.placeholder || "")}">`
      }${f.hint ? `<small>${esc(f.hint)}</small>` : ""}</label>`).join("")}
      <p class="ferr" role="alert"></p>
      <div class="row"><button type="button" class="btn" data-x>Huỷ</button><button type="submit" class="btn primary" data-ok>${esc(okLabel)}</button></div></form>`;
    const scrim = document.createElement("div"); scrim.className = "scrim";
    document.body.append(scrim, m);
    const form = m.querySelector("form"), prev = document.activeElement;
    const close = (v) => { m.classList.remove("on"); scrim.classList.remove("on"); setTimeout(() => { m.remove(); scrim.remove(); }, 200); document.removeEventListener("keydown", onKey, true); if (prev && prev.focus) prev.focus(); resolve(v); };
    const onKey = (e) => { if (e.key === "Escape") { e.stopPropagation(); close(null); } };
    document.addEventListener("keydown", onKey, true);
    m.querySelector("[data-x]").onclick = () => close(null);
    scrim.onclick = () => close(null);
    form.onsubmit = (e) => {
      e.preventDefault();
      const out = {};
      for (const f of fields) {
        const el = form.elements[f.name]; let v = el.value.trim();
        if (f.required && !v) { m.querySelector(".ferr").textContent = `Cần nhập: ${f.label}`; el.focus(); return; }
        if (f.type === "number" && v) {
          const n = Number(v.replace(/\s/g, "").replace(/\.(?=\d{3}(\D|$))/g, "").replace(",", "."));
          if (!Number.isFinite(n)) { m.querySelector(".ferr").textContent = `${f.label} phải là số`; el.focus(); return; }
          v = n;
        }
        out[f.name] = v === "" ? null : v;
      }
      close(out);
    };
    requestAnimationFrame(() => { m.classList.add("on"); scrim.classList.add("on"); (form.querySelector("input, textarea, select") || m.querySelector("[data-ok]")).focus(); });
  });
}
