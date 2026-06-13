"""API router — all HTTP endpoints live here.

This module follows the architecture defined in ``docs/ARCHITECTURE.md``:

    | Router | app/api/router.py | All HTTP endpoints |
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Return a simple health-check response.

    Returns:
        A dictionary with a single ``status`` key.
    """
    return {"status": "ok"}
