"""POST /reports - validate input and store one report."""

import base64
import json
import unicodedata
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from wardwatch_common import (
    CATEGORIES,
    MAX_AREA,
    MAX_BODY_BYTES,
    MAX_DESCRIPTION,
    MAX_LANDMARK,
    error,
    get_table,
    logger,
    request_id,
    response,
)


def _clean_text(value):
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("must be text")
    # Drop control characters (category Cc) and collapse runs of whitespace.
    # Format characters such as the zero-width joiner are kept on purpose,
    # because Hindi, Telugu, Malayalam and other Indian scripts need them.
    no_controls = "".join(ch if unicodedata.category(ch) != "Cc" else " " for ch in value)
    return " ".join(no_controls.split())


def _coordinate(value, low, high):
    if isinstance(value, bool):
        raise ValueError("must be a number")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("must be a number")
    if not number.is_finite() or number < low or number > high:
        raise ValueError(f"must be between {low} and {high}")
    return number.quantize(Decimal("0.000001"))


def validate(payload):
    """Return (clean_item_fields, errors)."""
    errors = {}
    clean = {}

    if not isinstance(payload, dict):
        return None, {"body": "must be a JSON object"}

    category = payload.get("category")
    if category not in CATEGORIES:
        errors["category"] = f"must be one of: {', '.join(CATEGORIES)}"
    else:
        clean["category"] = category

    for field, limit, required in (
        ("description", MAX_DESCRIPTION, True),
        ("area", MAX_AREA, True),
        ("landmark", MAX_LANDMARK, False),
    ):
        try:
            text = _clean_text(payload.get(field))
        except ValueError as exc:
            errors[field] = str(exc)
            continue
        if required and not text:
            errors[field] = "is required"
        elif len(text) > limit:
            errors[field] = f"must be at most {limit} characters"
        elif text:
            clean[field] = text

    lat, lng = payload.get("lat"), payload.get("lng")
    if (lat is None) != (lng is None):
        errors["location"] = "send both lat and lng, or neither"
    elif lat is not None:
        try:
            clean["lat"] = _coordinate(lat, -90, 90)
        except ValueError as exc:
            errors["lat"] = str(exc)
        try:
            clean["lng"] = _coordinate(lng, -180, 180)
        except ValueError as exc:
            errors["lng"] = str(exc)

    return clean, errors


def handler(event, context):
    rid = request_id(event, context)
    raw = (event or {}).get("body") or ""
    if (event or {}).get("isBase64Encoded"):
        try:
            raw = base64.b64decode(raw).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return error(400, "Body is not valid text")

    if len(raw.encode("utf-8")) > MAX_BODY_BYTES:
        logger.warning("report_rejected", extra={"request_id": rid, "reason": "body_too_large"})
        return error(413, f"Body must be at most {MAX_BODY_BYTES} bytes")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("report_rejected", extra={"request_id": rid, "reason": "bad_json"})
        return error(400, "Body must be valid JSON")

    clean, errors = validate(payload)
    if errors:
        logger.warning(
            "report_rejected",
            extra={"request_id": rid, "reason": "validation", "fields": sorted(errors)},
        )
        return error(400, "Validation failed", errors)

    item = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "open",
        **clean,
    }
    get_table().put_item(Item=item, ConditionExpression="attribute_not_exists(id)")

    logger.info(
        "report_created",
        extra={"request_id": rid, "report_id": item["id"], "category": item["category"]},
    )
    return response(201, item)
