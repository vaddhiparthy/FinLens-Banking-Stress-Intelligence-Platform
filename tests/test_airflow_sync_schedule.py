import ast
from pathlib import Path


def test_control_sync_uses_clock_time_trigger_timetable() -> None:
    source = Path("airflow/dags/dag_sync_control_plane.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    imports = {
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module == "airflow.timetables.trigger"
        for alias in node.names
    }
    assert "CronTriggerTimetable" in imports

    timetable_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "CronTriggerTimetable"
    ]
    assert len(timetable_calls) == 1
    timetable = timetable_calls[0]
    assert len(timetable.args) == 1
    assert ast.literal_eval(timetable.args[0]) == "0 5 * * *"
    keywords = {keyword.arg: ast.literal_eval(keyword.value) for keyword in timetable.keywords}
    assert keywords == {"timezone": "UTC", "run_immediately": False}
