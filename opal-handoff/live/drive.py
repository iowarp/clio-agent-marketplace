"""Drive live appl-core sessions against the isolated clio instance on :17990.

Usage: python drive.py RUN_NAME "prompt 1" ["prompt 2" ...]
Writes runs/<RUN_NAME>/{messages.json, transcript.md, summary.json}.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx

BASE = "http://127.0.0.1:17990"
LIVE = Path(__file__).resolve().parent
WS = LIVE / "ws"
PACK_SOURCE = Path("D:/Libraries/Documents/projects/opal-work/marketplace-appl-core")
BLUEPRINT = "appl-core"


def ensure_workspace(http: httpx.Client) -> str:
    for row in http.get("/v1/workspaces").json().get("workspaces", []):
        if Path(str(row.get("root_path") or "")).resolve() == WS.resolve():
            return str(row["id"])
    created = http.post(
        "/v1/workspaces",
        json={"name": "opal-live", "root_path": str(WS), "storage_root": str(WS / ".clio")},
    )
    created.raise_for_status()
    return str(created.json()["id"])


def install(http: httpx.Client, workspace_id: str) -> None:
    resp = http.post(
        "/v1/agent-blueprints/install",
        json={
            "source": str(PACK_SOURCE),
            "scope": "workspace",
            "workspace_id": workspace_id,
            "blueprint_id": BLUEPRINT,
        },
        timeout=300.0,
    )
    if resp.status_code >= 400:
        raise SystemExit(f"install failed {resp.status_code}: {resp.text[:1500]}")


def text_of(message: dict[str, Any]) -> str:
    parts = message.get("parts") or []
    out = []
    for part in parts:
        if isinstance(part, dict) and part.get("type") == "text":
            out.append(str(part.get("text") or ""))
    return "\n".join(out)


def run_turn(http: httpx.Client, session_id: str, prompt: str) -> dict[str, Any]:
    ack = http.post(
        f"/v1/sessions/{session_id}/messages",
        json={"parts": [{"type": "text", "text": prompt}]},
    )
    ack.raise_for_status()
    user_id = ack.json()["message_id"]
    start = time.monotonic()
    while True:
        messages = http.get(f"/v1/sessions/{session_id}/messages").json()["messages"]
        for index, message in enumerate(messages):
            if message.get("id") == user_id and index > 0:
                prev = messages[index - 1]
                if prev.get("role") == "assistant" and (
                    prev.get("stop_reason") or prev.get("error_info") is not None
                ):
                    prev["_elapsed_s"] = round(time.monotonic() - start, 1)
                    return prev
        if time.monotonic() - start > 3600:
            raise TimeoutError("turn exceeded 60 min")
        time.sleep(3.0)


def main() -> None:
    name, prompts = sys.argv[1], sys.argv[2:]
    out = LIVE / "runs" / name
    out.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url=BASE, timeout=300.0) as http:
        workspace_id = ensure_workspace(http)
        install(http, workspace_id)
        session = http.post("/v1/sessions", json={"title": name, "workspace_id": workspace_id, "approval_mode": "bypass"})
        session.raise_for_status()
        session_id = session.json()["id"]
        http.post(
            f"/v1/sessions/{session_id}/agent-blueprint", json={"blueprint_id": BLUEPRINT}
        ).raise_for_status()
        transcript = [f"# {name}\n\nsession `{session_id}`\n"]
        summary: dict[str, Any] = {"session_id": session_id, "turns": []}
        for prompt in prompts:
            reply = run_turn(http, session_id, prompt)
            transcript.append(f"\n## USER\n\n{prompt}\n\n## ASSISTANT ({reply['_elapsed_s']}s, stop={reply.get('stop_reason')})\n\n{text_of(reply)}\n")
            summary["turns"].append(
                {
                    "prompt": prompt,
                    "elapsed_s": reply["_elapsed_s"],
                    "stop_reason": reply.get("stop_reason"),
                    "error_info": reply.get("error_info"),
                }
            )
            (out / "transcript.md").write_text("".join(transcript), encoding="utf-8")
        messages = http.get(f"/v1/sessions/{session_id}/messages").json()["messages"]
        (out / "messages.json").write_text(json.dumps(messages, indent=1), encoding="utf-8")
        artifacts = http.get(
            f"/v1/sessions/{session_id}/artifacts", params={"include_children": "true"}
        )
        summary["artifacts"] = artifacts.json() if artifacts.status_code == 200 else artifacts.text[:500]
        (out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary["turns"], indent=1))


if __name__ == "__main__":
    main()
