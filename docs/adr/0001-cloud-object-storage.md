# ADR 0001: Cloud Object Storage

## Status

Superseded by [ADR 0009](0009-vps-local-storage.md)

## Context

FinLens needs a low-cost landing zone for raw API payloads and downstream artifact publication.

## Decision

(Original) Use AWS S3 for raw ingestion, DLQ, marts, docs, and Terraform state.

(Superseded) AWS S3 was removed entirely. Raw payloads now land on the VPS local filesystem
under `data/raw/`, partitioned by source and ingestion date, with a rotation policy that retains
one version per source. See ADR 0009.
