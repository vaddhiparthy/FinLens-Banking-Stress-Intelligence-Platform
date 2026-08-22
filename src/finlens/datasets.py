from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DatasetBundle:
    failures: object
    metrics: object
    acquirers: object


def load_demo_bundle() -> DatasetBundle:
    import pandas as pd

    failures = pd.DataFrame(
        [
            {
                "bank_id": "bank-1",
                "bank_name": "Bank of Granite",
                "state": "NC",
                "year": 2009,
                "assets_millions": 2200,
                "acquirer": "First Citizens",
            },
            {
                "bank_id": "bank-2",
                "bank_name": "Silicon Valley Bank",
                "state": "CA",
                "year": 2023,
                "assets_millions": 209000,
                "acquirer": "First Citizens",
            },
            {
                "bank_id": "bank-3",
                "bank_name": "Signature Bank",
                "state": "NY",
                "year": 2023,
                "assets_millions": 118000,
                "acquirer": "Flagstar Bank",
            },
            {
                "bank_id": "bank-4",
                "bank_name": "Washington Mutual Bank",
                "state": "WA",
                "year": 2008,
                "assets_millions": 307000,
                "acquirer": "JPMorgan Chase",
            },
            {
                "bank_id": "bank-5",
                "bank_name": "Colonial Bank",
                "state": "AL",
                "year": 2009,
                "assets_millions": 25000,
                "acquirer": "BB&T",
            },
            {
                "bank_id": "bank-6",
                "bank_name": "First Republic Bank",
                "state": "CA",
                "year": 2023,
                "assets_millions": 229000,
                "acquirer": "JPMorgan Chase",
            },
            {
                "bank_id": "bank-7",
                "bank_name": "Guaranty Bank",
                "state": "TX",
                "year": 2009,
                "assets_millions": 13000,
                "acquirer": "BBVA Compass",
            },
            {
                "bank_id": "bank-8",
                "bank_name": "IndyMac Bank",
                "state": "CA",
                "year": 2008,
                "assets_millions": 32000,
                "acquirer": "OneWest Bank",
            },
        ]
    )
    metrics = pd.DataFrame(
        [
            {
                "series_id": "UNRATE",
                "date": "2008-01-01",
                "value": 5.0,
                "metric_name": "Unemployment Rate",
            },
            {
                "series_id": "UNRATE",
                "date": "2008-06-01",
                "value": 5.6,
                "metric_name": "Unemployment Rate",
            },
            {
                "series_id": "UNRATE",
                "date": "2008-09-01",
                "value": 6.2,
                "metric_name": "Unemployment Rate",
            },
            {
                "series_id": "UNRATE",
                "date": "2009-03-01",
                "value": 8.7,
                "metric_name": "Unemployment Rate",
            },
            {
                "series_id": "UNRATE",
                "date": "2009-09-01",
                "value": 9.8,
                "metric_name": "Unemployment Rate",
            },
            {
                "series_id": "UNRATE",
                "date": "2010-06-01",
                "value": 9.4,
                "metric_name": "Unemployment Rate",
            },
            {
                "series_id": "UNRATE",
                "date": "2022-06-01",
                "value": 3.6,
                "metric_name": "Unemployment Rate",
            },
            {
                "series_id": "UNRATE",
                "date": "2023-01-01",
                "value": 3.4,
                "metric_name": "Unemployment Rate",
            },
            {
                "series_id": "UNRATE",
                "date": "2023-03-01",
                "value": 3.5,
                "metric_name": "Unemployment Rate",
            },
            {
                "series_id": "UNRATE",
                "date": "2023-06-01",
                "value": 3.6,
                "metric_name": "Unemployment Rate",
            },
            {
                "series_id": "UNRATE",
                "date": "2023-09-01",
                "value": 3.8,
                "metric_name": "Unemployment Rate",
            },
            {
                "series_id": "UNRATE",
                "date": "2023-12-01",
                "value": 3.7,
                "metric_name": "Unemployment Rate",
            },
            {
                "series_id": "DGS10",
                "date": "2008-01-01",
                "value": 3.74,
                "metric_name": "10Y Treasury",
            },
            {
                "series_id": "DGS10",
                "date": "2008-06-01",
                "value": 4.10,
                "metric_name": "10Y Treasury",
            },
            {
                "series_id": "DGS10",
                "date": "2008-09-01",
                "value": 3.68,
                "metric_name": "10Y Treasury",
            },
            {
                "series_id": "DGS10",
                "date": "2009-03-01",
                "value": 2.82,
                "metric_name": "10Y Treasury",
            },
            {
                "series_id": "DGS10",
                "date": "2009-09-01",
                "value": 3.30,
                "metric_name": "10Y Treasury",
            },
            {
                "series_id": "DGS10",
                "date": "2010-06-01",
                "value": 3.21,
                "metric_name": "10Y Treasury",
            },
            {
                "series_id": "DGS10",
                "date": "2022-06-01",
                "value": 3.29,
                "metric_name": "10Y Treasury",
            },
            {
                "series_id": "DGS10",
                "date": "2023-01-01",
                "value": 3.53,
                "metric_name": "10Y Treasury",
            },
            {
                "series_id": "DGS10",
                "date": "2023-03-01",
                "value": 3.66,
                "metric_name": "10Y Treasury",
            },
            {
                "series_id": "DGS10",
                "date": "2023-06-01",
                "value": 3.81,
                "metric_name": "10Y Treasury",
            },
            {
                "series_id": "DGS10",
                "date": "2023-09-01",
                "value": 4.38,
                "metric_name": "10Y Treasury",
            },
            {
                "series_id": "DGS10",
                "date": "2023-12-01",
                "value": 4.02,
                "metric_name": "10Y Treasury",
            },
            {
                "series_id": "DGS2",
                "date": "2008-01-01",
                "value": 2.88,
                "metric_name": "2Y Treasury",
            },
            {
                "series_id": "DGS2",
                "date": "2008-06-01",
                "value": 2.63,
                "metric_name": "2Y Treasury",
            },
            {
                "series_id": "DGS2",
                "date": "2008-09-01",
                "value": 2.24,
                "metric_name": "2Y Treasury",
            },
            {
                "series_id": "DGS2",
                "date": "2009-03-01",
                "value": 0.94,
                "metric_name": "2Y Treasury",
            },
            {
                "series_id": "DGS2",
                "date": "2009-09-01",
                "value": 0.95,
                "metric_name": "2Y Treasury",
            },
            {
                "series_id": "DGS2",
                "date": "2010-06-01",
                "value": 0.73,
                "metric_name": "2Y Treasury",
            },
            {
                "series_id": "DGS2",
                "date": "2022-06-01",
                "value": 3.13,
                "metric_name": "2Y Treasury",
            },
            {
                "series_id": "DGS2",
                "date": "2023-01-01",
                "value": 4.42,
                "metric_name": "2Y Treasury",
            },
            {
                "series_id": "DGS2",
                "date": "2023-03-01",
                "value": 4.62,
                "metric_name": "2Y Treasury",
            },
            {
                "series_id": "DGS2",
                "date": "2023-06-01",
                "value": 4.71,
                "metric_name": "2Y Treasury",
            },
            {
                "series_id": "DGS2",
                "date": "2023-09-01",
                "value": 5.03,
                "metric_name": "2Y Treasury",
            },
            {
                "series_id": "DGS2",
                "date": "2023-12-01",
                "value": 4.33,
                "metric_name": "2Y Treasury",
            },
            {
                "series_id": "CPIAUCSL",
                "date": "2008-01-01",
                "value": 211.08,
                "metric_name": "Consumer Price Index",
            },
            {
                "series_id": "CPIAUCSL",
                "date": "2008-09-01",
                "value": 218.78,
                "metric_name": "Consumer Price Index",
            },
            {
                "series_id": "CPIAUCSL",
                "date": "2009-09-01",
                "value": 215.97,
                "metric_name": "Consumer Price Index",
            },
            {
                "series_id": "CPIAUCSL",
                "date": "2022-06-01",
                "value": 296.31,
                "metric_name": "Consumer Price Index",
            },
            {
                "series_id": "CPIAUCSL",
                "date": "2023-01-01",
                "value": 299.17,
                "metric_name": "Consumer Price Index",
            },
            {
                "series_id": "CPIAUCSL",
                "date": "2023-03-01",
                "value": 301.84,
                "metric_name": "Consumer Price Index",
            },
            {
                "series_id": "CPIAUCSL",
                "date": "2023-06-01",
                "value": 303.84,
                "metric_name": "Consumer Price Index",
            },
            {
                "series_id": "CPIAUCSL",
                "date": "2023-09-01",
                "value": 307.48,
                "metric_name": "Consumer Price Index",
            },
            {
                "series_id": "CPIAUCSL",
                "date": "2023-12-01",
                "value": 308.74,
                "metric_name": "Consumer Price Index",
            },
            {
                "series_id": "NFCI",
                "date": "2022-06-01",
                "value": 0.14,
                "metric_name": "National Financial Conditions Index",
            },
            {
                "series_id": "NFCI",
                "date": "2023-03-01",
                "value": 0.42,
                "metric_name": "National Financial Conditions Index",
            },
            {
                "series_id": "NFCI",
                "date": "2023-12-01",
                "value": -0.08,
                "metric_name": "National Financial Conditions Index",
            },
            {
                "series_id": "BAA10Y",
                "date": "2022-06-01",
                "value": 2.35,
                "metric_name": "Moody's BAA minus 10Y Treasury",
            },
            {
                "series_id": "BAA10Y",
                "date": "2023-03-01",
                "value": 2.74,
                "metric_name": "Moody's BAA minus 10Y Treasury",
            },
            {
                "series_id": "BAA10Y",
                "date": "2023-12-01",
                "value": 1.68,
                "metric_name": "Moody's BAA minus 10Y Treasury",
            },
        ]
    )
    acquirers = pd.DataFrame(
        [
            {
                "acquirer": "First Citizens",
                "decade": "2020s",
                "assets_absorbed_millions": 211200,
            },
            {
                "acquirer": "Flagstar Bank",
                "decade": "2020s",
                "assets_absorbed_millions": 118000,
            },
            {
                "acquirer": "JPMorgan Chase",
                "decade": "2000s",
                "assets_absorbed_millions": 536000,
            },
            {
                "acquirer": "BB&T",
                "decade": "2000s",
                "assets_absorbed_millions": 25000,
            },
            {
                "acquirer": "BBVA Compass",
                "decade": "2000s",
                "assets_absorbed_millions": 13000,
            },
        ]
    )
    return DatasetBundle(failures=failures, metrics=metrics, acquirers=acquirers)


def load_demo_stress_pulse():
    import pandas as pd

    quarters = pd.period_range("2020Q1", "2025Q4", freq="Q")
    return pd.DataFrame(
        {
            "quarter": quarters.astype(str),
            "net_income": [
                42, 38, 31, 29, 47, 51, 56, 58, 63, 59, 54, 49,
                44, 41, 35, 32, 40, 46, 52, 57, 60, 62, 65, 67,
            ],
            "roa": [
                1.15, 1.02, 0.84, 0.80, 1.05, 1.12, 1.18, 1.20, 1.24, 1.16, 1.03, 0.97,
                0.88, 0.82, 0.71, 0.66, 0.79, 0.90, 0.97, 1.02, 1.07, 1.10, 1.13, 1.16,
            ],
            "nim": [
                3.22, 3.11, 2.94, 2.87, 2.95, 3.02, 3.09, 3.15, 3.21, 3.17, 3.08, 2.98,
                2.84, 2.73, 2.62, 2.51, 2.54, 2.67, 2.81, 2.95, 3.04, 3.12, 3.18, 3.23,
            ],
            "problem_banks": [
                58, 61, 73, 81, 77, 72, 68, 64, 60, 57, 55, 54,
                56, 60, 64, 71, 78, 74, 69, 61, 55, 49, 44, 41,
            ],
            "asset_yield": [
                3.85, 3.62, 3.18, 2.94, 2.82, 2.76, 2.73, 2.70, 2.74, 2.88, 3.02, 3.18,
                3.41, 3.70, 4.08, 4.42, 4.67, 4.82, 4.94, 5.03, 5.06, 5.08, 5.11, 5.13,
            ],
            "funding_cost": [
                1.22, 1.11, 0.81, 0.46, 0.24, 0.18, 0.15, 0.16, 0.19, 0.27, 0.35, 0.48,
                0.72, 1.05, 1.46, 1.82, 2.19, 2.44, 2.63, 2.78, 2.89, 2.95, 3.00, 3.03,
            ],
            "noncurrent_rate": [
                0.86, 0.91, 1.02, 1.18, 1.14, 1.07, 0.98, 0.90, 0.82, 0.76, 0.70, 0.67,
                0.71, 0.79, 0.90, 1.04, 1.12, 1.16, 1.11, 1.02, 0.96, 0.92, 0.88, 0.85,
            ],
            "nco_rate": [
                0.31, 0.33, 0.37, 0.43, 0.39, 0.35, 0.32, 0.30, 0.27, 0.24, 0.23, 0.22,
                0.25, 0.29, 0.34, 0.40, 0.43, 0.45, 0.41, 0.36, 0.33, 0.31, 0.29, 0.28,
            ],
            "afs_losses": [
                -8, -12, -17, -22, -18, -14, -11, -9, -7, -12, -18, -31,
                -54, -83, -112, -136, -121, -106, -88, -74, -59, -44, -30, -18,
            ],
            "htm_losses": [
                -4, -5, -6, -8, -7, -6, -5, -5, -6, -9, -15, -24,
                -38, -59, -86, -109, -101, -93, -81, -69, -56, -42, -29, -18,
            ],
        }
    )
