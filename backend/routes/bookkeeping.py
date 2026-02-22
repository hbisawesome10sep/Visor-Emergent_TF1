from fastapi import APIRouter, Depends
from typing import Optional
from database import db
from auth import get_current_user
from routes.loans import calculate_emi, generate_emi_schedule
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


def get_indian_fy_dates(fy: str = None):
    """Get Indian Financial Year start and end dates."""
    if fy:
        parts = fy.split("-")
        start_year = int(parts[0])
        return (
            datetime(start_year, 4, 1, tzinfo=timezone.utc),
            datetime(start_year + 1, 3, 31, tzinfo=timezone.utc),
        )
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
    search: Optional[str] = None,
    account_name: Optional[str] = None,
    user=Depends(get_current_user),
):
    """Get General Ledger from journal entries (double-entry)."""
    user_id = user["id"]

    if not start_date or not end_date:
        fy_start, fy_end = get_indian_fy_dates()
        start_date = start_date or fy_start.strftime("%Y-%m-%d")
        end_date = end_date or fy_end.strftime("%Y-%m-%d")

    query = {
        "user_id": user_id,
        "date": {"$gte": start_date, "$lte": end_date},
    }
    if search:
        query["$or"] = [
            {"narration": {"$regex": search, "$options": "i"}},
            {"entries.account_name": {"$regex": search, "$options": "i"}},
        ]
    if account_name:
        query["entries.account_name"] = account_name

    journal_docs = await db.journal_entries.find(
        query, {"_id": 0}
    ).sort("date", 1).to_list(2000)

    # Build accounts from journal entries
    accounts = {}
    for jdoc in journal_docs:
        # Skip entries without the 'entries' field
        if "entries" not in jdoc or not jdoc["entries"]:
            continue
        for entry in jdoc["entries"]:
            acc = entry["account_name"]
            if acc not in accounts:
                accounts[acc] = {
                    "account_type": entry["account_type"],
                    "account_group": entry["account_group"],
                    "entries": [],
                    "total_debit": 0,
                    "total_credit": 0,
                }
            accounts[acc]["entries"].append({
                "date": jdoc.get("date", ""),
                "entry_number": jdoc.get("entry_number", 0),
                "narration": jdoc.get("narration", ""),
                "debit": entry.get("debit", 0),
                "credit": entry.get("credit", 0),
                "reference_type": jdoc.get("reference_type", ""),
                "reference_id": jdoc.get("reference_id", ""),
            })
            accounts[acc]["total_debit"] += entry["debit"]
            accounts[acc]["total_credit"] += entry["credit"]

    # Calculate running balances
    for acc_name, data in accounts.items():
        running = 0
        for entry in data["entries"]:
            running += entry["debit"] - entry["credit"]
            entry["balance"] = round(running, 2)
        data["closing_balance"] = round(running, 2)
        data["total_debit"] = round(data["total_debit"], 2)
        data["total_credit"] = round(data["total_credit"], 2)

    # If no journal entries, fall back to transaction-based ledger
    if not accounts:
        txns = await db.transactions.find(
            {"user_id": user_id, "date": {"$gte": start_date, "$lte": end_date}},
            {"_id": 0}
        ).sort("date", 1).to_list(2000)

        for txn in txns:
            payment_name = txn.get("payment_account_name", "Cash")
            pay_acc = f"{payment_name} A/c" if payment_name != "Cash" else "Cash A/c"
            cat_acc = f"{txn['category']} A/c"

            for acc, debit, credit in [
                (pay_acc if txn["type"] == "income" else cat_acc,
                 txn["amount"] if txn["type"] in ("income",) else txn["amount"],
                 0 if txn["type"] in ("income",) else 0),
            ]:
                pass  # Fallback placeholder

            if txn["type"] == "income":
                for acc, d, c in [(pay_acc, txn["amount"], 0), (cat_acc, 0, txn["amount"])]:
                    if acc not in accounts:
                        accounts[acc] = {"account_type": "", "account_group": "", "entries": [], "total_debit": 0, "total_credit": 0}
                    accounts[acc]["entries"].append({"date": txn["date"], "narration": f"{txn['category']}: {txn.get('description','')}", "debit": d, "credit": c})
                    accounts[acc]["total_debit"] += d
                    accounts[acc]["total_credit"] += c
            elif txn["type"] == "expense":
                for acc, d, c in [(cat_acc, txn["amount"], 0), (pay_acc, 0, txn["amount"])]:
                    if acc not in accounts:
                        accounts[acc] = {"account_type": "", "account_group": "", "entries": [], "total_debit": 0, "total_credit": 0}
                    accounts[acc]["entries"].append({"date": txn["date"], "narration": f"{txn['category']}: {txn.get('description','')}", "debit": d, "credit": c})
                    accounts[acc]["total_debit"] += d
                    accounts[acc]["total_credit"] += c
            elif txn["type"] == "investment":
                for acc, d, c in [(cat_acc, txn["amount"], 0), (pay_acc, 0, txn["amount"])]:
                    if acc not in accounts:
                        accounts[acc] = {"account_type": "", "account_group": "", "entries": [], "total_debit": 0, "total_credit": 0}
                    accounts[acc]["entries"].append({"date": txn["date"], "narration": f"{txn['category']}: {txn.get('description','')}", "debit": d, "credit": c})
                    accounts[acc]["total_debit"] += d
                    accounts[acc]["total_credit"] += c

        for data in accounts.values():
            running = 0
            for entry in data["entries"]:
                running += entry["debit"] - entry["credit"]
                entry["balance"] = round(running, 2)
            data["closing_balance"] = round(running, 2)

    total_entries = sum(len(data["entries"]) for data in accounts.values())

    return {
        "fy_start": start_date,
        "fy_end": end_date,
        "accounts": accounts,
        "entry_count": total_entries,
        "account_count": len(accounts),
    }


@router.get("/books/pnl")
async def get_profit_loss(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user=Depends(get_current_user),
):
    """Get Profit & Loss Statement based on double-entry journal entries."""
    user_id = user["id"]

    if not start_date or not end_date:
        fy_start, fy_end = get_indian_fy_dates()
        start_date = start_date or fy_start.strftime("%Y-%m-%d")
        end_date = end_date or fy_end.strftime("%Y-%m-%d")

    # Aggregate from journal entries - Nominal accounts only
    pipeline = [
        {"$match": {
            "user_id": user_id,
            "date": {"$gte": start_date, "$lte": end_date},
        }},
        {"$unwind": "$entries"},
        {"$match": {"entries.account_type": "Nominal"}},
        {"$group": {
            "_id": {
                "account_name": "$entries.account_name",
                "account_group": "$entries.account_group",
            },
            "total_debit": {"$sum": "$entries.debit"},
            "total_credit": {"$sum": "$entries.credit"},
        }},
    ]

    results = await db.journal_entries.aggregate(pipeline).to_list(500)

    income_items = {}
    expense_items = {}
    total_income = 0
    total_expenses = 0

    for r in results:
        name = r["_id"]["account_name"].replace(" A/c", "")
        group = r["_id"]["account_group"]
        amount = round(abs(r["total_credit"] - r["total_debit"]), 2)

        if group == "Income":
            income_items[name] = income_items.get(name, 0) + amount
            total_income += amount
        elif group == "Expense":
            expense_items[name] = expense_items.get(name, 0) + amount
            total_expenses += amount

    # If no journal data, fall back to transactions
    if not income_items and not expense_items:
        txns = await db.transactions.find(
            {"user_id": user_id, "date": {"$gte": start_date, "$lte": end_date}},
            {"_id": 0}
        ).to_list(2000)
        for txn in txns:
            if txn["type"] == "income":
                income_items[txn["category"]] = income_items.get(txn["category"], 0) + txn["amount"]
                total_income += txn["amount"]
            elif txn["type"] == "expense":
                expense_items[txn["category"]] = expense_items.get(txn["category"], 0) + txn["amount"]
                total_expenses += txn["amount"]

    # Group income sections (Indian standard)
    income_groups = {
        "A": {"name": "Revenue from Employment", "categories": ["Salary", "Bonus"], "items": {}},
        "B": {"name": "Income from Profession/Freelance", "categories": ["Freelance", "Consulting", "Business Income", "Commission"], "items": {}},
        "C": {"name": "Income from Investments", "categories": ["Interest", "Dividends", "Capital Gains", "Rental Income"], "items": {}},
        "D": {"name": "Other Income", "categories": ["Pension", "Refund"], "items": {}},
    }
    expense_groups = {
        "E": {"name": "Living & Household Expenses", "categories": ["Food & Dining", "Groceries", "Utilities", "Electricity", "Water", "Rent", "Transport", "Fuel", "Shopping", "Entertainment", "Health", "Medicine", "Internet", "Mobile Recharge", "Subscriptions", "Personal Care", "Clothing", "Home Maintenance"], "items": {}},
        "F": {"name": "Financial Obligations", "categories": ["EMI", "Loan Repayment", "Insurance"], "items": {}},
        "G": {"name": "Taxes & Statutory Deductions", "categories": ["Taxes", "TDS"], "items": {}},
        "H": {"name": "Education & Development", "categories": ["Education"], "items": {}},
        "I": {"name": "Other Expenses", "categories": ["Bank Charges", "Travel", "Gifts", "Donations"], "items": {}},
    }

    for cat, amount in income_items.items():
        placed = False
        for group in income_groups.values():
            if cat in group["categories"] or any(c.lower() in cat.lower() for c in group["categories"]):
                group["items"][cat] = group["items"].get(cat, 0) + amount
                placed = True
                break
        if not placed:
            income_groups["D"]["items"][cat] = income_groups["D"]["items"].get(cat, 0) + amount

    for cat, amount in expense_items.items():
        placed = False
        for group in expense_groups.values():
            if cat in group["categories"] or any(c.lower() in cat.lower() for c in group["categories"]):
                group["items"][cat] = group["items"].get(cat, 0) + amount
                placed = True
                break
        if not placed:
            expense_groups["I"]["items"][cat] = expense_groups["I"]["items"].get(cat, 0) + amount

    income_sections = [
        {
            "id": gid,
            "name": g["name"],
            "items": [{"category": k, "amount": v} for k, v in sorted(g["items"].items(), key=lambda x: -x[1])],
            "subtotal": sum(g["items"].values()),
        }
        for gid, g in income_groups.items()
        if g["items"]
    ]

    expense_sections = [
        {
            "id": gid,
            "name": g["name"],
            "items": [{"category": k, "amount": v} for k, v in sorted(g["items"].items(), key=lambda x: -x[1])],
            "subtotal": sum(g["items"].values()),
        }
        for gid, g in expense_groups.items()
        if g["items"]
    ]

    # Investment total from transactions (not nominal, but needed for allocation)
    total_investments = 0
    inv_txns = await db.transactions.find(
        {"user_id": user_id, "type": "investment", "date": {"$gte": start_date, "$lte": end_date}},
        {"_id": 0, "amount": 1}
    ).to_list(2000)
    total_investments = sum(t["amount"] for t in inv_txns)

    surplus = round(total_income - total_expenses, 2)

    return {
        "period_start": start_date,
        "period_end": end_date,
        "income_sections": income_sections,
        "expense_sections": expense_sections,
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "total_investments": round(total_investments, 2),
        "surplus_deficit": surplus,
        "allocation": {
            "to_savings": round(max(0, surplus * 0.4), 2),
            "to_investments": round(total_investments, 2),
            "retained": round(max(0, surplus - total_investments - (surplus * 0.4)), 2),
        },
    }


@router.get("/books/balance-sheet")
async def get_balance_sheet(
    as_of_date: Optional[str] = None,
    user=Depends(get_current_user),
):
    """Get Balance Sheet based on double-entry system (Indian standard)."""
    user_id = user["id"]
    if not as_of_date:
        as_of_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Aggregate all journal entries up to as_of_date
    pipeline = [
        {"$match": {"user_id": user_id, "date": {"$lte": as_of_date}}},
        {"$unwind": "$entries"},
        {"$group": {
            "_id": {
                "account_name": "$entries.account_name",
                "account_type": "$entries.account_type",
                "account_group": "$entries.account_group",
            },
            "total_debit": {"$sum": "$entries.debit"},
            "total_credit": {"$sum": "$entries.credit"},
        }},
    ]
    results = await db.journal_entries.aggregate(pipeline).to_list(500)

    # Classify accounts
    real_assets = []  # Real accounts with debit balance (assets)
    personal_assets = []  # Personal accounts with debit balance (receivables)
    nominal_income_total = 0
    nominal_expense_total = 0
    liabilities = []  # Credit balance accounts (what we owe)
    investment_assets = []

    for r in results:
        name = r["_id"]["account_name"]
        acc_type = r["_id"]["account_type"]
        acc_group = r["_id"]["account_group"]
        balance = round(r["total_debit"] - r["total_credit"], 2)

        if acc_type == "Nominal":
            if acc_group == "Income":
                nominal_income_total += abs(balance)
            elif acc_group == "Expense":
                nominal_expense_total += abs(balance)
        elif acc_type == "Real":
            if acc_group == "Asset":
                if balance > 0:
                    investment_assets.append({"name": name, "amount": balance})
                elif balance < 0:
                    liabilities.append({"name": name, "amount": abs(balance)})
        elif acc_type == "Personal":
            if balance > 0:
                personal_assets.append({"name": name, "amount": balance})
            elif balance < 0:
                liabilities.append({"name": name, "amount": abs(balance)})

    # Fixed assets from assets collection
    assets_docs = await db.fixed_assets.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    fixed_asset_items = []
    total_fixed_assets = 0
    total_depreciation = 0
    for asset in assets_docs:
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

    # Loans from loans collection
    loans = await db.loans.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    long_term_loan_items = []
    short_term_loan_items = []
    total_long_term = 0
    total_short_term = 0

    for loan in loans:
        emi = loan.get("emi_amount") or calculate_emi(loan["principal_amount"], loan["interest_rate"], loan["tenure_months"])
        schedule = generate_emi_schedule(loan["principal_amount"], loan["interest_rate"], loan["tenure_months"], loan["start_date"], emi)
        paid_emis = [s for s in schedule if s["status"] == "paid"]
        total_principal_paid = sum(s["principal"] for s in paid_emis)
        outstanding = loan["principal_amount"] - total_principal_paid
        remaining_emis = loan["tenure_months"] - len(paid_emis)

        short_term_portion = min(outstanding, emi * min(12, remaining_emis) * (loan["principal_amount"] / (loan["principal_amount"] + loan["interest_rate"] * loan["tenure_months"] / 1200)))
        long_term_portion = outstanding - short_term_portion

        if long_term_portion > 0:
            long_term_loan_items.append({"name": f"{loan['name']} ({loan['loan_type']})", "amount": round(long_term_portion, 2), "lender": loan.get("lender")})
            total_long_term += long_term_portion
        if short_term_portion > 0:
            short_term_loan_items.append({"name": f"{loan['name']} (Current Portion)", "amount": round(short_term_portion, 2)})
            total_short_term += short_term_portion

    # Build balance sheet
    inv_total = sum(a["amount"] for a in investment_assets)
    personal_total = sum(a["amount"] for a in personal_assets)
    net_fixed = round(total_fixed_assets - total_depreciation, 2)

    # Cash/Bank from Real/Personal asset accounts
    cash_bank_items = [a for a in investment_assets if "Cash" in a["name"] or "Bank" in a["name"]]
    other_investments = [a for a in investment_assets if "Cash" not in a["name"] and "Bank" not in a["name"]]
    cash_bank_total = sum(a["amount"] for a in cash_bank_items)
    other_inv_total = sum(a["amount"] for a in other_investments)

    non_current_assets = {
        "fixed_assets": {
            "items": fixed_asset_items,
            "gross_value": total_fixed_assets,
            "depreciation": round(total_depreciation, 2),
            "net_value": net_fixed,
        },
        "long_term_investments": {
            "items": [a for a in other_investments if a["amount"] > 0],
            "total": round(other_inv_total, 2),
        },
        "total": round(net_fixed + other_inv_total, 2),
    }

    current_assets = {
        "short_term_investments": {
            "items": [],
            "total": 0,
        },
        "cash_bank": {
            "items": cash_bank_items if cash_bank_items else [{"name": "Cash & Bank Balances", "amount": cash_bank_total}],
            "total": round(cash_bank_total, 2),
        },
        "receivables": {
            "items": personal_assets,
            "total": round(personal_total, 2),
        },
        "total": round(cash_bank_total + personal_total, 2),
    }

    total_assets = round(non_current_assets["total"] + current_assets["total"], 2)

    liability_total = sum(l["amount"] for l in liabilities)
    non_current_liabilities = {
        "long_term_borrowings": {"items": long_term_loan_items, "total": round(total_long_term, 2)},
        "total": round(total_long_term, 2),
    }
    current_liabilities = {
        "short_term_borrowings": {"items": short_term_loan_items, "total": round(total_short_term, 2)},
        "payables": {"items": liabilities, "total": round(liability_total, 2)},
        "total": round(total_short_term + liability_total, 2),
    }

    total_liabilities = round(non_current_liabilities["total"] + current_liabilities["total"], 2)
    surplus = round(nominal_income_total - nominal_expense_total, 2)
    net_worth = round(total_assets - total_liabilities, 2)

    return {
        "as_of_date": as_of_date,
        "assets": {
            "non_current": non_current_assets,
            "current": current_assets,
            "total": total_assets,
        },
        "liabilities": {
            "non_current": non_current_liabilities,
            "current": current_liabilities,
            "total": total_liabilities,
        },
        "net_worth": {
            "opening": 0,
            "surplus_for_period": surplus,
            "closing": net_worth,
        },
        "total_liabilities_and_net_worth": round(total_liabilities + net_worth, 2),
        "is_balanced": abs(total_assets - (total_liabilities + net_worth)) < 0.01,
    }
