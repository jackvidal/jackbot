import hmac
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status

from agent import handle_message
from database import init_db, seen_message
from tools.whatsapp import send_text

load_dotenv()
logger = logging.getLogger("wa-bot")
logging.basicConfig(level=logging.INFO)

WEBHOOK_SECRET = os.environ["WASENDER_WEBHOOK_SECRET"]
SPEC = json.loads(Path("spec.json").read_text(encoding="utf-8"))
AUDIENCE = SPEC.get("audience", {})


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("bot ready: %s", SPEC.get("name"))
    yield


app = FastAPI(lifespan=lifespan)


def verify_signature(header_value: str | None) -> bool:
    if not header_value:
        return False
    return hmac.compare_digest(header_value, WEBHOOK_SECRET)


def is_allowed(chat_id: str) -> bool:
    if AUDIENCE.get("mode") != "whitelist":
        return True
    return chat_id in AUDIENCE.get("allowed_numbers", [])


@app.post("/webhook/wasender")
async def wasender_webhook(request: Request):
    if not verify_signature(request.headers.get("X-Webhook-Signature")):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "bad signature")

    payload = await request.json()
    event = payload.get("event")

    if event != "messages.received":
        return {"ok": True, "ignored": event}

    data = payload.get("data", {}).get("messages", {})
    key = data.get("key", {})
    msg_id = key.get("id")
    from_me = key.get("fromMe", False)

    if from_me or not msg_id:
        return {"ok": True, "ignored": "self_or_no_id"}

    if seen_message(msg_id):
        return {"ok": True, "ignored": "duplicate"}

    sender_phone = data.get("cleanedSenderPn") or key.get("remoteJid", "").split("@")[0]
    text = data.get("messageBody")
    remote_jid = key.get("remoteJid", "")

    logger.info(
        "inbound msg_id=%s remoteJid=%s cleanedSenderPn=%s text_len=%s",
        msg_id, remote_jid, data.get("cleanedSenderPn"), len(text or ""),
    )

    if not sender_phone or not text:
        return {"ok": True, "ignored": "no_text_or_sender"}

    if remote_jid.endswith("@g.us"):
        return {"ok": True, "ignored": "group"}

    chat_id = f"+{sender_phone}"

    if not is_allowed(chat_id):
        logger.info("whitelist_reject chat_id=%s allowed=%s", chat_id, AUDIENCE.get("allowed_numbers"))
        fallback = AUDIENCE.get("fallback_message")
        if fallback:
            try:
                await send_text(chat_id, fallback)
            except Exception:
                logger.exception("fallback send failed")
        return {"ok": True, "ignored": "not_whitelisted"}

    try:
        await handle_message(chat_id=chat_id, text=text)
    except Exception as e:
        logger.exception("handle_message failed: %s", e)

    return {"ok": True}


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "bot": SPEC.get("name")}
