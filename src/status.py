from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Any, Deque, Dict, Optional

from fastapi import FastAPI
import uvicorn


class StatusState:
    def __init__(self, max_items: int = 20) -> None:
        self.started_at = datetime.utcnow()
        self.total_signals = 0
        self.last_event: Optional[Dict[str, Any]] = None
        self.recent: Deque[Dict[str, Any]] = deque(maxlen=max_items)

    def record(self, event: Dict[str, Any]) -> None:
        self.total_signals += 1
        self.last_event = event
        self.recent.appendleft(event)


def build_app(state: StatusState) -> FastAPI:
    app = FastAPI()

    @app.get("/status")
    def status() -> Dict[str, Any]:
        return {
            "started_at": state.started_at.isoformat() + "Z",
            "uptime_sec": (datetime.utcnow() - state.started_at).total_seconds(),
            "total_signals": state.total_signals,
            "last_event": state.last_event,
            "recent": list(state.recent),
        }

    return app


async def serve_status(host: str, port: int, state: StatusState) -> None:
    config = uvicorn.Config(build_app(state), host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()
