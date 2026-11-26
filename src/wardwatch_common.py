"""Small shared helpers used by both Lambda handlers."""

import json
import logging
import os
from decimal import Decimal

import boto3

logger = logging.getLogger("wardwatch")
logger.setLevel(logging.INFO)

# The categories a resident can choose from. Anything else is rejected.
CATEGORIES = ("flooded_drain", "pothole", "garbage", "streetlight")

MAX_DESCRIPTION = 500
MAX_AREA = 100
MAX_LANDMARK = 100
MAX_BODY_BYTES = 4096

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}

_table = None


def get_table():
    """Return the DynamoDB table, created once per Lambda container."""
    global _table
    if _table is None:
        _table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
    return _table


def reset_table_cache():
    """Used by tests so each test gets a fresh table object."""
    global _table
    _table = None


def _json_default(value):
    if isinstance(value, Decimal):
        # Whole numbers come back as int, everything else as float.
        return int(value) if value == value.to_integral_value() else float(value)
    raise TypeError(f"Cannot serialise {type(value).__name__}")


def response(status_code, body):
    """Build an API Gateway proxy response with CORS headers."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", **CORS_HEADERS},
        "body": json.dumps(body, default=_json_default),
    }


def error(status_code, message, details=None):
    body = {"error": message}
    if details:
        body["details"] = details
    return response(status_code, body)


def request_id(event, context):
    """Pick a request id for log lines (API Gateway id if present)."""
    rc = (event or {}).get("requestContext") or {}
    return rc.get("requestId") or getattr(context, "aws_request_id", "local")
