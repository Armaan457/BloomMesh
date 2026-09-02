import hashlib
import math

class BloomFilter:
    def __init__(self, capacity: int = 1000, error_rate: float = 0.01):
        self.capacity = capacity
        self.error_rate = error_rate
        self.m = max(8, math.ceil(-1 * capacity * math.log(error_rate) / (math.log(2) ** 2)))
        self.k = max(1, round((self.m / capacity) * math.log(2)))
        self.bit_array = bytearray((self.m + 7) // 8)

    def hashes(self, item: str) -> list[int]:
        raw = item.encode("utf-8")
        digest = hashlib.sha256(raw).digest()
        h1 = int.from_bytes(digest[:8], "big")
        h2 = int.from_bytes(digest[8:16], "big") or 1
        return [(h1 + i * h2) % self.m for i in range(self.k)]

    def add(self, item: str) -> None:
        for bit in self.hashes(item):
            self.bit_array[bit // 8] |= 1 << (bit % 8)

    def contains(self, item: str) -> bool:
        for bit in self.hashes(item):
            if not (self.bit_array[bit // 8] & (1 << (bit % 8))):
                return False
        return True

    def __contains__(self, item: str) -> bool:
        return self.contains(item)

    def merge(self, other: "BloomFilter") -> None:
        if self.m != other.m or self.k != other.k:
            raise ValueError("Incompatible Bloom filters")
        for i in range(len(self.bit_array)):
            self.bit_array[i] |= other.bit_array[i]

    def serialize(self) -> bytes:
        return bytes(self.bit_array)

    @classmethod
    def deserialize(cls, data: bytes, capacity: int = 1000, error_rate: float = 0.01) -> "BloomFilter":
        bf = cls(capacity, error_rate)
        bf.bit_array = bytearray(data)
        return bf
