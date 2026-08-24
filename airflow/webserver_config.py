"""Web configuration for the Airflow FAB authentication manager."""

# Airflow 2 database sessions use a serializer that Airflow 3 cannot decode.
# A versioned cookie name makes upgraded browsers start a clean Airflow 3
# session while preserving the historical session rows for normal expiry.
SESSION_COOKIE_NAME = "airflow_session_v3"
