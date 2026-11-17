"""
================================================================================
 XUẤT DỮ LIỆU JSON ĐẦY ĐỦ CHO DASHBOARD (export_dashboard_data.py)
 
 Tạo file matches_for_dashboard.json chứa đầy đủ:
 - Ảnh đại diện profile
 - Link hồ sơ gốc
 - Điểm 5 chiều & lý do logic
 - Câu chuyện gốc của cả 2 bên
================================================================================
"""

import csv
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRAPER_DIR = os.path.dirname(BASE_DIR)
OUTPUT_DIR = os.path.join(SCRAPER_DIR, "output")

from preprocessing import preprocess_profile
from matcher import CandidateFunnel, calculate_match_score

V2_CSV = os.path.join(OUTPUT_DIR, "haylentieng_v2.csv")
JSON_OUT = os.path.join(OUTPUT_DIR, "matches_for_dashboard.json")

def main():
    print("Reading haylentieng_v2.csv...")
    raw_rows = []
    with open(V2_CSV, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            raw_rows.append(r)

    print(f"Total rows: {len(raw_rows)}")
    profiles = []
    seen = set()
    for r in raw_rows:
        p = preprocess_profile(r)
        if p["id"] and p["id"] not in seen:
            seen.add(p["id"])
            profiles.append(p)

    funnel = CandidateFunnel(profiles)
    candidates = funnel.generate_candidate_pairs()
    by_id = {p["id"]: p for p in profiles}

    matches = []
    for id_a, id_b in candidates:
        pa = by_id[id_a]
        pb = by_id[id_b]
        res = calculate_match_score(pa, pb)
        score = res["final_score"]

        # Lấy các case >= 65% cho dashboard
        if score >= 65.0:
            matches.append({
                "id_a": id_a,
                "title_a": pa["title"],
                "name_a": pa["name"]["raw"],
                "birth_a": pa["birth_year"],
                "loc_a": pa["que_quan_raw"],
                "lost_a": pa["lost_year"],
                "link_a": pa["link"],
                "img_a": pa["image_url"],
                "father_a": pa["father"]["raw"],
                "mother_a": pa["mother"]["raw"],
                "story_a": pa["story"][:800],

                "id_b": id_b,
                "title_b": pb["title"],
                "name_b": pb["name"]["raw"],
                "birth_b": pb["birth_year"],
                "loc_b": pb["que_quan_raw"],
                "lost_b": pb["lost_year"],
                "link_b": pb["link"],
                "img_b": pb["image_url"],
                "father_b": pb["father"]["raw"],
                "mother_b": pb["mother"]["raw"],
                "story_b": pb["story"][:800],

                "score": score,
                "level": res["match_level"],
                "breakdown": {
                    "name": res["details"]["name"],
                    "birth": res["details"]["birth_year"],
                    "location": res["details"]["location"],
                    "lost": res["details"]["lost_year"],
                    "story": res["details"]["story"],
                    "bonus": res["bonus_relatives"],
                    "relatives_notes": res["details"]["relatives_notes"]
                }
            })

    matches.sort(key=lambda x: x["score"], reverse=True)
    print(f"Total qualified matches (>=65%): {len(matches)}")
    high_count = sum(1 for m in matches if m["score"] >= 80)
    print(f"High matches (>=80%): {high_count}")

    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump({
            "total_profiles": len(profiles),
            "total_matches": len(matches),
            "high_matches": high_count,
            "matches": matches
        }, f, ensure_ascii=False, indent=2)

    print(f"Saved to: {JSON_OUT}")

if __name__ == "__main__":
    main()
