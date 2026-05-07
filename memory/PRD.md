# Ember — Real-time Chat (PRD)

## Original Problem Statement
"build a real time chatting like facebook... here signup signin then can chat on real time"

## User Choices
- Auth: Email/password (JWT)
- Features: 1-on-1 + group chats + media sharing + audio/video calls
- Extras: presence, typing indicators, read receipts (all)
- Friend request system (added in iteration 2)
- Design: creative & distinctive — "Organic & Earthy" theme (terracotta + sage + sand)
- Future: integrate with main social media

## Architecture
- Backend: FastAPI + MongoDB (motor) + WebSocket (`/api/ws`)
- Frontend: React + Tailwind + Lucide icons
- Real-time: WebSocket for messaging, presence, typing, read receipts, WebRTC signaling
- Calls: WebRTC (browser-native) with WebSocket signaling
- Auth: JWT Bearer tokens (stored in localStorage)

## Core Requirements (DONE)
- [x] Sign up / Sign in
- [x] Real-time messaging (1-on-1 + groups)
- [x] Image attachments (base64)
- [x] Online presence indicators
- [x] Typing indicators
- [x] Read receipts (✓ → ✓✓ in terracotta)
- [x] Audio + Video calls (WebRTC)
- [x] User search by username/email/name
- [x] Friend request system (send/accept/reject/list)
- [x] Profile editing (name, bio, avatar upload)
- [x] Notification sound (synthesized ping) for new messages
- [x] Date-grouped message timestamps (Today / Yesterday / weekday / date)

## Implemented (Jan 2026)
### Backend (`/app/backend/server.py`)
- `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`
- `GET /api/users/search?q=` (with friendship_status per user)
- `PATCH /api/users/me` (name, bio, avatar)
- `GET /api/conversations`, `POST /api/conversations`
- `GET /api/conversations/:id/messages`, `POST /api/messages`
- `POST /api/friends/request`, `POST /api/friends/accept`, `POST /api/friends/reject`
- `GET /api/friends`, `GET /api/friends/requests`, `GET /api/friends/status/:id`
- `DELETE /api/friends/:id`
- `WS /api/ws?token=` — message_new, conversation_new, presence, typing, messages_read, friend_request_new, friend_request_accepted, call_offer/answer/ice/end/reject

### Frontend (`/app/frontend/src/`)
- Auth split-screen (Cabinet Grotesk + Satoshi fonts, terracotta accents)
- Sidebar: profile button, friends button (with badge), new-chat, logout, conversation list
- ChatWindow: avatar, presence dot, audio/video call buttons, message bubbles, date separators, typing indicator, image attachments
- CallModal: WebRTC peer connection, mute/camera toggle, end call, mic/camera permission-denied state
- FriendsModal: tabs (Friends / Requests / Find people), add/accept/reject/chat actions
- ProfileModal: avatar upload, name, bio editing

## Test Status
- Backend: 39/39 pytest tests passing (auth, users, conversations, messages, ws, friends, profile)
- Frontend: critical flows verified (register, login, search, friend req, chat, profile)

## Backlog / Future
- P1: Group chat invite/leave UI controls
- P1: Voice messages (audio recording)
- P2: Message reactions (emojis)
- P2: Message edit/delete
- P2: File attachments beyond images (PDF, video)
- P2: Push notifications (browser Notification API)
- P3: End-to-end encryption
- P3: Stories / status updates (per the "social media" future direction)
- P3: Split server.py into routers (auth, users, conversations, messages, friends, ws)
- P3: Sanitize regex in user search (re.escape)
- P3: Pagination for messages endpoint (currently capped at 500)

## Test Credentials
- Admin: admin@example.com / admin123
- Alice: alice@test.com / password123
- Bob: bob@test.com / password123
