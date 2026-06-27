import os
import unittest

os.environ.setdefault("DATABASE_URL", "postgresql://aravindganesan@localhost:5432/todoapp")

from app import app as flask_app, get_connection


class ActivityTrackerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = flask_app.test_client()

    def tearDown(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM todo_history WHERE todo_id IN (SELECT id FROM todos WHERE title LIKE 'unit test%')"
                )
                cur.execute("DELETE FROM todos WHERE title LIKE 'unit test%'")

    def test_list_todos_returns_json_list(self):
        response = self.client.get("/api/todos")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.get_json(), list)

    def test_create_todo_persists_record(self):
        response = self.client.post(
            "/api/todos",
            json={"title": "unit test todo", "username": "tester", "workflow_step": "backlog"},
        )
        self.assertEqual(response.status_code, 201)
        payload = response.get_json()
        self.assertEqual(payload["title"], "unit test todo")
        self.assertEqual(payload["username"], "tester")
        self.assertEqual(payload["workflow_step"], "backlog")

    def test_move_todo_updates_workflow_state(self):
        create_response = self.client.post(
            "/api/todos",
            json={"title": "unit test move", "username": "tester", "workflow_step": "backlog"},
        )
        todo_id = create_response.get_json()["id"]

        move_response = self.client.post(
            f"/api/todos/{todo_id}/move",
            json={"workflow_step": "in_progress", "username": "tester"},
        )

        self.assertEqual(move_response.status_code, 200)
        payload = move_response.get_json()
        self.assertEqual(payload["workflow_step"], "in_progress")
        self.assertEqual(payload["username"], "tester")

    def test_history_endpoint_returns_change_log(self):
        create_response = self.client.post(
            "/api/todos",
            json={"title": "unit test history", "username": "tester", "workflow_step": "backlog"},
        )
        todo_id = create_response.get_json()["id"]
        self.client.post(
            f"/api/todos/{todo_id}/move",
            json={"workflow_step": "in_progress", "username": "tester"},
        )
        self.client.post(
            f"/api/todos/{todo_id}/move",
            json={"workflow_step": "completed", "username": "tester"},
        )

        history_response = self.client.get(f"/api/todos/{todo_id}/history")
        self.assertEqual(history_response.status_code, 200)
        history = history_response.get_json()
        self.assertTrue(len(history) >= 3)
        self.assertEqual(history[0]["current_step"], "backlog")
        self.assertEqual(history[1]["previous_step"], "backlog")
        self.assertEqual(history[1]["current_step"], "in_progress")
        self.assertEqual(history[-1]["previous_step"], "in_progress")
        self.assertEqual(history[-1]["current_step"], "completed")


if __name__ == "__main__":
    unittest.main()
