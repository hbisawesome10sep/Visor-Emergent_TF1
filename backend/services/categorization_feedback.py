"""
Visor — Categorization Feedback Loop
Tracks user corrections to transaction categories and applies them
automatically on future imports for the same merchant/pattern.
"""
import logging
import re
from datetime import datetime, timezone

from database import db

logger = logging.getLogger(__name__)

OVERRIDES_COLLECTION = "category_overrides"


async def record_category_override(user_id: str, old_category: str, new_category: str, description: str):
    """
    Record a user's category correction. Called when a transaction is updated.
    Extracts a merchant pattern from the description for future matching.
    """
    pattern = _extract_merchant_pattern(description)
    if not pattern:
        return

    existing = await db[OVERRIDES_COLLECTION].find_one({
        "user_id": user_id,
        "pattern": pattern,
    })

    if existing:
        # Update existing override with new category and increment count
        await db[OVERRIDES_COLLECTION].update_one(
            {"user_id": user_id, "pattern": pattern},
            {
                "$set": {
                    "new_category": new_category,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                "$inc": {"count": 1},
            },
        )
    else:
        await db[OVERRIDES_COLLECTION].insert_one({
            "user_id": user_id,
            "pattern": pattern,
            "old_category": old_category,
            "new_category": new_category,
            "sample_description": description[:200],
            "count": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

    logger.info(f"Category override recorded: '{pattern}' → {new_category} for user {user_id}")


def _extract_merchant_pattern(description: str) -> str:
    """
    Extract a reusable merchant pattern from a transaction description.
    E.g., "UPI - SWIGGY DELIVERY - 12345" → "swiggy"
    """
    desc = description.lower()

    # Remove common bank statement prefixes
    for prefix in [
        "upi -", "upi/", "neft -", "neft/", "imps -", "imps/",
        "pos -", "pos/", "ecom -", "ecom/", "atm -", "atm/",
        "by transfer-", "to transfer-", "nwd-", "neft cr-",
        "bil/", "ach d-", "ach/",
    ]:
        desc = desc.replace(prefix, "")

    # Remove trailing reference numbers, dates, transaction IDs
    desc = re.sub(r'\b\d{6,}\b', '', desc)
    desc = re.sub(r'\b[a-f0-9]{12,}\b', '', desc)
    desc = re.sub(r'\d{2}[/.\-]\d{2}[/.\-]\d{2,4}', '', desc)

    # Remove common noise words
    for noise in ["pvt", "ltd", "private", "limited", "india", "payment", "transfer", "(via cred)"]:
        desc = desc.replace(noise, "")

    # Clean up and take meaningful part
    desc = re.sub(r'\s+', ' ', desc).strip()
    words = desc.split()

    # Take first 1-2 meaningful words as pattern
    meaningful = [w for w in words if len(w) > 2 and not w.isdigit()]
    if meaningful:
        return " ".join(meaningful[:2]).strip()

    return ""


async def apply_user_overrides(user_id: str, description: str, current_category: str) -> str:
    """
    Check if user has a category override for this transaction description.
    Returns the override category if matched, otherwise returns current_category.
    """
    pattern = _extract_merchant_pattern(description)
    if not pattern:
        return current_category

    override = await db[OVERRIDES_COLLECTION].find_one({
        "user_id": user_id,
        "pattern": pattern,
    }, {"_id": 0})

    if override:
        logger.info(f"Applied user override: '{pattern}' → {override['new_category']}")
        return override["new_category"]

    return current_category


async def get_user_overrides(user_id: str) -> list:
    """Get all category overrides for a user."""
    overrides = await db[OVERRIDES_COLLECTION].find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("count", -1).to_list(200)
    return overrides


async def delete_user_override(user_id: str, pattern: str) -> bool:
    """Delete a specific override."""
    result = await db[OVERRIDES_COLLECTION].delete_one({
        "user_id": user_id,
        "pattern": pattern,
    })
    return result.deleted_count > 0


async def clear_user_overrides(user_id: str) -> int:
    """Delete all overrides for a user."""
    result = await db[OVERRIDES_COLLECTION].delete_many({"user_id": user_id})
    return result.deleted_count
