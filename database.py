import sqlite3
import os
import json
from config import Config
from werkzeug.security import generate_password_hash

def get_db():
    """Get a database connection for the current request context."""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    """Create all tables if they don't exist and handle schema migrations."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT NOT NULL,
        recipe_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(device_id, recipe_id)
    );

    CREATE TABLE IF NOT EXISTS search_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT NOT NULL,
        query TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS preferences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT NOT NULL UNIQUE,
        dietary TEXT DEFAULT '[]',
        cuisines TEXT DEFAULT '[]',
        max_cook_time INTEGER DEFAULT 120,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_fav_device ON favorites(device_id);
    CREATE INDEX IF NOT EXISTS idx_history_device ON search_history(device_id);
    """)
    
    # Migration: Add columns if missing
    cursor.execute("PRAGMA table_info(preferences)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    
    if 'dietary' not in existing_columns:
        cursor.execute("ALTER TABLE preferences ADD COLUMN dietary TEXT DEFAULT '[]'")
    if 'cuisines' not in existing_columns:
        cursor.execute("ALTER TABLE preferences ADD COLUMN cuisines TEXT DEFAULT '[]'")
    if 'max_cook_time' not in existing_columns:
        cursor.execute("ALTER TABLE preferences ADD COLUMN max_cook_time INTEGER DEFAULT 120")
    if 'units' not in existing_columns:
        cursor.execute("ALTER TABLE preferences ADD COLUMN units TEXT DEFAULT 'metric'")
    if 'default_servings' not in existing_columns:
        cursor.execute("ALTER TABLE preferences ADD COLUMN default_servings INTEGER DEFAULT 2")
    if 'notifications' not in existing_columns:
        cursor.execute("ALTER TABLE preferences ADD COLUMN notifications INTEGER DEFAULT 1")

    conn.commit()
    conn.close()

    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs("data", exist_ok=True)

# ── User Management Functions ──
def create_user(username, email, password):
    conn = get_db()
    try:
        pwd_hash = generate_password_hash(password)
        cursor = conn.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, pwd_hash)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_user_by_email(email):
    conn = get_db()
    try:
        return conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    finally:
        conn.close()

def get_user_by_id(user_id):
    conn = get_db()
    try:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    finally:
        conn.close()

def delete_user_account(user_id):
    conn = get_db()
    try:
        device_id = f"user_{user_id}"
        conn.execute("DELETE FROM favorites WHERE device_id = ?", (device_id,))
        conn.execute("DELETE FROM search_history WHERE device_id = ?", (device_id,))
        conn.execute("DELETE FROM preferences WHERE device_id = ?", (device_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting account: {e}")
        return False
    finally:
        conn.close()

# ── Favorites Functions ──
def add_favorite(device_id, recipe_id):
    conn = get_db()
    try:
        conn.execute("INSERT OR IGNORE INTO favorites (device_id, recipe_id) VALUES (?, ?)", (device_id, recipe_id))
        conn.commit()
    finally: conn.close()

def remove_favorite(device_id, recipe_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM favorites WHERE device_id = ? AND recipe_id = ?", (device_id, recipe_id))
        conn.commit()
    finally: conn.close()

def get_favorites(device_id):
    conn = get_db()
    try:
        rows = conn.execute("SELECT recipe_id FROM favorites WHERE device_id = ? ORDER BY created_at DESC", (device_id,)).fetchall()
        return [row["recipe_id"] for row in rows]
    finally: conn.close()

def is_favorited(device_id, recipe_id):
    conn = get_db()
    try:
        row = conn.execute("SELECT 1 FROM favorites WHERE device_id = ? AND recipe_id = ?", (device_id, recipe_id)).fetchone()
        return row is not None
    finally: conn.close()

def clear_all_favorites(device_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM favorites WHERE device_id = ?", (device_id,))
        conn.commit()
    finally: conn.close()

# ── Search History Functions ──
def add_search_history(device_id, query):
    conn = get_db()
    try:
        conn.execute("INSERT INTO search_history (device_id, query) VALUES (?, ?)", (device_id, query))
        conn.commit()
    finally: conn.close()

def get_search_history(device_id, limit=5):
    conn = get_db()
    try:
        rows = conn.execute("SELECT DISTINCT query FROM search_history WHERE device_id = ? ORDER BY created_at DESC LIMIT ?", (device_id, limit)).fetchall()
        return [row["query"] for row in rows]
    finally: conn.close()

def get_search_history_count(device_id):
    conn = get_db()
    try:
        row = conn.execute("SELECT COUNT(*) as count FROM search_history WHERE device_id = ?", (device_id,)).fetchone()
        return row['count'] if row else 0
    finally:
        conn.close()

def clear_search_history(device_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM search_history WHERE device_id = ?", (device_id,))
        conn.commit()
    finally: conn.close()

# ── Preferences Functions ──
def save_preferences(device_id, data):
    conn = get_db()
    try:
        conn.execute("""
        INSERT INTO preferences (device_id, dietary, cuisines, max_cook_time, units, default_servings, notifications)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(device_id) DO UPDATE SET
        dietary = excluded.dietary, cuisines = excluded.cuisines,
        max_cook_time = excluded.max_cook_time, units = excluded.units,
        default_servings = excluded.default_servings, notifications = excluded.notifications,
        updated_at = CURRENT_TIMESTAMP
        """, (
            device_id, 
            data.get("dietary", "[]"), 
            data.get("cuisines", "[]"), 
            data.get("max_cook_time", 120),
            data.get("units", "metric"),
            data.get("default_servings", 2),
            1 if data.get("notifications", True) else 0
        ))
        conn.commit()
    finally: conn.close()

def get_preferences(device_id):
    conn = get_db()
    try:
        row = conn.execute("SELECT dietary, cuisines, max_cook_time, units, default_servings, notifications FROM preferences WHERE device_id = ?", (device_id,)).fetchone()
        if row:
            return {
                "dietary": json.loads(row["dietary"]) if row["dietary"] else [],
                "cuisines": json.loads(row["cuisines"]) if row["cuisines"] else [],
                "max_cook_time": row["max_cook_time"] or 120,
                "units": row["units"] or "metric",
                "default_servings": row["default_servings"] or 2,
                "notifications": bool(row["notifications"]) if row["notifications"] is not None else True
            }
        return {"dietary": [], "cuisines": [], "max_cook_time": 120, "units": "metric", "default_servings": 2, "notifications": True}
    finally:
        conn.close()
