# HAYLENTIENG.VN Scraper — README

## 📋 Tổng quan
Script tự động trích xuất ~13.000 hồ sơ người mất liên lạc từ **haylentieng.vn** (1083 trang).  
Dữ liệu phục vụ dự án AI phi lợi nhuận: Semantic Search + Vector Embeddings hỗ trợ đoàn tụ gia đình.

---

## 📁 Cấu trúc thư mục
```
haylentieng-scraper/
├── scraper.js            ← Script Node.js (khuyên dùng nếu có Node)
├── scraper_python.py     ← Script Python (dễ cài hơn)
├── output/
│   ├── haylentieng_data.csv   ← File kết quả (tự tạo)
│   └── progress.json          ← Tiến độ (hỗ trợ resume)
└── README.md
```

---

## 🚀 CÁCH CHẠY — Chọn 1 trong 2 phương án

---

### ✅ PHƯƠNG ÁN 1: Python (Khuyên dùng — dễ cài nhất)

#### Bước 1: Cài Python
Tải tại: **https://www.python.org/downloads/**  
⚠️ Trong lúc cài, **TICK VÀO Ô "Add Python to PATH"**

Kiểm tra cài thành công:
```powershell
python --version
```

#### Bước 2: Cài thư viện
```powershell
pip install requests beautifulsoup4 lxml
```

#### Bước 3: Chạy script
```powershell
python "C:\Users\ad\.gemini\antigravity\scratch\haylentieng-scraper\scraper_python.py"
```

---

### ✅ PHƯƠNG ÁN 2: Node.js

#### Bước 1: Cài Node.js
Tải tại: **https://nodejs.org/** (chọn LTS)

Kiểm tra:
```powershell
node --version
npm --version
```

#### Bước 2: Cài thư viện
```powershell
cd "C:\Users\ad\.gemini\antigravity\scratch\haylentieng-scraper"
npm init -y
npm install axios cheerio
```

#### Bước 3: Chạy script
```powershell
node scraper.js
```

---

## 📊 Dữ liệu đầu ra (CSV)

File `output/haylentieng_data.csv` có **5 cột**:

| Cột | Nội dung | Ví dụ |
|-----|----------|-------|
| Tiêu đề (Mã số & Tên) | Mã hồ sơ + tên người tìm | `MS28447: Ông Lâm Anh Tuấn tha thiết tìm cha...` |
| Link chi tiết | URL hồ sơ đầy đủ | `https://haylentieng.vn/profile/...` |
| Mô tả câu chuyện | Đoạn tóm tắt câu chuyện | `Ông Lâm Trinh Tạo sinh năm 1940...` |
| URL hình ảnh | Link ảnh hồ sơ | `https://haylentieng.vn/wp-content/...` |
| Thông tin chi tiết (gộp) | Họ tên, năm sinh, cha mẹ, năm thất lạc | `Họ và tên: ... \| Năm sinh: 1940 \| ...` |

> **Mở bằng Excel:** File → Data → From Text/CSV → Chọn UTF-8

---

## ⚡ Tính năng kỹ thuật

| Tính năng | Chi tiết |
|-----------|----------|
| **Rate limiting** | Delay ngẫu nhiên 2–3 giây giữa mỗi request |
| **Auto-resume** | Nếu script dừng giữa chừng, chạy lại → tiếp tục từ chỗ dừng |
| **Retry logic** | Mỗi trang thất bại thử lại 3 lần trước khi bỏ qua |
| **Error handling** | `try/catch` — 1 trang lỗi không crash toàn bộ |
| **UTF-8 BOM** | Excel và Google Sheets hiển thị tiếng Việt đúng |
| **Live progress** | In tiến độ real-time: `[page/1083] ✅ 12 hồ sơ (2.3s) — Tổng: 4521` |

---

## ⏱️ Thời gian ước tính
- 1083 trang × ~2.5s delay = **~45 phút** (chạy nền)
- Khuyên để máy không ngủ trong lúc chạy (cài `powercfg /change standby-timeout-ac 0`)

---

## ⚠️ Lưu ý
- Script chỉ đọc dữ liệu công khai, không đăng nhập hay viết lại trang web
- Delay 2–3s là lịch sự, không gây quá tải server
- Dùng cho mục đích nhân đạo, phi thương mại
