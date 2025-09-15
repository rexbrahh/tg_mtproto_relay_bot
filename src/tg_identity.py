from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Protocol

import httpx

from .telemetry import log_event


AUTO_SENTINELS = {"", "auto", "latest"}
MACOS_BUNDLE_ID = "ru.keepcoder.Telegram"
IOS_BUNDLE_ID = "ph.telegra.Telegraph"
ALL_BUNDLES = (IOS_BUNDLE_ID, MACOS_BUNDLE_ID)
DEFAULT_DEVICE_MODEL = "iPhone 16 Pro"
DEFAULT_SYSTEM_VERSION = "iOS 18.0"
DEFAULT_APP_VERSION = "12.0"
DEFAULT_LANG_CODE = "en"
DEFAULT_SYSTEM_LANG_CODE = "en"


class SupportsIdentity(Protocol):
    tg_device_model: str
    tg_system_version: str
    tg_app_version: str
    tg_lang_code: str
    tg_system_lang_code: str


@dataclass
class TelegramIdentity:
    device_model: str
    system_version: str
    app_version: str
    lang_code: str
    system_lang_code: str


Fetcher = Callable[[str], Awaitable[str | None]]


def _coalesce(value: str | None, default: str) -> str:
    if value is None:
        return default
    text = value.strip()
    return text if text else default


def _unique(seq: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for item in seq:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return tuple(result)


def _bundles_for_device(device_model: str) -> tuple[str, ...]:
    model = device_model.lower()
    bundles: list[str] = [IOS_BUNDLE_ID, MACOS_BUNDLE_ID]
    if "mac" in model:
        return _unique((MACOS_BUNDLE_ID, IOS_BUNDLE_ID))
    if "ipad" in model or "iphone" in model:
        return (IOS_BUNDLE_ID,)
    return tuple(bundles)


def _parse_version_tuple(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for token in version.split("."):
        digits = "".join(ch for ch in token if ch.isdigit())
        if digits == "":
            continue
        parts.append(int(digits))
    return tuple(parts)


async def fetch_latest_app_store_version(bundle_id: str, timeout: float = 5.0) -> str | None:
    url = "https://itunes.apple.com/lookup"
    params = {"bundleId": bundle_id}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:  # pragma: no cover - network errors depend on env
        log_event(
            "tg_identity_version_fetch_failed",
            level="warning",
            bundle=bundle_id,
            error=str(exc),
        )
        return None

    if not data.get("resultCount"):
        log_event(
            "tg_identity_version_fetch_empty",
            level="warning",
            bundle=bundle_id,
        )
        return None

    version = str(data["results"][0].get("version", "")).strip()
    return version or None


async def resolve_identity(
    cfg: SupportsIdentity,
    fetch_version: Fetcher | None = None,
) -> TelegramIdentity:
    device_model = _coalesce(getattr(cfg, "tg_device_model", None), DEFAULT_DEVICE_MODEL)
    system_version = _coalesce(getattr(cfg, "tg_system_version", None), DEFAULT_SYSTEM_VERSION)
    lang_code = _coalesce(getattr(cfg, "tg_lang_code", None), DEFAULT_LANG_CODE)
    system_lang_code = _coalesce(
        getattr(cfg, "tg_system_lang_code", None), DEFAULT_SYSTEM_LANG_CODE
    )

    configured_app_version = getattr(cfg, "tg_app_version", None)
    app_version = _coalesce(configured_app_version, DEFAULT_APP_VERSION)

    normalized_app_version = app_version.lower()
    if normalized_app_version in AUTO_SENTINELS:
        fetch = fetch_version or fetch_latest_app_store_version
        bundles = _bundles_for_device(device_model) or ALL_BUNDLES
        best_version: str | None = None
        best_bundle: str | None = None
        for bundle_id in bundles:
            latest = await fetch(bundle_id)
            if not latest:
                continue
            if not best_version:
                best_version = latest
                best_bundle = bundle_id
                continue
            if _parse_version_tuple(latest) > _parse_version_tuple(best_version):
                best_version = latest
                best_bundle = bundle_id

        if best_version and best_bundle:
            app_version = best_version
            log_event(
                "tg_identity_version_auto",
                bundle=best_bundle,
                app_version=app_version,
            )
        else:
            app_version = DEFAULT_APP_VERSION
            log_event(
                "tg_identity_version_auto_fallback",
                level="warning",
                bundles=list(bundles),
                app_version=app_version,
            )

    return TelegramIdentity(
        device_model=device_model,
        system_version=system_version,
        app_version=app_version,
        lang_code=lang_code,
        system_lang_code=system_lang_code,
    )
