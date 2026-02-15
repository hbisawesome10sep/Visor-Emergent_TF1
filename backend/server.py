from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import bcrypt
import jwt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ['JWT_SECRET']
EMERGENT_LLM_KEY = os.environ['EMERGENT_LLM_KEY']

app = FastAPI()
api_router = APIRouter(prefix="/api")

# ── Logging ──
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ══════════════════════════════════════
#  MODELS
# ══════════════════════════════════════

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    dob: str
    pan: str
    aadhaar: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    dob: str
    pan: str
    aadhaar_last4: str
    created_at: str

class TransactionCreate(BaseModel):
    type: str
    amount: float
    category: str
    description: str
    date: str
    is_recurring: bool = False
    recurring_frequency: Optional[str] = None
    is_split: bool = False
    split_count: int = 1
    notes: Optional[str] = None

class TransactionResponse(BaseModel):
    id: str
    user_id: str
    type: str
    amount: float
    category: str
    description: str
    date: str
    is_recurring: bool = False
    recurring_frequency: Optional[str] = None
    is_split: bool = False
    split_count: int = 1
    notes: Optional[str] = None
    created_at: str

class GoalCreate(BaseModel):
    title: str
    target_amount: float
    current_amount: float = 0
    deadline: str
    category: str

class GoalUpdate(BaseModel):
    title: Optional[str] = None
    target_amount: Optional[float] = None
    current_amount: Optional[float] = None
    deadline: Optional[str] = None
    category: Optional[str] = None

class GoalResponse(BaseModel):
    id: str
    user_id: str
    title: str
    target_amount: float
    current_amount: float
    deadline: str
    category: str
    created_at: str

class AIMessageCreate(BaseModel):
    message: str

class ChatMessage(BaseModel):
    id: str
    user_id: str
    role: str
    content: str
    created_at: str

# ══════════════════════════════════════
#  BOOKKEEPING MODELS
# ══════════════════════════════════════

class FixedAssetCreate(BaseModel):
    name: str
    category: str  # Property, Vehicle, Electronics, Furniture, Other
    purchase_date: str
    purchase_value: float
    current_value: float
    depreciation_rate: float = 10.0  # Annual depreciation %
    notes: Optional[str] = None

class FixedAssetUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    purchase_date: Optional[str] = None
    purchase_value: Optional[float] = None
    current_value: Optional[float] = None
    depreciation_rate: Optional[float] = None
    notes: Optional[str] = None

class FixedAssetResponse(BaseModel):
    id: str
    user_id: str
    name: str
    category: str
    purchase_date: str
    purchase_value: float
    current_value: float
    depreciation_rate: float
    accumulated_depreciation: float
    notes: Optional[str]
    created_at: str

class AccountCreate(BaseModel):
    name: str
    account_type: str  # Assets, Liabilities, Income, Expenses
    account_group: str  # Sub-group like "Cash & Bank", "Investments", etc.
    opening_balance: float = 0
    notes: Optional[str] = None

class AccountResponse(BaseModel):
    id: str
    user_id: str
    name: str
    account_type: str
    account_group: str
    opening_balance: float
    current_balance: float
    notes: Optional[str]
    created_at: str

# ══════════════════════════════════════
#  AUTH HELPERS
# ══════════════════════════════════════

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, email: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc).timestamp() + 86400 * 7
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

async def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ══════════════════════════════════════
#  AUTH ENDPOINTS
# ══════════════════════════════════════

@api_router.post("/auth/register")
async def register(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email.lower()}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if len(user_data.pan) != 10:
        raise HTTPException(status_code=400, detail="PAN must be 10 characters")
    if len(user_data.aadhaar.replace(" ", "").replace("-", "")) != 12:
        raise HTTPException(status_code=400, detail="Aadhaar must be 12 digits")

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    aadhaar_clean = user_data.aadhaar.replace(" ", "").replace("-", "")
    
    user_doc = {
        "id": user_id,
        "email": user_data.email.lower(),
        "password": hash_password(user_data.password),
        "full_name": user_data.full_name,
        "dob": user_data.dob,
        "pan": user_data.pan.upper(),
        "aadhaar": aadhaar_clean,
        "created_at": now,
    }
    await db.users.insert_one(user_doc)
    
    token = create_token(user_id, user_data.email.lower())
    return {
        "token": token,
        "user": {
            "id": user_id,
            "email": user_data.email.lower(),
            "full_name": user_data.full_name,
            "dob": user_data.dob,
            "pan": user_data.pan.upper(),
            "aadhaar_last4": aadhaar_clean[-4:],
            "created_at": now,
        }
    }

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email.lower()}, {"_id": 0})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_token(user["id"], user["email"])
    aadhaar = user.get("aadhaar", "")
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "dob": user.get("dob", ""),
            "pan": user.get("pan", ""),
            "aadhaar_last4": aadhaar[-4:] if len(aadhaar) >= 4 else "",
            "created_at": user.get("created_at", ""),
        }
    }

@api_router.get("/auth/profile")
async def get_profile(user=Depends(get_current_user)):
    aadhaar = user.get("aadhaar", "")
    return {
        "id": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "dob": user.get("dob", ""),
        "pan": user.get("pan", ""),
        "aadhaar_last4": aadhaar[-4:] if len(aadhaar) >= 4 else "",
        "created_at": user.get("created_at", ""),
    }

# ══════════════════════════════════════
#  TRANSACTION ENDPOINTS
# ══════════════════════════════════════

@api_router.get("/transactions", response_model=List[TransactionResponse])
async def get_transactions(
    type: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    user=Depends(get_current_user)
):
    query = {"user_id": user["id"]}
    if type:
        query["type"] = type
    if category:
        query["category"] = category
    if search:
        query["$or"] = [
            {"description": {"$regex": search, "$options": "i"}},
            {"category": {"$regex": search, "$options": "i"}},
            {"notes": {"$regex": search, "$options": "i"}},
        ]
    
    txns = await db.transactions.find(query, {"_id": 0}).sort("date", -1).to_list(500)
    return txns

@api_router.post("/transactions", response_model=TransactionResponse)
async def create_transaction(txn: TransactionCreate, user=Depends(get_current_user)):
    txn_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    txn_doc = {
        "id": txn_id,
        "user_id": user["id"],
        "type": txn.type,
        "amount": txn.amount,
        "category": txn.category,
        "description": txn.description,
        "date": txn.date,
        "is_recurring": txn.is_recurring,
        "recurring_frequency": txn.recurring_frequency,
        "is_split": txn.is_split,
        "split_count": txn.split_count,
        "notes": txn.notes,
        "created_at": now,
    }
    await db.transactions.insert_one(txn_doc)
    return TransactionResponse(**txn_doc)

@api_router.delete("/transactions/{txn_id}")
async def delete_transaction(txn_id: str, user=Depends(get_current_user)):
    result = await db.transactions.delete_one({"id": txn_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"message": "Transaction deleted"}

# ══════════════════════════════════════
#  GOAL ENDPOINTS
# ══════════════════════════════════════

@api_router.get("/goals", response_model=List[GoalResponse])
async def get_goals(user=Depends(get_current_user)):
    goals = await db.goals.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    return goals

@api_router.post("/goals", response_model=GoalResponse)
async def create_goal(goal: GoalCreate, user=Depends(get_current_user)):
    goal_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    goal_doc = {
        "id": goal_id,
        "user_id": user["id"],
        "title": goal.title,
        "target_amount": goal.target_amount,
        "current_amount": goal.current_amount,
        "deadline": goal.deadline,
        "category": goal.category,
        "created_at": now,
    }
    await db.goals.insert_one(goal_doc)
    return GoalResponse(**goal_doc)

@api_router.put("/goals/{goal_id}", response_model=GoalResponse)
async def update_goal(goal_id: str, goal_update: GoalUpdate, user=Depends(get_current_user)):
    existing = await db.goals.find_one({"id": goal_id, "user_id": user["id"]}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    update_data = {k: v for k, v in goal_update.dict().items() if v is not None}
    if update_data:
        await db.goals.update_one({"id": goal_id}, {"$set": update_data})
    
    updated = await db.goals.find_one({"id": goal_id}, {"_id": 0})
    return GoalResponse(**updated)

@api_router.delete("/goals/{goal_id}")
async def delete_goal(goal_id: str, user=Depends(get_current_user)):
    result = await db.goals.delete_one({"id": goal_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"message": "Goal deleted"}

# ══════════════════════════════════════
#  DASHBOARD & HEALTH SCORE
# ══════════════════════════════════════

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(user=Depends(get_current_user)):
    user_id = user["id"]
    txns = await db.transactions.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
    goals = await db.goals.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    
    total_income = sum(t["amount"] for t in txns if t["type"] == "income")
    total_expenses = sum(t["amount"] for t in txns if t["type"] == "expense")
    total_investments = sum(t["amount"] for t in txns if t["type"] == "investment")
    net_balance = total_income - total_expenses - total_investments
    
    # Category breakdown for expenses
    category_breakdown = {}
    for t in txns:
        if t["type"] == "expense":
            cat = t["category"]
            category_breakdown[cat] = category_breakdown.get(cat, 0) + t["amount"]
    
    # Recent transactions (last 5)
    recent = sorted(txns, key=lambda x: x.get("date", ""), reverse=True)[:5]
    
    # Monthly summary (current month approximation)
    now = datetime.now(timezone.utc)
    current_month = now.strftime("%Y-%m")
    monthly_income = sum(t["amount"] for t in txns if t["type"] == "income" and t.get("date", "").startswith(current_month))
    monthly_expenses = sum(t["amount"] for t in txns if t["type"] == "expense" and t.get("date", "").startswith(current_month))
    monthly_investments = sum(t["amount"] for t in txns if t["type"] == "investment" and t.get("date", "").startswith(current_month))
    
    # Goal progress
    total_goal_target = sum(g["target_amount"] for g in goals) if goals else 0
    total_goal_current = sum(g["current_amount"] for g in goals) if goals else 0
    goal_progress = (total_goal_current / total_goal_target * 100) if total_goal_target > 0 else 0
    
    # Savings calculation
    savings = total_income - total_expenses - total_investments
    savings_rate = (savings / total_income * 100) if total_income > 0 else 0
    expense_ratio = (total_expenses / total_income * 100) if total_income > 0 else 0
    investment_ratio = (total_investments / total_income * 100) if total_income > 0 else 0

    # Monthly savings
    monthly_savings = monthly_income - monthly_expenses - monthly_investments

    # Budget tracking per category (as % of income)
    budget_items = []
    for cat, amount in sorted(category_breakdown.items(), key=lambda x: -x[1]):
        pct = (amount / total_income * 100) if total_income > 0 else 0
        budget_items.append({"category": cat, "amount": amount, "percentage": round(pct, 1)})

    # Investment breakdown
    invest_breakdown = {}
    for t in txns:
        if t["type"] == "investment":
            cat = t["category"]
            invest_breakdown[cat] = invest_breakdown.get(cat, 0) + t["amount"]

    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "total_investments": total_investments,
        "net_balance": net_balance,
        "savings": savings,
        "savings_rate": round(savings_rate, 1),
        "expense_ratio": round(expense_ratio, 1),
        "investment_ratio": round(investment_ratio, 1),
        "category_breakdown": category_breakdown,
        "budget_items": budget_items,
        "invest_breakdown": invest_breakdown,
        "recent_transactions": recent,
        "monthly_income": monthly_income,
        "monthly_expenses": monthly_expenses,
        "monthly_investments": monthly_investments,
        "monthly_savings": monthly_savings,
        "goal_count": len(goals),
        "goal_progress": round(goal_progress, 1),
        "transaction_count": len(txns),
    }

@api_router.get("/health-score")
async def get_health_score(user=Depends(get_current_user)):
    user_id = user["id"]
    txns = await db.transactions.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
    goals = await db.goals.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    
    total_income = sum(t["amount"] for t in txns if t["type"] == "income") or 1
    total_expenses = sum(t["amount"] for t in txns if t["type"] == "expense")
    total_investments = sum(t["amount"] for t in txns if t["type"] == "investment")
    
    savings_rate = max(0, (total_income - total_expenses) / total_income * 100)
    investment_rate = (total_investments / total_income * 100)
    expense_ratio = (total_expenses / total_income * 100)
    
    # Goal progress
    total_goal_target = sum(g["target_amount"] for g in goals) if goals else 1
    total_goal_current = sum(g["current_amount"] for g in goals) if goals else 0
    goal_score = min(100, (total_goal_current / total_goal_target * 100))
    
    # Calculate overall score (weighted)
    savings_score = min(100, savings_rate * 2.5)  # 40% savings = 100
    invest_score = min(100, investment_rate * 5)   # 20% investment = 100
    expense_score = max(0, 100 - expense_ratio)     # Lower expense ratio = higher score
    
    overall = (savings_score * 0.3 + invest_score * 0.2 + expense_score * 0.3 + goal_score * 0.2)
    overall = min(100, max(0, overall))
    
    if overall >= 80:
        grade = "Excellent"
    elif overall >= 65:
        grade = "Good"
    elif overall >= 45:
        grade = "Fair"
    elif overall >= 25:
        grade = "Needs Work"
    else:
        grade = "Critical"
    
    return {
        "overall_score": round(overall, 1),
        "grade": grade,
        "savings_rate": round(savings_rate, 1),
        "investment_rate": round(investment_rate, 1),
        "expense_ratio": round(expense_ratio, 1),
        "goal_progress": round(goal_score, 1),
        "breakdown": {
            "savings": round(savings_score, 1),
            "investments": round(invest_score, 1),
            "spending": round(expense_score, 1),
            "goals": round(goal_score, 1),
        }
    }

# ══════════════════════════════════════
#  AI CHAT ENDPOINTS
# ══════════════════════════════════════

@api_router.post("/ai/chat")
async def ai_chat(msg: AIMessageCreate, user=Depends(get_current_user)):
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    
    user_id = user["id"]
    now = datetime.now(timezone.utc).isoformat()
    
    # Save user message
    user_msg_id = str(uuid.uuid4())
    await db.chat_history.insert_one({
        "id": user_msg_id,
        "user_id": user_id,
        "role": "user",
        "content": msg.message,
        "created_at": now,
    })
    
    # Build financial context
    txns = await db.transactions.find({"user_id": user_id}, {"_id": 0}).to_list(500)
    goals = await db.goals.find({"user_id": user_id}, {"_id": 0}).to_list(50)
    
    total_income = sum(t["amount"] for t in txns if t["type"] == "income")
    total_expenses = sum(t["amount"] for t in txns if t["type"] == "expense")
    total_investments = sum(t["amount"] for t in txns if t["type"] == "investment")
    
    category_breakdown = {}
    for t in txns:
        if t["type"] == "expense":
            cat = t["category"]
            category_breakdown[cat] = category_breakdown.get(cat, 0) + t["amount"]
    
    goal_summary = [f"{g['title']}: ₹{g['current_amount']:,.0f}/₹{g['target_amount']:,.0f}" for g in goals]
    
    context = f"""User Financial Profile:
- Total Income: ₹{total_income:,.2f}
- Total Expenses: ₹{total_expenses:,.2f}
- Total Investments: ₹{total_investments:,.2f}
- Net Balance: ₹{total_income - total_expenses - total_investments:,.2f}
- Savings Rate: {((total_income - total_expenses) / max(total_income, 1) * 100):.1f}%
- Top Expense Categories: {', '.join(f'{k}: ₹{v:,.0f}' for k, v in sorted(category_breakdown.items(), key=lambda x: -x[1])[:5])}
- Financial Goals: {', '.join(goal_summary) if goal_summary else 'None set'}
"""
    
    system_msg = """You are Visor AI, an expert Indian personal finance advisor. You provide advice in the context of Indian financial markets, tax laws (Income Tax Act, GST), investment instruments (PPF, NPS, ELSS, FD, SIP, Mutual Funds, Stocks), and banking.

Key guidelines:
- Always use ₹ (Indian Rupee) for currency
- Reference Indian tax slabs, Section 80C, 80D deductions where relevant
- Suggest Indian investment instruments (PPF, NPS, ELSS, SIP, FD, Gold ETFs)
- Consider Indian inflation rates (~5-6%) in calculations
- Be concise, actionable, and encouraging
- Format numbers in Indian system (lakhs, crores)
- Keep responses under 200 words unless detailed analysis is needed"""
    
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"visor-{user_id}-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
            system_message=system_msg,
        )
        chat.with_model("openai", "gpt-5.2")
        
        user_message = UserMessage(text=f"{context}\n\nUser Question: {msg.message}")
        response_text = await chat.send_message(user_message)
        
    except Exception as e:
        logger.error(f"AI chat error: {e}")
        response_text = "I'm having trouble connecting right now. Please try again in a moment. In the meantime, here's a tip: Review your monthly expenses and identify subscriptions you no longer use—small savings add up!"
    
    # Save AI response
    ai_msg_id = str(uuid.uuid4())
    ai_now = datetime.now(timezone.utc).isoformat()
    await db.chat_history.insert_one({
        "id": ai_msg_id,
        "user_id": user_id,
        "role": "assistant",
        "content": response_text,
        "created_at": ai_now,
    })
    
    return {
        "id": ai_msg_id,
        "role": "assistant",
        "content": response_text,
        "created_at": ai_now,
    }

@api_router.get("/ai/history")
async def get_chat_history(user=Depends(get_current_user)):
    messages = await db.chat_history.find(
        {"user_id": user["id"]}, {"_id": 0}
    ).sort("created_at", 1).to_list(100)
    return messages

@api_router.delete("/ai/history")
async def clear_chat_history(user=Depends(get_current_user)):
    await db.chat_history.delete_many({"user_id": user["id"]})
    return {"message": "Chat history cleared"}

# ══════════════════════════════════════
#  DEMO DATA SEEDING
# ══════════════════════════════════════

async def seed_demo_data():
    # Check if demo users already exist
    demo1 = await db.users.find_one({"email": "rajesh@visor.demo"}, {"_id": 0})
    if demo1:
        logger.info("Demo data already exists, skipping seed")
        return

    logger.info("Seeding demo data...")
    now = datetime.now(timezone.utc).isoformat()

    # Demo User 1: Rajesh Kumar
    user1_id = str(uuid.uuid4())
    await db.users.insert_one({
        "id": user1_id,
        "email": "rajesh@visor.demo",
        "password": hash_password("Demo@123"),
        "full_name": "Rajesh Kumar",
        "dob": "1995-05-15",
        "pan": "ABCDE1234F",
        "aadhaar": "123456789012",
        "created_at": now,
    })

    # Demo User 2: Priya Sharma
    user2_id = str(uuid.uuid4())
    await db.users.insert_one({
        "id": user2_id,
        "email": "priya@visor.demo",
        "password": hash_password("Demo@456"),
        "full_name": "Priya Sharma",
        "dob": "1990-08-22",
        "pan": "FGHIJ5678K",
        "aadhaar": "987654321098",
        "created_at": now,
    })

    # Transactions for Rajesh
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

    # Transactions for Priya
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

    # Goals for Rajesh
    rajesh_goals = [
        {"title": "Emergency Fund", "target_amount": 300000, "current_amount": 185000, "deadline": "2026-06-30", "category": "Safety"},
        {"title": "Goa Trip", "target_amount": 50000, "current_amount": 32000, "deadline": "2026-04-15", "category": "Travel"},
        {"title": "New Laptop", "target_amount": 80000, "current_amount": 45000, "deadline": "2026-08-01", "category": "Purchase"},
    ]
    for g in rajesh_goals:
        await db.goals.insert_one({"id": str(uuid.uuid4()), "user_id": user1_id, **g, "created_at": now})

    # Goals for Priya
    priya_goals = [
        {"title": "House Down Payment", "target_amount": 2000000, "current_amount": 850000, "deadline": "2027-12-31", "category": "Property"},
        {"title": "Europe Trip", "target_amount": 300000, "current_amount": 120000, "deadline": "2026-09-01", "category": "Travel"},
        {"title": "Emergency Fund", "target_amount": 500000, "current_amount": 380000, "deadline": "2026-06-30", "category": "Safety"},
    ]
    for g in priya_goals:
        await db.goals.insert_one({"id": str(uuid.uuid4()), "user_id": user2_id, **g, "created_at": now})

    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.transactions.create_index("user_id")
    await db.goals.create_index("user_id")
    await db.chat_history.create_index("user_id")

    logger.info("Demo data seeded successfully!")

# ══════════════════════════════════════
#  APP SETUP
# ══════════════════════════════════════

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await seed_demo_data()

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
