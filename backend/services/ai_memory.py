"""
Visor AI — Persistent Memory Service
Maintains cross-session context so the AI remembers user preferences,
concerns, goals discussed, and open questions across conversations.

Memory is extracted after each conversation using gpt-4o-mini (cheap)
and stored in MongoDB. On each new conversation, relevant memory
is injected into context.
"""
import asyncio
import logging
from datetime import datetime, timezone

from database import db
from config import EMERGENT_LLM_KEY

logger = logging.getLogger(__name__)

MEMORY_COLLECTION = "user_ai_memory"

# The extraction prompt — asks gpt-4o-mini to extract structured memory
MEMORY_EXTRACTION_PROMPT = """You are a memory extraction system for a financial AI assistant. 
Analyze the conversation below and extract ONLY new, meaningful information about the user.

Rules:
- Extract financial topics discussed, user concerns, preferences, and open questions
- Be concise — each item should be 1 short sentence max
- Skip generic/obvious info (e.g., "user asked about finance")
- Only extract things worth remembering for FUTURE conversations
- Return valid JSON only, no markdown

Return this JSON structure:
{
  "topics": ["topic1", "topic2"],
  "concerns": ["concern1"],
  "preferences": ["preference1"],
  "open_questions": ["question1"],
  "financial_facts": ["fact1"],
  "language_preference": "hinglish|english|hindi|tamil|telugu|bengali|other|null"
}

If nothing meaningful to extract, return: {"topics":[],"concerns":[],"preferences":[],"open_questions":[],"financial_facts":[],"language_preference":null}
"""


async def extract_and_store_memory(user_id: str, user_message: str, ai_response: str):
    """
    Extract memory from a conversation turn and merge into persistent storage.
    Runs in background — never blocks the main response.
    """
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        import json

        conversation = f"User: {user_message}\nAI: {ai_response[:500]}"

        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"memory-extract-{user_id}",
            system_message=MEMORY_EXTRACTION_PROMPT,
        )
        chat.with_model("openai", "gpt-4o-mini")

        raw = await chat.send_message(UserMessage(text=conversation))

        # Parse JSON from response
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        extracted = json.loads(raw)

        # Merge into existing memory
        await _merge_memory(user_id, extracted)

    except Exception as e:
        logger.warning(f"Memory extraction failed for {user_id}: {e}")


async def _merge_memory(user_id: str, new_data: dict):
    """Merge newly extracted memory with existing user memory."""
    existing = await db[MEMORY_COLLECTION].find_one(
        {"user_id": user_id}, {"_id": 0}
    )

    if not existing:
        existing = {
            "user_id": user_id,
            "topics": [],
            "concerns": [],
            "preferences": [],
            "open_questions": [],
            "financial_facts": [],
            "language_preference": None,
            "conversation_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    # Merge lists — deduplicate by keeping only unique items (max 20 each)
    for field in ["topics", "concerns", "preferences", "open_questions", "financial_facts"]:
        existing_items = existing.get(field, [])
        new_items = new_data.get(field, [])
        # Add new items that aren't already present (case-insensitive comparison)
        existing_lower = {item.lower() for item in existing_items}
        for item in new_items:
            if item and item.lower() not in existing_lower:
                existing_items.append(item)
                existing_lower.add(item.lower())
        # Keep only last 20 items (most recent = most relevant)
        existing[field] = existing_items[-20:]

    # Update language preference if detected
    lang = new_data.get("language_preference")
    if lang and lang != "null":
        existing["language_preference"] = lang

    existing["conversation_count"] = existing.get("conversation_count", 0) + 1
    existing["updated_at"] = datetime.now(timezone.utc).isoformat()

    await db[MEMORY_COLLECTION].update_one(
        {"user_id": user_id},
        {"$set": existing},
        upsert=True,
    )


async def get_memory_context(user_id: str) -> str:
    """
    Retrieve formatted memory context string for injection into AI prompt.
    Returns empty string if no memory exists.
    """
    memory = await db[MEMORY_COLLECTION].find_one(
        {"user_id": user_id}, {"_id": 0}
    )

    if not memory:
        return ""

    parts = []

    topics = memory.get("topics", [])
    if topics:
        parts.append(f"Topics discussed before: {', '.join(topics[-10:])}")

    concerns = memory.get("concerns", [])
    if concerns:
        parts.append(f"User concerns: {', '.join(concerns[-5:])}")

    preferences = memory.get("preferences", [])
    if preferences:
        parts.append(f"User preferences: {', '.join(preferences[-5:])}")

    open_qs = memory.get("open_questions", [])
    if open_qs:
        parts.append(f"Open questions from past: {', '.join(open_qs[-3:])}")

    facts = memory.get("financial_facts", [])
    if facts:
        parts.append(f"Known facts: {', '.join(facts[-8:])}")

    lang = memory.get("language_preference")
    if lang and lang != "null":
        parts.append(f"Preferred language: {lang}")

    conv_count = memory.get("conversation_count", 0)
    if conv_count > 0:
        parts.append(f"Conversations so far: {conv_count}")

    if not parts:
        return ""

    return "\n\nUSER MEMORY (from past conversations — use this to personalize):\n" + "\n".join(f"- {p}" for p in parts)


async def get_user_memory(user_id: str) -> dict:
    """Get raw memory document for API response."""
    memory = await db[MEMORY_COLLECTION].find_one(
        {"user_id": user_id}, {"_id": 0}
    )
    return memory or {
        "user_id": user_id,
        "topics": [],
        "concerns": [],
        "preferences": [],
        "open_questions": [],
        "financial_facts": [],
        "language_preference": None,
        "conversation_count": 0,
    }


async def clear_user_memory(user_id: str) -> bool:
    """Delete all memory for a user."""
    result = await db[MEMORY_COLLECTION].delete_one({"user_id": user_id})
    return result.deleted_count > 0
