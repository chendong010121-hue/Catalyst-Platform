"""Select model context from the completed turns supplied by Workplace."""

import json

from .context import Turn
from .llm_controls import input_token_envelope
from .plugin_composition import PluginDefinition, PluginEffect


CHAT_HISTORY_SERVICE = "context.chat_history"


def recent_turns(turns: tuple[Turn, ...], budget: int) -> tuple[list[dict[str, str]], list[str]]:
    """Return a contiguous suffix in chronological order, with source run IDs."""
    messages = []
    run_ids = []
    for turn in reversed(turns):
        candidate = [
            {"role": "user", "content": turn.question},
            {"role": "assistant", "content": turn.answer},
            *messages,
        ]
        if input_token_envelope(json.dumps(candidate, ensure_ascii=False)) > budget:
            break
        messages = candidate
        run_ids.insert(0, turn.run_id)
    return messages, run_ids


DEFAULT_CHAT_CONTEXT_PLUGIN = PluginDefinition(
    plugin_id="workspace-chat-context",
    version="1.0.0",
    provides=(CHAT_HISTORY_SERVICE,),
    requires=(),
    apply=lambda _: PluginEffect(services={CHAT_HISTORY_SERVICE: recent_turns}),
)
