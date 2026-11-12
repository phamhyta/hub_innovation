// =====================================================================
// Minh hoạ SVG tự vẽ (phẳng + gradient thương hiệu), dùng chung cho web và video.
// Không dùng ảnh/logo bên ngoài. Mỗi lần gọi tạo id gradient riêng để không đụng nhau.
// =====================================================================
const ILLUS = (() => {
  let n = 0;
  const uid = () => `il${++n}`;
  const STYLE = `<style>
    .il-spin{transform-box:fill-box;transform-origin:center;animation:il-spin 28s linear infinite}
    .il-spin-r{transform-box:fill-box;transform-origin:center;animation:il-spin 40s linear infinite reverse}
    .il-float{animation:il-float 4s ease-in-out infinite}
    .il-float2{animation:il-float 5s ease-in-out -2s infinite}
    .il-pulse{transform-box:fill-box;transform-origin:center;animation:il-pulse 2.6s ease-in-out infinite}
    .il-dash{stroke-dasharray:4 6;animation:il-dash 1.2s linear infinite}
    .il-pop{transform-box:fill-box;transform-origin:center;animation:il-pop 2.8s ease-in-out infinite}
    @keyframes il-spin{to{transform:rotate(360deg)}}
    @keyframes il-float{50%{transform:translateY(-6px)}}
    @keyframes il-pulse{50%{transform:scale(1.06)}}
    @keyframes il-dash{to{stroke-dashoffset:-20}}
    @keyframes il-pop{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(1.25);opacity:.6}}
    @media (prefers-reduced-motion:reduce){.il-spin,.il-spin-r,.il-float,.il-float2,.il-pulse,.il-dash,.il-pop{animation:none}}
  </style>`;
  const grad = (id) => `<linearGradient id="${id}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2563EB"/><stop offset=".55" stop-color="#7C3AED"/><stop offset="1" stop-color="#06B6D4"/></linearGradient>`;
  const shadow = (id) => `<filter id="${id}" x="-40%" y="-40%" width="180%" height="180%"><feDropShadow dx="0" dy="6" stdDeviation="7" flood-color="#101828" flood-opacity=".14"/></filter>`;
  const mini = {
    doc: '<path d="M-6-8h8l5 5v11h-13z" fill="#fff" stroke="#16A34A" stroke-width="1.6" stroke-linejoin="round"/><path d="M-3 0h7M-3 3.5h7" stroke="#16A34A" stroke-width="1.6" stroke-linecap="round"/>',
    chart: '<path d="M-8 7h16M-6 4V0M-1 4v-7M4 4v-4" stroke="#2563EB" stroke-width="2.2" stroke-linecap="round"/>',
    globe: '<circle r="8" fill="none" stroke="#0891B2" stroke-width="1.8"/><path d="M-8 0h16M0-8c4 4 4 12 0 16c-4-4-4-12 0-16" fill="none" stroke="#0891B2" stroke-width="1.6"/>',
    star: '<path d="m0-8 2.4 5 5.4.7-4 3.8 1 5.4L0 4.3-4.8 6.9l1-5.4-4-3.8 5.4-.7z" fill="#DB2777"/>',
    check: '<circle r="8" fill="#7C3AED"/><path d="m-3.5 0 2.5 2.5 4.5-5" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
  };

  // Hub dữ liệu ở trung tâm, các nguồn quay quanh
  function hub({ w = 420 } = {}) {
    const g = uid(), s = uid(), r = uid();
    const nodes = [["doc", 60, 150], ["globe", 120, 48], ["chart", 300, 48], ["star", 360, 150], ["check", 210, 282]];
    return `<svg viewBox="0 0 420 320" width="${w}" style="max-width:100%;height:auto" role="img" aria-label="Minh hoạ: dữ liệu từ nhiều nguồn hội tụ về một trung tâm">${STYLE}
      <defs>${grad(g)}${shadow(s)}<radialGradient id="${r}"><stop offset="0" stop-color="#C4B5FD" stop-opacity=".55"/><stop offset="1" stop-color="#C4B5FD" stop-opacity="0"/></radialGradient></defs>
      <circle cx="210" cy="160" r="150" fill="url(#${r})"/>
      <ellipse cx="210" cy="160" rx="160" ry="112" fill="none" stroke="#C7D2FE" stroke-width="1.5" class="il-dash"/>
      <ellipse cx="210" cy="160" rx="104" ry="72" fill="none" stroke="#DDD6FE" stroke-width="1.5"/>
      ${nodes.map(([, x, y]) => `<path d="M210 160 L${x} ${y}" stroke="url(#${g})" stroke-width="2" class="il-dash" opacity=".7"/>`).join("")}
      <g class="il-pulse" filter="url(#${s})"><path d="M210 112 L251 136 V184 L210 208 L169 184 V136Z" fill="url(#${g})"/>
        <path d="M210 140 V180 M193 150 L227 170 M227 150 L193 170" stroke="#fff" stroke-width="5" stroke-linecap="round"/></g>
      ${nodes.map(([k, x, y], i) => `<g class="${i % 2 ? "il-float" : "il-float2"}"><g transform="translate(${x} ${y})" filter="url(#${s})"><circle r="26" fill="#fff"/><g transform="scale(1.35)">${mini[k]}</g></g></g>`).join("")}
      <circle cx="80" cy="250" r="5" fill="#06B6D4" class="il-pop"/><circle cx="350" cy="250" r="4" fill="#7C3AED" class="il-pop"/><circle cx="400" cy="90" r="3" fill="#2563EB" class="il-pop"/>
    </svg>`;
  }

  // Nhân vật theo vai trò
  const ROLES = {
    agency: { bg: "#DBEAFE", shirt: "#2563EB", skin: "#F2C9A9", hair: "#2B2118", hairPath: "M38 46c0-16 10-24 22-24s22 8 22 24c-4-6-10-9-22-9s-18 3-22 9z", prop: "doc" },
    reviewer: { bg: "#EDE9FE", shirt: "#7C3AED", skin: "#E3AE8C", hair: "#3B2A20", hairPath: "M36 50c-2-18 9-28 24-28s26 10 24 28c-2-9-8-15-24-15s-22 6-24 15zM36 50c0 10 2 20 4 26h-6c-2-8-2-18 2-26z", prop: "check" },
    leader: { bg: "#CFFAFE", shirt: "#0F766E", skin: "#F5D0B5", hair: "#6B7280", hairPath: "M39 44c2-14 11-21 21-21s19 7 21 21c-5-5-11-7-21-7s-16 2-21 7z", prop: "chart" },
    expert: { bg: "#FCE7F3", shirt: "#DB2777", skin: "#D79B78", hair: "#1F1A17", hairPath: "M37 48c0-17 10-26 23-26 14 0 23 9 23 26-3-3-6-6-10-7l-2-5-3 5c-6 0-12 1-17 2l-2-4-2 5c-4 1-7 2-10 4z", prop: "star" },
  };
  function person(role = "agency", { w = 96 } = {}) {
    const c = ROLES[role], clip = uid(), s = uid();
    return `<svg viewBox="0 0 120 120" width="${w}" height="${w}" role="img" aria-label="Minh hoạ người dùng">${STYLE}
      <defs><clipPath id="${clip}"><circle cx="60" cy="60" r="56"/></clipPath>${shadow(s)}</defs>
      <circle cx="60" cy="60" r="56" fill="${c.bg}"/>
      <g clip-path="url(#${clip})">
        <path d="M20 120c2-24 18-38 40-38s38 14 40 38z" fill="${c.shirt}"/>
        <path d="M50 80l10 10 10-10" fill="none" stroke="#fff" stroke-width="3" stroke-linejoin="round" opacity=".85"/>
        <rect x="53" y="66" width="14" height="16" rx="6" fill="${c.skin}"/>
        <ellipse cx="60" cy="50" rx="21" ry="23" fill="${c.skin}"/>
        <path d="${c.hairPath}" fill="${c.hair}"/>
        <circle cx="52" cy="52" r="2.2" fill="#1F2937"/><circle cx="68" cy="52" r="2.2" fill="#1F2937"/>
        <path d="M54 61c3.5 3 8.5 3 12 0" fill="none" stroke="#9A4A3A" stroke-width="2" stroke-linecap="round"/>
      </g>
      <g class="il-float" filter="url(#${s})"><g transform="translate(96 92)"><circle r="16" fill="#fff"/><g transform="scale(1.05)">${mini[c.prop]}</g></g></g>
    </svg>`;
  }

  // Tải file Excel lên
  function upload({ w = 220 } = {}) {
    const g = uid(), s = uid();
    return `<svg viewBox="0 0 240 170" width="${w}" style="max-width:100%;height:auto" role="img" aria-label="Minh hoạ tải file Excel lên">${STYLE}
      <defs>${grad(g)}${shadow(s)}</defs>
      <g filter="url(#${s})"><rect x="40" y="40" width="110" height="120" rx="12" fill="#fff"/>
        <rect x="40" y="40" width="110" height="26" rx="12" fill="#16A34A"/><rect x="40" y="54" width="110" height="12" fill="#16A34A"/>
        <text x="54" y="58" font-size="12" font-weight="700" fill="#fff" font-family="system-ui">XLSX</text>
        ${[0, 1, 2, 3, 4].map((r) => [0, 1, 2].map((c) => `<rect x="${52 + c * 32}" y="${76 + r * 15}" width="26" height="9" rx="2" fill="${r === 2 && c === 1 ? "#FECACA" : "#E8F5EC"}"/>`).join("")).join("")}</g>
      <g class="il-float"><circle cx="178" cy="62" r="30" fill="url(#${g})" filter="url(#${s})"/><path d="M178 76V48M166 60l12-12 12 12" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/></g>
      <g class="il-float2"><circle cx="192" cy="128" r="14" fill="#ECFDF3" stroke="#ABEFC6"/><path d="m185 128 5 5 9-10" fill="none" stroke="#067647" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></g>
      <circle cx="26" cy="70" r="4" fill="#06B6D4" class="il-pop"/><circle cx="214" cy="20" r="3" fill="#7C3AED" class="il-pop"/>
    </svg>`;
  }

  // Hoàn thành (pháo giấy)
  function done({ w = 180 } = {}) {
    const g = uid(), s = uid();
    const conf = [[30, 40, "#2563EB", 12], [160, 34, "#DB2777", -18], [40, 130, "#F59E0B", 30], [168, 120, "#06B6D4", -8], [100, 14, "#7C3AED", 20], [20, 90, "#16A34A", -25], [182, 80, "#7C3AED", 40]];
    return `<svg viewBox="0 0 200 160" width="${w}" style="max-width:100%;height:auto" role="img" aria-label="Minh hoạ hoàn thành">${STYLE}
      <defs>${grad(g)}${shadow(s)}</defs>
      ${conf.map(([x, y, c, r], i) => `<rect x="${x}" y="${y}" width="10" height="5" rx="2" fill="${c}" transform="rotate(${r} ${x} ${y})" class="${i % 2 ? "il-float" : "il-float2"}"/>`).join("")}
      <g class="il-pulse" filter="url(#${s})"><circle cx="100" cy="82" r="46" fill="url(#${g})"/><path d="m80 82 14 14 26-28" fill="none" stroke="#fff" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/></g>
    </svg>`;
  }

  // Trống
  function empty({ w = 170 } = {}) {
    const s = uid();
    return `<svg viewBox="0 0 200 150" width="${w}" style="max-width:100%;height:auto" role="img" aria-label="Minh hoạ chưa có dữ liệu">${STYLE}
      <defs>${shadow(s)}</defs>
      <ellipse cx="100" cy="132" rx="64" ry="8" fill="#E3E8EF"/>
      <g filter="url(#${s})"><path d="M48 70l52-20 52 20v48l-52 18-52-18z" fill="#fff"/><path d="M48 70l52 18 52-18" fill="none" stroke="#CDD5DF" stroke-width="2"/><path d="M100 88v48" stroke="#CDD5DF" stroke-width="2"/>
        <path d="M48 70l-14-18 52-18 14 16z" fill="#F1F4F9" stroke="#CDD5DF" stroke-width="2" stroke-linejoin="round"/><path d="M152 70l14-18-52-18-14 16z" fill="#F1F4F9" stroke="#CDD5DF" stroke-width="2" stroke-linejoin="round"/></g>
      <path d="M100 40V14M84 22l-6-10M116 22l6-10" stroke="#C4B5FD" stroke-width="3" stroke-linecap="round" class="il-dash"/>
    </svg>`;
  }

  // Địa cầu & các nguồn dữ liệu
  function globe({ w = 260 } = {}) {
    const g = uid(), s = uid(), rg = uid();
    return `<svg viewBox="0 0 280 240" width="${w}" style="max-width:100%;height:auto" role="img" aria-label="Minh hoạ các nguồn dữ liệu toàn cầu">${STYLE}
      <defs>${grad(g)}${shadow(s)}<radialGradient id="${rg}" cx=".35" cy=".3"><stop offset="0" stop-color="#E0F2FE"/><stop offset="1" stop-color="#93C5FD"/></radialGradient></defs>
      <g filter="url(#${s})"><circle cx="140" cy="120" r="74" fill="url(#${rg})"/></g>
      <g fill="none" stroke="#fff" stroke-width="2" opacity=".85"><ellipse cx="140" cy="120" rx="74" ry="26"/><ellipse cx="140" cy="120" rx="30" ry="74"/><path d="M66 120h148"/></g>
      <path d="M110 80c10-6 26-4 30 6s-8 14-4 22-12 12-20 6-14-26-6-34zM160 130c8-4 22 0 22 10s-12 18-20 12-8-18-2-22z" fill="#60A5FA" opacity=".55"/>
      <g><ellipse cx="140" cy="120" rx="118" ry="44" fill="none" stroke="url(#${g})" stroke-width="2" class="il-dash"/>
        ${[[22, 120, "chart"], [258, 120, "doc"], [140, 76, "check"], [140, 164, "star"]].map(([x, y, k]) => `<g transform="translate(${x} ${y})"><circle r="17" fill="#fff" filter="url(#${s})"/><g transform="scale(1.05)">${mini[k]}</g></g>`).join("")}</g>
    </svg>`;
  }

  return { hub, person, upload, done, empty, globe, ROLES: Object.keys(ROLES) };
})();
