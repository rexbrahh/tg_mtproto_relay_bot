from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Deque, Dict

from .telemetry import log_event


@dataclass
class StateManager:
    state_dir: Path
    last_seen_file: Path
    _ring: Deque[int] = field(default_factory=lambda: deque(maxlen=1024))
    last_seen_by_source: Dict[str, int] = field(default_factory=dict)

    def __init__(self, state_dir: str, last_seen_file: str) -> None:
        self.state_dir = Path(state_dir)
        self.last_seen_file = self.state_dir / last_seen_file
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._ring = deque(maxlen=1024)
        self.last_seen_by_source = {}
        self._load()

    # Persistence
    def _load(self) -> None:
        try:
            if self.last_seen_file.exists():
                data = json.loads(self.last_seen_file.read_text())
                if isinstance(data, dict):
                    self.last_seen_by_source = {str(k): int(v) for k, v in data.items()}
        except Exception as exc:
            log_event("state_load_error", level="error", error=str(exc))

    def flush(self) -> None:
        try:
            tmp = json.dumps(self.last_seen_by_source)
            self.last_seen_file.write_text(tmp)
        except Exception as exc:
            log_event("state_flush_error", level="error", error=str(exc))

    # Dedupe / last seen
    def should_process(self, source_id: int, message_id: int) -> bool:
        key = str(source_id)
        if message_id in self._ring:
            return False
        last = self.last_seen_by_source.get(key)
        if last is not None and message_id <= last:
            return False
        return True

    def mark_processed(self, source_id: int, message_id: int) -> None:
        key = str(source_id)
        self._ring.append(message_id)
        self.last_seen_by_source[key] = max(message_id, self.last_seen_by_source.get(key, 0))
