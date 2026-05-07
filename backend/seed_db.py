"""
Ember Chat — Database Seed Script

Creates collections, indexes, and sample data (users + conversations + messages
+ friendships + friend requests) for local development.

USAGE:
    cd backend
    source venv/bin/activate            # (or venv\\Scripts\\activate on Windows)
    pip install -r requirements.txt     # (one-time)
    python seed_db.py                   # populate with sample data
    python seed_db.py --reset           # drop everything first, then populate

ENVIRONMENT (read from backend/.env):
    MONGO_URL   default: mongodb://localhost:27017
    DB_NAME     default: chat_app_db
"""
from dotenv import load_dotenv
load_dotenv()

import os
import sys
import uuid
import asyncio
import bcrypt
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "chat_app_db")


def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def now_iso(offset_minutes: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=offset_minutes)).isoformat()


SAMPLE_USERS = [
    {"username": "admin",   "email": "admin@example.com",  "name": "Admin",          "password": "admin123",     "bio": "Keeper of the threads."},
    {"username": "alice",   "email": "alice@test.com",     "name": "Alice Lovelace", "password": "password123",  "bio": "Counting in binary."},
    {"username": "bob",     "email": "bob@test.com",       "name": "Bob Builder",    "password": "password123",  "bio": "Yes, we can."},
    {"username": "carol",   "email": "carol@test.com",     "name": "Carol Danvers",  "password": "password123",  "bio": "Higher, further, faster."},
    {"username": "diego",   "email": "diego@test.com",     "name": "Diego Rivera",   "password": "password123",  "bio": "Painter of walls."},
]


async def ensure_indexes(db):
    print("• Creating indexes…")
    await db.users.create_index("email", unique=True)
    await db.users.create_index("username", unique=True)
    await db.users.create_index("id", unique=True)

    await db.conversations.create_index("participants")
    await db.conversations.create_index("id", unique=True)

    await db.messages.create_index([("conversation_id", 1), ("created_at", 1)])
    await db.messages.create_index("id", unique=True)

    await db.friendships.create_index("users")
    await db.friend_requests.create_index([("from_user_id", 1), ("to_user_id", 1)])
    await db.friend_requests.create_index("to_user_id")
    print("  ✓ indexes ready")


async def seed_users(db):
    print("• Seeding users…")
    user_ids = {}
    for u in SAMPLE_USERS:
        existing = await db.users.find_one({"email": u["email"]})
        if existing:
            user_ids[u["username"]] = existing["id"]
            continue
        uid = str(uuid.uuid4())
        await db.users.insert_one({
            "id": uid,
            "email": u["email"],
            "username": u["username"],
            "name": u["name"],
            "password_hash": hash_password(u["password"]),
            "avatar": None,
            "bio": u["bio"],
            "online": False,
            "last_seen": now_iso(),
            "created_at": now_iso(),
        })
        user_ids[u["username"]] = uid
        print(f"  ✓ {u['username']:<8} {u['email']}")
    return user_ids


async def seed_friendships(db, ids):
    print("• Seeding friendships…")
    pairs = [("alice", "bob"), ("alice", "carol")]
    for a, b in pairs:
        users = sorted([ids[a], ids[b]])
        if await db.friendships.find_one({"users": users}):
            continue
        await db.friendships.insert_one({
            "id": str(uuid.uuid4()),
            "users": users,
            "created_at": now_iso(),
        })
        print(f"  ✓ {a} ↔ {b}")


async def seed_friend_requests(db, ids):
    print("• Seeding pending friend requests…")
    pendings = [("diego", "alice"), ("diego", "bob")]
    for from_u, to_u in pendings:
        if await db.friend_requests.find_one({
            "from_user_id": ids[from_u], "to_user_id": ids[to_u], "status": "pending"
        }):
            continue
        await db.friend_requests.insert_one({
            "id": str(uuid.uuid4()),
            "from_user_id": ids[from_u],
            "to_user_id": ids[to_u],
            "status": "pending",
            "created_at": now_iso(),
        })
        print(f"  ✓ {from_u} → {to_u}")


async def seed_conversations(db, ids):
    print("• Seeding conversations + messages…")

    # 1-on-1: alice + bob
    convs_seeded = 0
    for participants, is_group, name, sample_msgs in [
        (
            sorted([ids["alice"], ids["bob"]]),
            False,
            None,
            [
                ("alice", "Hey Bob! Did you check out the new Ember chat app? 🔥"),
                ("bob",   "Yes! Loving the warm color palette. Way better than blue."),
                ("alice", "Right? Feels calm but premium."),
                ("bob",   "Let's hop on a video call later to demo it."),
            ],
        ),
        (
            sorted([ids["alice"], ids["carol"]]),
            False,
            None,
            [
                ("carol", "Welcome to Ember 👋"),
                ("alice", "Glad to be here, Carol!"),
            ],
        ),
        (
            sorted([ids["alice"], ids["bob"], ids["carol"]]),
            True,
            "Design Squad",
            [
                ("alice", "Group chat works in Ember too 🎉"),
                ("bob",   "Nice. Let's plan v2."),
                ("carol", "Adding voice messages next?"),
            ],
        ),
    ]:
        existing = await db.conversations.find_one({"participants": participants, "is_group": is_group, "name": name})
        if existing:
            conv_id = existing["id"]
        else:
            conv_id = str(uuid.uuid4())
            created_by = participants[0]
            await db.conversations.insert_one({
                "id": conv_id,
                "is_group": is_group,
                "name": name,
                "participants": participants,
                "created_by": created_by,
                "created_at": now_iso(-60),
                "updated_at": now_iso(),
            })
            convs_seeded += 1

        # Insert messages with staggered timestamps; avoid duplicating
        existing_count = await db.messages.count_documents({"conversation_id": conv_id})
        if existing_count >= len(sample_msgs):
            continue
        offset = -30
        for sender_username, content in sample_msgs:
            sender_id = ids[sender_username]
            sender_user = await db.users.find_one({"id": sender_id})
            await db.messages.insert_one({
                "id": str(uuid.uuid4()),
                "conversation_id": conv_id,
                "sender_id": sender_id,
                "sender_username": sender_username,
                "sender_name": sender_user["name"],
                "content": content,
                "media": None,
                "media_type": None,
                "read_by": [sender_id],
                "created_at": now_iso(offset),
            })
            offset += 5

        await db.conversations.update_one({"id": conv_id}, {"$set": {"updated_at": now_iso()}})

    print(f"  ✓ {convs_seeded} new conversations created (existing ones reused)")


async def reset_database(db):
    print("• Resetting database (dropping all collections)…")
    for c in ["users", "conversations", "messages", "friendships", "friend_requests"]:
        await db[c].drop()
    print("  ✓ dropped")


async def main():
    reset = "--reset" in sys.argv
    print(f"Connecting to MongoDB at {MONGO_URL} → db={DB_NAME}")
    client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    try:
        await client.admin.command("ping")
    except Exception as e:
        print(f"❌ Could not connect to MongoDB: {e}")
        sys.exit(1)
    db = client[DB_NAME]

    if reset:
        await reset_database(db)

    await ensure_indexes(db)
    user_ids = await seed_users(db)
    await seed_friendships(db, user_ids)
    await seed_friend_requests(db, user_ids)
    await seed_conversations(db, user_ids)

    print("\n✅ Seed complete.")
    print("\nLogin credentials (all sample users use these passwords):")
    print("   admin@example.com / admin123")
    print("   alice@test.com    / password123")
    print("   bob@test.com      / password123")
    print("   carol@test.com    / password123")
    print("   diego@test.com    / password123")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
