"""Flowcept provider projection tests."""

from spotter_ai.providers.flowcept import _public, _workflow


def test_workflow_projection_matches_flowcept_agent_pruning() -> None:
    """Heavy runtime configuration does not enter an agent-facing workflow result."""
    result = _workflow(
        {
            "workflow_id": "workflow-1",
            "campaign_id": "campaign-1",
            "flowcept_settings": {"databases": {"password": "do-not-return"}},
            "conf": {"settings_path": "/private/settings.yaml"},
            "custom_metadata": {"clio": {"session_id": "session-1"}},
        }
    )

    evidence = result["extensions"]["flowcept"]
    assert "flowcept_settings" not in evidence
    assert "conf" not in evidence
    assert evidence["custom_metadata"]["clio"]["session_id"] == "session-1"


def test_public_projection_removes_nested_secret_keys() -> None:
    """Provider-specific evidence cannot leak common credential fields."""
    assert _public(
        {
            "host": "mongo.local",
            "password": "secret-value",
            "nested": {"api_key": "secret-value", "port": 27017},
        }
    ) == {"host": "mongo.local", "nested": {"port": 27017}}
