import unittest
from app.services.recommend import recommend_courses, extract_max_budget, load_programs


class TestRecommend(unittest.TestCase):
    def test_extract_max_budget(self):
        self.assertEqual(extract_max_budget("ค่าเทอมไม่เกิน 1 แสนบาท"), 100000.0)
        self.assertEqual(extract_max_budget("งบ 50,000"), 50000.0)
        self.assertEqual(extract_max_budget("ประมาณ 2 หมื่น"), 20000.0)

    def test_load_programs(self):
        programs = load_programs()
        self.assertIsInstance(programs, list)
        self.assertGreater(len(programs), 0)
        self.assertIn("program", programs[0])
        self.assertIn("faculty", programs[0])

    def test_recommend_courses(self):
        results = recommend_courses("สนใจ MBA เสาร์ อาทิตย์", degree_filter="ป.โท", top_k=3)
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        self.assertIn("match_score", results[0])
        self.assertIn("ai_reasoning", results[0])


if __name__ == "__main__":
    unittest.main()
