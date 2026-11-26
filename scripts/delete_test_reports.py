"""Delete the test reports created by `burst_test.py --post-sample`.

Only items whose description starts with "Burst test report" are touched.
Real reports are never deleted. It shows what it found and asks before deleting.

Usage (PowerShell, venv active):
    python scripts\\delete_test_reports.py --profile wardwatch --region ap-southeast-2
    python scripts\\delete_test_reports.py --profile wardwatch --region ap-southeast-2 --yes
"""

import argparse
import sys

import boto3

TEST_PREFIX = "Burst test report"


def find_table_name(session, stack_name):
    """Look up the real DynamoDB table name from the CloudFormation stack."""
    cfn = session.client("cloudformation")
    res = cfn.describe_stack_resource(StackName=stack_name, LogicalResourceId="ReportsTable")
    return res["StackResourceDetail"]["PhysicalResourceId"]


def find_test_items(table):
    items, kwargs = [], {}
    while True:
        page = table.scan(**kwargs)
        items += [i for i in page.get("Items", [])
                  if str(i.get("description", "")).startswith(TEST_PREFIX)]
        if "LastEvaluatedKey" not in page:
            return items
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def delete_items(table, items):
    with table.batch_writer() as batch:
        for item in items:
            batch.delete_item(Key={"id": item["id"]})
    return len(items)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Delete burst-test reports from the WardWatch table.")
    parser.add_argument("--profile", default="wardwatch")
    parser.add_argument("--region", default="ap-southeast-2")
    parser.add_argument("--stack", default="wardwatch", help="CloudFormation stack name")
    parser.add_argument("--table", help="table name (looked up from the stack if not given)")
    parser.add_argument("--yes", action="store_true", help="delete without asking")
    args = parser.parse_args(argv)

    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    table_name = args.table or find_table_name(session, args.stack)
    table = session.resource("dynamodb").Table(table_name)

    items = find_test_items(table)
    print(f"Table {table_name}: found {len(items)} test report(s) starting with '{TEST_PREFIX}'.")
    if not items:
        return 0
    if not args.yes and input("Delete them? Type y and press Enter: ").strip().lower() != "y":
        print("Nothing deleted.")
        return 0
    print(f"Deleted {delete_items(table, items)} test report(s). Real reports were not touched.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
