import json
import re
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from context.store import ContextStore
from submission_core import clip, compose, get_active_offer, merchant_name

AUTO_REPLY_PATTERNS = [
    r"thank you for contacting",
    r"our team will respond shortly",
    r"automated assistant",
    r"business hours",
    r"reply to this message",
    r"auto(?: |-)?reply",
]
OPT_OUT_PATTERNS = [
    r"\bstop\b",
    r"not interested",
    r"don't message",
    r"do not message",
    r"useless spam",
    r"remove me",
]
ACTION_PATTERNS = [
    r"let'?s do it",
    r"\bgo ahead\b",
    r"\byes\b",
    r"\bok\b",
    r"send it",
    r"please proceed",
    r"what'?s next",
    r"i want to join",
    r"mujhe .* join",
]

TEAM_METADATA = {
    "team_name": "magicpin-ai-challenge",
    "team_members": ["Sameer Gupta"],
    "model": "deterministic-rule-engine",
    "approach": "template composer with trigger-specific rules, context grounding, validation, and reply routing",
    "contact_email": "sameerguptaa09@example.com",
    "version": "0.1.0",
    "submitted_at": "2026-04-29T00:00:00Z",
}

app = FastAPI()
START_TIME = time.time()
STORE = ContextStore()
CONVERSATIONS: dict[str, dict[str, Any]] = {}
SENT_SUPPRESSIONS: set[tuple[str, str]] = set()
AUTO_REPLY_COUNTS: dict[str, dict[str, int]] = {}


class ContextBody(BaseModel):
    scope: str
    context_id: str
    version: int
    payload: dict[str, Any]
    delivered_at: str


class TickBody(BaseModel):
    now: str
    available_triggers: list[str] = []


class ReplyBody(BaseModel):
    conversation_id: str
    merchant_id: str | None = None
    customer_id: str | None = None
    from_role: str
    message: str
    received_at: str
    turn_number: int


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def record_outbound(conversation_id: str, merchant_id: str | None, customer_id: str | None, trigger_id: str | None, body: str) -> None:
    state = CONVERSATIONS.setdefault(
        conversation_id,
        {
            "merchant_id": merchant_id,
            "customer_id": customer_id,
            "trigger_id": trigger_id,
            "turns": [],
            "auto_reply_count": 0,
        },
    )
    state["turns"].append({"from": "bot", "message": body})


def is_auto_reply(message: str) -> bool:
    lowered = message.lower()
    return any(re.search(pattern, lowered) for pattern in AUTO_REPLY_PATTERNS)


def is_opt_out(message: str) -> bool:
    lowered = message.lower()
    return any(re.search(pattern, lowered) for pattern in OPT_OUT_PATTERNS)


def is_action_intent(message: str) -> bool:
    lowered = message.lower()
    return any(re.search(pattern, lowered) for pattern in ACTION_PATTERNS)


def normalized_message(message: str) -> str:
    return re.sub(r"\s+", " ", message.strip().lower())


def reply_body_for_intent(merchant_id: str | None) -> str:
    merchant = STORE.get_context("merchant", merchant_id) if merchant_id else None
    name = merchant_name(merchant) if merchant else "there"
    return clip(
        f"{name}, done. I'll keep this simple: I can send the first usable draft next, and you can approve or tweak it before anything goes live."
    )


def reply_body_for_question(merchant_id: str | None, message: str) -> str:
    merchant = STORE.get_context("merchant", merchant_id) if merchant_id else None
    name = merchant_name(merchant) if merchant else "there"
    offer = get_active_offer(merchant) if merchant else None
    if "what" in message.lower() or "how" in message.lower():
        return clip(
            f"{name}, shortest version: start with one concrete hook like {offer or 'a service+price offer'}, keep one CTA, and I can draft the exact copy for you next."
        )
    return clip(f"{name}, understood. I can turn that into a ready draft in the next message if you want.")


@app.get("/v1/healthz")
async def healthz():
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - START_TIME),
        "contexts_loaded": STORE.get_all_counts(),
    }


@app.get("/v1/metadata")
async def metadata():
    return TEAM_METADATA


@app.post("/v1/context")
async def push_context(body: ContextBody):
    if body.scope not in {"category", "merchant", "customer", "trigger"}:
        return {"accepted": False, "reason": "invalid_scope", "details": body.scope}

    accepted, reason, current_version = STORE.push_context(
        body.scope, body.context_id, body.version, body.payload
    )
    if not accepted:
        return {"accepted": False, "reason": reason, "current_version": current_version}
    return {
        "accepted": True,
        "ack_id": f"ack_{body.context_id}_v{body.version}",
        "stored_at": utc_now_iso(),
    }


@app.post("/v1/tick")
async def tick(body: TickBody):
    actions = []
    for trigger_id in body.available_triggers[:20]:
        trigger = STORE.get_context("trigger", trigger_id)
        if not trigger:
            continue

        suppression_key = trigger.get("suppression_key", "")
        merchant_id = trigger.get("merchant_id")
        if merchant_id and (suppression_key, merchant_id) in SENT_SUPPRESSIONS:
            continue

        merchant = STORE.get_context("merchant", merchant_id) if merchant_id else None
        if not merchant:
            continue
        category = STORE.get_context("category", merchant.get("category_slug"))
        if not category:
            continue
        customer_id = trigger.get("customer_id")
        customer = STORE.get_context("customer", customer_id) if customer_id else None

        message = compose(category, merchant, trigger, customer)
        conversation_id = f"conv_{trigger_id}_{uuid.uuid4().hex[:8]}"
        action = {
            "conversation_id": conversation_id,
            "merchant_id": merchant_id,
            "customer_id": customer_id,
            "send_as": message["send_as"],
            "trigger_id": trigger_id,
            "template_name": f"vera_{trigger.get('kind', 'generic')}_v1",
            "template_params": [merchant.get("identity", {}).get("name", ""), message["body"][:60]],
            "body": message["body"],
            "cta": message["cta"],
            "suppression_key": message["suppression_key"],
            "rationale": message["rationale"],
        }
        actions.append(action)
        SENT_SUPPRESSIONS.add((suppression_key, merchant_id))
        record_outbound(conversation_id, merchant_id, customer_id, trigger_id, message["body"])
    return {"actions": actions}


@app.post("/v1/reply")
async def reply(body: ReplyBody):
    state = CONVERSATIONS.setdefault(
        body.conversation_id,
        {
            "merchant_id": body.merchant_id,
            "customer_id": body.customer_id,
            "trigger_id": None,
            "turns": [],
            "auto_reply_count": 0,
        },
    )
    state["turns"].append({"from": body.from_role, "message": body.message})

    if is_opt_out(body.message):
        return {"action": "end", "rationale": "User opted out or responded hostilely"}

    if is_auto_reply(body.message):
        merchant_key = body.merchant_id or body.conversation_id
        norm = normalized_message(body.message)
        merchant_counts = AUTO_REPLY_COUNTS.setdefault(merchant_key, {})
        merchant_counts[norm] = merchant_counts.get(norm, 0) + 1
        state["auto_reply_count"] += 1
        if state["auto_reply_count"] >= 2 or merchant_counts[norm] >= 2:
            return {"action": "end", "rationale": "Repeated auto-reply detected"}
        return {
            "action": "send",
            "body": clip("Looks like this may be an auto-reply. When the owner sees this, just reply YES and I'll keep it simple."),
            "cta": "binary_yes_no",
            "rationale": "Possible auto-reply; trying one owner handoff before ending",
        }

    if is_action_intent(body.message):
        outbound = reply_body_for_intent(body.merchant_id)
        record_outbound(body.conversation_id, body.merchant_id, body.customer_id, state.get("trigger_id"), outbound)
        return {
            "action": "send",
            "body": outbound,
            "cta": "open_ended",
            "rationale": "Explicit intent detected; switching from pitch to action mode",
        }

    if "later" in body.message.lower() or "tomorrow" in body.message.lower():
        return {"action": "wait", "wait_seconds": 1800, "rationale": "Merchant asked for time"}

    outbound = reply_body_for_question(body.merchant_id, body.message)
    record_outbound(body.conversation_id, body.merchant_id, body.customer_id, state.get("trigger_id"), outbound)
    return {
        "action": "send",
        "body": outbound,
        "cta": "open_ended",
        "rationale": "Continuing conversation with a concise grounded reply",
    }


def load_seed_contexts(base_dir: Path | None = None) -> None:
    root = base_dir or Path(__file__).parent / "dataset"
    categories_dir = root / "categories"
    for path in categories_dir.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        STORE.push_context("category", payload["slug"], 1, payload)

    seeds = [
        ("merchant", root / "merchants_seed.json", "merchants", "merchant_id"),
        ("customer", root / "customers_seed.json", "customers", "customer_id"),
        ("trigger", root / "triggers_seed.json", "triggers", "id"),
    ]
    for scope, path, key_name, id_key in seeds:
        payload = json.loads(path.read_text(encoding="utf-8"))
        for item in payload.get(key_name, []):
            STORE.push_context(scope, item[id_key], 1, item)


load_seed_contexts()
