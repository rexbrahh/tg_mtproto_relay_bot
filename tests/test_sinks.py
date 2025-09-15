from __future__ import annotations

import asyncio
import hashlib
import hmac
from types import SimpleNamespace

import pytest

from src.runner import SinkManager
from src.sinks.webhook import WebhookSink


class _StubClient:
    def __init__(self, responses: list[BaseException | None]) -> None:
        self._responses = responses
        self.calls: list[tuple[bytes, dict[str, str]]] = []

    async def post(self, url: str, *, content: bytes, headers: dict[str, str]) -> None:
        self.calls.append((content, headers))
        outcome = self._responses.pop(0) if self._responses else None
        if isinstance(outcome, BaseException):
            raise outcome

    async def aclose(self) -> None:  # pragma: no cover - best-effort cleanup
        pass


@pytest.mark.asyncio
async def test_webhook_sink_adds_signature() -> None:
    secret = "shhhh"
    sink = WebhookSink("https://gmgn.example/ingest", secret=secret, timeout_ms=10)
    stub = _StubClient([None])
    sink._client = stub  # type: ignore[assignment]

    payload = {"contract_address": "AbCdEfGhJkMnPqRsTuVwXyZ23456789ABCDEFGH", "event": "signal"}
    await sink.emit(payload)

    assert len(stub.calls) == 1
    body, headers = stub.calls[0]
    assert headers["content-type"] == "application/json"
    expected_sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert headers["x-signature"] == expected_sig


@pytest.mark.asyncio
async def test_webhook_sink_retries_until_success(monkeypatch: pytest.MonkeyPatch) -> None:
    sink = WebhookSink("https://gmgn.example/ingest", timeout_ms=10, max_retries=3)
    stub = _StubClient(
        [
            RuntimeError("boom"),
            RuntimeError("boom"),
            None,
        ]
    )
    sink._client = stub  # type: ignore[assignment]

    async def fake_sleep(_: float) -> None:
        return

    monkeypatch.setattr("src.sinks.webhook.asyncio.sleep", fake_sleep)

    payload = {"contract_address": "AbCdEfGhJkMnPqRsTuVwXyZ23456789ABCDEFGH"}
    await sink.emit(payload)

    assert len(stub.calls) == 3


class _DummySink:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    async def emit(self, payload: dict[str, str]) -> None:
        self.calls.append(payload)


@pytest.mark.asyncio
async def test_sink_manager_emits_to_all_sinks(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = SimpleNamespace(
        event_sink_stdout=True,
        event_webhook_url="https://gmgn",
        event_webhook_secret=None,
        event_webhook_timeout_ms=1500,
        event_webhook_max_retries=2,
    )
    manager = SinkManager(cfg)

    stdout_sink = _DummySink()
    webhook_sink = _DummySink()
    manager.stdout = stdout_sink  # type: ignore[assignment]
    manager.webhook = webhook_sink  # type: ignore[assignment]

    payload = {"contract_address": "AbCdEfGhJkMnPqRsTuVwXyZ23456789ABCDEFGH"}
    await manager.emit(payload)

    assert stdout_sink.calls == [payload]
    assert webhook_sink.calls == [payload]
