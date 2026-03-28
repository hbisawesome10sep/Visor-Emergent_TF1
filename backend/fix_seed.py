"""
Fix seed data: Update holdings with realistic current values + Add loans/EMIs + Add SIPs
"""
import asyncio
from uuid import uuid4
from datetime import datetime, timezone
import sys
sys.path.insert(0, "/app/backend")
from database import db

USER_ID = "6f3eccc2-577a-4ae9-aca1-669ee6bccfa3"

def uid(): return str(uuid4())
def iso(): return datetime.now(timezone.utc).isoformat()

async def fix_holdings():
    """Update holdings with realistic current_value (gains/losses)."""
    updates = {
        "Reliance Industries": {"current_value": 23200, "buy_price": 2450},      # +18% gain
        "TCS":                 {"current_value": 21500, "buy_price": 3850},       # +12% gain
        "HDFC Bank":           {"current_value": 22800, "buy_price": 1620},       # +17% gain
        "Infosys":             {"current_value": 13400, "buy_price": 1480},       # -9% loss
        "Tata Motors":         {"current_value": 18700, "buy_price": 780},        # +20% gain
        "Bajaj Finance":       {"current_value": 24300, "buy_price": 7200},       # +13% gain
        "Parag Parikh Flexi Cap Fund - Direct Growth": {"current_value": 72500, "buy_price": 70.12},  # +21%
        "Mirae Asset Large Cap Fund - Direct Growth":  {"current_value": 57000, "buy_price": 98.0},   # +14%
        "Axis ELSS Tax Saver Fund - Direct Growth":    {"current_value": 38900, "buy_price": 83.18},  # +11%
        "HDFC Mid-Cap Opportunities Fund - Direct":    {"current_value": 30200, "buy_price": 128.0},  # +21%
        "Sovereign Gold Bond 2024-25 Series III":      {"current_value": 32400, "buy_price": 6263.0}, # +29%
        "Nippon India Gold ETF":                       {"current_value": 94800, "buy_price": 5280.0}, # +20%
    }
    for name, vals in updates.items():
        result = await db.holdings.update_one(
            {"user_id": USER_ID, "name": {"$regex": f"^{name[:30]}"}},
            {"$set": {"current_value": vals["current_value"]}}
        )
        status = "updated" if result.modified_count > 0 else "not found"
        print(f"  {name[:40]:40s} → ₹{vals['current_value']:>8,} ({status})")
    print("Holdings updated with realistic current values.")

async def seed_sips():
    """Add SIP entries for the mutual funds."""
    # First check what collection SIPs use
    sips = [
        {"id": uid(), "user_id": USER_ID,
         "fund_name": "Parag Parikh Flexi Cap Fund - Direct Growth",
         "amount": 10000, "frequency": "monthly", "sip_date": 7,
         "start_date": "2025-04-15", "status": "active",
         "category": "Flexi Cap", "isin": "INF879O01027",
         "created_at": iso()},
        {"id": uid(), "user_id": USER_ID,
         "fund_name": "Mirae Asset Large Cap Fund - Direct Growth",
         "amount": 5000, "frequency": "monthly", "sip_date": 10,
         "start_date": "2025-05-10", "status": "active",
         "category": "Large Cap", "isin": "INF769K01EI0",
         "created_at": iso()},
        {"id": uid(), "user_id": USER_ID,
         "fund_name": "Axis ELSS Tax Saver Fund - Direct Growth",
         "amount": 5000, "frequency": "monthly", "sip_date": 12,
         "start_date": "2025-06-01", "status": "active",
         "category": "ELSS", "isin": "INF846K01DP8",
         "created_at": iso()},
        {"id": uid(), "user_id": USER_ID,
         "fund_name": "HDFC Mid-Cap Opportunities Fund - Direct Growth",
         "amount": 3000, "frequency": "monthly", "sip_date": 15,
         "start_date": "2025-07-15", "status": "active",
         "category": "Mid Cap", "isin": "INF179K01BB2",
         "created_at": iso()},
    ]
    await db.sips.delete_many({"user_id": USER_ID})
    await db.sips.insert_many(sips)
    print(f"Created {len(sips)} SIPs.")

async def seed_loans():
    """Add realistic loans for EMI tracking."""
    await db.loans.delete_many({"user_id": USER_ID})
    
    loans = [
        {
            "id": uid(), "user_id": USER_ID,
            "name": "Home Loan - Andheri West 2BHK",
            "loan_type": "home_loan",
            "principal_amount": 4500000,   # ₹45 Lakh
            "interest_rate": 8.5,           # 8.5% p.a.
            "tenure_months": 240,           # 20 years
            "start_date": "2024-06-01",
            "emi_amount": 39015,            # Calculated EMI
            "lender": "HDFC Ltd",
            "account_number": "HDFC-HL-2024-89271",
            "notes": "Home loan for Andheri West 2BHK flat. Pre-approved with 85% LTV.",
            "created_at": iso(),
        },
        {
            "id": uid(), "user_id": USER_ID,
            "name": "Car Loan - Hyundai Creta",
            "loan_type": "car_loan",
            "principal_amount": 1000000,   # ₹10 Lakh
            "interest_rate": 9.25,          # 9.25% p.a.
            "tenure_months": 60,            # 5 years
            "start_date": "2025-01-15",
            "emi_amount": 20878,            # Calculated EMI
            "lender": "ICICI Bank",
            "account_number": "ICICI-AL-2025-54832",
            "notes": "Car loan for Hyundai Creta SX(O). 80% financing.",
            "created_at": iso(),
        },
        {
            "id": uid(), "user_id": USER_ID,
            "name": "Education Loan - MBA Program",
            "loan_type": "education_loan",
            "principal_amount": 800000,    # ₹8 Lakh
            "interest_rate": 10.5,          # 10.5% p.a.
            "tenure_months": 84,            # 7 years
            "start_date": "2023-08-01",
            "emi_amount": 13378,            # Calculated EMI
            "lender": "SBI",
            "account_number": "SBI-EL-2023-33921",
            "notes": "Education loan for MBA at IIM. Moratorium period ended Aug 2025.",
            "created_at": iso(),
        },
    ]
    
    await db.loans.insert_many(loans)
    print(f"Created {len(loans)} loans:")
    for l in loans:
        print(f"  {l['name']:40s} | ₹{l['principal_amount']:>12,} | {l['interest_rate']}% | {l['tenure_months']}mo | EMI: ₹{l['emi_amount']:,}")

async def main():
    print("=== Fixing Demo Data ===\n")
    
    print("1. Updating holdings with realistic current values...")
    await fix_holdings()
    
    print("\n2. Seeding SIPs...")
    await seed_sips()
    
    print("\n3. Seeding Loans/EMIs...")
    await seed_loans()
    
    print("\n=== Done! ===")

asyncio.run(main())
