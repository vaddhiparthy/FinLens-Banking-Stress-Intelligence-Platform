from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(dotenv_path=Path(".env"), override=False)


class Settings(BaseSettings):
    project_name: str = "FinLens"
    finlens_environment: str = "local"
    root_domain: str = "vaddhiparthy.vip"
    project_domain: str = "finlens.vaddhiparthy.vip"
    finlens_data_mode: str = "mock"
    finlens_active_sources: str = "fdic,fred,qbp,nic"
    finlens_artifact_dir: str = "data"
    finlens_public_base_url: str | None = None
    finlens_api_base_url: str | None = None
    finlens_telemetry_enabled: bool = True
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_default_region: str | None = None
    aws_s3_mirror_enabled: bool = False
    aws_s3_raw_bucket: str = "finlens-raw"
    aws_s3_dlq_bucket: str = "finlens-dlq"
    aws_s3_marts_bucket: str = "finlens-marts"
    aws_s3_docs_bucket: str = "finlens-docs"
    aws_s3_tfstate_bucket: str = "finlens-tfstate"
    fdic_failed_banks_url: str = "https://www.fdic.gov/bank-failures/download-data.csv"
    fdic_qbp_source_url: str | None = (
        "https://api.fdic.gov/banks/summary?"
        "filters=STNAME:%22United%20States%22%20AND%20YEAR:%5B%221985%22%20TO%20%222025%22%5D&"
        "fields=YEAR,STNAME,ASSET,DEP,EQ,NETINC,NIM,DRLNLS,P9LNLS&"
        "sort_by=YEAR&sort_order=ASC&limit=100&format=json"
    )
    fred_api_key: str | None = None
    fred_base_url: str = "https://api.stlouisfed.org/fred"
    fred_series_ids: str = "UNRATE,DGS10,DGS2,BAA10Y,NFCI,CPIAUCSL"
    nic_current_parent_source_url: str | None = (
        "https://api.fdic.gov/banks/institutions?"
        "filters=ACTIVE:1&fields=CERT,NAME,ACTIVE,BKCLASS,STALP,REGAGNT,ASSET,DEP,ROA,ROE,DATEUPDT&"
        "sort_by=ASSET&sort_order=DESC&limit=10000&format=json"
    )
    postgres_sync_dsn: str | None = None
    postgres_sync_schema: str = "finlens"
    cloudflare_turnstile_site_key: str | None = None
    cloudflare_turnstile_secret_key: str | None = None
    cloudflare_account_id: str | None = None
    cloudflare_zone_id: str | None = None
    airflow_api_base_url: str = "http://airflow-webserver:8080"
    snowflake_account: str | None = None
    snowflake_user: str | None = None
    snowflake_password: str | None = None
    snowflake_role: str = "FINLENS_ROLE"
    snowflake_loading_warehouse: str = "LOADING_WH"
    snowflake_transforming_warehouse: str = "TRANSFORMING_WH"
    snowflake_database_raw: str = "FINLENS_RAW"
    snowflake_database_staging: str = "FINLENS_STAGING"
    snowflake_database_intermediate: str = "FINLENS_INTERMEDIATE"
    snowflake_database_marts: str = "FINLENS_MARTS"
    cloudflare_api_token: str | None = None
    streamlit_app_title: str = "FinLens Dashboard"
    fastapi_env: str = "local"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def require(self, *keys: str) -> None:
        missing = [key for key in keys if not getattr(self, key)]
        if missing:
            joined = ", ".join(sorted(missing))
            raise ValueError(f"Missing required environment variables: {joined}")

    def missing_or_placeholder(self, *keys: str) -> list[str]:
        return [key for key in keys if self.is_missing_or_placeholder(key)]

    def as_masked_dict(self, keys: Iterable[str] | None = None) -> dict[str, str]:
        selected_keys = list(keys) if keys is not None else sorted(self.model_fields)
        masked: dict[str, str] = {}

        for key in selected_keys:
            value = getattr(self, key, None)
            if value in (None, ""):
                masked[key] = "<unset>"
                continue

            if "key" in key or "token" in key or "password" in key or "secret" in key:
                masked[key] = "***"
            else:
                masked[key] = str(value)

        return masked

    @property
    def fred_series_id_list(self) -> list[str]:
        return [item.strip() for item in self.fred_series_ids.split(",") if item.strip()]

    @property
    def bucket_names(self) -> dict[str, str]:
        return {
            "raw": self.aws_s3_raw_bucket,
            "dlq": self.aws_s3_dlq_bucket,
            "marts": self.aws_s3_marts_bucket,
            "docs": self.aws_s3_docs_bucket,
            "tfstate": self.aws_s3_tfstate_bucket,
        }

    @property
    def active_source_list(self) -> list[str]:
        return [
            item.strip().lower()
            for item in self.finlens_active_sources.split(",")
            if item.strip()
        ]

    def is_missing_or_placeholder(self, key: str) -> bool:
        value = getattr(self, key, None)
        if value in (None, ""):
            return True
        normalized = str(value).strip().lower()
        placeholders = {
            "changeme",
            "replace-me",
            "replace_me",
            "your-value-here",
            "your_value_here",
            "finlens dev contact@example.com",
        }
        return normalized in placeholders


@lru_cache
def get_settings() -> Settings:
    return Settings()
