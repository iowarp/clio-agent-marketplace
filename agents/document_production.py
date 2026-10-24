"""Document Production: one document specialist for CLIO's artifact review loop."""

from clio_agent.sdk import Agent


class DocumentProduction(Agent):
    """Creates and revises documents with anchored review and compatibility validation."""

    id = "document-production"
    version = "0.2.0"
    name = "Document Production"
    role = (
        "a writer and editor of documents in Markdown, HTML, LaTeX/PDF, Office and "
        "OpenDocument formats"
    )
    description = (
        "Creates and revises Markdown, HTML, LaTeX/PDF, OOXML, and OpenDocument artifacts with "
        "anchored human review and compatibility validation."
    )
    plugins = Agent.plugins + ["document-production", "workspace", "shell"]
