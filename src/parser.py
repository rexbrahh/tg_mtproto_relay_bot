from __future__ import annotations

import re
from typing import Optional

from .models import ParsedSignal


# Base58 (no 0, O, I, l) typical Solana address length 32-44
MINT_RE = re.compile(
    r"(?<![1-9A-HJ-NP-Za-km-z])([1-9A-HJ-NP-Za-km-z]{32,44})(?![1-9A-HJ-NP-Za-km-z])"
)

# Matches: "Up 2x" or "Up 2.5x"
UP_RE = re.compile(r"\bUp\s+(?P<up>[0-9]+(?:\.[0-9]+)?)x\b", re.IGNORECASE)

# Matches: "$88.6K MC -> $177.3K MC" or "$1.2M MC"
MC_RE = re.compile(
    r"\$(?P<num>[0-9]+(?:\.[0-9]+)?)\s*(?P<suf>[KMB])\s*MC",
    re.IGNORECASE,
)

HASHTAG_RE = re.compile(r"#(\w+)")


def _suffix_to_multiplier(suf: str) -> float:
    suf = suf.upper()
    if suf == "K":
        return 1_000.0
    if suf == "M":
        return 1_000_000.0
    if suf == "B":
        return 1_000_000_000.0
    return 1.0


def parse_signal(text: str) -> ParsedSignal:
    """Parse a raw message into a ParsedSignal.

    Extracts mint address, Up X, and market-cap from/to values.
    """
    mint_match = MINT_RE.search(text)
    mint: Optional[str] = mint_match.group(1) if mint_match else None

    up_match = UP_RE.search(text)
    up_x: Optional[float] = float(up_match.group("up")) if up_match else None

    mc_iter = list(MC_RE.finditer(text))
    mc_from_usd: Optional[float] = None
    mc_to_usd: Optional[float] = None
    if mc_iter:
        # if arrow format present, first is from, last is to
        first = mc_iter[0]
        last = mc_iter[-1]
        first_val = float(first.group("num")) * _suffix_to_multiplier(first.group("suf"))
        mc_from_usd = first_val
        last_val = float(last.group("num")) * _suffix_to_multiplier(last.group("suf"))
        if last.start() != first.start():
            mc_to_usd = last_val
        else:
            mc_to_usd = None

    hashtags = [m.group(1) for m in HASHTAG_RE.finditer(text)]

    return ParsedSignal(
        mint=mint,
        up_x=up_x,
        mc_from_usd=mc_from_usd,
        mc_to_usd=mc_to_usd,
        hashtags=hashtags,
        raw_text=text,
    )
