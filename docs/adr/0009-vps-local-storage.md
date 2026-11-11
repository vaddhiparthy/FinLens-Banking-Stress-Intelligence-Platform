# ADR 0009: VPS Local Storage (replaces S3 and Terraform)

## Status

Accepted

## Context

The earlier design (ADR 0001, ADR 0008) used AWS S3 as the raw landing zone and Terraform to
provision the buckets. In practice the S3 mirror was optional scaffold (`AWS_S3_MIRROR_ENABLED`,
off by default) and never the live path: raw data already landed on the local filesystem. Keeping
S3 meant carrying a billable dependency, AWS credentials, a boto3 dependency, and Terraform whose
only resources were the buckets. The goal is $0, self-hosted, no-cloud-object-store, with no chance
of incurring cost.

## Decision

- Remove Amazon S3 entirely: `src/finlens/aws.py`, the `aws_*` settings and `bucket_names`, the S3
  upload calls in the ingestion writers, the S3 platform probe, the boto3 dependency, the Terraform
  `s3_buckets` module and the whole `terraform/` directory, and the dead terraform CI workflow.
- Raw data is stored on the **VPS local filesystem** at
  `data/raw/source=<src>/ingestion_date=YYYY-MM-DD/<uuid>.json`, Hive-partitioned by source and
  ingestion date. This is directly loadable by DuckDB and gives a durable replay/audit boundary.
- A **rotation policy** (`scripts/rotate_raw_data.py`) retains exactly one version per source (the
  newest `ingestion_date`) and purges older partitions, so the landing zone does not grow unbounded.
- Deployment is **Caddy + `docker-compose.prod.yml`** on the VPS, with Cloudflare at the edge for
  DNS, TLS, and the branded domain. No infrastructure-as-code is needed because there are no cloud
  resources to provision.

## Consequences

- The `$0` invariant is strengthened: the `test_no_billable_imports` guard still forbids
  `finlens.aws` / `boto3` / `snowflake` imports in the ML subsystem, and those modules no longer
  exist on the raw-storage path.
- Snowflake remains an optional, credential-gated warehouse output in dbt; DuckDB is the warehouse
  of record. Removing S3 does not affect that boundary.
- Disaster recovery for raw payloads now depends on VPS backups rather than S3 durability; this is
  an accepted trade-off for a portfolio project, and the warehouse can always be rebuilt from a
  fresh ingestion run.
