import unittest
from src.hash_ring import HashRing

class TestHashRing(unittest.TestCase):
    def test_get_node(self):
        ring = HashRing(nodes=["n1", "n2", "n3"], vnodes=50)
        node = ring.get_nodes("user_123", count=1)[0]

        self.assertIn(node, ["n1", "n2", "n3"])
        self.assertEqual(node, ring.get_nodes("user_123", count=1)[0])

    def test_get_nodes_replication(self):
        ring = HashRing(nodes=["n1", "n2", "n3"], vnodes=50)
        replicas = ring.get_nodes("user_test", count=2)

        self.assertEqual(len(replicas), 2)
        self.assertEqual(len(set(replicas)), 2)

    def test_add_remove_node(self):
        ring = HashRing(nodes=["n1", "n2"], vnodes=50)
        ring.add_node("n3")
        self.assertIn("n3", ring.nodes)

        ring.remove_node("n1")
        self.assertNotIn("n1", ring.nodes)
        self.assertIn(ring.get_nodes("test_key_1", count=1)[0], ["n2", "n3"])
