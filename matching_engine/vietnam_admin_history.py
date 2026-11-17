"""
================================================================================
 CƠ SỞ DỮ LIỆU ĐỊA DANH LỊCH SỬ VIỆT NAM (vietnam_admin_history.py)
 Thời kỳ: Trước 1975, 1980, 1990, 2000, 2005, 2010, 2015 -> Hiện tại
 
 Mục đích:
 - Ánh xạ địa danh cũ/lịch sử (tỉnh sáp nhập, huyện chia tách) về địa danh hiện tại.
 - Hỗ trợ tính điểm địa danh chuẩn xác:
   * Đúng Tỉnh: Nửa điểm (50 điểm).
   * Đúng Xã / Phường / Thị trấn / Quận / Huyện: Full điểm (100 điểm).
================================================================================
"""

import re
import unicodedata
from unidecode import unidecode
from rapidfuzz import fuzz

def strip_accents(text: str) -> str:
    if not text:
        return ""
    return unidecode(text).lower().strip()

# ==============================================================================
# 1. BẢNG ÁNH XẠ TỈNH CŨ / LỊCH SỬ -> CÁC TỈNH HIỆN TẠI
# ==============================================================================
HISTORICAL_PROVINCES = {
    # Miền Bắc & Bắc Trung Bộ (Sáp nhập sau 1975-1976 -> Tách 1991/1996/2004/2008)
    "ha nam ninh": ["Ha Nam", "Nam Dinh", "Ninh Binh"],
    "ha son binh": ["Ha Noi", "Hoa Binh"],               # Hà Tây + Hòa Bình, Hà Tây sau sáp nhập vào Hà Nội
    "ha tay": ["Ha Noi"],                                 # Sáp nhập vào Hà Nội năm 2008
    "vinh phu": ["Vinh Phuc", "Phu Tho"],
    "ha bac": ["Bac Giang", "Bac Ninh"],
    "bac thai": ["Thai Nguyen", "Bac Kan"],
    "cao lang": ["Cao Bang", "Lang Son"],
    "hoang lien son": ["Lao Cai", "Yen Bai"],
    "lai chau cu": ["Lai Chau", "Dien Bien"],             # Tách tỉnh Điện Biên năm 2004
    "hai hung": ["Hai Duong", "Hung Yen"],
    "binh tri thien": ["Quang Binh", "Quang Tri", "Thua Thien Hue"],

    # Miền Trung & Tây Nguyên
    "nghia binh": ["Quang Ngai", "Binh Dinh"],
    "phu khanh": ["Phu Yen", "Khanh Hoa"],
    "thuan hai": ["Ninh Thuan", "Binh Thuan"],
    "gia lai - kon tum": ["Gia Lai", "Kon Tum"],
    "gia lai kon tum": ["Gia Lai", "Kon Tum"],
    "dak lak cu": ["Dak Lak", "Dak Nong"],                # Tách Đắk Nông năm 2004
    "dac lac": ["Dak Lak", "Dak Nong"],
    "quang tin": ["Quang Nam"],                           # Tỉnh cũ trước 1975
    "quang duc": ["Dak Nong"],                            # Tỉnh cũ trước 1975
    "tuyen duc": ["Lam Dong"],                            # Tỉnh cũ trước 1975
    "pleiku": ["Gia Lai"],
    "darlac": ["Dak Lak"],

    # Miền Đông & Tây Nam Bộ
    "song be": ["Binh Duong", "Binh Phuoc"],
    "minh hai": ["Ca Mau", "Bac Lieu"],
    "cuu long": ["Vinh Long", "Tra Vinh"],
    "hau giang cu": ["Can Tho", "Hau Giang", "Soc Trang"], # Hậu Giang cũ trước 1991 tách Cần Thơ, Sóc Trăng, sau đó 2004 Cần Thơ tách Hậu Giang
    "dong nai cu": ["Dong Nai", "Binh Duong", "Binh Phuoc", "Ba Ria - Vung Tau"],
    "sai gon": ["TP Ho Chi Minh"],
    "gia dinh": ["TP Ho Chi Minh"],
    "sai gon - gia dinh": ["TP Ho Chi Minh"],
    "bien hoa": ["Dong Nai"],                             # Trước 1975
    "long khanh": ["Dong Nai"],                           # Trước 1975
    "phuoc tuy": ["Ba Ria - Vung Tau"],                   # Trước 1975
    "binh tuy": ["Binh Thuan"],                           # Trước 1975
    "dinh tuong": ["Tien Giang"],                         # Trước 1975
    "go cong": ["Tien Giang"],                            # Trước 1975
    "kien hoa": ["Ben Tre"],                              # Trước 1975
    "vinh binh": ["Tra Vinh"],                            # Trước 1975
    "sa dec": ["Dong Thap"],                              # Trước 1975
    "kien phong": ["Dong Thap"],                          # Trước 1975
    "kien tuong": ["Long An"],                            # Trước 1975
    "hau nghia": ["Long An", "Tay Ninh", "TP Ho Chi Minh"], # Trước 1975
    "phong dinh": ["Can Tho"],                            # Trước 1975
    "ba xuyen": ["Soc Trang"],                            # Trước 1975
    "chuong thien": ["Hau Giang", "Kien Giang"],          # Trước 1975
    "an xuyen": ["Ca Mau"],                               # Trước 1975
    "rach gia": ["Kien Giang"],                           # Trước 1975
    "ha tien": ["Kien Giang"],                            # Trước 1975
    "chau doc": ["An Giang"],                             # Trước 1975
    "long xuyen": ["An Giang"],                           # Trước 1975
}

# 63 Tỉnh Thành Hiện Tại của Việt Nam (dạng chuẩn hóa không dấu và có dấu)
CURRENT_PROVINCES = [
    "An Giang", "Ba Ria - Vung Tau", "Bac Giang", "Bac Kan", "Bac Lieu", "Bac Ninh",
    "Ben Tre", "Binh Dinh", "Binh Duong", "Binh Phuoc", "Binh Thuan", "Ca Mau",
    "Can Tho", "Cao Bang", "Da Nang", "Dak Lak", "Dak Nong", "Dien Bien",
    "Dong Nai", "Dong Thap", "Gia Lai", "Ha Giang", "Ha Nam", "Ha Noi",
    "Ha Tinh", "Hai Duong", "Hai Phong", "Hau Giang", "Hoa Binh", "Hung Yen",
    "Khanh Hoa", "Kien Giang", "Kon Tum", "Lai Chau", "Lam Dong", "Lang Son",
    "Lao Cai", "Long An", "Nam Dinh", "Nghe An", "Ninh Binh", "Ninh Thuan",
    "Phu Tho", "Phu Yen", "Quang Binh", "Quang Nam", "Quang Ngai", "Quang Ninh",
    "Quang Tri", "Soc Trang", "Son La", "Tay Ninh", "Thai Binh", "Thai Nguyen",
    "Thanh Hoa", "Thua Thien Hue", "Tien Giang", "TP Ho Chi Minh", "Tra Vinh",
    "Tuyen Quang", "Vinh Long", "Vinh Phuc", "Yen Bai"
]

# Map unidecode tên tỉnh -> Tên chính thức
PROVINCE_NORM_MAP = {strip_accents(p): p for p in CURRENT_PROVINCES}
PROVINCE_NORM_MAP["sai gon"] = "TP Ho Chi Minh"
PROVINCE_NORM_MAP["tp ho chi minh"] = "TP Ho Chi Minh"
PROVINCE_NORM_MAP["tphcm"] = "TP Ho Chi Minh"
PROVINCE_NORM_MAP["ho chi minh"] = "TP Ho Chi Minh"
PROVINCE_NORM_MAP["ha tay"] = "Ha Noi"
PROVINCE_NORM_MAP["thua thien - hue"] = "Thua Thien Hue"
PROVINCE_NORM_MAP["hue"] = "Thua Thien Hue"
PROVINCE_NORM_MAP["vung tau"] = "Ba Ria - Vung Tau"
PROVINCE_NORM_MAP["ba ria vung tau"] = "Ba Ria - Vung Tau"

# ==============================================================================
# 2. BẢNG ÁNH XẠ CẤP HUYỆN LỊCH SỬ -> CÁC HUYỆN/THỊ XÃ HIỆN TẠI VÀ TỈNH TƯƠNG ỨNG
# ==============================================================================
HISTORICAL_DISTRICTS = {
    # --- Hà Nam Ninh (Ninh Bình, Nam Định, Hà Nam) ---
    "hoang long": {
        "current_districts": ["Nho Quan", "Gia Vien"],
        "provinces": ["Ninh Binh"],
        "note": "Huyện Hoàng Long tách thành Nho Quan và Gia Viễn (1991)"
    },
    "tam diep": {
        "current_districts": ["Yen Mo", "Yen Khanh", "Tam Diep"],
        "provinces": ["Ninh Binh"],
        "note": "Huyện Tam Điệp cũ bao gồm Yên Mô, Yên Khánh và TP Tam Điệp"
    },
    "hoa lu": {
        "current_districts": ["Hoa Lu"],
        "provinces": ["Ninh Binh"]
    },
    "kim son": {
        "current_districts": ["Kim Son"],
        "provinces": ["Ninh Binh"]
    },
    "xuan thuy": {
        "current_districts": ["Xuan Truong", "Giao Thuy"],
        "provinces": ["Nam Dinh"],
        "note": "Huyện Xuân Thủy tách thành Xuân Trường và Giao Thủy (1997)"
    },
    "nam ninh": {
        "current_districts": ["Nam Truc", "Truc Ninh"],
        "provinces": ["Nam Dinh"],
        "note": "Huyện Nam Ninh tách thành Nam Trực và Trực Ninh (1997)"
    },
    "hai hau": {
        "current_districts": ["Hai Hau"],
        "provinces": ["Nam Dinh"]
    },
    "nghia hung": {
        "current_districts": ["Nghia Hung"],
        "provinces": ["Nam Dinh"]
    },
    "binh luc": {
        "current_districts": ["Binh Luc"],
        "provinces": ["Ha Nam"]
    },
    "thanh liem": {
        "current_districts": ["Thanh Liem"],
        "provinces": ["Ha Nam"]
    },
    "kim bang": {
        "current_districts": ["Kim Bang"],
        "provinces": ["Ha Nam"]
    },
    "duy tien": {
        "current_districts": ["Duy Tien"],
        "provinces": ["Ha Nam"]
    },
    "ly nhan": {
        "current_districts": ["Ly Nhan"],
        "provinces": ["Ha Nam"]
    },
    "tx ha nam": {
        "current_districts": ["Phu Ly"],
        "provinces": ["Ha Nam"]
    },
    "phu ly": {
        "current_districts": ["Phu Ly"],
        "provinces": ["Ha Nam"]
    },
    "tx nam dinh": {
        "current_districts": ["Nam Dinh"],
        "provinces": ["Nam Dinh"]
    },
    "tx ninh binh": {
        "current_districts": ["Ninh Binh"],
        "provinces": ["Ninh Binh"]
    },

    # --- Hà Sơn Bình / Hà Tây / Hà Nội ---
    "hoai duc": {
        "current_districts": ["Hoai Duc", "Dan Phuong"],
        "provinces": ["Ha Noi"]
    },
    "quoc oai": {
        "current_districts": ["Quoc Oai"],
        "provinces": ["Ha Noi"]
    },
    "thach that": {
        "current_districts": ["Thach That"],
        "provinces": ["Ha Noi"]
    },
    "chuong my": {
        "current_districts": ["Chuong My"],
        "provinces": ["Ha Noi"]
    },
    "thanh oai": {
        "current_districts": ["Thanh Oai"],
        "provinces": ["Ha Noi"]
    },
    "ung hoa": {
        "current_districts": ["Ung Hoa"],
        "provinces": ["Ha Noi"]
    },
    "my duc": {
        "current_districts": ["My Duc"],
        "provinces": ["Ha Noi"]
    },
    "thuong tin": {
        "current_districts": ["Thuong Tin"],
        "provinces": ["Ha Noi"]
    },
    "phu xuyen": {
        "current_districts": ["Phu Xuyen"],
        "provinces": ["Ha Noi"]
    },
    "ha dong": {
        "current_districts": ["Ha Dong"],
        "provinces": ["Ha Noi"]
    },
    "son tay": {
        "current_districts": ["Son Tay"],
        "provinces": ["Ha Noi"]
    },
    "ba vi": {
        "current_districts": ["Ba Vi"],
        "provinces": ["Ha Noi"]
    },
    "phuc tho": {
        "current_districts": ["Phuc Tho"],
        "provinces": ["Ha Noi"]
    },
    "me linh": {
        "current_districts": ["Me Linh"],
        "provinces": ["Ha Noi"]
    },
    "soc son": {
        "current_districts": ["Soc Son"],
        "provinces": ["Ha Noi"]
    },
    "dong anh": {
        "current_districts": ["Dong Anh"],
        "provinces": ["Ha Noi"]
    },
    "gia lam": {
        "current_districts": ["Gia Lam", "Long Bien"],
        "provinces": ["Ha Noi"]
    },
    "thanh tri": {
        "current_districts": ["Thanh Tri", "Hoang Mai"],
        "provinces": ["Ha Noi"]
    },
    "tu liem": {
        "current_districts": ["Bac Tu Liem", "Nam Tu Liem", "Cau Giay"],
        "provinces": ["Ha Noi"]
    },

    # --- Vĩnh Phú (Vĩnh Phúc & Phú Thọ) ---
    "phong chau": {
        "current_districts": ["Lam Thao", "Phu Ninh"],
        "provinces": ["Phu Tho"]
    },
    "song thao": {
        "current_districts": ["Cam Khe", "Ha Hoa", "Yen Lap"],
        "provinces": ["Phu Tho"]
    },
    "tam thanh": {
        "current_districts": ["Thanh Ba", "Tam Nong", "Thanh Thuy"],
        "provinces": ["Phu Tho"]
    },
    "vinh tuong": {
        "current_districts": ["Vinh Tuong", "Yen Lac"],
        "provinces": ["Vinh Phuc"]
    },
    "lap thach": {
        "current_districts": ["Lap Thach", "Song Lo"],
        "provinces": ["Vinh Phuc"]
    },
    "tam dao": {
        "current_districts": ["Tam Dao", "Binh Xuyen"],
        "provinces": ["Vinh Phuc"]
    },

    # --- Hải Hưng (Hải Dương & Hưng Yên) ---
    "kim mon": {
        "current_districts": ["Kim Thanh", "Kinh Mon"],
        "provinces": ["Hai Duong"]
    },
    "tu loc": {
        "current_districts": ["Tu Ky", "Gia Loc"],
        "provinces": ["Hai Duong"]
    },
    "ninh thanh": {
        "current_districts": ["Ninh Giang", "Thanh Mien"],
        "provinces": ["Hai Duong"]
    },
    "cam binh": {
        "current_districts": ["Cam Giang", "Binh Giang"],
        "provinces": ["Hai Duong"]
    },
    "chau giang": {
        "current_districts": ["Khoai Chau", "Van Giang"],
        "provinces": ["Hung Yen"]
    },
    "my van": {
        "current_districts": ["My Hao", "Van Lam", "Yen My"],
        "provinces": ["Hung Yen"]
    },
    "kim thi": {
        "current_districts": ["Kim Dong", "An Thi"],
        "provinces": ["Hung Yen"]
    },
    "phu tien": {
        "current_districts": ["Phu Cu", "Tien Lu"],
        "provinces": ["Hung Yen"]
    },

    # --- Bình Trị Thiên (Quảng Bình, Quảng Trị, TT-Huế) ---
    "ben hai": {
        "current_districts": ["Vinh Linh", "Gio Linh", "Cam Lo"],
        "provinces": ["Quang Tri"]
    },
    "trieu hai": {
        "current_districts": ["Trieu Phong", "Hai Lang", "Quang Tri"],
        "provinces": ["Quang Tri"]
    },
    "huong phu": {
        "current_districts": ["Huong Thuy", "Phu Vang"],
        "provinces": ["Thua Thien Hue"]
    },
    "huong dien": {
        "current_districts": ["Huong Tra", "Phong Dien", "Quang Dien"],
        "provinces": ["Thua Thien Hue"]
    },
    "le ninh": {
        "current_districts": ["Le Thuy", "Quang Ninh"],
        "provinces": ["Quang Binh"]
    },

    # --- Nghĩa Bình (Bình Định & Quảng Ngãi) ---
    "hoai nhon": {
        "current_districts": ["Hoai Nhon"],
        "provinces": ["Binh Dinh"]
    },
    "an nhon": {
        "current_districts": ["An Nhon"],
        "provinces": ["Binh Dinh"]
    },
    "tuy phuoc": {
        "current_districts": ["Tuy Phuoc"],
        "provinces": ["Binh Dinh"]
    },
    "phu cat": {
        "current_districts": ["Phu Cat"],
        "provinces": ["Binh Dinh"]
    },
    "phu my": {
        "current_districts": ["Phu My"],
        "provinces": ["Binh Dinh"]
    },
    "tay son": {
        "current_districts": ["Tay Son"],
        "provinces": ["Binh Dinh"]
    },
    "duc pho": {
        "current_districts": ["Duc Pho"],
        "provinces": ["Quang Ngai"]
    },
    "mo duc": {
        "current_districts": ["Mo Duc"],
        "provinces": ["Quang Ngai"]
    },
    "binh son": {
        "current_districts": ["Binh Son"],
        "provinces": ["Quang Ngai"]
    },
    "son tinh": {
        "current_districts": ["Son Tinh"],
        "provinces": ["Quang Ngai"]
    },

    # --- Minh Hải (Cà Mau & Bạc Liêu) ---
    "thoi binh": {
        "current_districts": ["Thoi Binh"],
        "provinces": ["Ca Mau"]
    },
    "tran van thoi": {
        "current_districts": ["Tran Van Thoi"],
        "provinces": ["Ca Mau"]
    },
    "cai nuoc": {
        "current_districts": ["Cai Nuoc", "Phu Tan"],
        "provinces": ["Ca Mau"]
    },
    "dam doi": {
        "current_districts": ["Dam Doi"],
        "provinces": ["Ca Mau"]
    },
    "ngoc hien": {
        "current_districts": ["Ngoc Hien", "Nam Can"],
        "provinces": ["Ca Mau"]
    },
    "vinh loi": {
        "current_districts": ["Vinh Loi", "Hoa Binh"],
        "provinces": ["Bac Lieu"]
    },
    "gia rai": {
        "current_districts": ["Gia Rai", "Dong Hai"],
        "provinces": ["Bac Lieu"]
    },
    "hong dan": {
        "current_districts": ["Hong Dan", "Phuoc Long"],
        "provinces": ["Bac Lieu"]
    },

    # --- Sông Bé (Bình Dương & Bình Phước) ---
    "thuan an": {
        "current_districts": ["Thuan An", "Di An"],
        "provinces": ["Binh Duong"]
    },
    "ben cat": {
        "current_districts": ["Ben Cat", "Bau Bang"],
        "provinces": ["Binh Duong"]
    },
    "tan uyen": {
        "current_districts": ["Tan Uyen", "Bac Tan Uyen"],
        "provinces": ["Binh Duong"]
    },
    "dong phu": {
        "current_districts": ["Dong Phu", "Dong Xoai"],
        "provinces": ["Binh Phuoc"]
    },
    "binh long": {
        "current_districts": ["Binh Long", "Hon Quan", "Chon Thanh"],
        "provinces": ["Binh Phuoc"]
    },
    "phuoc long": {
        "current_districts": ["Phuoc Long", "Bu Gia Map", "Phu Rieng"],
        "provinces": ["Binh Phuoc"]
    },

    # --- Sài Gòn / Gia Định / TP.HCM ---
    "thu duc": {
        "current_districts": ["Thu Duc", "Quan 2", "Quan 9"],
        "provinces": ["TP Ho Chi Minh"]
    },
    "cu chi": {
        "current_districts": ["Cu Chi"],
        "provinces": ["TP Ho Chi Minh"]
    },
    "hoc mon": {
        "current_districts": ["Hoc Mon", "Quan 12"],
        "provinces": ["TP Ho Chi Minh"]
    },
    "binh chanh": {
        "current_districts": ["Binh Chanh", "Binh Tan"],
        "provinces": ["TP Ho Chi Minh"]
    },
    "nha be": {
        "current_districts": ["Nha Be", "Quan 7"],
        "provinces": ["TP Ho Chi Minh"]
    },
    "can gio": {
        "current_districts": ["Can Gio"],
        "provinces": ["TP Ho Chi Minh"]
    },
    "go vap": {
        "current_districts": ["Go Vap"],
        "provinces": ["TP Ho Chi Minh"]
    },
    "tan binh": {
        "current_districts": ["Tan Binh", "Tan Phu"],
        "provinces": ["TP Ho Chi Minh"]
    },
    "binh thanh": {
        "current_districts": ["Binh Thanh"],
        "provinces": ["TP Ho Chi Minh"]
    },
    "phu nhuan": {
        "current_districts": ["Phu Nhuan"],
        "provinces": ["TP Ho Chi Minh"]
    },
}

# ==============================================================================
# 2. BẢNG ÁNH XẠ CẤP HUYỆN (INDEX 2 CHIỀU CẢ CŨ VÀ MỚI)
# ==============================================================================
DISTRICT_LOOKUP = {}

for old_dist_key, d_info in HISTORICAL_DISTRICTS.items():
    norm_old = strip_accents(old_dist_key)
    if norm_old not in DISTRICT_LOOKUP:
        DISTRICT_LOOKUP[norm_old] = {
            "current_districts": set(d_info["current_districts"]),
            "historical_equivalents": {norm_old},
            "provinces": set(d_info["provinces"])
        }
    else:
        DISTRICT_LOOKUP[norm_old]["current_districts"].update(d_info["current_districts"])
        DISTRICT_LOOKUP[norm_old]["provinces"].update(d_info["provinces"])

    # Index ngược từ tên huyện hiện tại sang huyện lịch sử
    for curr_d in d_info["current_districts"]:
        norm_curr = strip_accents(curr_d)
        if norm_curr not in DISTRICT_LOOKUP:
            DISTRICT_LOOKUP[norm_curr] = {
                "current_districts": {curr_d},
                "historical_equivalents": {norm_old},
                "provinces": set(d_info["provinces"])
            }
        else:
            DISTRICT_LOOKUP[norm_curr]["current_districts"].add(curr_d)
            DISTRICT_LOOKUP[norm_curr]["historical_equivalents"].add(norm_old)
            DISTRICT_LOOKUP[norm_curr]["provinces"].update(d_info["provinces"])

REGION_PROVINCES = {
    1: ["Dien Bien", "Lai Chau", "Son La", "Hoa Binh"], # Tây Bắc
    2: ["Ha Giang", "Cao Bang", "Bac Kan", "Lang Son", "Tuyen Quang", "Thai Nguyen", "Phu Tho", "Bac Giang", "Quang Ninh"], # Đông Bắc
    3: ["Ha Noi", "Hai Phong", "Vinh Phuc", "Bac Ninh", "Hai Duong", "Hung Yen", "Ha Nam", "Nam Dinh", "Thai Binh", "Ninh Binh"], # ĐB Sông Hồng
    4: ["Thanh Hoa", "Nghe An", "Ha Tinh", "Quang Binh", "Quang Tri", "Thua Thien Hue"], # Bắc Trung Bộ
    5: ["Da Nang", "Quang Nam", "Quang Ngai", "Binh Dinh", "Phu Yen", "Khanh Hoa", "Ninh Thuan", "Binh Thuan"], # Duyên hải Nam Trung Bộ
    6: ["Kon Tum", "Gia Lai", "Dak Lak", "Dak Nong", "Lam Dong"], # Tây Nguyên
    7: ["TP Ho Chi Minh", "Ba Ria - Vung Tau", "Binh Duong", "Binh Phuoc", "Dong Nai", "Tay Ninh",
        "An Giang", "Bac Lieu", "Ben Tre", "Ca Mau", "Can Tho", "Dong Thap", "Hau Giang",
        "Kien Giang", "Long An", "Soc Trang", "Tien Giang", "Tra Vinh", "Vinh Long"], # Nam Bộ
}

PROVINCE_TO_REGION = {}
for r_id, p_list in REGION_PROVINCES.items():
    for p in p_list:
        PROVINCE_TO_REGION[p] = r_id


# ==============================================================================
# 4. HÀM TRA CỨU & ÁNH XẠ ĐỊA DANH
# ==============================================================================

def clean_location_string(raw: str) -> str:
    """Loại bỏ các từ phụ như '(cũ)', 'tỉnh', 'huyện', 'thị xã', v.v."""
    if not raw:
        return ""
    text = raw.lower()
    text = re.sub(r"\(cũ\)|\(trước 1975\)|\(cũ\)|cũ", " ", text)
    text = re.sub(r"\btỉnh\b|\bhuyện\b|\bthị xã\b|\btx\b|\bthành phố\b|\btp\b|\bxã\b|\bphường\b|\bthị trấn\b|\btt\b", " ", text)
    text = re.sub(r"[,;./\-_]+", " ", text)
    return " ".join(text.split()).strip()


def parse_and_resolve_location(raw_text: str) -> dict:
    """
    Phân tích chuỗi địa danh tự do và ánh xạ về:
    - matched_provinces: tập các tỉnh hiện tại tương ứng
    - matched_districts: tập các huyện/thị xã tương ứng
    - region_ids: các vùng địa lý tương ứng (1..7)
    - raw_clean: chuỗi đã làm sạch
    """
    if not raw_text or not raw_text.strip():
        return {
            "matched_provinces": set(),
            "matched_districts": set(),
            "region_ids": set(),
            "raw_clean": ""
        }

    norm = strip_accents(raw_text)
    clean_norm = strip_accents(clean_location_string(raw_text))

    matched_provinces = set()
    matched_districts = set()

    # 1. Kiểm tra bảng Huyện lịch sử & hiện tại (DISTRICT_LOOKUP 2 chiều)
    for dist_term, dist_data in DISTRICT_LOOKUP.items():
        pattern = r"\b" + re.escape(dist_term) + r"\b"
        if re.search(pattern, norm) or re.search(pattern, clean_norm):
            matched_districts.update(dist_data["current_districts"])
            matched_provinces.update(dist_data["provinces"])

    # 2. Kiểm tra bảng Tỉnh lịch sử (Hà Nam Ninh, Sông Bé, Hà Tây, v.v.)
    for hist_p, current_p_list in HISTORICAL_PROVINCES.items():
        pattern = r"\b" + re.escape(hist_p) + r"\b"
        if re.search(pattern, norm) or re.search(pattern, clean_norm):
            matched_provinces.update(current_p_list)

    # 3. Kiểm tra danh sách 63 Tỉnh hiện tại
    for norm_p, official_p in PROVINCE_NORM_MAP.items():
        pattern = r"\b" + re.escape(norm_p) + r"\b"
        if re.search(pattern, norm) or re.search(pattern, clean_norm):
            matched_provinces.add(official_p)

    # 4. Xác định vùng địa lý
    region_ids = set()
    for p in matched_provinces:
        if p in PROVINCE_TO_REGION:
            region_ids.add(PROVINCE_TO_REGION[p])

    return {
        "matched_provinces": matched_provinces,
        "matched_districts": matched_districts,
        "region_ids": region_ids,
        "raw_clean": clean_norm
    }


def score_locations(loc_a: dict, loc_b: dict) -> float:
    """
    Tính điểm trùng khớp địa danh giữa 2 hồ sơ:
    - Cùng Huyện / Xã / Thị trấn (hoặc tương đương lịch sử): 100 điểm
    - Cùng Tỉnh / Thành phố (hoặc giao nhau qua lịch sử sáp nhập): 50 điểm
    - Khác hoàn toàn: 0 điểm
    - Một bên không có dữ liệu: 35 điểm trung lập
    """
    # Nếu một trong hai bên thiếu thông tin địa danh
    if not loc_a["raw_clean"] or not loc_b["raw_clean"]:
        return 35.0

    # 1. Kiểm tra trùng Huyện / Quận / Xã
    shared_districts = loc_a["matched_districts"].intersection(loc_b["matched_districts"])
    if shared_districts:
        return 100.0

    # 2. Kiểm tra fuzzy match chuỗi chi tiết nếu có nhắc cùng tên huyện/xã
    if loc_a["raw_clean"] and loc_b["raw_clean"]:
        tokens_a = set(loc_a["raw_clean"].split())
        tokens_b = set(loc_b["raw_clean"].split())
        overlap = tokens_a.intersection(tokens_b)
        # Nếu trùng >= 2 token cụ thể (ví dụ "hoang long", "yen khanh", "an do")
        if len(overlap) >= 2:
            return 90.0

    # 3. Kiểm tra trùng Tỉnh / Thành phố
    shared_provinces = loc_a["matched_provinces"].intersection(loc_b["matched_provinces"])
    if shared_provinces:
        return 50.0

    # 4. Kiểm tra cùng vùng địa lý
    shared_regions = loc_a["region_ids"].intersection(loc_b["region_ids"])
    if shared_regions:
        return 20.0

    # 5. Fuzzy match dự phòng nếu địa danh không có trong từ điển
    ratio = fuzz.token_set_ratio(loc_a["raw_clean"], loc_b["raw_clean"])
    if ratio >= 80:
        return 50.0
    elif ratio >= 60:
        return 30.0

    return 0.0
