# Test Credentials

## Admin
- Email: `admin@example.com`
- Password: `admin123`
- Username: `admin`

## Test Users
- Email: `alice@test.com` | Password: `password123` | Username: `alice`
- Email: `bob@test.com` | Password: `password123` | Username: `bob`

## Auth Endpoints
- `POST /api/auth/register` — register new user (email, username, name?, password)
- `POST /api/auth/login` — login (email, password)
- `POST /api/auth/logout` — logout (clears cookie)
- `GET /api/auth/me` — get current user (requires auth)

## How to Auth
- Token is returned in JSON response and also set as httpOnly cookie `access_token`
- Bearer auth: `Authorization: Bearer <token>`
- Cookie is also sent automatically

## WebSocket
- URL: `wss://<host>/api/ws?token=<jwt_token>`
- Used for: real-time messages, presence, typing indicators, read receipts, WebRTC signaling
