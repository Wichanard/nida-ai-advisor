import os
import json
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup

def scrape_nida_news():
    """
    ฟังก์ชันสำหรับดึงข่าวสาร/อัปเดต จากหน้าเว็บไซต์ NIDA แบบอัตโนมัติ
    (นี่คือ Template พื้นฐาน สามารถนำไปปรับ Class หรือ Tag ตามโครงสร้างเว็บจริงได้)
    """
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] เริ่มกระบวนการดึงข้อมูลจากเว็บไซต์ NIDA...")
    
    url = "https://nida.ac.th/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"เกิดข้อผิดพลาดในการเชื่อมต่อกับเว็บไซต์: {e}")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    
    # ดึงข้อมูลจาก Heading Tag (h2, h3) หรือคลาสที่มักจะใช้แสดงหัวข้อข่าว
    # (สามารถปรับแก้ Tag หรือ Class ให้ตรงกับหน้าเว็บเป๊ะๆ ได้ในอนาคต)
    news_elements = soup.find_all(['h2', 'h3'])
    
    scraped_data = []
    seen_titles = set()

    for element in news_elements:
        title = element.get_text(strip=True)
        # กรองข้อมูลสั้นเกินไปออกไป
        if len(title) > 15 and title not in seen_titles:
            # พยายามหา Link ที่ครอบหัวข้อนี้อยู่
            parent_link = element.find_parent('a')
            link = parent_link['href'] if parent_link and 'href' in parent_link.attrs else url

            # แปลง Link ให้สมบูรณ์ถ้าเป็น Relative path
            if link.startswith('/'):
                link = f"https://nida.ac.th{link}"

            scraped_data.append({
                "title": title,
                "link": link,
                "scraped_at": datetime.now().isoformat(),
                "source": "nida_main_website"
            })
            seen_titles.add(title)

    if not scraped_data:
        print("ไม่พบหัวข้อข่าวหรือประกาศใหม่บนเว็บไซต์")
        return

    # บันทึกข้อมูลลงโฟลเดอร์ data
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    
    output_file = os.path.join(data_dir, "nida_scraped_news.jsonl")
    
    # อ่านข้อมูลเก่าก่อน เพื่อที่จะได้ไม่บันทึกซ้ำ (Append / Sync)
    existing_titles = set()
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        record = json.loads(line)
                        existing_titles.add(record.get('title', ''))
                    except:
                        pass

    new_items_count = 0
    with open(output_file, 'a', encoding='utf-8') as f:
        for item in scraped_data:
            if item['title'] not in existing_titles:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
                new_items_count += 1

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ดึงข้อมูลสำเร็จ! พบรายการข่าวทั้งหมด {len(scraped_data)} รายการ (เป็นข้อมูลใหม่ {new_items_count} รายการ)")
    print(f"บันทึกข้อมูลไว้ที่: {output_file}")

if __name__ == "__main__":
    scrape_nida_news()
