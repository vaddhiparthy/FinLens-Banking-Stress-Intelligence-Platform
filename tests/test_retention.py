from finlens.retention import rotate_partitions


def _make_partition(base, source, date):
    part = base / f"source={source}" / f"ingestion_date={date}"
    part.mkdir(parents=True, exist_ok=True)
    (part / "artifact.json").write_text("{}", encoding="utf-8")
    return part


def test_rotation_keeps_only_newest_version_per_source(tmp_path):
    _make_partition(tmp_path, "fdic", "2026-04-25")
    _make_partition(tmp_path, "fdic", "2026-04-27")
    newest = _make_partition(tmp_path, "fdic", "2026-06-07")
    _make_partition(tmp_path, "fred", "2026-04-27")
    fred_newest = _make_partition(tmp_path, "fred", "2026-06-07")

    results = rotate_partitions(tmp_path, keep=1)

    by_source = {r.source: r for r in results}
    assert by_source["fdic"].kept == ["2026-06-07"]
    assert sorted(by_source["fdic"].removed) == ["2026-04-25", "2026-04-27"]
    assert newest.exists() and fred_newest.exists()
    assert not (tmp_path / "source=fdic" / "ingestion_date=2026-04-25").exists()
    assert not (tmp_path / "source=fdic" / "ingestion_date=2026-04-27").exists()
    # exactly one partition remains per source
    assert len(list((tmp_path / "source=fdic").glob("ingestion_date=*"))) == 1
    assert len(list((tmp_path / "source=fred").glob("ingestion_date=*"))) == 1


def test_rotation_dry_run_deletes_nothing(tmp_path):
    _make_partition(tmp_path, "qbp", "2026-04-27")
    _make_partition(tmp_path, "qbp", "2026-06-07")

    results = rotate_partitions(tmp_path, keep=1, dry_run=True)

    assert results[0].removed == ["2026-04-27"]
    assert len(list((tmp_path / "source=qbp").glob("ingestion_date=*"))) == 2  # nothing deleted


def test_rotation_keep_two(tmp_path):
    for d in ("2026-04-25", "2026-04-27", "2026-06-07"):
        _make_partition(tmp_path, "nic", d)

    results = rotate_partitions(tmp_path, keep=2)

    assert results[0].kept == ["2026-06-07", "2026-04-27"]
    assert results[0].removed == ["2026-04-25"]
