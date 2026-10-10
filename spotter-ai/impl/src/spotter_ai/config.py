"""Resolve Spotter's query providers from a CLIO provenance configuration."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

CONFIG_ENV = "SPOTTER_CLIO_CONFIG"


class SpotterConfigurationError(ValueError):
    """Raised when the CLIO configuration cannot describe a query provider."""


@dataclass(frozen=True)
class FlowceptQueryConfig:
    """Direct MongoDB query configuration derived from Flowcept settings."""

    uri: str
    database: str


@dataclass(frozen=True)
class CMFQueryConfig:
    """Direct CMF REST query configuration."""

    server_url: str
    pipeline_name: str


@dataclass(frozen=True)
class NativeQueryConfig:
    """Read-only CLIO/native JSONL and workspace locations."""

    jsonl_path: Path
    workspace_root: Path


@dataclass(frozen=True)
class SpotterConfig:
    """Selected agentic and artifact query providers."""

    source_path: Path
    agentic_provider: str
    artifact_provider: str
    flowcept: FlowceptQueryConfig | None = None
    cmf: CMFQueryConfig | None = None
    native: NativeQueryConfig | None = None
    attention_files_dir: Path | None = None
    #: How the agentic query lane was chosen: ``configured`` (query_default set),
    #: ``only_enabled`` (the single enabled provider) or ``default_jsonl`` (several
    #: enabled, none chosen: the native journal answers, ``alternatives`` do not).
    agentic_selected_by: str = "configured"
    agentic_alternatives: tuple[str, ...] = ()


def load_config(path: str | Path | None = None) -> SpotterConfig:
    """Load one explicit CLIO YAML file and resolve Spotter's active providers."""
    raw_path = str(path or os.environ.get(CONFIG_ENV, "")).strip()
    if not raw_path:
        raise SpotterConfigurationError(
            f"configure a CLIO config path with --clio-config or {CONFIG_ENV}"
        )
    source = Path(raw_path).expanduser().resolve()
    if not source.is_file():
        raise SpotterConfigurationError(f"CLIO config file does not exist: {source}")
    try:
        document = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise SpotterConfigurationError(f"could not read CLIO config {source}: {exc}") from exc
    if not isinstance(document, Mapping):
        raise SpotterConfigurationError("CLIO config must contain a YAML object")

    providers = _string_list(_value(document, "provenance.agentic.providers", ["jsonl"]))
    providers = ["jsonl" if name in {"native", "file"} else name for name in providers]
    query_default = str(_value(document, "provenance.agentic.query_default", "")).strip().lower()
    if query_default in {"native", "file"}:
        query_default = "jsonl"
    selected_by = "configured"
    if not query_default:
        query_default = providers[0] if len(providers) == 1 else "jsonl"
        selected_by = "only_enabled" if len(providers) == 1 else "default_jsonl"
    if query_default not in providers:
        raise SpotterConfigurationError(
            f"agentic query provider {query_default!r} is not enabled in {providers!r}"
        )
    if query_default not in {"jsonl", "flowcept"}:
        raise SpotterConfigurationError(f"unsupported agentic query provider: {query_default}")

    artifact_provider = (
        str(_value(document, "provenance.artifacts.provider", "native")).strip().lower()
    )
    if artifact_provider not in {"native", "cmf"}:
        raise SpotterConfigurationError(f"unsupported artifact query provider: {artifact_provider}")

    attention_root = str(_value(document, "provenance.attention.files_dir", "")).strip()
    if attention_root and "flowcept" not in providers:
        raise SpotterConfigurationError(
            "attention queries require Flowcept among enabled providers"
        )
    flowcept = (
        _flowcept_config(document, source)
        if query_default == "flowcept" or attention_root
        else None
    )
    cmf = _cmf_config(document) if artifact_provider == "cmf" else None
    native = (
        _native_config(document, source)
        if query_default == "jsonl" or artifact_provider == "native"
        else None
    )
    return SpotterConfig(
        source_path=source,
        agentic_provider=query_default,
        artifact_provider=artifact_provider,
        agentic_selected_by=selected_by,
        agentic_alternatives=tuple(name for name in providers if name != query_default),
        flowcept=flowcept,
        cmf=cmf,
        native=native,
        attention_files_dir=_resolved_path(attention_root, source.parent)
        if attention_root
        else None,
    )


def _flowcept_config(document: Mapping[str, Any], source: Path) -> FlowceptQueryConfig:
    settings_value = str(_value(document, "provenance.agentic.flowcept.settings_path", "")).strip()
    if not settings_value:
        raise SpotterConfigurationError(
            "Flowcept queries require provenance.agentic.flowcept.settings_path"
        )
    settings_path = _resolved_path(settings_value, source.parent)
    try:
        settings = yaml.safe_load(settings_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise SpotterConfigurationError(
            f"could not read Flowcept settings {settings_path}: {exc}"
        ) from exc
    if not isinstance(settings, Mapping):
        raise SpotterConfigurationError("Flowcept settings must contain a YAML object")
    enabled = bool(_value(settings, "databases.mongodb.enabled", False))
    if not enabled:
        raise SpotterConfigurationError("Spotter requires Flowcept MongoDB query storage")
    uri = str(_value(settings, "databases.mongodb.uri", "")).strip()
    if not uri:
        host = str(_value(settings, "databases.mongodb.host", "localhost")).strip()
        port = int(_value(settings, "databases.mongodb.port", 27017))
        uri = f"mongodb://{host}:{port}"
    database = str(_value(settings, "databases.mongodb.db", "")).strip()
    if not database:
        database = str(_value(settings, "project.name", "flowcept")).strip() or "flowcept"
    return FlowceptQueryConfig(uri=uri, database=database)


def _cmf_config(document: Mapping[str, Any]) -> CMFQueryConfig:
    server_url = str(_value(document, "provenance.artifacts.cmf.server_url", "")).strip()
    if not server_url:
        raise SpotterConfigurationError("CMF queries require provenance.artifacts.cmf.server_url")
    pipeline = str(_value(document, "provenance.artifacts.cmf.pipeline_name", "clio-agent")).strip()
    return CMFQueryConfig(server_url=server_url.rstrip("/"), pipeline_name=pipeline or "clio-agent")


def _native_config(document: Mapping[str, Any], source: Path) -> NativeQueryConfig:
    jsonl_value = str(_value(document, "provenance.agentic.jsonl.path", "")).strip()
    if not jsonl_value:
        raise SpotterConfigurationError(
            "native queries require an explicit provenance.agentic.jsonl.path"
        )
    workspace_value = str(
        _value(document, "provenance.artifacts.native.workspace_root", "")
    ).strip()
    if workspace_value:
        workspace_root = _resolved_path(workspace_value, source.parent)
    elif source.parent.name == ".clio":
        workspace_root = source.parent.parent.resolve()
    else:
        raise SpotterConfigurationError(
            "native queries require provenance.artifacts.native.workspace_root when the "
            "config is not <workspace>/.clio/config.yaml"
        )
    return NativeQueryConfig(
        jsonl_path=_resolved_path(jsonl_value, source.parent),
        workspace_root=workspace_root,
    )


def _resolved_path(value: str, base: Path) -> Path:
    path = Path(value).expanduser()
    return (base / path).resolve() if not path.is_absolute() else path.resolve()


def _value(document: Mapping[str, Any], dotted: str, default: Any) -> Any:
    if dotted in document:
        return document[dotted]
    current: Any = document
    for part in dotted.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return default
        current = current[part]
    return current


def _string_list(value: Any) -> list[str]:
    raw = value if isinstance(value, (list, tuple)) else str(value).split(",")
    return [str(item).strip().lower() for item in raw if str(item).strip()]
