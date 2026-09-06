import json
import unittest
from fastapi.testclient import TestClient
from app.server import app
from app.utils import resolve_consistency

class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_ctx = TestClient(app)
        cls.client = cls.client_ctx.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_ctx.__exit__(None, None, None)

    def test_index_route(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("BloomMesh", response.text)

    def test_resolve_consistency(self):
        self.assertEqual(resolve_consistency({"choice": "single"}, 4), (1, 1, "SINGLE (1/1)"))
        self.assertEqual(resolve_consistency({"choice": "primary_plus_one"}, 4), (2, 2, "PRIMARY+1 (2/2)"))
        self.assertEqual(resolve_consistency({"choice": "quorum"}, 4), (3, 2, "QUORUM (2/3)"))
        self.assertEqual(resolve_consistency({"choice": "all"}, 4), (4, 4, "ALL (4/4)"))
        self.assertEqual(resolve_consistency({"choice": "custom", "replicas": 3, "consistency": 1}, 4), (3, 1, "CUSTOM (1/3)"))
        # Dynamic adaptation when nodes are reduced
        self.assertEqual(resolve_consistency({"choice": "quorum"}, 2), (2, 2, "QUORUM (2/2)"))
        self.assertEqual(resolve_consistency({"choice": "all"}, 2), (2, 2, "ALL (2/2)"))
        self.assertEqual(resolve_consistency({"choice": "quorum"}, 1), (1, 1, "QUORUM (1/1)"))

    def test_websocket_initial_state(self):
        with self.client.websocket_connect("/ws") as ws:
            data = ws.receive_json()
            self.assertEqual(data.get("type"), "state")
            nodes = data.get("nodes", [])
            self.assertEqual(len(nodes), 4)
            self.assertTrue(all(n["online"] for n in nodes))
            self.assertTrue(len(data.get("vnodes", [])) > 0)

    def test_websocket_add_and_contains(self):
        with self.client.websocket_connect("/ws") as ws:
            _ = ws.receive_json()  

            ws.send_text(json.dumps({"action": "add", "key": "test_user_42", "choice": "quorum"}))
            add_result = ws.receive_json()
            self.assertEqual(add_result.get("action"), "add")
            self.assertEqual(add_result.get("key"), "test_user_42")
            self.assertTrue(add_result.get("success"))
            self.assertEqual(add_result.get("mode"), "QUORUM (2/3)")
            self.assertGreater(len(add_result.get("targets", [])), 0)

            state_update = ws.receive_json()
            self.assertEqual(state_update.get("type"), "state")

            ws.send_text(json.dumps({"action": "contains", "key": "test_user_42", "choice": "quorum"}))
            contains_result = ws.receive_json()
            self.assertEqual(contains_result.get("action"), "contains")
            self.assertTrue(contains_result.get("found"))

            ws.send_text(json.dumps({"action": "contains", "key": "non_existent_key_xyz", "choice": "quorum"}))
            missing_result = ws.receive_json()
            self.assertFalse(missing_result.get("found"))

    def test_websocket_toggle_and_sync(self):
        with self.client.websocket_connect("/ws") as ws:
            _ = ws.receive_json()  
            target_addr = "127.0.0.1:9001"

            ws.send_text(json.dumps({"action": "toggle_node", "node_id": target_addr}))
            offline_state = ws.receive_json()
            node = next(n for n in offline_state["nodes"] if n["id"] == target_addr)
            self.assertFalse(node["online"])

            ws.send_text(json.dumps({"action": "toggle_node", "node_id": target_addr}))
            online_state = ws.receive_json()
            node = next(n for n in online_state["nodes"] if n["id"] == target_addr)
            self.assertTrue(node["online"])

            ws.send_text(json.dumps({"action": "sync"}))
            sync_state = ws.receive_json()
            self.assertEqual(sync_state.get("type"), "state")

    def test_websocket_add_and_remove_node(self):
        with self.client.websocket_connect("/ws") as ws:
            _ = ws.receive_json()

            ws.send_text(json.dumps({"action": "add_node"}))
            state_after_add = ws.receive_json()
            initial_count = len(state_after_add["nodes"])

            ws.send_text(json.dumps({"action": "remove_node"}))
            state_after_remove = ws.receive_json()
            self.assertEqual(len(state_after_remove["nodes"]), initial_count - 1)