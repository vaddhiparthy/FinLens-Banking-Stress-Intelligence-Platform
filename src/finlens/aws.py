from __future__ import annotations

from pathlib import Path

import boto3

from finlens.config import get_settings
from finlens.ingestion.base import IngestionTarget, build_s3_key


def s3_client():
    settings = get_settings()
    settings.require("aws_access_key_id", "aws_secret_access_key", "aws_default_region")
    return boto3.client(
        "s3",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_default_region,
    )


def upload_json_artifact(path: Path, target: IngestionTarget) -> str:
    client = s3_client()
    settings = get_settings()
    bucket = settings.aws_s3_dlq_bucket if target.dead_letter else settings.aws_s3_raw_bucket
    key = build_s3_key(target).split(f"s3://{bucket}/", maxsplit=1)[1]
    client.upload_file(str(path), bucket, key)
    return f"s3://{bucket}/{key}"


def upload_artifact_if_configured(path: Path, target: IngestionTarget) -> str | None:
    settings = get_settings()
    if not settings.aws_s3_mirror_enabled:
        return None
    try:
        return upload_json_artifact(path, target)
    except Exception:
        return None
