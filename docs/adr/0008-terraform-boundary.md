# ADR 0008: Terraform Boundary

## Status

Superseded by [ADR 0009](0009-vps-local-storage.md)

## Decision

(Original) Use Terraform for S3, IAM, and Snowflake-adjacent resources while keeping DNS and
app-hosting setup as click-ops.

(Superseded) With S3 removed and the warehouse on local DuckDB, there are no cloud resources left
to provision. Terraform was deleted; deployment is Caddy + `docker-compose.prod.yml` on a VPS, with
Cloudflare at the edge. See ADR 0009.
