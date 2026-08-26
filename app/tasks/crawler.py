import os
import sys
from pathlib import Path
import chromadb
import time

# This script simulates a web crawler that scrapes NIDA's website and updates ChromaDB.
# In a real enterprise system, this would use BeautifulSoup or Scrapy and run via APScheduler or Celery.

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(BASE_DIR))

def run_crawler():
    print("🕷️ Starting NIDA Web Crawler...")
    print("🔗 Connecting to https://www.nida.ac.th/th/programs")
    time.sleep(2)
    
    # Simulated scraped data
    new_courses = [
        {
            "id": "prog_crawler_001",
            "document": "บริหารธุรกิจมหาบัณฑิต (MBA) นวัตกรรมธุรกิจ หลักสูตรปรับปรุงใหม่ เรียนเสาร์-อาทิตย์ ค่าเทอม 250000 บาท",
            "metadata": {
                "faculty": "บริหารธุรกิจ",
                "degree": "ป.โท",
                "study_mode": "เสาร์-อาทิตย์",
                "numeric_fee": 250000.0
            }
        },
        {
            "id": "prog_crawler_002",
            "document": "วิทยาศาสตรมหาบัณฑิต วิทยาการข้อมูล (Data Science) เน้น AI และ Machine Learning ภาคพิเศษ เรียนค่ำ ค่าเทอม 180000 บาท",
            "metadata": {
                "faculty": "สถิติประยุกต์",
                "degree": "ป.โท",
                "study_mode": "ภาคพิเศษ",
                "numeric_fee": 180000.0
            }
        }
    ]
    
    print(f"✅ Scraped {len(new_courses)} updated courses.")
    print("💾 Upserting to ChromaDB Dynamic Vector Store...")
    
    from app.services.vector_store import NIDAVectorStore
    vs = NIDAVectorStore.get_instance()
    
    # In ChromaDB, upsert updates existing documents or inserts new ones.
    docs = [c["document"] for c in new_courses]
    metadatas = [c["metadata"] for c in new_courses]
    ids = [c["id"] for c in new_courses]
    
    try:
        vs.collection.upsert(
            documents=docs,
            metadatas=metadatas,
            ids=ids
        )
        print("🎉 Successfully updated ChromaDB!")
    except Exception as e:
        print(f"❌ Failed to update ChromaDB: {e}")

if __name__ == "__main__":
    run_crawler()
