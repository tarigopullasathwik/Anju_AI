import sqlite3
import os
import json
from datetime import datetime

# Define database path relative to this file
DB_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(DB_DIR, "anju_memory.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Conversation History (existing)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            role TEXT,
            content TEXT
        )
    ''')

    # 2. User Profile (new)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profile (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        )
    ''')

    # 3. Projects (new)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            description TEXT,
            tech_stack TEXT,
            status TEXT,
            tasks TEXT,
            updated_at TEXT
        )
    ''')

    # 4. Structured Facts (new)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            content TEXT UNIQUE,
            tags TEXT,
            importance INTEGER DEFAULT 1,
            timestamp TEXT
        )
    ''')

    # 5. Ongoing Tasks (new)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            status TEXT,
            context TEXT,
            updated_at TEXT
        )
    ''')

    # Insert default Sathwik profile if empty
    cursor.execute("SELECT COUNT(*) FROM user_profile WHERE key = 'name'")
    if cursor.fetchone()[0] == 0:
        now = datetime.now().isoformat()
        cursor.execute("INSERT OR REPLACE INTO user_profile (key, value, updated_at) VALUES ('name', 'Sathwik', ?)", (now,))
        cursor.execute("INSERT OR REPLACE INTO user_profile (key, value, updated_at) VALUES ('role', 'Engineering Student & Developer', ?)", (now,))
        cursor.execute("INSERT OR REPLACE INTO user_profile (key, value, updated_at) VALUES ('relation', 'Creator of Anju AI', ?)", (now,))
        cursor.execute("INSERT OR REPLACE INTO user_profile (key, value, updated_at) VALUES ('interests', 'Software engineering, cybersecurity, AI companions, high-tech systems', ?)", (now,))
        cursor.execute("INSERT OR REPLACE INTO user_profile (key, value, updated_at) VALUES ('communication_style', 'Warm, supportive, Jarvis-level immersive, technical, personal', ?)", (now,))
        cursor.execute("INSERT OR REPLACE INTO user_profile (key, value, updated_at) VALUES ('coding_preferences', 'Python, JavaScript, SQLite, HTML5, clean architectural design', ?)", (now,))

    # Insert default facts if empty
    cursor.execute("SELECT COUNT(*) FROM facts")
    if cursor.fetchone()[0] == 0:
        now = datetime.now().isoformat()
        cursor.execute(
            "INSERT OR IGNORE INTO facts (category, content, tags, importance, timestamp) VALUES (?, ?, ?, ?, ?)",
            ('personal', "Pavan holds a deeply significant, unique, and special place in Sathwik's heart.", 'pavan,relationship,important', 5, now)
        )
        cursor.execute(
            "INSERT OR IGNORE INTO facts (category, content, tags, importance, timestamp) VALUES (?, ?, ?, ?, ?)",
            ('personal', "Sathwik built Anju AI to be a highly realistic, emotionally aware, pro-level digital companion.", 'anju,purpose,creator', 4, now)
        )

    conn.commit()
    conn.close()

# ── Message Logs ──────────────────────────────────────────────────────────────
def save_message(role: str, content: str):
    """Save a message to the database."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conversation (timestamp, role, content) VALUES (?, ?, ?)",
        (datetime.now().isoformat(), role, content)
    )
    conn.commit()
    conn.close()

def get_recent_history(limit=10):
    """Retrieve the most recent conversation history."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM conversation ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"role": role, "content": content} for role, content in reversed(rows)]

# ── User Profile Helpers ──────────────────────────────────────────────────────
def upsert_user_profile(key: str, value: str):
    """Sets or updates a profile value for the owner."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO user_profile (key, value, updated_at) VALUES (?, ?, ?)",
        (key, value, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def get_user_profile() -> dict:
    """Retrieves all user profile entries as a dictionary."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM user_profile")
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

# ── Project Helpers ───────────────────────────────────────────────────────────
def add_or_update_project(name: str, description: str = None, tech_stack: str = None, status: str = 'active', tasks: str = None):
    """Adds a new project or updates an existing one."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if exists
    cursor.execute("SELECT id, description, tech_stack, status, tasks FROM projects WHERE name = ?", (name,))
    row = cursor.fetchone()

    now = datetime.now().isoformat()
    if row:
        # Update existing
        desc = description if description is not None else row[1]
        tech = tech_stack if tech_stack is not None else row[2]
        stat = status if status is not None else row[3]
        tsks = tasks if tasks is not None else row[4]
        cursor.execute(
            "UPDATE projects SET description = ?, tech_stack = ?, status = ?, tasks = ?, updated_at = ? WHERE name = ?",
            (desc, tech, stat, tsks, now, name)
        )
    else:
        # Insert new
        cursor.execute(
            "INSERT INTO projects (name, description, tech_stack, status, tasks, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (name, description or "", tech_stack or "", status, tasks or "", now)
        )
    conn.commit()
    conn.close()

def get_projects() -> list:
    """Retrieves all projects from registry."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, description, tech_stack, status, tasks, updated_at FROM projects ORDER BY updated_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "name": r[0],
            "description": r[1],
            "tech_stack": r[2],
            "status": r[3],
            "tasks": r[4],
            "updated_at": r[5]
        } for r in rows
    ]

# ── Structured Fact Helpers ───────────────────────────────────────────────────
def add_fact(category: str, content: str, tags: str = "", importance: int = 1):
    """Saves a structured fact to the database."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR REPLACE INTO facts (category, content, tags, importance, timestamp) VALUES (?, ?, ?, ?, ?)",
            (category, content, tags, importance, datetime.now().isoformat())
        )
        conn.commit()
    except Exception as e:
        print(f"[DB] Error adding fact: {e}")
    conn.close()

def search_facts(query: str, limit: int = 6) -> list:
    """Performs an advanced dynamic keyword match on structured facts."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Split query into keywords
    words = [w.lower().strip() for w in query.split() if len(w.strip()) > 3]
    if not words:
        # Default fallback: get high importance facts
        cursor.execute("SELECT category, content, tags, importance FROM facts ORDER BY importance DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [{"category": r[0], "content": r[1], "tags": r[2], "importance": r[3]} for r in rows]

    # Match facts that contain any keyword in content, tags, or category
    cursor.execute("SELECT category, content, tags, importance FROM facts")
    all_facts = cursor.fetchall()
    conn.close()

    scored_facts = []
    for category, content, tags, importance in all_facts:
        score = 0
        fact_str = f"{category} {content} {tags}".lower()

        # Add to score based on keyword matches
        for w in words:
            if w in fact_str:
                score += 2

        # Scale score with importance multiplier
        if score > 0:
            score += importance
            scored_facts.append((score, category, content, tags, importance))

    # Sort by score descending
    scored_facts.sort(key=lambda x: x[0], reverse=True)

    return [
        {
            "category": f[1],
            "content": f[2],
            "tags": f[3],
            "importance": f[4]
        } for f in scored_facts[:limit]
    ]

# ── Task Helpers ──────────────────────────────────────────────────────────────
def add_or_update_task(title: str, description: str = "", status: str = 'pending', context: str = ""):
    """Adds a new ongoing task or updates an existing one by title."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, description, status, context FROM tasks WHERE title = ?", (title,))
    row = cursor.fetchone()

    now = datetime.now().isoformat()
    if row:
        desc = description if description else row[1]
        stat = status if status else row[2]
        ctx = context if context else row[3]
        cursor.execute(
            "UPDATE tasks SET description = ?, status = ?, context = ?, updated_at = ? WHERE title = ?",
            (desc, stat, ctx, now, title)
        )
    else:
        cursor.execute(
            "INSERT INTO tasks (title, description, status, context, updated_at) VALUES (?, ?, ?, ?, ?)",
            (title, description, status, context, now)
        )
    conn.commit()
    conn.close()

def get_active_tasks() -> list:
    """Gets all pending or active tasks."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT title, description, status, context, updated_at FROM tasks WHERE status != 'completed' ORDER BY updated_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "title": r[0],
            "description": r[1],
            "status": r[2],
            "context": r[3],
            "updated_at": r[4]
        } for r in rows
    ]
