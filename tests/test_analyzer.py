import unittest
from social_listening.analyzer import analyze_sentiment_and_intent, tokenize_thai, get_word_frequencies


class TestAnalyzer(unittest.TestCase):
    def test_analyze_sentiment_positive(self):
        res = analyze_sentiment_and_intent("เรียนต่อ MBA นิด้า อาจารย์ดีมากและสังคมอบอุ่น คุ้มค่ามากครับ")
        self.assertEqual(res["sentiment"], "Positive")

    def test_analyze_sentiment_negation(self):
        res = analyze_sentiment_and_intent("หลักสูตรไม่ได้ดีขนาดนั้น ระบบลงทะเบียนแย่มาก")
        self.assertEqual(res["sentiment"], "Negative")

    def test_analyze_sentiment_question(self):
        res = analyze_sentiment_and_intent("ค่าเทอม นิด้า ป.โท เท่าไหร่ครับ สมัครยังไง?")
        self.assertEqual(res["sentiment"], "Question")
        self.assertIn(res["intent"], ["Tuition & Cost", "Admission & Requirements"])

    def test_tokenize_thai(self):
        tokens = tokenize_thai("เรียนต่อ ปริญญาโท NIDA ด้าน Data Science")
        self.assertIsInstance(tokens, list)
        self.assertGreater(len(tokens), 0)


if __name__ == "__main__":
    unittest.main()
