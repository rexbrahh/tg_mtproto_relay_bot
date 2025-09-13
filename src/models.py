from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ParsedSignal(BaseModel):
    ts: datetime = Field(default_factory=datetime.utcnow)
    # Message metadata
    message_id: Optional[int] = None
    chat_id: Optional[int] = None
    sender_id: Optional[int] = None

    # Parsed fields
    mint: Optional[str] = None
    up_x: Optional[float] = None
    mc_from_usd: Optional[float] = None
    mc_to_usd: Optional[float] = None
    hashtags: List[str] = Field(default_factory=list)
    raw_text: str = ""

    def to_event(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "ts": self.ts.isoformat() + "Z",
            "event": "signal_parsed",
            "message_id": self.message_id,
            "chat_id": self.chat_id,
            "sender_id": self.sender_id,
            "mint": self.mint,
            "up_x": self.up_x,
            "mc_from_usd": self.mc_from_usd,
            "mc_to_usd": self.mc_to_usd,
            "hashtags": self.hashtags,
        }
        return data
