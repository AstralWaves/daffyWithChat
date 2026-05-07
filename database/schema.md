# Ember Chat — Database Schema Reference

Database name: **`chat_app_db`** (configurable via `DB_NAME` env var)

All documents use `id` (string UUID) as their primary key. The native `_id` (ObjectId) field is excluded from API responses.

---

## Collection: `users`

Stores all registered users (admin + regular users).

| Field | Type | Notes |
|---|---|---|
| `id` | string (uuid) | Primary key. Used in JWT `sub` claim. |
| `email` | string | Lowercase, unique. |
| `username` | string | Unique, 2–30 chars. |
| `name` | string | Display name. |
| `password_hash` | string | bcrypt hash (`$2b$…`). Never returned in API. |
| `avatar` | string \| null | Base64 data URL (`data:image/...;base64,...`) or null. |
| `bio` | string \| null | Short user bio. |
| `online` | bool | Set true when at least one WebSocket is connected. |
| `last_seen` | string (ISO 8601) | Last connection time. |
| `created_at` | string (ISO 8601) | Registration timestamp. |

**Indexes:** `email` (unique), `username` (unique), `id` (unique)

---

## Collection: `conversations`

A 1-on-1 thread or a group chat. The same collection holds both — distinguished by `is_group`.

| Field | Type | Notes |
|---|---|---|
| `id` | string (uuid) | Primary key. |
| `is_group` | bool | `false` for 1-on-1, `true` for group. |
| `name` | string \| null | Group name (only used when `is_group=true`). |
| `participants` | string[] | Array of user `id`s. Sorted for 1-on-1 to allow uniqueness lookup. |
| `created_by` | string (uuid) | User who created the conversation. |
| `created_at` | string (ISO 8601) | |
| `updated_at` | string (ISO 8601) | Updated whenever a message is sent. Used for sidebar ordering. |

**Indexes:** `participants`, `id` (unique)

---

## Collection: `messages`

Chat messages within a conversation. Supports text and base64-image media.

| Field | Type | Notes |
|---|---|---|
| `id` | string (uuid) | Primary key. |
| `conversation_id` | string (uuid) | FK to `conversations.id`. |
| `sender_id` | string (uuid) | FK to `users.id`. |
| `sender_username` | string | Denormalized for performance. |
| `sender_name` | string | Denormalized for performance. |
| `content` | string | Message text (can be empty if `media` is set). |
| `media` | string \| null | Base64 data URL, currently used for images. |
| `media_type` | string \| null | e.g. `"image"`. Future: `"audio"`, `"video"`, `"file"`. |
| `read_by` | string[] | Array of user `id`s who have read the message. The sender's id is added on insert. |
| `created_at` | string (ISO 8601) | |

**Indexes:** compound `(conversation_id ASC, created_at ASC)`, `id` (unique)

---

## Collection: `friendships`

Bidirectional friendships. Each row represents an established mutual friendship.

| Field | Type | Notes |
|---|---|---|
| `id` | string (uuid) | Primary key. |
| `users` | string[] | Always **sorted** array of two user `id`s. Sorting allows direct equality lookup for any pair. |
| `created_at` | string (ISO 8601) | When the friendship was created. |

**Indexes:** `users`

**Lookup pattern:**
```js
db.friendships.findOne({ users: { $all: [meId, otherId] } })
```

---

## Collection: `friend_requests`

Tracks friend request lifecycle. A request transitions: `pending` → `accepted` (creates a `friendships` row) or `pending` → `rejected`.

| Field | Type | Notes |
|---|---|---|
| `id` | string (uuid) | Primary key. |
| `from_user_id` | string (uuid) | Sender. |
| `to_user_id` | string (uuid) | Recipient. |
| `status` | string | `"pending"` \| `"accepted"` \| `"rejected"`. |
| `created_at` | string (ISO 8601) | |
| `accepted_at` | string (ISO 8601) | Set on accept. |

**Indexes:** compound `(from_user_id, to_user_id)`, `to_user_id`

**Auto-accept:** If user A sends a request to user B while B already has a pending request to A, the request is automatically accepted on both sides — a `friendships` row is created and the pending request is marked `accepted`.

---

## Relationships diagram

```
users  1───┐
           │ (created_by)        ┌─── messages
           ├───── conversations ─┤  (sender_id)
           │   (participants[])  │
           │                     └─── read_by[]
           │
           ├──── friendships (users[])
           │
           └──── friend_requests (from_user_id, to_user_id)
```

---

## ID format

All primary keys (`id`) are RFC-4122 UUIDs (e.g., `e37f1090-238e-4f97-ab02-a48066065af5`).
**Never use MongoDB's internal `_id` (ObjectId) in API responses** — it is not JSON serializable and is always excluded from queries via `{ "_id": 0 }` projection.

---

## Sizing notes

- `password_hash` ≈ 60 bytes
- `avatar` (base64) can be up to ~2 MB per user — consider switching to S3/object storage if you scale
- `media` in messages similarly base64-encoded — capped at 5 MB per message in the frontend
- `messages` collection grows fastest; consider TTL or archival policies for very old conversations
