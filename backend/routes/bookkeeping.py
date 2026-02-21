from fastapi import APIRouter, Depends
from typing import Optional
from database import db
from auth import get_current_user
from routes.loans import calculate_emi, generate_emi_schedule
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


def get_indian_fy_dates():
    """Get current Indian Financial Year start and end dates."""
    now = datetime.now(timezone.utc)
    if now.month >= 4:
        fy_start = datetime(now.year, 4, 1, tzinfo=timezone.utc)
        fy_end = datetime(now.year + 1, 3, 31, tzinfo=timezone.utc)
    else:
        fy_start = datetime(now.year - 1, 4, 1, tzinfo=timezone.utc)
        fy_end = datetime(now.year, 3, 31, tzinfo=timezone.utc)
    return fy_start, fy_end


@router.get("/books/ledger")
async def get_ledger(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user=Depends(get_current_user)
):
    """Get General Ledger entries in double-entry format."""
    user_id = user["id"]

    if not start_date or not end_date:
        fy_start, fy_end = get_indian_fy_dates()
        start_date = start_date or fy_start.strftime("%Y-%m-%d")
        end_date = end_date or fy_end.strftime("%Y-%m-%d")

    query = {
        "user_id": user_id,
        "date": {"$gte": start_date, "$lte": end_date}
    }
    txns = await db.transactions.find(query, {"_id": 0}).sort("date", 1).to_list(2000)

    ledger_entries = []
    for txn in txns:
        if txn["type"] == "income":
            ledger_entries.append({
                "date": txn["date"],
                "account": "Cash/Bank",
                "particulars": f"Income - {txn['category']}: {txn.get('description', '')}",
                "debit": txn["amount"],
                "credit": 0,
                "transaction_id": txn["id"],
            })
            ledger_entries.append({
                "date": txn["date"],
                "account": f"Income - {txn['category']}",
                "particulars": txn.get("description", txn["category"]),
                "debit": 0,
                "credit": txn["amount"],
                "transaction_id": txn["id"],
            })
        elif txn["type"] == "expense":
            ledger_entries.append({
                "date": txn["date"],
                "account": f"Expense - {txn['category']}",
                "particulars": txn.get("description", txn["category"]),
                "debit": txn["amount"],
                "credit": 0,
                "transaction_id": txn["id"],
            })
            ledger_entries.append({
                "date": txn["date"],
                "account": "Cash/Bank",
                "particulars": f"Expense - {txn['category']}: {txn.get('description', '')}",
                "debit": 0,
                "credit": txn["amount"],
                "transaction_id": txn["id"],
            })
        elif txn["type"] == "investment":
            ledger_entries.append({
                "date": txn["date"],
                "account": f"Investment - {txn['category']}",
                "particulars": txn.get("description", txn["category"]),
                "debit": txn["amount"],
                "credit": 0,
                "transaction_id": txn["id"],
            })
            ledger_entries.append({
                "date": txn["date"],
                "account": "Cash/Bank",
                "particulars": f"Investment - {txn['category']}: {txn.get('description', '')}",
                "debit": 0,
                "credit": txn["amount"],
                "transaction_id": txn["id"],
            })

    accounts = {}
    for entry in ledger_entries:
        acc = entry["account"]
        if acc not in accounts:
            accounts[acc] = {"entries": [], "total_debit": 0, "total_credit": 0}
        accounts[acc]["entries"].append(entry)
        accounts[acc]["total_debit"] += entry["debit"]
        accounts[acc]["total_credit"] += entry["credit"]

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


@router.get("/books/pnl")
async def get_profit_loss(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user=Depends(get_current_user)
):
    """Get Profit & Loss (Income & Expenditure) Statement"""
    user_id = user["id"]

    if not start_date or not end_date:
        fy_start, fy_end = get_indian_fy_dates()
        start_date = start_date or fy_start.strftime("%Y-%m-%d")
        end_date = end_date or fy_end.strftime("%Y-%m-%d")

    query = {
        "user_id": user_id,
        "date": {"$gte": start_date, "$lte": end_date}
    }
    txns = await db.transactions.find(query, {"_id": 0}).to_list(2000)

    income_groups = {
        "A": {"name": "Revenue from Employment", "categories": ["Salary", "Bonus"], "items": {}},
        "B": {"name": "Income from Profession/Freelance", "categories": ["Freelance", "Consulting"], "items": {}},
        "C": {"name": "Income from Investments", "categories": ["Interest", "Dividend", "Capital Gains"], "items": {}},
        "D": {"name": "Other Income", "categories": ["Rental", "Other"], "items": {}},
    }

    expense_groups = {
        "E": {"name": "Living & Household Expenses", "categories": ["Food", "Groceries", "Utilities", "Rent", "Transport", "Shopping", "Entertainment", "Health"], "items": {}},
        "F": {"name": "Financial Obligations", "categories": ["EMI", "Insurance"], "items": {}},
        "G": {"name": "Taxes & Statutory Deductions", "categories": ["Tax", "TDS"], "items": {}},
        "H": {"name": "Education & Development", "categories": ["Education"], "items": {}},
        "I": {"name": "Other Expenses", "categories": ["Bank Charges", "Depreciation", "Other"], "items": {}},
    }

    total_income = 0
    total_expenses = 0
    total_investments = 0

    for txn in txns:
        cat = txn.get("category", "Other")
        amount = txn["amount"]

        if txn["type"] == "income":
            total_income += amount
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


@router.get("/books/balance-sheet")
async def get_balance_sheet(
    as_of_date: Optional[str] = None,
    user=Depends(get_current_user)
):
    """Get Balance Sheet as of a specific date"""
    user_id = user["id"]

    if not as_of_date:
        as_of_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    query = {"user_id": user_id, "date": {"$lte": as_of_date}}
    txns = await db.transactions.find(query, {"_id": 0}).to_list(5000)

    assets = await db.fixed_assets.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    goals = await db.goals.find({"user_id": user_id}, {"_id": 0}).to_list(100)

    total_income = sum(t["amount"] for t in txns if t["type"] == "income")
    total_expenses = sum(t["amount"] for t in txns if t["type"] == "expense")
    total_investments = sum(t["amount"] for t in txns if t["type"] == "investment")

    invest_by_cat = {}
    for t in txns:
        if t["type"] == "investment":
            cat = t.get("category", "Other")
            invest_by_cat[cat] = invest_by_cat.get(cat, 0) + t["amount"]

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

    cash_balance = total_income - total_expenses - total_investments

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

    loans = await db.loans.find({"user_id": user_id}, {"_id": 0}).to_list(100)

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
    net_worth = total_assets - total_liabilities
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
