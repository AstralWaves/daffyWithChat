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
