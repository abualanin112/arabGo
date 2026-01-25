# tests/test_automation.py
import unittest
import logging
from fastapi.testclient import TestClient
from integrations.endpoint_server import app
from integrations import queue_handler, session_manager

class TestAutomation(unittest.TestCase):
    def setUp(self):
        # Silence logging during tests
        logging.getLogger("endpoint_server").setLevel(logging.CRITICAL)
        
        self.client = TestClient(app)
        # Initialize session for tests that require an active session
        session_manager.initialize_session()
        # Clear queue before each test
        while queue_handler.pop_translation():
            pass

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("session", data)

    def test_submit_translation(self):
        payload = {
            "chunk_id": 1,
            "translation": "[1] This is a test translation."
        }
        response = self.client.post("/api/submit_translation", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

        # Verify it reached the queue
        item = queue_handler.pop_translation()
        self.assertIsNotNone(item)
        self.assertEqual(item["chunk_id"], 1)
        self.assertEqual(item["translation"], "[1] This is a test translation.")

    def test_payload_too_large(self):
        # Create a large string
        large_string = "a" * 60000 
        payload = {
            "chunk_id": 1,
            "translation": large_string
        }
        response = self.client.post("/api/submit_translation", json=payload)
        # FastAPI might return 422 for pydantic failure or 413 from our check
        # Our custom check is after pydantic, so let's see.
        self.assertIn(response.status_code, [413, 422])

if __name__ == "__main__":
    unittest.main()
