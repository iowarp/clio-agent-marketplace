"""Server-side workload configuration, resolved once from the environment.

Campaign name, data directory, and the provenance database path are
workspace-fixed for the lifetime of a running ``phenotype-workload``/
``spotter`` server process: a demo box points one server pair at one
campaign's data directory and that never changes mid-session. Campaign/
data-dir are therefore NOT per-call tool arguments -- a model should never
be asked to repeat a constant on every call (that was the defect:
``campaign``/``data_dir`` showing up in every tool schema, and
``spotter_campaign_health`` observed being called with ``campaign: null``).

All three resolve from environment variables:

- ``SPOTTER_CAMPAIGN`` -- the campaign name (default:
  :data:`DEFAULT_CAMPAIGN_NAME`).
- ``SPOTTER_DATA_DIR`` -- the campaign data directory (default:
  :data:`DEFAULT_DATA_DIR`, resolved relative to the server's cwd, but
  ALWAYS returned as an absolute path -- see :func:`resolve_data_dir`).
- ``SPOTTER_DB`` -- the provenance database path (default: see
  :func:`resolve_db_path` -- a SIBLING of the resolved data directory, not
  an independently cwd-relative literal; see that function's docstring for
  why).

Callers resolve these ONCE (at server construction / process start) and
close over the result -- they are not re-read per tool call.

Absoluteness matters beyond this process: every path a tool RETURNS (e.g.
``measure_cohort``'s ``written_path``) is built from :func:`resolve_data_dir`,
and clio-agent's platform auto-mints a recognized result-path key as a
workspace artifact by resolving it with ``Path(value).resolve()`` -- against
the PLATFORM SERVER's own process cwd, not this MCP server's. A relative
value here is therefore ambiguous downstream and silently fails that
platform's containment check (observed: #1218 r4, ``written_path`` returned
as ``campaign_data\reports\batch-001.json``, resolved against the wrong
process, rejected as outside the workspace root). Returning an already-
absolute path removes the ambiguity entirely -- resolving it again is then
always a no-op.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Campaign name applied when ``SPOTTER_CAMPAIGN`` is unset. Matches the
#: campaign CLI's own historical default (see
#: :mod:`phenotype_workload.pipeline.campaign`).
DEFAULT_CAMPAIGN_NAME = "phenotype-2026"

#: Campaign data directory (relative to the server's cwd) applied when
#: ``SPOTTER_DATA_DIR`` is unset.
DEFAULT_DATA_DIR = "./campaign_data"

#: Provenance database filename applied when ``SPOTTER_DB`` is unset -- see
#: :func:`resolve_db_path` for where it is placed.
DB_FILENAME = "spotter_provenance.sqlite"


def resolve_campaign_name() -> str:
    """Resolve the campaign name from ``SPOTTER_CAMPAIGN``, or the default.

    Returns:
        The value of ``SPOTTER_CAMPAIGN`` if set, otherwise
        :data:`DEFAULT_CAMPAIGN_NAME`.
    """
    return os.environ.get("SPOTTER_CAMPAIGN", DEFAULT_CAMPAIGN_NAME)


def resolve_data_dir() -> Path:
    """Resolve the campaign data directory from ``SPOTTER_DATA_DIR``, or the default.

    ALWAYS returns an absolute path, even when the source (an explicit
    relative ``SPOTTER_DATA_DIR``, or the relative :data:`DEFAULT_DATA_DIR`
    fallback) is relative -- resolved against THIS process's cwd, at the
    moment this is called (server construction). See the module docstring
    for why a relative result here is unsafe once it round-trips through a
    tool result to a DIFFERENT process (#1218 r4).

    Returns:
        The absolute path from ``SPOTTER_DATA_DIR`` if set, otherwise
        :data:`DEFAULT_DATA_DIR` resolved against this process's cwd.
    """
    return Path(os.environ.get("SPOTTER_DATA_DIR", DEFAULT_DATA_DIR)).resolve()


def resolve_db_path() -> Path:
    """Resolve the provenance database path -- the ONE location both the
    workload and forensic servers must agree on.

    ``SPOTTER_DB`` wins outright when set, resolved to an absolute path.

    When unset, the historical default was an independently cwd-relative
    literal (``Path("./spotter_provenance.sqlite")``, resolved against
    whatever the CURRENT PROCESS's cwd happened to be at connection time) --
    computed completely separately from :func:`resolve_data_dir`'s own,
    ALSO cwd-relative, default. The two could silently disagree whenever the
    workload and forensic server processes were launched with different
    working directories: a stray, empty database was observed created
    *inside* the campaign data directory (``<data_dir>/spotter_provenance.sqlite``)
    alongside the real one at the historical location one level up, when
    just one of the two servers resolved this fallback from a different cwd
    (#1218 r3).

    The fix anchors the fallback to the SAME resolution :func:`resolve_data_dir`
    already performs, rather than re-deriving cwd independently: the
    database sits as a SIBLING of the resolved data directory -- i.e. one
    level above ``campaign_data``, matching the historical workspace-root
    location -- so as long as both servers agree on ``SPOTTER_DATA_DIR``
    (or share a cwd), they now provably agree on the database path too,
    because both derive it from the one same resolution.

    Returns:
        The absolute path from ``SPOTTER_DB`` if set, otherwise
        ``resolve_data_dir().parent / DB_FILENAME`` (already absolute, since
        :func:`resolve_data_dir` now always returns one).
    """
    env_value = os.environ.get("SPOTTER_DB")
    if env_value:
        return Path(env_value).resolve()
    return resolve_data_dir().parent / DB_FILENAME
