"""Sinh file CSV tin tuyển dụng GIẢ LẬP để minh hoạ tiêu chí "nhu cầu nhân lực R&D/AI".

    uv run python -m scripts.generate_job_sample

Không crawl trang tuyển dụng thật (điều khoản sử dụng). Khi triển khai, thay file này bằng dữ liệu
được cấp phép (đối tác tuyển dụng, cơ quan thống kê lao động) cùng định dạng cột.
"""

import csv
import random

from app.external import JOBS_CSV

RD_TITLES = ["Kỹ sư AI/Machine Learning", "Kỹ sư thiết kế vi mạch (IC design)", "Nghiên cứu viên R&D vật liệu",
             "Data Scientist", "Kỹ sư phần mềm nhúng IoT", "Kỹ sư robot tự động hoá", "Kỹ sư kiểm thử bán dẫn"]
OTHER_TITLES = ["Nhân viên kinh doanh", "Kế toán tổng hợp", "Chuyên viên marketing", "Lập trình viên web",
                "Nhân viên chăm sóc khách hàng", "Kỹ sư xây dựng", "Chuyên viên nhân sự", "Lập trình viên mobile",
                "Quản lý cửa hàng", "Kỹ sư cơ khí"]
PROVINCES = ["Hà Nội", "TP. Hồ Chí Minh", "Đà Nẵng", "Bắc Ninh", "Hải Phòng", "Bình Dương", "Cần Thơ"]
# tỷ trọng tin R&D/AI tăng dần theo năm (giả lập)
RD_SHARE = {2021: 0.05, 2022: 0.06, 2023: 0.075, 2024: 0.09, 2025: 0.11}
PER_YEAR = 400


def main() -> None:
    rnd = random.Random(2026)
    JOBS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with JOBS_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "title", "company", "province", "posted_date", "skills", "note"])
        n = 0
        for year, share in RD_SHARE.items():
            for _ in range(PER_YEAR):
                n += 1
                rd = rnd.random() < share
                title = rnd.choice(RD_TITLES if rd else OTHER_TITLES)
                skills = "python, pytorch" if "AI" in title or "Data" in title else ("verilog" if "vi mạch" in title else "")
                w.writerow([f"JOB{n:05d}", title, f"Công ty giả lập {rnd.randint(1, 300)}", rnd.choice(PROVINCES),
                            f"{year}-{rnd.randint(1, 12):02d}-{rnd.randint(1, 28):02d}", skills, "GIẢ LẬP"])
    print(f"Đã ghi {n} tin tuyển dụng giả lập: {JOBS_CSV}")


if __name__ == "__main__":
    main()
