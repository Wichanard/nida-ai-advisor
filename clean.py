import sqlite3
conn = sqlite3.connect('data/nida_enterprise.db')
c = conn.cursor()
c.execute("DELETE FROM chat_messages WHERE message LIKE '%Gemini API ขัดข้อง%'")
c.execute("DELETE FROM chat_messages WHERE message LIKE '%ขออภัยครับ ตอนนี้ระบบ AI (ทั้งออนไลน์และออฟไลน์) ไม่พร้อมใช้งาน%'")
conn.commit()
print("Cleaned up old error messages.")
