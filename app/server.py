import json
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from src.tcp_node import BloomNode
from .utils import PORTS, nodes, node_keys, client, connections, get_state, handle_action

UI_DIR = Path(__file__).resolve().parent.parent / "ui"
if not UI_DIR.exists():
    UI_DIR = Path(__file__).resolve().parent / "ui"

@asynccontextmanager
async def lifespan(app: FastAPI):
    for port in PORTS:
        addr = f"127.0.0.1:{port}"
        node = BloomNode(host="127.0.0.1", port=port, capacity=1000, error_rate=0.01)
        await node.start()
        nodes[addr] = node
        node_keys[addr] = []
        client.ring.add_node(addr)

    yield
    for node in list(nodes.values()):
        await node.stop()
    nodes.clear()
    node_keys.clear()
    client.ring.nodes.clear()
    client.ring.ring.clear()
    client.ring.sorted_keys.clear()


app = FastAPI(lifespan=lifespan)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections.append(websocket)
    try:
        await websocket.send_json(get_state())
        while True:
            text = await websocket.receive_text()
            await handle_action(json.loads(text))
    except WebSocketDisconnect:
        if websocket in connections:
            connections.remove(websocket)


app.mount("/", StaticFiles(directory=UI_DIR, html=True), name="ui")
