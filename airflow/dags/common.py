from datetime import timedelta

default_args = {
    "owner": "finlens",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}
