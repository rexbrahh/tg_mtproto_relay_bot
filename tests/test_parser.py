from __future__ import annotations

from src.parser import parse_signal


def test_parse_up_and_mc_arrow() -> None:
    text = (
        "POLYTALE #POLYTALE\n"
        "B8bFLQUZg9exgB1RvW9D7RsQwEjfyKU22jf1pf1\n"
        "Up 2x\n"
        "$88.6K MC -> $177.3K MC\n"
    )
    p = parse_signal(text)
    assert p.mint and len(p.mint) >= 32
    assert p.up_x == 2.0
    assert p.mc_from_usd and abs(p.mc_from_usd - 88600) < 1
    assert p.mc_to_usd and abs(p.mc_to_usd - 177300) < 1
    assert "POLYTALE" in p.hashtags


def test_parse_up_only() -> None:
    text = (
        "Gem Bot #ONBOARDING\n"
        "Fzp08vGJRRB9d8h9vF5dNuvsTSKcs56GfVpNzupmp\n"
        "Up 10x\n"
        "$84.8K MC\n"
    )
    p = parse_signal(text)
    assert p.up_x == 10.0
    assert p.mc_from_usd and abs(p.mc_from_usd - 84800) < 1
