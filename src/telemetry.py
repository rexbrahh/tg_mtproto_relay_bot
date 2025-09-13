from __future__ import annotations

import json
import sys
from datetime import datetime
from typing import Any, Dict


def log_event(event: str, level: str = "info", **fields: Any) -> None:
    record: Dict[str, Any] = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "level": level,
        "event": event,
    }
    record.update(fields)
    sys.stdout.write(json.dumps(record, separators=(",", ":")) + "\n")
    sys.stdout.flush()
