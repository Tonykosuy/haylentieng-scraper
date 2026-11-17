"""
================================================================================
 AI MATCHING ENGINE & 4-TIER FUNNEL (matcher.py)
 
 Thiết kế chặt chẽ theo các quy tắc logic:
 - Tên người (35%): Đúng chỉ Tên = 50% điểm tên, Đúng cả Họ & Tên = 100% điểm tên.
 - Năm sinh (20%): Chênh lệch <= 2 năm.
 - Địa danh (20%): Đúng Tỉnh = 50% điểm địa danh, Đúng Xã/Phường/Quận/Huyện = 100% điểm địa danh (có tra cứu lịch sử).
 - Năm thất lạc (15%): Chênh lệch <= 2 năm.
 - Câu chuyện (10%): Trùng khớp từ khóa bối cảnh / ngữ nghĩa.
 - Bonus Cha / Mẹ (+15 điểm): Cross-reference tên cha, mẹ.
 - Phễu lọc 4 tầng: 3 năm thất lạc liên tiếp -> Năm sinh +-2 -> Khu vực địa lý -> Tên & Câu chuyện.
 - Đánh dấu các trường hợp Match Score >= 80%.
================================================================================
"""

from collections import defaultdict
from rapidfuzz import fuzz
from vietnam_admin_history import score_locations

# Trọng số chuẩn của 5 chiều đo lường
WEIGHT_NAME = 35.0
WEIGHT_BIRTH_YEAR = 20.0
WEIGHT_LOCATION = 20.0
WEIGHT_LOST_YEAR = 15.0
WEIGHT_STORY = 10.0

KEY_CONTEXT_TERMS = [
    "vuot bien", "thuyen", "nha thuong", "benh vien", "trai mo coi",
    "tan cu", "di cu", "bo doi", "quan gioi", "chay loan", "lac me",
    "lac cha", "cho", "ga tau", "ben xe", "con nuoi", "cho con"
]

def score_name(name_a: dict, name_b: dict) -> tuple[float, str]:
    """
    Tính điểm tên người theo quy tắc:
    - Đúng cả Họ và Tên: 100% (full điểm = 35đ)
    - Đúng chỉ Tên gọi (từ cuối): 50% (nửa điểm = 17.5đ)
    - Đúng Tên + 1 từ đệm/họ: 75%
    - Fuzzy match >= 85%: 60%
    - Fuzzy match 70-84%: 30%
    - Dưới 70%: 0 điểm
    """
    norm_a = name_a.get("norm", "")
    norm_b = name_b.get("norm", "")
    first_a = name_a.get("first_name", "")
    first_b = name_b.get("first_name", "")

    if not norm_a or not norm_b:
        return 20.0, "Thiếu dữ liệu tên"

    # 1. Trùng hoàn toàn cả họ và tên
    if norm_a == norm_b:
        return 100.0, "Đúng cả Họ và Tên hoàn toàn (100%)"

    # Kiểm tra cả tên bí danh nếu có
    for alias_a in name_a.get("aliases", []):
        if fuzz.ratio(alias_a.lower(), norm_b) >= 90:
            return 100.0, f"Trùng bí danh: {alias_a}"
    for alias_b in name_b.get("aliases", []):
        if fuzz.ratio(alias_b.lower(), norm_a) >= 90:
            return 100.0, f"Trùng bí danh: {alias_b}"

    # 2. So sánh tên gọi (từ cuối cùng)
    tokens_a = set(name_a.get("tokens", []))
    tokens_b = set(name_b.get("tokens", []))
    common_tokens = tokens_a.intersection(tokens_b)

    if first_a and first_b and first_a == first_b:
        if len(common_tokens) >= 2:
            return 75.0, f"Đúng Tên '{first_a}' + trùng từ khác trong họ đệm (75%)"
        return 50.0, f"Đúng chỉ Tên gọi '{first_a}' (50%)"

    # 3. Fuzzy matching tổng thể (bắt lỗi gõ, phiên âm)
    ratio = fuzz.ratio(norm_a, norm_b)
    token_sort = fuzz.token_sort_ratio(norm_a, norm_b)
    best_score = max(ratio, token_sort)

    if best_score >= 85:
        return 60.0, f"Fuzzy tên cao ({best_score:.0f}%)"
    elif best_score >= 70:
        return 30.0, f"Fuzzy tên trung bình ({best_score:.0f}%)"

    return 0.0, "Không khớp tên"


def score_birth_year(year_a: int | None, year_b: int | None) -> tuple[float, str]:
    """
    Năm sinh cho phép sai số +-2 năm:
    - 0 năm: 100%
    - 1 năm: 90%
    - 2 năm: 70%
    - 3 năm: 30%
    - >= 4 năm: 0%
    - Thiếu: 40% (trung lập)
    """
    if year_a is None or year_b is None:
        return 40.0, "Khuyết năm sinh (Điểm trung lập)"

    diff = abs(year_a - year_b)
    if diff == 0:
        return 100.0, f"Trùng năm sinh ({year_a})"
    elif diff == 1:
        return 90.0, f"Chênh lệch 1 năm ({year_a} vs {year_b})"
    elif diff == 2:
        return 70.0, f"Chênh lệch 2 năm ({year_a} vs {year_b})"
    elif diff == 3:
        return 30.0, f"Chênh lệch 3 năm ({year_a} vs {year_b})"
    else:
        return 0.0, f"Chênh lệch quá lớn ({diff} năm)"


def score_lost_year(year_a: int | None, year_b: int | None) -> tuple[float, str]:
    """
    Năm thất lạc (chênh lệch <= 2 năm):
    - 0 năm: 100%
    - 1 năm: 85%
    - 2 năm: 60%
    - >= 3 năm: 0%
    - Thiếu: 40% (trung lập)
    """
    if year_a is None or year_b is None:
        return 40.0, "Khuyết năm thất lạc (Điểm trung lập)"

    diff = abs(year_a - year_b)
    if diff == 0:
        return 100.0, f"Trùng năm thất lạc ({year_a})"
    elif diff == 1:
        return 85.0, f"Chênh lệch 1 năm ({year_a} vs {year_b})"
    elif diff == 2:
        return 60.0, f"Chênh lệch 2 năm ({year_a} vs {year_b})"
    else:
        return 0.0, f"Chênh lệch năm thất lạc ({diff} năm)"


def score_story_context(story_a: str, story_b: str) -> tuple[float, str]:
    """
    So sánh bối cảnh thất lạc trong câu chuyện:
    Trích xuất các từ khóa lịch sử/bối cảnh chung.
    """
    if not story_a or not story_b:
        return 20.0, "Không có nội dung câu chuyện"

    s_a = story_a.lower()
    s_b = story_b.lower()

    matched_keywords = []
    for term in KEY_CONTEXT_TERMS:
        if term in s_a and term in s_b:
            matched_keywords.append(term)

    if len(matched_keywords) >= 3:
        return 100.0, f"Trùng nhiều từ khóa bối cảnh ({', '.join(matched_keywords)})"
    elif len(matched_keywords) >= 1:
        return 60.0, f"Cùng bối cảnh ({', '.join(matched_keywords)})"

    # Token overlap tổng thể
    fuzz_val = fuzz.token_set_ratio(story_a[:400], story_b[:400])
    if fuzz_val >= 60:
        return 50.0, "Độ tương đồng nội dung vừa"

    return 10.0, "Bối cảnh khác biệt"


def check_relatives_cross_ref(prof_a: dict, prof_b: dict) -> tuple[float, list[str]]:
    """
    Kiểm tra chéo người thân (Cha, Mẹ):
    - Tên cha A trùng tên người B -> +15 điểm
    - Tên mẹ A trùng tên người B -> +15 điểm
    - Tên cha A trùng tên cha B -> +10 điểm
    - Tên mẹ A trùng tên mẹ B -> +10 điểm
    """
    bonus = 0.0
    notes = []

    name_a = prof_a["name"]["norm"]
    name_b = prof_b["name"]["norm"]
    fa_a = prof_a["father"]["norm"]
    fa_b = prof_b["father"]["norm"]
    mo_a = prof_a["mother"]["norm"]
    mo_b = prof_b["mother"]["norm"]

    # 1. Tên cha A trùng tên người được tìm B
    if fa_a and name_b and (fa_a == name_b or fuzz.ratio(fa_a, name_b) >= 85):
        bonus += 15.0
        notes.append(f"Tên cha A ('{prof_a['father']['raw']}') trùng tên người B ('{prof_b['name']['raw']}')")

    # 2. Tên cha B trùng tên người được tìm A
    if fa_b and name_a and (fa_b == name_a or fuzz.ratio(fa_b, name_a) >= 85):
        bonus += 15.0
        notes.append(f"Tên cha B ('{prof_b['father']['raw']}') trùng tên người A ('{prof_a['name']['raw']}')")

    # 3. Tên mẹ A trùng tên người B
    if mo_a and name_b and (mo_a == name_b or fuzz.ratio(mo_a, name_b) >= 85):
        bonus += 15.0
        notes.append(f"Tên mẹ A ('{prof_a['mother']['raw']}') trùng tên người B ('{prof_b['name']['raw']}')")

    # 4. Tên cha A trùng Tên cha B
    if fa_a and fa_b and (fa_a == fa_b or fuzz.ratio(fa_a, fa_b) >= 85):
        bonus += 10.0
        notes.append(f"Trùng tên cha: {prof_a['father']['raw']}")

    # 5. Tên mẹ A trùng Tên mẹ B
    if mo_a and mo_b and (mo_a == mo_b or fuzz.ratio(mo_a, mo_b) >= 85):
        bonus += 10.0
        notes.append(f"Trùng tên mẹ: {prof_a['mother']['raw']}")

    return min(25.0, bonus), notes


def calculate_match_score(prof_a: dict, prof_b: dict) -> dict:
    """
    Tính Match Score tổng hợp đầy đủ 5 chiều + Bonus chéo.
    """
    # 1. Tên người (35%)
    sc_name, note_name = score_name(prof_a["name"], prof_b["name"])

    # 2. Năm sinh (20%)
    sc_birth, note_birth = score_birth_year(prof_a["birth_year"], prof_b["birth_year"])

    # 3. Địa danh (20%)
    sc_loc = score_locations(prof_a["location"], prof_b["location"])
    if sc_loc >= 90:
        note_loc = "Trùng Xã/Phường/Quận/Huyện (hoặc tương đương lịch sử)"
    elif sc_loc >= 50:
        note_loc = "Trùng Tỉnh/Thành phố (hoặc giao nhau qua lịch sử sáp nhập)"
    elif sc_loc >= 20:
        note_loc = "Cùng vùng địa lý"
    elif sc_loc == 35:
        note_loc = "Khuyết địa danh (trung lập)"
    else:
        note_loc = "Khác địa danh"

    # 4. Năm thất lạc (15%)
    sc_lost, note_lost = score_lost_year(prof_a["lost_year"], prof_b["lost_year"])

    # 5. Câu chuyện (10%)
    sc_story, note_story = score_story_context(prof_a["story"], prof_b["story"])

    # Điểm thô có trọng số (0 - 100)
    raw_score = (
        (sc_name * (WEIGHT_NAME / 100.0)) +
        (sc_birth * (WEIGHT_BIRTH_YEAR / 100.0)) +
        (sc_loc * (WEIGHT_LOCATION / 100.0)) +
        (sc_lost * (WEIGHT_LOST_YEAR / 100.0)) +
        (sc_story * (WEIGHT_STORY / 100.0))
    )

    # Cross-reference Cha Mẹ
    bonus_relatives, notes_relatives = check_relatives_cross_ref(prof_a, prof_b)

    final_score = min(100.0, raw_score + bonus_relatives)

    # Phân loại Match Level
    if final_score >= 80.0:
        match_level = "HIGH_MATCH" # >= 80% có khả năng là người thân thất lạc
    elif final_score >= 65.0:
        match_level = "MEDIUM_MATCH"
    elif final_score >= 50.0:
        match_level = "LOW_MATCH"
    else:
        match_level = "NO_MATCH"

    return {
        "final_score": round(final_score, 1),
        "raw_score": round(raw_score, 1),
        "bonus_relatives": bonus_relatives,
        "match_level": match_level,
        "details": {
            "name": {"score": sc_name, "weighted": round(sc_name * 0.35, 1), "note": note_name},
            "birth_year": {"score": sc_birth, "weighted": round(sc_birth * 0.20, 1), "note": note_birth},
            "location": {"score": sc_loc, "weighted": round(sc_loc * 0.20, 1), "note": note_loc},
            "lost_year": {"score": sc_lost, "weighted": round(sc_lost * 0.15, 1), "note": note_lost},
            "story": {"score": sc_story, "weighted": round(sc_story * 0.10, 1), "note": note_story},
            "relatives_notes": notes_relatives
        }
    }


# ==============================================================================
# HÀNG PHỄU LỌC 4 TẦNG (4-TIER RETRIEVAL FUNNEL)
# ==============================================================================

class CandidateFunnel:
    """
    Phễu lọc 4 tầng:
    1. Nhóm theo 3 năm thất lạc liên tiếp (window +-1 năm).
    2. Lọc tiếp theo Năm sinh (+-2 năm).
    3. Lọc tiếp theo Địa danh (cùng huyện, tỉnh, vùng hoặc wildcard).
    4. Lọc sơ bộ Tên (trùng tên gọi hoặc fuzzy >= 65% hoặc có liên hệ cha/mẹ).
    """

    def __init__(self, profiles: list[dict]):
        self.profiles = profiles
        self.by_id = {p["id"]: p for p in profiles}

    def generate_candidate_pairs(self) -> set[tuple[str, str]]:
        candidate_pairs = set()

        # -------------------------------------------------------------
        # TẦNG 1: Nhóm theo Năm Thất Lạc (Window 3 năm)
        # -------------------------------------------------------------
        lost_buckets = defaultdict(list)
        unknown_lost = []

        for p in self.profiles:
            p_id = p["id"]
            if p["lost_year"] is not None:
                # Gán vào các năm trong window 3 năm: [Y-1, Y, Y+1]
                for yr in p["lost_windows"]:
                    lost_buckets[yr].append(p_id)
            else:
                unknown_lost.append(p_id)

        # Tạo các cặp sơ bộ từ Tầng 1
        tier1_pairs = set()
        for yr, p_ids in lost_buckets.items():
            n = len(p_ids)
            for i in range(n):
                for j in range(i + 1, n):
                    id_a, id_b = p_ids[i], p_ids[j]
                    if id_a != id_b:
                        pair = tuple(sorted([id_a, id_b]))
                        tier1_pairs.add(pair)

        # Các hồ sơ không rõ năm thất lạc: so với các hồ sơ khác nếu trùng tên
        # để không bỏ sót! (sẽ được lọc chặt ở tầng tên)

        # -------------------------------------------------------------
        # TẦNG 2 & 3 & 4: Lọc kết hợp Năm sinh, Địa danh và Tên
        # -------------------------------------------------------------
        for id_a, id_b in tier1_pairs:
            prof_a = self.by_id[id_a]
            prof_b = self.by_id[id_b]

            # Kiểm tra Tầng 2: Năm sinh (+-2 năm)
            by_a = prof_a["birth_year"]
            by_b = prof_b["birth_year"]
            if by_a is not None and by_b is not None:
                if abs(by_a - by_b) > 2:
                    continue # Bỏ qua nếu chênh lệch > 2 năm

            # Kiểm tra Tầng 3: Địa danh (loại nếu 2 bên đều có tỉnh nhưng hoàn toàn khác tỉnh/vùng)
            prov_a = prof_a["location"]["matched_provinces"]
            prov_b = prof_b["location"]["matched_provinces"]
            if prov_a and prov_b and not prov_a.intersection(prov_b):
                # Khác tỉnh, kiểm tra có cùng vùng không
                reg_a = prof_a["location"]["region_ids"]
                reg_b = prof_b["location"]["region_ids"]
                if reg_a and reg_b and not reg_a.intersection(reg_b):
                    # Nếu khác cả vùng, chỉ giữ nếu tên gọi trùng khớp hoàn toàn!
                    fn_a = prof_a["name"]["first_name"]
                    fn_b = prof_b["name"]["first_name"]
                    if not (fn_a and fn_b and fn_a == fn_b):
                        continue

            # Kiểm tra Tầng 4: Lọc sơ bộ Tên (bắt buộc có tên gọi trùng hoặc fuzzy >= 65% hoặc có liên hệ cha mẹ)
            fn_a = prof_a["name"]["first_name"]
            fn_b = prof_b["name"]["first_name"]
            norm_a = prof_a["name"]["norm"]
            norm_b = prof_b["name"]["norm"]

            # Có trùng tên gọi không?
            has_same_name = bool(fn_a and fn_b and fn_a == fn_b)
            # Có fuzzy tương đối không?
            has_fuzzy_name = bool(norm_a and norm_b and fuzz.ratio(norm_a, norm_b) >= 65)
            # Có liên hệ tên cha/mẹ không?
            has_relative_link = False
            if prof_a["father"]["norm"] and (prof_a["father"]["norm"] == norm_b):
                has_relative_link = True
            if prof_b["father"]["norm"] and (prof_b["father"]["norm"] == norm_a):
                has_relative_link = True

            if has_same_name or has_fuzzy_name or has_relative_link:
                candidate_pairs.add((id_a, id_b))

        return candidate_pairs
