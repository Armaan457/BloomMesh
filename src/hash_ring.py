import bisect
import hashlib
from typing import Optional

class HashRing:
    def __init__(self, nodes: Optional[list[str]] = None, vnodes: int = 100):
        self.vnodes = vnodes
        self.ring: dict[int, str] = {}
        self.sorted_keys: list[int] = []
        self.nodes: set[str] = set()

        if nodes:
            for node in nodes:
                self.add_node(node)

    def hash(self, key: str) -> int:
        digest = hashlib.md5(key.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big")

    def add_node(self, node: str) -> None:
        if node in self.nodes:
            return
        self.nodes.add(node)
        for i in range(self.vnodes):
            h = self.hash(f"{node}#{i}")
            self.ring[h] = node
            bisect.insort(self.sorted_keys, h)

    def remove_node(self, node: str) -> None:
        if node not in self.nodes:
            return
        self.nodes.remove(node)
        for i in range(self.vnodes):
            h = self.hash(f"{node}#{i}")
            self.ring.pop(h, None)
        self.sorted_keys = sorted(self.ring.keys())

    def get_nodes(self, key: str, count: int = 1) -> list[str]:
        if not self.ring:
            return []

        count = min(count, len(self.nodes))
        h = self.hash(key)
        idx = bisect.bisect_right(self.sorted_keys, h)

        result: list[str] = []
        seen: set[str] = set()
        total_keys = len(self.sorted_keys)

        for i in range(total_keys):
            pos = (idx + i) % total_keys
            node = self.ring[self.sorted_keys[pos]]
            if node not in seen:
                seen.add(node)
                result.append(node)
                if len(result) == count:
                    break

        return result


