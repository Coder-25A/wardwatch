"""GET /reports - return a page of reports.

Reads reports from DynamoDB with a Scan, page by page, using an
optional `limit` and a `next` pagination token.
"""

import base64
import binascii
import json

from wardwatch_common import error, get_table, logger, request_id, response

DEFAULT_LIMIT = 50
MAX_LIMIT = 100


def encode_token(last_key):
    raw = json.dumps(last_key, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_token(token):
    """Turn a 'next' token back into a DynamoDB ExclusiveStartKey."""
    try:
        padded = token + "=" * (-len(token) % 4)
        key = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    except (ValueError, binascii.Error, UnicodeError):
        raise ValueError("bad token")
    # Only our own key shape is accepted: {"id": "<string>"}
    if not isinstance(key, dict) or set(key) != {"id"} or not isinstance(key["id"], str):
        raise ValueError("bad token")
    return key


def handler(event, context):
    rid = request_id(event, context)
    params = (event or {}).get("queryStringParameters") or {}

    limit_raw = params.get("limit", str(DEFAULT_LIMIT))
    try:
        limit = int(limit_raw)
    except (TypeError, ValueError):
        return error(400, "limit must be a whole number")
    if not 1 <= limit <= MAX_LIMIT:
        return error(400, f"limit must be between 1 and {MAX_LIMIT}")

    scan_args = {"Limit": limit}
    token = params.get("next")
    if token:
        try:
            scan_args["ExclusiveStartKey"] = decode_token(token)
        except ValueError:
            return error(400, "next token is not valid")

    result = get_table().scan(**scan_args)
    # A Scan returns items in no useful order, so each page is sorted newest
    # first. (Order across pages is not guaranteed; fine for one small ward.)
    items = sorted(result.get("Items", []), key=lambda i: i.get("created_at", ""), reverse=True)

    body = {"items": items, "count": len(items)}
    if "LastEvaluatedKey" in result:
        body["next"] = encode_token(result["LastEvaluatedKey"])

    logger.info(
        "reports_listed",
        extra={"request_id": rid, "count": len(items), "has_more": "next" in body},
    )
    return response(200, body)
