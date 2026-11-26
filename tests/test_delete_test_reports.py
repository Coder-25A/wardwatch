import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import delete_test_reports  # noqa: E402


def test_only_burst_test_reports_are_deleted(table):
    table.put_item(Item={"id": "real-1", "description": "Drain blocked near temple"})
    table.put_item(Item={"id": "real-2", "description": "Pothole on Station Road"})
    for i in range(3):
        table.put_item(Item={"id": f"test-{i}", "description": f"Burst test report {i} (safe to ignore)"})

    found = delete_test_reports.find_test_items(table)
    assert sorted(i["id"] for i in found) == ["test-0", "test-1", "test-2"]

    assert delete_test_reports.delete_items(table, found) == 3
    remaining = sorted(i["id"] for i in table.scan()["Items"])
    assert remaining == ["real-1", "real-2"]


def test_main_with_explicit_table(table, monkeypatch):
    table.put_item(Item={"id": "test-x", "description": "Burst test report 9 (safe to ignore)"})
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    # Use the default (fake) credentials from conftest instead of a named profile.
    monkeypatch.setattr(delete_test_reports.boto3, "Session",
                        lambda profile_name=None, region_name=None: delete_test_reports.boto3.session.Session(region_name=region_name))
    rc = delete_test_reports.main(["--table", table.name, "--yes"])
    assert rc == 0
    assert table.scan()["Count"] == 0
