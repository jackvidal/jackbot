import asyncio
import datetime as dt

from .registry import register
from .whatsapp import send_text

_pending: list[asyncio.Task] = []


async def _fire(when_seconds: float, chat_id: str, message: str):
    await asyncio.sleep(when_seconds)
    try:
        await send_text(chat_id, f"⏰ תזכורת: {message}")
    except Exception:
        pass


async def schedule_reminder(chat_id: str, in_minutes: int, message: str) -> str:
    when = max(int(in_minutes) * 60, 5)
    task = asyncio.create_task(_fire(when, chat_id, message))
    _pending.append(task)
    fire_at = dt.datetime.now() + dt.timedelta(seconds=when)
    return f"קבעתי תזכורת ל-{fire_at.strftime('%H:%M')}: {message}"


register(
    name="schedule_reminder",
    description=(
        "Schedule a reminder that will be sent back to the user via WhatsApp after N minutes. "
        "Use when the user asks to be reminded about something at a future time."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "in_minutes": {
                "type": "integer",
                "description": "Number of minutes from now until the reminder should fire.",
            },
            "message": {
                "type": "string",
                "description": "The reminder text, in the user's language.",
            },
        },
        "required": ["in_minutes", "message"],
    },
    handler=schedule_reminder,
)
