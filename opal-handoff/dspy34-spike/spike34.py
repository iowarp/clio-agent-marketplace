"""DSPy 3.4.0 spike: capture the exact messages DSPy sends, per call.

Questions:
 Q1 Predict + History (text mode): layout; where the "Respond with..." reminder sits; append-only across calls?
 Q2 ReActV2 (text mode): message sequence per step; prefix property between consecutive calls.
 Q3 Native function calling: what request (messages + tools) does the adapter build?
 Q4 acall works with a scripted LM.
"""

from __future__ import annotations

import asyncio
import json
import warnings

import dspy
from dspy.utils.dummies import DummyLM

warnings.filterwarnings("ignore")


def msgs(entry):
    return entry.get("messages") or []


def show(title, lm):
    print(f"\n==================== {title}")
    for i, entry in enumerate(lm.history):
        m = msgs(entry)
        print(f"--- call {i}: {len(m)} messages; kwargs keys={sorted(k for k in (entry.get('kwargs') or {}))}")
        for j, msg in enumerate(m):
            content = msg.get("content")
            if isinstance(content, list):
                content = json.dumps(content)[:300]
            text = str(content).replace("\n", "\\n")
            extra = {k: v for k, v in msg.items() if k not in ("role", "content")}
            print(f"   [{j}] {msg.get('role')}: {text[:220]}{' ...' if len(text) > 220 else ''}"
                  f"{'  EXTRA=' + json.dumps(extra, default=str)[:200] if extra else ''}")


def prefix_report(lm):
    calls = [msgs(e) for e in lm.history]
    for a in range(len(calls) - 1):
        prev, new = calls[a], calls[a + 1]
        strict = len(new) > len(prev) and prev == new[: len(prev)]
        body_ok = len(prev) >= 1 and prev[:-1] == new[: len(prev) - 1]
        tail_same = prev[-1] == new[-1] if prev and new else False
        first_diff = next((i for i, (x, y) in enumerate(zip(prev, new)) if x != y), None)
        print(f"   call{a}->call{a + 1}: strict_prefix={strict} prefix_except_last={body_ok} "
              f"last_msg_identical={tail_same} first_diff_index={first_diff}")


# ---------------- Q1
class QA(dspy.Signature):
    """Answer the question."""

    question: str = dspy.InputField()
    history: dspy.History = dspy.InputField()
    answer: str = dspy.OutputField()


lm1 = DummyLM([{"answer": "Paris"}, {"answer": "Berlin"}])
with dspy.context(lm=lm1, adapter=dspy.ChatAdapter()):
    p = dspy.Predict(QA)
    o1 = p(question="Capital of France?", history=dspy.History(messages=[]))
    h = dspy.History(messages=[{"question": "Capital of France?", "answer": o1.answer}])
    p(question="Capital of Germany?", history=h)
show("Q1 Predict+History text mode", lm1)
prefix_report(lm1)


# ---------------- Q2
def search(query: str) -> str:
    """Search for information."""
    return f"result for {query}"


class Task(dspy.Signature):
    """Solve the task."""

    question: str = dspy.InputField()
    answer: str = dspy.OutputField()


script = [
    {"next_thought": "I should search.", "tool_calls": {"tool_calls": [{"name": "search", "args": {"query": "a"}}]}},
    {"next_thought": "Search again.", "tool_calls": {"tool_calls": [{"name": "search", "args": {"query": "b"}}]}},
    {"next_thought": "Done.", "tool_calls": {"tool_calls": [{"name": "submit", "args": {"answer": "42"}}]}},
]
lm2 = DummyLM(script)
with dspy.context(lm=lm2, adapter=dspy.ChatAdapter()):
    agent = dspy.ReActV2(Task, tools=[search], max_iters=5)
    try:
        out = agent(question="What is it?")
        print("\nQ2 result:", out.answer, out.termination_reason)
    except Exception as exc:  # noqa: BLE001 - spike: report whatever happens
        print("\nQ2 raised:", type(exc).__name__, exc)
show("Q2 ReActV2 text mode", lm2)
prefix_report(lm2)

# ---------------- Q3 native function calling: capture the request the adapter builds
print("\n==================== Q3 native function calling (request shape)")
adapter = dspy.ChatAdapter(use_native_function_calling=True)
agent3 = dspy.ReActV2(Task, tools=[search], max_iters=2)
sig = agent3.react.signature
try:
    formatted = adapter.format(sig, demos=[], inputs={
        "question": "What is it?",
        "history": dspy.History(messages=[]),
        "tools": list(agent3.tools.values()),
    })
    for j, msg in enumerate(formatted):
        print(f"   [{j}] {msg.get('role')}: {str(msg.get('content')).replace(chr(10), '\\n')[:300]}")
    print("   native-FC preprocess:")
    lm_kwargs: dict = {}
    processed = adapter._call_preprocess(DummyLM([]), lm_kwargs, sig, {
        "question": "What is it?", "history": dspy.History(messages=[]), "tools": list(agent3.tools.values())})
    print("   processed signature outputs:", list(processed.output_fields))
    print("   lm_kwargs keys:", sorted(lm_kwargs), json.dumps(lm_kwargs.get("tools", ""), default=str)[:400])
except Exception as exc:  # noqa: BLE001
    print("   Q3 raised:", type(exc).__name__, exc)

# ---------------- Q4 acall
async def q4() -> None:
    lm4 = DummyLM([{"answer": "ok"}])
    with dspy.context(lm=lm4, adapter=dspy.ChatAdapter()):
        r = await dspy.Predict("question -> answer").acall(question="hi")
        print("\nQ4 acall answer:", r.answer)

asyncio.run(q4())
