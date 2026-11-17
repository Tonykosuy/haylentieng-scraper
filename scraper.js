/**
 * ============================================================
 *  HAYLENTIENG.VN - Web Scraper
 *  Dự án: Tìm kiếm & kết nối người thân mất liên lạc (phi lợi nhuận)
 *  Tác giả: AI-assisted scraper for humanitarian use
 *  Mục tiêu: Trích xuất ~13.000 hồ sơ từ 1083 trang
 * ============================================================
 */

const axios = require('axios');
const cheerio = require('cheerio');
const fs = require('fs');
const path = require('path');

// ─── CẤU HÌNH ───────────────────────────────────────────────
const CONFIG = {
  BASE_URL: 'https://haylentieng.vn/profiles/',
  TOTAL_PAGES: 1083,
  OUTPUT_FILE: path.join(__dirname, 'output', 'haylentieng_data.csv'),
  PROGRESS_FILE: path.join(__dirname, 'output', 'progress.json'),
  DELAY_MIN_MS: 2000,   // Thời gian nghỉ tối thiểu giữa các request
  DELAY_MAX_MS: 3000,   // Thời gian nghỉ tối đa giữa các request
  MAX_RETRIES: 3,       // Số lần thử lại nếu request bị lỗi
  RETRY_DELAY_MS: 5000, // Thời gian chờ trước khi thử lại
  HEADERS: {
    'User-Agent':
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' +
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'vi-VN,vi;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
  },
};

// ─── TIỆN ÍCH ───────────────────────────────────────────────

/** Hàm delay ngẫu nhiên giữa min và max ms */
const delay = (min, max) => {
  const ms = Math.floor(Math.random() * (max - min + 1)) + min;
  return new Promise((resolve) => setTimeout(resolve, ms));
};

/** Làm sạch chuỗi: xóa dấu nháy kép, xuống dòng, ký tự thừa */
const cleanText = (str = '') =>
  str
    .replace(/"/g, "'")         // Thay " bằng ' để không phá CSV
    .replace(/\n|\r/g, ' ')     // Xóa xuống dòng
    .replace(/\s+/g, ' ')       // Thu gọn khoảng trắng thừa
    .trim();

/** Tạo URL theo số trang */
const buildUrl = (page) =>
  page === 1 ? CONFIG.BASE_URL : `${CONFIG.BASE_URL}page/${page}/`;

/** Đọc tiến độ đã lưu (resume khi bị gián đoạn) */
const loadProgress = () => {
  try {
    if (fs.existsSync(CONFIG.PROGRESS_FILE)) {
      const data = JSON.parse(fs.readFileSync(CONFIG.PROGRESS_FILE, 'utf-8'));
      return data;
    }
  } catch (_) {}
  return { lastPage: 0, totalRecords: 0 };
};

/** Lưu tiến độ hiện tại */
const saveProgress = (lastPage, totalRecords) => {
  fs.writeFileSync(
    CONFIG.PROGRESS_FILE,
    JSON.stringify({ lastPage, totalRecords }, null, 2),
    'utf-8'
  );
};

// ─── LẤY TRANG VỚI CƠ CHẾ THỬ LẠI ─────────────────────────

const fetchPage = async (page) => {
  const url = buildUrl(page);
  for (let attempt = 1; attempt <= CONFIG.MAX_RETRIES; attempt++) {
    try {
      const response = await axios.get(url, {
        headers: CONFIG.HEADERS,
        timeout: 15000,
      });
      return response.data;
    } catch (err) {
      const isLast = attempt === CONFIG.MAX_RETRIES;
      console.warn(
        `  ⚠️  Trang ${page} - Lần thử ${attempt}/${CONFIG.MAX_RETRIES} thất bại: ${err.message}`
      );
      if (!isLast) {
        console.log(`     Chờ ${CONFIG.RETRY_DELAY_MS / 1000}s rồi thử lại...`);
        await delay(CONFIG.RETRY_DELAY_MS, CONFIG.RETRY_DELAY_MS);
      }
    }
  }
  console.error(`  ❌ Bỏ qua trang ${page} sau ${CONFIG.MAX_RETRIES} lần thử.`);
  return null;
};

// ─── PARSE HỒ SƠ TỪ HTML ─────────────────────────────────────

const parseProfiles = (html) => {
  const $ = cheerio.load(html);
  const profiles = [];

  $('ul.content-block.type-profile li').each((_, li) => {
    const $li = $(li);

    // 1. Tiêu đề (Mã số & Tên đầy đủ)
    const titleEl = $li.find('.single-title a');
    const title = cleanText(titleEl.text());

    // 2. Link chi tiết hồ sơ
    const link = titleEl.attr('href') || '';

    // 3. Mô tả câu chuyện (trong thuộc tính title)
    const story = cleanText(titleEl.attr('title') || '');

    // 4. URL hình ảnh
    const imageUrl = $li.find('.profile-right img').attr('src') || '';

    // 5. Tất cả thông tin chi tiết trong .profile-left > p
    //    Gộp thành một chuỗi, phân cách bởi |
    const details = $li
      .find('.profile-left p')
      .map((_, p) => cleanText($(p).text()))
      .get()
      .filter(Boolean)
      .join(' | ');

    // Chỉ thêm hồ sơ nếu có tiêu đề (tránh thẻ li rỗng)
    if (title) {
      profiles.push({ title, link, story, imageUrl, details });
    }
  });

  return profiles;
};

// ─── GHI CSV ─────────────────────────────────────────────────

/** Wrap field bằng dấu nháy kép (chuẩn CSV RFC 4180) */
const csvField = (val = '') => `"${String(val).replace(/"/g, "'")}"`;

const csvRow = (profile) =>
  [
    csvField(profile.title),
    csvField(profile.link),
    csvField(profile.story),
    csvField(profile.imageUrl),
    csvField(profile.details),
  ].join(',');

// ─── HÀM CHÍNH ───────────────────────────────────────────────

const main = async () => {
  // Tạo thư mục output
  const outputDir = path.dirname(CONFIG.OUTPUT_FILE);
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  // Đọc tiến độ cũ (hỗ trợ resume nếu script bị dừng giữa chừng)
  const progress = loadProgress();
  const startPage = progress.lastPage + 1;
  let totalRecords = progress.totalRecords;

  // Xác định chế độ ghi file: tạo mới hay ghi tiếp
  const fileExists = fs.existsSync(CONFIG.OUTPUT_FILE) && startPage > 1;
  const writeStream = fs.createWriteStream(CONFIG.OUTPUT_FILE, {
    flags: fileExists ? 'a' : 'w',  // append nếu tiếp tục, write nếu mới
    encoding: 'utf-8',
  });

  // Ghi BOM + Header nếu là file mới
  if (!fileExists) {
    writeStream.write('\uFEFF'); // UTF-8 BOM — cần cho Excel & Google Sheets
    const header = '"Tiêu đề (Mã số & Tên)","Link chi tiết","Mô tả câu chuyện","URL hình ảnh","Thông tin chi tiết (gộp)"\n';
    writeStream.write(header);
  }

  console.log('╔══════════════════════════════════════════════════╗');
  console.log('║   HAYLENTIENG.VN - BẮT ĐẦU SCRAPING DỮ LIỆU    ║');
  console.log('╚══════════════════════════════════════════════════╝');
  console.log(`📄 Bắt đầu từ trang: ${startPage} / ${CONFIG.TOTAL_PAGES}`);
  console.log(`📦 Đã có: ${totalRecords} hồ sơ`);
  console.log(`⏱️  Delay: ${CONFIG.DELAY_MIN_MS}–${CONFIG.DELAY_MAX_MS}ms / trang\n`);

  for (let page = startPage; page <= CONFIG.TOTAL_PAGES; page++) {
    const startTime = Date.now();
    process.stdout.write(`[${page}/${CONFIG.TOTAL_PAGES}] Đang tải... `);

    try {
      const html = await fetchPage(page);

      if (!html) {
        // Trang bị lỗi sau tất cả các lần thử → bỏ qua, tiếp tục
        console.log('⏭️  Bỏ qua.');
        continue;
      }

      const profiles = parseProfiles(html);

      if (profiles.length === 0) {
        console.log('⚠️  Không tìm thấy hồ sơ nào (có thể trang cuối hoặc thay đổi cấu trúc).');
      } else {
        // Ghi từng hồ sơ vào CSV
        for (const profile of profiles) {
          writeStream.write(csvRow(profile) + '\n');
          totalRecords++;
        }

        const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
        console.log(`✅ ${profiles.length} hồ sơ (${elapsed}s) — Tổng: ${totalRecords}`);
      }

      // Lưu tiến độ sau mỗi trang
      saveProgress(page, totalRecords);

    } catch (err) {
      // Bắt lỗi không ngờ — vẫn tiếp tục vòng lặp
      console.error(`❌ Lỗi bất ngờ trang ${page}: ${err.message}`);
    }

    // Delay ngẫu nhiên trước khi sang trang tiếp theo
    if (page < CONFIG.TOTAL_PAGES) {
      await delay(CONFIG.DELAY_MIN_MS, CONFIG.DELAY_MAX_MS);
    }
  }

  // Đóng stream ghi file
  await new Promise((resolve) => writeStream.end(resolve));

  console.log('\n╔══════════════════════════════════════════════════╗');
  console.log('║              HOÀN THÀNH SCRAPING!                ║');
  console.log('╚══════════════════════════════════════════════════╝');
  console.log(`✅ Tổng hồ sơ đã lưu: ${totalRecords}`);
  console.log(`📁 File output: ${CONFIG.OUTPUT_FILE}`);
};

// ─── CHẠY ────────────────────────────────────────────────────
main().catch((err) => {
  console.error('💥 Lỗi nghiêm trọng:', err);
  process.exit(1);
});
