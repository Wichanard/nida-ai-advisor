import unittest
from fastapi.testclient import TestClient
from app.main import app


class TestEnterpriseAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_check(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "online")
        self.assertIn("system_stats", data)

    def test_chat_api(self):
        resp = self.client.post(
            "/api/v1/chat",
            json={
                "session_id": "test-api-session-01",
                "message": "สนใจเรียนต่อ MBA วันเสาร์-อาทิตย์",
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("reply", data)
        self.assertIn("tools_used", data)
        self.assertIn("recommended_programs", data)

    def test_absa_api(self):
        resp = self.client.get("/api/v1/analytics/absa")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("aspect_sentiment_breakdown", data)

    def test_executive_summary_api(self):
        resp = self.client.get("/api/v1/analytics/executive-summary")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("executive_swot", data)

    def test_feedback_api(self):
        resp = self.client.post(
            "/api/v1/feedback",
            json={
                "session_id": "test-api-session-01",
                "rating": 1,
                "feedback_text": "ยอดเยี่ยมมาก",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "success")


if __name__ == "__main__":
    unittest.main()
