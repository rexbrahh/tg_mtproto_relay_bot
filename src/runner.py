from __future__ import annotations

import asyncio
import signal
from typing import Any, Dict, List
import contextlib
from pathlib import Path

from telethon import TelegramClient, events
from telethon.errors.rpcerrorlist import UpdateAppToLoginError

from .config import Config
from .models import ParsedSignal
from .parser import parse_signal
from .sinks.stdout import StdoutSink
from .sinks.webhook import WebhookSink
from .state import StateManager
from .status import StatusState, serve_status
from .telemetry import log_event


class SinkManager:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.stdout = StdoutSink() if cfg.event_sink_stdout else None
        self.webhook = (
            WebhookSink(
                cfg.event_webhook_url,
                secret=cfg.event_webhook_secret,
                timeout_ms=cfg.event_webhook_timeout_ms,
                max_retries=cfg.event_webhook_max_retries,
            )
            if cfg.event_webhook_url
            else None
        )

    def reload(self, cfg: Config) -> None:
        self.cfg = cfg
        self.stdout = StdoutSink() if cfg.event_sink_stdout else None
        # recreate webhook sink if URL changed
        if cfg.event_webhook_url:
            self.webhook = WebhookSink(
                cfg.event_webhook_url,
                secret=cfg.event_webhook_secret,
                timeout_ms=cfg.event_webhook_timeout_ms,
                max_retries=cfg.event_webhook_max_retries,
            )
        else:
            self.webhook = None

    async def emit(self, payload: Dict[str, Any]) -> None:
        tasks: List[asyncio.Task[None]] = []
        if self.stdout:
            tasks.append(asyncio.create_task(self.stdout.emit(payload)))
        if self.webhook:
            tasks.append(asyncio.create_task(self.webhook.emit(payload)))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


async def run() -> None:
    cfg = Config.from_env()
    state = StateManager(cfg.state_dir, cfg.state_last_seen_file)
    sinks = SinkManager(cfg)
    status_state = StatusState()

    stop_event = asyncio.Event()

    def _sigterm(*_: int) -> None:
        log_event("signal", signal="SIGTERM")
        stop_event.set()

    def _sigint(*_: int) -> None:
        log_event("signal", signal="SIGINT")
        stop_event.set()

    def _sighup(*_: int) -> None:
        cfg.hot_reload()
        sinks.reload(cfg)
        log_event("reloaded_config")

    loop = asyncio.get_running_loop()
    for s in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(s, _sigterm if s == signal.SIGTERM else _sigint)
    loop.add_signal_handler(signal.SIGHUP, _sighup)

    # Store Telethon session under state dir to keep secrets out of repo root
    session_path = Path(cfg.state_dir) / cfg.session_name
    client = TelegramClient(
        str(session_path),
        cfg.api_id,
        cfg.api_hash,
        device_model=cfg.tg_device_model,
        system_version=cfg.tg_system_version,
        app_version=cfg.tg_app_version,
        lang_code=cfg.tg_lang_code,
        system_lang_code=cfg.tg_system_lang_code,
    )
    try:
        await client.start()
    except UpdateAppToLoginError as e:  # pragma: no cover - network dependent
        log_event(
            "update_app_to_login",
            level="error",
            hint=(
                "Telegram requires a newer app identity to login. "
                "Set TG_APP_VERSION/TG_SYSTEM_VERSION or login once via official app then retry."
            ),
            error=str(e),
        )
        return
    log_event("client_started", session=cfg.session_name)

    # Status server
    status_task: asyncio.Task[None] | None = None
    if cfg.status_http_enabled:
        status_task = asyncio.create_task(
            serve_status(cfg.status_http_host, cfg.status_http_port, status_state)
        )

    # Periodic state flush
    async def _periodic_flush() -> None:
        try:
            while not stop_event.is_set():
                await asyncio.sleep(5)
                state.flush()
        except asyncio.CancelledError:
            return

    flush_task = asyncio.create_task(_periodic_flush())

    @client.on(events.NewMessage(from_users=cfg.signal_source_id))  # type: ignore[misc]
    async def handler(event: Any) -> None:  # Telethon type is dynamic
        try:
            msg_id = int(event.message.id)
            chat_id = int(event.chat_id) if getattr(event, "chat_id", None) else None
            sender_id = int(event.sender_id) if getattr(event, "sender_id", None) else None

            if not state.should_process(cfg.signal_source_id, msg_id):
                return

            text = (event.raw_text or "").strip()
            parsed: ParsedSignal = parse_signal(text)
            parsed.message_id = msg_id
            parsed.chat_id = chat_id
            parsed.sender_id = sender_id

            payload = parsed.to_event()
            await sinks.emit(payload)
            status_state.record(payload)
            state.mark_processed(cfg.signal_source_id, msg_id)
        except Exception as exc:
            log_event("handler_error", level="error", error=str(exc))

    log_event("listening", source_id=cfg.signal_source_id)

    # Run until stop_event is set
    async with client:
        await stop_event.wait()

    # Graceful shutdown
    state.flush()
    log_event("shutdown_complete")
    if status_task:
        status_task.cancel()
        with contextlib.suppress(Exception):
            await status_task
    flush_task.cancel()
    with contextlib.suppress(Exception):
        await flush_task
