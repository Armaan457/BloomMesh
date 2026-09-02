import unittest
from src.bloom_filter import BloomFilter

class TestBloomFilter(unittest.TestCase):
    def test_add_and_contains(self):
        bf = BloomFilter(capacity=100, error_rate=0.01)
        bf.add("apple")
        bf.add("banana")

        self.assertTrue("apple" in bf)
        self.assertTrue("banana" in bf)
        self.assertFalse("orange" in bf)

    def test_merge(self):
        bf1 = BloomFilter(capacity=100, error_rate=0.01)
        bf2 = BloomFilter(capacity=100, error_rate=0.01)
        bf1.add("apple")
        bf2.add("banana")
        bf1.merge(bf2)

        self.assertTrue("apple" in bf1)
        self.assertTrue("banana" in bf1)

    def test_serialization(self):
        bf = BloomFilter(capacity=100, error_rate=0.01)
        bf.add("apple")
        data = bf.serialize()
        restored = BloomFilter.deserialize(data, capacity=100, error_rate=0.01)

        self.assertTrue("apple" in restored)
        self.assertFalse("banana" in restored)

    def test_deserialization(self):
        bf = BloomFilter(capacity=100, error_rate=0.01)
        bf.add("apple")
        bf.add("banana")
        data = bf.serialize()
        restored = BloomFilter.deserialize(data,capacity=100,error_rate=0.01)

        self.assertTrue("apple" in restored)
        self.assertTrue("banana" in restored)
        self.assertFalse("orange" in restored)