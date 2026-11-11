# ADR 0001: Cloud Object Storage

## Status

Accepted

## Context

FinLens needs a low-cost landing zone for raw API payloads and downstream artifact publication.

## Decision

Use AWS S3 for raw ingestion, DLQ, marts, docs, and Terraform state.
