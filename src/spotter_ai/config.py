"""Server-side workload configuration, resolved once from the environment.

Campaign name and data directory are workspace-fixed for the lifetime of a
running ``phenotype-workload``/``spotter`` server process: a demo box points
one server pair at one campaign's data directory and that never changes
mid-session. They are therefore NOT per-call tool arguments -- a model
should never be asked to repeat a constant on every call (that was the
defect: ``campaign``/``data_dir`` showing up in every tool schema, and
``spotter_campaign_health`` observed being called with ``campaign: null``).

Both resolve from environment variables, following the same pattern already
established by :func:`spotter_ai.provenance.store.default_db_path` and its
``SPOTTER_DB`` variable:

- ``SPOTTER_CAMPAIGN`` -- the campaign name (default:
  :data:`DEFAULT_CAMPAIGN_NAME`).
- ``SPOTTER_DATA_DIR`` -- the campaign data directory (default:
  :data:`DEFAULT_DATA_DIR`, resolved relative to the server's cwd).

Callers resolve these ONCE (at server construction / process start) and
close over the result -- they are not re-read per tool call.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Campaign name applied when ``SPOTTER_CAMPAIGN`` is unset. Matches the
#: campaign CLI's own historical default (see
#: :mod:`spotter_ai.pipeline.campaign`).
DEFAULT_CAMPAIGN_NAME = "phenotype-2026"

#: Campaign data directory (relative to the server's cwd) applied when
#: ``SPOTTER_DATA_DIR`` is unset.
DEFAULT_DATA_DIR = "./campaign_data"


def resolve_campaign_name() -> str:
    """Resolve the campaign name from ``SPOTTER_CAMPAIGN``, or the default.

    Returns:
        The value of ``SPOTTER_CAMPAIGN`` if set, otherwise
        :data:`DEFAULT_CAMPAIGN_NAME`.
    """
    return os.environ.get("SPOTTER_CAMPAIGN", DEFAULT_CAMPAIGN_NAME)


def resolve_data_dir() -> Path:
    """Resolve the campaign data directory from ``SPOTTER_DATA_DIR``, or the default.

    Returns:
        The path from ``SPOTTER_DATA_DIR`` if set, otherwise
        :data:`DEFAULT_DATA_DIR`.
    """
    return Path(os.environ.get("SPOTTER_DATA_DIR", DEFAULT_DATA_DIR))
