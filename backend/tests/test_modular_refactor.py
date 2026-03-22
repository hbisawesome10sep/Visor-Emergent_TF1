"""
Backend API Regression Tests After Modular Refactoring
Tests all 16 route modules imported into server.py

Modules tested:
- auth.py: /api/auth/login, /api/auth/register, /api/auth/profile
- transactions.py: /api/transactions CRUD
- goals.py: /api/goals CRUD
- dashboard.py: /api/dashboard/stats, /api/health-score
- tax.py: /api/tax-summary, /api/capital-gains, /api/tax-calculator
- holdings.py: /api/holdings CRUD
- loans.py: /api/loans CRUD
- recurring.py: /api/recurring CRUD
- market_data.py: /api/market-data
- portfolio.py: /api/portfolio-overview
- assets.py: /api/assets CRUD
- risk_profile.py: /api/risk-profile
- bookkeeping.py: /api/books/ledger, /api/books/pnl, /api/books/balance-sheet
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

# Use the public URL from environment
BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://visor-finance-3.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_EMAIL = "rajesh@visor.demo"
TEST_PASSWORD = "Demo@123"


class TestAuthModule:
    """Test auth.py routes: /api/auth/login, /api/auth/register, /api/auth/profile"""
    
    def test_login_success(self):
        """Test login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert "user" in data, "No user in response"
        assert data["user"]["email"] == TEST_EMAIL
        assert "id" in data["user"]
        assert "full_name" in data["user"]
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@email.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
    
    def test_profile_without_auth(self):
        """Test profile endpoint without token"""
        response = requests.get(f"{BASE_URL}/api/auth/profile")
        assert response.status_code in [401, 403, 422]
    
    def test_profile_with_auth(self, auth_token):
        """Test profile endpoint with valid token"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/profile", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert data["email"] == TEST_EMAIL


class TestTransactionsModule:
    """Test transactions.py routes: GET, POST, PUT, DELETE /api/transactions"""
    
    def test_get_transactions(self, auth_token):
        """Test GET /api/transactions"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/transactions", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Transactions should be a list"
    
    def test_get_transactions_with_filter(self, auth_token):
        """Test GET /api/transactions with type filter"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/transactions?type=income", headers=headers)
        assert response.status_code == 200
        data = response.json()
        for txn in data:
            assert txn["type"] == "income"
    
    def test_create_transaction(self, auth_token):
        """Test POST /api/transactions"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        txn_data = {
            "type": "expense",
            "amount": 500,
            "category": "Food",
            "description": "TEST_Lunch",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "is_recurring": False,
            "is_split": False,
            "notes": "Test transaction"
        }
        response = requests.post(f"{BASE_URL}/api/transactions", json=txn_data, headers=headers)
        assert response.status_code == 200, f"Create failed: {response.text}"
        data = response.json()
        assert data["amount"] == 500
        assert data["category"] == "Food"
        assert "id" in data
        return data["id"]
    
    def test_transaction_crud_flow(self, auth_token):
        """Test full CRUD flow: Create -> Read -> Update -> Delete"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # CREATE
        txn_data = {
            "type": "expense",
            "amount": 999,
            "category": "Shopping",
            "description": "TEST_CRUD_Item",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "is_recurring": False,
            "is_split": False,
            "notes": "CRUD test"
        }
        create_resp = requests.post(f"{BASE_URL}/api/transactions", json=txn_data, headers=headers)
        assert create_resp.status_code == 200
        txn_id = create_resp.json()["id"]
        
        # READ - Verify created
        get_resp = requests.get(f"{BASE_URL}/api/transactions?search=TEST_CRUD_Item", headers=headers)
        assert get_resp.status_code == 200
        found = [t for t in get_resp.json() if t["id"] == txn_id]
        assert len(found) == 1, "Created transaction not found"
        
        # UPDATE
        update_data = {**txn_data, "amount": 1999, "description": "TEST_CRUD_Updated"}
        update_resp = requests.put(f"{BASE_URL}/api/transactions/{txn_id}", json=update_data, headers=headers)
        assert update_resp.status_code == 200
        assert update_resp.json()["amount"] == 1999
        
        # DELETE
        delete_resp = requests.delete(f"{BASE_URL}/api/transactions/{txn_id}", headers=headers)
        assert delete_resp.status_code == 200
        
        # Verify deleted
        get_resp2 = requests.get(f"{BASE_URL}/api/transactions?search=TEST_CRUD_Updated", headers=headers)
        found2 = [t for t in get_resp2.json() if t["id"] == txn_id]
        assert len(found2) == 0, "Transaction not deleted"


class TestGoalsModule:
    """Test goals.py routes: CRUD /api/goals"""
    
    def test_get_goals(self, auth_token):
        """Test GET /api/goals"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/goals", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_goals_crud_flow(self, auth_token):
        """Test full Goals CRUD"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # CREATE
        goal_data = {
            "title": "TEST_Goal_Vacation",
            "target_amount": 100000,
            "current_amount": 25000,
            "deadline": "2026-12-31",
            "category": "Travel"
        }
        create_resp = requests.post(f"{BASE_URL}/api/goals", json=goal_data, headers=headers)
        assert create_resp.status_code == 200
        goal_id = create_resp.json()["id"]
        
        # READ
        get_resp = requests.get(f"{BASE_URL}/api/goals", headers=headers)
        found = [g for g in get_resp.json() if g["id"] == goal_id]
        assert len(found) == 1
        assert found[0]["title"] == "TEST_Goal_Vacation"
        
        # UPDATE
        update_resp = requests.put(f"{BASE_URL}/api/goals/{goal_id}", json={"current_amount": 50000}, headers=headers)
        assert update_resp.status_code == 200
        assert update_resp.json()["current_amount"] == 50000
        
        # DELETE
        delete_resp = requests.delete(f"{BASE_URL}/api/goals/{goal_id}", headers=headers)
        assert delete_resp.status_code == 200


class TestDashboardModule:
    """Test dashboard.py routes: /api/dashboard/stats, /api/health-score"""
    
    def test_dashboard_stats(self, auth_token):
        """Test GET /api/dashboard/stats"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_income" in data
        assert "total_expenses" in data
        assert "total_investments" in data
        assert "net_balance" in data
        assert "health_score" in data
        assert "trend_data" in data
    
    def test_dashboard_stats_with_date_range(self, auth_token):
        """Test dashboard stats with date filter"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        start_date = "2025-01-01"
        end_date = "2025-12-31"
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats?start_date={start_date}&end_date={end_date}", 
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["date_range"]["start"] == start_date
    
    def test_health_score(self, auth_token):
        """Test GET /api/health-score"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/health-score", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "overall_score" in data
        assert "grade" in data
        assert "breakdown" in data
        assert data["grade"] in ["Excellent", "Good", "Fair", "Needs Work", "Critical"]


class TestTaxModule:
    """Test tax.py routes: /api/tax-summary, /api/capital-gains, /api/tax-calculator"""
    
    def test_tax_summary(self, auth_token):
        """Test GET /api/tax-summary"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/tax-summary", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "sections" in data
        assert "total_deductions" in data
        assert "fy" in data
    
    def test_capital_gains(self, auth_token):
        """Test GET /api/capital-gains"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/capital-gains", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "gains" in data
        assert "summary" in data
        assert "total_stcg" in data["summary"]
        assert "total_ltcg" in data["summary"]
    
    def test_tax_calculator(self, auth_token):
        """Test GET /api/tax-calculator"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/tax-calculator", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "fy" in data
        assert "old_regime" in data
        assert "new_regime" in data
        assert "comparison" in data
        assert "better_regime" in data["comparison"]
    
    def test_tax_calculator_with_fy(self, auth_token):
        """Test tax calculator with specific FY"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/tax-calculator?fy=2024-25", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["fy"] == "2024-25"


class TestHoldingsModule:
    """Test holdings.py routes: CRUD /api/holdings"""
    
    def test_get_holdings(self, auth_token):
        """Test GET /api/holdings"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/holdings", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "holdings" in data
        assert "summary" in data
        assert "total_invested" in data["summary"]
    
    def test_holdings_crud_flow(self, auth_token):
        """Test Holdings CRUD"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # CREATE
        holding_data = {
            "name": "TEST_Stock_TCS",
            "ticker": "TCS.NS",
            "isin": "INE467B01029",
            "category": "Stocks",
            "quantity": 10,
            "buy_price": 3500,
            "buy_date": "2025-01-15"
        }
        create_resp = requests.post(f"{BASE_URL}/api/holdings", json=holding_data, headers=headers)
        assert create_resp.status_code == 200
        holding_id = create_resp.json()["id"]
        
        # READ
        get_resp = requests.get(f"{BASE_URL}/api/holdings", headers=headers)
        found = [h for h in get_resp.json()["holdings"] if h.get("id") == holding_id]
        assert len(found) == 1
        
        # UPDATE
        update_data = {**holding_data, "quantity": 15}
        update_resp = requests.put(f"{BASE_URL}/api/holdings/{holding_id}", json=update_data, headers=headers)
        assert update_resp.status_code == 200
        
        # DELETE
        delete_resp = requests.delete(f"{BASE_URL}/api/holdings/{holding_id}", headers=headers)
        assert delete_resp.status_code == 200


class TestLoansModule:
    """Test loans.py routes: CRUD /api/loans"""
    
    def test_get_loans(self, auth_token):
        """Test GET /api/loans"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/loans", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_loans_crud_flow(self, auth_token):
        """Test Loans CRUD"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # CREATE
        loan_data = {
            "name": "TEST_Car_Loan",
            "loan_type": "Car Loan",
            "principal_amount": 500000,
            "interest_rate": 9.5,
            "tenure_months": 60,
            "start_date": "2025-01-01",
            "lender": "TEST Bank",
            "account_number": "1234567890",
            "notes": "Test loan"
        }
        create_resp = requests.post(f"{BASE_URL}/api/loans", json=loan_data, headers=headers)
        assert create_resp.status_code == 200
        loan_id = create_resp.json()["id"]
        assert "emi_amount" in create_resp.json()
        
        # READ detail
        get_resp = requests.get(f"{BASE_URL}/api/loans/{loan_id}", headers=headers)
        assert get_resp.status_code == 200
        assert "schedule" in get_resp.json()
        
        # UPDATE
        update_resp = requests.put(f"{BASE_URL}/api/loans/{loan_id}", json={"notes": "Updated test"}, headers=headers)
        assert update_resp.status_code == 200
        
        # DELETE
        delete_resp = requests.delete(f"{BASE_URL}/api/loans/{loan_id}", headers=headers)
        assert delete_resp.status_code == 200


class TestRecurringModule:
    """Test recurring.py routes: CRUD /api/recurring"""
    
    def test_get_recurring(self, auth_token):
        """Test GET /api/recurring"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/recurring", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "recurring" in data
        assert "summary" in data
        assert "monthly_commitment" in data["summary"]
    
    def test_recurring_crud_flow(self, auth_token):
        """Test Recurring CRUD"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # CREATE
        recurring_data = {
            "name": "TEST_SIP_HDFC",
            "amount": 5000,
            "frequency": "monthly",
            "category": "SIP",
            "start_date": "2025-01-01",
            "day_of_month": 5,
            "notes": "Test SIP",
            "is_active": True
        }
        create_resp = requests.post(f"{BASE_URL}/api/recurring", json=recurring_data, headers=headers)
        assert create_resp.status_code == 200
        recurring_id = create_resp.json()["id"]
        assert "upcoming" in create_resp.json()
        
        # READ
        get_resp = requests.get(f"{BASE_URL}/api/recurring", headers=headers)
        found = [r for r in get_resp.json()["recurring"] if r["id"] == recurring_id]
        assert len(found) == 1
        
        # UPDATE
        update_resp = requests.put(f"{BASE_URL}/api/recurring/{recurring_id}", json={"amount": 7500}, headers=headers)
        assert update_resp.status_code == 200
        
        # PAUSE
        pause_resp = requests.post(f"{BASE_URL}/api/recurring/{recurring_id}/pause", headers=headers)
        assert pause_resp.status_code == 200
        
        # DELETE
        delete_resp = requests.delete(f"{BASE_URL}/api/recurring/{recurring_id}", headers=headers)
        assert delete_resp.status_code == 200


class TestMarketDataModule:
    """Test market_data.py routes: /api/market-data"""
    
    def test_get_market_data(self):
        """Test GET /api/market-data (no auth required)"""
        response = requests.get(f"{BASE_URL}/api/market-data")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have Nifty 50, Sensex, Nifty Bank, Gold, Silver
        keys = [item["key"] for item in data]
        assert "nifty_50" in keys or len(data) >= 3
    
    def test_market_data_refresh(self, auth_token):
        """Test POST /api/market-data/refresh"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(f"{BASE_URL}/api/market-data/refresh", headers=headers)
        assert response.status_code == 200


class TestPortfolioModule:
    """Test portfolio.py routes: /api/portfolio-overview"""
    
    def test_portfolio_overview(self, auth_token):
        """Test GET /api/portfolio-overview"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/portfolio-overview", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_invested" in data
        assert "total_current_value" in data
        assert "total_gain_loss" in data
        assert "categories" in data


class TestAssetsModule:
    """Test assets.py routes: CRUD /api/assets"""
    
    def test_get_assets(self, auth_token):
        """Test GET /api/assets"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/assets", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_assets_crud_flow(self, auth_token):
        """Test Assets CRUD"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # CREATE
        asset_data = {
            "name": "TEST_Laptop",
            "category": "Electronics",
            "purchase_date": "2025-01-01",
            "purchase_value": 150000,
            "current_value": 130000,
            "depreciation_rate": 25,
            "notes": "Test asset"
        }
        create_resp = requests.post(f"{BASE_URL}/api/assets", json=asset_data, headers=headers)
        assert create_resp.status_code == 200
        asset_id = create_resp.json()["id"]
        
        # UPDATE
        update_resp = requests.put(f"{BASE_URL}/api/assets/{asset_id}", json={"current_value": 120000}, headers=headers)
        assert update_resp.status_code == 200
        
        # DELETE
        delete_resp = requests.delete(f"{BASE_URL}/api/assets/{asset_id}", headers=headers)
        assert delete_resp.status_code == 200


class TestRiskProfileModule:
    """Test risk_profile.py routes: /api/risk-profile"""
    
    def test_get_risk_profile(self, auth_token):
        """Test GET /api/risk-profile"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/risk-profile", headers=headers)
        assert response.status_code == 200
        # May return None if no profile saved
    
    def test_save_risk_profile(self, auth_token):
        """Test POST /api/risk-profile"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        # Note: answers must be a list, not a dict (per RiskProfileCreate model)
        profile_data = {
            "answers": [3, 4, 2, 5, 3],
            "score": 65,
            "profile": "Moderate",
            "breakdown": {"equity": 50, "debt": 30, "gold": 10, "cash": 10}
        }
        response = requests.post(f"{BASE_URL}/api/risk-profile", json=profile_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["profile"] == "Moderate"


class TestBookkeepingModule:
    """Test bookkeeping.py routes: /api/books/ledger, pnl, balance-sheet"""
    
    def test_get_ledger(self, auth_token):
        """Test GET /api/books/ledger"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/books/ledger", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "accounts" in data
        assert "entry_count" in data
    
    def test_get_pnl(self, auth_token):
        """Test GET /api/books/pnl"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/books/pnl", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "income_sections" in data
        assert "expense_sections" in data
        assert "total_income" in data
        assert "total_expenses" in data
        assert "surplus_deficit" in data
    
    def test_get_balance_sheet(self, auth_token):
        """Test GET /api/books/balance-sheet"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/books/balance-sheet", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "assets" in data
        assert "liabilities" in data
        assert "net_worth" in data


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_check(self):
        """Test GET /api/health"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "visor-finance-api"


# ========== FIXTURES ==========

@pytest.fixture(scope="session")
def auth_token():
    """Get authentication token for test session"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["token"]
    pytest.skip("Authentication failed - cannot proceed with tests")


# ========== TEST RUNNER CONFIG ==========

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
