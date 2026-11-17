"""Test nhanh scraper_v2: chỉ chạy 2 trang đầu để xác nhận cấu trúc CSV."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

# Patch TOTAL_PAGES để chỉ chạy 2 trang
import scraper_v2
scraper_v2.TOTAL_PAGES  = 2
scraper_v2.OUTPUT_FILE  = os.path.join(scraper_v2.OUTPUT_DIR, "test_v2.csv")
scraper_v2.PROGRESS_FILE= os.path.join(scraper_v2.OUTPUT_DIR, "test_progress_v2.json")

scraper_v2.main()
