"""DSPy 3.4.0 spike Q3: native function calling message layout across a history."""

from __future__ import annotations

import json
import warnings

import dspy
from dspy.adapters.types.tool import ToolCallResults, ToolCalls
from dspy.utils.dummies import DummyLM

warnings.filterwarnings("ignore")


class FCLM(DummyLM):
    """A scripted LM that declares native function-calling + reasoning support."""

    @property
    def supports_function_calling(self) -> bool:  # type: ignore[override]
        return True

    @property
    def supports_reasoning(self) -> bool:  # type: ignore[override]
        return True


def search(query: str) -> str:
    """Search for information."""
    return f"result for {query}"


class Task(dspy.Signature):
    """Solve the task."""

    question: str = dspy.InputField()
    answer: str = dspy.OutputField()


agent = dspy.ReActV2(Task, tools=[search], max_iters=3)
sig = agent.react.signature
tools = list(agent.tools.values())
adapter = dspy.ChatAdapter(use_native_function_calling=True)
lm = FCLM([])

calls = ToolCalls(tool_calls=[ToolCalls.ToolCall(id="call_0_0", name="search", args={"query": "a"})])
calls = calls.model_copy(update={"tool_call_results": ToolCallResults.from_tool_calls_and_values(
    calls, ["result for a"], [False])})

for step, history in enumerate([
    dspy.History(messages=[]),
    dspy.History(messages=[{"question": "What is it?", "next_thought": "I should search.", "tool_calls": calls}]),
]):
    inputs = {"history": history, "tools": tools}
    if step == 0:
        inputs["question"] = "What is it?"
    lm_kwargs: dict = {}
    processed = adapter._call_preprocess(lm, lm_kwargs, sig, dict(inputs))
    formatted = adapter.format(processed, demos=[], inputs=dict(inputs))
    print(f"\n=== native step {step}: processed outputs={list(processed.output_fields)} "
          f"lm_kwargs={sorted(lm_kwargs)} reasoning_effort={lm_kwargs.get('reasoning_effort')}")
    print("   tools kwarg:", json.dumps([t['function']['name'] for t in lm_kwargs.get('tools', [])]))
    for j, msg in enumerate(formatted):
        extra = {k: v for k, v in msg.items() if k not in ("role", "content")}
        print(f"   [{j}] {msg.get('role')}: {str(msg.get('content')).replace(chr(10), '\\n')[:240]}"
              f"{'  EXTRA=' + json.dumps(extra, default=str)[:240] if extra else ''}")
