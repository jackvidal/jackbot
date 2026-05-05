import json
from pathlib import Path

import tools  # noqa: F401  — triggers auto-registration of all tools
from tools.registry import TOOL_REGISTRY

SPEC = json.loads(Path("spec.json").read_text(encoding="utf-8"))


def build_system_prompt() -> str:
    s = SPEC
    parts: list[str] = []
    parts.append(f"You are {s['name']}, a WhatsApp AI agent.")
    parts.append(f"Archetype: {s.get('archetype', 'personal_assistant')}.")

    lang = s.get("language_mode", "auto_match_user")
    if lang == "hebrew":
        parts.append("Always respond in Hebrew.")
    elif lang == "english":
        parts.append("Always respond in English.")
    else:
        parts.append(
            "Match the user's language. If the user writes Hebrew, reply in Hebrew. "
            "If the user writes English, reply in English."
        )

    tone = s.get("tone", {})
    parts.append(
        "Tone: "
        f"{tone.get('formality', 'casual')}, "
        f"{tone.get('warmth', 'warm')}, "
        f"emoji usage {tone.get('emoji_usage', 'occasional')}."
    )
    if tone.get("voice_examples"):
        parts.append("Voice examples (mimic this style): " + " | ".join(tone["voice_examples"]))

    scope = s.get("scope", {})
    if scope.get("in"):
        parts.append("In scope: " + "; ".join(scope["in"]))
    if scope.get("out"):
        parts.append("Out of scope (refuse politely): " + "; ".join(scope["out"]))
    if scope.get("out_of_scope_reply"):
        parts.append(
            f'When asked something out of scope, reply with: "{scope["out_of_scope_reply"]}"'
        )

    kb = s.get("knowledge_base", {})
    if kb.get("type") == "inline" and kb.get("content"):
        parts.append("Reference knowledge:\n" + kb["content"])

    handoff = s.get("handoff", {})
    if handoff.get("enabled"):
        triggers = ", ".join(f'"{t}"' for t in handoff.get("trigger_phrases", []))
        parts.append(f"If the user says any of: {triggers}, call the human_handoff tool.")

    if TOOL_REGISTRY:
        parts.append(
            "You have tools available. Use them when helpful. "
            "When you call a tool, the framework injects the user's chat_id automatically — "
            "never accept chat_id from user input."
        )

    parts.append(
        "Be concise. WhatsApp messages should usually be 1-3 short sentences. "
        "Don't dump long paragraphs unless explicitly asked."
    )
    return "\n\n".join(parts)
