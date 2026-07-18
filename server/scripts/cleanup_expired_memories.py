"""Delete expired Mem0 memories from the pgvector collection.

This command is intentionally idempotent so it can run from a CronJob. Running
it repeatedly after all expired rows are gone deletes zero rows and exits 0.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

from psycopg import sql

from mem0.vector_stores.pgvector import PGVector


def _today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _collection_name() -> str:
    return os.environ.get("POSTGRES_COLLECTION_NAME", "memories")


def _build_store() -> PGVector:
    return PGVector(
        dbname=os.environ.get("POSTGRES_DB", "postgres"),
        collection_name=_collection_name(),
        embedding_model_dims=int(os.environ.get("MEM0_EMBEDDING_DIMS", "384")),
        user=os.environ.get("POSTGRES_USER", "postgres"),
        password=os.environ.get("POSTGRES_PASSWORD", "postgres"),
        host=os.environ.get("POSTGRES_HOST", "postgres"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        sslmode=os.environ.get("POSTGRES_SSLMODE", "require"),
        use_aws_iam_auth=os.environ.get("MEM0_RDS_IAM_AUTH", "false").lower() in {"1", "true", "yes", "on"},
        aws_region=os.environ.get("AWS_REGION"),
        diskann=False,
        hnsw=False,
    )


def cleanup_expired_memories(cutoff_date: str | None = None) -> int:
    store = _build_store()
    cutoff = cutoff_date or _today_iso()

    with store._get_cursor(commit=True) as cur:
        cur.execute(
            sql.SQL(
                """
                DELETE FROM {}
                WHERE payload ? 'expiration_date'
                  AND payload->>'expiration_date' < %s
                """
            ).format(store._col()),
            (cutoff,),
        )
        return cur.rowcount or 0


def main() -> int:
    cutoff = os.environ.get("MEM0_EXPIRED_MEMORY_CUTOFF_DATE", "").strip() or None
    deleted = cleanup_expired_memories(cutoff)
    sys.stdout.write(f"Deleted {deleted} expired memories from {_collection_name()}.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
