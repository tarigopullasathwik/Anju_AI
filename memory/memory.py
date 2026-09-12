import os
from memory.database import (
    upsert_user_profile,
    get_user_profile,
    add_or_update_project,
    get_projects,
    add_fact,
    search_facts,
    add_or_update_task,
    get_active_tasks
)

def remember_fact(user_input: str):
    """
    Parses 'Remember that X is Y' and stores it in SQLite.
    Expected input format: 'Remember that my birthday is May 5th'
    """
    fact = user_input
    if "remember that" in user_input.lower():
        fact = user_input.lower().split("remember that")[-1].strip()

    # Auto-classify category
    category = "general"
    tags = "remembered"

    fact_lower = fact.lower()
    if any(w in fact_lower for w in ["pavan", "relationship", "friend"]):
        category = "relationship"
        tags = "pavan,personal,relationship"
    elif any(w in fact_lower for w in ["code", "programming", "python", "js", "html", "css", "database"]):
        category = "coding"
        tags = "technical,coding,preference"
    elif any(w in fact_lower for w in ["project", "build", "create", "make"]):
        category = "projects"
        tags = "projects,tracking"
    elif any(w in fact_lower for w in ["task", "todo", "finish", "complete"]):
        category = "tasks"
        tags = "tasks,todo"

    add_fact(category, fact, tags=tags, importance=3)
    return f"Got it. I've recorded that {fact} in my persistent memory registry."

def get_owner_identity():
    """Returns the profile of the owner, Sathwik, merged with SQLite overrides."""
    default_profile = {
        "name": "Sathwik",
        "role": "Engineering Student",
        "relation": "Creator of Anju AI",
        "description": "Sathwik is an engineering student and the visionary behind Anju AI. He designed me to be his personal companion and a powerful assistant."
    }
    try:
        db_profile = get_user_profile()
        if db_profile and "name" in db_profile:
            default_profile.update(db_profile)
    except Exception:
        pass
    return default_profile

def handle_identity_query(query: str):
    """Checks if a query is about the user's or the AI's identity."""
    q = query.lower()
    owner = get_owner_identity()

    if any(word in q for word in ["who am i", "what am i", "my name", "who is sathwik"]):
        return f"You are {owner['name']}, an {owner['role']} and the creator of Anju AI. You're the one who built my brain!"

    if any(word in q for word in ["who are you", "what are you", "who is anju", "your creator", "who made you", "who built you"]):
        return f"I am Anju, your personal AI assistant. I was created by {owner['name']}, a talented {owner['role']}, to assist and accompany him."

    return None

def get_memory(query: str):
    """
    Searches SQLite structured facts for a given query, returning context-aware matches.
    """
    try:
        matches = search_facts(query, limit=4)
        if not matches:
            return "I don't know much yet. You haven't told me to remember anything."
        fact_strings = [m["content"] for m in matches]
        return "Here is what I know: " + ", ".join(fact_strings)
    except Exception as e:
        print(f"[Memory] Search error: {e}")
        return "I'm sorry, I had trouble searching my memory right now."
