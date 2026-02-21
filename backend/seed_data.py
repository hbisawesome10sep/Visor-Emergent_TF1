from database import db
from auth import hash_password
from encryption import generate_user_dek, encrypt_field
from config import USER_SENSITIVE_FIELDS
from datetime import datetime, timezone
import uuid
import logging

logger = logging.getLogger(__name__)


async def seed_demo_data():
    """Seed demo user data for testing."""
    demo1 = await db.users.find_one({"email": "rajesh@visor.demo"}, {"_id": 0})
    if demo1:
        if not demo1.get("encryption_key"):
            dek = generate_user_dek()
            updates = {"encryption_key": dek}
            for field in USER_SENSITIVE_FIELDS:
                val = demo1.get(field, "")
                if val and not val.startswith("ENC:"):
                    updates[field] = encrypt_field(val, dek)
            await db.users.update_one({"email": "rajesh@visor.demo"}, {"$set": updates})
            logger.info("Migrated demo user rajesh with encryption key")
        else:
            dek = demo1["encryption_key"]
            updates = {}
            for field in USER_SENSITIVE_FIELDS:
                val = demo1.get(field, "")
                if val and not val.startswith("ENC:"):
                    updates[field] = encrypt_field(val, dek)
            if updates:
                await db.users.update_one({"email": "rajesh@visor.demo"}, {"$set": updates})
                logger.info("Migrated demo user rajesh full_name/dob encryption")
        
        demo2 = await db.users.find_one({"email": "priya@visor.demo"}, {"_id": 0})
        if demo2 and not demo2.get("encryption_key"):
            dek2 = generate_user_dek()
            updates2 = {"encryption_key": dek2}
            for field in USER_SENSITIVE_FIELDS:
                val = demo2.get(field, "")
                if val and not val.startswith("ENC:"):
                    updates2[field] = encrypt_field(val, dek2)
            await db.users.update_one({"email": "priya@visor.demo"}, {"$set": updates2})
            logger.info("Migrated demo user priya with encryption key")
        elif demo2 and demo2.get("encryption_key"):
            dek2 = demo2["encryption_key"]
            updates2 = {}
            for field in USER_SENSITIVE_FIELDS:
                val = demo2.get(field, "")
                if val and not val.startswith("ENC:"):
                    updates2[field] = encrypt_field(val, dek2)
            if updates2:
                await db.users.update_one({"email": "priya@visor.demo"}, {"$set": updates2})
                logger.info("Migrated demo user priya full_name/dob encryption")
        logger.info("Demo data already exists, skipping seed")
        return

    logger.info("Seeding demo data...")
    now = datetime.now(timezone.utc).isoformat()

    user1_id = str(uuid.uuid4())
    user1_dek = generate_user_dek()
    await db.users.insert_one({
        "id": user1_id,
        "email": "rajesh@visor.demo",
        "password": hash_password("Demo@123"),
        "full_name": encrypt_field("Rajesh Kumar", user1_dek),
        "dob": encrypt_field("1995-05-15", user1_dek),
        "pan": encrypt_field("ABCDE1234F", user1_dek),
        "aadhaar": encrypt_field("123456789012", user1_dek),
        "encryption_key": user1_dek,
        "created_at": now,
    })

    user2_id = str(uuid.uuid4())
    user2_dek = generate_user_dek()
    await db.users.insert_one({
        "id": user2_id,
        "email": "priya@visor.demo",
        "password": hash_password("Demo@456"),
        "full_name": encrypt_field("Priya Sharma", user2_dek),
        "dob": encrypt_field("1990-08-22", user2_dek),
        "pan": encrypt_field("FGHIJ5678K", user2_dek),
        "aadhaar": encrypt_field("987654321098", user2_dek),
        "encryption_key": user2_dek,
        "created_at": now,
    })

    rajesh_txns = [
        {"type": "income", "amount": 85000, "category": "Salary", "description": "Monthly Salary - TCS", "date": "2026-02-01"},
        {"type": "income", "amount": 85000, "category": "Salary", "description": "Monthly Salary - TCS", "date": "2026-01-01"},
        {"type": "income", "amount": 12000, "category": "Freelance", "description": "UI Design Project", "date": "2026-01-15"},
        {"type": "expense", "amount": 18000, "category": "Rent", "description": "Monthly Rent - Koramangala", "date": "2026-02-01"},
        {"type": "expense", "amount": 18000, "category": "Rent", "description": "Monthly Rent - Koramangala", "date": "2026-01-01"},
        {"type": "expense", "amount": 6500, "category": "Groceries", "description": "BigBasket + D-Mart", "date": "2026-02-05"},
        {"type": "expense", "amount": 5800, "category": "Groceries", "description": "Monthly Groceries", "date": "2026-01-08"},
        {"type": "expense", "amount": 3200, "category": "Food", "description": "Swiggy & Zomato", "date": "2026-02-10"},
        {"type": "expense", "amount": 4100, "category": "Food", "description": "Dining Out + Delivery", "date": "2026-01-12"},
        {"type": "expense", "amount": 2500, "category": "Transport", "description": "Uber + Metro", "date": "2026-02-08"},
        {"type": "expense", "amount": 2200, "category": "Transport", "description": "Ola + Auto", "date": "2026-01-10"},
        {"type": "expense", "amount": 4500, "category": "Shopping", "description": "Amazon - Electronics", "date": "2026-01-20"},
        {"type": "expense", "amount": 1500, "category": "Utilities", "description": "Electricity + Internet", "date": "2026-02-03"},
        {"type": "expense", "amount": 1500, "category": "Utilities", "description": "Electricity + Internet", "date": "2026-01-03"},
        {"type": "expense", "amount": 2000, "category": "Entertainment", "description": "Netflix + Spotify + Books", "date": "2026-02-07"},
        {"type": "expense", "amount": 3000, "category": "Health", "description": "Gym + Medicines", "date": "2026-01-25"},
        {"type": "investment", "amount": 10000, "category": "SIP", "description": "Axis Bluechip SIP", "date": "2026-02-05"},
        {"type": "investment", "amount": 10000, "category": "SIP", "description": "Axis Bluechip SIP", "date": "2026-01-05"},
        {"type": "investment", "amount": 5000, "category": "PPF", "description": "PPF Contribution", "date": "2026-02-01"},
        {"type": "investment", "amount": 5000, "category": "PPF", "description": "PPF Contribution", "date": "2026-01-01"},
        {"type": "investment", "amount": 8000, "category": "Stocks", "description": "Reliance + HDFC Bank", "date": "2026-01-18"},
    ]

    for txn in rajesh_txns:
        await db.transactions.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user1_id,
            **txn,
            "created_at": now,
        })

    priya_txns = [
        {"type": "income", "amount": 120000, "category": "Salary", "description": "Monthly Salary - Flipkart", "date": "2026-02-01"},
        {"type": "income", "amount": 120000, "category": "Salary", "description": "Monthly Salary - Flipkart", "date": "2026-01-01"},
        {"type": "income", "amount": 25000, "category": "Bonus", "description": "Quarterly Bonus", "date": "2026-01-15"},
        {"type": "expense", "amount": 25000, "category": "Rent", "description": "Monthly Rent - Indiranagar", "date": "2026-02-01"},
        {"type": "expense", "amount": 25000, "category": "Rent", "description": "Monthly Rent - Indiranagar", "date": "2026-01-01"},
        {"type": "expense", "amount": 8000, "category": "Groceries", "description": "Organic Store + Zepto", "date": "2026-02-04"},
        {"type": "expense", "amount": 7500, "category": "Groceries", "description": "Monthly Groceries", "date": "2026-01-06"},
        {"type": "expense", "amount": 5000, "category": "Food", "description": "Restaurants + Cafes", "date": "2026-02-09"},
        {"type": "expense", "amount": 6000, "category": "Shopping", "description": "Myntra + Nykaa", "date": "2026-01-22"},
        {"type": "expense", "amount": 3500, "category": "Transport", "description": "Uber Premier", "date": "2026-02-06"},
        {"type": "expense", "amount": 2000, "category": "Utilities", "description": "Bills", "date": "2026-02-02"},
        {"type": "expense", "amount": 15000, "category": "EMI", "description": "Car Loan EMI", "date": "2026-02-05"},
        {"type": "expense", "amount": 15000, "category": "EMI", "description": "Car Loan EMI", "date": "2026-01-05"},
        {"type": "expense", "amount": 4000, "category": "Health", "description": "Yoga + Health Insurance", "date": "2026-01-20"},
        {"type": "investment", "amount": 15000, "category": "Mutual Funds", "description": "HDFC Mid Cap SIP", "date": "2026-02-05"},
        {"type": "investment", "amount": 15000, "category": "Mutual Funds", "description": "HDFC Mid Cap SIP", "date": "2026-01-05"},
        {"type": "investment", "amount": 10000, "category": "FD", "description": "SBI FD", "date": "2026-01-10"},
        {"type": "investment", "amount": 5000, "category": "Gold", "description": "Sovereign Gold Bond", "date": "2026-01-15"},
    ]

    for txn in priya_txns:
        await db.transactions.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user2_id,
            **txn,
            "created_at": now,
        })

    rajesh_goals = [
        {"title": "Emergency Fund", "target_amount": 300000, "current_amount": 185000, "deadline": "2026-06-30", "category": "Safety"},
        {"title": "Goa Trip", "target_amount": 50000, "current_amount": 32000, "deadline": "2026-04-15", "category": "Travel"},
        {"title": "New Laptop", "target_amount": 80000, "current_amount": 45000, "deadline": "2026-08-01", "category": "Purchase"},
    ]
    for g in rajesh_goals:
        await db.goals.insert_one({"id": str(uuid.uuid4()), "user_id": user1_id, **g, "created_at": now})

    priya_goals = [
        {"title": "House Down Payment", "target_amount": 2000000, "current_amount": 850000, "deadline": "2027-12-31", "category": "Property"},
        {"title": "Europe Trip", "target_amount": 300000, "current_amount": 120000, "deadline": "2026-09-01", "category": "Travel"},
        {"title": "Emergency Fund", "target_amount": 500000, "current_amount": 380000, "deadline": "2026-06-30", "category": "Safety"},
    ]
    for g in priya_goals:
        await db.goals.insert_one({"id": str(uuid.uuid4()), "user_id": user2_id, **g, "created_at": now})

    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.transactions.create_index("user_id")
    await db.goals.create_index("user_id")
    await db.chat_history.create_index("user_id")

    logger.info("Demo data seeded successfully!")


async def migrate_all_users_encryption():
    """Ensure ALL users have encryption keys and all PII fields encrypted."""
    cursor = db.users.find({}, {"_id": 0})
    migrated = 0
    async for user in cursor:
        updates = {}
        dek = user.get("encryption_key", "")
        if not dek:
            dek = generate_user_dek()
            updates["encryption_key"] = dek
            for field in USER_SENSITIVE_FIELDS:
                val = user.get(field, "")
                if val and not val.startswith("ENC:"):
                    updates[field] = encrypt_field(val, dek)
        else:
            for field in USER_SENSITIVE_FIELDS:
                val = user.get(field, "")
                if val and isinstance(val, str) and not val.startswith("ENC:"):
                    updates[field] = encrypt_field(val, dek)
        if updates:
            await db.users.update_one({"id": user["id"]}, {"$set": updates})
            migrated += 1
    if migrated:
        logger.info(f"Encryption migration: {migrated} users updated")
