import time
from typing import Any
from fastapi import WebSocket
from src.bloom_filter import BloomFilter
from src.tcp_node import BloomNode
from src.tcp_client import BloomClient

PORTS = [9001, 9002, 9003, 9004]
nodes: dict[str, BloomNode] = {}
node_keys: dict[str, list[str]] = {}
client = BloomClient(nodes=[], replicas=2)
connections: list[WebSocket] = []

def resolve_consistency(data: dict[str, Any], total_nodes: int) -> tuple[int, int, str]:
    total = max(1, total_nodes)
    choice = str(data.get("choice") or data.get("level") or data.get("consistency") or "quorum").lower()

    if choice in ("single", "1"):
        return 1, 1, "SINGLE (1/1)"
    elif choice in ("primary_plus_one", "primary+1", "2"):
        r = min(2, total)
        return r, r, f"PRIMARY+1 ({r}/{r})"
    elif choice in ("quorum", "3"):
        r = min(3, total)
        w = (r // 2) + 1
        return r, w, f"QUORUM ({w}/{r})"
    elif choice in ("all", "4"):
        return total, total, f"ALL ({total}/{total})"
    elif choice == "custom":
        r = max(1, min(int(data.get("replicas") or 3), total))
        c = max(1, min(int(data.get("consistency") or 1), r))
        return r, c, f"CUSTOM ({c}/{r})"
    else:
        c = int(data.get("consistency") or 2)
        r = int(data.get("replicas") or c)
        r = max(1, min(r, total))
        c = max(1, min(c, r))
        return r, c, f"CUSTOM ({c}/{r})"


def get_state() -> dict[str, Any]:
    node_data = []
    for i, (addr, node) in enumerate(nodes.items(), start=1):
        online = node.server is not None
        m = node.bloom.m
        k = node.bloom.k
        capacity = node.bloom.capacity
        set_bits = sum(bin(byte).count("1") for byte in node.bloom.bit_array) if online else 0
        fill_ratio = (set_bits / m) if m > 0 else 0
        est_fpr = (fill_ratio ** k) if fill_ratio > 0 else 0
        keys = node_keys.get(addr, [])

        node_data.append({
            "id": addr,
            "name": f"Node {i}",
            "host": addr,
            "online": online,
            "m": m,
            "k": k,
            "capacity": capacity,
            "set_bits": set_bits,
            "fill_pct": round(fill_ratio * 100, 2),
            "est_fpr": round(est_fpr * 100, 4),
            "memory_bytes": len(node.bloom.bit_array) if online else 0,
            "keys": keys,
        })

    vnodes = [{"hash": h / (2**32), "nodeId": n} for h, n in client.ring.ring.items()]
    vnodes.sort(key=lambda x: x["hash"])

    return {"type": "state", "nodes": node_data, "vnodes": vnodes}

async def broadcast(message: dict[str, Any]) -> None:
    dead = []
    for ws in connections:
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in connections:
            connections.remove(ws)

async def handle_action(data: dict[str, Any]) -> None:
    action = data.get("action")

    if action == "add":
        key = data.get("key", "").strip()
        if not key:
            return

        replicas, consistency, mode_label = resolve_consistency(data, len(nodes))
        t0 = time.perf_counter()
        targets = client.ring.get_nodes(key, count=replicas)
        success = await client.add(key, consistency=consistency, replicas=replicas)
        latency = round((time.perf_counter() - t0) * 1000, 2)

        if success:
            for target in targets:
                if target in nodes and nodes[target].server is not None:
                    if target in node_keys and key not in node_keys[target]:
                        node_keys[target].append(key)

        await broadcast({
            "type": "op_result",
            "action": "add",
            "key": key,
            "success": success,
            "targets": targets,
            "mode": mode_label,
            "latency_ms": latency,
        })
        await broadcast(get_state())

    elif action == "contains":
        key = data.get("key", "").strip()
        if not key:
            return

        replicas, consistency, mode_label = resolve_consistency(data, len(nodes))
        t0 = time.perf_counter()
        targets = client.ring.get_nodes(key, count=replicas)
        found = await client.contains(key, consistency=consistency, replicas=replicas)
        latency = round((time.perf_counter() - t0) * 1000, 2)

        await broadcast({
            "type": "op_result",
            "action": "contains",
            "key": key,
            "found": found,
            "targets": targets,
            "mode": mode_label,
            "latency_ms": latency,
        })

    elif action == "toggle_node":
        node_id = data.get("node_id")
        if node_id in nodes:
            node = nodes[node_id]
            if node.server:
                await node.stop()
            else:
                port = int(node_id.split(":")[1])
                new_node = BloomNode(host="127.0.0.1", port=port, capacity=1000, error_rate=0.01)
                new_node.bloom = node.bloom
                await new_node.start()
                nodes[node_id] = new_node

            await broadcast(get_state())

    elif action == "add_node":
        next_port = max([int(addr.split(":")[1]) for addr in nodes.keys()] + [9000]) + 1
        addr = f"127.0.0.1:{next_port}"
        node = BloomNode(host="127.0.0.1", port=next_port, capacity=1000, error_rate=0.01)
        await node.start()
        nodes[addr] = node
        node_keys[addr] = []
        client.ring.add_node(addr)
        await broadcast(get_state())

    elif action == "remove_node":
        node_id = data.get("node_id")
        if not node_id and len(nodes) > 1:
            node_id = list(nodes.keys())[-1]

        if node_id and node_id in nodes and len(nodes) > 1:
            node = nodes.pop(node_id)
            if node.server:
                await node.stop()
            node_keys.pop(node_id, None)
            client.ring.remove_node(node_id)
            await broadcast(get_state())

    elif action == "sync":
        active = [addr for addr, node in nodes.items() if node.server]
        merged_bf = BloomFilter(capacity=1000, error_rate=0.01)

        for addr in active:
            hex_data = await client.send(addr, "SYNC")
            if hex_data and hex_data != "ERR_CONN":
                other = BloomFilter.deserialize(bytes.fromhex(hex_data), capacity=1000, error_rate=0.01)
                merged_bf.merge(other)

        serialized_hex = merged_bf.serialize().hex()
        for addr in active:
            await client.send(addr, f"MERGE {serialized_hex}")

        all_active_keys = sorted(list({k for addr in active for k in node_keys.get(addr, [])}))
        for addr in active:
            node_keys[addr] = list(all_active_keys)

        await broadcast(get_state())
