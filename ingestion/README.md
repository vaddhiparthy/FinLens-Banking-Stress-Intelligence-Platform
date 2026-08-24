# Ingestion

Source ingestion scripts for the approved FinLens source set live here.

Active source clients:
- `fdic.py` for FDIC BankFind failure data
- `fred.py` for FRED macro series
- `qbp.py` for official FDIC quarterly time-series XLSX discovery, preservation, and normalization
- `nic.py` for current-parent NIC metadata artifacts

SEC, FR Y-9C, SLOOS, and UBPR are outside the current resilient build scope.
