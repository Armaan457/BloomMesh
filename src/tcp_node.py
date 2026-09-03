import asyncio
from typing import Optional
from .bloom_filter import BloomFilter

class BloomNode:
    def __init__(self, host: str = "127.0.0.1", port: int = 0, capacity: int = 1000, error_rate: float = 0.01):
        self.host = host
        self.port = port
        self.bloom = BloomFilter(capacity, error_rate)
        self.server: Optional[asyncio.Server] = None

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break

                parts = line.decode("utf-8").strip().split(maxsplit=1)
                if not parts:
                    continue

                cmd = parts[0].upper()
                arg = parts[1] if len(parts) > 1 else ""

                if cmd == "ADD":
                    self.bloom.add(arg)
                    writer.write(b"OK\n")
                elif cmd == "CONTAINS":
                    resp = b"TRUE\n" if arg in self.bloom else b"FALSE\n"
                    writer.write(resp)
                elif cmd == "SYNC":
                    writer.write(self.bloom.serialize().hex().encode("utf-8") + b"\n")
                elif cmd == "MERGE":
                    data = bytes.fromhex(arg)
                    other = BloomFilter.deserialize(data, self.bloom.capacity, self.bloom.error_rate)
                    self.bloom.merge(other)
                    writer.write(b"OK\n")
                elif cmd == "PING":
                    writer.write(b"PONG\n")
                else:
                    writer.write(b"ERR\n")

                await writer.drain()
        except asyncio.CancelledError:
            pass
        finally:
            writer.close()
            await writer.wait_closed()

    async def start(self) -> None:
        self.server = await asyncio.start_server(self.handle_client, self.host, self.port)
        if self.server.sockets:
            self.port = self.server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        if self.server:
            self.server.close()
            await self.server.wait_closed()

