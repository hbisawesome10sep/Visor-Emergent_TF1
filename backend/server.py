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
from datetime import datetime, timezone, timedelta
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
ALPHA_VANTAGE_KEY = os.environ.get('ALPHA_VANTAGE_KEY', '')

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
    description: str = ""
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
#  LOAN/LIABILITY MODELS
# ══════════════════════════════════════

class LoanCreate(BaseModel):
    name: str
    loan_type: str  # Home Loan, Car Loan, Personal Loan, Education Loan, Credit Card, Other
    principal_amount: float
    interest_rate: float  # Annual interest rate %
    tenure_months: int
    start_date: str
    emi_amount: Optional[float] = None  # If not provided, will be calculated
    lender: Optional[str] = None
    account_number: Optional[str] = None
    notes: Optional[str] = None

class LoanUpdate(BaseModel):
    name: Optional[str] = None
    loan_type: Optional[str] = None
    principal_amount: Optional[float] = None
    interest_rate: Optional[float] = None
    tenure_months: Optional[int] = None
    start_date: Optional[str] = None
    emi_amount: Optional[float] = None
    lender: Optional[str] = None
    account_number: Optional[str] = None
    notes: Optional[str] = None

class LoanResponse(BaseModel):
    id: str
    user_id: str
    name: str
    loan_type: str
    principal_amount: float
    interest_rate: float
    tenure_months: int
    start_date: str
    emi_amount: float
    lender: Optional[str]
    account_number: Optional[str]
    notes: Optional[str]
    outstanding_principal: float
    total_interest_paid: float
    total_principal_paid: float
    remaining_emis: int
    created_at: str

class EMIScheduleItem(BaseModel):
    month: int
    date: str
    opening_balance: float
    emi: float
    principal: float
    interest: float
    closing_balance: float
    status: str  # paid, upcoming, overdue

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

@api_router.put("/transactions/{txn_id}", response_model=TransactionResponse)
async def update_transaction(txn_id: str, txn: TransactionCreate, user=Depends(get_current_user)):
    existing = await db.transactions.find_one({"id": txn_id, "user_id": user["id"]}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Transaction not found")
    update_data = {
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
    }
    await db.transactions.update_one({"id": txn_id, "user_id": user["id"]}, {"$set": update_data})
    updated = await db.transactions.find_one({"id": txn_id}, {"_id": 0})
    return TransactionResponse(**updated)

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
async def get_dashboard_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user=Depends(get_current_user),
):
    user_id = user["id"]
    
    # Build query filter
    query = {"user_id": user_id}
    if start_date and end_date:
        query["date"] = {"$gte": start_date, "$lte": end_date}
    
    txns = await db.transactions.find(query, {"_id": 0}).to_list(1000)
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

    # Get user's account creation date for date range limits
    user_created_at = user.get("created_at", now.isoformat())

    # ── Compute Health Score from ALL-TIME data (not filtered) ──
    all_txns = txns
    if start_date and end_date:
        # If date-filtered, fetch ALL transactions for health score
        all_txns = await db.transactions.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
    
    hs_income = sum(t["amount"] for t in all_txns if t["type"] == "income") or 1
    hs_expenses = sum(t["amount"] for t in all_txns if t["type"] == "expense")
    hs_investments = sum(t["amount"] for t in all_txns if t["type"] == "investment")
    
    hs_savings_rate = max(0, (hs_income - hs_expenses) / hs_income * 100)
    hs_investment_rate = (hs_investments / hs_income * 100)
    hs_expense_ratio = (hs_expenses / hs_income * 100)
    
    hs_goal_target = sum(g["target_amount"] for g in goals) if goals else 1
    hs_goal_current = sum(g["current_amount"] for g in goals) if goals else 0
    hs_goal_score = min(100, (hs_goal_current / hs_goal_target * 100))
    
    hs_savings_score = min(100, hs_savings_rate * 2.5)
    hs_invest_score = min(100, hs_investment_rate * 5)
    hs_expense_score = max(0, 100 - hs_expense_ratio)
    
    hs_overall = (hs_savings_score * 0.3 + hs_invest_score * 0.2 + hs_expense_score * 0.3 + hs_goal_score * 0.2)
    hs_overall = min(100, max(0, hs_overall))
    
    if hs_overall >= 80:
        hs_grade = "Excellent"
    elif hs_overall >= 65:
        hs_grade = "Good"
    elif hs_overall >= 45:
        hs_grade = "Fair"
    elif hs_overall >= 25:
        hs_grade = "Needs Work"
    else:
        hs_grade = "Critical"

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
        "user_created_at": user_created_at,
        "date_range": {
            "start": start_date,
            "end": end_date,
        } if start_date and end_date else None,
        "health_score": {
            "overall": round(hs_overall, 1),
            "grade": hs_grade,
            "breakdown": {
                "savings": round(hs_savings_score, 1),
                "investments": round(hs_invest_score, 1),
                "spending": round(hs_expense_score, 1),
                "goals": round(hs_goal_score, 1),
            },
            "metrics": {
                "savings_rate": round(hs_savings_rate, 1),
                "investment_rate": round(hs_investment_rate, 1),
                "expense_ratio": round(hs_expense_ratio, 1),
                "goal_progress": round(hs_goal_score, 1),
            },
        },
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
#  FIXED ASSETS ENDPOINTS
# ══════════════════════════════════════

@api_router.get("/assets", response_model=List[FixedAssetResponse])
async def get_fixed_assets(user=Depends(get_current_user)):
    assets = await db.fixed_assets.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    # Calculate accumulated depreciation for each asset
    result = []
    for asset in assets:
        purchase_date = datetime.fromisoformat(asset["purchase_date"].replace("Z", "+00:00")) if "T" in asset["purchase_date"] else datetime.strptime(asset["purchase_date"], "%Y-%m-%d")
        years_held = (datetime.now(timezone.utc) - purchase_date.replace(tzinfo=timezone.utc)).days / 365.25
        acc_dep = min(asset["purchase_value"], asset["purchase_value"] * (asset.get("depreciation_rate", 10) / 100) * years_held)
        asset["accumulated_depreciation"] = round(acc_dep, 2)
        result.append(FixedAssetResponse(**asset))
    return result

@api_router.post("/assets", response_model=FixedAssetResponse)
async def create_fixed_asset(asset: FixedAssetCreate, user=Depends(get_current_user)):
    asset_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    asset_doc = {
        "id": asset_id,
        "user_id": user["id"],
        "name": asset.name,
        "category": asset.category,
        "purchase_date": asset.purchase_date,
        "purchase_value": asset.purchase_value,
        "current_value": asset.current_value,
        "depreciation_rate": asset.depreciation_rate,
        "notes": asset.notes,
        "created_at": now,
    }
    await db.fixed_assets.insert_one(asset_doc)
    asset_doc["accumulated_depreciation"] = 0
    return FixedAssetResponse(**asset_doc)

@api_router.put("/assets/{asset_id}", response_model=FixedAssetResponse)
async def update_fixed_asset(asset_id: str, asset_update: FixedAssetUpdate, user=Depends(get_current_user)):
    existing = await db.fixed_assets.find_one({"id": asset_id, "user_id": user["id"]}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    update_data = {k: v for k, v in asset_update.dict().items() if v is not None}
    if update_data:
        await db.fixed_assets.update_one({"id": asset_id}, {"$set": update_data})
    
    updated = await db.fixed_assets.find_one({"id": asset_id}, {"_id": 0})
    purchase_date = datetime.fromisoformat(updated["purchase_date"].replace("Z", "+00:00")) if "T" in updated["purchase_date"] else datetime.strptime(updated["purchase_date"], "%Y-%m-%d")
    years_held = (datetime.now(timezone.utc) - purchase_date.replace(tzinfo=timezone.utc)).days / 365.25
    acc_dep = min(updated["purchase_value"], updated["purchase_value"] * (updated.get("depreciation_rate", 10) / 100) * years_held)
    updated["accumulated_depreciation"] = round(acc_dep, 2)
    return FixedAssetResponse(**updated)

@api_router.delete("/assets/{asset_id}")
async def delete_fixed_asset(asset_id: str, user=Depends(get_current_user)):
    result = await db.fixed_assets.delete_one({"id": asset_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"message": "Asset deleted"}

# ══════════════════════════════════════
#  LOAN/LIABILITY ENDPOINTS
# ══════════════════════════════════════

def calculate_emi(principal: float, annual_rate: float, tenure_months: int) -> float:
    """Calculate EMI using standard formula"""
    if annual_rate == 0:
        return principal / tenure_months
    monthly_rate = annual_rate / 12 / 100
    emi = principal * monthly_rate * ((1 + monthly_rate) ** tenure_months) / (((1 + monthly_rate) ** tenure_months) - 1)
    return round(emi, 2)

def generate_emi_schedule(principal: float, annual_rate: float, tenure_months: int, start_date: str, emi: float) -> List[dict]:
    """Generate complete EMI amortization schedule"""
    schedule = []
    balance = principal
    monthly_rate = annual_rate / 12 / 100 if annual_rate > 0 else 0
    
    start = datetime.strptime(start_date, "%Y-%m-%d")
    today = datetime.now()
    
    for month in range(1, tenure_months + 1):
        payment_date = start + timedelta(days=30 * month)
        
        interest = balance * monthly_rate
        principal_component = emi - interest
        closing_balance = max(0, balance - principal_component)
        
        # Determine status
        if payment_date < today:
            status = "paid"
        elif payment_date.month == today.month and payment_date.year == today.year:
            status = "current"
        else:
            status = "upcoming"
        
        schedule.append({
            "month": month,
            "date": payment_date.strftime("%Y-%m-%d"),
            "opening_balance": round(balance, 2),
            "emi": emi,
            "principal": round(principal_component, 2),
            "interest": round(interest, 2),
            "closing_balance": round(closing_balance, 2),
            "status": status,
        })
        
        balance = closing_balance
        if balance <= 0:
            break
    
    return schedule

@api_router.get("/loans")
async def get_loans(user=Depends(get_current_user)):
    """Get all loans with calculated outstanding amounts"""
    loans = await db.loans.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    result = []
    
    for loan in loans:
        emi = loan.get("emi_amount") or calculate_emi(loan["principal_amount"], loan["interest_rate"], loan["tenure_months"])
        schedule = generate_emi_schedule(
            loan["principal_amount"],
            loan["interest_rate"],
            loan["tenure_months"],
            loan["start_date"],
            emi
        )
        
        # Calculate paid amounts
        paid_emis = [s for s in schedule if s["status"] == "paid"]
        total_principal_paid = sum(s["principal"] for s in paid_emis)
        total_interest_paid = sum(s["interest"] for s in paid_emis)
        outstanding = loan["principal_amount"] - total_principal_paid
        remaining_emis = loan["tenure_months"] - len(paid_emis)
        
        result.append({
            **loan,
            "emi_amount": emi,
            "outstanding_principal": round(outstanding, 2),
            "total_principal_paid": round(total_principal_paid, 2),
            "total_interest_paid": round(total_interest_paid, 2),
            "remaining_emis": remaining_emis,
        })
    
    return result

@api_router.post("/loans")
async def create_loan(loan: LoanCreate, user=Depends(get_current_user)):
    """Create a new loan"""
    loan_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    emi = loan.emi_amount or calculate_emi(loan.principal_amount, loan.interest_rate, loan.tenure_months)
    
    loan_doc = {
        "id": loan_id,
        "user_id": user["id"],
        "name": loan.name,
        "loan_type": loan.loan_type,
        "principal_amount": loan.principal_amount,
        "interest_rate": loan.interest_rate,
        "tenure_months": loan.tenure_months,
        "start_date": loan.start_date,
        "emi_amount": emi,
        "lender": loan.lender,
        "account_number": loan.account_number,
        "notes": loan.notes,
        "created_at": now,
    }
    await db.loans.insert_one(loan_doc)
    
    # Return without _id
    return {
        "id": loan_id,
        "user_id": user["id"],
        "name": loan.name,
        "loan_type": loan.loan_type,
        "principal_amount": loan.principal_amount,
        "interest_rate": loan.interest_rate,
        "tenure_months": loan.tenure_months,
        "start_date": loan.start_date,
        "emi_amount": emi,
        "lender": loan.lender,
        "account_number": loan.account_number,
        "notes": loan.notes,
        "created_at": now,
        "outstanding_principal": loan.principal_amount,
        "total_principal_paid": 0,
        "total_interest_paid": 0,
        "remaining_emis": loan.tenure_months,
    }

@api_router.get("/loans/{loan_id}")
async def get_loan_detail(loan_id: str, user=Depends(get_current_user)):
    """Get loan details with EMI schedule"""
    loan = await db.loans.find_one({"id": loan_id, "user_id": user["id"]}, {"_id": 0})
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    emi = loan.get("emi_amount") or calculate_emi(loan["principal_amount"], loan["interest_rate"], loan["tenure_months"])
    schedule = generate_emi_schedule(
        loan["principal_amount"],
        loan["interest_rate"],
        loan["tenure_months"],
        loan["start_date"],
        emi
    )
    
    paid_emis = [s for s in schedule if s["status"] == "paid"]
    total_principal_paid = sum(s["principal"] for s in paid_emis)
    total_interest_paid = sum(s["interest"] for s in paid_emis)
    outstanding = loan["principal_amount"] - total_principal_paid
    
    return {
        **loan,
        "emi_amount": emi,
        "outstanding_principal": round(outstanding, 2),
        "total_principal_paid": round(total_principal_paid, 2),
        "total_interest_paid": round(total_interest_paid, 2),
        "remaining_emis": loan["tenure_months"] - len(paid_emis),
        "emi_schedule": schedule,
    }

@api_router.put("/loans/{loan_id}")
async def update_loan(loan_id: str, loan_update: LoanUpdate, user=Depends(get_current_user)):
    """Update a loan"""
    existing = await db.loans.find_one({"id": loan_id, "user_id": user["id"]}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    update_data = {k: v for k, v in loan_update.dict().items() if v is not None}
    if update_data:
        await db.loans.update_one({"id": loan_id}, {"$set": update_data})
    
    updated = await db.loans.find_one({"id": loan_id}, {"_id": 0})
    return updated

@api_router.delete("/loans/{loan_id}")
async def delete_loan(loan_id: str, user=Depends(get_current_user)):
    """Delete a loan"""
    result = await db.loans.delete_one({"id": loan_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Loan not found")
    return {"message": "Loan deleted"}

# ══════════════════════════════════════
#  BOOKKEEPING / LEDGER ENDPOINTS
# ══════════════════════════════════════

def get_indian_fy_dates(fy_year: int = None):
    """Get Indian Financial Year dates (April 1 to March 31)"""
    now = datetime.now(timezone.utc)
    if fy_year is None:
        # Current FY: if we're in Jan-Mar, FY started previous year
        if now.month < 4:
            fy_year = now.year - 1
        else:
            fy_year = now.year
    
    fy_start = datetime(fy_year, 4, 1, tzinfo=timezone.utc)
    fy_end = datetime(fy_year + 1, 3, 31, 23, 59, 59, tzinfo=timezone.utc)
    return fy_start, fy_end

@api_router.get("/books/ledger")
async def get_ledger(
    account_group: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user=Depends(get_current_user)
):
    """Get general ledger with double-entry bookkeeping entries"""
    user_id = user["id"]
    
    # Default to current FY if no dates provided
    if not start_date or not end_date:
        fy_start, fy_end = get_indian_fy_dates()
        start_date = start_date or fy_start.strftime("%Y-%m-%d")
        end_date = end_date or fy_end.strftime("%Y-%m-%d")
    
    # Fetch all transactions in date range
    query = {
        "user_id": user_id,
        "date": {"$gte": start_date, "$lte": end_date}
    }
    txns = await db.transactions.find(query, {"_id": 0}).sort("date", 1).to_list(2000)
    
    # Map transaction types/categories to account groups
    account_mapping = {
        # Assets
        "Salary": "Cash & Bank Balances",
        "Freelance": "Cash & Bank Balances",
        "Bonus": "Cash & Bank Balances",
        "Interest": "Cash & Bank Balances",
        "Dividend": "Cash & Bank Balances",
        # Investments
        "SIP": "Investments",
        "PPF": "Investments",
        "Stocks": "Investments",
        "Mutual Funds": "Investments",
        "FD": "Investments",
        "Gold": "Investments",
        "NPS": "Investments",
        # Expenses
        "Rent": "Rent & Housing",
        "Groceries": "Food & Dining",
        "Food": "Food & Dining",
        "Transport": "Transport & Fuel",
        "Shopping": "Shopping & Personal",
        "Utilities": "Utilities & Bills",
        "Entertainment": "Entertainment & Leisure",
        "Health": "Health & Medical",
        "EMI": "Financial Obligations",
        "Education": "Education & Learning",
        "Insurance": "Insurance Premiums",
    }
    
    # Build ledger entries with double-entry
    ledger_entries = []
    running_balances = {}
    
    for txn in txns:
        cat = txn.get("category", "Other")
        mapped_group = account_mapping.get(cat, "Other")
        
        if account_group and mapped_group != account_group:
            continue
        
        if txn["type"] == "income":
            # Debit: Cash & Bank, Credit: Income account
            ledger_entries.append({
                "date": txn["date"],
                "particulars": txn["description"],
                "voucher_ref": f"TXN-{txn['id'][:8].upper()}",
                "account": "Cash & Bank Balances",
                "debit": txn["amount"],
                "credit": 0,
                "transaction_id": txn["id"],
            })
            ledger_entries.append({
                "date": txn["date"],
                "particulars": txn["description"],
                "voucher_ref": f"TXN-{txn['id'][:8].upper()}",
                "account": f"{cat} Income",
                "debit": 0,
                "credit": txn["amount"],
                "transaction_id": txn["id"],
            })
        elif txn["type"] == "expense":
            # Debit: Expense account, Credit: Cash & Bank
            ledger_entries.append({
                "date": txn["date"],
                "particulars": txn["description"],
                "voucher_ref": f"TXN-{txn['id'][:8].upper()}",
                "account": mapped_group,
                "debit": txn["amount"],
                "credit": 0,
                "transaction_id": txn["id"],
            })
            ledger_entries.append({
                "date": txn["date"],
                "particulars": txn["description"],
                "voucher_ref": f"TXN-{txn['id'][:8].upper()}",
                "account": "Cash & Bank Balances",
                "debit": 0,
                "credit": txn["amount"],
                "transaction_id": txn["id"],
            })
        elif txn["type"] == "investment":
            # Debit: Investment account, Credit: Cash & Bank
            ledger_entries.append({
                "date": txn["date"],
                "particulars": txn["description"],
                "voucher_ref": f"TXN-{txn['id'][:8].upper()}",
                "account": f"{cat} Investment",
                "debit": txn["amount"],
                "credit": 0,
                "transaction_id": txn["id"],
            })
            ledger_entries.append({
                "date": txn["date"],
                "particulars": txn["description"],
                "voucher_ref": f"TXN-{txn['id'][:8].upper()}",
                "account": "Cash & Bank Balances",
                "debit": 0,
                "credit": txn["amount"],
                "transaction_id": txn["id"],
            })
    
    # Group by account and calculate running balances
    accounts = {}
    for entry in ledger_entries:
        acc = entry["account"]
        if acc not in accounts:
            accounts[acc] = {"entries": [], "total_debit": 0, "total_credit": 0}
        accounts[acc]["entries"].append(entry)
        accounts[acc]["total_debit"] += entry["debit"]
        accounts[acc]["total_credit"] += entry["credit"]
    
    # Calculate running balance for each account
    for acc, data in accounts.items():
        running = 0
        for entry in data["entries"]:
            running += entry["debit"] - entry["credit"]
            entry["balance"] = running
        data["closing_balance"] = running
    
    return {
        "fy_start": start_date,
        "fy_end": end_date,
        "accounts": accounts,
        "entry_count": len(ledger_entries),
    }

@api_router.get("/books/pnl")
async def get_profit_loss(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user=Depends(get_current_user)
):
    """Get Profit & Loss (Income & Expenditure) Statement"""
    user_id = user["id"]
    
    # Default to current FY if no dates provided
    if not start_date or not end_date:
        fy_start, fy_end = get_indian_fy_dates()
        start_date = start_date or fy_start.strftime("%Y-%m-%d")
        end_date = end_date or fy_end.strftime("%Y-%m-%d")
    
    query = {
        "user_id": user_id,
        "date": {"$gte": start_date, "$lte": end_date}
    }
    txns = await db.transactions.find(query, {"_id": 0}).to_list(2000)
    
    # Income categories mapping
    income_groups = {
        "A": {"name": "Revenue from Employment", "categories": ["Salary", "Bonus"], "items": {}},
        "B": {"name": "Income from Profession/Freelance", "categories": ["Freelance", "Consulting"], "items": {}},
        "C": {"name": "Income from Investments", "categories": ["Interest", "Dividend", "Capital Gains"], "items": {}},
        "D": {"name": "Other Income", "categories": ["Rental", "Other"], "items": {}},
    }
    
    # Expense categories mapping
    expense_groups = {
        "E": {"name": "Living & Household Expenses", "categories": ["Food", "Groceries", "Utilities", "Rent", "Transport", "Shopping", "Entertainment", "Health"], "items": {}},
        "F": {"name": "Financial Obligations", "categories": ["EMI", "Insurance"], "items": {}},
        "G": {"name": "Taxes & Statutory Deductions", "categories": ["Tax", "TDS"], "items": {}},
        "H": {"name": "Education & Development", "categories": ["Education"], "items": {}},
        "I": {"name": "Other Expenses", "categories": ["Bank Charges", "Depreciation", "Other"], "items": {}},
    }
    
    # Process transactions
    total_income = 0
    total_expenses = 0
    total_investments = 0
    
    for txn in txns:
        cat = txn.get("category", "Other")
        amount = txn["amount"]
        
        if txn["type"] == "income":
            total_income += amount
            # Find appropriate income group
            placed = False
            for group_id, group in income_groups.items():
                if cat in group["categories"] or any(c.lower() in cat.lower() for c in group["categories"]):
                    if cat not in group["items"]:
                        group["items"][cat] = 0
                    group["items"][cat] += amount
                    placed = True
                    break
            if not placed:
                income_groups["D"]["items"][cat] = income_groups["D"]["items"].get(cat, 0) + amount
                
        elif txn["type"] == "expense":
            total_expenses += amount
            # Find appropriate expense group
            placed = False
            for group_id, group in expense_groups.items():
                if cat in group["categories"] or any(c.lower() in cat.lower() for c in group["categories"]):
                    if cat not in group["items"]:
                        group["items"][cat] = 0
                    group["items"][cat] += amount
                    placed = True
                    break
            if not placed:
                expense_groups["I"]["items"][cat] = expense_groups["I"]["items"].get(cat, 0) + amount
                
        elif txn["type"] == "investment":
            total_investments += amount
    
    # Calculate subtotals
    income_sections = []
    for group_id, group in income_groups.items():
        subtotal = sum(group["items"].values())
        if subtotal > 0 or group["items"]:
            income_sections.append({
                "id": group_id,
                "name": group["name"],
                "items": [{"category": k, "amount": v} for k, v in sorted(group["items"].items(), key=lambda x: -x[1])],
                "subtotal": subtotal,
            })
    
    expense_sections = []
    for group_id, group in expense_groups.items():
        subtotal = sum(group["items"].values())
        if subtotal > 0 or group["items"]:
            expense_sections.append({
                "id": group_id,
                "name": group["name"],
                "items": [{"category": k, "amount": v} for k, v in sorted(group["items"].items(), key=lambda x: -x[1])],
                "subtotal": subtotal,
            })
    
    surplus = total_income - total_expenses
    
    return {
        "period_start": start_date,
        "period_end": end_date,
        "income_sections": income_sections,
        "expense_sections": expense_sections,
        "total_income": total_income,
        "total_expenses": total_expenses,
        "total_investments": total_investments,
        "surplus_deficit": surplus,
        "allocation": {
            "to_savings": max(0, surplus * 0.4),
            "to_investments": total_investments,
            "retained": max(0, surplus - total_investments - (surplus * 0.4)),
        }
    }

@api_router.get("/books/balance-sheet")
async def get_balance_sheet(
    as_of_date: Optional[str] = None,
    user=Depends(get_current_user)
):
    """Get Balance Sheet as of a specific date"""
    user_id = user["id"]
    
    if not as_of_date:
        as_of_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Get all transactions up to the date
    query = {"user_id": user_id, "date": {"$lte": as_of_date}}
    txns = await db.transactions.find(query, {"_id": 0}).to_list(5000)
    
    # Get fixed assets
    assets = await db.fixed_assets.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    
    # Get goals (as receivables/planned savings)
    goals = await db.goals.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    
    # Calculate totals
    total_income = sum(t["amount"] for t in txns if t["type"] == "income")
    total_expenses = sum(t["amount"] for t in txns if t["type"] == "expense")
    total_investments = sum(t["amount"] for t in txns if t["type"] == "investment")
    
    # Investment breakdown
    invest_by_cat = {}
    for t in txns:
        if t["type"] == "investment":
            cat = t.get("category", "Other")
            invest_by_cat[cat] = invest_by_cat.get(cat, 0) + t["amount"]
    
    # Calculate fixed assets with depreciation
    fixed_asset_items = []
    total_fixed_assets = 0
    total_depreciation = 0
    for asset in assets:
        purchase_date = datetime.fromisoformat(asset["purchase_date"].replace("Z", "+00:00")) if "T" in asset["purchase_date"] else datetime.strptime(asset["purchase_date"], "%Y-%m-%d")
        years_held = (datetime.now(timezone.utc) - purchase_date.replace(tzinfo=timezone.utc)).days / 365.25
        acc_dep = min(asset["purchase_value"], asset["purchase_value"] * (asset.get("depreciation_rate", 10) / 100) * years_held)
        net_value = asset["purchase_value"] - acc_dep
        fixed_asset_items.append({
            "name": asset["name"],
            "category": asset["category"],
            "purchase_value": asset["purchase_value"],
            "accumulated_depreciation": round(acc_dep, 2),
            "net_value": round(net_value, 2),
        })
        total_fixed_assets += asset["purchase_value"]
        total_depreciation += acc_dep
    
    # Build balance sheet structure
    cash_balance = total_income - total_expenses - total_investments
    
    # Non-current assets
    non_current_assets = {
        "fixed_assets": {
            "items": fixed_asset_items,
            "gross_value": total_fixed_assets,
            "depreciation": round(total_depreciation, 2),
            "net_value": round(total_fixed_assets - total_depreciation, 2),
        },
        "long_term_investments": {
            "items": [
                {"name": "PPF", "amount": invest_by_cat.get("PPF", 0)},
                {"name": "NPS", "amount": invest_by_cat.get("NPS", 0)},
                {"name": "Long-term MF", "amount": invest_by_cat.get("Mutual Funds", 0) * 0.5},
            ],
            "total": invest_by_cat.get("PPF", 0) + invest_by_cat.get("NPS", 0) + invest_by_cat.get("Mutual Funds", 0) * 0.5,
        },
        "total": round(total_fixed_assets - total_depreciation + invest_by_cat.get("PPF", 0) + invest_by_cat.get("NPS", 0) + invest_by_cat.get("Mutual Funds", 0) * 0.5, 2),
    }
    
    # Current assets
    current_assets = {
        "short_term_investments": {
            "items": [
                {"name": "Fixed Deposits", "amount": invest_by_cat.get("FD", 0)},
                {"name": "Liquid MF", "amount": invest_by_cat.get("Mutual Funds", 0) * 0.5},
                {"name": "Stocks", "amount": invest_by_cat.get("Stocks", 0)},
                {"name": "Gold", "amount": invest_by_cat.get("Gold", 0)},
                {"name": "SIP Accumulation", "amount": invest_by_cat.get("SIP", 0)},
            ],
            "total": invest_by_cat.get("FD", 0) + invest_by_cat.get("Mutual Funds", 0) * 0.5 + invest_by_cat.get("Stocks", 0) + invest_by_cat.get("Gold", 0) + invest_by_cat.get("SIP", 0),
        },
        "cash_bank": {
            "items": [
                {"name": "Bank Balances", "amount": max(0, cash_balance)},
            ],
            "total": max(0, cash_balance),
        },
        "receivables": {
            "items": [],
            "total": 0,
        },
        "total": round(invest_by_cat.get("FD", 0) + invest_by_cat.get("Mutual Funds", 0) * 0.5 + invest_by_cat.get("Stocks", 0) + invest_by_cat.get("Gold", 0) + invest_by_cat.get("SIP", 0) + max(0, cash_balance), 2),
    }
    
    total_assets = non_current_assets["total"] + current_assets["total"]
    
    # Get loans for liabilities
    loans = await db.loans.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    
    # Calculate loan liabilities
    long_term_loan_items = []
    short_term_loan_items = []
    total_long_term = 0
    total_short_term = 0
    
    for loan in loans:
        emi = loan.get("emi_amount") or calculate_emi(loan["principal_amount"], loan["interest_rate"], loan["tenure_months"])
        schedule = generate_emi_schedule(
            loan["principal_amount"],
            loan["interest_rate"],
            loan["tenure_months"],
            loan["start_date"],
            emi
        )
        
        paid_emis = [s for s in schedule if s["status"] == "paid"]
        total_principal_paid = sum(s["principal"] for s in paid_emis)
        outstanding = loan["principal_amount"] - total_principal_paid
        remaining_emis = loan["tenure_months"] - len(paid_emis)
        
        # Principal due within 12 months = short-term, rest = long-term
        short_term_portion = min(outstanding, emi * min(12, remaining_emis) * (loan["principal_amount"] / (loan["principal_amount"] + loan["interest_rate"] * loan["tenure_months"] / 1200)))
        long_term_portion = outstanding - short_term_portion
        
        if long_term_portion > 0:
            long_term_loan_items.append({
                "name": f"{loan['name']} ({loan['loan_type']})",
                "amount": round(long_term_portion, 2),
                "lender": loan.get("lender"),
            })
            total_long_term += long_term_portion
        
        if short_term_portion > 0:
            short_term_loan_items.append({
                "name": f"{loan['name']} (Current Portion)",
                "amount": round(short_term_portion, 2),
            })
            total_short_term += short_term_portion
    
    # Liabilities
    non_current_liabilities = {
        "long_term_borrowings": {
            "items": long_term_loan_items,
            "total": round(total_long_term, 2),
        },
        "total": round(total_long_term, 2),
    }
    
    current_liabilities = {
        "short_term_borrowings": {
            "items": short_term_loan_items,
            "total": round(total_short_term, 2),
        },
        "payables": {
            "items": [],
            "total": 0,
        },
        "total": round(total_short_term, 2),
    }
    
    total_liabilities = non_current_liabilities["total"] + current_liabilities["total"]
    
    # Net Worth
    net_worth = total_assets - total_liabilities
    
    # Check if balanced
    is_balanced = abs(total_assets - (total_liabilities + net_worth)) < 0.01
    
    return {
        "as_of_date": as_of_date,
        "assets": {
            "non_current": non_current_assets,
            "current": current_assets,
            "total": round(total_assets, 2),
        },
        "liabilities": {
            "non_current": non_current_liabilities,
            "current": current_liabilities,
            "total": round(total_liabilities, 2),
        },
        "net_worth": {
            "opening": 0,
            "surplus_for_period": round(total_income - total_expenses, 2),
            "closing": round(net_worth, 2),
        },
        "total_liabilities_and_net_worth": round(total_liabilities + net_worth, 2),
        "is_balanced": is_balanced,
    }

# ══════════════════════════════════════
#  MARKET DATA (Yahoo Finance — Live)
# ══════════════════════════════════════

import asyncio
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor

REFRESH_TIMES_IST = ["09:25", "11:30", "12:30", "15:15"]
TROY_OZ_TO_GRAMS = 31.1035
GOLD_DOMESTIC_PREMIUM = 1.082
SILVER_DOMESTIC_PREMIUM = 1.209

_yf_executor = ThreadPoolExecutor(max_workers=2)

def _fetch_yfinance_data() -> list:
    """Synchronous yfinance fetch — runs in thread executor."""
    results = []
    try:
        tickers = yf.Tickers("^NSEI ^BSESN ^NSEBANK GC=F SI=F INR=X")
        usd_inr = 87.0
        try:
            fx = tickers.tickers["INR=X"].fast_info
            usd_inr = float(fx.last_price) if fx.last_price else 87.0
        except Exception:
            pass

        configs = [
            {"key": "nifty_50", "name": "Nifty 50", "yf": "^NSEI", "type": "index"},
            {"key": "sensex", "name": "SENSEX", "yf": "^BSESN", "type": "index"},
            {"key": "nifty_bank", "name": "Nifty Bank", "yf": "^NSEBANK", "type": "index"},
            {"key": "gold_10g", "name": "Gold (10g)", "yf": "GC=F", "type": "gold"},
            {"key": "silver_1kg", "name": "Silver (1Kg)", "yf": "SI=F", "type": "silver"},
        ]

        for cfg in configs:
            try:
                t = tickers.tickers[cfg["yf"]]
                info = t.fast_info
                last = float(info.last_price) if info.last_price else 0
                prev = float(info.previous_close) if info.previous_close else 0

                if cfg["type"] == "gold":
                    price_per_gram = (last / TROY_OZ_TO_GRAMS) * usd_inr * GOLD_DOMESTIC_PREMIUM
                    price = round(price_per_gram * 10, 0)
                    prev_price_per_gram = (prev / TROY_OZ_TO_GRAMS) * usd_inr * GOLD_DOMESTIC_PREMIUM
                    prev_price = round(prev_price_per_gram * 10, 0)
                    change = round(price - prev_price, 0)
                    change_pct = round((change / prev_price * 100), 2) if prev_price else 0
                    results.append({"key": cfg["key"], "name": cfg["name"], "price": price, "change": change, "change_percent": change_pct, "prev_close": prev_price})
                elif cfg["type"] == "silver":
                    price_per_kg = (last * (1000 / TROY_OZ_TO_GRAMS)) * usd_inr * SILVER_DOMESTIC_PREMIUM
                    price = round(price_per_kg, 0)
                    prev_per_kg = (prev * (1000 / TROY_OZ_TO_GRAMS)) * usd_inr * SILVER_DOMESTIC_PREMIUM
                    prev_price = round(prev_per_kg, 0)
                    change = round(price - prev_price, 0)
                    change_pct = round((change / prev_price * 100), 2) if prev_price else 0
                    results.append({"key": cfg["key"], "name": cfg["name"], "price": price, "change": change, "change_percent": change_pct, "prev_close": prev_price})
                else:
                    price = round(last, 2)
                    change = round(last - prev, 2)
                    change_pct = round((change / prev * 100), 2) if prev else 0
                    results.append({"key": cfg["key"], "name": cfg["name"], "price": price, "change": change, "change_percent": change_pct, "prev_close": round(prev, 2)})
            except Exception as e:
                logger.error(f"yfinance fetch error for {cfg['key']}: {e}")
    except Exception as e:
        logger.error(f"yfinance batch fetch error: {e}")
    return results

async def refresh_all_market_data():
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(_yf_executor, _fetch_yfinance_data)
    now = datetime.now(timezone.utc).isoformat()
    for item in results:
        if item.get("price"):
            item["last_updated"] = now
            await db.market_data.update_one({"key": item["key"]}, {"$set": item}, upsert=True)
            logger.info(f"Market LIVE: {item['name']} = {item['price']}")
    return results

async def market_data_scheduler():
    last_refresh = None
    while True:
        utc_now = datetime.now(timezone.utc)
        ist_now = utc_now + timedelta(hours=5, minutes=30)
        ist_hhmm = ist_now.strftime("%H:%M")
        if ist_hhmm in REFRESH_TIMES_IST and last_refresh != ist_hhmm:
            logger.info(f"Scheduled market refresh at IST {ist_hhmm}")
            last_refresh = ist_hhmm
            await refresh_all_market_data()
        await asyncio.sleep(30)

async def seed_market_data():
    """Seed with live data from yfinance, or use accurate fallback values."""
    await db.market_data.delete_many({})
    logger.info("Fetching live market data for seed...")
    results = await refresh_all_market_data()
    if not results or len(results) < 5:
        logger.warning("Live fetch incomplete, using accurate fallback seed data")
        now = datetime.now(timezone.utc).isoformat()
        fallback = [
            {"key": "nifty_50", "name": "Nifty 50", "price": 25734.20, "change": 51.75, "change_percent": 0.20, "prev_close": 25682.45, "last_updated": now},
            {"key": "sensex", "name": "SENSEX", "price": 83389.45, "change": 112.39, "change_percent": 0.13, "prev_close": 83277.06, "last_updated": now},
            {"key": "nifty_bank", "name": "Nifty Bank", "price": 61126.95, "change": 133.10, "change_percent": 0.22, "prev_close": 60993.85, "last_updated": now},
            {"key": "gold_10g", "name": "Gold (10g)", "price": 154910.0, "change": -1530.0, "change_percent": -0.98, "prev_close": 156440.0, "last_updated": now},
            {"key": "silver_1kg", "name": "Silver (1Kg)", "price": 260000.0, "change": -8000.0, "change_percent": -2.99, "prev_close": 268000.0, "last_updated": now},
        ]
        for s in fallback:
            await db.market_data.update_one({"key": s["key"]}, {"$set": s}, upsert=True)
    logger.info("Market data seeded successfully")

@api_router.get("/market-data")
async def get_market_data():
    data = await db.market_data.find({}, {"_id": 0}).to_list(10)
    return data

@api_router.post("/market-data/refresh")
async def trigger_market_refresh(user=Depends(get_current_user)):
    asyncio.create_task(refresh_all_market_data())
    return {"message": "Market data refresh triggered"}

# ══════════════════════════════════════
#  PORTFOLIO OVERVIEW
# ══════════════════════════════════════

# Annual return assumptions by category
CATEGORY_RETURNS = {
    "Stocks": "nifty", "SIP": "nifty", "Mutual Funds": "nifty", "ETFs": "nifty", "ELSS": "nifty",
    "Gold": "gold", "Sovereign Gold Bond": "gold",
    "Silver": "silver",
    "PPF": 0.071, "EPF": 0.0815, "NPS": 0.10, "FD": 0.07, "Fixed Deposit": 0.07,
    "Bonds": 0.075, "ULIP": 0.08, "Real Estate": 0.08, "Crypto": 0.0,
}

def _compute_portfolio_values(transactions: list, market_data: dict) -> dict:
    """Compute estimated current value for each investment category."""
    from datetime import date as dt_date
    today = dt_date.today()
    categories = {}
    for txn in transactions:
        cat = txn["category"]
        if cat not in categories:
            categories[cat] = {"invested": 0, "current_value": 0, "transactions": 0}
        amount = txn["amount"]
        categories[cat]["invested"] += amount
        categories[cat]["transactions"] += 1
        try:
            parts = txn["date"].split("-")
            txn_date = dt_date(int(parts[0]), int(parts[1]), int(parts[2]))
        except Exception:
            txn_date = today
        days_held = max((today - txn_date).days, 0)
        return_type = CATEGORY_RETURNS.get(cat, 0.0)
        if return_type == "nifty":
            nifty_now = market_data.get("nifty_50", {}).get("price", 0)
            nifty_prev = market_data.get("nifty_50", {}).get("prev_close", nifty_now)
            if nifty_now and nifty_prev:
                daily_return = (nifty_now / nifty_prev - 1) if nifty_prev else 0
                estimated_return = daily_return * days_held * 0.6
                categories[cat]["current_value"] += amount * (1 + estimated_return)
            else:
                categories[cat]["current_value"] += amount
        elif return_type == "gold":
            gold_now = market_data.get("gold_10g", {}).get("price", 0)
            gold_prev = market_data.get("gold_10g", {}).get("prev_close", gold_now)
            if gold_now and gold_prev:
                daily_return = (gold_now / gold_prev - 1) if gold_prev else 0
                estimated_return = daily_return * days_held * 0.5
                categories[cat]["current_value"] += amount * (1 + estimated_return)
            else:
                categories[cat]["current_value"] += amount
        elif return_type == "silver":
            silver_now = market_data.get("silver_1kg", {}).get("price", 0)
            silver_prev = market_data.get("silver_1kg", {}).get("prev_close", silver_now)
            if silver_now and silver_prev:
                daily_return = (silver_now / silver_prev - 1) if silver_prev else 0
                estimated_return = daily_return * days_held * 0.5
                categories[cat]["current_value"] += amount * (1 + estimated_return)
            else:
                categories[cat]["current_value"] += amount
        elif isinstance(return_type, (int, float)):
            annual_rate = return_type
            pro_rated = annual_rate * (days_held / 365)
            categories[cat]["current_value"] += amount * (1 + pro_rated)
        else:
            categories[cat]["current_value"] += amount
    for cat in categories:
        categories[cat]["invested"] = round(categories[cat]["invested"], 2)
        categories[cat]["current_value"] = round(categories[cat]["current_value"], 2)
        inv = categories[cat]["invested"]
        cur = categories[cat]["current_value"]
        categories[cat]["gain_loss"] = round(cur - inv, 2)
        categories[cat]["gain_loss_pct"] = round(((cur - inv) / inv * 100), 2) if inv else 0
    return categories

@api_router.get("/portfolio-overview")
async def get_portfolio_overview(user=Depends(get_current_user)):
    transactions = await db.transactions.find(
        {"user_id": user["id"], "type": "investment"}, {"_id": 0}
    ).to_list(1000)
    mkt_list = await db.market_data.find({}, {"_id": 0}).to_list(10)
    market_data = {m["key"]: m for m in mkt_list}
    loop = asyncio.get_event_loop()
    categories = await loop.run_in_executor(
        _yf_executor, _compute_portfolio_values, transactions, market_data
    )

    # Merge holdings data into portfolio categories
    holdings_cursor = db.holdings.find({"user_id": user["id"]})
    holdings_list = []
    async for doc in holdings_cursor:
        doc["id"] = str(doc.pop("_id"))
        holdings_list.append(doc)
    if holdings_list:
        tickers = list(set(h["ticker"] for h in holdings_list if h.get("ticker")))
        prices = await loop.run_in_executor(_yf_executor, _fetch_live_prices, tickers)
        for h in holdings_list:
            cat = h.get("category", "Stock")
            # Map holding categories to portfolio categories
            cat_key = cat
            if cat in ("Mutual Fund", "ETF"):
                cat_key = cat
            invested = h["quantity"] * h["buy_price"]
            current_price = h["buy_price"]
            if h.get("ticker") and h["ticker"] in prices:
                current_price = prices[h["ticker"]]["price"]
            current_value = h["quantity"] * current_price
            if cat_key not in categories:
                categories[cat_key] = {"invested": 0, "current_value": 0, "gain_loss": 0, "gain_loss_pct": 0, "transactions": 0}
            categories[cat_key]["invested"] = round(categories[cat_key]["invested"] + invested, 2)
            categories[cat_key]["current_value"] = round(categories[cat_key]["current_value"] + current_value, 2)
            categories[cat_key]["transactions"] += 1
        # Recalculate gain/loss for each category
        for cat_key in categories:
            inv = categories[cat_key]["invested"]
            cur = categories[cat_key]["current_value"]
            categories[cat_key]["gain_loss"] = round(cur - inv, 2)
            categories[cat_key]["gain_loss_pct"] = round((cur - inv) / inv * 100, 2) if inv else 0

    total_invested = sum(c["invested"] for c in categories.values())
    total_current = sum(c["current_value"] for c in categories.values())
    total_gain = round(total_current - total_invested, 2)
    total_gain_pct = round((total_gain / total_invested * 100), 2) if total_invested else 0
    breakdown = []
    for cat, data in sorted(categories.items(), key=lambda x: x[1]["invested"], reverse=True):
        breakdown.append({
            "category": cat,
            "invested": data["invested"],
            "current_value": data["current_value"],
            "gain_loss": data["gain_loss"],
            "gain_loss_pct": data["gain_loss_pct"],
            "transactions": data["transactions"],
        })
    return {
        "total_invested": total_invested,
        "total_current_value": round(total_current, 2),
        "total_gain_loss": total_gain,
        "total_gain_loss_pct": total_gain_pct,
        "categories": breakdown,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

# ══════════════════════════════════════
#  HOLDINGS (Manual + CAS Upload)
# ══════════════════════════════════════

from fastapi import File, UploadFile, Form
import pdfplumber
import re
import io
from bson import ObjectId

class HoldingCreate(BaseModel):
    name: str
    ticker: str = ""
    isin: str = ""
    category: str = "Stock"
    quantity: float
    buy_price: float
    buy_date: str = ""

def _fetch_live_prices(tickers: list[str]) -> dict:
    """Fetch live prices for a list of tickers via yfinance."""
    result = {}
    if not tickers:
        return result
    try:
        batch = yf.Tickers(" ".join(tickers))
        for t_str in tickers:
            try:
                info = batch.tickers[t_str].fast_info
                price = float(info.last_price) if info.last_price else 0
                prev = float(info.previous_close) if info.previous_close else 0
                result[t_str] = {"price": price, "prev_close": prev}
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Batch price fetch error: {e}")
    return result

def _search_ticker(name: str, category: str) -> str:
    """Try to find a Yahoo Finance ticker for a given name."""
    try:
        suffix = ".NS"
        clean = re.sub(r'[^a-zA-Z0-9 ]', '', name).strip()
        search = yf.Ticker(clean.split()[0].upper() + suffix)
        if search.fast_info.last_price:
            return clean.split()[0].upper() + suffix
    except Exception:
        pass
    return ""

@api_router.post("/holdings")
async def add_holding(holding: HoldingCreate, user=Depends(get_current_user)):
    doc = {
        "user_id": user["id"],
        "name": holding.name,
        "ticker": holding.ticker,
        "isin": holding.isin,
        "category": holding.category,
        "quantity": holding.quantity,
        "buy_price": holding.buy_price,
        "buy_date": holding.buy_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": "manual",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.holdings.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    return doc

@api_router.get("/holdings")
async def get_holdings(user=Depends(get_current_user)):
    holdings = []
    cursor = db.holdings.find({"user_id": user["id"]})
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        holdings.append(doc)
    return holdings

@api_router.get("/holdings/live")
async def get_holdings_live(user=Depends(get_current_user)):
    holdings = []
    cursor = db.holdings.find({"user_id": user["id"]})
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        holdings.append(doc)
    tickers = list(set(h["ticker"] for h in holdings if h.get("ticker")))
    loop = asyncio.get_event_loop()
    prices = await loop.run_in_executor(_yf_executor, _fetch_live_prices, tickers)
    result = []
    for h in holdings:
        invested = h["quantity"] * h["buy_price"]
        current_price = 0
        if h.get("ticker") and h["ticker"] in prices:
            current_price = prices[h["ticker"]]["price"]
        else:
            current_price = h["buy_price"]
        current_value = h["quantity"] * current_price
        gain = current_value - invested
        gain_pct = round((gain / invested * 100), 2) if invested else 0
        result.append({
            **{k: v for k, v in h.items()},
            "current_price": round(current_price, 2),
            "invested_value": round(invested, 2),
            "current_value": round(current_value, 2),
            "gain_loss": round(gain, 2),
            "gain_loss_pct": gain_pct,
        })
    total_invested = sum(r["invested_value"] for r in result)
    total_current = sum(r["current_value"] for r in result)
    total_gain = round(total_current - total_invested, 2)
    return {
        "holdings": result,
        "summary": {
            "total_invested": round(total_invested, 2),
            "total_current": round(total_current, 2),
            "total_gain_loss": total_gain,
            "total_gain_loss_pct": round((total_gain / total_invested * 100), 2) if total_invested else 0,
            "count": len(result),
        },
    }

@api_router.put("/holdings/{holding_id}")
async def update_holding(holding_id: str, holding: HoldingCreate, user=Depends(get_current_user)):
    update = {
        "name": holding.name, "ticker": holding.ticker, "isin": holding.isin,
        "category": holding.category, "quantity": holding.quantity,
        "buy_price": holding.buy_price, "buy_date": holding.buy_date,
    }
    result = await db.holdings.update_one(
        {"_id": ObjectId(holding_id), "user_id": user["id"]}, {"$set": update}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Holding not found")
    return {"message": "Updated"}

@api_router.delete("/holdings/{holding_id}")
async def delete_holding(holding_id: str, user=Depends(get_current_user)):
    result = await db.holdings.delete_one({"_id": ObjectId(holding_id), "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(404, "Holding not found")
    return {"message": "Deleted"}

def _parse_cas_pdf(pdf_bytes: bytes, password: str = "") -> list:
    """Parse NSDL/CDSL CAS PDF to extract holdings."""
    holdings = []
    try:
        open_kwargs = {}
        if password:
            open_kwargs["password"] = password
        with pdfplumber.open(io.BytesIO(pdf_bytes), **open_kwargs) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    if not table:
                        continue
                    for row in table:
                        if not row:
                            continue
                        row_text = " ".join([str(c) for c in row if c])
                        isin_match = re.search(r'(INE[A-Z0-9]{7,10}|INF[A-Z0-9]{7,10})', row_text)
                        if isin_match:
                            isin = isin_match.group(1)
                            cells = [str(c).strip() if c else "" for c in row]
                            name = ""
                            qty = 0.0
                            price = 0.0
                            for i, cell in enumerate(cells):
                                if isin in cell:
                                    name_parts = cell.replace(isin, "").strip().split("\n")
                                    name = name_parts[0].strip() if name_parts else cell
                                    continue
                                if not name and cell and not re.match(r'^[\d,.\s]+$', cell) and len(cell) > 3:
                                    name = cell.strip()
                            nums = []
                            for cell in cells:
                                clean = cell.replace(",", "").replace(" ", "")
                                try:
                                    nums.append(float(clean))
                                except ValueError:
                                    pass
                            if len(nums) >= 2:
                                qty = nums[0]
                                price = nums[1] if len(nums) >= 3 else nums[-1]
                            is_mf = isin.startswith("INF")
                            category = "Mutual Fund" if is_mf else "Stock"
                            if name and qty > 0:
                                ticker = ""
                                if not is_mf:
                                    first_word = re.sub(r'[^A-Z]', '', name.split()[0].upper()) if name.split() else ""
                                    if first_word and len(first_word) >= 3:
                                        ticker = first_word + ".NS"
                                holdings.append({
                                    "name": name[:80],
                                    "ticker": ticker,
                                    "isin": isin,
                                    "category": category,
                                    "quantity": qty,
                                    "buy_price": price,
                                })
                if not tables:
                    text = page.extract_text() or ""
                    lines = text.split("\n")
                    for line in lines:
                        isin_match = re.search(r'(INE[A-Z0-9]{7,10}|INF[A-Z0-9]{7,10})', line)
                        if isin_match:
                            isin = isin_match.group(1)
                            name = line[:line.index(isin)].strip() if isin in line else ""
                            nums = re.findall(r'[\d,]+\.?\d*', line[line.index(isin):]) if isin in line else []
                            clean_nums = []
                            for n in nums:
                                try:
                                    clean_nums.append(float(n.replace(",", "")))
                                except ValueError:
                                    pass
                            qty = clean_nums[0] if clean_nums else 0
                            price = clean_nums[1] if len(clean_nums) >= 2 else 0
                            is_mf = isin.startswith("INF")
                            if name and qty > 0:
                                holdings.append({
                                    "name": name[:80],
                                    "ticker": "",
                                    "isin": isin,
                                    "category": "Mutual Fund" if is_mf else "Stock",
                                    "quantity": qty,
                                    "buy_price": price,
                                })
    except Exception as e:
        logger.error(f"CAS PDF parse error: {e}")
        raise HTTPException(400, f"Failed to parse PDF: {str(e)}")
    return holdings

@api_router.post("/holdings/upload-cas")
async def upload_cas(
    file: UploadFile = File(...),
    password: str = Form(""),
    user=Depends(get_current_user),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Please upload a PDF file")
    pdf_bytes = await file.read()
    if len(pdf_bytes) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 10MB)")
    parsed = _parse_cas_pdf(pdf_bytes, password)
    if not parsed:
        raise HTTPException(400, "No holdings found in the PDF. Please check the file format or password.")
    created = []
    now = datetime.now(timezone.utc).isoformat()
    for h in parsed:
        doc = {
            "user_id": user["id"],
            "name": h["name"],
            "ticker": h.get("ticker", ""),
            "isin": h["isin"],
            "category": h["category"],
            "quantity": h["quantity"],
            "buy_price": h.get("buy_price", 0),
            "buy_date": "",
            "source": "cas_upload",
            "created_at": now,
        }
        result = await db.holdings.insert_one(doc)
        doc["id"] = str(result.inserted_id)
        doc.pop("_id", None)
        created.append(doc)
    return {"message": f"Imported {len(created)} holdings from CAS", "holdings": created}

@api_router.delete("/holdings/clear-all")
async def clear_all_holdings(user=Depends(get_current_user)):
    result = await db.holdings.delete_many({"user_id": user["id"]})
    return {"message": f"Deleted {result.deleted_count} holdings"}

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
#  AI FINANCIAL ADVISOR
# ══════════════════════════════════════

class ChatMessage(BaseModel):
    message: str
    calculator_type: Optional[str] = None  # emi, sip, portfolio, compound, etc.
    calculator_params: Optional[dict] = None

class ChatResponse(BaseModel):
    response: str
    calculator_result: Optional[dict] = None

# Financial Calculator Functions
def calculate_sip_returns(monthly_investment: float, annual_return: float, years: int) -> dict:
    """Calculate SIP returns with compound interest"""
    months = years * 12
    monthly_rate = annual_return / 12 / 100
    
    if monthly_rate == 0:
        future_value = monthly_investment * months
    else:
        future_value = monthly_investment * (((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate)
    
    total_invested = monthly_investment * months
    wealth_gained = future_value - total_invested
    
    return {
        "monthly_investment": monthly_investment,
        "time_period_years": years,
        "expected_return_rate": annual_return,
        "total_invested": round(total_invested, 2),
        "future_value": round(future_value, 2),
        "wealth_gained": round(wealth_gained, 2),
        "absolute_returns": round((wealth_gained / total_invested) * 100, 2),
    }

def calculate_compound_interest(principal: float, annual_rate: float, years: int, compounding: str = "yearly") -> dict:
    """Calculate compound interest"""
    n = {"yearly": 1, "half-yearly": 2, "quarterly": 4, "monthly": 12}.get(compounding, 1)
    rate = annual_rate / 100
    
    amount = principal * ((1 + rate/n) ** (n * years))
    interest = amount - principal
    
    return {
        "principal": principal,
        "annual_rate": annual_rate,
        "time_years": years,
        "compounding": compounding,
        "maturity_amount": round(amount, 2),
        "interest_earned": round(interest, 2),
        "effective_rate": round(((amount/principal) ** (1/years) - 1) * 100, 2),
    }

def calculate_loan_emi_details(principal: float, annual_rate: float, tenure_years: int) -> dict:
    """Calculate EMI with full breakdown"""
    tenure_months = tenure_years * 12
    monthly_rate = annual_rate / 12 / 100
    
    if monthly_rate == 0:
        emi = principal / tenure_months
    else:
        emi = principal * monthly_rate * ((1 + monthly_rate) ** tenure_months) / (((1 + monthly_rate) ** tenure_months) - 1)
    
    total_payment = emi * tenure_months
    total_interest = total_payment - principal
    
    return {
        "loan_amount": principal,
        "interest_rate": annual_rate,
        "tenure_years": tenure_years,
        "tenure_months": tenure_months,
        "monthly_emi": round(emi, 2),
        "total_payment": round(total_payment, 2),
        "total_interest": round(total_interest, 2),
        "interest_to_principal_ratio": round((total_interest / principal) * 100, 2),
    }

def calculate_portfolio_returns(investments: list, years: int) -> dict:
    """Calculate weighted portfolio returns"""
    total_invested = sum(inv.get("amount", 0) for inv in investments)
    weighted_return = sum(
        (inv.get("amount", 0) / total_invested) * inv.get("expected_return", 0) 
        for inv in investments if total_invested > 0
    )
    
    future_value = total_invested * ((1 + weighted_return/100) ** years)
    
    return {
        "total_invested": total_invested,
        "weighted_avg_return": round(weighted_return, 2),
        "time_years": years,
        "projected_value": round(future_value, 2),
        "projected_gain": round(future_value - total_invested, 2),
        "breakdown": investments,
    }

def calculate_tax_savings_80c(investments: dict) -> dict:
    """Calculate tax savings under Section 80C"""
    limit_80c = 150000
    total_claimed = min(sum(investments.values()), limit_80c)
    
    # Tax slabs for FY 2025-26 (New Regime)
    tax_saved_30_percent = total_claimed * 0.30  # Highest slab
    tax_saved_20_percent = total_claimed * 0.20
    
    return {
        "section_80c_limit": limit_80c,
        "investments": investments,
        "total_claimed": total_claimed,
        "remaining_limit": limit_80c - total_claimed,
        "tax_saved_30_slab": round(tax_saved_30_percent, 2),
        "tax_saved_20_slab": round(tax_saved_20_percent, 2),
        "recommendation": "Maximize 80C limit for optimal tax savings" if total_claimed < limit_80c else "80C limit fully utilized",
    }

def calculate_fire_number(monthly_expenses: float, withdrawal_rate: float = 4) -> dict:
    """Calculate FIRE (Financial Independence Retire Early) number"""
    annual_expenses = monthly_expenses * 12
    fire_number = annual_expenses * (100 / withdrawal_rate)
    
    return {
        "monthly_expenses": monthly_expenses,
        "annual_expenses": annual_expenses,
        "withdrawal_rate": withdrawal_rate,
        "fire_number": round(fire_number, 2),
        "explanation": f"You need ₹{round(fire_number/100000, 2)} lakhs to be financially independent at {withdrawal_rate}% withdrawal rate",
    }

FINANCIAL_ADVISOR_SYSTEM_PROMPT = """You are Visor, a friendly yet highly knowledgeable Indian Financial Advisor. You possess expertise equivalent to:
- Chartered Accountant (CA)
- Chartered Financial Analyst (CFA)
- Financial Risk Manager (FRM)
- ACCA qualified
- MBA in Finance from IIM

## Your Core Competencies:

### 1. Indian Tax Laws & Planning
- Income Tax Act 1961 - All sections (80C, 80D, 80CCD, 80G, 80E, 80EE, 80TTA, etc.)
- New Tax Regime vs Old Tax Regime comparison
- Capital Gains Tax (Short-term & Long-term)
- TDS provisions and compliance
- GST implications on investments
- Tax-saving investment instruments (ELSS, PPF, NPS, ULIP)
- HRA, LTA, Standard Deduction rules
- Advance Tax and TDS deadlines

### 2. Investment Knowledge
- Indian Equity Markets (NSE, BSE, NIFTY 50, Sensex)
- Mutual Funds (Equity, Debt, Hybrid, ELSS, Index, ETFs)
- Fixed Income (FDs, RDs, Bonds, NCDs, Government Securities)
- PPF, EPF, NPS, VPF
- Gold (Physical, SGB, Gold ETFs, Digital Gold)
- Silver, Copper, and other commodities (MCX)
- Real Estate investment considerations
- REITs and InvITs
- International investing (US stocks, Mutual Funds)

### 3. Financial Regulations
- SEBI regulations
- RBI guidelines
- IRDAI (Insurance)
- PFRDA (NPS/Pension)
- Banking regulations

### 4. Risk Management
- Risk profiling (Conservative, Moderate, Aggressive)
- Asset allocation strategies
- Diversification principles
- Emergency fund planning
- Insurance (Term, Health, ULIP analysis)

### 5. Financial Planning
- Goal-based investing
- Retirement planning (FIRE calculations)
- Education planning
- Marriage planning
- House purchase planning
- Estate planning basics

## Built-in Calculators You Can Use:
- **SIP Calculator**: Calculate SIP returns with compounding
- **EMI Calculator**: Loan EMI with amortization
- **Compound Interest**: FD/RD returns
- **Portfolio Returns**: Weighted average portfolio performance
- **Tax Savings (80C)**: Section 80C optimization
- **FIRE Calculator**: Financial Independence number

## User Context:
You have access to the user's financial data including:
- Income, Expenses, Investments
- Savings rate, EMI obligations
- Financial goals and progress
- Transaction history
- Age and risk profile

## Communication Style:
- Be friendly, educational, and supportive
- Explain complex concepts in simple Hindi-English (Hinglish) when appropriate
- Always provide specific numbers and calculations
- Give actionable recommendations
- Cite relevant sections/rules when discussing taxes
- Compare options with pros and cons
- Use Indian currency (₹) and Indian number system (lakhs, crores)

## Important Guidelines:
- Never provide specific stock tips or guarantee returns
- Always mention that past performance doesn't guarantee future returns
- Recommend consulting a registered financial advisor for large decisions
- Be transparent about risks involved in any investment
- Consider the user's specific situation before giving advice

When user asks for calculations, use the calculator tools provided and explain the results."""

@api_router.post("/ai-advisor/chat", response_model=ChatResponse)
async def chat_with_advisor(chat_msg: ChatMessage, user=Depends(get_current_user)):
    """Chat with the AI Financial Advisor"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except ImportError:
        raise HTTPException(status_code=500, detail="AI service not available")
    
    # Get user's financial context
    transactions = await db.transactions.find({"user_id": user["id"]}, {"_id": 0}).to_list(1000)
    goals = await db.goals.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    loans = await db.loans.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    assets = await db.fixed_assets.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    
    # Calculate financial summary
    total_income = sum(t["amount"] for t in transactions if t["type"] == "income")
    total_expenses = sum(t["amount"] for t in transactions if t["type"] == "expense")
    total_investments = sum(t["amount"] for t in transactions if t["type"] == "investment")
    savings_rate = ((total_income - total_expenses) / total_income * 100) if total_income > 0 else 0
    
    # Calculate age from DOB
    user_age = None
    if user.get("dob"):
        try:
            dob = datetime.strptime(user["dob"], "%Y-%m-%d")
            user_age = (datetime.now() - dob).days // 365
        except:
            pass
    
    # Build financial context
    financial_context = f"""
## Current User Financial Profile:
- **Name**: {user.get('full_name', 'User')}
- **Age**: {user_age or 'Not provided'} years
- **Account Created**: {user.get('created_at', 'N/A')[:10] if user.get('created_at') else 'N/A'}

## Financial Summary (All Time):
- **Total Income**: ₹{total_income:,.0f}
- **Total Expenses**: ₹{total_expenses:,.0f}
- **Total Investments**: ₹{total_investments:,.0f}
- **Net Savings**: ₹{(total_income - total_expenses):,.0f}
- **Savings Rate**: {savings_rate:.1f}%
- **Investment Rate**: {(total_investments/total_income*100) if total_income > 0 else 0:.1f}%

## Investment Breakdown:
{chr(10).join([f"- {cat}: ₹{sum(t['amount'] for t in transactions if t['type']=='investment' and t['category']==cat):,.0f}" for cat in set(t['category'] for t in transactions if t['type']=='investment')])}

## Expense Categories:
{chr(10).join([f"- {cat}: ₹{sum(t['amount'] for t in transactions if t['type']=='expense' and t['category']==cat):,.0f}" for cat in set(t['category'] for t in transactions if t['type']=='expense')])}

## Active Loans:
{chr(10).join([f"- {l['name']}: ₹{l['principal_amount']:,.0f} at {l['interest_rate']}% ({l['tenure_months']} months)" for l in loans]) if loans else 'No active loans'}

## Fixed Assets:
{chr(10).join([f"- {a['name']}: ₹{a.get('current_value', a['purchase_value']):,.0f}" for a in assets]) if assets else 'No fixed assets recorded'}

## Financial Goals:
{chr(10).join([f"- {g['title']}: ₹{g['current_amount']:,.0f} / ₹{g['target_amount']:,.0f} ({(g['current_amount']/g['target_amount']*100):.0f}% complete)" for g in goals]) if goals else 'No goals set'}
"""

    # Handle calculator requests
    calculator_result = None
    if chat_msg.calculator_type and chat_msg.calculator_params:
        params = chat_msg.calculator_params
        try:
            if chat_msg.calculator_type == "sip":
                calculator_result = calculate_sip_returns(
                    params.get("monthly_investment", 10000),
                    params.get("annual_return", 12),
                    params.get("years", 10)
                )
            elif chat_msg.calculator_type == "emi":
                calculator_result = calculate_loan_emi_details(
                    params.get("principal", 5000000),
                    params.get("annual_rate", 8.5),
                    params.get("tenure_years", 20)
                )
            elif chat_msg.calculator_type == "compound":
                calculator_result = calculate_compound_interest(
                    params.get("principal", 100000),
                    params.get("annual_rate", 7),
                    params.get("years", 5),
                    params.get("compounding", "yearly")
                )
            elif chat_msg.calculator_type == "portfolio":
                calculator_result = calculate_portfolio_returns(
                    params.get("investments", []),
                    params.get("years", 10)
                )
            elif chat_msg.calculator_type == "tax_80c":
                calculator_result = calculate_tax_savings_80c(params.get("investments", {}))
            elif chat_msg.calculator_type == "fire":
                calculator_result = calculate_fire_number(
                    params.get("monthly_expenses", 50000),
                    params.get("withdrawal_rate", 4)
                )
        except Exception as e:
            logger.error(f"Calculator error: {e}")
    
    # Get or create chat session
    session_id = f"advisor_{user['id']}"
    
    # Load chat history
    history = await db.chat_history.find(
        {"user_id": user["id"], "type": "advisor"}
    ).sort("created_at", -1).limit(20).to_list(20)
    history.reverse()
    
    # Build message with context
    user_message_text = f"""
{financial_context}

---
**User Question**: {chat_msg.message}
"""
    
    if calculator_result:
        user_message_text += f"\n\n**Calculator Result ({chat_msg.calculator_type})**: {calculator_result}"
    
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message=FINANCIAL_ADVISOR_SYSTEM_PROMPT
        ).with_model("openai", "gpt-4o")
        
        # Note: History is already managed by session_id, we don't need to replay it
        # Just send the current message with context
        
        # Send message and get response
        response = await chat.send_message(UserMessage(text=user_message_text))
        
        # Store messages in database
        now = datetime.now(timezone.utc).isoformat()
        await db.chat_history.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "type": "advisor",
            "role": "user",
            "content": chat_msg.message,
            "created_at": now,
        })
        await db.chat_history.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "type": "advisor",
            "role": "assistant",
            "content": response,
            "created_at": now,
        })
        
        return ChatResponse(response=response, calculator_result=calculator_result)
        
    except Exception as e:
        logger.error(f"AI Advisor error: {e}")
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

@api_router.get("/ai-advisor/history")
async def get_chat_history(user=Depends(get_current_user)):
    """Get chat history with AI advisor"""
    history = await db.chat_history.find(
        {"user_id": user["id"], "type": "advisor"},
        {"_id": 0}
    ).sort("created_at", 1).to_list(100)
    return history

@api_router.delete("/ai-advisor/history")
async def clear_chat_history(user=Depends(get_current_user)):
    """Clear chat history"""
    await db.chat_history.delete_many({"user_id": user["id"], "type": "advisor"})
    return {"message": "Chat history cleared"}

@api_router.post("/ai-advisor/calculate/{calc_type}")
async def run_calculator(calc_type: str, params: dict, user=Depends(get_current_user)):
    """Run a financial calculator"""
    try:
        if calc_type == "sip":
            return calculate_sip_returns(
                params.get("monthly_investment", 10000),
                params.get("annual_return", 12),
                params.get("years", 10)
            )
        elif calc_type == "emi":
            return calculate_loan_emi_details(
                params.get("principal", 5000000),
                params.get("annual_rate", 8.5),
                params.get("tenure_years", 20)
            )
        elif calc_type == "compound":
            return calculate_compound_interest(
                params.get("principal", 100000),
                params.get("annual_rate", 7),
                params.get("years", 5),
                params.get("compounding", "yearly")
            )
        elif calc_type == "portfolio":
            return calculate_portfolio_returns(
                params.get("investments", []),
                params.get("years", 10)
            )
        elif calc_type == "tax_80c":
            return calculate_tax_savings_80c(params.get("investments", {}))
        elif calc_type == "fire":
            return calculate_fire_number(
                params.get("monthly_expenses", 50000),
                params.get("withdrawal_rate", 4)
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown calculator: {calc_type}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ══════════════════════════════════════
#  EXPORT ENDPOINTS (Excel & PDF)
# ══════════════════════════════════════

from fastapi.responses import StreamingResponse
import io

@api_router.get("/books/export/{report_type}/{format}")
async def export_report(
    report_type: str,  # ledger, pnl, balance
    format: str,  # excel, pdf
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user=Depends(get_current_user)
):
    """Export financial reports as Excel or PDF"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
    from fpdf import FPDF
    
    user_id = user["id"]
    user_name = user.get("full_name", "User")
    
    # Default to current FY if no dates provided
    if not start_date or not end_date:
        fy_start, fy_end = get_indian_fy_dates()
        start_date = start_date or fy_start.strftime("%Y-%m-%d")
        end_date = end_date or fy_end.strftime("%Y-%m-%d")
    
    if format == "excel":
        wb = Workbook()
        ws = wb.active
        
        # Styling
        header_font = Font(bold=True, size=12, color="FFFFFF")
        header_fill = PatternFill(start_color="3B82F6", end_color="3B82F6", fill_type="solid")
        title_font = Font(bold=True, size=16)
        subtitle_font = Font(bold=True, size=11, color="666666")
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        if report_type == "ledger":
            ws.title = "General Ledger"
            
            # Title
            ws.merge_cells('A1:G1')
            ws['A1'] = f"GENERAL LEDGER - {user_name}"
            ws['A1'].font = title_font
            ws['A2'] = f"Period: {start_date} to {end_date}"
            ws['A2'].font = subtitle_font
            ws['A3'] = f"Generated: {datetime.now().strftime('%d-%b-%Y %H:%M')}"
            ws['A3'].font = subtitle_font
            
            # Get ledger data
            query = {"user_id": user_id, "date": {"$gte": start_date, "$lte": end_date}}
            txns = await db.transactions.find(query, {"_id": 0}).sort("date", 1).to_list(2000)
            
            # Process transactions into ledger entries
            row = 5
            
            # Headers
            headers = ['Date', 'Particulars', 'Voucher Ref', 'Account', 'Debit (₹)', 'Credit (₹)', 'Balance (₹)']
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=row, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal='center')
                cell.border = border
            
            row += 1
            balance = 0
            
            for txn in txns:
                debit = txn['amount'] if txn['type'] == 'income' else 0
                credit = txn['amount'] if txn['type'] in ['expense', 'investment'] else 0
                balance += debit - credit
                
                ws.cell(row=row, column=1, value=txn['date']).border = border
                ws.cell(row=row, column=2, value=txn['description']).border = border
                ws.cell(row=row, column=3, value=f"TXN-{txn['id'][:8].upper()}").border = border
                ws.cell(row=row, column=4, value=txn['category']).border = border
                ws.cell(row=row, column=5, value=debit if debit > 0 else "").border = border
                ws.cell(row=row, column=6, value=credit if credit > 0 else "").border = border
                ws.cell(row=row, column=7, value=balance).border = border
                row += 1
            
            # Column widths
            ws.column_dimensions['A'].width = 12
            ws.column_dimensions['B'].width = 30
            ws.column_dimensions['C'].width = 15
            ws.column_dimensions['D'].width = 18
            ws.column_dimensions['E'].width = 14
            ws.column_dimensions['F'].width = 14
            ws.column_dimensions['G'].width = 14
            
        elif report_type == "pnl":
            ws.title = "Profit & Loss"
            
            # Title
            ws.merge_cells('A1:C1')
            ws['A1'] = f"INCOME & EXPENDITURE STATEMENT - {user_name}"
            ws['A1'].font = title_font
            ws['A2'] = f"Period: {start_date} to {end_date}"
            ws['A2'].font = subtitle_font
            
            # Get P&L data
            query = {"user_id": user_id, "date": {"$gte": start_date, "$lte": end_date}}
            txns = await db.transactions.find(query, {"_id": 0}).to_list(2000)
            
            total_income = sum(t["amount"] for t in txns if t["type"] == "income")
            total_expenses = sum(t["amount"] for t in txns if t["type"] == "expense")
            total_investments = sum(t["amount"] for t in txns if t["type"] == "investment")
            
            # Income by category
            income_cats = {}
            expense_cats = {}
            for t in txns:
                if t["type"] == "income":
                    income_cats[t["category"]] = income_cats.get(t["category"], 0) + t["amount"]
                elif t["type"] == "expense":
                    expense_cats[t["category"]] = expense_cats.get(t["category"], 0) + t["amount"]
            
            row = 4
            
            # Income Section
            ws.cell(row=row, column=1, value="INCOME").font = Font(bold=True, size=14, color="10B981")
            row += 1
            
            for cat, amt in sorted(income_cats.items(), key=lambda x: -x[1]):
                ws.cell(row=row, column=1, value=cat)
                ws.cell(row=row, column=3, value=amt)
                row += 1
            
            ws.cell(row=row, column=1, value="TOTAL INCOME").font = Font(bold=True)
            ws.cell(row=row, column=3, value=total_income).font = Font(bold=True, color="10B981")
            row += 2
            
            # Expenses Section
            ws.cell(row=row, column=1, value="EXPENDITURE").font = Font(bold=True, size=14, color="EF4444")
            row += 1
            
            for cat, amt in sorted(expense_cats.items(), key=lambda x: -x[1]):
                ws.cell(row=row, column=1, value=cat)
                ws.cell(row=row, column=3, value=amt)
                row += 1
            
            ws.cell(row=row, column=1, value="TOTAL EXPENDITURE").font = Font(bold=True)
            ws.cell(row=row, column=3, value=total_expenses).font = Font(bold=True, color="EF4444")
            row += 2
            
            # Surplus/Deficit
            surplus = total_income - total_expenses
            label = "SURPLUS" if surplus >= 0 else "DEFICIT"
            ws.cell(row=row, column=1, value=f"{label} FOR THE PERIOD").font = Font(bold=True, size=14)
            ws.cell(row=row, column=3, value=abs(surplus)).font = Font(bold=True, size=14, color="10B981" if surplus >= 0 else "EF4444")
            
            ws.column_dimensions['A'].width = 30
            ws.column_dimensions['B'].width = 15
            ws.column_dimensions['C'].width = 18
            
        elif report_type == "balance":
            ws.title = "Balance Sheet"
            
            # Get balance sheet data
            query = {"user_id": user_id, "date": {"$lte": end_date}}
            txns = await db.transactions.find(query, {"_id": 0}).to_list(5000)
            assets = await db.fixed_assets.find({"user_id": user_id}, {"_id": 0}).to_list(100)
            loans = await db.loans.find({"user_id": user_id}, {"_id": 0}).to_list(100)
            
            total_income = sum(t["amount"] for t in txns if t["type"] == "income")
            total_expenses = sum(t["amount"] for t in txns if t["type"] == "expense")
            total_investments = sum(t["amount"] for t in txns if t["type"] == "investment")
            
            ws.merge_cells('A1:C1')
            ws['A1'] = f"STATEMENT OF FINANCIAL POSITION - {user_name}"
            ws['A1'].font = title_font
            ws['A2'] = f"As at: {end_date}"
            ws['A2'].font = subtitle_font
            
            row = 4
            
            # Assets
            ws.cell(row=row, column=1, value="I. ASSETS").font = Font(bold=True, size=14, color="3B82F6")
            row += 1
            
            # Fixed Assets
            total_fixed = sum(a.get("current_value", a["purchase_value"]) for a in assets)
            ws.cell(row=row, column=1, value="Fixed Assets")
            ws.cell(row=row, column=3, value=total_fixed)
            row += 1
            
            # Investments
            ws.cell(row=row, column=1, value="Investments")
            ws.cell(row=row, column=3, value=total_investments)
            row += 1
            
            # Cash & Bank
            cash_balance = total_income - total_expenses - total_investments
            ws.cell(row=row, column=1, value="Cash & Bank Balance")
            ws.cell(row=row, column=3, value=max(0, cash_balance))
            row += 1
            
            total_assets = total_fixed + total_investments + max(0, cash_balance)
            ws.cell(row=row, column=1, value="TOTAL ASSETS").font = Font(bold=True)
            ws.cell(row=row, column=3, value=total_assets).font = Font(bold=True, color="3B82F6")
            row += 2
            
            # Liabilities
            ws.cell(row=row, column=1, value="II. LIABILITIES").font = Font(bold=True, size=14, color="EF4444")
            row += 1
            
            total_liabilities = 0
            for loan in loans:
                ws.cell(row=row, column=1, value=loan["name"])
                ws.cell(row=row, column=3, value=loan.get("outstanding_principal", loan["principal_amount"]))
                total_liabilities += loan.get("outstanding_principal", loan["principal_amount"])
                row += 1
            
            ws.cell(row=row, column=1, value="TOTAL LIABILITIES").font = Font(bold=True)
            ws.cell(row=row, column=3, value=total_liabilities).font = Font(bold=True, color="EF4444")
            row += 2
            
            # Net Worth
            net_worth = total_assets - total_liabilities
            ws.cell(row=row, column=1, value="III. NET WORTH").font = Font(bold=True, size=14, color="10B981")
            row += 1
            ws.cell(row=row, column=1, value="Closing Net Worth").font = Font(bold=True)
            ws.cell(row=row, column=3, value=net_worth).font = Font(bold=True, color="10B981")
            
            ws.column_dimensions['A'].width = 25
            ws.column_dimensions['B'].width = 15
            ws.column_dimensions['C'].width = 18
        
        # Save to buffer
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        filename = f"Visor_{report_type.title()}_{end_date}.xlsx"
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    elif format == "pdf":
        # Create PDF using fpdf2
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Header
        pdf.set_font("Helvetica", "B", 20)
        pdf.set_text_color(59, 130, 246)  # Blue
        
        if report_type == "ledger":
            pdf.cell(0, 10, "GENERAL LEDGER", ln=True, align="C")
        elif report_type == "pnl":
            pdf.cell(0, 10, "INCOME & EXPENDITURE STATEMENT", ln=True, align="C")
        else:
            pdf.cell(0, 10, "STATEMENT OF FINANCIAL POSITION", ln=True, align="C")
        
        pdf.set_font("Helvetica", "", 12)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 8, f"User: {user_name}", ln=True, align="C")
        pdf.cell(0, 8, f"Period: {start_date} to {end_date}", ln=True, align="C")
        pdf.cell(0, 8, f"Generated: {datetime.now().strftime('%d-%b-%Y %H:%M')}", ln=True, align="C")
        pdf.ln(10)
        
        # Content
        query = {"user_id": user_id, "date": {"$gte": start_date, "$lte": end_date}}
        txns = await db.transactions.find(query, {"_id": 0}).sort("date", 1).to_list(2000)
        
        if report_type == "ledger":
            # Table header
            pdf.set_fill_color(59, 130, 246)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 10)
            
            pdf.cell(25, 8, "Date", border=1, fill=True)
            pdf.cell(60, 8, "Particulars", border=1, fill=True)
            pdf.cell(30, 8, "Category", border=1, fill=True)
            pdf.cell(25, 8, "Debit", border=1, fill=True, align="R")
            pdf.cell(25, 8, "Credit", border=1, fill=True, align="R")
            pdf.cell(25, 8, "Balance", border=1, fill=True, align="R")
            pdf.ln()
            
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", "", 9)
            
            balance = 0
            for txn in txns[:50]:  # Limit for PDF
                debit = txn['amount'] if txn['type'] == 'income' else 0
                credit = txn['amount'] if txn['type'] in ['expense', 'investment'] else 0
                balance += debit - credit
                
                pdf.cell(25, 7, txn['date'][:10], border=1)
                pdf.cell(60, 7, txn['description'][:25], border=1)
                pdf.cell(30, 7, txn['category'][:15], border=1)
                pdf.cell(25, 7, f"{debit:,.0f}" if debit > 0 else "-", border=1, align="R")
                pdf.cell(25, 7, f"{credit:,.0f}" if credit > 0 else "-", border=1, align="R")
                pdf.cell(25, 7, f"{balance:,.0f}", border=1, align="R")
                pdf.ln()
        
        elif report_type == "pnl":
            total_income = sum(t["amount"] for t in txns if t["type"] == "income")
            total_expenses = sum(t["amount"] for t in txns if t["type"] == "expense")
            
            # Income by category
            income_cats = {}
            expense_cats = {}
            for t in txns:
                if t["type"] == "income":
                    income_cats[t["category"]] = income_cats.get(t["category"], 0) + t["amount"]
                elif t["type"] == "expense":
                    expense_cats[t["category"]] = expense_cats.get(t["category"], 0) + t["amount"]
            
            # Income Section
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(16, 185, 129)  # Green
            pdf.cell(0, 10, "INCOME", ln=True)
            
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(0, 0, 0)
            
            for cat, amt in sorted(income_cats.items(), key=lambda x: -x[1]):
                pdf.cell(100, 8, cat)
                pdf.cell(50, 8, f"Rs. {amt:,.2f}", align="R")
                pdf.ln()
            
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(16, 185, 129)
            pdf.cell(100, 10, "TOTAL INCOME")
            pdf.cell(50, 10, f"Rs. {total_income:,.2f}", align="R")
            pdf.ln(15)
            
            # Expenses Section
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(239, 68, 68)  # Red
            pdf.cell(0, 10, "EXPENDITURE", ln=True)
            
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(0, 0, 0)
            
            for cat, amt in sorted(expense_cats.items(), key=lambda x: -x[1]):
                pdf.cell(100, 8, cat)
                pdf.cell(50, 8, f"Rs. {amt:,.2f}", align="R")
                pdf.ln()
            
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(239, 68, 68)
            pdf.cell(100, 10, "TOTAL EXPENDITURE")
            pdf.cell(50, 10, f"Rs. {total_expenses:,.2f}", align="R")
            pdf.ln(15)
            
            # Surplus/Deficit
            surplus = total_income - total_expenses
            pdf.set_font("Helvetica", "B", 16)
            if surplus >= 0:
                pdf.set_text_color(16, 185, 129)
                pdf.cell(100, 12, "SURPLUS FOR THE PERIOD")
            else:
                pdf.set_text_color(239, 68, 68)
                pdf.cell(100, 12, "DEFICIT FOR THE PERIOD")
            pdf.cell(50, 12, f"Rs. {abs(surplus):,.2f}", align="R")
        
        elif report_type == "balance":
            query = {"user_id": user_id, "date": {"$lte": end_date}}
            txns = await db.transactions.find(query, {"_id": 0}).to_list(5000)
            assets = await db.fixed_assets.find({"user_id": user_id}, {"_id": 0}).to_list(100)
            loans = await db.loans.find({"user_id": user_id}, {"_id": 0}).to_list(100)
            
            total_income = sum(t["amount"] for t in txns if t["type"] == "income")
            total_expenses = sum(t["amount"] for t in txns if t["type"] == "expense")
            total_investments = sum(t["amount"] for t in txns if t["type"] == "investment")
            cash_balance = total_income - total_expenses - total_investments
            
            # Assets
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(59, 130, 246)
            pdf.cell(0, 10, "I. ASSETS", ln=True)
            
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(0, 0, 0)
            
            total_fixed = sum(a.get("current_value", a["purchase_value"]) for a in assets)
            
            pdf.cell(100, 8, "Fixed Assets")
            pdf.cell(50, 8, f"Rs. {total_fixed:,.2f}", align="R")
            pdf.ln()
            
            pdf.cell(100, 8, "Investments")
            pdf.cell(50, 8, f"Rs. {total_investments:,.2f}", align="R")
            pdf.ln()
            
            pdf.cell(100, 8, "Cash & Bank Balance")
            pdf.cell(50, 8, f"Rs. {max(0, cash_balance):,.2f}", align="R")
            pdf.ln()
            
            total_assets = total_fixed + total_investments + max(0, cash_balance)
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(59, 130, 246)
            pdf.cell(100, 10, "TOTAL ASSETS")
            pdf.cell(50, 10, f"Rs. {total_assets:,.2f}", align="R")
            pdf.ln(15)
            
            # Liabilities
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(239, 68, 68)
            pdf.cell(0, 10, "II. LIABILITIES", ln=True)
            
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(0, 0, 0)
            
            total_liabilities = 0
            for loan in loans:
                outstanding = loan.get("outstanding_principal", loan["principal_amount"])
                pdf.cell(100, 8, loan["name"])
                pdf.cell(50, 8, f"Rs. {outstanding:,.2f}", align="R")
                pdf.ln()
                total_liabilities += outstanding
            
            if not loans:
                pdf.cell(100, 8, "No liabilities")
                pdf.ln()
            
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(239, 68, 68)
            pdf.cell(100, 10, "TOTAL LIABILITIES")
            pdf.cell(50, 10, f"Rs. {total_liabilities:,.2f}", align="R")
            pdf.ln(15)
            
            # Net Worth
            net_worth = total_assets - total_liabilities
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(16, 185, 129)
            pdf.cell(0, 10, "III. NET WORTH", ln=True)
            
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(100, 12, "Closing Net Worth")
            pdf.cell(50, 12, f"Rs. {net_worth:,.2f}", align="R")
        
        # Footer
        pdf.ln(20)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 8, "Generated by Visor Finance App", ln=True, align="C")
        
        # Save to buffer
        buffer = io.BytesIO()
        pdf.output(buffer)
        buffer.seek(0)
        
        filename = f"Visor_{report_type.title()}_{end_date}.pdf"
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    else:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'excel' or 'pdf'")

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
    await seed_market_data()
    asyncio.create_task(market_data_scheduler())

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
