"""The packaged smoke hook: deny a prompt that carries the block marker.

Formerly ``hooks/pre_message.py``'s ``pre_message(session_id, text)``; it now
runs as an SDK hook on prompt submission with the same behavior.
"""

from clio_agent.sdk import HookEvent, hook

BLOCK_MARKER = "CLIO_HOOK_SMOKE_BLOCK"


@hook("prompt_submit")
def pre_message(ev: HookEvent) -> None:
    """Deny the submitted prompt when it contains the smoke block marker."""

    if BLOCK_MARKER in (ev.prompt or ""):
        raise PermissionError("blocked by packaged hook smoke pre_message")
