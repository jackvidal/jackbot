import logging
import os

from anthropic import AsyncAnthropic

from database import append, tail
from prompt import build_system_prompt
from tools.registry import TOOL_REGISTRY
from tools.whatsapp import send_text

logger = logging.getLogger("wa-bot.agent")
client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = os.environ.get("LLM_MODEL", "claude-haiku-4-5")
MAX_HISTORY = int(os.environ.get("MAX_HISTORY", "20"))
MAX_TOOL_ITER = 5


def _claude_tools():
    return [
        {
            "name": t["name"],
            "description": t["description"],
            "input_schema": t["input_schema"],
        }
        for t in TOOL_REGISTRY.values()
    ]


def _serialize_assistant_content(content) -> list[dict]:
    out: list[dict] = []
    for b in content:
        if b.type == "text":
            out.append({"type": "text", "text": b.text})
        elif b.type == "tool_use":
            out.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})
    return out


async def handle_message(chat_id: str, text: str):
    append(chat_id, "user", text)
    history = tail(chat_id, MAX_HISTORY)
    messages = [{"role": h["role"], "content": h["content"]} for h in history]

    system = build_system_prompt()
    tools = _claude_tools()

    for _ in range(MAX_TOOL_ITER):
        resp = await client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system,
            tools=tools or None,
            messages=messages,
        )
        if resp.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": _serialize_assistant_content(resp.content)})
            tool_results = []
            for b in resp.content:
                if b.type != "tool_use":
                    continue
                spec = TOOL_REGISTRY.get(b.name)
                if not spec:
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": b.id,
                            "content": "tool not found",
                            "is_error": True,
                        }
                    )
                    continue
                try:
                    out = await spec["handler"](chat_id=chat_id, **(b.input or {}))
                except Exception as e:
                    logger.exception("tool %s failed", b.name)
                    out = f"tool error: {e}"
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": b.id, "content": str(out)}
                )
            messages.append({"role": "user", "content": tool_results})
            continue

        reply = "".join(b.text for b in resp.content if b.type == "text").strip()
        if not reply:
            reply = "..."
        append(chat_id, "assistant", reply)
        await send_text(chat_id, reply)
        return

    fallback = "סליחה, נתקעתי. אפשר לנסח את הבקשה אחרת?"
    append(chat_id, "assistant", fallback)
    await send_text(chat_id, fallback)
