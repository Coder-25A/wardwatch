import json

import list_reports


def get(params=None):
    return list_reports.handler({"queryStringParameters": params}, None)


def seed(table, n):
    for i in range(n):
        table.put_item(
            Item={
                "id": f"id-{i:03d}",
                "created_at": f"2026-07-01T10:{i:02d}:00+00:00",
                "category": "pothole",
                "description": f"Pothole {i}",
                "area": "Main Road",
                "status": "open",
            }
        )


def test_empty_table(table):
    res = get()
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert body == {"items": [], "count": 0}


def test_returns_items_newest_first(table):
    seed(table, 3)
    body = json.loads(get()["body"])
    assert body["count"] == 3
    times = [i["created_at"] for i in body["items"]]
    assert times == sorted(times, reverse=True)


def test_pagination_walks_every_item(table):
    seed(table, 7)
    seen, token, pages = set(), None, 0
    while True:
        params = {"limit": "3"}
        if token:
            params["next"] = token
        body = json.loads(get(params)["body"])
        seen.update(i["id"] for i in body["items"])
        pages += 1
        token = body.get("next")
        if not token:
            break
    assert len(seen) == 7
    assert pages >= 3


def test_bad_limit_rejected(table):
    assert get({"limit": "abc"})["statusCode"] == 400
    assert get({"limit": "0"})["statusCode"] == 400
    assert get({"limit": "1000"})["statusCode"] == 400


def test_bad_token_rejected(table):
    assert get({"next": "!!!notbase64"})["statusCode"] == 400


def test_token_with_wrong_shape_rejected(table):
    forged = list_reports.encode_token({"id": "x", "extra": "y"})
    assert get({"next": forged})["statusCode"] == 400


def test_token_round_trip():
    key = {"id": "abc-123"}
    assert list_reports.decode_token(list_reports.encode_token(key)) == key


def test_cors_headers_present(table):
    assert get()["headers"]["Access-Control-Allow-Origin"] == "*"
