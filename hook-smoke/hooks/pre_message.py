def pre_message(session_id, text):
    if "CLIO_HOOK_SMOKE_BLOCK" in text:
        raise PermissionError("blocked by packaged hook smoke pre_message")
