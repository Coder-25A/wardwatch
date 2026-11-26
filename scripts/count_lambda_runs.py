"""Count how many times a WardWatch Lambda ran during one burst test.

It reads the start time and duration saved by burst_test.py --save, then asks
CloudWatch (AWS's metrics service) for the Lambda "Invocations" metric in that
window. Wait about 2 minutes after the burst before running this; metrics
arrive a little late.

Usage (PowerShell, venv active):
    python scripts\\count_lambda_runs.py evidence\\burst-before.json
    python scripts\\count_lambda_runs.py evidence\\post-spam-before.json --function CreateReportFunction
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone

import boto3


def burst_window(summary, slack_minutes=2):
    """Return (start, end) datetimes covering the burst, on minute boundaries."""
    start = datetime.fromisoformat(summary["start_utc"]).astimezone(timezone.utc)
    start = start.replace(second=0, microsecond=0)
    end = start + timedelta(seconds=summary.get("wall_seconds", 0)) + timedelta(minutes=slack_minutes)
    return start, end


def main(argv=None):
    parser = argparse.ArgumentParser(description="Count Lambda runs during a saved burst test.")
    parser.add_argument("burst_file", help="JSON file written by burst_test.py --save")
    parser.add_argument("--function", default="ListReportsFunction",
                        help="logical name in template.yaml (ListReportsFunction or CreateReportFunction)")
    parser.add_argument("--profile", default="wardwatch")
    parser.add_argument("--region", default="ap-southeast-2")
    parser.add_argument("--stack", default="wardwatch")
    args = parser.parse_args(argv)

    with open(args.burst_file, encoding="utf-8") as fh:
        summary = json.load(fh)
    if "start_utc" not in summary:
        parser.error("this file has no start_utc; re-run the burst with the current burst_test.py")
    start, end = burst_window(summary)

    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    name = session.client("cloudformation").describe_stack_resource(
        StackName=args.stack, LogicalResourceId=args.function
    )["StackResourceDetail"]["PhysicalResourceId"]
    stats = session.client("cloudwatch").get_metric_statistics(
        Namespace="AWS/Lambda", MetricName="Invocations",
        Dimensions=[{"Name": "FunctionName", "Value": name}],
        StartTime=start, EndTime=end, Period=60, Statistics=["Sum"],
    )
    runs = int(sum(p["Sum"] for p in stats["Datapoints"]))
    print(f"{args.function} ({name})")
    print(f"Window (UTC): {start:%H:%M} to {end:%H:%M}")
    print(f"Lambda runs in that window: {runs}   (burst '{summary.get('label', '')}' sent {summary['total']} requests)")
    print("If this looks too high, another test ran in the same minutes. Wait 3 minutes between bursts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
