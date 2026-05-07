# Ember Chat — MongoDB Database

This folder contains everything you need to set up the database for the project.

## 📁 Files

| File | Purpose |
|---|---|
| `ember_chat.archive` | **Binary dump** (gzipped) of a working database with sample users, conversations, and messages. Restore with one command. |
| `schema.md` | Human-readable schema reference for every collection and field. |
| `../backend/seed_db.py` | **Python script** that creates indexes and inserts sample data fresh. Use this if you want to start clean. |

---

## 🚀 Three ways to set up the database

### Option A — Restore the binary dump (fastest, recommended)

Make sure MongoDB is running on `localhost:27017`, then:

```bash
mongorestore --uri="mongodb://localhost:27017" --gzip --archive=database/ember_chat.archive
```

This restores the `chat_app_db` database with all collections, indexes, and sample data.

### Option B — Run the Python seed script (recommended for development)

```bash
cd backend
source venv/bin/activate              # Windows: venv\Scripts\activate
pip install -r requirements.txt
python seed_db.py                      # add sample data (idempotent — safe to re-run)
python seed_db.py --reset              # WIPE everything and re-seed fresh
```

### Option C — Just start the backend (empty DB)

The backend automatically creates indexes and seeds the admin user on first run. You then register users via the UI.

---

## 👥 Sample login credentials

After restoring or seeding, you can log in with any of these:

| Email | Password | Role |
|---|---|---|
| `admin@example.com` | `admin123` | Admin |
| `alice@test.com` | `password123` | User |
| `bob@test.com` | `password123` | User |
| `carol@test.com` | `password123` | User |
| `diego@test.com` | `password123` | User |

Sample data includes:
- 1 admin + 4 user accounts with bios
- 2 friendships (alice↔bob, alice↔carol)
- 2 pending friend requests (diego→alice, diego→bob)
- 3 conversations with sample messages (incl. one group "Design Squad")

---

## 💾 How to back up your database later

```bash
mongodump --uri="mongodb://localhost:27017" --db=chat_app_db --archive=database/ember_chat.archive --gzip
```

Replace the existing `ember_chat.archive` file to update the snapshot.

---

## 🧹 How to wipe everything

```bash
mongosh mongodb://localhost:27017
> use chat_app_db
> db.dropDatabase()
> exit
```

Or with the Python script:

```bash
python backend/seed_db.py --reset
```
