"""User storage.

UserStore is a small interface with two implementations:
  MongoUserStore     the real one, backed by MongoDB (local or Atlas)
  InMemoryUserStore  used by tests, so they run without a database

The Mongo client is created lazily and reused, which matters on Vercel: a warm serverless
instance keeps the connection instead of reconnecting on every request.
"""

import uuid
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import AsyncMongoClient
from pymongo.errors import DuplicateKeyError


class EmailTakenError(Exception):
    pass


def _now():
    return datetime.now(timezone.utc)


class UserStore:
    async def create_user(self, email, name, password_hash):
        raise NotImplementedError

    async def get_by_email(self, email):
        raise NotImplementedError

    async def get_by_id(self, user_id):
        raise NotImplementedError


class MongoUserStore(UserStore):
    def __init__(self, db):
        self.users = db["users"]
        self._indexed = False

    async def _ensure_indexes(self):
        if not self._indexed:
            await self.users.create_index("email", unique=True)
            self._indexed = True

    @staticmethod
    def _out(doc):
        if doc is None:
            return None
        doc = dict(doc)
        doc["id"] = str(doc.pop("_id"))
        return doc

    async def create_user(self, email, name, password_hash):
        await self._ensure_indexes()
        doc = {"email": email, "name": name, "password_hash": password_hash, "created_at": _now()}
        try:
            result = await self.users.insert_one(doc)
        except DuplicateKeyError:
            raise EmailTakenError(email) from None
        doc["_id"] = result.inserted_id
        return self._out(doc)

    async def get_by_email(self, email):
        return self._out(await self.users.find_one({"email": email}))

    async def get_by_id(self, user_id):
        try:
            oid = ObjectId(user_id)
        except (InvalidId, TypeError):
            return None
        return self._out(await self.users.find_one({"_id": oid}))


class InMemoryUserStore(UserStore):
    def __init__(self):
        self.by_id = {}

    async def create_user(self, email, name, password_hash):
        if await self.get_by_email(email):
            raise EmailTakenError(email)
        user = {"id": uuid.uuid4().hex, "email": email, "name": name,
                "password_hash": password_hash, "created_at": _now()}
        self.by_id[user["id"]] = user
        return dict(user)

    async def get_by_email(self, email):
        return next((dict(u) for u in self.by_id.values() if u["email"] == email), None)

    async def get_by_id(self, user_id):
        user = self.by_id.get(user_id)
        return dict(user) if user else None


_client = None
_store = None


def get_mongo_store(settings):
    """Shared MongoUserStore, or None when no MONGODB_URI is configured."""
    global _client, _store
    if not settings.mongodb_uri:
        return None
    if _store is None:
        _client = AsyncMongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
        _store = MongoUserStore(_client[settings.mongodb_db])
    return _store


async def close_mongo():
    global _client, _store
    if _client is not None:
        await _client.close()
    _client = _store = None
