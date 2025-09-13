from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
from typing import Any, Dict, Optional

import httpx


class WebhookSink:
    def __init__(
        self,
        url: str,
        *,
        secret: Optional[str] = None,
        timeout_ms: int = 1500,
        max_retries: int = 2,
    ) -> None:
        self.url = url
        self.secret = secret
        self.timeout = timeout_ms / 1000.0
        self.max_retries = max_retries
        self._client = httpx.AsyncClient(timeout=self.timeout)

    async def emit(self, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload).encode()
        headers: Dict[str, str] = {"content-type": "application/json"}
        if self.secret:
            sig = hmac.new(self.secret.encode(), body, hashlib.sha256).hexdigest()
            headers["x-signature"] = sig
        attempt = 0
        backoff = 0.5
        while True:
            try:
                await self._client.post(self.url, content=body, headers=headers)
                return
            except Exception:
                attempt += 1
                if attempt > self.max_retries:
                    return
                await asyncio.sleep(backoff)
                backoff *= 2

    async def aclose(self) -> None:
        await self._client.aclose()
