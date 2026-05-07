# Ember — Real-time Chat App

A real-time chat application like Facebook Messenger / WhatsApp, with email/password authentication, 1-on-1 + group chats, media sharing, audio/video calls (WebRTC), friend requests, presence indicators, typing indicators, read receipts, and a beautiful "Organic & Earthy" design.

**Stack:** FastAPI · MongoDB · WebSocket · React · Tailwind CSS · WebRTC

---

## ✨ Features

- 📝 Email/password sign up + sign in (JWT)
- 💬 Real-time messaging (1-on-1 + group chats)
- 🖼️ Image attachments (base64)
- 🟢 Online / offline presence
- ✍️ Typing indicators
- ✓✓ Read receipts (terracotta double-check when read)
- 📞 Audio calls (WebRTC)
- 📹 Video calls (WebRTC)
- 👥 Friend request system (send / accept / reject / auto-accept on mutual)
- 👤 Profile editing (name, bio, avatar upload)
- 🔔 Notification ping sound on new message
- 📆 Date-grouped messages (Today / Yesterday / weekday / date)
- 🔍 Search users by username, email, or name

---

## 📋 Prerequisites

You need these installed on your machine:

| Tool | Min version | Where to get it |
|---|---|---|
| **Python** | 3.10+ | https://www.python.org/downloads/ |
| **Node.js** | 18+ | https://nodejs.org/ |
| **Yarn** | 1.22+ | `npm install -g yarn` |
| **MongoDB** | 6.0+ (community) | https://www.mongodb.com/try/download/community |

> **Tip:** If you don't want to install MongoDB, use Docker (see "Run with Docker MongoDB" below) — easiest option.

---

## 🚀 Quick Start

### 1. Clone the repo

```bash
git clone <your-github-repo-url> ember-chat
cd ember-chat
```

### 2. Set up environment variables

Copy the example files:

```bash
# Linux / Mac
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# Windows (PowerShell)
copy backend\.env.example backend\.env
copy frontend\.env.example frontend\.env
```

Edit `backend/.env` if you want to change the JWT secret or admin credentials. Defaults are fine for local development.

### 3. Start MongoDB

**Option A — Local MongoDB:**
```bash
# Linux / Mac
mongod --dbpath ~/data/db

# Windows (run as service or)
"C:\Program Files\MongoDB\Server\7.0\bin\mongod.exe" --dbpath "C:\data\db"
```

**Option B — Docker MongoDB (easiest):**
```bash
docker run -d --name ember-mongo -p 27017:27017 -v ember_mongo_data:/data/db mongo:7
```

### 3a. (Optional) Load sample database

To start with sample users and conversations, restore the included dump:

```bash
mongorestore --uri="mongodb://localhost:27017" --gzip --archive=database/ember_chat.archive
```

…or run the Python seed script for a fresh sample:

```bash
cd backend
python seed_db.py
```

See `database/README.md` and `database/schema.md` for full details.

### 4. Start the backend

In a new terminal:

```bash
cd backend
python -m venv venv

# Activate venv:
# Linux / Mac
source venv/bin/activate
# Windows (PowerShell)
venv\Scripts\Activate.ps1
# Windows (cmd)
venv\Scripts\activate.bat

pip install -r requirements.txt
uvicorn server:app --reload --host 0.0.0.0 --port 8001
```

Backend runs at **http://localhost:8001**. Verify: open http://localhost:8001/api/health → `{"status":"ok"}`

### 5. Start the frontend

In **another new terminal**:

```bash
cd frontend
yarn install
yarn start
```

Frontend runs at **http://localhost:3000**. Browser should open automatically.

### 6. Use the app

1. Go to http://localhost:3000
2. Click **"Create an account"**
3. Register two users (e.g., open another browser / incognito window for the second one)
4. Search and add as friends, or just start chatting directly
5. Send messages, share images, place audio/video calls 🎉

---

## 🗂️ Project Structure

```
ember-chat/
├── backend/
│   ├── server.py              # FastAPI app (auth, users, conversations, messages, friends, ws)
│   ├── seed_db.py             # Sample data seeder (run: python seed_db.py [--reset])
│   ├── requirements.txt       # Python dependencies
│   └── .env                   # Backend config (you create this)
│
├── database/
│   ├── ember_chat.archive     # Binary mongodump backup with sample data
│   ├── schema.md              # Detailed collection/field documentation
│   └── README.md              # How to restore/seed
│
├── frontend/
│   ├── src/
│   │   ├── App.js             # Routing
│   │   ├── AuthContext.js     # Auth state + login/register
│   │   ├── api.js             # axios + WebSocket URL helper
│   │   ├── index.js / .css    # Entry point + global styles
│   │   └── components/
│   │       ├── AuthScreen.jsx     # Login / Register split-screen
│   │       ├── ChatApp.jsx        # Main app (manages WS + state)
│   │       ├── Sidebar.jsx        # Conversation list, search, profile/friends/logout
│   │       ├── ChatWindow.jsx     # Messages, typing indicator, input, call buttons
│   │       ├── CallModal.jsx      # WebRTC audio/video call UI
│   │       ├── FriendsModal.jsx   # Friends / Requests / Find people tabs
│   │       └── ProfileModal.jsx   # Edit profile (avatar, name, bio)
│   ├── public/index.html
│   ├── package.json
│   ├── tailwind.config.js
│   └── .env                   # Frontend config (you create this)
│
└── README.md                  # This file
```

---

## ⚙️ Environment Variables

### `backend/.env`

```env
MONGO_URL="mongodb://localhost:27017"
DB_NAME="chat_app_db"
JWT_SECRET="change-me-to-a-long-random-hex-string"
ADMIN_EMAIL="admin@example.com"
ADMIN_PASSWORD="admin123"
```

### `frontend/.env`

```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

> ⚠️ Important: Every backend API path is prefixed with `/api`. The frontend builds requests as `${REACT_APP_BACKEND_URL}/api/...`. **Do not include `/api` in `REACT_APP_BACKEND_URL`.**

---

## 📜 Run Commands Cheat Sheet

| What | Command |
|---|---|
| Start MongoDB (Docker) | `docker run -d --name ember-mongo -p 27017:27017 mongo:7` |
| Start backend | `cd backend && source venv/bin/activate && uvicorn server:app --reload --port 8001` |
| Start frontend | `cd frontend && yarn start` |
| Build frontend (production) | `cd frontend && yarn build` |
| Stop MongoDB (Docker) | `docker stop ember-mongo` |

---

## 🧪 Default test accounts

After first launch, the seeded admin is:
- Email: `admin@example.com`
- Password: `admin123`

You can register more users via the UI.

---

## 🛠️ Troubleshooting

**Backend can't connect to MongoDB:**  
Make sure `mongod` is running and `MONGO_URL` in `backend/.env` is reachable. Test with `mongosh mongodb://localhost:27017`.

**Frontend shows "Network Error" or can't login:**  
Check `frontend/.env` has the correct `REACT_APP_BACKEND_URL` (no trailing slash, no `/api` suffix). Restart `yarn start` after changing the `.env`.

**Audio/video call fails:**  
Calls need browser mic/camera permission. Click "Allow" when the browser prompts. Calls work over `localhost` and `https://`. They will NOT work over plain `http://` on a remote host — browsers block media devices on insecure origins.

**WebSocket disconnects immediately:**  
Token may have expired (7-day default). Sign out and back in.

**Port already in use:**  
- Backend: change `--port 8001` to another port and update `REACT_APP_BACKEND_URL` accordingly.
- Frontend: `PORT=3001 yarn start` (Linux/Mac) or `set PORT=3001 && yarn start` (Windows).

---

## 🚢 Production Build

```bash
cd frontend
yarn build
# Serves the static files from frontend/build/
```

Then run the backend behind a reverse proxy (nginx/Caddy) that:
- Serves `frontend/build/` as static
- Proxies `/api/*` (and `/api/ws`) to `http://localhost:8001`
- Provides HTTPS (required for WebRTC audio/video)

---

## 📄 License

Personal / educational use. Customize freely for your social platform.
