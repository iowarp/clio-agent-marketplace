"""The wildfire review's acquisition, analysis and map stages, as a workflow.

This replaces the blueprint's declared ``workflow:`` block. The workflow runs on
the ``workflow`` flow from ``core``: each stage is an ordinary child assignment of a
defined subagent, started once the stage before it finishes, and each stage
receives the task plus the earlier stages' answers and typed ``workflow_state``.
The main agent starts it with ``run_flow`` and writes the brief from its result.
"""

from __future__ import annotations

from typing import Any

from clio_agent.sdk import Flow, Step, Workflow

SMOKE_REVIEW = Workflow(
    steps=[
        Step(
            "start_with_data",
            "data",
            description=(
                "acquire active fire perimeters, derive the impacted region, then gather "
                "smoke-forecast and air-quality monitors over that region; return typed "
                "workflow_state.acquisition evidence"
            ),
        ),
        Step(
            "data_to_analysis",
            "analysis",
            after=["start_with_data"],
            description=(
                "select the impactful fire (smoke over monitored population, not acreage) and "
                "rank affected communities; return typed workflow_state.impact evidence"
            ),
        ),
        Step(
            "analysis_to_visualization",
            "visualization",
            after=["data_to_analysis"],
            description=(
                "render the situational map (fire perimeter + smoke + AQI monitors) to a PNG "
                "artifact over the region; the user asked for a map, so always render it, "
                "whether or not significant downwind impact was found"
            ),
        ),
    ]
)


class SmokeReview(Flow):
    """Run the three review stages in order and return their answers and typed state."""

    id = "smoke-review"
    description = (
        "Acquire fire, smoke and air-quality data, analyze downwind impact, render the map."
    )

    async def forward(self, task: Any, ctx: Any) -> Any:
        return await ctx.call("workflow", {"workflow": SMOKE_REVIEW.to_dict(), "task": task})
