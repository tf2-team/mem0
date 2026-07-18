"""Bootstrap the least-privilege PostgreSQL role used by Mem0 on Amazon RDS.

This command is safe to run repeatedly from a Kubernetes migration Job. It
uses the RDS-managed master credential only during bootstrap; the Mem0 API
later connects as ``mem0_app`` with an IRSA-generated IAM token.
"""

from __future__ import annotations

import os

import psycopg
from psycopg import sql


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required for RDS IAM bootstrap.")
    return value


def bootstrap() -> None:
    app_user = os.getenv("POSTGRES_USER", "mem0_app")
    database = _required("POSTGRES_DB")
    with psycopg.connect(
        host=_required("MEM0_RDS_MASTER_HOST"),
        port=int(os.getenv("MEM0_RDS_MASTER_PORT", "5432")),
        dbname=database,
        user=_required("MEM0_RDS_MASTER_USERNAME"),
        password=_required("MEM0_RDS_MASTER_PASSWORD"),
        sslmode=os.getenv("POSTGRES_SSLMODE", "require"),
        autocommit=True,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (app_user,))
            if cur.fetchone() is None:
                cur.execute(sql.SQL("CREATE ROLE {} LOGIN").format(sql.Identifier(app_user)))

            cur.execute(sql.SQL("GRANT rds_iam TO {}").format(sql.Identifier(app_user)))
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(sql.SQL("GRANT CONNECT, TEMPORARY ON DATABASE {} TO {}").format(sql.Identifier(database), sql.Identifier(app_user)))
            cur.execute(sql.SQL("GRANT USAGE, CREATE ON SCHEMA public TO {}").format(sql.Identifier(app_user)))


if __name__ == "__main__":
    bootstrap()
