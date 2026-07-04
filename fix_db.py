"""
One-time database fix: recreate the preferences table with correct schema.
Run once, then delete this file.
"""
import sqlite3
import os

DB_PATH = "cooking_app.db"

if not os.path.exists(DB_PATH):
    print("No database found. Nothing to fix — init_db() will create it on first run.")
    exit(0)

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA journal_mode=WAL")
cursor = conn.cursor()

# Check if preferences table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='preferences'")
exists = cursor.fetchone()

if exists:
    # Check current columns
    cursor.execute("PRAGMA table_info(preferences)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Current preferences columns: {columns}")

    if "key" not in columns or "value" not in columns:
        print("Schema is wrong. Dropping and recreating preferences table...")
        cursor.execute("DROP TABLE preferences")
        cursor.execute("""
            CREATE TABLE preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(device_id, key)
            )
        """)
        conn.commit()
        print("preferences table recreated successfully.")
    else:
        print("preferences table schema is already correct. No changes needed.")
else:
    print("preferences table doesn't exist yet. Creating it...")
    cursor.execute("""
        CREATE TABLE preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(device_id, key)
        )
    """)
    conn.commit()
    print("preferences table created.")

# Also verify users table exists (for the new auth feature)
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
if not cursor.fetchone():
    print("users table missing. Creating it...")
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT DEFAULT '',
            bio TEXT DEFAULT '',
            avatar_color TEXT DEFAULT '#ED8F47',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    print("users table created.")
else:
    print("users table already exists.")

conn.close()
print("\nDone! You can now restart your Flask app.")