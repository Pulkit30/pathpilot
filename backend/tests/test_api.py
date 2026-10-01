"""API tests.  Run:  .venv/bin/python -m pytest backend/tests -q

Most tests swap MongoDB for an in-memory store, so no database is needed.
test_mongo_round_trip uses a real MongoDB (database 'pathpilot_test') and is skipped if none is reachable.
"""

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from backend.app import db as db_module
from backend.app.config import Settings, get_settings
from backend.app.db import InMemoryUserStore
from backend.app.deps import get_user_store
from backend.app.main import app

TEST_SETTINGS = Settings(_env_file=None, jwt_secret="test-secret-" + "x" * 32, mongodb_uri="")


@pytest.fixture
def client():
    store = InMemoryUserStore()
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS
    app.dependency_overrides[get_user_store] = lambda: store
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ------------------------------------------------------------------ meta ----

def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["model"]["careers"] == 15


# ------------------------------------------------------------- recommend ----

def test_recommend_returns_explained_careers(client):
    r = client.post("/api/recommend", json={"query": "I know C# and I love video games"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    top = body["recommendations"][0]
    assert top["career_id"] == "game_developer"
    assert "csharp" in body["parsed"]["known_skills"]
    assert any("C#" in reason for reason in top["reasons"])


def test_recommend_hides_near_zero_matches(client):
    body = client.post("/api/recommend", json={"query": "I know C# and I love video games"}).json()
    assert all(r["match"] >= 5.0 for r in body["recommendations"][1:])
    everything = client.post("/api/recommend", json={"query": "I know C# and I love video games",
                                                      "min_match": 0}).json()
    assert len(everything["recommendations"]) == 3


def test_recommend_vague_query_asks_for_more(client):
    body = client.post("/api/recommend", json={"query": "hello there"}).json()
    assert body["status"] == "need_more_info"
    assert body["recommendations"] == []


def test_recommend_skill_chips_override(client):
    body = client.post("/api/recommend", json={"query": "I like data", "known_skills": ["sql", "excel"]}).json()
    assert body["parsed"]["known_skills"] == ["sql", "excel"]


def test_recommend_validation(client):
    assert client.post("/api/recommend", json={"query": ""}).status_code == 422
    assert client.post("/api/recommend", json={"query": "x" * 1001}).status_code == 422
    assert client.post("/api/recommend", json={"query": "hi", "known_skills": ["not_a_skill"]}).status_code == 422


# --------------------------------------------------------------- roadmap ----

def test_roadmap_skips_known_and_implied_skills(client):
    r = client.post("/api/roadmap", json={"career_id": "data_scientist", "known_skills": ["pandas"],
                                          "hours_per_week": 5})
    assert r.status_code == 200
    body = r.json()
    todo = [s["skill_id"] for s in body["steps"]]
    assert "pandas" not in todo and "python" not in todo
    assert body["hours_per_week"] == 5
    assert body["steps"][0]["resources"], "every step should carry learning resources"


def test_roadmap_errors(client):
    assert client.post("/api/roadmap", json={"career_id": "astronaut"}).status_code == 404
    assert client.post("/api/roadmap", json={"career_id": "qa_engineer", "hours_per_week": 0}).status_code == 422


# --------------------------------------------------------------- catalog ----

def test_careers_list_and_detail(client):
    careers = client.get("/api/careers").json()
    assert len(careers) == 15
    detail = client.get("/api/careers/devops_engineer").json()
    assert set(detail["stages"]) == {"beginner", "intermediate", "advanced"}
    assert detail["stages"]["beginner"][0]["name"]
    assert client.get("/api/careers/astronaut").status_code == 404


def test_skills_list(client):
    skills = client.get("/api/skills").json()
    assert len(skills) == 135
    assert {"id", "name", "category"} <= set(skills[0])


# ------------------------------------------------------------------ auth ----

def _register(client, email="riya@example.com", password="supersecret"):
    return client.post("/api/auth/register", json={"email": email, "name": "Riya", "password": password})


def test_register_login_me(client):
    r = _register(client)
    assert r.status_code == 201
    assert "password" not in str(r.json()["user"])

    r = client.post("/api/auth/login", json={"email": "RIYA@example.com", "password": "supersecret"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "riya@example.com"


def test_auth_failures(client):
    _register(client)
    assert _register(client).status_code == 409                                    # duplicate email
    assert _register(client, email="a@b.com", password="short").status_code == 422  # weak password
    bad = client.post("/api/auth/login", json={"email": "riya@example.com", "password": "wrong-pass"})
    assert bad.status_code == 401
    assert client.get("/api/auth/me").status_code == 401                            # no token
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_accounts_unavailable_without_database():
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, mongodb_uri="", jwt_secret="")
    try:
        with TestClient(app) as c:
            assert _register(c).status_code == 503
            assert c.post("/api/recommend", json={"query": "I love games"}).status_code == 200  # ML still works
    finally:
        app.dependency_overrides.clear()


# ----------------------------------------------------- real MongoDB check ----

MONGO_URI = "mongodb://localhost:27017"


def _mongo_available():
    try:
        MongoClient(MONGO_URI, serverSelectionTimeoutMS=1000).admin.command("ping")
        return True
    except PyMongoError:
        return False


@pytest.mark.skipif(not _mongo_available(), reason="no local MongoDB running")
def test_mongo_round_trip():
    settings = Settings(_env_file=None, mongodb_uri=MONGO_URI, mongodb_db="pathpilot_test",
                        jwt_secret="test-secret-" + "x" * 32)
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as c:
            assert _register(c).status_code == 201
            assert _register(c).status_code == 409  # unique index on email
            token = c.post("/api/auth/login", json={"email": "riya@example.com",
                                                    "password": "supersecret"}).json()["access_token"]
            assert c.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    finally:
        app.dependency_overrides.clear()
        MongoClient(MONGO_URI).drop_database("pathpilot_test")
        db_module._client = db_module._store = None
