import asyncio
import unittest
from src.tcp_node import BloomNode

class TestBloomNode(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.node = BloomNode(host="127.0.0.1", port=0, capacity=100, error_rate=0.01)
        await self.node.start()

    async def asyncTearDown(self):
        await self.node.stop()

    async def _send_command(self, cmd: str) -> str:
        reader, writer = await asyncio.open_connection("127.0.0.1", self.node.port)
        writer.write(f"{cmd}\n".encode("utf-8"))
        await writer.drain()
        resp = await reader.readline()
        writer.close()
        await writer.wait_closed()
        return resp.decode("utf-8").strip()

    async def test_add_and_contains(self):
        self.assertEqual(await self._send_command("ADD apple"), "OK")
        self.assertEqual(await self._send_command("CONTAINS apple"), "TRUE")
        self.assertEqual(await self._send_command("CONTAINS banana"), "FALSE")

    async def test_sync_and_merge(self):
        node2 = BloomNode(host="127.0.0.1", port=0, capacity=100, error_rate=0.01)
        await node2.start()
        try:
            await self._send_command("ADD apple")
            hex_data = await self._send_command("SYNC")

            r2, w2 = await asyncio.open_connection("127.0.0.1", node2.port)
            w2.write(f"MERGE {hex_data}\n".encode("utf-8"))
            await w2.drain()
            resp = await r2.readline()
            self.assertEqual(resp.decode("utf-8").strip(), "OK")

            w2.write(b"CONTAINS apple\n")
            await w2.drain()
            resp = await r2.readline()
            self.assertEqual(resp.decode("utf-8").strip(), "TRUE")

            w2.close()
            await w2.wait_closed()
        finally:
            await node2.stop()


