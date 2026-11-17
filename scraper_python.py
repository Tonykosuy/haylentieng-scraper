"""
============================================================
 HAYLENTIENG.VN - Web Scraper (Python version)
 Dự án: Tìm kiếm & kết nối người thân mất liên lạc
 Thư viện cần cài: requests, beautifulsoup4, lxml
============================================================
"""

import csv
import json
import os
import random
import time

import requests
from bs4 import BeautifulSoup

# ─── CẤU HÌNH ─────────────────────────────────────────────────
BASE_URL = "https://haylentieng.vn/profiles/"
TOTAL_PAGES = 1083
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "haylentieng_data.csv")
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "progress.json")
DELAY_MIN = 0.1   # giây, nghỉ tối thiểu giữa các request
DELAY_MAX = 0.1   # giây, nghỉ tối đa
MAX_RETRIES = 3
RETRY_DELAY = 5.0
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}

CSV_COLUMNS = [
    "Tiêu đề (Mã số & Tên)",
    "Link chi tiết",
    "Mô tả câu chuyện",
    "URL hình ảnh",
    "Thông tin chi tiết (gộp)",
]


# ─── TIỆN ÍCH ─────────────────────────────────────────────────

def build_url(page: int) -> str:
    return BASE_URL if page == 1 else f"{BASE_URL}page/{page}/"


def clean_text(text: str) -> str:
    """Làm sạch chuỗi: xóa xuống dòng, thu gọn khoảng trắng."""
    if not text:
        return ""
    return " ".join(text.replace("\n", " ").replace("\r", " ").split()).strip()


def load_progress() -> dict:
    """Đọc tiến độ đã lưu để resume khi script bị dừng."""
    try:
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"last_page": 0, "total_records": 0}


def save_progress(last_page: int, total_records: int) -> None:
    """Lưu tiến độ hiện tại."""
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_page": last_page, "total_records": total_records}, f, indent=2)


# ─── TẢI TRANG ────────────────────────────────────────────────

def fetch_page(page: int) -> str | None:
    """Tải HTML của trang, có cơ chế thử lại."""
    url = build_url(page)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            return resp.text
        except requests.RequestException as e:
            is_last = attempt == MAX_RETRIES
            print(f"  ⚠️  Trang {page} - Lần thử {attempt}/{MAX_RETRIES}: {e}")
            if not is_last:
                print(f"     Chờ {RETRY_DELAY}s rồi thử lại...")
                time.sleep(RETRY_DELAY)
    print(f"  ❌ Bỏ qua trang {page} sau {MAX_RETRIES} lần thử.")
    return None


# ─── PARSE HỒ SƠ ──────────────────────────────────────────────

def parse_profiles(html: str) -> list[dict]:
    """Trích xuất tất cả hồ sơ từ HTML của một trang."""
    soup = BeautifulSoup(html, "lxml")
    profiles = []

    # Tìm container danh sách hồ sơ
    ul = soup.find("ul", class_=lambda c: c and "content-block" in c and "type-profile" in c)
    if not ul:
        return profiles

    for li in ul.find_all("li", recursive=False):
        # 1. Tiêu đề & link
        title_el = li.select_one(".single-title a")
        if not title_el:
            continue

        title = clean_text(title_el.get_text())
        link = title_el.get("href", "")
        story = clean_text(title_el.get("title", ""))  # Mô tả câu chuyện

        # 2. Hình ảnh
        img = li.select_one(".profile-right img")
        image_url = img.get("src", "") if img else ""

        # 3. Thông tin chi tiết: gom tất cả <p> trong .profile-left
        detail_parts = []
        for p in li.select(".profile-left p"):
            text = clean_text(p.get_text())
            if text:
                detail_parts.append(text)
        details = " | ".join(detail_parts)

        if title:
            profiles.append({
                "Tiêu đề (Mã số & Tên)": title,
                "Link chi tiết": link,
                "Mô tả câu chuyện": story,
                "URL hình ảnh": image_url,
                "Thông tin chi tiết (gộp)": details,
            })

    return profiles


# ─── HÀM CHÍNH ────────────────────────────────────────────────

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load tiến độ cũ (resume)
    progress = load_progress()
    start_page = progress["last_page"] + 1
    total_records = progress["total_records"]

    # Chế độ ghi: tạo mới hoặc ghi tiếp
    file_exists = os.path.exists(OUTPUT_FILE) and start_page > 1
    write_mode = "a" if file_exists else "w"

    print("╔══════════════════════════════════════════════════╗")
    print("║   HAYLENTIENG.VN - BẮT ĐẦU SCRAPING DỮ LIỆU    ║")
    print("╚══════════════════════════════════════════════════╝")
    print(f"📄 Bắt đầu từ trang: {start_page} / {TOTAL_PAGES}")
    print(f"📦 Đã có: {total_records} hồ sơ")
    print(f"⏱️  Delay: {DELAY_MIN}–{DELAY_MAX}s / trang\n")

    # Mở file CSV (newline='' là bắt buộc với csv module trên Windows)
    with open(OUTPUT_FILE, mode=write_mode, encoding="utf-8-sig", newline="") as csvfile:
        # utf-8-sig = UTF-8 + BOM → Excel & Google Sheets đọc đúng tiếng Việt
        writer = csv.DictWriter(
            csvfile,
            fieldnames=CSV_COLUMNS,
            quoting=csv.QUOTE_ALL,
            extrasaction="ignore",
        )

        # Ghi header chỉ khi tạo file mới
        if not file_exists:
            writer.writeheader()

        for page in range(start_page, TOTAL_PAGES + 1):
            t0 = time.time()
            print(f"[{page}/{TOTAL_PAGES}] Đang tải...", end=" ", flush=True)

            try:
                html = fetch_page(page)
                if not html:
                    print("⏭️  Bỏ qua.")
                    continue

                profiles = parse_profiles(html)

                if not profiles:
                    print("⚠️  Không tìm thấy hồ sơ nào.")
                else:
                    writer.writerows(profiles)
                    csvfile.flush()  # Ghi ngay vào đĩa
                    total_records += len(profiles)
                    elapsed = time.time() - t0
                    print(f"✅ {len(profiles)} hồ sơ ({elapsed:.1f}s) — Tổng: {total_records}")

                save_progress(page, total_records)

            except Exception as e:
                print(f"❌ Lỗi bất ngờ trang {page}: {e}")

            # Delay ngẫu nhiên
            if page < TOTAL_PAGES:
                wait = random.uniform(DELAY_MIN, DELAY_MAX)
                time.sleep(wait)

    print("\n╔══════════════════════════════════════════════════╗")
    print("║              HOÀN THÀNH SCRAPING!                ║")
    print("╚══════════════════════════════════════════════════╝")
    print(f"✅ Tổng hồ sơ đã lưu: {total_records}")
    print(f"📁 File output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
