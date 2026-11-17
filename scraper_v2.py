"""
============================================================
 HAYLENTIENG.VN - Web Scraper v2 (HOÀN THIỆN)
 - Lấy câu chuyện ĐẦY ĐỦ từ trang chi tiết
 - Tách riêng: Họ tên | Năm sinh | Quê quán | Tên cha | Tên mẹ | Năm thất lạc
 - Hỗ trợ resume (tiếp tục từ chỗ dừng)
============================================================
"""

import csv
import json
import os
import re
import random
import sys
import time

import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")

# ─── CẤU HÌNH ─────────────────────────────────────────────────
BASE_URL     = "https://haylentieng.vn/profiles/"
TOTAL_PAGES  = 1083
OUTPUT_DIR   = os.path.join(os.path.dirname(__file__), "output")
OUTPUT_FILE  = os.path.join(OUTPUT_DIR, "haylentieng_v2.csv")
PROGRESS_FILE= os.path.join(OUTPUT_DIR, "progress_v2.json")

LIST_DELAY   = 0.1   # giây nghỉ giữa mỗi trang danh sách
DETAIL_DELAY = 0.15  # giây nghỉ giữa mỗi trang chi tiết (nhỏ nhưng lịch sự)
MAX_RETRIES  = 3
RETRY_DELAY  = 5.0

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}

CSV_COLUMNS = [
    "Mã số",
    "Tiêu đề",
    "Họ và tên",
    "Năm sinh",
    "Quê quán",
    "Tên cha",
    "Tên mẹ",
    "Năm thất lạc",
    "Câu chuyện đầy đủ",
    "URL hình ảnh",
    "Link chi tiết",
]


# ─── TIỆN ÍCH ─────────────────────────────────────────────────

def clean(text: str) -> str:
    if not text:
        return ""
    return " ".join(text.replace("\n", " ").replace("\r", " ").split()).strip()


def build_list_url(page: int) -> str:
    return BASE_URL if page == 1 else f"{BASE_URL}page/{page}/"


def load_progress() -> dict:
    try:
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"last_page": 0, "total_records": 0}


def save_progress(last_page: int, total_records: int) -> None:
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_page": last_page, "total_records": total_records}, f, indent=2)


# ─── TẢI TRANG (có retry) ─────────────────────────────────────

def fetch(url: str, label: str = "") -> str | None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            r.encoding = "utf-8"
            return r.text
        except requests.RequestException as e:
            if attempt == MAX_RETRIES:
                print(f"  ❌ Bỏ qua [{label}]: {e}")
                return None
            time.sleep(RETRY_DELAY)
    return None


# ─── PARSE TRANG DANH SÁCH ────────────────────────────────────

def parse_list_page(html: str) -> list[dict]:
    """Lấy các hồ sơ cơ bản từ trang danh sách (link + ảnh)."""
    soup = BeautifulSoup(html, "lxml")
    ul = soup.find("ul", class_=lambda c: c and "content-block" in c and "type-profile" in c)
    if not ul:
        return []

    results = []
    for li in ul.find_all("li", recursive=False):
        a = li.select_one(".single-title a")
        if not a:
            continue
        img = li.select_one(".profile-right img")
        results.append({
            "title_raw": clean(a.get_text()),
            "link":      a.get("href", ""),
            "image_url": img.get("src", "") if img else "",
        })
    return results


# ─── PARSE TRANG CHI TIẾT ─────────────────────────────────────

# Map nhãn tiếng Việt → tên cột CSV
FIELD_MAP = {
    "họ và tên":   "Họ và tên",
    "năm sinh":    "Năm sinh",
    "quê quán":    "Quê quán",
    "tên cha":     "Tên cha",
    "tên mẹ":      "Tên mẹ",
    "năm thất lạc":"Năm thất lạc",
}

def parse_detail_page(html: str) -> dict:
    """Lấy câu chuyện đầy đủ + thông tin chi tiết từ trang hồ sơ."""
    soup = BeautifulSoup(html, "lxml")

    # --- Thông tin cấu trúc từ profile-left ---
    fields = {v: "" for v in FIELD_MAP.values()}
    pl = soup.find(class_="profile-left")
    if pl:
        for p in pl.find_all("p"):
            text = clean(p.get_text())
            if ":" in text:
                key, _, val = text.partition(":")
                mapped = FIELD_MAP.get(key.strip().lower())
                if mapped:
                    fields[mapped] = clean(val)

    # --- Câu chuyện đầy đủ từ profile-content ---
    story = ""
    pc = soup.find(class_="profile-content")
    if pc:
        # Bỏ caption ảnh (wp-caption-text) vì đó không phải câu chuyện
        for caption in pc.find_all(class_="wp-caption-text"):
            caption.decompose()
        story = clean(pc.get_text(separator=" "))

    return {**fields, "Câu chuyện đầy đủ": story}


# ─── TÁCH MÃ SỐ & TIÊU ĐỀ ────────────────────────────────────

def split_title(title_raw: str) -> tuple[str, str]:
    """Tách 'MS12345: Tên tiêu đề' → ('MS12345', 'Tên tiêu đề')"""
    m = re.match(r"^(MS\d+)\s*:\s*(.+)$", title_raw, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return "", title_raw


# ─── HÀM CHÍNH ────────────────────────────────────────────────

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    progress     = load_progress()
    start_page   = progress["last_page"] + 1
    total_records= progress["total_records"]

    file_exists  = os.path.exists(OUTPUT_FILE) and start_page > 1
    write_mode   = "a" if file_exists else "w"

    print("╔══════════════════════════════════════════════════════════╗")
    print("║   HAYLENTIENG.VN Scraper v2 — DỮ LIỆU ĐẦY ĐỦ           ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"📄 Trang bắt đầu : {start_page} / {TOTAL_PAGES}")
    print(f"📦 Hồ sơ hiện có : {total_records}")
    print(f"📁 Output         : {OUTPUT_FILE}\n")

    with open(OUTPUT_FILE, mode=write_mode, encoding="utf-8-sig", newline="") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=CSV_COLUMNS,
            quoting=csv.QUOTE_ALL,
            extrasaction="ignore",
        )
        if not file_exists:
            writer.writeheader()

        for page in range(start_page, TOTAL_PAGES + 1):
            print(f"\n── Trang {page}/{TOTAL_PAGES} ──────────────────────────────")

            list_html = fetch(build_list_url(page), f"trang {page}")
            if not list_html:
                save_progress(page, total_records)
                continue

            items = parse_list_page(list_html)
            if not items:
                print("  ⚠️  Không có hồ sơ.")
                save_progress(page, total_records)
                continue

            page_count = 0
            for item in items:
                ms, title = split_title(item["title_raw"])

                # Tải trang chi tiết
                detail = {}
                if item["link"]:
                    d_html = fetch(item["link"], ms or title[:20])
                    if d_html:
                        detail = parse_detail_page(d_html)
                    time.sleep(DETAIL_DELAY)

                row = {
                    "Mã số":              ms,
                    "Tiêu đề":            title,
                    "Họ và tên":          detail.get("Họ và tên", ""),
                    "Năm sinh":           detail.get("Năm sinh", ""),
                    "Quê quán":           detail.get("Quê quán", ""),
                    "Tên cha":            detail.get("Tên cha", ""),
                    "Tên mẹ":             detail.get("Tên mẹ", ""),
                    "Năm thất lạc":       detail.get("Năm thất lạc", ""),
                    "Câu chuyện đầy đủ":  detail.get("Câu chuyện đầy đủ", ""),
                    "URL hình ảnh":       item["image_url"],
                    "Link chi tiết":      item["link"],
                }
                writer.writerow(row)
                page_count += 1
                total_records += 1
                print(f"  ✅ [{ms}] {title[:45]}")

            csvfile.flush()
            save_progress(page, total_records)
            print(f"  → {page_count} hồ sơ | Tổng cộng: {total_records}")

            if page < TOTAL_PAGES:
                time.sleep(LIST_DELAY)

    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║                  HOÀN THÀNH!                             ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"✅ Tổng hồ sơ : {total_records}")
    print(f"📁 File       : {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
