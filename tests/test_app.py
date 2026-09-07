from app import app


def test_home_ok():
    client = app.test_client()
    res = client.get("/")
    assert res.status_code == 200
    assert b"pipeline" in res.data.lower()


def test_pipeline_page():
    client = app.test_client()
    res = client.get("/pipeline")
    assert res.status_code == 200
    assert b"pytest" in res.data.lower()


def test_health():
    client = app.test_client()
    res = client.get("/health")
    assert res.status_code == 200
    body = res.get_json()
    assert body["status"] == "ok"
