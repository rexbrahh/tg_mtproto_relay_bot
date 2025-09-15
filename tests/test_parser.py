from __future__ import annotations

from src.parser import parse_signal

DUMMY_CA = "AbCdEfGhJkMnPqRsTuVwXyZ23456789ABCDEFGH"


def test_parser_extracts_contract_address_simple() -> None:
    text = "\n".join(["Signal Drop", DUMMY_CA, "Buy now", ""])
    p = parse_signal(text)
    assert p.contract_address == DUMMY_CA


def test_parser_extracts_with_noise() -> None:
    text = "\n".join(["Gem Bot", DUMMY_CA, "Hype x10", "More hype", ""])
    p = parse_signal(text)
    assert p.contract_address == DUMMY_CA


def test_parser_handles_full_signal_card() -> None:
    text = "\n".join(
        [
            "⚖️ SURVIVE THE STREETS #SURVIVE",
            DUMMY_CA,
            "Bopump",
            "",
            "MC: $76.3K | Liq: $17.9K",
            "Holders: 223 | Txns: 790",
            "Bundled: 7.0% | Snipers: 36.0%",
            "Creator: 0.2% | Fresh: 9.5%",
            "Platform Users: 67",
            "Socials: X",
            "Buy $Survive",
            "",
        ]
    )
    p = parse_signal(text)
    assert p.contract_address == DUMMY_CA


def test_parser_ignores_embedded_urls() -> None:
    text = "\n".join(
        [
            "Token drop incoming",
            f"https://pump.fun/board/{DUMMY_CA}",
            "Use code 1234",
            f"{DUMMY_CA} is live",
            "",
        ]
    )
    p = parse_signal(text)
    assert p.contract_address == DUMMY_CA
