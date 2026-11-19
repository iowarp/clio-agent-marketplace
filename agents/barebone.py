"""Barebone: the model alone, seeing only the conversation."""

from clio_agent.sdk import Agent


class BareboneAgent(Agent):
    """No system prompt, no tools, no context injections: every reply is the answer.

    For experiments that need the model's input to be exactly the person's text, such as
    attributing an answer's attention over the prompt (SPOTTER-AI), and for small local
    models, where a stock agent's instructions and tool schemas (13-31k tokens) would not
    fit the context. Needs a CLIO whose SDK supports ``Agent.bare``; the agent carries
    ``core`` because every agent must, and ``bare`` strips its prompt and tools.
    """

    id = "barebone"
    version = "1.0.0"
    name = "Barebone"
    role = "the bare model, answering from the conversation alone"
    description = (
        "The model with nothing added: no system prompt, no tools and no context "
        "injections, so its input is exactly the conversation. For attention attribution "
        "and other experiments on the model's own behavior, and for small local models."
    )
    plugins = ["core"]
    bare = True
