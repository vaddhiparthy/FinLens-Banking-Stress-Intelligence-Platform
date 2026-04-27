from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT_DIR / "docs"
INGESTION_DIR = ROOT_DIR / "ingestion"
TESTS_DIR = ROOT_DIR / "tests"
RAW_DATA_DIR = ROOT_DIR / "data" / "raw"
DLQ_DATA_DIR = ROOT_DIR / "data" / "dlq"
STATE_DIR = ROOT_DIR / "data" / "state"
