from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ParsedSignal(BaseModel):
    ts: datetime = Field(default_factory=datetime.utcnow)
    # Message metadata
    message_id: Optional[int] = None
    chat_id: Optional[int] = None
    sender_id: Optional[int] = None

    # Parsed fields
    contract_address: Optional[str] = None
    raw_text: str = ""

    def to_event(self) -> dict[str, Any]:
        return {
            "ts": self.ts.isoformat() + "Z",
            "event": "signal_parsed",
            "message_id": self.message_id,
            "chat_id": self.chat_id,
            "sender_id": self.sender_id,
            "contract_address": self.contract_address,
        }
