import unittest
from app.services.agent_engine import NIDAAgentEngine, tool_search_courses, tool_compare_programs
from app.models.database import get_chat_history


class TestAgentEngine(unittest.TestCase):
    def test_tool_search_courses(self):
        results = tool_search_courses("MBA เสาร์-อาทิตย์", top_k=2)
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    def test_tool_compare_programs(self):
        comp = tool_compare_programs("MBA", "วิทยาการข้อมูล")
        self.assertIn("programs", comp)

    def test_multi_turn_chat_execution(self):
        session_id = "test-session-agent-01"
        res1 = NIDAAgentEngine.execute_chat(
            session_id=session_id,
            user_message="สนใจเรียนต่อ MBA วันเสาร์-อาทิตย์ ค่าเทอมไม่แพง",
        )
        self.assertIn("reply", res1)
        self.assertGreater(len(res1["reply"]), 10)

    def test_greeting_response_natural(self):
        session_id = "test-session-greeting-01"
        res = NIDAAgentEngine.execute_chat(
            session_id=session_id,
            user_message="สวัสดีครับ",
        )
        self.assertIn("reply", res)
        # Verify it greeted warmly and did not dump random course/regulation data
        self.assertIn("สวัสดี", res["reply"])
        self.assertEqual(len(res.get("recommended_programs", [])), 0)
        self.assertEqual(len(res.get("tools_used", [])), 0)

    def test_meta_knowledge_scope_query(self):
        session_id = "test-session-meta-01"
        res = NIDAAgentEngine.execute_chat(
            session_id=session_id,
            user_message="คุณรู้เกี่ยวกับนิด้า มากแค่ไหน",
        )
        self.assertIn("reply", res)
        # Verify it directly answers its knowledge scope without dumping course cards
        self.assertIn("73 สาขาวิชา", res["reply"])
        self.assertIn("AACSB", res["reply"])
        self.assertEqual(len(res.get("recommended_programs", [])), 0)

    def test_faculty_directory_query(self):
        session_id = "test-session-faculty-01"
        res = NIDAAgentEngine.execute_chat(
            session_id=session_id,
            user_message="นิด้ามีกี่คณะ คณะอะไรบ้าง",
        )
        self.assertIn("reply", res)
        self.assertIn("คณะรัฐประศาสนศาสตร์", res["reply"])
        self.assertIn("คณะบริหารธุรกิจ", res["reply"])
        self.assertEqual(len(res.get("recommended_programs", [])), 0)

    def test_campus_location_query(self):
        session_id = "test-session-campus-01"
        res = NIDAAgentEngine.execute_chat(
            session_id=session_id,
            user_message="นิด้าอยู่ที่ไหน เดินทางยังไง",
        )
        self.assertIn("reply", res)
        self.assertIn("เสรีไทย", res["reply"])
        self.assertEqual(len(res.get("recommended_programs", [])), 0)


if __name__ == "__main__":
    unittest.main()
