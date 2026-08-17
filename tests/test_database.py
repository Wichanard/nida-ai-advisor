import unittest
from app.models.database import (
    init_db,
    save_chat_message,
    get_chat_history,
    record_feedback,
    get_system_stats,
)


class TestDatabase(unittest.TestCase):
    def setUp(self):
        init_db()

    def test_chat_save_and_history(self):
        session_id = "test-db-session-01"
        msg_id = save_chat_message(
            session_id=session_id,
            sender="user",
            message="สวัสดีครับ อยากเรียน MBA",
        )
        self.assertGreater(msg_id, 0)

        history = get_chat_history(session_id)
        self.assertGreaterEqual(len(history), 1)
        self.assertEqual(history[0]["message"], "สวัสดีครับ อยากเรียน MBA")

    def test_record_feedback_and_stats(self):
        session_id = "test-db-session-02"
        success = record_feedback(session_id=session_id, rating=1, feedback_text="ดีมาก")
        self.assertTrue(success)

        stats = get_system_stats()
        self.assertIn("total_sessions", stats)
        self.assertIn("satisfaction_rate", stats)


if __name__ == "__main__":
    unittest.main()
