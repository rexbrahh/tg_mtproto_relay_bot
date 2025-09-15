import asyncio
from types import SimpleNamespace

from src.tg_identity import (
    DEFAULT_APP_VERSION,
    IOS_BUNDLE_ID,
    MACOS_BUNDLE_ID,
    resolve_identity,
)


def run(coro):
    return asyncio.run(coro)


def test_resolve_identity_auto_prefers_newest_version_for_mac():
    calls: list[str] = []

    async def fake_fetch(bundle_id: str) -> str | None:
        calls.append(bundle_id)
        return {
            MACOS_BUNDLE_ID: "11.15.1",
            IOS_BUNDLE_ID: "12.0",
        }.get(bundle_id)

    cfg = SimpleNamespace(
        tg_device_model="MacBook Pro",
        tg_system_version="macOS 15.6",
        tg_app_version="auto",
        tg_lang_code="en",
        tg_system_lang_code="en",
    )

    identity = run(resolve_identity(cfg, fetch_version=fake_fetch))

    assert identity.app_version == "12.0"
    assert calls == [MACOS_BUNDLE_ID, IOS_BUNDLE_ID]


def test_resolve_identity_auto_falls_back_when_fetch_fails():
    async def fake_fetch(_: str) -> str | None:
        return None

    cfg = SimpleNamespace(
        tg_device_model="Mac",
        tg_system_version="macOS 15.6",
        tg_app_version="auto",
        tg_lang_code="en",
        tg_system_lang_code="en",
    )

    identity = run(resolve_identity(cfg, fetch_version=fake_fetch))

    assert identity.app_version == DEFAULT_APP_VERSION


def test_resolve_identity_selects_ios_bundle_for_iphone():
    calls: list[str] = []

    async def fake_fetch(bundle_id: str) -> str | None:
        calls.append(bundle_id)
        return "12.0"

    cfg = SimpleNamespace(
        tg_device_model="iPhone 16 Pro",
        tg_system_version="iOS 18.0",
        tg_app_version="auto",
        tg_lang_code="en",
        tg_system_lang_code="en",
    )

    run(resolve_identity(cfg, fetch_version=fake_fetch))

    assert calls == [IOS_BUNDLE_ID]


def test_resolve_identity_respects_explicit_version():
    async def fake_fetch(_: str) -> str | None:  # pragma: no cover
        raise AssertionError("fetch should not be called when version explicit")

    cfg = SimpleNamespace(
        tg_device_model="Mac",
        tg_system_version="macOS 15.6",
        tg_app_version="11.99",
        tg_lang_code="en",
        tg_system_lang_code="en",
    )

    identity = run(resolve_identity(cfg, fetch_version=fake_fetch))

    assert identity.app_version == "11.99"

