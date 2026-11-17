"""
================================================================================
 TIỀN XỬ LÝ & CHUẨN HÓA DỮ LIỆU HỒ SƠ (preprocessing.py)
 
 Nhiệm vụ:
 - Chuẩn hóa họ tên, bóc tách Tên, Họ, Tên đệm, lọc bỏ đại từ xưng hô (ông, bà...).
 - Trích xuất Năm sinh, Năm thất lạc (dạng số nguyên int).
 - Chuẩn hóa Quê quán / Địa danh và gán vùng địa lý thông qua vietnam_admin_history.
 - Chuẩn hóa tên Cha, Mẹ để phục vụ Cross-reference matching.
 - Gán các cửa sổ thời gian (sliding window) để đưa vào phễu lọc 4 tầng.
================================================================================
"""

import re
from unidecode import unidecode
from vietnam_admin_history import parse_and_resolve_location, strip_accents

HONORIFICS = [
    r"^ong\s+", r"^ba\s+", r"^anh\s+", r"^chi\s+", r"^em\s+",
    r"^cu\s+", r"^bac\s+", r"^chu\s+", r"^co\s+", r"^thay\s+"
]

def clean_vietnamese_name(raw_name: str) -> dict:
    """
    Chuẩn hóa tên người:
    - Bóc tách tên trong ngoặc (bí danh/tên gọi khác) nếu có.
    - Lược bỏ từ xưng hô (ông, bà, anh, chị, cụ...).
    - Trích xuất: full_norm, first_name (tên gọi - từ cuối), last_name (họ - từ đầu), middle_name.
    """
    if not raw_name or not raw_name.strip():
        return {
            "raw": "",
            "clean_raw": "",
            "norm": "",
            "first_name": "",  # Tên gọi (từ cuối cùng)
            "last_name": "",   # Họ (từ đầu tiên)
            "middle_name": "", # Tên đệm
            "tokens": [],
            "aliases": []
        }

    raw = raw_name.strip()
    
    # Kiểm tra tên bí danh trong ngoặc: ví dụ "Liam Guigues (Trần Văn Hùng)"
    aliases = []
    alias_match = re.findall(r"\(([^)]+)\)", raw)
    for a in alias_match:
        aliases.append(a.strip())
    
    # Chuỗi chính (bỏ ngoặc)
    main_name = re.sub(r"\([^)]*\)", " ", raw)
    main_name = " ".join(main_name.split()).strip()

    # Bỏ dấu & lowercase để chuẩn hóa
    norm = strip_accents(main_name)

    # Lược bỏ các từ xưng hô ở đầu tên
    for pattern in HONORIFICS:
        norm = re.sub(pattern, "", norm).strip()

    tokens = norm.split()

    first_name = tokens[-1] if len(tokens) >= 1 else ""
    last_name = tokens[0] if len(tokens) >= 2 else ""
    middle_name = " ".join(tokens[1:-1]) if len(tokens) >= 3 else ""

    return {
        "raw": raw,
        "clean_raw": main_name,
        "norm": norm,
        "first_name": first_name,
        "last_name": last_name,
        "middle_name": middle_name,
        "tokens": tokens,
        "aliases": aliases
    }


def parse_year(raw_year: str) -> int | None:
    """
    Trích xuất năm 4 chữ số (1800 - 2030) từ chuỗi tự do:
    '1940', 'khoảng 1945', 'sinh năm 1950', '~1952', '1954-1955' -> int
    """
    if not raw_year or not str(raw_year).strip():
        return None
    matches = re.findall(r"\b(18\d{2}|19\d{2}|20[0-2]\d)\b", str(raw_year))
    if matches:
        return int(matches[0])
    return None


def preprocess_profile(raw_row: dict) -> dict:
    """
    Tiền xử lý toàn diện 1 hồ sơ từ dòng CSV.
    """
    ma_so = raw_row.get("Mã số", "").strip()
    tieu_de = raw_row.get("Tiêu đề", "").strip()
    ho_ten_raw = raw_row.get("Họ và tên", "").strip()
    
    # Nếu trường Họ và tên rỗng, thử trích xuất từ tiêu đề
    if not ho_ten_raw and tieu_de:
        m = re.search(r"(?:tìm|về)\s+(?:cha|mẹ|anh|chị|em|con|chú|bác|ông|bà|người thân)?\s*([A-ZÀ-Ỹa-zà-ỹ\s]+)", tieu_de)
        if m:
            ho_ten_raw = m.group(1).strip()

    # 1. Họ và tên
    name_info = clean_vietnamese_name(ho_ten_raw)

    # 2. Năm sinh & Năm thất lạc
    birth_year = parse_year(raw_row.get("Năm sinh", ""))
    lost_year = parse_year(raw_row.get("Năm thất lạc", ""))

    # 3. Quê quán & Địa danh
    que_quan_raw = raw_row.get("Quê quán", "").strip()
    story_raw = raw_row.get("Câu chuyện đầy đủ", "").strip()

    # Phân tích địa danh từ cột Quê quán
    location_info = parse_and_resolve_location(que_quan_raw)

    # Nếu quê quán không có địa danh, thử tìm trong câu chuyện (đặc biệt các tỉnh/huyện)
    if not location_info["matched_provinces"] and story_raw:
        story_loc = parse_and_resolve_location(story_raw[:300]) # 300 ký tự đầu thường chứa quê quán
        if story_loc["matched_provinces"]:
            location_info["matched_provinces"].update(story_loc["matched_provinces"])
            location_info["region_ids"].update(story_loc["region_ids"])

    # 4. Tên Cha & Mẹ (chuẩn hóa để phục vụ Cross-reference)
    father_name = clean_vietnamese_name(raw_row.get("Tên cha", "").strip())
    mother_name = clean_vietnamese_name(raw_row.get("Tên mẹ", "").strip())

    # 5. Thiết lập Cửa sổ (Sliding Windows) cho Phễu lọc
    # Cửa sổ Năm thất lạc: [Y-1, Y, Y+1]
    lost_windows = [lost_year - 1, lost_year, lost_year + 1] if lost_year else []

    # Cửa sổ Năm sinh: [B-2, B-1, B, B+1, B+2]
    birth_windows = [birth_year + i for i in range(-2, 3)] if birth_year else []

    return {
        "id": ma_so,
        "title": tieu_de,
        "link": raw_row.get("Link chi tiết", "").strip(),
        "image_url": raw_row.get("URL hình ảnh", "").strip(),
        "story": story_raw,
        
        # Họ tên
        "name": name_info,
        
        # Năm
        "birth_year": birth_year,
        "birth_windows": birth_windows,
        "lost_year": lost_year,
        "lost_windows": lost_windows,

        # Địa danh
        "location": location_info,
        "que_quan_raw": que_quan_raw,

        # Người thân
        "father": father_name,
        "mother": mother_name,
    }
