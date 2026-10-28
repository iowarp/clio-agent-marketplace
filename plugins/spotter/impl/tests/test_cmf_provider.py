"""CMF REST client contract tests."""

import httpx

from spotter_ai.config import CMFQueryConfig
from spotter_ai.providers.cmf import CMFProvider


def test_queries_current_stage_based_cmf_api() -> None:
    """Spotter uses CMF's current REST resources and preserves raw evidence."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/api/pipelines":
            return httpx.Response(200, json=["clio-live"])
        if request.url.path == "/api/pipeline-stages/clio-live":
            return httpx.Response(200, json={"stages": ["agent/tool"]})
        if request.url.path == "/api/executions-by-stage/clio-live":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "execution_id": 7,
                            "execution_properties": [
                                {"name": "Execution_uuid", "value": "execution-1"},
                                {"name": "clio_status", "value": "ok"},
                            ],
                        }
                    ]
                },
            )
        raise AssertionError(f"unexpected CMF request: {request.url}")

    client = httpx.Client(base_url="http://cmf.test", transport=httpx.MockTransport(handler))
    provider = CMFProvider(CMFQueryConfig("http://cmf.test", "clio-live"), client=client)

    assert provider.list_pipelines(10)["items"] == [{"pipeline": "clio-live"}]
    executions = provider.list_executions(None, None, 10)
    assert executions["items"][0]["execution_id"] == "execution-1"
    assert executions["items"][0]["extensions"]["cmf"]["execution_id"] == 7
    assert any(request.url.path.endswith("executions-by-stage/clio-live") for request in requests)


def test_normalizes_cmf_execution_lineage() -> None:
    """The graph contract retains CMF's full response in an extension."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/execution-lineage/tangled-tree/exe-1/pipeline-1"
        return httpx.Response(
            200,
            json={
                "nodes": [{"id": "a"}, {"id": "b"}],
                "links": [{"source": "a", "target": "b"}],
            },
        )

    client = httpx.Client(base_url="http://cmf.test", transport=httpx.MockTransport(handler))
    provider = CMFProvider(CMFQueryConfig("http://cmf.test", "pipeline-1"), client=client)

    result = provider.execution_lineage(None, "exe-1")

    assert result["edges"] == [{"source": "a", "target": "b", "kind": "lineage"}]
    assert result["extensions"]["cmf"]["nodes"][0]["id"] == "a"


def test_resolves_clio_artifact_id_through_cmf_display_name() -> None:
    """The CLIO ID remains queryable even though CMF lineage exposes a display label."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/artifact-lineage/tangled-tree/pipeline-1":
            return httpx.Response(
                200,
                json=[[{"id": "result.txt://ar", "parents": ["input.txt://ar"]}]],
            )
        if request.url.path == "/api/pipeline-stages/pipeline-1":
            return httpx.Response(200, json={"stages": ["agent/tool"]})
        if request.url.path == "/api/artifact-types-by-stage/pipeline-1":
            return httpx.Response(200, json=["Dataset"])
        if request.url.path == "/api/artifacts-by-stage/pipeline-1":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "artifact_id": 7,
                            "name": "result.txt:clio://artifact/artifact-1",
                            "artifact_properties": [
                                {"name": "clio_artifact_id", "value": "artifact-1"}
                            ],
                        }
                    ]
                },
            )
        raise AssertionError(f"unexpected CMF request: {request.url}")

    client = httpx.Client(base_url="http://cmf.test", transport=httpx.MockTransport(handler))
    provider = CMFProvider(CMFQueryConfig("http://cmf.test", "pipeline-1"), client=client)

    result = provider.artifact_lineage(None, "artifact-1")

    assert result["root"] == "artifact-1"
    assert result["nodes"][0]["id"] == "artifact-1"
    assert result["nodes"][0]["extensions"]["cmf"]["display_id"] == "result.txt://ar"
    assert result["edges"] == [
        {"source": "input.txt://ar", "target": "artifact-1", "kind": "generated"}
    ]
