import unittest
from src.tcp_node import BloomNode
from src.tcp_client import BloomClient

class TestBloomClient(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.nodes = [
            BloomNode(host="127.0.0.1", port=0, capacity=100, error_rate=0.01)
            for _ in range(3)
        ]
        for node in self.nodes:
            await node.start()

        addresses = [f"{n.host}:{n.port}" for n in self.nodes]
        self.client = BloomClient(nodes=addresses, replicas=2)

    async def asyncTearDown(self):
        for node in self.nodes:
            await node.stop()

    async def test_distributed_add_and_contains(self):
        success = await self.client.add("key1", consistency=2)
        self.assertTrue(success)

        found = await self.client.contains("key1", consistency=2)
        self.assertTrue(found)

        missing = await self.client.contains("unknown_key", consistency=1)
        self.assertFalse(missing)

