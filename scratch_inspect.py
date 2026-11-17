import requests
from bs4 import BeautifulSoup
import sys
sys.stdout.reconfigure(encoding='utf-8')

r = requests.get(
    'https://haylentieng.vn/profile/ong-lam-anh-tuan-mong-moi-co-tin-ve-cha-lam-trinh-tao/',
    headers={'User-Agent': 'Mozilla/5.0'}
)
soup = BeautifulSoup(r.text, 'lxml')

pl = soup.find(class_='profile-left')
pc = soup.find(class_='profile-content')

print("=== PROFILE-LEFT (thông tin) ===")
print(pl.get_text(separator='\n').strip()[:1000] if pl else 'NONE')
print("\n=== PROFILE-CONTENT (câu chuyện) ===")
print(pc.get_text(separator='\n').strip()[:3000] if pc else 'NONE')
