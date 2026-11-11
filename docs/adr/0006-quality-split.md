# ADR 0006: Quality Split

## Status

Accepted

## Decision

Use dbt tests for structural assertions and use reconciliation tables plus lightweight runtime checks
for source-to-serving validation.
