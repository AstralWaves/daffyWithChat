"""Backend API tests for Ember chat app."""
import os
import time
import uuid
import json
import asyncio
import pytest
import requests
import websockets

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

WS_URL = BASE_URL.replace("https://", "wss://").replace("http://", "ws://") + "/api/ws"

UNIQUE = uuid.uuid4().hex[:8]
ALICE = {"email": f"test_alice_{UNIQUE}@test.com", "username": f"test_alice_{UNIQUE}", "password": "password123", "name": "Alice"}
BOB = {"email": f"test_bob_{UNIQUE}@test.com", "username": f"test_bob_{UNIQUE}", "password": "password123", "name": "Bob"}

state = {}


# ---- Auth ----
def test_health():
    r = requests.get(f"{BASE_URL}/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register_alice():
    r = requests.post(f"{BASE_URL}/api/auth/register", json=ALICE)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "token" in data and "user" in data
    assert data["user"]["email"] == ALICE["email"]
    assert data["user"]["username"] == ALICE["username"]
    assert "id" in data["user"]
    state["alice_token"] = data["token"]
    state["alice_id"] = data["user"]["id"]


def test_register_bob():
    r = requests.post(f"{BASE_URL}/api/auth/register", json=BOB)
    assert r.status_code == 200, r.text
    data = r.json()
    state["bob_token"] = data["token"]
    state["bob_id"] = data["user"]["id"]


def test_register_duplicate_email():
    r = requests.post(f"{BASE_URL}/api/auth/register", json=ALICE)
    assert r.status_code == 400


def test_login_alice():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ALICE["email"], "password": ALICE["password"]})
    assert r.status_code == 200
    assert "token" in r.json()
    # Cookie set?
    assert "access_token" in r.cookies


def test_login_invalid():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ALICE["email"], "password": "wrong"})
    assert r.status_code == 401


def test_me_with_bearer():
    r = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {state['alice_token']}"})
    assert r.status_code == 200
    assert r.json()["email"] == ALICE["email"]


def test_me_no_auth():
    r = requests.get(f"{BASE_URL}/api/auth/me")
    assert r.status_code == 401


# ---- Users search ----
def test_search_users_by_username():
    r = requests.get(f"{BASE_URL}/api/users/search", params={"q": BOB["username"]},
                     headers={"Authorization": f"Bearer {state['alice_token']}"})
    assert r.status_code == 200
    results = r.json()
    assert any(u["id"] == state["bob_id"] for u in results)
    # excludes self
    assert not any(u["id"] == state["alice_id"] for u in results)


def test_search_users_empty_query():
    r = requests.get(f"{BASE_URL}/api/users/search", params={"q": ""},
                     headers={"Authorization": f"Bearer {state['alice_token']}"})
    assert r.status_code == 200
    assert r.json() == []


# ---- Conversations ----
def test_create_conversation():
    r = requests.post(f"{BASE_URL}/api/conversations",
                      json={"user_ids": [state["bob_id"]], "is_group": False},
                      headers={"Authorization": f"Bearer {state['alice_token']}"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "id" in data
    assert len(data["participants"]) == 2
    state["conv_id"] = data["id"]


def test_create_conversation_returns_existing():
    r = requests.post(f"{BASE_URL}/api/conversations",
                      json={"user_ids": [state["bob_id"]], "is_group": False},
                      headers={"Authorization": f"Bearer {state['alice_token']}"})
    assert r.status_code == 200
    assert r.json()["id"] == state["conv_id"]


def test_list_conversations():
    r = requests.get(f"{BASE_URL}/api/conversations",
                     headers={"Authorization": f"Bearer {state['alice_token']}"})
    assert r.status_code == 200
    convs = r.json()
    assert any(c["id"] == state["conv_id"] for c in convs)


# ---- Messages ----
def test_send_message():
    r = requests.post(f"{BASE_URL}/api/messages",
                      json={"conversation_id": state["conv_id"], "content": "Hello Bob from TEST"},
                      headers={"Authorization": f"Bearer {state['alice_token']}"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["content"] == "Hello Bob from TEST"
    assert data["sender_id"] == state["alice_id"]
    assert "id" in data
    state["msg_id"] = data["id"]


def test_get_messages_marks_read():
    # bob fetches messages -> should mark alice's message as read (server marks AFTER returning)
    r = requests.get(f"{BASE_URL}/api/conversations/{state['conv_id']}/messages",
                     headers={"Authorization": f"Bearer {state['bob_token']}"})
    assert r.status_code == 200
    msgs = r.json()
    assert any(m["id"] == state["msg_id"] for m in msgs)
    # Refetch -> read_by should now include bob (alice fetches to see updated state)
    r2 = requests.get(f"{BASE_URL}/api/conversations/{state['conv_id']}/messages",
                      headers={"Authorization": f"Bearer {state['alice_token']}"})
    assert r2.status_code == 200
    target = next(m for m in r2.json() if m["id"] == state["msg_id"])
    assert state["bob_id"] in target["read_by"]


def test_send_message_to_invalid_conv():
    r = requests.post(f"{BASE_URL}/api/messages",
                      json={"conversation_id": "nonexistent", "content": "hi"},
                      headers={"Authorization": f"Bearer {state['alice_token']}"})
    assert r.status_code == 404


def test_get_messages_unauthorized_conv():
    # Create third user, try to access alice/bob conv
    third = {"email": f"test_third_{UNIQUE}@test.com", "username": f"test_third_{UNIQUE}",
             "password": "password123", "name": "Third"}
    rr = requests.post(f"{BASE_URL}/api/auth/register", json=third)
    assert rr.status_code == 200
    third_tok = rr.json()["token"]
    r = requests.get(f"{BASE_URL}/api/conversations/{state['conv_id']}/messages",
                     headers={"Authorization": f"Bearer {third_tok}"})
    assert r.status_code == 404


# ---- WebSocket ----
@pytest.mark.asyncio
async def test_websocket_message_delivery():
    """Alice connects via WS, Bob sends a message via REST, Alice should receive it."""
    alice_ws_url = f"{WS_URL}?token={state['alice_token']}"
    async with websockets.connect(alice_ws_url) as ws:
        # Give server a moment
        await asyncio.sleep(0.3)
        # Bob sends a message
        r = requests.post(f"{BASE_URL}/api/messages",
                          json={"conversation_id": state["conv_id"], "content": "Hello from Bob WS"},
                          headers={"Authorization": f"Bearer {state['bob_token']}"})
        assert r.status_code == 200
        # receive
        got_msg = False
        try:
            for _ in range(5):
                raw = await asyncio.wait_for(ws.recv(), timeout=3)
                msg = json.loads(raw)
                if msg.get("type") == "message_new" and msg["message"]["content"] == "Hello from Bob WS":
                    got_msg = True
                    break
        except asyncio.TimeoutError:
            pass
        assert got_msg, "Did not receive message_new event"


@pytest.mark.asyncio
async def test_websocket_invalid_token():
    try:
        async with websockets.connect(f"{WS_URL}?token=invalid") as ws:
            await asyncio.wait_for(ws.recv(), timeout=2)
            assert False, "Should have closed"
    except Exception:
        pass  # Expected


@pytest.mark.asyncio
async def test_websocket_typing_and_call_signaling():
    a_url = f"{WS_URL}?token={state['alice_token']}"
    b_url = f"{WS_URL}?token={state['bob_token']}"
    async with websockets.connect(a_url) as a_ws, websockets.connect(b_url) as b_ws:
        await asyncio.sleep(0.3)
        # drain any presence msgs
        async def drain(ws):
            try:
                while True:
                    await asyncio.wait_for(ws.recv(), timeout=0.3)
            except asyncio.TimeoutError:
                pass
        await drain(a_ws)
        await drain(b_ws)

        # Alice typing
        await a_ws.send(json.dumps({"type": "typing", "conversation_id": state["conv_id"], "is_typing": True}))
        raw = await asyncio.wait_for(b_ws.recv(), timeout=3)
        ev = json.loads(raw)
        assert ev["type"] == "typing"
        assert ev["user_id"] == state["alice_id"]

        # Call offer
        await a_ws.send(json.dumps({"type": "call_offer", "target_user_id": state["bob_id"], "sdp": "fake-sdp"}))
        raw = await asyncio.wait_for(b_ws.recv(), timeout=3)
        ev = json.loads(raw)
        assert ev["type"] == "call_offer"
        assert ev["from_user_id"] == state["alice_id"]



# ---- Profile (PATCH /api/users/me) ----
def test_update_profile_name_bio_avatar():
    avatar_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    payload = {"name": "Alice Updated", "bio": "Hello I am Alice", "avatar": avatar_b64}
    r = requests.patch(f"{BASE_URL}/api/users/me", json=payload,
                       headers={"Authorization": f"Bearer {state['alice_token']}"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["name"] == "Alice Updated"
    assert data["bio"] == "Hello I am Alice"
    assert data["avatar"] == avatar_b64
    # Verify GET /me returns persisted values
    r2 = requests.get(f"{BASE_URL}/api/auth/me",
                      headers={"Authorization": f"Bearer {state['alice_token']}"})
    assert r2.status_code == 200
    me = r2.json()
    assert me["name"] == "Alice Updated"
    assert me["bio"] == "Hello I am Alice"
    assert me["avatar"] == avatar_b64


def test_update_profile_partial():
    r = requests.patch(f"{BASE_URL}/api/users/me", json={"bio": "Just bio"},
                       headers={"Authorization": f"Bearer {state['alice_token']}"})
    assert r.status_code == 200
    assert r.json()["bio"] == "Just bio"
    # name should remain
    assert r.json()["name"] == "Alice Updated"


def test_update_profile_unauth():
    r = requests.patch(f"{BASE_URL}/api/users/me", json={"bio": "x"})
    assert r.status_code == 401


# ---- Friends ----
def test_friends_status_initial_none():
    r = requests.get(f"{BASE_URL}/api/friends/status/{state['bob_id']}",
                     headers={"Authorization": f"Bearer {state['alice_token']}"})
    assert r.status_code == 200
    assert r.json()["status"] == "none"


def test_friend_request_send():
    r = requests.post(f"{BASE_URL}/api/friends/request",
                      json={"target_user_id": state["bob_id"]},
                      headers={"Authorization": f"Bearer {state['alice_token']}"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "pending_out"


def test_friend_request_duplicate_send():
    r = requests.post(f"{BASE_URL}/api/friends/request",
                      json={"target_user_id": state["bob_id"]},
                      headers={"Authorization": f"Bearer {state['alice_token']}"})
    assert r.status_code == 400


def test_friend_request_to_self():
    r = requests.post(f"{BASE_URL}/api/friends/request",
                      json={"target_user_id": state["alice_id"]},
                      headers={"Authorization": f"Bearer {state['alice_token']}"})
    assert r.status_code == 400


def test_friends_status_pending_in_for_bob():
    r = requests.get(f"{BASE_URL}/api/friends/status/{state['alice_id']}",
                     headers={"Authorization": f"Bearer {state['bob_token']}"})
    assert r.json()["status"] == "pending_in"


def test_friends_status_pending_out_for_alice():
    r = requests.get(f"{BASE_URL}/api/friends/status/{state['bob_id']}",
                     headers={"Authorization": f"Bearer {state['alice_token']}"})
    assert r.json()["status"] == "pending_out"


def test_list_friend_requests_for_bob():
    r = requests.get(f"{BASE_URL}/api/friends/requests",
                     headers={"Authorization": f"Bearer {state['bob_token']}"})
    assert r.status_code == 200
    reqs = r.json()
    assert any(item["from_user"]["id"] == state["alice_id"] for item in reqs)


def test_search_includes_friendship_status():
    r = requests.get(f"{BASE_URL}/api/users/search", params={"q": BOB["username"]},
                     headers={"Authorization": f"Bearer {state['alice_token']}"})
    assert r.status_code == 200
    bob_entry = next(u for u in r.json() if u["id"] == state["bob_id"])
    assert "friendship_status" in bob_entry
    assert bob_entry["friendship_status"] == "pending_out"


def test_friend_request_accept():
    r = requests.post(f"{BASE_URL}/api/friends/accept",
                      json={"target_user_id": state["alice_id"]},
                      headers={"Authorization": f"Bearer {state['bob_token']}"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "friends"


def test_friends_list_after_accept():
    r = requests.get(f"{BASE_URL}/api/friends",
                     headers={"Authorization": f"Bearer {state['alice_token']}"})
    assert r.status_code == 200
    friends = r.json()
    assert any(f["id"] == state["bob_id"] for f in friends)


def test_friends_status_friends():
    r = requests.get(f"{BASE_URL}/api/friends/status/{state['bob_id']}",
                     headers={"Authorization": f"Bearer {state['alice_token']}"})
    assert r.json()["status"] == "friends"


def test_search_friendship_status_friends():
    r = requests.get(f"{BASE_URL}/api/users/search", params={"q": BOB["username"]},
                     headers={"Authorization": f"Bearer {state['alice_token']}"})
    bob_entry = next(u for u in r.json() if u["id"] == state["bob_id"])
    assert bob_entry["friendship_status"] == "friends"


def test_friend_auto_accept_on_mutual_request():
    # Create two new users, charlie sends to dave, dave sends back -> auto-accept
    c = {"email": f"test_charlie_{UNIQUE}@test.com", "username": f"test_charlie_{UNIQUE}",
         "password": "password123", "name": "Charlie"}
    d = {"email": f"test_dave_{UNIQUE}@test.com", "username": f"test_dave_{UNIQUE}",
         "password": "password123", "name": "Dave"}
    rc = requests.post(f"{BASE_URL}/api/auth/register", json=c).json()
    rd = requests.post(f"{BASE_URL}/api/auth/register", json=d).json()
    # charlie -> dave
    r1 = requests.post(f"{BASE_URL}/api/friends/request",
                       json={"target_user_id": rd["user"]["id"]},
                       headers={"Authorization": f"Bearer {rc['token']}"})
    assert r1.json()["status"] == "pending_out"
    # dave -> charlie => auto-accept
    r2 = requests.post(f"{BASE_URL}/api/friends/request",
                       json={"target_user_id": rc["user"]["id"]},
                       headers={"Authorization": f"Bearer {rd['token']}"})
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "friends"


def test_remove_friend():
    r = requests.delete(f"{BASE_URL}/api/friends/{state['bob_id']}",
                        headers={"Authorization": f"Bearer {state['alice_token']}"})
    assert r.status_code == 200
    # status should be 'none' now
    r2 = requests.get(f"{BASE_URL}/api/friends/status/{state['bob_id']}",
                      headers={"Authorization": f"Bearer {state['alice_token']}"})
    assert r2.json()["status"] == "none"


def test_friend_request_reject_flow():
    # bob sends to alice (now removed), alice rejects
    r1 = requests.post(f"{BASE_URL}/api/friends/request",
                       json={"target_user_id": state["alice_id"]},
                       headers={"Authorization": f"Bearer {state['bob_token']}"})
    assert r1.status_code == 200
    assert r1.json()["status"] == "pending_out"
    r2 = requests.post(f"{BASE_URL}/api/friends/reject",
                       json={"target_user_id": state["bob_id"]},
                       headers={"Authorization": f"Bearer {state['alice_token']}"})
    assert r2.status_code == 200
    assert r2.json()["status"] == "rejected"
    # second reject -> 404
    r3 = requests.post(f"{BASE_URL}/api/friends/reject",
                       json={"target_user_id": state["bob_id"]},
                       headers={"Authorization": f"Bearer {state['alice_token']}"})
    assert r3.status_code == 404


# ---- WS friend_request_new event ----
@pytest.mark.asyncio
async def test_ws_friend_request_event():
    # Create two new users so we don't pollute prior state
    e = {"email": f"test_eve_{UNIQUE}@test.com", "username": f"test_eve_{UNIQUE}",
         "password": "password123", "name": "Eve"}
    f = {"email": f"test_frank_{UNIQUE}@test.com", "username": f"test_frank_{UNIQUE}",
         "password": "password123", "name": "Frank"}
    re = requests.post(f"{BASE_URL}/api/auth/register", json=e).json()
    rf = requests.post(f"{BASE_URL}/api/auth/register", json=f).json()
    eve_url = f"{WS_URL}?token={re['token']}"
    async with websockets.connect(eve_url) as ws:
        await asyncio.sleep(0.3)
        # Frank sends request to Eve via REST
        rr = requests.post(f"{BASE_URL}/api/friends/request",
                           json={"target_user_id": re["user"]["id"]},
                           headers={"Authorization": f"Bearer {rf['token']}"})
        assert rr.status_code == 200
        got = False
        try:
            for _ in range(5):
                raw = await asyncio.wait_for(ws.recv(), timeout=3)
                msg = json.loads(raw)
                if msg.get("type") == "friend_request_new":
                    assert msg["from_user"]["id"] == rf["user"]["id"]
                    got = True
                    break
        except asyncio.TimeoutError:
            pass
        assert got, "Did not receive friend_request_new"
