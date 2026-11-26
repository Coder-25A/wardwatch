import os
import sys

import boto3
import pytest
from moto import mock_aws

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

# Fake settings so nothing ever talks to real AWS.
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_SESSION_TOKEN"] = "testing"
os.environ["AWS_DEFAULT_REGION"] = "ap-southeast-2"
os.environ["TABLE_NAME"] = "wardwatch-test-reports"
os.environ.pop("AWS_PROFILE", None)

import wardwatch_common  # noqa: E402


@pytest.fixture
def table():
    """A fresh fake DynamoDB table for every test."""
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="ap-southeast-2")
        tbl = ddb.create_table(
            TableName=os.environ["TABLE_NAME"],
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        wardwatch_common.reset_table_cache()
        yield tbl
        wardwatch_common.reset_table_cache()
