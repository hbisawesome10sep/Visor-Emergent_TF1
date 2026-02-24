from fastapi import APIRouter, HTTPException, Depends
from typing import List
from database import db
from auth import get_current_user
from models import LoanCreate, LoanUpdate, LoanResponse, EMIScheduleItem
from config import LOAN_SENSITIVE_FIELDS
from encryption import encrypt_field, decrypt_field
from datetime import datetime, timezone, timedelta
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


def decrypt_sensitive_fields(doc: dict, dek: str, fields: list):
    """Decrypt sensitive fields in place."""
    for field in fields:
        val = doc.get(field, "")
        if val and isinstance(val, str) and val.startswith("ENC:"):
            doc[field] = decrypt_field(val, dek)


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


@router.get("/loans")
async def get_loans(user=Depends(get_current_user)):
    """Get all loans with calculated outstanding amounts"""
    loans = await db.loans.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    result = []
    dek = user.get("encryption_key", "")

    for loan in loans:
        if dek:
            decrypt_sensitive_fields(loan, dek, LOAN_SENSITIVE_FIELDS)

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


@router.post("/loans")
async def create_loan(loan: LoanCreate, user=Depends(get_current_user)):
    """Create a new loan"""
    loan_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    dek = user.get("encryption_key", "")

    emi = loan.emi_amount or calculate_emi(loan.principal_amount, loan.interest_rate, loan.tenure_months)

    account_number_raw = loan.account_number
    account_number_enc = encrypt_field(account_number_raw, dek) if dek and account_number_raw else account_number_raw

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
        "account_number": account_number_enc,
        "notes": loan.notes,
        "created_at": now,
    }
    await db.loans.insert_one(loan_doc)

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
        "account_number": account_number_raw,
        "notes": loan.notes,
        "created_at": now,
        "outstanding_principal": loan.principal_amount,
        "total_principal_paid": 0,
        "total_interest_paid": 0,
        "remaining_emis": loan.tenure_months,
    }


@router.get("/loans/{loan_id}")
async def get_loan_detail(loan_id: str, user=Depends(get_current_user)):
    """Get loan details with EMI schedule"""
    loan = await db.loans.find_one({"id": loan_id, "user_id": user["id"]}, {"_id": 0})
    if not loan:
        raise HTTPException(404, "Loan not found")

    dek = user.get("encryption_key", "")
    if dek:
        decrypt_sensitive_fields(loan, dek, LOAN_SENSITIVE_FIELDS)

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
    remaining_emis = loan["tenure_months"] - len(paid_emis)

    return {
        **loan,
        "emi_amount": emi,
        "outstanding_principal": round(outstanding, 2),
        "total_principal_paid": round(total_principal_paid, 2),
        "total_interest_paid": round(total_interest_paid, 2),
        "remaining_emis": remaining_emis,
        "schedule": schedule,
    }


@router.put("/loans/{loan_id}")
async def update_loan(loan_id: str, loan: LoanUpdate, user=Depends(get_current_user)):
    """Update a loan"""
    existing = await db.loans.find_one({"id": loan_id, "user_id": user["id"]}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Loan not found")

    dek = user.get("encryption_key", "")
    update_data = {k: v for k, v in loan.dict().items() if v is not None}

    if "account_number" in update_data and dek:
        update_data["account_number"] = encrypt_field(update_data["account_number"], dek)

    if "principal_amount" in update_data or "interest_rate" in update_data or "tenure_months" in update_data:
        principal = update_data.get("principal_amount", existing["principal_amount"])
        rate = update_data.get("interest_rate", existing["interest_rate"])
        tenure = update_data.get("tenure_months", existing["tenure_months"])
        update_data["emi_amount"] = calculate_emi(principal, rate, tenure)

    if update_data:
        await db.loans.update_one({"id": loan_id}, {"$set": update_data})

    updated = await db.loans.find_one({"id": loan_id}, {"_id": 0})
    if dek:
        decrypt_sensitive_fields(updated, dek, LOAN_SENSITIVE_FIELDS)
    return updated


@router.delete("/loans/{loan_id}")
async def delete_loan(loan_id: str, user=Depends(get_current_user)):
    """Delete a loan"""
    result = await db.loans.delete_one({"id": loan_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(404, "Loan not found")
    return {"message": "Loan deleted"}


@router.get("/emi-tracker/dashboard")
async def get_emi_tracker_dashboard(user=Depends(get_current_user)):
    """
    Get comprehensive EMI tracker dashboard with:
    - All active loans/EMIs summary
    - Upcoming EMI payments
    - Overall progress metrics
    - Monthly EMI burden
    """
    user_id = user["id"]
    dek = user.get("encryption_key", "")
    
    # Get all loans
    loans = await db.loans.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    
    # Get recurring EMI transactions from both bank and CC
    emi_txns = await db.transactions.find({
        "user_id": user_id,
        "category": "EMI",
        "is_recurring": True,
    }, {"_id": 0}).to_list(100)
    
    cc_emi_txns = await db.credit_card_transactions.find({
        "user_id": user_id,
        "category": "EMI",
    }, {"_id": 0}).to_list(100)
    
    # Process loans
    active_emis = []
    total_monthly_emi = 0
    total_outstanding = 0
    total_principal = 0
    total_paid = 0
    
    upcoming_payments = []
    today = datetime.now()
    current_month = today.strftime("%Y-%m")
    
    for loan in loans:
        if dek:
            decrypt_sensitive_fields(loan, dek, LOAN_SENSITIVE_FIELDS)
        
        emi = loan.get("emi_amount") or calculate_emi(
            loan["principal_amount"], 
            loan["interest_rate"], 
            loan["tenure_months"]
        )
        schedule = generate_emi_schedule(
            loan["principal_amount"],
            loan["interest_rate"],
            loan["tenure_months"],
            loan["start_date"],
            emi
        )
        
        paid_emis = [s for s in schedule if s["status"] == "paid"]
        current_emi = next((s for s in schedule if s["status"] == "current"), None)
        upcoming_emis = [s for s in schedule if s["status"] == "upcoming"][:3]
        
        total_principal_paid = sum(s["principal"] for s in paid_emis)
        total_interest_paid = sum(s["interest"] for s in paid_emis)
        outstanding = loan["principal_amount"] - total_principal_paid
        remaining_emis = loan["tenure_months"] - len(paid_emis)
        progress = (len(paid_emis) / loan["tenure_months"]) * 100 if loan["tenure_months"] > 0 else 0
        
        total_monthly_emi += emi
        total_outstanding += outstanding
        total_principal += loan["principal_amount"]
        total_paid += total_principal_paid + total_interest_paid
        
        # Add to active EMIs list
        active_emis.append({
            "id": loan["id"],
            "name": loan["name"],
            "loan_type": loan.get("loan_type", "Personal"),
            "lender": loan.get("lender", ""),
            "principal_amount": loan["principal_amount"],
            "interest_rate": loan["interest_rate"],
            "tenure_months": loan["tenure_months"],
            "emi_amount": emi,
            "outstanding": round(outstanding, 2),
            "total_paid": round(total_principal_paid + total_interest_paid, 2),
            "principal_paid": round(total_principal_paid, 2),
            "interest_paid": round(total_interest_paid, 2),
            "remaining_emis": remaining_emis,
            "paid_emis": len(paid_emis),
            "progress": round(progress, 1),
            "start_date": loan["start_date"],
            "next_emi_date": current_emi["date"] if current_emi else (upcoming_emis[0]["date"] if upcoming_emis else None),
            "source": "loan",
        })
        
        # Add upcoming payment
        if current_emi:
            upcoming_payments.append({
                "loan_id": loan["id"],
                "loan_name": loan["name"],
                "amount": emi,
                "due_date": current_emi["date"],
                "principal": current_emi["principal"],
                "interest": current_emi["interest"],
                "status": "due_this_month",
            })
    
    # Add recurring EMI transactions that aren't linked to loans
    for txn in emi_txns:
        # Check if this amount matches any loan EMI
        is_linked = any(abs(l["emi_amount"] - txn["amount"]) < 10 for l in active_emis)
        if not is_linked:
            active_emis.append({
                "id": txn["id"],
                "name": txn.get("description", "EMI Payment"),
                "loan_type": "Other",
                "lender": txn.get("payment_account_name", ""),
                "principal_amount": 0,
                "interest_rate": 0,
                "tenure_months": 0,
                "emi_amount": txn["amount"],
                "outstanding": 0,
                "total_paid": txn["amount"],
                "principal_paid": 0,
                "interest_paid": 0,
                "remaining_emis": 0,
                "paid_emis": 1,
                "progress": 0,
                "start_date": txn.get("date", ""),
                "next_emi_date": None,
                "source": "transaction",
                "is_recurring": True,
            })
            total_monthly_emi += txn["amount"]
    
    # Add CC EMIs
    for txn in cc_emi_txns:
        active_emis.append({
            "id": txn["id"],
            "name": txn.get("description", "Credit Card EMI"),
            "loan_type": "Credit Card EMI",
            "lender": txn.get("card_name", "Credit Card"),
            "principal_amount": 0,
            "interest_rate": 0,
            "tenure_months": 0,
            "emi_amount": txn["amount"],
            "outstanding": txn["amount"],
            "total_paid": 0,
            "principal_paid": 0,
            "interest_paid": 0,
            "remaining_emis": 0,
            "paid_emis": 0,
            "progress": 0,
            "start_date": txn.get("date", ""),
            "next_emi_date": None,
            "source": "credit_card",
        })
        total_monthly_emi += txn["amount"]
    
    # Sort active EMIs by outstanding amount
    active_emis.sort(key=lambda x: -x["outstanding"])
    
    # Sort upcoming payments by date
    upcoming_payments.sort(key=lambda x: x["due_date"])
    
    # Calculate summary stats
    overall_progress = (total_paid / (total_principal + total_outstanding)) * 100 if (total_principal + total_outstanding) > 0 else 0
    
    return {
        "summary": {
            "total_monthly_emi": round(total_monthly_emi, 2),
            "total_outstanding": round(total_outstanding, 2),
            "total_principal": round(total_principal, 2),
            "total_paid": round(total_paid, 2),
            "active_count": len([e for e in active_emis if e["remaining_emis"] > 0 or e["source"] != "loan"]),
            "overall_progress": round(overall_progress, 1),
        },
        "active_emis": active_emis,
        "upcoming_payments": upcoming_payments[:5],
        "this_month_total": sum(p["amount"] for p in upcoming_payments if p["status"] == "due_this_month"),
    }

