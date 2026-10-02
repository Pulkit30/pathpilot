"""Storage for users, saved roadmaps and feedback.

Store is a small interface with two implementations:
  MongoStore     the real one, backed by MongoDB (local or Atlas)
  InMemoryStore  used by tests, so they run without a database

Collections:
  users      {email (unique), name, password_hash, created_at}
  roadmaps   {user_id, career_id, known_skills, hours_per_week, completed_skills, created_at, updated_at}
             one per (user_id, career_id)
  feedback   {user_id|None, query, career_id, rating (+1/-1), rank, model_version, created_at}

The Mongo client is created lazily and reused, which matters on Vercel: a warm serverless
instance keeps the connection instead of reconnecting on every request.
"""

import asyncio
import re
import uuid
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ASCENDING, DESCENDING, AsyncMongoClient, ReturnDocument
from pymongo.errors import DuplicateKeyError


class EmailTakenError(Exception):
    pass


def _now():
    return datetime.now(timezone.utc)


class Store:
    # users
    async def create_user(self, email, name, password_hash): raise NotImplementedError
    async def get_user_by_email(self, email): raise NotImplementedError
    async def get_user_by_id(self, user_id): raise NotImplementedError
    # saved roadmaps
    async def save_roadmap(self, user_id, career_id, known_skills, hours_per_week): raise NotImplementedError
    async def list_roadmaps(self, user_id): raise NotImplementedError
    async def get_roadmap(self, user_id, career_id): raise NotImplementedError
    async def set_skill_done(self, user_id, career_id, skill_id, done): raise NotImplementedError
    async def delete_roadmap(self, user_id, career_id): raise NotImplementedError
    # feedback
    async def add_feedback(self, doc): raise NotImplementedError


def _out(doc):
    """Mongo document -> plain dict with a string 'id' instead of '_id'."""
    if doc is None:
        return None
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


class MongoStore(Store):
    def __init__(self, db):
        self.users = db["users"]
        self.roadmaps = db["roadmaps"]
        self.feedback = db["feedback"]
        self._indexed = False

    async def _ensure_indexes(self):
        if not self._indexed:
            await self.users.create_index("email", unique=True)
            await self.roadmaps.create_index([("user_id", ASCENDING), ("career_id", ASCENDING)], unique=True)
            await self.feedback.create_index("created_at")
            self._indexed = True

    # ---------------------------------------------------------------- users ----

    async def create_user(self, email, name, password_hash):
        await self._ensure_indexes()
        doc = {"email": email, "name": name, "password_hash": password_hash, "created_at": _now()}
        try:
            result = await self.users.insert_one(doc)
        except DuplicateKeyError:
            raise EmailTakenError(email) from None
        doc["_id"] = result.inserted_id
        return _out(doc)

    async def get_user_by_email(self, email):
        return _out(await self.users.find_one({"email": email}))

    async def get_user_by_id(self, user_id):
        try:
            oid = ObjectId(user_id)
        except (InvalidId, TypeError):
            return None
        return _out(await self.users.find_one({"_id": oid}))

    # -------------------------------------------------------------- roadmaps ----

    async def save_roadmap(self, user_id, career_id, known_skills, hours_per_week):
        """Create the saved roadmap, or update its known skills / hours (keeping completed skills)."""
        await self._ensure_indexes()
        now = _now()
        doc = await self.roadmaps.find_one_and_update(
            {"user_id": user_id, "career_id": career_id},
            {"$set": {"known_skills": known_skills, "hours_per_week": hours_per_week, "updated_at": now},
             "$setOnInsert": {"completed_skills": [], "created_at": now}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return _out(doc)

    async def list_roadmaps(self, user_id):
        cursor = self.roadmaps.find({"user_id": user_id}).sort("updated_at", DESCENDING)
        return [_out(d) async for d in cursor]

    async def get_roadmap(self, user_id, career_id):
        return _out(await self.roadmaps.find_one({"user_id": user_id, "career_id": career_id}))

    async def set_skill_done(self, user_id, career_id, skill_id, done):
        op = "$addToSet" if done else "$pull"
        doc = await self.roadmaps.find_one_and_update(
            {"user_id": user_id, "career_id": career_id},
            {op: {"completed_skills": skill_id}, "$set": {"updated_at": _now()}},
            return_document=ReturnDocument.AFTER,
        )
        return _out(doc)

    async def delete_roadmap(self, user_id, career_id):
        result = await self.roadmaps.delete_one({"user_id": user_id, "career_id": career_id})
        return result.deleted_count == 1

    # -------------------------------------------------------------- feedback ----

    async def add_feedback(self, doc):
        await self._ensure_indexes()
        doc = {**doc, "created_at": _now()}
        result = await self.feedback.insert_one(doc)
        doc["_id"] = result.inserted_id
        return _out(doc)


class InMemoryStore(Store):
    def __init__(self):
        self.users = {}
        self.roadmaps = {}   # (user_id, career_id) -> doc
        self.feedback = []

    async def create_user(self, email, name, password_hash):
        if await self.get_user_by_email(email):
            raise EmailTakenError(email)
        user = {"id": uuid.uuid4().hex, "email": email, "name": name,
                "password_hash": password_hash, "created_at": _now()}
        self.users[user["id"]] = user
        return dict(user)

    async def get_user_by_email(self, email):
        return next((dict(u) for u in self.users.values() if u["email"] == email), None)

    async def get_user_by_id(self, user_id):
        user = self.users.get(user_id)
        return dict(user) if user else None

    async def save_roadmap(self, user_id, career_id, known_skills, hours_per_week):
        now = _now()
        doc = self.roadmaps.get((user_id, career_id)) or {
            "id": uuid.uuid4().hex, "user_id": user_id, "career_id": career_id,
            "completed_skills": [], "created_at": now}
        doc.update(known_skills=list(known_skills), hours_per_week=hours_per_week, updated_at=now)
        self.roadmaps[(user_id, career_id)] = doc
        return dict(doc)

    async def list_roadmaps(self, user_id):
        docs = [dict(d) for (uid, _), d in self.roadmaps.items() if uid == user_id]
        return sorted(docs, key=lambda d: d["updated_at"], reverse=True)

    async def get_roadmap(self, user_id, career_id):
        doc = self.roadmaps.get((user_id, career_id))
        return dict(doc) if doc else None

    async def set_skill_done(self, user_id, career_id, skill_id, done):
        doc = self.roadmaps.get((user_id, career_id))
        if doc is None:
            return None
        if done and skill_id not in doc["completed_skills"]:
            doc["completed_skills"].append(skill_id)
        if not done and skill_id in doc["completed_skills"]:
            doc["completed_skills"].remove(skill_id)
        doc["updated_at"] = _now()
        return dict(doc)

    async def delete_roadmap(self, user_id, career_id):
        return self.roadmaps.pop((user_id, career_id), None) is not None

    async def add_feedback(self, doc):
        doc = {**doc, "id": uuid.uuid4().hex, "created_at": _now()}
        self.feedback.append(doc)
        return dict(doc)


_client = None
_store = None
_loop = None  # the event loop the client was created in


def get_mongo_store(settings):
    """Shared MongoStore, or None when no MONGODB_URI is configured.

    Must be called from async code. An async Mongo client belongs to the event loop it was created
    in, so if the server ever runs requests in a new loop we create a fresh client for it.
    """
    global _client, _store, _loop
    if not settings.mongodb_uri:
        return None
    loop = asyncio.get_running_loop()
    if _store is None or _loop is not loop:
        _client = AsyncMongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
        _store = MongoStore(_client[settings.mongodb_db])
        _loop = loop
    return _store


async def close_mongo():
    global _client, _store, _loop
    if _client is not None:
        await _client.close()
    _client = _store = _loop = None


def redact(text):
    """Hide credentials in connection strings: mongodb+srv://user:pass@host -> mongodb+srv://***@host"""
    return re.sub(r"//[^/@\s]+@", "//***@", str(text))


async def database_status(settings):
    """'ok', 'not configured', or 'error: <reason>' (credentials redacted). Used by /api/health."""
    if not settings.mongodb_uri:
        return "not configured"
    try:
        get_mongo_store(settings)
        await _client.admin.command("ping")
        return "ok"
    except Exception as exc:  # report any failure, including connection, auth and DNS problems
        return f"error: {type(exc).__name__}: {redact(exc)[:300]}"
