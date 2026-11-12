# Kế hoạch tối ưu UI/UX – Innovation Hub

> Mục tiêu: **nhìn vào là biết web làm gì, ai cũng tự làm được việc của mình**. Tông sáng, sạch, đáng tin cậy như một cổng dữ liệu nhà nước hiện đại.
> Bản thiết kế mẫu (mockup) kèm theo: [`poc/docs/ui-mockup/index.html`](poc/docs/ui-mockup/index.html). Mở trực tiếp trong trình duyệt, không cần server.
> Ngày lập: 12/11/2026
> **Trạng thái:** đã áp dụng giai đoạn 1 vào app (`poc/backend/app/static`); chưa làm "Tải file đã đánh dấu lỗi" và chưa tự lưu font Be Vietnam Pro.

---

## 0. Định hướng thẩm mỹ: "Tech-art, ít chữ" (cập nhật theo góp ý)

Góp ý của người dùng: **UI ít chữ thì đỡ khó dùng; thích phong cách nghệ thuật, công nghệ cao**. Định hướng:

| Yếu tố | Cách làm | Học từ |
|---|---|---|
| **Nền** | Trắng ngà + **dải màu "aurora"** mờ (xanh dương → tím → xanh ngọc) ở đầu trang + **lưới chấm** rất nhạt | Stripe, Vercel |
| **Bề mặt** | **Thẻ kính mờ** (trắng 72%, blur 16px, viền trắng 1px + bóng mềm); viền gradient cho thẻ nổi bật | Apple, Raycast |
| **Chữ** | Tiêu đề lớn, đậm, có **chữ gradient** cho từ khoá; mã chỉ tiêu, số liệu kỹ thuật dùng **monospace** | Linear, Vercel |
| **Số liệu** | **Số là nhân vật chính**: 40–56px, nhãn ngắn 2–4 chữ phía trên, chi tiết để trong tooltip | Apple, Stripe |
| **Icon** | Icon nét mảnh trong ô vuông bo góc có nền gradient nhạt, thay cho chữ giải thích | Linear, Raycast |
| **Chuyển động** | Nhẹ: thẻ nhích lên khi hover, số đếm lên khi tải, panel trượt mượt; tôn trọng `prefers-reduced-motion` | Framer, Linear |
| **Ít chữ** | Mỗi màn **≤ 1 câu mô tả**; nhãn ≤ 4 chữ; giải thích ẩn vào tooltip/"Xem thêm" | Apple, GOV.UK |

**Quy tắc ít chữ:**
1. Tiêu đề trang ≤ 4 chữ.
2. Mô tả ≤ 1 câu, ≤ 15 chữ.
3. Nút là động từ ≤ 3 chữ ("Nộp số liệu", "Duyệt").
4. Thẻ chỉ có: nhãn, số, xu hướng.
5. Mọi giải thích khác vào tooltip, panel hoặc trang chi tiết (*progressive disclosure*).

Phần design system ở §5 được điều chỉnh theo định hướng này (màu nhấn gradient, kính mờ, monospace). Mockup thể hiện đúng phong cách này.

---

## 1. Hiện trạng & vấn đề

Rà soát 10 trang của PoC ở chế độ sáng, trên khổ máy tính (1024px) và điện thoại (375px).

| # | Vấn đề | Ở đâu | Mức độ | Vì sao quan trọng |
|---|---|---|---|---|
| 1 | **Trang chủ không nói web làm gì.** Vào là gặp ngay 4 ô số ("5/46", "816 điểm dữ liệu chờ duyệt"), không có câu giới thiệu, không có lối vào theo vai trò. | `/` | Cao | Người mới (cán bộ đơn vị, lãnh đạo) không biết bắt đầu từ đâu. |
| 2 | **Thanh điều hướng 8 mục phẳng**, không nhóm, bị xuống 2 dòng ở 800px, **3 dòng trên điện thoại** (header cao 250px ≈ 1/3 màn hình). | Mọi trang | Cao | Khó tìm, tốn chỗ, không thể hiện quy trình nộp → duyệt → xem. |
| 3 | **Nhãn lẫn Anh–Việt**: "Registry", "API docs", "case", "connector", "Doc-ETL", "origin", "crawler:gii". | Mọi trang | Cao | Cán bộ nhà nước không quen thuật ngữ kỹ thuật. |
| 4 | **Bảng Duyệt dữ liệu 10 cột quá chật**: cột "đoạn trích" bị ngắt **2–3 ký tự mỗi dòng**, tên chỉ tiêu xuống 7 dòng. | `/review` | Cao | Đây là màn hình làm việc nhiều nhất của người duyệt. |
| 5 | **Dùng `prompt()` của trình duyệt** để nhập lý do từ chối và ghi chú. | Duyệt, Case, Đề xuất | Trung bình | Không giống ứng dụng, không kiểm tra được nội dung, không hiển thị ngữ cảnh. |
| 6 | **Icon là emoji** (⬇ 🖨 ▶ ↻ ✓ ✕ ◔), hiển thị khác nhau theo hệ điều hành. | Nhiều nơi | Trung bình | Trông thiếu chuyên nghiệp, không đồng bộ. |
| 7 | **Thiếu trạng thái tải (loading)** và **trạng thái trống** nhất quán: trang trắng vài giây khi chờ API; lỗi chỉ hiện bằng toast rồi biến mất. | Mọi trang | Trung bình | Người dùng tưởng hệ thống treo. |
| 8 | **Thiếu viền focus** khi dùng bàn phím; checkbox nhỏ (13px); nút nhỏ 24px. | Mọi trang | Trung bình | Không đạt WCAG 2.1 AA; khó bấm trên điện thoại. |
| 9 | **Trang Nộp số liệu dồn 2 việc khác nhau** (nộp template / trích từ tài liệu) cạnh nhau ngang hàng; không có các bước rõ ràng. | `/upload` | Trung bình | Cán bộ đơn vị chỉ cần việc thứ nhất. |
| 10 | **Không có tìm kiếm toàn cục**: muốn xem chỉ tiêu 0428 phải vào Registry rồi gõ. | — | Thấp | Chậm với người dùng thường xuyên. |
| 11 | **Mật độ thông tin không phân tầng**: thẻ chỉ tiêu chứa 7–8 dòng chữ cỡ 11–12px cạnh nhau, tag mức tin cậy chỉ có "B/C". | Tổng quan, Registry | Thấp | Khó quét nhanh. |
| 12 | **Chế độ tối tự bật theo máy** nhưng chưa được thiết kế kỹ; người dùng yêu cầu **tông sáng**. | Mọi trang | Thấp | Thống nhất nhận diện. |

Những gì **đang tốt, giữ lại**:
- Mỗi số liệu đều có nguồn, mức tin cậy, minh chứng.
- Báo lỗi file theo từng ô.
- Biểu đồ SVG tự viết, không phụ thuộc CDN.
- Có cột đối chiếu nguồn khác.
- Tooltip trên biểu đồ.

---

## 2. Tham khảo – học được gì từ đâu

| Nguồn | Học điều gì cụ thể | Áp dụng vào |
|---|---|---|
| **GOV.UK Design System** | Ngôn ngữ đơn giản, "một việc mỗi trang"; mẫu **Error summary** (hộp lỗi đầu trang, liên kết tới từng ô lỗi); mẫu **Task list** cho quy trình nhiều bước. | Luồng Nộp số liệu; cách viết nhãn và thông báo lỗi. |
| **USWDS** (U.S. Web Design System) | Hệ token màu/chữ/khoảng cách cho cổng chính phủ; tiêu chuẩn accessibility; **Step indicator**; banner xác thực "trang chính thức". | Design tokens, Stepper, banner nhận diện. |
| **Our World in Data** | Mỗi biểu đồ có **tiêu đề là một câu kết luận**, mô tả nguồn ngay dưới; nút chuyển **Biểu đồ ↔ Bảng**; tải dữ liệu ngay tại biểu đồ. | Trang chi tiết chỉ tiêu, thẻ số liệu trang chủ. |
| **OECD Data Explorer** | **Thanh lọc dạng chip**, hiển thị rõ bộ lọc đang áp dụng; chọn chiều dữ liệu (năm, địa bàn, phân tổ) không rời trang. | FilterBar ở Bộ chỉ tiêu và Hàng chờ duyệt. |
| **Stripe Dashboard** | Bảng dữ liệu gọn: **ít cột, bấm dòng mở panel chi tiết bên phải**; badge trạng thái icon+chữ; thanh thao tác hàng loạt xuất hiện khi chọn dòng. | Hàng chờ duyệt (thay bảng 10 cột). |
| **Linear** | **Phím tắt** cho thao tác lặp lại (J/K di chuyển, A/R duyệt/từ chối); command palette (Ctrl+K) để tìm và nhảy trang; phản hồi tức thì. | Hàng chờ duyệt, tìm kiếm toàn cục. |
| **IBM Carbon** | Bảng **mật độ cao** cho dữ liệu doanh nghiệp: tuỳ chọn mật độ dòng, header dính, cột số căn phải, skeleton loading. | DataTable, Skeleton. |
| **Atlassian Design System** | **Modal** xác nhận có lý do; **Flag/Toast** có hành động "Hoàn tác"; **Empty state** có minh hoạ + hành động tiếp theo; sidebar điều hướng nhóm theo việc. | Modal thay `prompt()`, EmptyState, Sidebar. |
| **Stripe** (stripe.com) | Dải màu gradient mềm làm điểm nhấn thương hiệu; số liệu lớn, ít chữ; tông sáng sang trọng. | Nền aurora, StatCard. |
| **Vercel** | Lưới chấm/đường kẻ mảnh làm nền; chữ đen trắng tương phản cao; monospace cho thông tin kỹ thuật. | Nền trang, mã chỉ tiêu. |
| **Apple** | Mỗi khối chỉ 1 thông điệp + 1 con số lớn; khoảng trắng rộng. | Trang chủ ít chữ. |
| **Raycast / Linear** | Thẻ kính mờ, icon trong ô gradient, command palette. | Thẻ vai trò, tìm kiếm Ctrl+K. |

> Chỉ học **nguyên tắc và mẫu tương tác**, không sao chép logo, hình ảnh hay nhận diện thương hiệu của các trang trên.

---

## 3. Nguyên tắc thiết kế

0. **Ít chữ**: số và icon nói trước, chữ giải thích để sau (quy tắc ở §0).
1. **Rõ mục đích ngay 5 giây đầu**: mỗi trang có tiêu đề + 1 câu mô tả + 1 hành động chính.
2. **Theo vai trò, không theo kỹ thuật**: tổ chức menu theo *việc người dùng cần làm* (nộp, duyệt, xem, đánh giá), không theo module hệ thống (connector, Doc-ETL).
3. **Thuần Việt, ngắn gọn**: bỏ thuật ngữ kỹ thuật khỏi giao diện người dùng (xem Từ điển §7).
4. **Mỗi con số đều kể được nguồn**: giá trị, năm, nguồn, mức tin cậy, trạng thái duyệt luôn đi cùng nhau.
5. **Ít mà rõ**: mặc định chỉ hiện thông tin để ra quyết định; chi tiết mở trong panel bên phải.
6. **Phản hồi mọi thao tác**: loading → thành công/lỗi rõ ràng, có hoàn tác khi có thể.
7. **Tông sáng, tin cậy**: nền trắng ngà, một màu nhấn xanh dương, màu trạng thái chỉ dùng cho trạng thái.
8. **Dùng được bằng bàn phím và trên điện thoại** (WCAG 2.1 AA).

---

## 4. Kiến trúc thông tin mới

### 4.1. Khung trang (App shell)

```
┌────────────┬───────────────────────────────────────────────────────────────┐
│ ◆ Cổng dữ  │  [🔍 Tìm chỉ tiêu, đơn vị, trang…  Ctrl K]   [🔔 816 chờ duyệt] [👤] │
│ liệu ĐMST  ├───────────────────────────────────────────────────────────────┤
│            │  Trang chủ › Hàng chờ duyệt                                      │
│ ⌂ Tổng quan│  Hàng chờ duyệt                               [Hành động chính]  │
│ ▤ Bộ chỉ tiêu│ 816 số liệu đang chờ xác nhận trước khi công bố.               │
│            │                                                                 │
│ DỮ LIỆU    │  (nội dung trang)                                               │
│ ⤒ Nộp số liệu│                                                               │
│ ☑ Hàng chờ duyệt 816│                                                        │
│ ⟳ Nguồn tự động│                                                             │
│            │                                                                 │
│ PHÂN TÍCH  │                                                                 │
│ ★ Đánh giá chương trình│                                                     │
│ ✦ Đề xuất tiêu chí│                                                          │
│ ▦ Báo cáo  │                                                                 │
│ ─────────  │                                                                 │
│ ? Hướng dẫn│                                                                 │
│ </> Dành cho kỹ thuật│                                                       │
└────────────┴───────────────────────────────────────────────────────────────┘
```

- **Sidebar trái 248px**: 3 nhóm, icon SVG đồng bộ, badge số việc chờ. Thu gọn còn 64px; trên điện thoại thành **ngăn kéo** mở bằng nút ☰ (header điện thoại cao **56px** thay vì 250px).
- **Thanh trên cùng**:
  - Ô tìm kiếm toàn cục (Ctrl+K) tìm chỉ tiêu theo mã/tên không dấu, đơn vị, trang.
  - Chuông việc chờ.
  - Người dùng (vai trò hiện tại).
- **PageHeader** thống nhất: breadcrumb, tiêu đề, 1 câu mô tả, hành động chính bên phải.
- "API docs" chuyển xuống mục **"Dành cho kỹ thuật"** cuối sidebar.

### 4.2. Sơ đồ trang

| Nhóm | Trang | URL hiện tại | Đổi tên / thay đổi |
|---|---|---|---|
| — | **Tổng quan** | `/` | Thêm phần giới thiệu + lối vào theo vai trò |
| — | **Bộ chỉ tiêu** | `/registry` | Đổi tên từ "Registry"; bấm chỉ tiêu mở trang chi tiết thay vì panel chật |
| — | ↳ Chi tiết chỉ tiêu | `/indicator` | Thêm tab Biểu đồ / Bảng / Nguồn / Lịch sử |
| Dữ liệu | **Nộp số liệu** | `/upload` | Stepper 3 bước; "Trích từ tài liệu" thành tab phụ |
| Dữ liệu | **Hàng chờ duyệt** | `/review` | Danh sách gọn + panel chi tiết + phím tắt |
| Dữ liệu | **Nguồn tự động** | `/connectors` | Đổi tên từ "Thu thập tự động"; dạng thẻ có trạng thái sức khoẻ |
| Phân tích | **Đánh giá chương trình** | `/cases` | Đổi tên từ "Đánh giá case" |
| Phân tích | **Đề xuất tiêu chí** | `/insights` | Giữ, chuẩn hoá thẻ |
| Phân tích | **Báo cáo** | `/report` | Đưa thành mục riêng trên menu (đang ẩn trong nút) |

### 4.3. Trang chủ: lối vào theo vai trò

```
            ░░▒▒ nền aurora + lưới chấm ▒▒░░
   Dữ liệu Đổi mới sáng tạo  (chữ gradient)
   46 chỉ tiêu quốc gia · một nơi duy nhất          ← 1 câu, 8 chữ

   [⤒ Nộp số liệu]  [☑ Duyệt · 816]  [▦ Báo cáo]  [★ Đánh giá]   ← 4 ô icon, mỗi ô 2–3 chữ

   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
   │ Có số liệu│ │ Chờ duyệt │ │ GII 2026 │ │ Nhân lực │   ← nhãn ≤ 3 chữ
   │  9/46    │ │  816      │ │  #43 ▲1  │ │ 8,9 ▲7%  │   ← số 40–56px
   └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

Tiếp theo: 4 vòng tiến độ theo trụ cột (chỉ số + tên trụ cột), lưới chỉ tiêu nổi bật dạng thẻ nhỏ (mã monospace, số, sparkline). Mọi giải thích nằm trong tooltip.

---

## 5. Design system – tông sáng

### 5.1. Màu

| Token | Giá trị | Dùng cho |
|---|---|---|
| `--bg` | `#F6F8FB` | Nền trang (xám xanh rất nhạt) |
| `--surface` | `#FFFFFF` | Thẻ, bảng, panel |
| `--surface-2` | `#F1F4F9` | Nền phụ: hàng header bảng, ô nhập vô hiệu |
| `--border` | `#E3E8EF` | Viền thẻ, đường kẻ bảng |
| `--border-strong` | `#CDD5DF` | Viền ô nhập |
| `--text` | `#0F1B2D` | Chữ chính (tương phản 16:1) |
| `--text-2` | `#475467` | Chữ phụ (7,5:1) |
| `--text-3` | `#667085` | Chú thích, placeholder (4,9:1 – vẫn đạt AA) |
| `--primary` | `#1D5FD1` | Nút chính, liên kết, mục menu đang chọn (5,6:1 trên trắng) |
| `--primary-hover` | `#174DAA` | Hover nút chính |
| `--primary-soft` | `#EAF1FD` | Nền mục menu đang chọn, chip lọc đang bật |
| `--focus` | `#1D5FD1` + vòng 3px `#9EC2F7` | Viền focus bàn phím |
| `--grad-brand` | `linear-gradient(135deg, #2563EB 0%, #7C3AED 55%, #06B6D4 100%)` | Logo, chữ gradient tiêu đề, nút chính nổi bật, viền thẻ nổi bật |
| `--aurora` | 3 vùng mờ: `#93C5FD` · `#C4B5FD` · `#99F6E4` (opacity 35–45%, blur 80px) | Nền đầu trang |
| `--glass` | `rgba(255,255,255,.72)` + `backdrop-filter: blur(16px)` + viền `rgba(255,255,255,.8)` | Thẻ, sidebar, top bar |
| `--grid-dot` | chấm `#CBD5E1` 1px, cách 22px, mờ dần về cuối trang | Nền trang |

> Gradient chỉ dùng cho **nhận diện và điểm nhấn** (logo, tiêu đề, 1 nút chính/màn), không dùng cho chữ thường hay trạng thái, để giữ tương phản và tính nghiêm túc của cổng dữ liệu nhà nước.

**Màu trạng thái** (chỉ dùng cho trạng thái, luôn đi kèm icon + chữ):

| Trạng thái | Chữ | Nền | Icon | Dùng cho |
|---|---|---|---|---|
| Thành công / Đã công bố | `#067647` | `#ECFDF3` | ✓ vòng tròn | Số liệu đã công bố, lần chạy thành công |
| Cảnh báo / Chờ duyệt | `#B54708` | `#FFFAEB` | ◷ đồng hồ | Chờ duyệt, tạm tính |
| Lỗi / Từ chối | `#B42318` | `#FEF3F2` | ✕ vòng tròn | Lỗi kiểm tra, từ chối, connector lỗi |
| Thông tin | `#175CD3` | `#EFF8FF` | ⓘ | Ghi chú, gợi ý |
| Trung tính | `#475467` | `#F2F4F7` | — | Chưa có dữ liệu |

**Mức tin cậy A–D**: badge viền, **không** dùng màu trạng thái để tránh nhầm "D = lỗi". Chữ kèm nghĩa khi hover ("A – Nguồn chuẩn quốc tế").

**Bảng màu biểu đồ** (skill dataviz, đã kiểm tra an toàn cho người mù màu ở chế độ sáng; dùng **theo thứ tự cố định**, tối đa 3 chuỗi/biểu đồ):

| Thứ tự | Màu | Hex |
|---|---|---|
| 1 | Xanh dương | `#2a78d6` |
| 2 | Cam | `#eb6834` |
| 3 | Xanh ngọc | `#1baf7a` |
| (4–8, chỉ khi thật cần) | vàng, hồng, xanh lá, tím, đỏ | `#eda100` `#e87ba4` `#008300` `#6250d6` `#e34948` |

Chuỗi đơn sắc (ma trận, mật độ): xanh dương `#cde2fb → #0d366b`. Màu trạng thái **không** dùng làm màu chuỗi.

### 5.2. Chữ

- **Be Vietnam Pro**: font thiết kế cho tiếng Việt, dấu đặt đúng, giấy phép OFL. **Tự host** các file `.woff2` 400/500/600/700 trong `/static/fonts`, vì máy chủ cơ quan thường chặn Internet nên không dùng CDN. Font dự phòng: `system-ui, "Segoe UI", Roboto, sans-serif`.
- Số liệu dùng `font-variant-numeric: tabular-nums` để các cột số thẳng hàng.
- **Monospace** (JetBrains Mono, OFL, tự host; dự phòng `ui-monospace, SF Mono, Menlo`) cho mã chỉ tiêu (`0428`, `DX-01`), mã nguồn, số hiệu văn bằng: tạo cảm giác "công nghệ" và dễ dò.

| Cấp | Cỡ / dòng | Đậm | Dùng cho |
|---|---|---|---|
| Display | 32 / 40 | 700 | Tiêu đề trang chủ |
| H1 | 24 / 32 | 700 | Tiêu đề trang |
| H2 | 18 / 28 | 600 | Tiêu đề mục |
| H3 | 16 / 24 | 600 | Tiêu đề thẻ |
| Body | **15** / 24 | 400 | Nội dung (tăng từ 14) |
| Small | 13 / 20 | 400 | Chú thích, nhãn phụ |
| Số lớn | 28 / 36 | 700 | Giá trị trong thẻ số liệu |

### 5.3. Khoảng cách, bo góc, đổ bóng

- **Khoảng cách** theo bội số 4: `4 8 12 16 20 24 32 40 48 64`. Thẻ đệm 20–24px; khoảng giữa các mục 32px.
- **Bo góc**: ô nhập/nút `8px`, thẻ `12px`, badge `999px`.
- **Đổ bóng** rất nhẹ, chỉ cho phần tử nổi:
  - `--shadow-sm: 0 1px 2px rgba(16,24,40,.06)` cho thẻ;
  - `--shadow-lg: 0 12px 32px rgba(16,24,40,.12)` cho modal/panel.
- **Kích thước chạm** tối thiểu **40px** cho nút/ô nhập (44px trên điện thoại); checkbox 18px.
- **Lưới**: nội dung tối đa 1280px; sidebar 248px; panel chi tiết 480px.

### 5.4. Icon

Bộ icon SVG nét (stroke 1,75px, 20px) tự chứa trong một file `icons.svg` dạng sprite, theo phong cách Lucide (giấy phép ISC). **Bỏ toàn bộ emoji.**

---

## 6. Thư viện component

| Component | Mô tả & hành vi | Thay cho |
|---|---|---|
| **Sidebar** | 3 nhóm, icon + nhãn, badge số chờ; thu gọn/mở; ngăn kéo trên mobile; nhớ trạng thái thu gọn | Thanh tab 8 mục |
| **TopBar** | Tìm kiếm toàn cục (Ctrl+K, kết quả nhóm theo Chỉ tiêu / Đơn vị / Trang), chuông việc chờ, menu người dùng | — |
| **PageHeader** | Breadcrumb + H1 + mô tả 1 câu + hành động chính (tối đa 1 nút chính + 1 nút phụ) | Tiêu đề rời rạc |
| **StatCard** | Nhãn → số lớn → câu giải thích → xu hướng (▲/▼ + chữ "cải thiện/kém đi") → nguồn | Ô KPI chỉ có số |
| **StatusBadge** | Icon + chữ + màu trạng thái (bảng §5.1); không bao giờ chỉ có màu | `.status` hiện tại |
| **ConfidenceBadge** | "A" … "D" dạng viền, tooltip giải nghĩa | `.conf` màu đặc |
| **DataTable** | Header dính, cột số căn phải, hover dòng, chọn nhiều, mật độ Thoáng/Gọn, phân trang 50 dòng, cột co giãn có `min-width`, chữ dài thì cắt "…" + tooltip | Bảng tự do |
| **FilterBar** | Ô tìm + các nút lọc dạng menu; bộ lọc đang bật hiện thành **chip có nút ✕**, nút "Xoá lọc" | Hàng `<select>` |
| **Drawer** (panel phải) | 480px, có tiêu đề, nội dung cuộn, thanh hành động dính đáy; Esc để đóng; giữ focus bên trong | Panel hiện tại (không khoá focus) |
| **Modal** | Xác nhận/nhập lý do: tiêu đề, mô tả hậu quả, ô lý do bắt buộc (đếm ký tự), gợi ý lý do nhanh dạng chip | `prompt()` |
| **Toast** | Góc dưới phải, icon trạng thái, nút "Hoàn tác" cho thao tác duyệt; lỗi không tự biến mất | Toast đen giữa màn hình |
| **Banner** | Thông báo nội trang (thông tin/cảnh báo/lỗi), dùng cho "Số liệu giả lập", "Độ phủ thấp" | `warnbox` |
| **EmptyState** | Minh hoạ nhỏ + 1 câu giải thích + hành động tiếp theo | "Không có điểm dữ liệu nào." |
| **Skeleton** | Khối xám nhấp nháy theo hình dạng nội dung khi đang tải | Trang trắng |
| **Stepper** | 3 bước có số, trạng thái đã xong/đang làm/chưa làm, quay lại được | — |
| **ErrorSummary** | Hộp lỗi đầu trang kiểu GOV.UK: "Có 9 lỗi cần sửa", mỗi lỗi là liên kết tới dòng trong bảng | Bảng lỗi thuần |
| **Tabs** | Gạch chân màu primary, điều hướng phím ←/→ | — |
| **Chart** | Tiêu đề là câu kết luận, chú thích nguồn dưới, nút Biểu đồ/Bảng, nút tải CSV | Biểu đồ không tiêu đề |

---

## 7. Spec từng trang

### 7.1. Tổng quan (`/`)

1. **Phần giới thiệu**: tên cổng + câu mô tả (xem §4.3) + năm báo cáo đang xem + "Cập nhật lần cuối".
2. **"Bạn cần làm gì hôm nay?"**: 4 thẻ vai trò, mỗi thẻ có 1 con số việc cần làm và 1 nút.
3. **4 StatCard có câu giải thích**:
   - "9 / 46 chỉ tiêu có số liệu công bố";
   - "816 số liệu chờ duyệt";
   - "GII 2026: hạng 43 (▲ 1 bậc)";
   - "Nhân lực R&D: 8,9 FTE/vạn dân (▲ 7,2%)".
4. **Độ phủ theo trụ cột**: thanh ngang có nhãn số trực tiếp.
5. **Chỉ tiêu nổi bật**: lưới thẻ, tối đa 6, nút "Xem tất cả 46 chỉ tiêu".
6. **Ma trận** chuyển xuống trang Bộ chỉ tiêu (tab "Theo năm"), vì quá dài cho trang chủ.

### 7.2. Bộ chỉ tiêu (`/registry`)

- FilterBar dạng chip: Văn bản · Trụ cột · Cách thu thập · Mức tin cậy · Giai đoạn · Cơ quan.
- 2 chế độ xem: **Danh sách** (bảng 5 cột: Mã, Tên + văn bản, Trụ cột, Số liệu mới nhất, Trạng thái dữ liệu) và **Theo năm** (ma trận).
- Bấm dòng → **trang chi tiết** (không còn panel chật); sửa định nghĩa/mục tiêu qua nút "Chỉnh sửa" mở Drawer.

### 7.3. Chi tiết chỉ tiêu (`/indicator?code=`)

- PageHeader: mã + tên, badge văn bản, cơ quan chủ trì, mức tin cậy; hành động: "Tải dữ liệu", "Chỉnh sửa".
- 4 StatCard: giá trị mới nhất · so kỳ trước · mục tiêu & % đạt · số nguồn.
- Tabs: **Biểu đồ** (tiêu đề kết luận, chọn phân tổ & so sánh, nút Bảng) · **Bảng số liệu** · **Nguồn & minh chứng** · **Lịch sử duyệt**.

### 7.4. Nộp số liệu (`/upload`): stepper 3 bước

1. **Tải mẫu**:
   - thẻ mẫu 0101 + 0102: phiên bản, ngày cập nhật, nút tải;
   - tóm tắt 3 lưu ý quan trọng nhất (không sửa cột, chọn từ danh sách, để trống nếu chưa có số).
2. **Tải lên**: vùng kéo thả lớn; hiện tên file, dung lượng, thanh tiến trình.
3. **Kết quả kiểm tra**:
   - Hợp lệ: banner xanh "Đã nhận 39 dòng của Cục Thông tin, Thống kê – đang chờ duyệt", kèm bảng tóm tắt theo chỉ tiêu × năm.
   - Có lỗi: **ErrorSummary** "Có 9 lỗi ở 9 dòng – file chưa được nhập"; bảng lỗi gom theo sheet, mỗi dòng có hướng dẫn sửa cụ thể; nút **"Tải file đã đánh dấu lỗi"** (tô đỏ ô lỗi + ghi chú trong Excel); nút "Nộp lại file đã sửa".
- **"Trích số liệu từ tài liệu"** chuyển thành tab phụ (dành cho người duyệt/chuyên gia), không đặt ngang hàng.
- Bên dưới: "Lượt nộp của đơn vị bạn": bảng 5 cột + StatusBadge.

### 7.5. Hàng chờ duyệt (`/review`): danh sách + panel

- **Tab theo nguồn** ở đầu: Tất cả (816) · Đơn vị nộp (45) · Nguồn tự động (768) · Trích tài liệu (3); kèm chip "Có cảnh báo (3)".
- **Bảng 6 cột**: ☐ · Chỉ tiêu (mã + tên 1 dòng, cắt …) · Kỳ / địa bàn · Giá trị (căn phải, đơn vị nhỏ) · So với nguồn khác (±% có màu + icon) · Nguồn (StatusBadge mức tin cậy).
- **Bấm dòng → Drawer** chi tiết:
  - đoạn trích nguồn đầy đủ;
  - nút mở minh chứng;
  - lịch sử phiên bản;
  - cảnh báo;
  - 2 nút dính đáy "Công bố" / "Từ chối…".
- **Thanh hàng loạt** nổi ở đáy khi chọn ≥ 1 dòng: "Đã chọn 39 · Công bố · Từ chối · Bỏ chọn".
- **Phím tắt**: `J/K` lên xuống · `X` chọn · `A` công bố · `R` từ chối (mở Modal) · `?` xem phím tắt.
- **Từ chối = Modal** có ô lý do bắt buộc + chip lý do nhanh ("Sai đơn vị", "Lệch nguồn chính thức", "Thiếu minh chứng", "Trùng số liệu").
- Toast "Đã công bố 39 số liệu · **Hoàn tác**" (trong 10 giây).
- Tên người duyệt lấy từ phiên đăng nhập (giai đoạn 2); giai đoạn 1 nhập 1 lần ở menu người dùng, không đặt trong thanh lọc.

### 7.6. Nguồn tự động (`/connectors`)

- Lưới thẻ: tên nguồn, chỉ tiêu, lịch chạy, lần chạy gần nhất (StatusBadge + "2 giờ trước"), kết quả bằng chữ ("42 số liệu, không có thay đổi").
- Thẻ lỗi nổi lên đầu kèm hướng dẫn xử lý; nút "Chạy ngay" có trạng thái loading trong nút.
- Lịch sử chạy chuyển vào Drawer của từng nguồn.

### 7.7. Đánh giá chương trình (`/cases`, `/case`)

- Danh sách dạng thẻ: tên, giai đoạn, **vòng điểm** 0–100, kết luận, độ phủ "12/50 tiêu chí".
- Scorecard:
  - Banner "Tạm tính – độ phủ thấp" đặt **ngay dưới điểm**, không lẫn trong chữ nhỏ.
  - 5 nhóm thành thanh ngang có nhãn trực tiếp.
  - Bảng tiêu chí gom theo nhóm, mặc định chỉ hiện tiêu chí đã có điểm.
- Form tạo mới chuyển thành **stepper 4 bước**: Thông tin → Công bố & tác giả → Văn bằng → Mục tiêu.

### 7.8. Đề xuất tiêu chí (`/insights`)

- Thẻ đề xuất gọn hơn: tên, trụ cột, giá trị tính thử + sparkline, 3 thanh điểm, cảnh báo trùng dạng Banner; chi tiết (công thức, nguồn, lý do) mở bằng "Xem chi tiết".
- Chấp nhận/Từ chối qua Modal.

### 7.9. Báo cáo (`/report`)

- Chọn kỳ → xem trước → "Tải Excel" / "In / Lưu PDF". Thêm lựa chọn "Chỉ chỉ tiêu có số liệu" / "Tất cả 46 chỉ tiêu".

### 7.10. Trạng thái chung mọi trang

- **Đang tải**: Skeleton theo hình nội dung, không để trang trắng.
- **Trống**: EmptyState có hành động (vd. "Chưa có số liệu nào chờ duyệt 🎉 → Xem tổng quan").
- **Lỗi kết nối**: Banner đỏ cố định ở đầu nội dung + nút "Thử lại".

---

## 8. Từ điển thuật ngữ (giao diện người dùng)

| Đang dùng | Đổi thành | Ghi chú |
|---|---|---|
| Registry | **Bộ chỉ tiêu** | |
| Case | **Chương trình / nhiệm vụ** | "Đánh giá chương trình" |
| Connector / Thu thập tự động | **Nguồn tự động** | |
| crawler:gii, origin | **Nguồn: WIPO – GII (tự động)** | Hiển thị tên nguồn, không hiển thị mã |
| agency:… | **Đơn vị nộp: …** | |
| calc:… | **Tự tính** | |
| Doc-ETL | **Trích từ tài liệu** | |
| Data point / điểm dữ liệu | **Số liệu** | "816 số liệu chờ duyệt" |
| Published / Đã công bố | **Đã công bố** | giữ |
| Needs review | **Chờ duyệt** | giữ |
| Breakdown / phân tổ | **Phân tổ** | giữ – thuật ngữ thống kê chính thức |
| Confidence A/B/C/D | **Độ tin cậy A–D** + tooltip | |
| TRL | **Mức sẵn sàng công nghệ (TRL)** | Lần đầu viết đủ |
| API docs | **Dành cho kỹ thuật** | Cuối sidebar |
| Scorecard | **Bảng điểm** | |
| Snapshot / evidence | **Minh chứng** | |
| Proxy | **Số liệu tham khảo (khác định nghĩa)** | |

---

## 9. Accessibility – WCAG 2.1 AA

- Tương phản chữ ≥ 4,5:1, chữ lớn ≥ 3:1 (bảng màu §5.1 đã đạt). Màu biểu đồ có nhãn trực tiếp hoặc bảng thay thế (một số màu dưới 3:1 trên nền sáng).
- **Không truyền thông tin chỉ bằng màu**: trạng thái luôn có icon + chữ; xu hướng có ▲/▼ + "cải thiện/kém đi".
- **Viền focus** rõ (vòng 3px) trên mọi phần tử tương tác; thứ tự Tab hợp lý; nút "Bỏ qua tới nội dung".
- Modal/Drawer: khoá focus, Esc để đóng, trả focus về nút đã mở.
- Bảng có `<caption>`, `scope` cho header; biểu đồ có `aria-label` mô tả + bảng thay thế.
- Kích thước chạm ≥ 40px (44px mobile); văn bản phóng to 200% không vỡ bố cục.
- Ngôn ngữ trang `lang="vi"`; thông báo động dùng `aria-live`.
- Kiểm tra bằng axe DevTools + điều hướng thuần bàn phím + VoiceOver trước mỗi lần bàn giao.

---

## 10. Lộ trình

### Giai đoạn 1: làm lại trong stack hiện tại (HTML + CSS/JS dùng chung), **≈ 8–10 ngày công**

| # | Hạng mục | Ước lượng |
|---|---|---|
| 1 | Design tokens (`tokens.css`), font Be Vietnam Pro tự host, bộ icon SVG, bỏ chế độ tối tự động (giữ tông sáng) | 1 ngày |
| 2 | App shell: Sidebar + TopBar + PageHeader + drawer mobile; áp cho 10 trang | 1,5 ngày |
| 3 | Component: StatusBadge, ConfidenceBadge, StatCard, Banner, Toast (có hoàn tác), Modal, Drawer, EmptyState, Skeleton | 1,5 ngày |
| 4 | Trang chủ mới (giới thiệu + lối vào theo vai trò + StatCard có câu giải thích) | 1 ngày |
| 5 | Nộp số liệu: Stepper + ErrorSummary + "Tải file đã đánh dấu lỗi" (backend sinh xlsx tô đỏ) | 1,5 ngày |
| 6 | Hàng chờ duyệt: bảng 6 cột + Drawer + thanh hàng loạt + phím tắt + Modal từ chối | 1,5 ngày |
| 7 | Đổi thuật ngữ toàn bộ theo §8; tìm kiếm toàn cục Ctrl+K | 1 ngày |
| 8 | Accessibility pass + kiểm tra mobile + sửa lỗi | 1 ngày |

### Giai đoạn 2: cho MVP, **cân nhắc chuyển sang React/Next.js**

- **Lý do**: số trang và trạng thái tăng (đăng nhập, phân quyền theo đơn vị, thông báo, nhiều bảng phức tạp). Component dùng lại và kiểm thử dễ hơn.
- **Đề xuất**: Next.js + TypeScript, TanStack Table cho DataTable, Radix UI/shadcn cho Modal/Drawer/Tabs (đã có sẵn accessibility). Design tokens giữ nguyên từ giai đoạn 1.
- **Ước lượng**: ≈ 15–20 ngày công cho 10 trang + đăng nhập. Nên làm sau khi UAT xác nhận luồng ở giai đoạn 1.
- **Nếu giữ stack hiện tại**: tách JS mỗi trang thành module, thêm kiểm thử giao diện bằng Playwright.

---

## 11. Chỉ số thành công

| Chỉ số | Cách đo | Mục tiêu |
|---|---|---|
| **5-second test** | Cho người dùng mới xem trang chủ 5 giây rồi hỏi "Trang này để làm gì?" | ≥ 4/5 người trả lời đúng ý "thu thập/theo dõi chỉ tiêu ĐMST" |
| **Tỷ lệ hoàn thành nhiệm vụ** | Kịch bản [`poc/docs/UAT_checklist.md`](poc/docs/UAT_checklist.md) (A1–A4, B1–B4, C1–C4) | ≥ 90% nhiệm vụ hoàn thành không cần trợ giúp |
| **Thời gian làm nhiệm vụ** | Đo theo UAT | A3 (sửa file lỗi) < 10 phút; B3 (duyệt 1 lượt nộp) < 2 phút; C1 (trả lời thứ hạng GII) < 30 giây |
| **SUS** (System Usability Scale) | Bảng hỏi 10 câu sau UAT | ≥ 75 (mức "tốt") |
| **Lỗi accessibility** | axe DevTools trên 10 trang | 0 lỗi nghiêm trọng |
| **Hiệu năng cảm nhận** | Thời gian đến khi thấy nội dung (có skeleton) | < 1 giây trên mạng nội bộ |

So sánh trước/sau: chạy cùng kịch bản UAT trên giao diện hiện tại và giao diện mới với 2 nhóm người dùng khác nhau.

---

## 12. Mockup kèm theo

[`poc/docs/ui-mockup/index.html`](poc/docs/ui-mockup/index.html) là trang HTML tự chứa, không cần server hay Internet. Dùng số liệu demo hiện có và chuyển được giữa 3 màn:

1. **Trang chủ**: giới thiệu, lối vào theo vai trò, StatCard có câu giải thích, độ phủ trụ cột, chỉ tiêu nổi bật.
2. **Nộp số liệu**: Stepper 3 bước, ErrorSummary 9 lỗi, chuyển qua lại giữa "Có lỗi" và "Hợp lệ".
3. **Hàng chờ duyệt**: tab theo nguồn, bảng 6 cột, Drawer chi tiết, thanh hàng loạt, Modal từ chối thay `prompt()`.

Mockup là **bản minh hoạ hướng thiết kế**, chưa nối API.
