from dotenv import load_dotenv
load_dotenv()

import os
import jwt
import bcrypt
import uuid
import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Set
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request, Response, WebSocket, WebSocketDisconnect, status, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from motor.motor_asyncio import AsyncIOMotorClient

# ---------------------- Config ----------------------
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]


# ---------------------- Helpers ----------------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "username": user["username"],
        "name": user.get("name", user["username"]),
        "avatar": user.get("avatar"),
        "bio": user.get("bio"),
        "online": user.get("online", False),
        "last_seen": user.get("last_seen"),
    }


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ---------------------- Models ----------------------
class RegisterIn(BaseModel):
    email: EmailStr
    username: str = Field(min_length=2, max_length=30)
    name: Optional[str] = None
    password: str = Field(min_length=6)

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class ConversationCreate(BaseModel):
    user_ids: List[str]
    is_group: bool = False
    name: Optional[str] = None

class MessageIn(BaseModel):
    conversation_id: str
    content: str = ""
    media: Optional[str] = None  # base64 data url
    media_type: Optional[str] = None  # "image"


class FriendRequestIn(BaseModel):
    target_user_id: str


class ProfileUpdateIn(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    avatar: Optional[str] = None  # base64 data URL


# ---------------------- WS Manager ----------------------
class ConnectionManager:
    def __init__(self):
        self.active: Dict[str, Set[WebSocket]] = {}  # user_id -> set of websockets

    async def connect(self, user_id: str, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(user_id, set()).add(ws)
        await db.users.update_one({"id": user_id}, {"$set": {"online": True, "last_seen": now_iso()}})
        await self.broadcast_presence(user_id, True)

    async def disconnect(self, user_id: str, ws: WebSocket):
        if user_id in self.active:
            self.active[user_id].discard(ws)
            if not self.active[user_id]:
                self.active.pop(user_id, None)
                await db.users.update_one({"id": user_id}, {"$set": {"online": False, "last_seen": now_iso()}})
                await self.broadcast_presence(user_id, False)

    def is_online(self, user_id: str) -> bool:
        return user_id in self.active and len(self.active[user_id]) > 0

    async def send_to_user(self, user_id: str, message: dict):
        if user_id in self.active:
            dead = []
            for ws in list(self.active[user_id]):
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append(ws)
            for w in dead:
                self.active[user_id].discard(w)

    async def broadcast_presence(self, user_id: str, online: bool):
        # find all conversations involving this user
        convs = db.conversations.find({"participants": user_id})
        notified: Set[str] = set()
        async for c in convs:
            for p in c.get("participants", []):
                if p != user_id and p not in notified:
                    notified.add(p)
                    await self.send_to_user(p, {
                        "type": "presence",
                        "user_id": user_id,
                        "online": online,
                        "last_seen": now_iso(),
                    })

manager = ConnectionManager()


# ---------------------- Lifespan ----------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Indexes
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

    # Seed admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
    admin_pass = os.environ.get("ADMIN_PASSWORD", "admin123")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": admin_email,
            "username": "admin",
            "name": "Admin",
            "password_hash": hash_password(admin_pass),
            "avatar": None,
            "online": False,
            "last_seen": now_iso(),
            "created_at": now_iso(),
        })
    elif not verify_password(admin_pass, existing["password_hash"]):
        await db.users.update_one(
            {"email": admin_email},
            {"$set": {"password_hash": hash_password(admin_pass)}}
        )
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")


# ---------------------- Auth ----------------------
@api.post("/auth/register")
async def register(payload: RegisterIn, response: Response):
    email = payload.email.lower().strip()
    username = payload.username.strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    if await db.users.find_one({"username": username}):
        raise HTTPException(status_code=400, detail="Username already taken")
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "email": email,
        "username": username,
        "name": payload.name or username,
        "password_hash": hash_password(payload.password),
        "avatar": None,
        "online": False,
        "last_seen": now_iso(),
        "created_at": now_iso(),
    }
    await db.users.insert_one(user)
    token = create_access_token(user_id, email)
    response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=60*60*24*7, path="/")
    return {"token": token, "user": public_user(user)}


@api.post("/auth/login")
async def login(payload: LoginIn, response: Response):
    email = payload.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user["id"], email)
    response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=60*60*24*7, path="/")
    return {"token": token, "user": public_user(user)}


@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}


@api.get("/auth/me")
async def me(user=Depends(get_current_user)):
    return public_user(user)


# ---------------------- Users ----------------------
@api.get("/users/search")
async def search_users(q: str = "", user=Depends(get_current_user)):
    if not q or len(q) < 1:
        return []
    cursor = db.users.find({
        "$and": [
            {"id": {"$ne": user["id"]}},
            {"$or": [
                {"username": {"$regex": q, "$options": "i"}},
                {"email": {"$regex": q, "$options": "i"}},
                {"name": {"$regex": q, "$options": "i"}},
            ]}
        ]
    }, {"_id": 0}).limit(20)
    results = []
    async for u in cursor:
        u["online"] = manager.is_online(u["id"])
        pu = public_user(u)
        pu["friendship_status"] = await friendship_status(user["id"], u["id"])
        results.append(pu)
    return results


# ---------------------- Conversations ----------------------
async def serialize_conversation(c: dict, viewer_id: str) -> dict:
    participants = c.get("participants", [])
    users = []
    async for u in db.users.find({"id": {"$in": participants}}, {"_id": 0}):
        u["online"] = manager.is_online(u["id"])
        users.append(public_user(u))
    last_msg = await db.messages.find_one(
        {"conversation_id": c["id"]},
        {"_id": 0},
        sort=[("created_at", -1)],
    )
    unread = await db.messages.count_documents({
        "conversation_id": c["id"],
        "sender_id": {"$ne": viewer_id},
        "read_by": {"$nin": [viewer_id]},
    })
    return {
        "id": c["id"],
        "is_group": c.get("is_group", False),
        "name": c.get("name"),
        "participants": users,
        "last_message": last_msg,
        "unread_count": unread,
        "updated_at": c.get("updated_at"),
        "created_at": c.get("created_at"),
    }


@api.get("/conversations")
async def list_conversations(user=Depends(get_current_user)):
    cursor = db.conversations.find({"participants": user["id"]}, {"_id": 0}).sort("updated_at", -1)
    out = []
    async for c in cursor:
        out.append(await serialize_conversation(c, user["id"]))
    return out


@api.post("/conversations")
async def create_conversation(payload: ConversationCreate, user=Depends(get_current_user)):
    user_ids = list(set(payload.user_ids + [user["id"]]))
    if len(user_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least one other user")

    if not payload.is_group and len(user_ids) == 2:
        # Check if 1-on-1 exists
        existing = await db.conversations.find_one({
            "is_group": False,
            "participants": {"$all": user_ids, "$size": 2},
        }, {"_id": 0})
        if existing:
            return await serialize_conversation(existing, user["id"])

    conv = {
        "id": str(uuid.uuid4()),
        "is_group": payload.is_group or len(user_ids) > 2,
        "name": payload.name,
        "participants": user_ids,
        "created_by": user["id"],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.conversations.insert_one(conv)

    # Notify all participants
    serialized = await serialize_conversation(conv, user["id"])
    for p in user_ids:
        await manager.send_to_user(p, {"type": "conversation_new", "conversation": serialized})
    return serialized


@api.get("/conversations/{conv_id}/messages")
async def get_messages(conv_id: str, user=Depends(get_current_user)):
    conv = await db.conversations.find_one({"id": conv_id})
    if not conv or user["id"] not in conv.get("participants", []):
        raise HTTPException(status_code=404, detail="Conversation not found")

    cursor = db.messages.find({"conversation_id": conv_id}, {"_id": 0}).sort("created_at", 1).limit(500)
    msgs = []
    async for m in cursor:
        msgs.append(m)

    # Mark as read
    await db.messages.update_many(
        {"conversation_id": conv_id, "sender_id": {"$ne": user["id"]}, "read_by": {"$nin": [user["id"]]}},
        {"$addToSet": {"read_by": user["id"]}},
    )

    # Notify other participants of read receipt
    for p in conv["participants"]:
        if p != user["id"]:
            await manager.send_to_user(p, {
                "type": "messages_read",
                "conversation_id": conv_id,
                "reader_id": user["id"],
            })
    return msgs


@api.post("/messages")
async def send_message(payload: MessageIn, user=Depends(get_current_user)):
    conv = await db.conversations.find_one({"id": payload.conversation_id})
    if not conv or user["id"] not in conv.get("participants", []):
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg = {
        "id": str(uuid.uuid4()),
        "conversation_id": payload.conversation_id,
        "sender_id": user["id"],
        "sender_username": user["username"],
        "sender_name": user.get("name", user["username"]),
        "content": payload.content,
        "media": payload.media,
        "media_type": payload.media_type,
        "read_by": [user["id"]],
        "created_at": now_iso(),
    }
    await db.messages.insert_one(msg)
    await db.conversations.update_one({"id": payload.conversation_id}, {"$set": {"updated_at": now_iso()}})

    msg.pop("_id", None)

    # broadcast
    for p in conv["participants"]:
        await manager.send_to_user(p, {"type": "message_new", "message": msg})
    return msg


# ---------------------- WebSocket ----------------------
@app.websocket("/api/ws")
async def websocket_endpoint(ws: WebSocket, token: str = ""):
    user_id: Optional[str] = None
    try:
        payload = decode_token(token)
        user_id = payload["sub"]
        u = await db.users.find_one({"id": user_id})
        if not u:
            await ws.close(code=4401)
            return
    except Exception:
        await ws.close(code=4401)
        return

    await manager.connect(user_id, ws)
    try:
        while True:
            data = await ws.receive_json()
            t = data.get("type")
            if t == "typing":
                conv_id = data.get("conversation_id")
                conv = await db.conversations.find_one({"id": conv_id})
                if conv and user_id in conv.get("participants", []):
                    for p in conv["participants"]:
                        if p != user_id:
                            await manager.send_to_user(p, {
                                "type": "typing",
                                "conversation_id": conv_id,
                                "user_id": user_id,
                                "is_typing": data.get("is_typing", True),
                            })
            elif t in ("call_offer", "call_answer", "call_ice", "call_end", "call_reject"):
                target = data.get("target_user_id")
                if target:
                    forward = dict(data)
                    forward["from_user_id"] = user_id
                    await manager.send_to_user(target, forward)
            elif t == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if user_id:
            await manager.disconnect(user_id, ws)


@api.get("/health")
async def health():
    return {"status": "ok"}


# ---------------------- Profile ----------------------
@api.patch("/users/me")
async def update_profile(payload: ProfileUpdateIn, user=Depends(get_current_user)):
    update = {}
    if payload.name is not None:
        update["name"] = payload.name.strip() or user["username"]
    if payload.bio is not None:
        update["bio"] = payload.bio.strip()
    if payload.avatar is not None:
        update["avatar"] = payload.avatar
    if not update:
        return public_user(user)
    await db.users.update_one({"id": user["id"]}, {"$set": update})
    fresh = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return public_user(fresh)


# ---------------------- Friends ----------------------
async def friendship_status(me_id: str, other_id: str) -> str:
    """Returns: 'none' | 'pending_out' | 'pending_in' | 'friends'"""
    if me_id == other_id:
        return "self"
    fr = await db.friendships.find_one({
        "users": {"$all": [me_id, other_id]}
    })
    if fr:
        return "friends"
    out = await db.friend_requests.find_one({"from_user_id": me_id, "to_user_id": other_id, "status": "pending"})
    if out:
        return "pending_out"
    inc = await db.friend_requests.find_one({"from_user_id": other_id, "to_user_id": me_id, "status": "pending"})
    if inc:
        return "pending_in"
    return "none"


@api.post("/friends/request")
async def send_friend_request(payload: FriendRequestIn, user=Depends(get_current_user)):
    if payload.target_user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot send request to yourself")
    target = await db.users.find_one({"id": payload.target_user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    status_str = await friendship_status(user["id"], payload.target_user_id)
    if status_str == "friends":
        raise HTTPException(status_code=400, detail="Already friends")
    if status_str == "pending_out":
        raise HTTPException(status_code=400, detail="Request already sent")
    if status_str == "pending_in":
        # auto-accept
        return await accept_friend_request_internal(user, payload.target_user_id)
    req = {
        "id": str(uuid.uuid4()),
        "from_user_id": user["id"],
        "to_user_id": payload.target_user_id,
        "status": "pending",
        "created_at": now_iso(),
    }
    await db.friend_requests.insert_one(req)
    req.pop("_id", None)
    # notify target
    await manager.send_to_user(payload.target_user_id, {
        "type": "friend_request_new",
        "request": req,
        "from_user": public_user(user),
    })
    return {"status": "pending_out", "request": req}


async def accept_friend_request_internal(me: dict, other_id: str):
    req = await db.friend_requests.find_one({
        "from_user_id": other_id, "to_user_id": me["id"], "status": "pending"
    })
    if not req:
        raise HTTPException(status_code=404, detail="No pending request")
    await db.friend_requests.update_one({"id": req["id"]}, {"$set": {"status": "accepted", "accepted_at": now_iso()}})
    fr = {
        "id": str(uuid.uuid4()),
        "users": sorted([me["id"], other_id]),
        "created_at": now_iso(),
    }
    await db.friendships.insert_one(fr)
    fr.pop("_id", None)
    other = await db.users.find_one({"id": other_id}, {"_id": 0})
    # notify both sides
    await manager.send_to_user(other_id, {
        "type": "friend_request_accepted",
        "by_user": public_user(me),
    })
    return {"status": "friends", "user": public_user(other) if other else None}


@api.post("/friends/accept")
async def accept_friend_request(payload: FriendRequestIn, user=Depends(get_current_user)):
    return await accept_friend_request_internal(user, payload.target_user_id)


@api.post("/friends/reject")
async def reject_friend_request(payload: FriendRequestIn, user=Depends(get_current_user)):
    res = await db.friend_requests.update_one(
        {"from_user_id": payload.target_user_id, "to_user_id": user["id"], "status": "pending"},
        {"$set": {"status": "rejected"}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="No pending request")
    return {"status": "rejected"}


@api.delete("/friends/{friend_id}")
async def remove_friend(friend_id: str, user=Depends(get_current_user)):
    await db.friendships.delete_many({"users": {"$all": [user["id"], friend_id]}})
    return {"ok": True}


@api.get("/friends")
async def list_friends(user=Depends(get_current_user)):
    cursor = db.friendships.find({"users": user["id"]}, {"_id": 0})
    friend_ids = []
    async for f in cursor:
        for uid in f["users"]:
            if uid != user["id"]:
                friend_ids.append(uid)
    if not friend_ids:
        return []
    friends = []
    async for u in db.users.find({"id": {"$in": friend_ids}}, {"_id": 0}):
        u["online"] = manager.is_online(u["id"])
        friends.append(public_user(u))
    return friends


@api.get("/friends/requests")
async def list_friend_requests(user=Depends(get_current_user)):
    cursor = db.friend_requests.find({"to_user_id": user["id"], "status": "pending"}, {"_id": 0}).sort("created_at", -1)
    out = []
    async for r in cursor:
        u = await db.users.find_one({"id": r["from_user_id"]}, {"_id": 0})
        if u:
            out.append({"request": r, "from_user": public_user(u)})
    return out


@api.get("/friends/status/{other_id}")
async def get_friendship_status(other_id: str, user=Depends(get_current_user)):
    return {"status": await friendship_status(user["id"], other_id)}


app.include_router(api)
