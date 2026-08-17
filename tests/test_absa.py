import unittest
from social_listening.advanced_analytics import (
    extract_aspects,
    compute_absa_metrics,
    compute_anomaly_radar,
    generate_executive_swot_summary,
)


class TestABSA(unittest.TestCase):
    def test_extract_aspects(self):
        text = "อาจารย์สอนดีมาก แต่ค่าเทอมค่อนข้างแพงและรถติดแถวบางกะปิ"
        aspects = extract_aspects(text)
        self.assertIn("academics_faculty", aspects)
        self.assertIn("tuition_value", aspects)
        self.assertIn("campus_schedule", aspects)

    def test_compute_absa_metrics(self):
        sample_comments = [
            {"text": "อาจารย์นิด้าสอนดีมาก คุ้มค่า", "sentiment": "Positive"},
            {"text": "ค่าเทอมแพงไปหน่อย", "sentiment": "Negative"},
            {"text": "ศิษย์เก่าคอนเนกชันดีมาก ช่วยเรื่องงาน", "sentiment": "Positive"},
        ]
        metrics = compute_absa_metrics(sample_comments)
        self.assertIn("academics_faculty", metrics)
        self.assertIn("career_network", metrics)
        self.assertGreaterEqual(metrics["academics_faculty"]["satisfaction_index"], 0.0)

    def test_compute_anomaly_radar(self):
        sample_comments = [
            {"text": "ดีมาก", "sentiment": "Positive"},
            {"text": "ยอดเยี่ยม", "sentiment": "Positive"},
        ]
        radar = compute_anomaly_radar(sample_comments)
        self.assertIn("crisis_level", radar)
        self.assertIn("crisis_score", radar)

    def test_executive_swot_summary(self):
        sample_comments = [{"text": "หลักสูตรยอดเยี่ยม", "sentiment": "Positive"}]
        swot = generate_executive_swot_summary(sample_comments)
        self.assertIn("strengths", swot)
        self.assertIn("strategic_actions", swot)


if __name__ == "__main__":
    unittest.main()
