"""SQLite-backed provenance capture for the SPOTTER-AI pipeline."""

from spotter_ai.provenance.store import ArtifactRef, ProvenanceStore, default_db_path

__all__ = ["ArtifactRef", "ProvenanceStore", "default_db_path"]
