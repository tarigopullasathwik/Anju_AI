"""Persistent assistant memory with Neon PostgreSQL in deployment and SQLite locally."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

DB_PATH = os.path.join(os.path.dirname(__file__), "anju_memory.db")
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")


def _postgres():
    if not DATABASE_URL:
        return None
    try:
        import psycopg
        return psycopg.connect(DATABASE_URL, connect_timeout=8)
    except Exception as exc:
        print(f"[DB] Neon unavailable, using local fallback: {exc}")
        return None


def _conn():
    return _postgres() or sqlite3.connect(DB_PATH, timeout=10)


def _pg(conn) -> bool:
    return conn.__class__.__module__.startswith("psycopg")


def _exec(cur, query: str, params=()):
    if cur.connection.__class__.__module__.startswith("psycopg"):
        query = query.replace("?", "%s")
    return cur.execute(query, params)


def _commit_close(conn):
    conn.commit()
    conn.close()


def init_db():
    conn = _conn()
    cur = conn.cursor()
    if _pg(conn):
        statements = [
            "CREATE TABLE IF NOT EXISTS conversation (id BIGSERIAL PRIMARY KEY, timestamp TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS user_profile (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)",
            "CREATE TABLE IF NOT EXISTS projects (id BIGSERIAL PRIMARY KEY, name TEXT UNIQUE, description TEXT, tech_stack TEXT, status TEXT, tasks TEXT, updated_at TEXT)",
            "CREATE TABLE IF NOT EXISTS facts (id BIGSERIAL PRIMARY KEY, category TEXT, content TEXT UNIQUE, tags TEXT, importance INTEGER DEFAULT 1, timestamp TEXT)",
            "CREATE TABLE IF NOT EXISTS tasks (id BIGSERIAL PRIMARY KEY, title TEXT UNIQUE, description TEXT, status TEXT, context TEXT, updated_at TEXT)",
        ]
    else:
        statements = [
            "CREATE TABLE IF NOT EXISTS conversation (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, role TEXT, content TEXT)",
            "CREATE TABLE IF NOT EXISTS user_profile (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)",
            "CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, description TEXT, tech_stack TEXT, status TEXT, tasks TEXT, updated_at TEXT)",
            "CREATE TABLE IF NOT EXISTS facts (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, content TEXT UNIQUE, tags TEXT, importance INTEGER DEFAULT 1, timestamp TEXT)",
            "CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT UNIQUE, description TEXT, status TEXT, context TEXT, updated_at TEXT)",
        ]
    for statement in statements:
        cur.execute(statement)
    if not _pg(conn):
        _exec(cur, "INSERT OR IGNORE INTO user_profile (key,value,updated_at) VALUES (?,?,?)", ("name", "Sathwik", _now()))
    else:
        _exec(cur, "INSERT INTO user_profile (key,value,updated_at) VALUES (?,?,?) ON CONFLICT (key) DO NOTHING", ("name", "Sathwik", _now()))
    _commit_close(conn)


def _now():
    return datetime.now(timezone.utc).isoformat()


def save_message(role: str, content: str):
    init_db(); conn = _conn(); cur = conn.cursor()
    _exec(cur, "INSERT INTO conversation (timestamp,role,content) VALUES (?,?,?)", (_now(), role, content)); _commit_close(conn)


def get_recent_history(limit=10):
    init_db(); conn = _conn(); cur = conn.cursor()
    _exec(cur, "SELECT role,content FROM conversation ORDER BY id DESC LIMIT ?", (int(limit),))
    rows = cur.fetchall(); conn.close()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


def upsert_user_profile(key: str, value: str):
    init_db(); conn = _conn(); cur = conn.cursor()
    if _pg(conn):
        _exec(cur, "INSERT INTO user_profile (key,value,updated_at) VALUES (?,?,?) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value,updated_at=EXCLUDED.updated_at", (key, value, _now()))
    else:
        _exec(cur, "INSERT OR REPLACE INTO user_profile (key,value,updated_at) VALUES (?,?,?)", (key, value, _now()))
    _commit_close(conn)


def get_user_profile() -> dict:
    init_db(); conn = _conn(); cur = conn.cursor(); cur.execute("SELECT key,value FROM user_profile")
    rows = cur.fetchall(); conn.close(); return {r[0]: r[1] for r in rows}


def add_or_update_project(name: str, description=None, tech_stack=None, status="active", tasks=None):
    init_db(); conn = _conn(); cur = conn.cursor()
    if _pg(conn):
        _exec(cur, "INSERT INTO projects (name,description,tech_stack,status,tasks,updated_at) VALUES (?,?,?,?,?,?) ON CONFLICT (name) DO UPDATE SET description=COALESCE(EXCLUDED.description,projects.description),tech_stack=COALESCE(EXCLUDED.tech_stack,projects.tech_stack),status=EXCLUDED.status,tasks=COALESCE(EXCLUDED.tasks,projects.tasks),updated_at=EXCLUDED.updated_at", (name, description or "", tech_stack or "", status, tasks or "", _now()))
    else:
        _exec(cur, "INSERT OR REPLACE INTO projects (name,description,tech_stack,status,tasks,updated_at) VALUES (?,?,?,?,?,?)", (name, description or "", tech_stack or "", status, tasks or "", _now()))
    _commit_close(conn)


def get_projects() -> list:
    init_db(); conn = _conn(); cur = conn.cursor(); cur.execute("SELECT name,description,tech_stack,status,tasks,updated_at FROM projects ORDER BY updated_at DESC"); rows = cur.fetchall(); conn.close()
    return [{"name":r[0],"description":r[1],"tech_stack":r[2],"status":r[3],"tasks":r[4],"updated_at":r[5]} for r in rows]


def add_fact(category: str, content: str, tags="", importance=1):
    init_db(); conn = _conn(); cur = conn.cursor()
    if _pg(conn):
        _exec(cur, "INSERT INTO facts (category,content,tags,importance,timestamp) VALUES (?,?,?,?,?) ON CONFLICT (content) DO UPDATE SET category=EXCLUDED.category,tags=EXCLUDED.tags,importance=EXCLUDED.importance,timestamp=EXCLUDED.timestamp", (category, content, tags, importance, _now()))
    else:
        _exec(cur, "INSERT OR REPLACE INTO facts (category,content,tags,importance,timestamp) VALUES (?,?,?,?,?)", (category, content, tags, importance, _now()))
    _commit_close(conn)


def search_facts(query: str, limit=6) -> list:
    init_db(); conn = _conn(); cur = conn.cursor(); cur.execute("SELECT category,content,tags,importance FROM facts"); rows = cur.fetchall(); conn.close()
    words = [w.lower() for w in query.split() if len(w) > 3]; scored=[]
    for category, content, tags, importance in rows:
        score = sum(2 for w in words if w in f"{category} {content} {tags}".lower())
        if score or not words: scored.append((score + int(importance or 0), category, content, tags, importance))
    scored.sort(reverse=True); return [{"category":r[1],"content":r[2],"tags":r[3],"importance":r[4]} for r in scored[:int(limit)]]


def add_or_update_task(title: str, description="", status="pending", context=""):
    init_db(); conn = _conn(); cur = conn.cursor()
    if _pg(conn):
        _exec(cur, "INSERT INTO tasks (title,description,status,context,updated_at) VALUES (?,?,?,?,?) ON CONFLICT (title) DO UPDATE SET description=EXCLUDED.description,status=EXCLUDED.status,context=EXCLUDED.context,updated_at=EXCLUDED.updated_at", (title, description, status, context, _now()))
    else:
        _exec(cur, "INSERT OR REPLACE INTO tasks (title,description,status,context,updated_at) VALUES (?,?,?,?,?)", (title, description, status, context, _now()))
    _commit_close(conn)


def get_active_tasks() -> list:
    init_db(); conn = _conn(); cur = conn.cursor(); cur.execute("SELECT title,description,status,context,updated_at FROM tasks WHERE status != 'completed' ORDER BY updated_at DESC"); rows = cur.fetchall(); conn.close()
    return [{"title":r[0],"description":r[1],"status":r[2],"context":r[3],"updated_at":r[4]} for r in rows]


try:
    init_db()
except Exception as exc:
    print(f"[DB] Initialization deferred: {exc}")
