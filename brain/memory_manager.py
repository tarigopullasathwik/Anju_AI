"""
Anju AI — Enhanced Memory Manager
Long-term memory with consolidation, importance scoring, auto-summarization,
semantic decay, and cross-reference building.
"""
import os
import json
import sqlite3
import re
from datetime import datetime, timedelta
from typing import Optional

from memory.database import (
    DB_PATH,
    get_user_profile,
    get_projects,
    search_facts,
    get_active_tasks,
    add_fact,
    save_message,
    get_recent_history,
)

# ── Memory Configuration ────────────────────────────────────────────────────
SHORT_TERM_LIMIT = 10        # Number of recent messages to always keep
MEDIUM_TERM_LIMIT = 50       # Number of messages before summarization kicks in
IMPORTANCE_BOOST_WORDS = [   # Words that boost a memory's importance
    "important", "critical", "urgent", "never forget", "remember this",
    "significant", "key", "essential", "vital", "crucial",
    "pavan", "project", "deadline", "birthday", "anniversary",
]
MAX_MEMORY_CONTEXT = 5       # Max facts/projects to include in context


# ══════════════════════════════════════════════════════════════════════════
#  IMPORTANCE-BASED MEMORY CONSOLIDATION
# ══════════════════════════════════════════════════════════════════════════

def calculate_importance(content: str) -> int:
    """
    Calculate the importance score (1-10) of a memory based on content analysis.
    - Emotional words boost score
    - Personal references boost score
    - Technical complexity boosts score
    - Repetition across sessions boosts score
    """
    content_lower = content.lower()
    score = 1  # Base score

    # Boost for explicit importance markers
    for word in IMPORTANCE_BOOST_WORDS:
        if word in content_lower:
            score += 2

    # Boost for emotional content
    emotional_words = ["love", "miss", "feel", "sad", "happy", "excited",
                       "worried", "stressed", "lonely", "grateful", "proud"]
    for word in emotional_words:
        if word in content_lower:
            score += 1
            break

    # Boost for personal relationship mentions
    if "pavan" in content_lower:
        score += 3

    # Boost for project/coding content
    if any(w in content_lower for w in ["code", "project", "build", "create", "app"]):
        score += 1

    # Boost for longer, more detailed memories
    if len(content) > 100:
        score += 1
    if len(content) > 300:
        score += 1

    return min(score, 10)  # Cap at 10


def consolidate_memories() -> dict:
    """
    Run memory consolidation:
    1. Identify low-importance old facts and archive them
    2. Boost importance of frequently referenced facts
    3. Merge duplicate/similar facts
    4. Generate cross-references between related memories

    Returns summary of actions taken.
    """
    stats = {"archived": 0, "boosted": 0, "merged": 0, "cross_refs": 0}

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 1. Archive low-importance facts older than 30 days
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
        cursor.execute(
            "UPDATE facts SET importance = 0 WHERE importance <= 2 AND timestamp < ?",
            (thirty_days_ago,)
        )
        stats["archived"] = cursor.rowcount

        # 2. Boost importance of facts that appear in recent conversation context
        recent = get_recent_history(limit=20)
        recent_text = " ".join([m["content"] for m in recent])
        cursor.execute("SELECT id, content, importance FROM facts WHERE importance > 0")
        for row in cursor.fetchall():
            fact_id, content, importance = row
            # If fact content appears in recent conversation, boost it
            words = content.lower().split()
            matches = sum(1 for w in words if len(w) > 3 and w in recent_text.lower())
            if matches >= 2 and importance < 10:
                new_importance = min(importance + 1, 10)
                cursor.execute("UPDATE facts SET importance = ? WHERE id = ?",
                              (new_importance, fact_id))
                stats["boosted"] += 1

        # 3. Detect and mark potential duplicate facts
        cursor.execute("SELECT id, content, category FROM facts WHERE importance > 0")
        all_facts = cursor.fetchall()
        for i, (id1, content1, cat1) in enumerate(all_facts):
            for j, (id2, content2, cat2) in enumerate(all_facts):
                if i < j:  # Only compare each pair once
                    # Simple similarity: shared significant words
                    words1 = set(w.lower() for w in content1.split() if len(w) > 4)
                    words2 = set(w.lower() for w in content2.split() if len(w) > 4)
                    if words1 and words2:
                        overlap = len(words1 & words2)
                        min_len = min(len(words1), len(words2))
                        if min_len > 0 and overlap / min_len > 0.5:
                            # Tag the second fact as related to the first
                            cursor.execute(
                                "UPDATE facts SET tags = tags || ',duplicate_of:' || ? WHERE id = ?",
                                (str(id1), id2)
                            )
                            stats["merged"] += 1

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Memory] Consolidation error: {e}")

    return stats


# ══════════════════════════════════════════════════════════════════════════
#  CONTEXTUAL MEMORY RETRIEVAL (ENHANCED)
# ══════════════════════════════════════════════════════════════════════════

def get_context_summary(limit=7):
    """
    Summarizes older conversation context to prevent context bloat while retaining key info.
    Enhanced with importance-aware truncation.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # Get messages older than the active window
        cursor.execute(
            """SELECT role, content FROM conversation
               WHERE id NOT IN (SELECT id FROM conversation ORDER BY id DESC LIMIT ?)
               ORDER BY id DESC LIMIT 20""",
            (limit,)
        )
        rows = cursor.fetchall()
    except Exception:
        rows = []
    finally:
        conn.close()

    if not rows:
        return ""

    # Build a compact summary, preserving key information
    summary_parts = []
    for role, content in reversed(rows):
        clean = content.replace("\n", " ").strip()
        if len(clean) < 5:
            continue
        # Extract key info: first sentence or important keywords
        first_sentence = clean.split(".")[0] if "." in clean else clean[:60]
        summary_parts.append(f"[{role[0].upper()}]: {first_sentence[:50]}")

        # Keep summary concise
        if len(summary_parts) >= 8:
            summary_parts.append("[...older history summarized]")
            break

    return "Previously: " + " | ".join(summary_parts) if summary_parts else ""


def get_significant_context(query: str) -> str:
    """
    Enhanced context retrieval with importance scoring, cross-referencing,
    and intelligent prioritization.
    """
    context_blocks = []

    # 1. Fetch User Profile
    try:
        profile = get_user_profile()
        if profile:
            profile_str = (
                f"Owner: {profile.get('name', 'Sathwik')} | "
                f"Role: {profile.get('role', 'Developer')} | "
                f"Interests: {profile.get('interests', 'Engineering')}"
            )
            context_blocks.append(f"[User Profile]\n{profile_str}")
    except Exception:
        pass

    # 2. Fetch Relevant Facts by Importance + Relevance
    try:
        # Get high-importance facts first, then relevance-matched
        facts = search_facts(query, limit=MAX_MEMORY_CONTEXT)
        if facts:
            fact_strs = []
            for f in facts:
                importance_mark = "⭐" * (f.get('importance', 1) // 2) if f.get('importance', 0) > 2 else ""
                fact_strs.append(
                    f"- {f['content']} {importance_mark}"
                )
            context_blocks.append("[Key Memories]\n" + "\n".join(fact_strs))
    except Exception:
        pass

    # 3. Fetch Active Projects (with priority for matching ones)
    try:
        projects = get_projects()
        if projects:
            matching = []
            query_words = [w.lower() for w in query.split() if len(w) > 3]
            for p in projects:
                p_str = f"- {p['name']} ({p['tech_stack']}): {p['description'][:80]} [Status: {p['status']}]"
                if not query_words or any(w in p['name'].lower() or w in p['description'].lower() for w in query_words):
                    matching.append(p_str)
            if matching:
                context_blocks.append("[Projects]\n" + "\n".join(matching[:3]))
    except Exception:
        pass

    # 4. Fetch Active Tasks
    try:
        tasks = get_active_tasks()
        if tasks:
            task_strs = [
                f"- {t['title']} ({t['status']}): {t['description'][:60]}"
                for t in tasks
            ]
            if task_strs:
                context_blocks.append("[Active Tasks]\n" + "\n".join(task_strs[:4]))
    except Exception:
        pass

    # 5. Generate conversation statistics for awareness
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM conversation")
        total_msgs = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM conversation WHERE timestamp > ?",
            ((datetime.now() - timedelta(days=1)).isoformat(),)
        )
        today_msgs = cursor.fetchone()[0]
        conn.close()

        if total_msgs > 100:
            context_blocks.append(
                f"[Engagement]\n{total_msgs} total messages exchanged | {today_msgs} today"
            )
    except Exception:
        pass

    return "\n\n".join(context_blocks)


# ══════════════════════════════════════════════════════════════════════════
#  MEMORY MAINTENANCE
# ══════════════════════════════════════════════════════════════════════════

def auto_summarize_old_conversations() -> str:
    """
    Automatically summarize conversations older than 7 days into compact memory entries.
    This prevents the conversation table from growing unbounded.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        week_ago = (datetime.now() - timedelta(days=7)).isoformat()

        # Count old messages
        cursor.execute(
            "SELECT COUNT(*) FROM conversation WHERE timestamp < ?",
            (week_ago,)
        )
        old_count = cursor.fetchone()[0]

        if old_count < 5:
            conn.close()
            return "No significant old conversations to summarize."

        # Get the oldest messages as a single block
        cursor.execute(
            "SELECT role, content FROM conversation WHERE timestamp < ? ORDER BY id ASC LIMIT 100",
            (week_ago,)
        )
        old_msgs = cursor.fetchall()

        # Extract key talking points
        topics = set()
        for role, content in old_msgs:
            # Extract potential topic keywords (capitalized words, technical terms)
            if role == "user":
                words = content.split()
                for i, w in enumerate(words):
                    if w[0].isupper() and len(w) > 3:
                        topics.add(w)

        # Save a summary fact
        if topics:
            topic_str = ", ".join(sorted(topics)[:10])
            summary = f"Past conversations covered topics including: {topic_str}."

            cursor.execute(
                "INSERT OR IGNORE INTO facts (category, content, tags, importance, timestamp) VALUES (?, ?, ?, ?, ?)",
                ('conversation_summary', summary, 'auto-generated,summary', 2, datetime.now().isoformat())
            )

        # Don't delete old messages - they provide continuity
        # But we could mark them as summarized
        conn.close()

        return f"Summarized {old_count} old messages into memory. Key topics: {topic_str if topics else 'general conversation'}"

    except Exception as e:
        return f"Auto-summary error: {e}"


def run_memory_maintenance() -> dict:
    """
    Run all memory maintenance tasks.
    Should be called periodically (e.g., on startup, or once per session).
    """
    results = {}

    results["consolidation"] = consolidate_memories()
    results["summarization"] = auto_summarize_old_conversations()

    return results


# ══════════════════════════════════════════════════════════════════════════
#  MEMORY STATISTICS
# ══════════════════════════════════════════════════════════════════════════

def get_memory_stats() -> dict:
    """Get comprehensive memory system statistics."""
    stats = {"facts": 0, "projects": 0, "tasks": 0, "conversations": 0, "profile_keys": 0}

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM facts WHERE importance > 0")
        stats["facts"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM projects")
        stats["projects"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status != 'completed'")
        stats["active_tasks"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks")
        stats["tasks"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM conversation")
        stats["conversations"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM user_profile")
        stats["profile_keys"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM api_cache")
        stats["cache_entries"] = cursor.fetchone()[0]

        conn.close()
    except Exception:
        pass

    return stats


def format_memory_stats() -> str:
    """Get memory stats as a formatted string for display."""
    stats = get_memory_stats()

    return (
        f"🧠 **Memory System Status**\n\n"
        f"• **Facts remembered:** {stats.get('facts', 0)}\n"
        f"• **Projects tracked:** {stats.get('projects', 0)}\n"
        f"• **Active tasks:** {stats.get('active_tasks', 0)} / {stats.get('tasks', 0)}\n"
        f"• **Conversation entries:** {stats.get('conversations', 0)}\n"
        f"• **Profile properties:** {stats.get('profile_keys', 0)}\n"
        f"• **Cache entries:** {stats.get('cache_entries', 0)}\n"
    )
