import json

import create_report


def post(body):
    raw = body if isinstance(body, str) else json.dumps(body)
    return create_report.handler({"body": raw, "requestContext": {"requestId": "t-1"}}, None)


VALID = {
    "category": "flooded_drain",
    "description": "Drain near the bus stop is overflowing onto the road.",
    "area": "Gandhi Nagar 2nd Cross",
    "landmark": "Opposite Ganesh Temple",
    "lat": 17.385,
    "lng": 78.4867,
}


def test_valid_report_is_saved(table):
    res = post(VALID)
    assert res["statusCode"] == 201
    body = json.loads(res["body"])
    assert body["category"] == "flooded_drain"
    assert body["status"] == "open"
    assert len(body["id"]) == 36
    assert body["created_at"].endswith("+00:00")
    stored = table.get_item(Key={"id": body["id"]})["Item"]
    assert stored["area"] == "Gandhi Nagar 2nd Cross"
    assert float(stored["lat"]) == 17.385


def test_cors_headers_present(table):
    res = post(VALID)
    assert res["headers"]["Access-Control-Allow-Origin"] == "*"


def test_location_is_optional(table):
    body = {k: v for k, v in VALID.items() if k not in ("lat", "lng", "landmark")}
    assert post(body)["statusCode"] == 201


def test_unknown_category_rejected(table):
    res = post({**VALID, "category": "aliens"})
    assert res["statusCode"] == 400
    assert "category" in json.loads(res["body"])["details"]


def test_description_too_long_rejected(table):
    res = post({**VALID, "description": "x" * 501})
    assert res["statusCode"] == 400
    assert "description" in json.loads(res["body"])["details"]


def test_description_exactly_500_ok(table):
    assert post({**VALID, "description": "x" * 500})["statusCode"] == 201


def test_missing_area_rejected(table):
    body = dict(VALID)
    del body["area"]
    res = post(body)
    assert res["statusCode"] == 400
    assert "area" in json.loads(res["body"])["details"]


def test_lat_without_lng_rejected(table):
    body = dict(VALID)
    del body["lng"]
    res = post(body)
    assert res["statusCode"] == 400
    assert "location" in json.loads(res["body"])["details"]


def test_lat_out_of_range_rejected(table):
    res = post({**VALID, "lat": 123})
    assert res["statusCode"] == 400


def test_bad_json_rejected(table):
    assert post("{not json")["statusCode"] == 400


def test_non_object_rejected(table):
    assert post([1, 2, 3])["statusCode"] == 400


def test_huge_body_rejected(table):
    assert post("x" * 5000)["statusCode"] == 413


def test_nothing_saved_on_error(table):
    post({**VALID, "category": "nope"})
    assert table.scan()["Count"] == 0


def test_indian_script_text_kept_intact(table):
    # Hindi text with a zero-width joiner (U+200D) must survive cleaning.
    text = "\u0928\u093e\u0932\u0940 \u092c\u0902\u0926 \u0939\u0948 \u0915\u094d\u200d\u0937"
    res = post({**VALID, "description": text})
    assert res["statusCode"] == 201
    assert json.loads(res["body"])["description"] == text


def test_control_characters_removed(table):
    res = post({**VALID, "description": "Drain\x00 blocked\n\n near   gate\x07"})
    assert json.loads(res["body"])["description"] == "Drain blocked near gate"


def test_boolean_coordinates_rejected(table):
    assert post({**VALID, "lat": True, "lng": False})["statusCode"] == 400
