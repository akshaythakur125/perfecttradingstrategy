from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set
import json
import asyncio

from engines.data_collector import DataCollector
from engines.scanner import ScannerEngine

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()


@router.websocket("/ws/scanner")
async def websocket_scanner(websocket: WebSocket):
    await manager.connect(websocket)
    collector = DataCollector()
    scanner = ScannerEngine()

    try:
        while True:
            data = await websocket.receive_text()
            try:
                params = json.loads(data)
                exchange = params.get("exchange", "BINANCE")
                pairs = await collector.get_top_pairs_by_volume(exchange, 30)
                signals = await scanner.scan_all_pairs(pairs, exchange)
                await websocket.send_json({"type": "scan_results", "data": signals})
            except json.JSONDecodeError:
                pairs = await collector.get_top_pairs_by_volume("BINANCE", 30)
                signals = await scanner.scan_all_pairs(pairs, "BINANCE")
                await websocket.send_json({"type": "scan_results", "data": signals})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
