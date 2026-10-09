from app import config

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32

FORM = {
    "citizen_name": "Rahul Patil",
    "category": "pothole",
    "latitude": "18.6298",
    "longitude": "73.7997",
    "description": "Large pothole near market road",
}


def test_root(client):
    assert client.get("/").json()["status"] == "running"


def test_create_pothole_is_routed(client):
    r = client.post("/complaints", data=FORM)
    assert r.status_code == 201
    body = r.json()
    assert body["department"] == "Road Maintenance Department"
    assert body["priority"] == "High"
    assert body["status"] == "Submitted"
    assert 1 <= body["ward_number"] <= 20
    assert len(body["history"]) == 1
    assert body["image_url"] is None


def test_invalid_category_rejected(client):
    r = client.post("/complaints", data={**FORM, "category": "alien_landing"})
    assert r.status_code == 422


def test_invalid_coordinates_rejected(client):
    r = client.post("/complaints", data={**FORM, "latitude": "123"})
    assert r.status_code == 422


def test_photo_upload_and_serving(client):
    r = client.post("/complaints", data=FORM, files={"image": ("p.png", PNG, "image/png")})
    assert r.status_code == 201
    url = r.json()["image_url"]
    assert url.startswith("/uploads/") and url.endswith(".png")
    assert client.get(url).content == PNG


def test_fake_image_rejected(client):
    r = client.post("/complaints", data=FORM, files={"image": ("x.png", b"not an image", "image/png")})
    assert r.status_code == 400


def test_status_update_records_history(client):
    cid = client.post("/complaints", data=FORM).json()["id"]
    r = client.patch(f"/complaints/{cid}/status", json={"status": "In Progress", "note": "Crew sent"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "In Progress"
    assert [h["status"] for h in body["history"]] == ["Submitted", "In Progress"]
    assert body["history"][1]["note"] == "Crew sent"


def test_same_status_rejected_and_unknown_404(client):
    cid = client.post("/complaints", data=FORM).json()["id"]
    assert client.patch(f"/complaints/{cid}/status", json={"status": "Submitted"}).status_code == 400
    assert client.patch("/complaints/999999/status", json={"status": "Resolved"}).status_code == 404
    assert client.get("/complaints/999999").status_code == 404


def test_list_filter_and_stats(client):
    client.post("/complaints", data={**FORM, "category": "garbage"})
    cid = client.post("/complaints", data=FORM).json()["id"]
    client.patch(f"/complaints/{cid}/status", json={"status": "Resolved"})

    stats = client.get("/stats").json()
    assert stats["total"] >= 2
    assert stats["resolved"] >= 1
    assert stats["high_priority"] >= 1

    only_garbage = client.get("/complaints", params={"category": "garbage"}).json()
    assert only_garbage and all(c["category"] == "garbage" for c in only_garbage)


def test_admin_key_protects_dashboard_api(client, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_KEY", "secret123")
    assert client.get("/complaints").status_code == 401
    assert client.get("/stats").status_code == 401
    assert client.get("/stats", headers={"X-Admin-Key": "wrong"}).status_code == 401
    assert client.get("/stats", headers={"X-Admin-Key": "secret123"}).status_code == 200
    # Citizens can still submit without a key.
    assert client.post("/complaints", data=FORM).status_code == 201


def test_dashboard_page_served(client):
    r = client.get("/dashboard")
    assert r.status_code == 200 and "My Ward" in r.text


# ---- automatic detection (YOLO is faked; no model needed) ----
from app import main as app_main
from app.detector import Detection, DetectorUnavailable
from app.enums import Category

NO_CATEGORY = {k: v for k, v in FORM.items() if k != "category"}
IMG = {"image": ("p.png", PNG, "image/png")}


def test_no_category_and_no_photo_rejected(client):
    assert client.post("/complaints", data=NO_CATEGORY).status_code == 422


def test_ai_detects_category_from_photo(client, monkeypatch):
    monkeypatch.setattr(app_main, "detect_category", lambda b: Detection(Category.GARBAGE, 0.87))
    r = client.post("/complaints", data=NO_CATEGORY, files=IMG)
    assert r.status_code == 201
    body = r.json()
    assert body["category"] == "garbage"
    assert body["category_source"] == "ai"
    assert body["ai_confidence"] == 0.87
    assert body["department"] == "Solid Waste Management Department"


def test_ai_finds_nothing(client, monkeypatch):
    monkeypatch.setattr(app_main, "detect_category", lambda b: None)
    assert client.post("/complaints", data=NO_CATEGORY, files=IMG).status_code == 422


def test_ai_unavailable(client, monkeypatch):
    def boom(b):
        raise DetectorUnavailable("model missing")
    monkeypatch.setattr(app_main, "detect_category", boom)
    assert client.post("/complaints", data=NO_CATEGORY, files=IMG).status_code == 422


def test_manual_category_skips_ai(client, monkeypatch):
    def boom(b):
        raise AssertionError("detector must not run when category is given")
    monkeypatch.setattr(app_main, "detect_category", boom)
    r = client.post("/complaints", data=FORM, files=IMG)
    assert r.status_code == 201 and r.json()["category_source"] == "citizen"
