from __future__ import annotations

import os
from dataclasses import dataclass


def _get_bool(env: str, default: bool) -> bool:
    val = os.environ.get(env)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(env: str, default: int) -> int:
    val = os.environ.get(env)
    if val is None or val.strip() == "":
        return default
    return int(val)


@dataclass
class Config:
    # Telegram
    api_id: int
    api_hash: str
    session_name: str
    signal_source_id: int

    # Behavior
    dry_run: bool = True

    # Sinks
    event_sink_stdout: bool = True
    event_webhook_url: str | None = None
    event_webhook_secret: str | None = None
    event_webhook_timeout_ms: int = 1500
    event_webhook_max_retries: int = 2

    # Status server
    status_http_enabled: bool = True
    status_http_host: str = "127.0.0.1"
    status_http_port: int = 8787

    # Persistence
    state_dir: str = "./state"
    state_last_seen_file: str = "last_seen.json"

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            api_id=int(os.environ["API_ID"]),
            api_hash=os.environ["API_HASH"],
            session_name=os.environ.get("SESSION_NAME", "spare_tg_user"),
            signal_source_id=int(os.environ.get("SIGNAL_SOURCE_ID", "0") or 0),
            dry_run=_get_bool("DRY_RUN", True),
            event_sink_stdout=_get_bool("EVENT_SINK_STDOUT", True),
            event_webhook_url=(os.environ.get("EVENT_WEBHOOK_URL") or "") or None,
            event_webhook_secret=(os.environ.get("EVENT_WEBHOOK_SECRET") or "") or None,
            event_webhook_timeout_ms=_get_int("EVENT_WEBHOOK_TIMEOUT_MS", 1500),
            event_webhook_max_retries=_get_int("EVENT_WEBHOOK_MAX_RETRIES", 2),
            status_http_enabled=_get_bool("STATUS_HTTP_ENABLED", True),
            status_http_host=os.environ.get("STATUS_HTTP_HOST", "127.0.0.1"),
            status_http_port=_get_int("STATUS_HTTP_PORT", 8787),
            state_dir=os.environ.get("STATE_DIR", "./state"),
            state_last_seen_file=os.environ.get("STATE_LAST_SEEN_FILE", "last_seen.json"),
        )

    def hot_reload(self) -> None:
        """Reload only hot-reloadable fields from the environment."""
        self.dry_run = _get_bool("DRY_RUN", self.dry_run)
        self.event_sink_stdout = _get_bool("EVENT_SINK_STDOUT", self.event_sink_stdout)
        self.event_webhook_url = (os.environ.get("EVENT_WEBHOOK_URL") or "") or None
        self.event_webhook_secret = (os.environ.get("EVENT_WEBHOOK_SECRET") or "") or None
        self.event_webhook_timeout_ms = _get_int(
            "EVENT_WEBHOOK_TIMEOUT_MS", self.event_webhook_timeout_ms
        )
        self.event_webhook_max_retries = _get_int(
            "EVENT_WEBHOOK_MAX_RETRIES", self.event_webhook_max_retries
        )
        self.status_http_enabled = _get_bool("STATUS_HTTP_ENABLED", self.status_http_enabled)
        self.status_http_host = os.environ.get("STATUS_HTTP_HOST", self.status_http_host)
        self.status_http_port = _get_int("STATUS_HTTP_PORT", self.status_http_port)
