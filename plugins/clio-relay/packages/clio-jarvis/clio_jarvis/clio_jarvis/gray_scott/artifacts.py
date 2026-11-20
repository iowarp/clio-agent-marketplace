"""jarvis-cd artifact provider: the package's contract.yaml drives it (RL40)."""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE.parents[1]) not in sys.path:
    sys.path.insert(0, str(_HERE.parents[1]))

from clio_jarvis._contract.runtime import artifact_adapter  # noqa: E402


def adapter_from_package(context):
    return artifact_adapter(_HERE, context)
