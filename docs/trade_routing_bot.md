Relay ↔ Executor Communication Spec

Purpose: Connect the existing MTProto Message Relay Bot (“Relay”) to the Trade Routing/Execution Bot (“Executor”) so that detected contract addresses (mints) can be turned into trades.

Design choice: Two separate processes. The Relay never holds private keys; the Executor does. Communication is one-way from Relay → Executor via HTTP webhook, with optional callback from Executor → Relay.

1. Transport & Endpoint

Protocol: HTTPS (HTTP allowed in local dev)

Method: POST

URL (env-driven): ${EXECUTOR_WEBHOOK}

Example: http://127.0.0.1:8787/events/trade

Timeout (Relay → Executor): 3s connect, 5s read

Retry (Relay): exponential backoff: 250ms, 500ms, 1s, 2s (give up after ~4.75s). Retries are safe due to idempotency key (below).

2. Authentication (HMAC)

The Relay signs the JSON body with an HMAC-SHA256 using ${EXECUTOR_SHARED_SECRET}.

Header: X-Signature: sha256=<hex>

Computation: hex(hmac_sha256(secret, raw_request_body))

Clock: Not required (no timestamp check).

Executor behavior: reject if sig invalid; respond 401.

3. Event Contract (Relay → Executor) JSON Payload (v1) see payload_v1.json in the same folder

Field notes

version: event schema version (“1”).

id: idempotency key; generate as UUIDv5 from chat_id + message_id (stable across retries).

side: "buy" (default). ("sell" possible later.)

mint: base58 Solana mint address extracted by Relay.

params: per-trade knobs Relay is allowed to set. Omit to use Executor defaults.

meta.raw_text: truncated to 2k chars for audit/debug only.

JSON Schema (for validation) -- same folder

4. Executor Responses Success (accepted for processing) see executor_response.json

HTTP 202. Executor will process async and post result later (see callbacks), or Relay can ignore.

Duplicate (idempotent):

```json
{ "status": "duplicate", "id": "7be0...", "first_seen_at": "..." }
```

HTTP 200 (or 409 acceptable). Relay treats as success and must not retry.

Rejected (validation/auth)

HTTP 400 malformed payload

HTTP 401 bad signature

HTTP 422 logical validation failure (e.g., bad mint)

5. Optional Callback (Executor → Relay)

Executor can notify a bot admin channel or your Relay’s small HTTP endpoint.

Callback JSON (callback.json)

6. Health & Introspection

Liveness: GET ${EXECUTOR_BASE}/healthz → 200 OK JSON {"ok":true,"version":"exec-0.1.0"}

Readiness: GET ${EXECUTOR_BASE}/readyz (verifies GMGN reachability, signer loaded)

Metrics (optional): GET ${EXECUTOR_BASE}/metrics (Prometheus)

7. Environment Variables (Relay side)

Add these to your Relay’s .env (or Nix/Secrets Manager):

```env
EXECUTOR_WEBHOOK=http://127.0.0.1:8787/events/trade
EXECUTOR_SHARED_SECRET=replace-with-32B-hex
BASE_ASSET=SOL
DEFAULT_SLIPPAGE_BPS=50
DEFAULT_ANTI_MEV_FEE_SOL=0.002
DEFAULT_BUDGET_SOL=0.05
```

8. Minimal Patch (Relay)

After you extract the mint, emit the event:

```python
import os, hmac, hashlib, json, requests, uuid
from datetime import datetime, timezone

def _idempotency(chat_id: int, message_id: int) -> str:
    ns = uuid.UUID("00000000-0000-0000-0000-000000000001")
    return str(uuid.uuid5(ns, f"{chat_id}:{message_id}"))

def _sign(body: bytes, secret: str) -> str:
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"

def emit_trade_event(mint: str, chat_id: int, message_id: int, sender_id: int, raw_text: str):
    payload = {
        "version": "1",
        "id": _idempotency(chat_id, message_id),
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
        "source": {
            "platform": "telegram",
            "chat_id": chat_id,
            "message_id": message_id,
            "sender_id": sender_id
        },
        "action": "trade",
        "side": "buy",
        "mint": mint,
        "base_asset": os.getenv("BASE_ASSET", "SOL"),
        "params": {
            "slippage_bps": int(os.getenv("DEFAULT_SLIPPAGE_BPS", "50")),
            "anti_mev_fee_sol": float(os.getenv("DEFAULT_ANTI_MEV_FEE_SOL", "0.002")),
            "budget_sol": float(os.getenv("DEFAULT_BUDGET_SOL", "0.05"))
        },
        "meta": {"raw_text": raw_text[:2000], "relay_version": "relay-0.3.1"}
    }
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    headers = {
        "Content-Type": "application/json",
        "X-Signature": _sign(body, os.environ["EXECUTOR_SHARED_SECRET"])
    }
    url = os.environ["EXECUTOR_WEBHOOK"]
    try:
        r = requests.post(url, data=body, headers=headers, timeout=(3,5))
        # treat 200/202 as success; 409 duplicate also OK
        if r.status_code in (200, 202, 409):
            return True, r.text
        return False, f"{r.status_code} {r.text}"
    except Exception as e:
        return False, str(e)
```

Call emit_trade_event(...) right after your CA_REGEX match. Keep the existing “forward to channel” behavior unchanged.

9. Executor Expectations (relevant to comms)

Accepts only version: "1" payloads at /events/trade.

Validates:

HMAC signature

JSON schema

Mint base58 length 32–44

Idempotency:

Drops duplicate id within a 24h window; returns duplicate.

Rate limits:

Soft: 10 req/s; on 429 Relay should not retry (drop).

Processing model:

Async: enqueue & return 202 accepted fast; actual trade can finish later.

Optional callback:

If CALLBACK_URL + CALLBACK_SECRET configured on Executor, it will POST the outcome JSON (see §5).

10. Local Dev Tips

Start Executor on :8787 (FastAPI/Flask).

Use EXECUTOR_SHARED_SECRET="dev-secret".

Test with:

```bash
body='{"version":"1","id":"test-1","ts":"2025-09-15T00:00:00Z","source":{"platform":"telegram","chat_id":1,"message_id":1},"action":"trade","mint":"So11111111111111111111111111111111111111112"}'
sig="sha256=$(printf '%s' "$body" | openssl dgst -sha256 -hmac "dev-secret" -binary | xxd -p -c 256)"
curl -i -H "Content-Type: application/json" -H "X-Signature: $sig" --data "$body" http://127.0.0.1:8787/events/trade
```

11. Versioning

Event schema starts at "version":"1".

Backward-incompatible changes bump to "2" and new endpoint /events/trade.v2 (Executor should advertise supported versions at /readyz).

Ownership boundaries:

Relay (existing) = Telegram IO + parsing + emitting events.

Executor (separate) = validation, sizing, routing (GMGN), signing, submission, status, callbacks.

That’s everything Codex needs to wire the comms without touching your execution logic.
