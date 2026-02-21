from pydantic import BaseModel
from typing import List, Optional


# ══════════════════════════════════════
#  AUTH MODELS
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


# ══════════════════════════════════════
#  TRANSACTION MODELS
# ══════════════════════════════════════

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
    buy_sell: Optional[str] = None
    units: Optional[float] = None
    price_per_unit: Optional[float] = None
    payment_mode: Optional[str] = "cash"
    payment_account_name: Optional[str] = "Cash"

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
    buy_sell: Optional[str] = None
    units: Optional[float] = None
    price_per_unit: Optional[float] = None
    payment_mode: Optional[str] = "cash"
    payment_account_name: Optional[str] = "Cash"
    created_at: str


# ══════════════════════════════════════
#  GOAL MODELS
# ══════════════════════════════════════

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


# ══════════════════════════════════════
#  AI CHAT MODELS
# ══════════════════════════════════════

class AIMessageCreate(BaseModel):
    message: str
    screen_context: Optional[str] = None


# ══════════════════════════════════════
#  BOOKKEEPING / FIXED ASSET MODELS
# ══════════════════════════════════════

class FixedAssetCreate(BaseModel):
    name: str
    category: str
    purchase_date: str
    purchase_value: float
    current_value: float
    depreciation_rate: float = 10.0
    notes: Optional[str] = None
    payment_mode: Optional[str] = "cash"
    payment_account_name: Optional[str] = "Cash"

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
    account_type: str
    account_group: str
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
    loan_type: str
    principal_amount: float
    interest_rate: float
    tenure_months: int
    start_date: str
    emi_amount: Optional[float] = None
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
    status: str


# ══════════════════════════════════════
#  RISK PROFILE MODELS
# ══════════════════════════════════════

class RiskProfileCreate(BaseModel):
    answers: list
    score: float
    profile: str
    breakdown: dict


# ══════════════════════════════════════
#  TAX DEDUCTION MODELS
# ══════════════════════════════════════

class UserTaxDeductionCreate(BaseModel):
    deduction_id: str
    section: str
    name: str
    limit: Optional[int] = None
    invested_amount: float = 0

class UserTaxDeductionUpdate(BaseModel):
    invested_amount: Optional[float] = None


# ══════════════════════════════════════
#  RECURRING TRANSACTION MODELS
# ══════════════════════════════════════

class RecurringCreate(BaseModel):
    name: str
    amount: float
    frequency: str
    category: str
    start_date: str
    end_date: Optional[str] = None
    day_of_month: int = 1
    notes: Optional[str] = None
    is_active: bool = True

class RecurringUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    frequency: Optional[str] = None
    category: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    day_of_month: Optional[int] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


# ══════════════════════════════════════
#  HOLDINGS MODELS
# ══════════════════════════════════════

class HoldingCreate(BaseModel):
    name: str
    ticker: str = ""
    isin: str = ""
    category: str = "Stock"
    quantity: float
    buy_price: float
    buy_date: str = ""


# ══════════════════════════════════════
#  AI ADVISOR MODELS
# ══════════════════════════════════════

class AdvisorChatMessage(BaseModel):
    message: str
    calculator_type: Optional[str] = None
    calculator_params: Optional[dict] = None

class AdvisorChatResponse(BaseModel):
    response: str
    calculator_result: Optional[dict] = None
