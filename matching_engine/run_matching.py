"""
================================================================================
 CHƯƠNG TRÌNH CHẠY MATCHING & XUẤT KẾT QUẢ (run_matching.py)
 
 Chạy toàn bộ quy trình:
 1. Đọc dữ liệu CSV từ haylentieng_v2.csv (hoặc test_v2.csv).
 2. Tiền xử lý & chuẩn hóa toàn bộ hồ sơ (tên, năm sinh, địa danh lịch sử, cha mẹ).
 3. Đưa qua Hàng Phễu Lọc 4 Tầng:
    - Tầng 1: Cửa sổ 3 năm thất lạc liên tiếp
    - Tầng 2: Năm sinh +-2 năm
    - Tầng 3: Khu vực địa lý & tra cứu lịch sử
    - Tầng 4: Tên gọi & người thân
 4. Chạy Scoring Engine tính điểm chi tiết 5 chiều.
 5. Lọc ra các case Match Score >= 80% (Người thân thất lạc tiềm năng).
 6. Xuất kết quả ra output/matches_found.csv và in báo cáo.
================================================================================
"""

import csv
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

from preprocessing import preprocess_profile
from matcher import CandidateFunnel, calculate_match_score

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRAPER_DIR = os.path.dirname(BASE_DIR)
OUTPUT_DIR = os.path.join(SCRAPER_DIR, "output")

# File dữ liệu đầu vào ưu tiên: haylentieng_v2.csv -> haylentieng_data.csv -> test_v2.csv
CANDIDATE_INPUTS = [
    os.path.join(OUTPUT_DIR, "haylentieng_v2.csv"),
    os.path.join(OUTPUT_DIR, "haylentieng_data.csv"),
    os.path.join(OUTPUT_DIR, "test_v2.csv")
]

MATCH_OUTPUT_FILE = os.path.join(OUTPUT_DIR, "matches_found.csv")


def load_input_profiles() -> tuple[str, list[dict]]:
    input_file = None
    for f in CANDIDATE_INPUTS:
        if os.path.exists(f) and os.path.getsize(f) > 100:
            input_file = f
            break

    if not input_file:
        print("❌ Không tìm thấy file dữ liệu CSV nào trong thư mục output!")
        sys.exit(1)

    print(f"📖 Đang đọc dữ liệu từ: {input_file}")
    raw_rows = []
    with open(input_file, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_rows.append(row)

    print(f"✅ Đã tải {len(raw_rows)} dòng dữ liệu thô.")
    return input_file, raw_rows


def main():
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║     HỆ THỐNG AI MATCHING — TÌM NGƯỜI THÂN THẤT LẠC (>= 80%)      ║")
    print("╚══════════════════════════════════════════════════════════════════╝\n")

    input_file, raw_rows = load_input_profiles()

    # BƯỚC 1: Tiền xử lý dữ liệu
    print("\n[1/4] Đang tiền xử lý & chuẩn hóa dữ liệu hồ sơ...")
    t0 = time.time()
    profiles = []
    seen_ids = set()
    for row in raw_rows:
        prof = preprocess_profile(row)
        # Bỏ qua dòng rỗng hoặc trùng lặp ID
        if prof["id"] and prof["id"] not in seen_ids:
            seen_ids.add(prof["id"])
            profiles.append(prof)
        elif not prof["id"] and prof["title"]:
            prof["id"] = f"ROW_{len(profiles)+1}"
            profiles.append(prof)

    print(f"  → Hoàn tất chuẩn hóa {len(profiles)} hồ sơ ({time.time() - t0:.2f}s).")

    # BƯỚC 2: Phễu lọc 4 tầng
    print("\n[2/4] Đang khởi chạy HÀNG PHỄU LỌC 4 TẦNG...")
    print("  - Tầng 1: Nhóm theo cửa sổ 3 năm thất lạc liên tiếp")
    print("  - Tầng 2: Thu hẹp theo năm sinh (+-2 năm)")
    print("  - Tầng 3: Đối chiếu địa danh & phân vùng lịch sử")
    print("  - Tầng 4: Sàng lọc tên gọi & liên hệ thân nhân")

    t1 = time.time()
    funnel = CandidateFunnel(profiles)
    candidate_pairs = funnel.generate_candidate_pairs()
    print(f"  → Phễu đã thu hẹp thành công còn {len(candidate_pairs)} cặp ứng viên triển vọng ({time.time() - t1:.2f}s).")

    # BƯỚC 3: Tính điểm Matching chi tiết 5 chiều
    print("\n[3/4] Đang tính Match Score chi tiết 5 chiều cho các cặp ứng viên...")
    t2 = time.time()
    by_id = {p["id"]: p for p in profiles}

    matches_high = []
    matches_medium = []
    all_scored = []

    for id_a, id_b in candidate_pairs:
        prof_a = by_id[id_a]
        prof_b = by_id[id_b]

        result = calculate_match_score(prof_a, prof_b)
        score = result["final_score"]

        match_record = {
            "id_a": id_a,
            "title_a": prof_a["title"],
            "name_a": prof_a["name"]["raw"],
            "birth_a": prof_a["birth_year"] or "",
            "loc_a": prof_a["que_quan_raw"],
            "lost_a": prof_a["lost_year"] or "",
            "link_a": prof_a["link"],

            "id_b": id_b,
            "title_b": prof_b["title"],
            "name_b": prof_b["name"]["raw"],
            "birth_b": prof_b["birth_year"] or "",
            "loc_b": prof_b["que_quan_raw"],
            "lost_b": prof_b["lost_year"] or "",
            "link_b": prof_b["link"],

            "final_score": score,
            "level": result["match_level"],
            "score_name": result["details"]["name"]["weighted"],
            "score_birth": result["details"]["birth_year"]["weighted"],
            "score_loc": result["details"]["location"]["weighted"],
            "score_lost": result["details"]["lost_year"]["weighted"],
            "score_story": result["details"]["story"]["weighted"],
            "bonus_relatives": result["bonus_relatives"],
            "notes": " | ".join(filter(None, [
                result["details"]["name"]["note"],
                result["details"]["birth_year"]["note"],
                result["details"]["location"]["note"],
                result["details"]["lost_year"]["note"],
                ", ".join(result["details"]["relatives_notes"])
            ]))
        }

        if score >= 80.0:
            matches_high.append(match_record)
        elif score >= 65.0:
            matches_medium.append(match_record)

        if score >= 50.0:
            all_scored.append(match_record)

    # Sắp xếp theo điểm giảm dần
    matches_high.sort(key=lambda x: x["final_score"], reverse=True)
    matches_medium.sort(key=lambda x: x["final_score"], reverse=True)
    all_scored.sort(key=lambda x: x["final_score"], reverse=True)

    print(f"  → Hoàn tất chấm điểm ({time.time() - t2:.2f}s).")
    print(f"  🔥 TÌM THẤY {len(matches_high)} CẶP HIGH MATCH (>= 80% KHẢ NĂNG LÀ NGƯỜI THÂN)!")
    print(f"  ⚡ TÌM THẤY {len(matches_medium)} CẶP MEDIUM MATCH (65% - 79%)!")

    # BƯỚC 4: Xuất file CSV kết quả
    print("\n[4/4] Đang xuất báo cáo kết quả ra file CSV...")
    fieldnames = [
        "Mức độ", "Match Score (%)", "Mã số A", "Họ tên A", "Năm sinh A", "Quê quán A", "Năm thất lạc A", "Link A",
        "Mã số B", "Họ tên B", "Năm sinh B", "Quê quán B", "Năm thất lạc B", "Link B",
        "Điểm Tên (35đ)", "Điểm Năm sinh (20đ)", "Điểm Địa danh (20đ)", "Điểm Thất lạc (15đ)", "Điểm Bối cảnh (10đ)",
        "Bonus Thân nhân", "Chi tiết phân tích logic"
    ]

    with open(MATCH_OUTPUT_FILE, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        for m in all_scored:
            writer.writerow([
                m["level"],
                f"{m['final_score']}%",
                m["id_a"], m["name_a"], m["birth_a"], m["loc_a"], m["lost_a"], m["link_a"],
                m["id_b"], m["name_b"], m["birth_b"], m["loc_b"], m["lost_b"], m["link_b"],
                m["score_name"], m["score_birth"], m["score_loc"], m["score_lost"], m["score_story"],
                m["bonus_relatives"], m["notes"]
            ])

    print(f"✅ Đã lưu toàn bộ kết quả vào: {MATCH_OUTPUT_FILE}")

    # In các cặp High Match nổi bật
    if matches_high:
        print("\n" + "=" * 75)
        print(" DANH SÁCH CÁC CẶP TRÙNG KHỚP CAO NHẤT (>= 80%):")
        print("=" * 75)
        for idx, m in enumerate(matches_high[:15], 1):
            print(f"\n[{idx}] MATCH SCORE: {m['final_score']}%")
            print(f"  • Hồ sơ 1: [{m['id_a']}] {m['name_a']} (Sinh: {m['birth_a']} | Thất lạc: {m['lost_a']} | {m['loc_a']})")
            print(f"    Link: {m['link_a']}")
            print(f"  • Hồ sơ 2: [{m['id_b']}] {m['name_b']} (Sinh: {m['birth_b']} | Thất lạc: {m['lost_b']} | {m['loc_b']})")
            print(f"    Link: {m['link_b']}")
            print(f"  • Logic trùng khớp: {m['notes']}")
        print("\n" + "=" * 75)


if __name__ == "__main__":
    main()
