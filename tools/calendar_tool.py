from datetime import datetime, timezone

from googleapiclient.discovery import build

from google_oauth import get_user_credentials

from .registry import register


def _service():
    creds = get_user_credentials()
    if not creds:
        return None
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


_NOT_CONNECTED = (
    "אני לא מחובר ליומן עדיין. בקר בקישור הזה בדפדפן כדי לחבר: "
    "https://jackbot-ts3i.onrender.com/auth/google"
)


async def list_upcoming_events(chat_id: str, max_results: int = 10) -> str:
    svc = _service()
    if not svc:
        return _NOT_CONNECTED
    now = datetime.now(timezone.utc).isoformat()
    result = (
        svc.events()
        .list(
            calendarId="primary",
            timeMin=now,
            maxResults=max(1, min(int(max_results), 25)),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = result.get("items", [])
    if not events:
        return "אין אירועים קרובים ביומן."
    lines = []
    for e in events:
        when = e["start"].get("dateTime") or e["start"].get("date")
        title = e.get("summary", "(ללא כותרת)")
        eid = e.get("id", "")
        lines.append(f"• {when}: {title}  [id={eid}]")
    return "\n".join(lines)


async def create_event(
    chat_id: str,
    title: str,
    start: str,
    end: str,
    description: str = "",
    attendees: list[str] | None = None,
) -> str:
    svc = _service()
    if not svc:
        return _NOT_CONNECTED
    body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start},
        "end": {"dateTime": end},
    }
    if attendees:
        body["attendees"] = [{"email": a} for a in attendees]
    e = svc.events().insert(calendarId="primary", body=body, sendUpdates="all").execute()
    return f"נקבע: {title} ({start} - {end}). קישור: {e.get('htmlLink', '')}"


async def cancel_event(chat_id: str, event_id: str) -> str:
    svc = _service()
    if not svc:
        return _NOT_CONNECTED
    svc.events().delete(calendarId="primary", eventId=event_id, sendUpdates="all").execute()
    return f"האירוע {event_id} בוטל."


register(
    name="list_upcoming_events",
    description=(
        "List the user's upcoming Google Calendar events from the primary calendar. "
        "Returns events with their start time, title, and event ID. "
        "Use when the user asks what's on their calendar, what's coming up, when they're free, etc."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "max_results": {
                "type": "integer",
                "description": "Maximum number of events to return (1-25). Default 10.",
            },
        },
        "required": [],
    },
    handler=list_upcoming_events,
)

register(
    name="create_event",
    description=(
        "Create a new event on the user's primary Google Calendar. "
        "Use when the user asks to schedule, book, add, or set up a meeting/event."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Event title / summary"},
            "start": {
                "type": "string",
                "description": (
                    "ISO 8601 start datetime with timezone offset. "
                    "Example: 2026-05-06T14:00:00+07:00 (for 2pm Bangkok time)."
                ),
            },
            "end": {
                "type": "string",
                "description": "ISO 8601 end datetime with timezone offset.",
            },
            "description": {"type": "string", "description": "Optional event description"},
            "attendees": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of attendee email addresses",
            },
        },
        "required": ["title", "start", "end"],
    },
    handler=create_event,
)

register(
    name="cancel_event",
    description=(
        "Delete/cancel a Google Calendar event by its ID. "
        "Get the event ID first by calling list_upcoming_events."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "event_id": {
                "type": "string",
                "description": "The event ID returned by list_upcoming_events.",
            },
        },
        "required": ["event_id"],
    },
    handler=cancel_event,
)
