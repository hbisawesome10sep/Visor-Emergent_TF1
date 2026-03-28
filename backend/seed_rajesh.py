"""
Seed script: Populate Rajesh's demo account with 6 months of realistic Mumbai salaried employee data.
"""
import asyncio
import random
from datetime import datetime, timedelta
from uuid import uuid4
import sys
sys.path.insert(0, "/app/backend")
from database import db

USER_ID = "6f3eccc2-577a-4ae9-aca1-669ee6bccfa3"  # rajesh@visor.demo
NOW = datetime.now()

# ─── Helpers ───
def uid(): return str(uuid4())
def iso(): return datetime.utcnow().isoformat()
def date_str(y, m, d): return f"{y}-{m:02d}-{d:02d}"

async def clear_existing():
    """Clear existing data for clean seed."""
    for coll in ["transactions", "holdings", "credit_cards", "credit_card_transactions",
                 "bank_accounts", "goals", "recurring", "insurance", "journal_entries",
                 "statement_hashes", "loans"]:
        await db[coll].delete_many({"user_id": USER_ID})
    print("Cleared existing data.")

async def seed_bank_account():
    """HDFC Savings Account"""
    doc = {
        "id": uid(), "user_id": USER_ID,
        "bank_name": "HDFC Bank", "account_name": "HDFC Savings - Andheri",
        "account_type": "savings", "balance": 142350.0,
        "is_default": True, "created_at": iso(),
    }
    await db.bank_accounts.insert_one(doc)
    print("Bank account created.")
    return doc["id"]

async def seed_credit_cards():
    """2 credit cards: HDFC Regalia + SBI SimplyCLICK"""
    cards = [
        {"id": uid(), "user_id": USER_ID, "card_name": "HDFC Regalia",
         "issuer": "HDFC Bank", "network": "Visa", "last_four": "4821",
         "credit_limit": 300000, "current_outstanding": 18750,
         "billing_date": 15, "due_date": 5, "is_active": True, "created_at": iso()},
        {"id": uid(), "user_id": USER_ID, "card_name": "SBI SimplyCLICK",
         "issuer": "SBI Card", "network": "Visa", "last_four": "7392",
         "credit_limit": 150000, "current_outstanding": 8420,
         "billing_date": 1, "due_date": 20, "is_active": True, "created_at": iso()},
        {"id": uid(), "user_id": USER_ID, "card_name": "Amazon Pay ICICI",
         "issuer": "ICICI Bank", "network": "Visa", "last_four": "5563",
         "credit_limit": 270000, "current_outstanding": 5200,
         "billing_date": 10, "due_date": 30, "is_active": True, "created_at": iso()},
    ]
    await db.credit_cards.insert_many(cards)
    print(f"Created {len(cards)} credit cards.")
    return [c["id"] for c in cards]

async def seed_goals():
    """Financial goals"""
    goals = [
        {"id": uid(), "user_id": USER_ID, "title": "Emergency Fund",
         "target_amount": 500000, "current_amount": 325000,
         "deadline": "2026-06-30", "category": "Safety", "created_at": iso()},
        {"id": uid(), "user_id": USER_ID, "title": "House Down Payment",
         "target_amount": 2000000, "current_amount": 480000,
         "deadline": "2028-12-31", "category": "Home", "created_at": iso()},
        {"id": uid(), "user_id": USER_ID, "title": "Goa Trip",
         "target_amount": 60000, "current_amount": 42000,
         "deadline": "2026-04-15", "category": "Travel", "created_at": iso()},
        {"id": uid(), "user_id": USER_ID, "title": "New MacBook Pro",
         "target_amount": 180000, "current_amount": 65000,
         "deadline": "2026-09-01", "category": "Purchase", "created_at": iso()},
    ]
    await db.goals.insert_many(goals)
    print(f"Created {len(goals)} goals.")

async def seed_holdings():
    """Stocks, Mutual Funds, Gold"""
    holdings = [
        # ── Stocks ──
        {"id": uid(), "user_id": USER_ID, "name": "Reliance Industries",
         "ticker": "RELIANCE.NS", "category": "Stock", "quantity": 8,
         "buy_price": 2450.0, "invested_value": 19600.0, "current_value": 0,
         "buy_date": "2025-06-15", "created_at": iso()},
        {"id": uid(), "user_id": USER_ID, "name": "TCS",
         "ticker": "TCS.NS", "category": "Stock", "quantity": 5,
         "buy_price": 3850.0, "invested_value": 19250.0, "current_value": 0,
         "buy_date": "2025-07-20", "created_at": iso()},
        {"id": uid(), "user_id": USER_ID, "name": "HDFC Bank",
         "ticker": "HDFCBANK.NS", "category": "Stock", "quantity": 12,
         "buy_price": 1620.0, "invested_value": 19440.0, "current_value": 0,
         "buy_date": "2025-08-10", "created_at": iso()},
        {"id": uid(), "user_id": USER_ID, "name": "Infosys",
         "ticker": "INFY.NS", "category": "Stock", "quantity": 10,
         "buy_price": 1480.0, "invested_value": 14800.0, "current_value": 0,
         "buy_date": "2025-09-05", "created_at": iso()},
        {"id": uid(), "user_id": USER_ID, "name": "Tata Motors",
         "ticker": "TATAMOTORS.NS", "category": "Stock", "quantity": 20,
         "buy_price": 780.0, "invested_value": 15600.0, "current_value": 0,
         "buy_date": "2025-10-18", "created_at": iso()},
        {"id": uid(), "user_id": USER_ID, "name": "Bajaj Finance",
         "ticker": "BAJFINANCE.NS", "category": "Stock", "quantity": 3,
         "buy_price": 7200.0, "invested_value": 21600.0, "current_value": 0,
         "buy_date": "2025-11-02", "created_at": iso()},
        # ── Mutual Funds ──
        {"id": uid(), "user_id": USER_ID, "name": "Parag Parikh Flexi Cap Fund - Direct Growth",
         "ticker": "INF879O01027", "isin": "INF879O01027", "category": "Mutual Fund",
         "quantity": 285.5, "buy_price": 70.12, "invested_value": 60000.0, "current_value": 0,
         "buy_date": "2025-04-15", "created_at": iso()},
        {"id": uid(), "user_id": USER_ID, "name": "Mirae Asset Large Cap Fund - Direct Growth",
         "ticker": "INF769K01EI0", "isin": "INF769K01EI0", "category": "Mutual Fund",
         "quantity": 510.2, "buy_price": 98.0, "invested_value": 50000.0, "current_value": 0,
         "buy_date": "2025-05-10", "created_at": iso()},
        {"id": uid(), "user_id": USER_ID, "name": "Axis ELSS Tax Saver Fund - Direct Growth",
         "ticker": "INF846K01DP8", "isin": "INF846K01DP8", "category": "Mutual Fund",
         "quantity": 420.8, "buy_price": 83.18, "invested_value": 35000.0, "current_value": 0,
         "buy_date": "2025-06-01", "created_at": iso()},
        {"id": uid(), "user_id": USER_ID, "name": "HDFC Mid-Cap Opportunities Fund - Direct Growth",
         "ticker": "INF179K01BB2", "isin": "INF179K01BB2", "category": "Mutual Fund",
         "quantity": 195.3, "buy_price": 128.0, "invested_value": 25000.0, "current_value": 0,
         "buy_date": "2025-07-15", "created_at": iso()},
        # ── Gold ──
        {"id": uid(), "user_id": USER_ID, "name": "Sovereign Gold Bond 2024-25 Series III",
         "ticker": "SGB", "category": "Gold", "quantity": 4,
         "buy_price": 6263.0, "invested_value": 25052.0, "current_value": 29640.0,
         "buy_date": "2025-02-15", "created_at": iso()},
        {"id": uid(), "user_id": USER_ID, "name": "Nippon India Gold ETF",
         "ticker": "GOLDBEES.NS", "category": "Gold", "quantity": 15,
         "buy_price": 5280.0, "invested_value": 79200.0, "current_value": 0,
         "buy_date": "2025-08-20", "created_at": iso()},
    ]
    await db.holdings.insert_many(holdings)
    print(f"Created {len(holdings)} holdings.")

async def seed_transactions(bank_account_id):
    """6 months of transactions: Oct 2025 – Mar 2026"""
    txns = []
    
    months = [
        (2025, 10), (2025, 11), (2025, 12),
        (2026, 1), (2026, 2), (2026, 3),
    ]
    
    for y, m in months:
        # Days in month
        if m == 12: next_m_start = datetime(y+1, 1, 1)
        else: next_m_start = datetime(y, m+1, 1)
        days_in = (next_m_start - datetime(y, m, 1)).days
        today_d = min(days_in, 22 if (y == 2026 and m == 3) else days_in)

        # ── INCOME ──
        # Salary (credited on 1st)
        salary_amt = 92000 + random.randint(-500, 500)
        txns.append({"type": "income", "amount": salary_amt, "category": "Salary",
                      "description": f"NEFT - Infosys Ltd - Salary {datetime(y,m,1).strftime('%b %Y')}",
                      "date": date_str(y, m, 1), "payment_mode": "bank",
                      "payment_account_name": "HDFC Savings - Andheri"})

        # Interest credit (every quarter: Dec, Mar)
        if m in [12, 3]:
            txns.append({"type": "income", "amount": round(random.uniform(820, 1150), 2),
                          "category": "Interest", "description": "Interest Credit - HDFC Savings Account",
                          "date": date_str(y, m, min(28, today_d)), "payment_mode": "bank",
                          "payment_account_name": "HDFC Savings - Andheri"})

        # Freelance income (occasional — Nov, Jan, Mar)
        if m in [11, 1, 3]:
            txns.append({"type": "income", "amount": random.choice([15000, 20000, 25000, 18000]),
                          "category": "Freelance", "description": f"UPI - Freelance project payment - {'WebDev' if m==11 else 'Data Dashboard' if m==1 else 'API Consulting'}",
                          "date": date_str(y, m, random.randint(10, min(20, today_d))),
                          "payment_mode": "upi", "payment_account_name": "HDFC Savings - Andheri"})

        # ── RENT ──
        txns.append({"type": "expense", "amount": 35000, "category": "Rent",
                      "description": "UPI - Rent payment - Andheri West flat",
                      "date": date_str(y, m, min(3, today_d)), "payment_mode": "upi",
                      "payment_account_name": "HDFC Savings - Andheri"})

        # ── GROCERIES (3-4 per month) ──
        for _ in range(random.randint(3, 5)):
            d = random.randint(1, today_d)
            store = random.choice(["BigBasket", "Blinkit", "Zepto", "DMart", "Nature's Basket"])
            amt = round(random.uniform(600, 2800), 2)
            txns.append({"type": "expense", "amount": amt, "category": "Groceries",
                          "description": f"UPI - {store} - groceries",
                          "date": date_str(y, m, d), "payment_mode": "upi",
                          "payment_account_name": "HDFC Savings - Andheri"})

        # ── FOOD & DINING (4-6 per month) ──
        for _ in range(random.randint(4, 7)):
            d = random.randint(1, today_d)
            vendor = random.choice(["Swiggy", "Zomato", "Starbucks", "Chaayos", "Pizza Hut",
                                     "McDonald's", "Haldiram's", "BBQ Nation", "Local Restaurant"])
            amt = round(random.uniform(200, 1600), 2)
            txns.append({"type": "expense", "amount": amt, "category": "Food & Dining",
                          "description": f"UPI - {vendor}",
                          "date": date_str(y, m, d), "payment_mode": "upi",
                          "payment_account_name": "HDFC Savings - Andheri"})

        # ── UTILITIES ──
        # Electricity
        txns.append({"type": "expense", "amount": round(random.uniform(1200, 2400), 2),
                      "category": "Electricity",
                      "description": "UPI - Adani Electricity Mumbai - Bill Payment",
                      "date": date_str(y, m, min(8, today_d)), "payment_mode": "upi",
                      "payment_account_name": "HDFC Savings - Andheri"})
        # Internet
        txns.append({"type": "expense", "amount": 999, "category": "Internet",
                      "description": "UPI - ACT Fibernet - Monthly Plan",
                      "date": date_str(y, m, min(5, today_d)), "payment_mode": "upi",
                      "payment_account_name": "HDFC Savings - Andheri"})
        # Mobile
        txns.append({"type": "expense", "amount": 599, "category": "Mobile Recharge",
                      "description": "UPI - Jio Prepaid Recharge",
                      "date": date_str(y, m, min(12, today_d)), "payment_mode": "upi",
                      "payment_account_name": "HDFC Savings - Andheri"})

        # ── TRANSPORT ──
        for _ in range(random.randint(3, 6)):
            d = random.randint(1, today_d)
            vendor = random.choice(["Uber", "Ola", "Mumbai Metro", "Mumbai Metro", "Rapido"])
            amt = round(random.uniform(80, 450), 2)
            txns.append({"type": "expense", "amount": amt, "category": "Transport",
                          "description": f"UPI - {vendor}",
                          "date": date_str(y, m, d), "payment_mode": "upi",
                          "payment_account_name": "HDFC Savings - Andheri"})

        # Fuel (car owner — once or twice a month)
        if random.random() > 0.3:
            txns.append({"type": "expense", "amount": round(random.uniform(2500, 4000), 2),
                          "category": "Fuel",
                          "description": f"UPI - {random.choice(['HP Petrol Pump', 'Indian Oil', 'Bharat Petroleum'])} - Fuel",
                          "date": date_str(y, m, random.randint(5, min(20, today_d))),
                          "payment_mode": "upi", "payment_account_name": "HDFC Savings - Andheri"})

        # ── SUBSCRIPTIONS ──
        txns.append({"type": "expense", "amount": 199, "category": "Subscriptions",
                      "description": "Netflix - Monthly Subscription",
                      "date": date_str(y, m, min(15, today_d)), "payment_mode": "bank",
                      "payment_account_name": "HDFC Savings - Andheri"})
        txns.append({"type": "expense", "amount": 119, "category": "Subscriptions",
                      "description": "Spotify Premium - Monthly",
                      "date": date_str(y, m, min(10, today_d)), "payment_mode": "bank",
                      "payment_account_name": "HDFC Savings - Andheri"})
        if random.random() > 0.5:
            txns.append({"type": "expense", "amount": 299, "category": "Subscriptions",
                          "description": "YouTube Premium - Monthly",
                          "date": date_str(y, m, min(18, today_d)), "payment_mode": "bank",
                          "payment_account_name": "HDFC Savings - Andheri"})

        # ── SHOPPING (1-3 per month) ──
        for _ in range(random.randint(1, 3)):
            d = random.randint(1, today_d)
            vendor = random.choice(["Amazon", "Flipkart", "Myntra", "Ajio", "Croma", "Decathlon"])
            amt = round(random.uniform(500, 5000), 2)
            txns.append({"type": "expense", "amount": amt, "category": "Shopping",
                          "description": f"UPI - {vendor} - Order",
                          "date": date_str(y, m, d), "payment_mode": "upi",
                          "payment_account_name": "HDFC Savings - Andheri"})

        # ── HEALTH ──
        if random.random() > 0.5:
            txns.append({"type": "expense", "amount": round(random.uniform(200, 1500), 2),
                          "category": "Health",
                          "description": f"UPI - {random.choice(['Apollo Pharmacy', '1mg', 'PharmEasy', 'Dr. Patils Clinic'])}",
                          "date": date_str(y, m, random.randint(1, today_d)),
                          "payment_mode": "upi", "payment_account_name": "HDFC Savings - Andheri"})

        # ── ENTERTAINMENT ──
        if random.random() > 0.4:
            vendor = random.choice(["BookMyShow - Movie", "PVR Cinemas", "Dream11"])
            txns.append({"type": "expense", "amount": round(random.uniform(300, 1200), 2),
                          "category": "Entertainment", "description": f"UPI - {vendor}",
                          "date": date_str(y, m, random.randint(1, today_d)),
                          "payment_mode": "upi", "payment_account_name": "HDFC Savings - Andheri"})

        # ── PERSONAL CARE ──
        if random.random() > 0.5:
            txns.append({"type": "expense", "amount": round(random.uniform(400, 800), 2),
                          "category": "Personal Care",
                          "description": f"UPI - {random.choice(['Urban Company - Salon', 'Fascino Salon'])}",
                          "date": date_str(y, m, random.randint(1, today_d)),
                          "payment_mode": "upi", "payment_account_name": "HDFC Savings - Andheri"})

        # ── MAINTENANCE (Society) ──
        txns.append({"type": "expense", "amount": 4500, "category": "Maintenance",
                      "description": "NEFT - Andheri Heights CHS - Society Maintenance",
                      "date": date_str(y, m, min(5, today_d)), "payment_mode": "bank",
                      "payment_account_name": "HDFC Savings - Andheri"})

        # ── INVESTMENTS (SIPs - monthly) ──
        # SIP 1: Parag Parikh Flexi Cap
        txns.append({"type": "investment", "amount": 10000, "category": "SIP",
                      "description": "SIP - Parag Parikh Flexi Cap Fund - Monthly",
                      "date": date_str(y, m, min(7, today_d)), "payment_mode": "bank",
                      "payment_account_name": "HDFC Savings - Andheri"})
        # SIP 2: Mirae Asset Large Cap
        txns.append({"type": "investment", "amount": 5000, "category": "SIP",
                      "description": "SIP - Mirae Asset Large Cap Fund - Monthly",
                      "date": date_str(y, m, min(10, today_d)), "payment_mode": "bank",
                      "payment_account_name": "HDFC Savings - Andheri"})
        # SIP 3: Axis ELSS (tax saver)
        txns.append({"type": "investment", "amount": 5000, "category": "SIP",
                      "description": "SIP - Axis ELSS Tax Saver Fund - Monthly",
                      "date": date_str(y, m, min(12, today_d)), "payment_mode": "bank",
                      "payment_account_name": "HDFC Savings - Andheri"})

        # Occasional lump-sum stock purchase
        if m in [10, 12, 2]:
            stock = random.choice(["Reliance Industries", "HDFC Bank", "Infosys"])
            txns.append({"type": "investment", "amount": random.choice([10000, 15000, 20000]),
                          "category": "Stocks",
                          "description": f"Zerodha - Buy {stock} shares",
                          "date": date_str(y, m, random.randint(10, min(20, today_d))),
                          "payment_mode": "bank", "payment_account_name": "HDFC Savings - Andheri"})

        # ── INSURANCE (quarterly) ──
        if m in [10, 1]:
            txns.append({"type": "expense", "amount": 6500, "category": "Insurance",
                          "description": "NEFT - HDFC Life - Term Plan Premium",
                          "date": date_str(y, m, min(15, today_d)), "payment_mode": "bank",
                          "payment_account_name": "HDFC Savings - Andheri"})
        if m == 12:
            txns.append({"type": "expense", "amount": 12000, "category": "Insurance",
                          "description": "NEFT - Star Health Insurance - Annual Premium",
                          "date": date_str(y, m, 20), "payment_mode": "bank",
                          "payment_account_name": "HDFC Savings - Andheri"})

        # ── CREDIT CARD PAYMENTS ──
        if m > 10 or y > 2025:  # start paying after first month
            txns.append({"type": "expense", "amount": round(random.uniform(12000, 22000), 2),
                          "category": "Credit Card",
                          "description": "NEFT - HDFC Credit Card Bill Payment - via Cred",
                          "date": date_str(y, m, min(4, today_d)), "payment_mode": "bank",
                          "payment_account_name": "HDFC Savings - Andheri"})
            txns.append({"type": "expense", "amount": round(random.uniform(5000, 12000), 2),
                          "category": "Credit Card",
                          "description": "NEFT - SBI SimplyCLICK Card Payment",
                          "date": date_str(y, m, min(18, today_d)), "payment_mode": "bank",
                          "payment_account_name": "HDFC Savings - Andheri"})

        # ── CASH WITHDRAWAL (ATM) ──
        if random.random() > 0.3:
            txns.append({"type": "expense", "amount": random.choice([2000, 3000, 5000]),
                          "category": "Cash",
                          "description": "ATM - Cash Withdrawal - HDFC ATM Andheri",
                          "date": date_str(y, m, random.randint(1, today_d)),
                          "payment_mode": "bank", "payment_account_name": "HDFC Savings - Andheri"})

        # ── MISCELLANEOUS ──
        # Donations (Diwali month)
        if m == 11:
            txns.append({"type": "expense", "amount": 5100, "category": "Donations",
                          "description": "UPI - Diwali donation - Siddhivinayak Temple",
                          "date": date_str(y, m, 12), "payment_mode": "upi",
                          "payment_account_name": "HDFC Savings - Andheri"})
        # Education (online course)
        if m in [11, 2]:
            txns.append({"type": "expense", "amount": random.choice([499, 799, 1299]),
                          "category": "Education",
                          "description": f"UPI - {random.choice(['Udemy', 'Coursera'])} - Course Purchase",
                          "date": date_str(y, m, random.randint(5, min(15, today_d))),
                          "payment_mode": "upi", "payment_account_name": "HDFC Savings - Andheri"})

        # ── UPI Transfers (personal) ──
        for _ in range(random.randint(1, 3)):
            d = random.randint(1, today_d)
            person = random.choice(["Amit", "Priya", "Vikram", "Sneha", "Rohan", "Neha", "Karan"])
            amt = random.choice([500, 1000, 1500, 2000, 2500])
            txns.append({"type": "expense", "amount": amt, "category": "Transfer",
                          "description": f"UPI - {person} - transfer",
                          "date": date_str(y, m, d), "payment_mode": "upi",
                          "payment_account_name": "HDFC Savings - Andheri"})

    # Build docs for insert
    docs = []
    for t in txns:
        docs.append({
            "id": uid(),
            "user_id": USER_ID,
            "type": t["type"],
            "amount": t["amount"],
            "category": t["category"],
            "description": t["description"],
            "date": t["date"],
            "is_recurring": False,
            "recurring_frequency": None,
            "is_split": False,
            "split_count": None,
            "notes": "",
            "buy_sell": None,
            "units": None,
            "price_per_unit": None,
            "payment_mode": t.get("payment_mode", "upi"),
            "payment_account_name": t.get("payment_account_name", "HDFC Savings - Andheri"),
            "is_flagged": False,
            "flagged_type": None,
            "is_approved": False,
            "created_at": iso(),
            "updated_at": iso(),
            "source": "seed",
        })

    await db.transactions.insert_many(docs)
    print(f"Created {len(docs)} transactions across 6 months.")
    return docs

async def seed_cc_transactions(card_ids):
    """Credit card transactions for 6 months"""
    hdfc_id, sbi_id, icici_id = card_ids
    cc_txns = []
    months = [(2025,10),(2025,11),(2025,12),(2026,1),(2026,2),(2026,3)]

    for y, m in months:
        if m == 12: next_m = datetime(y+1,1,1)
        else: next_m = datetime(y,m+1,1)
        days_in = (next_m - datetime(y,m,1)).days
        today_d = min(days_in, 22 if (y==2026 and m==3) else days_in)

        # HDFC Regalia card spending (lifestyle + travel)
        for _ in range(random.randint(3, 6)):
            d = random.randint(1, today_d)
            vendor, cat, amt = random.choice([
                ("Zara", "Shopping", random.uniform(2000, 8000)),
                ("Tanishq", "Shopping", random.uniform(3000, 15000)),
                ("MakeMyTrip", "Travel", random.uniform(2000, 12000)),
                ("Amazon", "Shopping", random.uniform(500, 5000)),
                ("Myntra", "Shopping", random.uniform(800, 4000)),
                ("Taj Lands End", "Food & Dining", random.uniform(2000, 6000)),
                ("Croma", "Shopping", random.uniform(1000, 8000)),
            ])
            cc_txns.append({"id": uid(), "user_id": USER_ID, "card_id": hdfc_id,
                "type": "expense", "amount": round(amt, 2), "category": cat,
                "description": f"{vendor}", "date": date_str(y,m,d),
                "created_at": iso()})

        # SBI SimplyCLICK (online purchases)
        for _ in range(random.randint(2, 4)):
            d = random.randint(1, today_d)
            vendor, cat, amt = random.choice([
                ("Flipkart", "Shopping", random.uniform(500, 3000)),
                ("BookMyShow", "Entertainment", random.uniform(300, 800)),
                ("Swiggy", "Food & Dining", random.uniform(300, 1200)),
                ("Uber", "Transport", random.uniform(200, 600)),
            ])
            cc_txns.append({"id": uid(), "user_id": USER_ID, "card_id": sbi_id,
                "type": "expense", "amount": round(amt, 2), "category": cat,
                "description": f"{vendor}", "date": date_str(y,m,d),
                "created_at": iso()})

        # Amazon Pay ICICI (Amazon purchases)
        for _ in range(random.randint(1, 3)):
            d = random.randint(1, today_d)
            amt = random.uniform(500, 6000)
            cc_txns.append({"id": uid(), "user_id": USER_ID, "card_id": icici_id,
                "type": "expense", "amount": round(amt, 2), "category": "Shopping",
                "description": "Amazon.in - Purchase", "date": date_str(y,m,d),
                "created_at": iso()})

    await db.credit_card_transactions.insert_many(cc_txns)
    print(f"Created {len(cc_txns)} credit card transactions.")

async def seed_insurance():
    """Insurance policies"""
    policies = [
        {"id": uid(), "user_id": USER_ID, "type": "term_life",
         "provider": "HDFC Life", "policy_name": "Click 2 Protect Life",
         "sum_assured": 10000000, "premium": 13000, "frequency": "semi-annual",
         "start_date": "2024-10-01", "end_date": "2054-10-01",
         "next_due": "2026-04-01", "created_at": iso()},
        {"id": uid(), "user_id": USER_ID, "type": "health",
         "provider": "Star Health", "policy_name": "Comprehensive Health Insurance",
         "sum_assured": 1000000, "premium": 12000, "frequency": "annual",
         "start_date": "2025-12-20", "end_date": "2026-12-19",
         "next_due": "2026-12-20", "created_at": iso()},
    ]
    await db.insurance.insert_many(policies)
    print(f"Created {len(policies)} insurance policies.")

async def seed_recurring():
    """Recurring transactions"""
    items = [
        {"id": uid(), "user_id": USER_ID, "title": "Monthly Rent",
         "amount": 35000, "type": "expense", "category": "Rent",
         "frequency": "monthly", "day_of_month": 3, "is_active": True,
         "next_execution": "2026-04-03", "payment_mode": "upi",
         "created_at": iso()},
        {"id": uid(), "user_id": USER_ID, "title": "SIP - Parag Parikh Flexi Cap",
         "amount": 10000, "type": "investment", "category": "SIP",
         "frequency": "monthly", "day_of_month": 7, "is_active": True,
         "next_execution": "2026-04-07", "payment_mode": "bank",
         "created_at": iso()},
        {"id": uid(), "user_id": USER_ID, "title": "SIP - Mirae Asset Large Cap",
         "amount": 5000, "type": "investment", "category": "SIP",
         "frequency": "monthly", "day_of_month": 10, "is_active": True,
         "next_execution": "2026-04-10", "payment_mode": "bank",
         "created_at": iso()},
        {"id": uid(), "user_id": USER_ID, "title": "SIP - Axis ELSS Tax Saver",
         "amount": 5000, "type": "investment", "category": "SIP",
         "frequency": "monthly", "day_of_month": 12, "is_active": True,
         "next_execution": "2026-04-12", "payment_mode": "bank",
         "created_at": iso()},
        {"id": uid(), "user_id": USER_ID, "title": "Netflix Subscription",
         "amount": 199, "type": "expense", "category": "Subscriptions",
         "frequency": "monthly", "day_of_month": 15, "is_active": True,
         "next_execution": "2026-04-15", "payment_mode": "bank",
         "created_at": iso()},
        {"id": uid(), "user_id": USER_ID, "title": "Spotify Premium",
         "amount": 119, "type": "expense", "category": "Subscriptions",
         "frequency": "monthly", "day_of_month": 10, "is_active": True,
         "next_execution": "2026-04-10", "payment_mode": "bank",
         "created_at": iso()},
        {"id": uid(), "user_id": USER_ID, "title": "Society Maintenance",
         "amount": 4500, "type": "expense", "category": "Maintenance",
         "frequency": "monthly", "day_of_month": 5, "is_active": True,
         "next_execution": "2026-04-05", "payment_mode": "bank",
         "created_at": iso()},
    ]
    await db.recurring.insert_many(items)
    print(f"Created {len(items)} recurring items.")

async def main():
    print("=== Seeding Rajesh's Demo Account ===\n")
    await clear_existing()
    bank_id = await seed_bank_account()
    card_ids = await seed_credit_cards()
    await seed_goals()
    await seed_holdings()
    txns = await seed_transactions(bank_id)
    await seed_cc_transactions(card_ids)
    await seed_insurance()
    await seed_recurring()

    # Summary
    inc = sum(t["amount"] for t in txns if t["type"] == "income")
    exp = sum(t["amount"] for t in txns if t["type"] == "expense")
    inv = sum(t["amount"] for t in txns if t["type"] == "investment")
    print(f"\n=== Seed Complete ===")
    print(f"Transactions: {len(txns)}")
    print(f"Total Income:      {inc:>12,.2f}")
    print(f"Total Expenses:    {exp:>12,.2f}")
    print(f"Total Investments: {inv:>12,.2f}")
    print(f"Net:               {inc - exp - inv:>12,.2f}")

asyncio.run(main())
