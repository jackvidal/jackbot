from typing import Any, Awaitable, Callable

TOOL_REGISTRY: dict[str, dict[str, Any]] = {}


def register(
    name: str,
    description: str,
    input_schema: dict,
    handler: Callable[..., Awaitable[str]],
):
    TOOL_REGISTRY[name] = {
        "name": name,
        "description": description,
        "input_schema": input_schema,
        "handler": handler,
    }
