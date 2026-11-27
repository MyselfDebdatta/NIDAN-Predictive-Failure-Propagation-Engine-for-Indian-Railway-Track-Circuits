"""CLI runner for one-way read-only CRIS SMMS asset & precedent sync.

Usage:
    python -m app.cli.smms_sync --input smms_export.json
    cat smms_export.json | python -m app.cli.smms_sync --input -
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from app.config import get_settings
from app.connectors.smms import SmmsReadSyncAdapter, SmmsSyncRequest
from app.database import DatabaseManager
from app.services import MemoryRepository, PostgresRepository


async def _run_sync(raw_text: str) -> dict[str, object]:
    cfg = get_settings()
    db = DatabaseManager(
        cfg.database_url,
        cfg.redis_url,
        data_mode=cfg.data_mode,
        require_postgres=cfg.require_postgres,
    )
    await db.connect()
    try:
        repo = (
            PostgresRepository(db.pool)
            if db.pool is not None
            else MemoryRepository(cfg.fixtures_snapshot_path)
        )
        adapter = SmmsReadSyncAdapter(repo)
        request = SmmsSyncRequest.model_validate(json.loads(raw_text))
        response = await adapter.sync(request)
        return response.model_dump(by_alias=True)
    finally:
        await db.disconnect()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NIDAN Phase 4 read-only SMMS sync CLI.")
    parser.add_argument(
        "--input",
        required=True,
        help="Path to JSON SMMS export payload, or '-' for stdin.",
    )
    args = parser.parse_args(argv)
    raw_text = (
        sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
    )
    result = asyncio.run(_run_sync(raw_text))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
