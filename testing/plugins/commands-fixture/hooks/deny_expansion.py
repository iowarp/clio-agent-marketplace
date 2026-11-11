"""A UserPromptExpansion hook that stops /deny-me, the way a guard refuses a command."""

import json
import sys

event = json.load(sys.stdin)
if event.get("command_name") == "commands-fixture:deny-me":
    print(json.dumps({"decision": "block", "reason": "The fixture hook refuses /deny-me."}))
