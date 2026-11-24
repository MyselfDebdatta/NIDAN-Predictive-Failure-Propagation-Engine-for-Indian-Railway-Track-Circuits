"""Rolling Block maintenance windows and jobs service."""

from __future__ import annotations

from typing import Any

from app.services.repository import NidanRepository


class BlockService:
    """Provides published Rolling Block windows and fitted maintenance jobs."""

    def __init__(self, repo: NidanRepository) -> None:
        self.repo = repo

    async def get_blocks(
        self, *, date_from: str | None = None, date_to: str | None = None
    ) -> dict[str, Any]:
        data = await self.repo.get_blocks()
        if date_from or date_to:
            windows = [
                w
                for w in data["windows"]
                if (not date_from or w["date"] >= date_from)
                and (not date_to or w["date"] <= date_to)
            ]
            allowed_ids = {w["id"] for w in windows}
            jobs = [
                j for j in data["jobs"] if j.get("blockId") is None or j["blockId"] in allowed_ids
            ]
            data["windows"] = windows
            data["jobs"] = jobs
        return data
