from __future__ import annotations

import re
from typing import Optional

from .models import ParsedSignal


# Base58 (no 0, O, I, l) typical Solana address length 32-44
MINT_RE = re.compile(
    r"(?<![1-9A-HJ-NP-Za-km-z])([1-9A-HJ-NP-Za-km-z]{32,44})(?![1-9A-HJ-NP-Za-km-z])"
)


def parse_signal(text: str) -> ParsedSignal:
    """Parse a raw message into a ParsedSignal with just the contract address."""

    match = MINT_RE.search(text)
    contract_address: Optional[str] = match.group(1) if match else None

    return ParsedSignal(contract_address=contract_address, raw_text=text)
