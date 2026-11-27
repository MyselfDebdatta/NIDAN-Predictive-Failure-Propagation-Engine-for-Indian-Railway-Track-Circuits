"""CLI telemetry ingestion worker running Stream QC against Postgres or fixture store.

Usage:
    python -m app.cli.ingest_worker --input sample.json --format canonical
    cat ccsp.json | python -m app.cli.ingest_worker --input - --format ccsp
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Literal

from app.config import get_settings
from app.database import DatabaseManager
from app.ingestion.worker import TelemetryIngestProcessor
from app.services import MemoryRepository, PostgresRepository, StreamHub


async def _run_ingest(
    raw_text: str,
    *,
    fmt: Literal["canonical", "ccsp", "rdpms"],
) -> dict[str, object]:
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
        hub = StreamHub(redis_client=db.redis)
        processor = TelemetryIngestProcessor(repo, stream_hub=hub)
        payload = json.loads(raw_text)
        return await processor.process_raw(payload, protocol=fmt)
    finally:
        await db.disconnect()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NIDAN Phase 3 telemetry ingestion worker.")
    parser.add_argument(
        "--input",
        required=True,
        help="Path to JSON payload, or '-' for stdin.",
    )
    parser.add_argument(
        "--format",
        choices=("canonical", "ccsp", "rdpms"),
        default="canonical",
        help="Input payload protocol format.",
    )
    args = parser.parse_args(argv)
    raw_text = (
        sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
    )
    result = asyncio.run(_run_ingest(raw_text, fmt=args.format))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
