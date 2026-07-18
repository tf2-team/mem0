"""AWS RDS IAM database authentication helpers."""

from __future__ import annotations

import os


def rds_iam_auth_enabled(value: str | None = None) -> bool:
    """Return whether RDS IAM authentication is enabled for this process."""
    setting = value if value is not None else os.getenv("MEM0_RDS_IAM_AUTH", "false")
    return setting.strip().lower() in {"1", "true", "yes", "on"}


def generate_rds_iam_auth_token(host: str, port: int, user: str, region: str | None = None) -> str:
    """Generate a short-lived PostgreSQL password using ambient AWS credentials.

    On EKS, boto3 resolves these credentials through the service account's IRSA
    role. The token is never persisted and is valid only for opening a new
    database connection.
    """
    resolved_region = region or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
    if not resolved_region:
        raise RuntimeError("AWS_REGION is required when MEM0_RDS_IAM_AUTH is enabled.")

    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("boto3 is required when MEM0_RDS_IAM_AUTH is enabled.") from exc

    return boto3.client("rds", region_name=resolved_region).generate_db_auth_token(
        DBHostname=host,
        Port=int(port),
        DBUsername=user,
        Region=resolved_region,
    )
