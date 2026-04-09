"""Target schema configuration."""

from __future__ import annotations

import os


def get_target_schemas() -> list[str]:
    """Return list of Oracle schemas this instance manages.

    Reads from QC_SCHEMAS env var (comma-separated).
    Example: QC_SCHEMAS=PROD_ORDER,PROD_PLAN
    """
    raw = os.environ.get("QC_SCHEMAS", "")
    if not raw.strip():
        return []
    return [s.strip().upper() for s in raw.split(",") if s.strip()]
