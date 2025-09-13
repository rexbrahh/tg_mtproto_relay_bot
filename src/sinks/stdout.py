from __future__ import annotations

from typing import Any, Dict

from ..telemetry import log_event


class StdoutSink:
    def __init__(self) -> None:
        pass

    async def emit(self, payload: Dict[str, Any]) -> None:
        log_event("signal_event", **payload)
