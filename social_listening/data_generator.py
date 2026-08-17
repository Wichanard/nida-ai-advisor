"""
social_listening/data_generator.py
Enterprise Big Data Generator for NIDA Social Listening Platform.
Generates 1,500+ realistic, rich student & alumni discussions across 5 platforms with Aspect Sentiment & Intents.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List


FACULTIES = [
    "คณะบริหารธุรกิจ (GSBA)",
    "คณะสถิติประยุกต์ (GSAS)",
    "คณะรัฐประศาสนศาสตร์ (GSPA)",
    "คณะพัฒนาการเศรษฐกิจ (GSDE)",
    "คณะพัฒนาทรัพยากรมนุษย์ (GSHRD)",
    "คณะนิเทศศาสตร์และนวัตกรรมการจัดการ (GSCOM)",
    "คณะนิติศาสตร์ (NIDA LAW)",
    "วิทยาลัยนานาชาติ (ICO NIDA)",
    "คณะการจัดการการท่องเที่ยว (GST)",
    "คณะพัฒนาสังคมและยุทธศาสตร์การบริหาร (GSSD)",
    "คณะสิ่งแวดล้อมและการพัฒนาอย่างยั่งยืน",
]

PROGRAMS = [
    "Flexible MBA (เสาร์-อาทิตย์)",
    "Data Analytics and Data Science (DADS)",
    "Executive MBA (EMBA)",
    "MPA รัฐประศาสนศาสตร์",
    "Management of Analytics and Data Technologies (MADT)",
    "เศรษฐศาสตร์ธุรกิจและการเงิน",
    "LL.M. กฎหมายธุรกิจ",
    "การพัฒนาทรัพยากรมนุษย์ HROD",
    "นิเทศศาสตร์การตลาดดิจิทัล",
    "ปริญญาเอก DBA บริหารธุรกิจ",
    "ปริญญาเอก D.P.A. รัฐประศาสนศาสตร์",
]

POSITIVE_TEMPLATES = [
    "เรียน {prog} ที่นิด้ามา 1 ปี รู้สึกคุ้มค่ามาก อาจารย์ระดับศาสตราจารย์สอนเอง ได้เคสจริงมาวิเคราะห์ตลอด",
    "อาจารย์ที่ {fac} เก่งและใส่ใจมาก คอนเนกชันเพื่อนร่วมรุ่นดีเยี่ยม มีผู้บริหารระดับสูงหลายองค์กร",
    "สำหรับคนทำงานประจำ แนะนำ {prog} นิด้าเลยครับ ตารางเรียนเสาร์-อาทิตย์จัดดีมาก ไม่กระทบงานประจำ",
    "จบไม่ตรงสายมาเรียน {prog} นิด้า ตอนแรกกังวลมาก แต่วิชาปรับพื้นฐานช่วยได้เยอะมาก ตอนนี้เกรด 3.7 แล้วครับ",
    "หอสมุดสุขุม นวพันธ์ นิด้า ทันสมัยมาก มีฐานข้อมูล Bloomberg กับ Scopus ให้ใช้ฟรี ประทับใจสุดๆ",
    "ชื่อเสียงของ {fac} นิด้า ได้รับการยอมรับในวงการราชการและเอกชนมาก สมัครงานต่อยอดได้เร็ว",
    "คณะบริหารธุรกิจ GSBA นิด้า ได้มาตรฐาน AACSB ระดับโลก ทำให้เนื้อหาหลักสูตรทันสมัยเทียบเท่ายูท็อปต่างประเทศ",
    "สอบสัมภาษณ์ {prog} นิด้า อาจารย์ถามเชิงทรรศนะและตรรกะดีมาก ไม่กดดัน บรรยากาศเป็นกันเอง",
    "ระบบการเรียนออนไลน์และไฮบริดของนิด้าทำได้เสถียรมาก ดูคลิปย้อนหลังทบทวนได้ตลอดเทอม",
    "ทุนการศึกษาประเภทเรียนดีของนิด้าช่วยประหยัดค่าใช้จ่ายได้ 100% เลยครับ แนะนำให้ทุกคนที่มีเกรด ป.ตรี สูงๆ สมัคร",
]

NEGATIVE_TEMPLATES = [
    "ค่าเทอม {prog} ค่อนข้างสูงเมื่อเทียบกับมหาวิทยาลัยรัฐทั่วไป อยากให้มีโครงการผ่อนชำระที่ยืดหยุ่นกว่านี้",
    "การเดินทางไปนิด้า คลองจั่น ช่วงเย็นวันศุกร์รถติดแถวลำสาลีมาก หวังว่า MRT สายสีส้มจะเปิดให้บริการเต็มรูปแบบเร็วๆ นี้",
    "งานกลุ่มและเคสการบ้านของ {prog} หนักมากครับ ต้องแบ่งเวลาเสาร์-อาทิตย์ดีๆ ใครทำงานหนักอาจเหนื่อยหน่อย",
    "เกณฑ์คะแนนภาษาอังกฤษ NIDA TEAP ค่อนข้างเข้มงวด ต้องเตรียมตัวทำข้อสอบ Reading กับ Grammar ล่วงหน้า",
    "ที่จอดรถช่วงเช้าวันเสาร์-อาทิตย์ที่อาคารจอดรถนิด้าค่อนข้างเต็มเร็ว ต้องเผื่อเวลามาก่อนเข้าเรียน",
    "อยากให้เพิ่มวิชาเลือกเกี่ยวกับ Generative AI และ Cloud Architecture ในหลักสูตร {prog} ให้มากกว่านี้",
]

NEUTRAL_TEMPLATES = [
    "กำลังลังเลระหว่างเรียน {prog} ที่นิด้า กับ ม.อื่น เสาร์-อาทิตย์ ใครมีข้อมูลเปรียบเทียบค่าใช้จ่ายบ้างครับ?",
    "สอบถามเกณฑ์การเทียบโอนหน่วยกิตจากสถาบันอื่นมายัง {fac} นิด้า ต้องใช้เกรดเท่าไหร่ และทำเรื่องอย่างไรครับ?",
    "รอบรับสมัคร {prog} ภาค 1/2569 ปิดรับสมัครวันไหนครับ และต้องสอบข้อเขียนอะไรบ้าง?",
    "คนทำงานข้าราชการ เรียน {prog} แนะนำให้เลือก แผน ก (วิทยานิพนธ์) หรือ แผน ข (IS) ดีกว่ากันครับ?",
    "ใครเคยสอบ NIDA TEAP มาแล้วบ้าง ข้อสอบยากประมาณ TOEIC หรือ TOEFL ครับ และมีที่เรียนติวแนะนำไหม?",
    "หลักสูตร {prog} นิด้า มีการไปศึกษาดูงานต่างประเทศ (Study Trip) ในช่วงเทอมไหนบ้างครับ?",
]

INTENTS = ["interest_apply", "inquire_tuition", "ask_scholarship", "compare_programs", "review_advice"]


def generate_social_dataset(target_count: int = 1600) -> Dict[str, List[Dict[str, Any]]]:
    """Generate balanced multi-platform social discussions."""
    platforms = {
        "pantip": int(target_count * 0.35),
        "facebook": int(target_count * 0.25),
        "youtube": int(target_count * 0.20),
        "dekd": int(target_count * 0.12),
        "news": int(target_count * 0.08),
    }

    results: Dict[str, List[Dict[str, Any]]] = {k: [] for k in platforms}

    for platform, count in platforms.items():
        for i in range(count):
            fac = random.choice(FACULTIES)
            prog = random.choice(PROGRAMS)
            sentiment_roll = random.random()

            if sentiment_roll < 0.65:
                text = random.choice(POSITIVE_TEMPLATES).format(fac=fac, prog=prog)
                sentiment = "Positive"
            elif sentiment_roll < 0.85:
                text = random.choice(NEUTRAL_TEMPLATES).format(fac=fac, prog=prog)
                sentiment = "Neutral"
            else:
                text = random.choice(NEGATIVE_TEMPLATES).format(fac=fac, prog=prog)
                sentiment = "Negative"

            intent = random.choice(INTENTS)
            month = random.randint(1, 12)
            day = random.randint(1, 28)
            hour = random.randint(8, 22)
            minute = random.randint(10, 59)

            item = {
                "id": f"{platform}-{i+10001}",
                "platform": platform,
                "title": f"สอบถาม/รีวิว: {prog} {fac} นิด้า (ความคิดเห็นที่ #{i+1})",
                "text": text,
                "author": f"User_{platform}_{random.randint(100, 999)}",
                "published_at": f"2026-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:00Z",
                "url": f"https://www.{platform}.com/topic/nida-{i+10001}",
                "sentiment": sentiment,
                "intent": intent,
                "faculty_tagged": fac,
                "program_tagged": prog,
            }
            results[platform].append(item)

    return results


def write_all_social_data() -> int:
    """Save generated dataset to social_listening/data/*.jsonl files."""
    base_dir = Path(__file__).resolve().parent / "data"
    base_dir.mkdir(parents=True, exist_ok=True)

    dataset = generate_social_dataset(1600)
    total_written = 0

    for platform, items in dataset.items():
        file_path = base_dir / f"comments_{platform}.jsonl"
        with open(file_path, "w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        total_written += len(items)
        print(f"[OK] Written {len(items)} records to {file_path.name}")

    return total_written


if __name__ == "__main__":
    count = write_all_social_data()
    print(f"[SUCCESS] Big Data Social Warehouse populated with {count} records!")
