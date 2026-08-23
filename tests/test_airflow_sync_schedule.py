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

    dag_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "DAG"
    ]
    assert len(dag_calls) == 1
    dag_keywords = {keyword.arg: keyword.value for keyword in dag_calls[0].keywords}
    start_date = dag_keywords["start_date"]
    assert isinstance(start_date, ast.Call)
    assert isinstance(start_date.func, ast.Name)
    assert start_date.func.id == "datetime"
    assert [ast.literal_eval(arg) for arg in start_date.args] == [2026, 8, 24]
