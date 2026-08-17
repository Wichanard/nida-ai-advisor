# Social Listening for NIDA

โครงงานนี้ออกแบบมาเพื่อเก็บและจัดการคอมเมนต์ออนไลน์เกี่ยวกับ "นิด้า" จากหลายแพลตฟอร์มด้วยข้อมูลตระกูล JSONL.

## โครงสร้างหลัก

- `requirements.txt` - dependencies สำหรับโปรเจคนี้
- `config_example.json` - ตัวอย่าง config คีย์เวิร์ดและแพลตฟอร์ม
- `collector_base.py` - interface และ helper สำหรับ collectors
- `collector_x.py` - collector สำหรับ Twitter/X
- `storage.py` - writer/reader JSONL, dedupe
- `utils.py` - query builder, normalization, language detection
- `analyzer.py` - ฟังก์ชันวิเคราะห์พื้นฐาน
- `run_collector.py` - CLI สำหรับเรียกใช้งาน collector

## ตั้งค่าเบื้องต้น

1. สร้าง virtual environment และติดตั้ง dependencies:

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. คัดลอก `config_example.json` เป็น `config.json` และใส่คีย์ API (ถ้ามี)

3. ตั้งค่า environment variables สำหรับ Twitter/X:

```powershell
$env:TWITTER_BEARER_TOKEN = "YOUR_BEARER_TOKEN"
```

4. รัน dry-run query ก่อน:

```bash
python run_collector.py --platform x --dry-run
```

5. รัน collector จริง:

```bash
python run_collector.py --platform x --output data/comments_x.jsonl
```

## ถัดไป

- เพิ่ม collector สำหรับ YouTube, Reddit, CrowdTangle, Pantip, เว็บข่าว
- เพิ่ม analyzer เพื่อทำ sentiment/topic/NER
- สร้าง dashboard หรือ export เป็น CSV/Excel
- เพิ่ม dashboard แบบ Streamlit เพื่อดู `fallback_stage` / `source_url`

## ตัวอย่างการใช้งาน collector ใหม่

- News:

```bash
python run_collector.py --platform news --output data/comments_news.jsonl
```

- CrowdTangle:

```bash
python run_collector.py --platform crowdtangle --output data/comments_crowdtangle.jsonl
```

> ต้องใช้ `NEWSAPI_KEY` สำหรับ News API และ `CROWDTANGLE_API_TOKEN` สำหรับ CrowdTangle API

## ตัวเลือก query ขั้นสูง

ใน `config.json` สำหรับ `news` และ `crowdtangle`:

- `query_operator`: `OR` หรือ `AND`
- `max_results`: จำนวนผลลัพธ์สูงสุด
- `sort_by`: เรียงตาม `relevancy`, `date`, หรือค่าอื่นตาม API
- `comment_parsing`: (news เท่านั้น) ถ้าเป็น `true` จะลองดึง block คอมเมนต์จากหน้า article
- `comment_selectors`: selector CSS ทั่วไปสำหรับค้นหาคอมเมนต์
- `comment_context_selectors`: parent selector เช่น `article`, `section`, `main` เพื่อค้นหา comment node แบบลึกขึ้น
- `comment_selectors_by_domain`: selector CSS เฉพาะโดเมนข่าวไทย เช่น `thairath.co.th`, `mgronline.com`, `kapook.com`, `springnews.co.th`, `dailynews.co.th`
- `comment_iframe`: ถ้าเป็น `true` จะพยายามดึงคอมเมนต์จาก `iframe`
- `iframe_selectors`: selector สำหรับ iframe เช่น `iframe`
- `iframe_comment_selectors`: selector ใน iframe เพื่อค้นหาคอมเมนต์
- `render_js`: ถ้าเป็น `true` จะใช้ backend ที่เลือกเรนเดอร์ JS ก่อน parse
- `render_backend`: เลือก backend สำหรับเรนเดอร์ JS, เช่น `requests-html`, `selenium`, หรือ `playwright`
- `render_sleep`: ระยะเวลารอหลังเรนเดอร์ JS (วินาที)
- `render_timeout`: timeout สำหรับ render
- `comment_regex`: regex กรองคอมเมนต์ที่ต้องการเก็บ เช่น `นิด้า`, `NIDA`, `หลักสูตร`

> ถ้าเปิด `render_js` กับ `render_backend=selenium` ต้องติดตั้ง `selenium` และ Chrome/Chromium driver ตามด้วย `pip install selenium`.
> ถ้าเลือก `render_backend=playwright` ต้องติดตั้ง `playwright` และรัน `playwright install`.
> `requests-html` ยังรองรับได้ถ้าใช้ `render_backend=requests-html`.
