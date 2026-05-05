import asyncio
import logging
import os
import time

import httpx

logger = logging.getLogger("wa-bot.whatsapp")

WASENDER_BASE = "https://www.wasenderapi.com/api"
SESSION_API_KEY = os.environ["WASENDER_API_KEY"]
ACCOUNT_PROTECTION = os.environ.get("WASENDER_ACCOUNT_PROTECTION", "true").lower() == "true"

_last_send = 0.0
_send_lock = asyncio.Lock()


async def _throttle():
    global _last_send
    if not ACCOUNT_PROTECTION:
        return
    async with _send_lock:
        now = time.monotonic()
        wait = 5.0 - (now - _last_send)
        if wait > 0:
            await asyncio.sleep(wait)
        _last_send = time.monotonic()


async def _post(path: str, body: dict) -> dict:
    await _throttle()
    headers = {
        "Authorization": f"Bearer {SESSION_API_KEY}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(f"{WASENDER_BASE}{path}", json=body, headers=headers)
    if r.status_code == 429:
        logger.warning("rate limited; sleeping 10s")
        await asyncio.sleep(10)
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(f"{WASENDER_BASE}{path}", json=body, headers=headers)
    if r.status_code >= 400:
        logger.error(
            "wasender %s %s -> %s body=%s response=%s",
            "POST", path, r.status_code, body, r.text[:500],
        )
    r.raise_for_status()
    return r.json()


async def send_text(to: str, text: str) -> dict:
    return await _post("/send-message", {"to": to, "text": text})


async def send_image(to: str, image_url: str, caption: str = "") -> dict:
    return await _post(
        "/send-message",
        {"to": to, "text": caption, "imageUrl": image_url},
    )


async def send_document(to: str, document_url: str, file_name: str, caption: str = "") -> dict:
    return await _post(
        "/send-message",
        {"to": to, "text": caption, "documentUrl": document_url, "fileName": file_name},
    )
