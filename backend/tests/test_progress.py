"""Saved roadmaps, progress and feedback.  Run:  .venv/bin/python -m pytest backend/tests -q"""

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

from backend.app import db as db_module
from backend.app.config import Settings, get_settings
from backend.app.db import InMemoryStore
from backend.app.deps import get_store_or_none
from backend.app.main import app
from backend.tests.test_api import MONGO_URI, _mongo_available

SECRET = "test-secret-" + "x" * 32


@pytest.fixture
def store():
    return InMemoryStore()


@pytest.fixture
def client(store):
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, jwt_secret=SECRET, mongodb_uri="")
    app.dependency_overrides[get_store_or_none] = lambda: store
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def login(client, email="riya@example.com"):
    r = client.post("/api/auth/register", json={"email": email, "name": "Riya", "password": "supersecret"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


SAVE = {"career_id": "data_analyst", "known_skills": ["python", "sql"], "hours_per_week": 10}


# --------------------------------------------------------- saved roadmaps ----

def test_requires_login(client):
    assert client.get("/api/roadmaps").status_code == 401
    assert client.post("/api/roadmaps", json=SAVE).status_code == 401


def test_save_and_list(client):
    auth = login(client)
    r = client.post("/api/roadmaps", json=SAVE, headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["steps_done"] == 0
    assert body["steps_total"] == len(body["roadmap"]["steps"]) == 9
    assert body["progress"] == round(2 / 11, 3)          # knows 2 of Data Analyst's 11 skills

    listed = client.get("/api/roadmaps", headers=auth).json()
    assert [r["career_id"] for r in listed] == ["data_analyst"]


def test_mark_skills_done_updates_progress(client):
    auth = login(client)
    client.post("/api/roadmaps", json=SAVE, headers=auth)
    r = client.put("/api/roadmaps/data_analyst/skills/excel", json={"done": True}, headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["completed_skills"] == ["excel"]
    assert body["steps_done"] == 1
    assert body["progress"] == round(3 / 11, 3)
    assert body["hours_left"] == body["roadmap"]["total_hours"] - 20   # Excel is ~20 hrs

    # marking twice doesn't double count; undoing works
    client.put("/api/roadmaps/data_analyst/skills/excel", json={"done": True}, headers=auth)
    body = client.put("/api/roadmaps/data_analyst/skills/excel", json={"done": False}, headers=auth).json()
    assert body["completed_skills"] == [] and body["steps_done"] == 0


def test_resaving_keeps_completed_skills(client):
    auth = login(client)
    client.post("/api/roadmaps", json=SAVE, headers=auth)
    client.put("/api/roadmaps/data_analyst/skills/excel", json={"done": True}, headers=auth)
    body = client.post("/api/roadmaps", json={**SAVE, "hours_per_week": 5}, headers=auth).json()
    assert body["hours_per_week"] == 5
    assert body["completed_skills"] == ["excel"]


def test_mark_skill_errors(client):
    auth = login(client)
    assert client.put("/api/roadmaps/data_analyst/skills/excel", json={"done": True}, headers=auth).status_code == 404
    client.post("/api/roadmaps", json=SAVE, headers=auth)
    # python is already known, so it isn't a step
    assert client.put("/api/roadmaps/data_analyst/skills/python", json={"done": True}, headers=auth).status_code == 422
    assert client.put("/api/roadmaps/data_analyst/skills/unity", json={"done": True}, headers=auth).status_code == 422


def test_users_only_see_their_own_roadmaps(client):
    riya = login(client, "riya@example.com")
    aman = login(client, "aman@example.com")
    client.post("/api/roadmaps", json=SAVE, headers=riya)
    assert client.get("/api/roadmaps", headers=aman).json() == []
    assert client.get("/api/roadmaps/data_analyst", headers=aman).status_code == 404
    assert client.delete("/api/roadmaps/data_analyst", headers=aman).status_code == 404


def test_delete(client):
    auth = login(client)
    client.post("/api/roadmaps", json=SAVE, headers=auth)
    assert client.delete("/api/roadmaps/data_analyst", headers=auth).status_code == 204
    assert client.get("/api/roadmaps", headers=auth).json() == []


def test_save_validation(client):
    auth = login(client)
    assert client.post("/api/roadmaps", json={**SAVE, "career_id": "astronaut"}, headers=auth).status_code == 404
    assert client.post("/api/roadmaps", json={**SAVE, "known_skills": ["nope"]}, headers=auth).status_code == 422


# --------------------------------------------------------------- feedback ----

FEEDBACK = {"query": "I love video games", "career_id": "game_developer", "rating": 1, "rank": 1}


def test_feedback_anonymous_and_logged_in(client, store):
    assert client.post("/api/feedback", json=FEEDBACK).status_code == 201
    auth = login(client)
    assert client.post("/api/feedback", json={**FEEDBACK, "rating": -1}, headers=auth).status_code == 201

    anon, mine = store.feedback
    assert anon["user_id"] is None and anon["rating"] == 1
    assert mine["user_id"] is not None and mine["rating"] == -1
    assert mine["model_version"]  # records which trained model made the recommendation


def test_feedback_validation(client):
    assert client.post("/api/feedback", json={**FEEDBACK, "rating": 5}).status_code == 422
    assert client.post("/api/feedback", json={**FEEDBACK, "career_id": "astronaut"}).status_code == 404
    assert client.post("/api/feedback", json={**FEEDBACK, "query": ""}).status_code == 422


# ----------------------------------------------------- real MongoDB check ----

@pytest.mark.skipif(not _mongo_available(), reason="no local MongoDB running")
def test_mongo_progress_round_trip():
    settings = Settings(_env_file=None, mongodb_uri=MONGO_URI, mongodb_db="pathpilot_test", jwt_secret=SECRET)
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as c:
            auth = login(c)
            assert c.post("/api/roadmaps", json=SAVE, headers=auth).status_code == 200
            assert c.post("/api/roadmaps", json=SAVE, headers=auth).status_code == 200  # upsert, no duplicate
            body = c.put("/api/roadmaps/data_analyst/skills/excel", json={"done": True}, headers=auth).json()
            assert body["completed_skills"] == ["excel"]
            assert len(c.get("/api/roadmaps", headers=auth).json()) == 1
            assert c.post("/api/feedback", json=FEEDBACK, headers=auth).status_code == 201
            assert c.delete("/api/roadmaps/data_analyst", headers=auth).status_code == 204
    finally:
        app.dependency_overrides.clear()
        MongoClient(MONGO_URI).drop_database("pathpilot_test")
        db_module._client = db_module._store = None
