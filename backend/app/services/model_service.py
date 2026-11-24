"""Model assurance, calibration, and drift snapshot service."""

from __future__ import annotations

from typing import Any

from app.services.repository import NidanRepository


class ModelService:
    """Serves model registry, calibration, drift, and promotion gate state."""

    def __init__(self, repo: NidanRepository) -> None:
        self.repo = repo

    async def get_health(self) -> dict[str, Any]:
        return await self.repo.get_model_health()
