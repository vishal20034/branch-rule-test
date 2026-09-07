from app import app


def test_home_ok():
    client = app.test_client()
    res = client.get("/")
    assert res.status_code == 200
    assert b"Operator board" in res.data


def test_add_note_and_list():
    client = app.test_client()
    res = client.post("/notes", data={"author": "qa", "text": "gate passed"}, follow_redirects=True)
    assert res.status_code == 200
    assert b"gate passed" in res.data


def test_checks():
    client = app.test_client()
    res = client.post("/checks", data={"test": "on", "sonar": "on"}, follow_redirects=True)
    assert res.status_code == 200
    assert b"checked" in res.data.lower() or b"pytest passed" in res.data


def test_health_json():
    client = app.test_client()
    res = client.get("/health")
    assert res.status_code == 200
    body = res.get_json()
    assert body["status"] == "ok"


def test_health_ui():
    client = app.test_client()
    res = client.get("/health/ui")
    assert res.status_code == 200
    assert b"test-webapp" in res.data


def test_pipeline_page():
    client = app.test_client()
    res = client.get("/pipeline")
    assert res.status_code == 200
    assert b"pytest" in res.data.lower()
