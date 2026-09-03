import asyncio
from .hash_ring import HashRing

class BloomClient:
    def __init__(self, nodes: list[str], replicas: int = 1):
        self.replicas = replicas
        self.ring = HashRing(nodes=nodes)

    async def send(self, node: str, cmd: str) -> str:
        host, port_str = node.split(":")
        reader, writer = await asyncio.open_connection(host, int(port_str))
        try:
            writer.write(f"{cmd}\n".encode("utf-8"))
            await writer.drain()
            resp = await reader.readline()
            return resp.decode("utf-8").strip()
        finally:
            writer.close()
            await writer.wait_closed()

    async def add(self, key: str, consistency: int = 1) -> bool:
        nodes = self.ring.get_nodes(key, count=self.replicas)
        tasks = [self.send(node, f"ADD {key}") for node in nodes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        success_count = sum(1 for r in results if r == "OK")
        return success_count >= consistency

    async def contains(self, key: str, consistency: int = 1) -> bool:
        nodes = self.ring.get_nodes(key, count=self.replicas)
        tasks = [self.send(node, f"CONTAINS {key}") for node in nodes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        true_count = sum(1 for r in results if r == "TRUE")
        return true_count >= consistency

