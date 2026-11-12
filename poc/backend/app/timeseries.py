"""Chuỗi thời gian theo kỳ (spec §5.1): mã kỳ, gộp tháng → quý → năm, cửa sổ, mức thay đổi.

Mã kỳ: '2025' (năm), '2025-Q4' (quý), '2025-11' (tháng).
Nguyên tắc:
- Gộp theo quy tắc của chỉ tiêu: sum (cộng), avg (trung bình), last (giá trị kỳ con cuối).
- Kỳ cha thiếu kỳ con thì KHÔNG tính (không suy diễn, không nội suy).
- Kỳ thiếu số liệu trong cửa sổ trả về None (biểu đồ để trống, không nối liền).
- Thay đổi so với kỳ trước (MoM/QoQ) và cùng kỳ năm trước (YoY) tính theo %; thiếu kỳ so sánh → None.
- Luỹ kế từ đầu năm (YTD) chỉ có nghĩa với quy tắc sum.
"""

from __future__ import annotations

import re
from collections import defaultdict

ORDER = {"M": 0, "Q": 1, "Y": 2}
CHILDREN = {("M", "Q"): 3, ("M", "Y"): 12, ("Q", "Y"): 4}
RULES = ("sum", "avg", "last")


def parse_period(p: str) -> tuple[str, int, int]:
    """'2025' → ('Y', 2025, 0); '2025-Q4' → ('Q', 2025, 4); '2025-11' → ('M', 2025, 11)."""
    s = str(p).strip()
    if m := re.fullmatch(r"(\d{4})-Q([1-4])", s):
        return "Q", int(m[1]), int(m[2])
    if m := re.fullmatch(r"(\d{4})-(\d{2})", s):
        month = int(m[2])
        if 1 <= month <= 12:
            return "M", int(m[1]), month
    if re.fullmatch(r"\d{4}", s):
        return "Y", int(s), 0
    raise ValueError(f"Mã kỳ không hợp lệ: {p}")


def fmt_period(t: str, year: int, sub: int = 0) -> str:
    return str(year) if t == "Y" else f"{year}-Q{sub}" if t == "Q" else f"{year}-{sub:02d}"


def period_type(p: str) -> str:
    return parse_period(p)[0]


def parent_of(p: str, to: str) -> str:
    t, y, sub = parse_period(p)
    if ORDER[to] <= ORDER[t]:
        raise ValueError(f"Không gộp {t} lên {to}")
    if to == "Y":
        return str(y)
    return fmt_period("Q", y, (sub - 1) // 3 + 1)  # M → Q


def shift(p: str, n: int) -> str:
    """Dịch n kỳ cùng loại (n âm = lùi)."""
    t, y, sub = parse_period(p)
    if t == "Y":
        return str(y + n)
    per = 4 if t == "Q" else 12
    idx = y * per + (sub - 1) + n
    return fmt_period(t, idx // per, idx % per + 1)


def previous(p: str) -> str:
    return shift(p, -1)


def same_period_last_year(p: str) -> str:
    t = period_type(p)
    return shift(p, -{"Y": 1, "Q": 4, "M": 12}[t])


def period_range(first: str, last: str) -> list[str]:
    out, p = [], first
    while _key(p) <= _key(last):
        out.append(p)
        p = shift(p, 1)
    return out


def _key(p: str) -> tuple[int, int]:
    _, y, sub = parse_period(p)
    return y, sub


def aggregate(values: dict[str, float], rule: str, to: str) -> dict[str, float]:
    """Gộp chuỗi {kỳ: giá trị} (cùng một loại kỳ) lên loại kỳ `to`. Chỉ trả kỳ cha đủ kỳ con."""
    if rule not in RULES:
        raise ValueError(f"Quy tắc gộp không hợp lệ: {rule}")
    if not values:
        return {}
    src = period_type(next(iter(values)))
    need = CHILDREN[(src, to)]
    groups: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for p, v in values.items():
        if v is not None:
            groups[parent_of(p, to)].append((p, v))
    out = {}
    for parent, items in groups.items():
        if len(items) < need:
            continue
        items.sort(key=lambda kv: _key(kv[0]))
        vals = [v for _, v in items]
        out[parent] = sum(vals) if rule == "sum" else sum(vals) / len(vals) if rule == "avg" else vals[-1]
    return dict(sorted(out.items(), key=lambda kv: _key(kv[0])))


def window(values: dict[str, float | None], n: int | None) -> list[tuple[str, float | None]]:
    """N kỳ gần nhất (tính cả kỳ thiếu số liệu, trả None), kết thúc ở kỳ mới nhất có số liệu."""
    have = [p for p, v in values.items() if v is not None]
    if not have:
        return []
    have.sort(key=_key)
    full = period_range(have[0], have[-1])
    if n:
        full = full[-n:]
    return [(p, values.get(p)) for p in full]


def pct(new: float | None, old: float | None) -> float | None:
    if new is None or old is None or old == 0:
        return None
    return (new / old - 1) * 100


def changes(values: dict[str, float | None], rule: str | None = None) -> dict:
    """Mức thay đổi tại kỳ mới nhất có số liệu."""
    have = sorted((p for p, v in values.items() if v is not None), key=_key)
    if not have:
        return {"period": None, "value": None, "previous": None, "pop": None, "same_last_year": None, "yoy": None,
                "ytd": None, "ytd_last_year": None, "ytd_yoy": None}
    p = have[-1]
    t, year, sub = parse_period(p)
    prev, ly = previous(p), same_period_last_year(p)
    out = {"period": p, "value": values[p], "previous_period": prev, "previous": values.get(prev),
           "pop": pct(values[p], values.get(prev)), "same_period_last_year": ly,
           "same_last_year": values.get(ly), "yoy": pct(values[p], values.get(ly)),
           "ytd": None, "ytd_last_year": None, "ytd_yoy": None}
    if rule == "sum" and t != "Y":
        cur = [fmt_period(t, year, k) for k in range(1, sub + 1)]
        old = [fmt_period(t, year - 1, k) for k in range(1, sub + 1)]
        if all(values.get(x) is not None for x in cur):
            out["ytd"] = sum(values[x] for x in cur)
        if all(values.get(x) is not None for x in old):
            out["ytd_last_year"] = sum(values[x] for x in old)
        out["ytd_yoy"] = pct(out["ytd"], out["ytd_last_year"])
    return out
