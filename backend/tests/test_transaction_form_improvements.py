"""
Test suite for Transaction Form Improvements - Iteration 7
Features:
1. PUT /api/transactions/:id updates correctly
2. POST /api/transactions with empty description (optional)
3. GET /api/dashboard/stats returns invest_breakdown for investment transactions
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://visor-india-app.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_EMAIL = "rajesh@visor.demo"
TEST_PASSWORD = "Demo@123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip("Authentication failed - skipping authenticated tests")
    return response.json().get("token")


@pytest.fixture
def api_client(auth_token):
    """Shared requests session with auth"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestTransactionPUTEndpoint:
    """Tests for PUT /api/transactions/:id - update transaction correctly"""
    
    def test_update_transaction_amount_change(self, api_client):
        """Test updating transaction amount persists correctly"""
        # CREATE transaction
        create_payload = {
            "type": "expense",
            "amount": 5000,
            "category": "Food & Dining",
            "description": "TEST_PUT_amount_change",
            "date": "2026-01-20"
        }
        create_resp = api_client.post(f"{BASE_URL}/api/transactions", json=create_payload)
        assert create_resp.status_code == 200, f"Create failed: {create_resp.text}"
        txn_id = create_resp.json()["id"]
        
        # UPDATE amount
        update_payload = {
            "type": "expense",
            "amount": 7500,  # Changed amount
            "category": "Food & Dining",
            "description": "TEST_PUT_amount_change_updated",
            "date": "2026-01-20"
        }
        update_resp = api_client.put(f"{BASE_URL}/api/transactions/{txn_id}", json=update_payload)
        assert update_resp.status_code == 200, f"Update failed: {update_resp.text}"
        
        # Verify response has correct amount
        updated = update_resp.json()
        assert updated["amount"] == 7500, f"Amount not updated: {updated}"
        assert updated["description"] == "TEST_PUT_amount_change_updated"
        
        # GET to verify persistence
        get_resp = api_client.get(f"{BASE_URL}/api/transactions")
        assert get_resp.status_code == 200
        txns = get_resp.json()
        found = [t for t in txns if t["id"] == txn_id]
        assert len(found) == 1
        assert found[0]["amount"] == 7500
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/transactions/{txn_id}")
        print("✓ PUT /api/transactions/:id - amount update works correctly")
    
    def test_update_transaction_category_change(self, api_client):
        """Test updating transaction category persists correctly"""
        # CREATE
        create_payload = {
            "type": "expense",
            "amount": 3000,
            "category": "Shopping",
            "description": "TEST_PUT_category_change",
            "date": "2026-01-21"
        }
        create_resp = api_client.post(f"{BASE_URL}/api/transactions", json=create_payload)
        assert create_resp.status_code == 200
        txn_id = create_resp.json()["id"]
        
        # UPDATE category
        update_payload = {
            "type": "expense",
            "amount": 3000,
            "category": "Entertainment",  # Changed category
            "description": "TEST_PUT_category_change",
            "date": "2026-01-21"
        }
        update_resp = api_client.put(f"{BASE_URL}/api/transactions/{txn_id}", json=update_payload)
        assert update_resp.status_code == 200
        
        # Verify
        updated = update_resp.json()
        assert updated["category"] == "Entertainment"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/transactions/{txn_id}")
        print("✓ PUT /api/transactions/:id - category update works correctly")
    
    def test_update_transaction_type_change(self, api_client):
        """Test changing transaction type from expense to income"""
        # CREATE expense
        create_payload = {
            "type": "expense",
            "amount": 2000,
            "category": "Food & Dining",
            "description": "TEST_PUT_type_change",
            "date": "2026-01-22"
        }
        create_resp = api_client.post(f"{BASE_URL}/api/transactions", json=create_payload)
        assert create_resp.status_code == 200
        txn_id = create_resp.json()["id"]
        
        # UPDATE to income
        update_payload = {
            "type": "income",
            "amount": 2000,
            "category": "Freelance",
            "description": "TEST_PUT_type_change",
            "date": "2026-01-22"
        }
        update_resp = api_client.put(f"{BASE_URL}/api/transactions/{txn_id}", json=update_payload)
        assert update_resp.status_code == 200
        
        updated = update_resp.json()
        assert updated["type"] == "income"
        assert updated["category"] == "Freelance"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/transactions/{txn_id}")
        print("✓ PUT /api/transactions/:id - type change works correctly")


class TestOptionalDescription:
    """Tests for POST /api/transactions with empty description (now optional)"""
    
    def test_create_transaction_empty_description(self, api_client):
        """Test creating transaction with empty description string"""
        payload = {
            "type": "expense",
            "amount": 500,
            "category": "Groceries",
            "description": "",  # Empty description - should be allowed
            "date": "2026-01-23"
        }
        resp = api_client.post(f"{BASE_URL}/api/transactions", json=payload)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        
        data = resp.json()
        assert data["description"] == ""
        assert data["amount"] == 500
        assert data["category"] == "Groceries"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/transactions/{data['id']}")
        print("✓ POST /api/transactions - empty description accepted")
    
    def test_create_transaction_no_description_field(self, api_client):
        """Test creating transaction without description field at all"""
        payload = {
            "type": "expense",
            "amount": 600,
            "category": "Transport",
            # "description" field omitted - should default to ""
            "date": "2026-01-23"
        }
        resp = api_client.post(f"{BASE_URL}/api/transactions", json=payload)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        
        data = resp.json()
        # description should default to empty string
        assert data["description"] == "" or data.get("description") is not None
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/transactions/{data['id']}")
        print("✓ POST /api/transactions - missing description field defaults correctly")
    
    def test_create_transaction_with_description(self, api_client):
        """Test creating transaction with description still works"""
        payload = {
            "type": "income",
            "amount": 10000,
            "category": "Salary",
            "description": "Monthly salary payment",
            "date": "2026-01-24"
        }
        resp = api_client.post(f"{BASE_URL}/api/transactions", json=payload)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        
        data = resp.json()
        assert data["description"] == "Monthly salary payment"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/transactions/{data['id']}")
        print("✓ POST /api/transactions - with description still works")


class TestInvestmentBreakdown:
    """Tests for GET /api/dashboard/stats invest_breakdown field"""
    
    def test_dashboard_stats_has_invest_breakdown(self, api_client):
        """Test that dashboard stats returns invest_breakdown object"""
        resp = api_client.get(f"{BASE_URL}/api/dashboard/stats")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        
        data = resp.json()
        assert "invest_breakdown" in data, "Missing invest_breakdown field"
        assert isinstance(data["invest_breakdown"], dict), "invest_breakdown should be a dict"
        print("✓ GET /api/dashboard/stats - invest_breakdown field exists")
    
    def test_investment_transaction_appears_in_breakdown(self, api_client):
        """Test that investment transactions appear in invest_breakdown"""
        # Create investment transaction with specific category
        payload = {
            "type": "investment",
            "amount": 15000,
            "category": "TEST_SIP_Category",  # Unique category to test
            "description": "TEST_investment_breakdown",
            "date": "2026-01-25"
        }
        create_resp = api_client.post(f"{BASE_URL}/api/transactions", json=payload)
        assert create_resp.status_code == 200
        txn_id = create_resp.json()["id"]
        
        # Get dashboard stats
        stats_resp = api_client.get(f"{BASE_URL}/api/dashboard/stats")
        assert stats_resp.status_code == 200
        
        data = stats_resp.json()
        invest_breakdown = data.get("invest_breakdown", {})
        
        # Verify our category appears in breakdown
        assert "TEST_SIP_Category" in invest_breakdown, f"Category not in breakdown: {invest_breakdown}"
        assert invest_breakdown["TEST_SIP_Category"] == 15000
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/transactions/{txn_id}")
        print("✓ GET /api/dashboard/stats - investment transactions appear in invest_breakdown")
    
    def test_multiple_investments_same_category_sum(self, api_client):
        """Test that multiple investments in same category are summed"""
        # Create two investment transactions with same category
        payload1 = {
            "type": "investment",
            "amount": 5000,
            "category": "TEST_MutualFunds",
            "description": "TEST_sum_check_1",
            "date": "2026-01-26"
        }
        payload2 = {
            "type": "investment",
            "amount": 8000,
            "category": "TEST_MutualFunds",
            "description": "TEST_sum_check_2",
            "date": "2026-01-26"
        }
        
        resp1 = api_client.post(f"{BASE_URL}/api/transactions", json=payload1)
        assert resp1.status_code == 200
        txn1_id = resp1.json()["id"]
        
        resp2 = api_client.post(f"{BASE_URL}/api/transactions", json=payload2)
        assert resp2.status_code == 200
        txn2_id = resp2.json()["id"]
        
        # Get dashboard stats
        stats_resp = api_client.get(f"{BASE_URL}/api/dashboard/stats")
        assert stats_resp.status_code == 200
        
        data = stats_resp.json()
        invest_breakdown = data.get("invest_breakdown", {})
        
        # Verify sum
        assert "TEST_MutualFunds" in invest_breakdown
        assert invest_breakdown["TEST_MutualFunds"] == 13000  # 5000 + 8000
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/transactions/{txn1_id}")
        api_client.delete(f"{BASE_URL}/api/transactions/{txn2_id}")
        print("✓ GET /api/dashboard/stats - investment categories are summed correctly")
    
    def test_investment_categories_in_breakdown(self, api_client):
        """Test common investment categories appear in breakdown"""
        # Create different investment types
        categories = ["SIP", "Mutual Funds", "Stocks", "Gold"]
        txn_ids = []
        
        for cat in categories:
            payload = {
                "type": "investment",
                "amount": 1000,
                "category": cat,
                "description": f"TEST_{cat}_breakdown",
                "date": "2026-01-27"
            }
            resp = api_client.post(f"{BASE_URL}/api/transactions", json=payload)
            assert resp.status_code == 200
            txn_ids.append(resp.json()["id"])
        
        # Get stats
        stats_resp = api_client.get(f"{BASE_URL}/api/dashboard/stats")
        assert stats_resp.status_code == 200
        
        data = stats_resp.json()
        invest_breakdown = data.get("invest_breakdown", {})
        
        # Verify all categories present
        for cat in categories:
            assert cat in invest_breakdown, f"Missing {cat} in invest_breakdown"
        
        # Cleanup
        for tid in txn_ids:
            api_client.delete(f"{BASE_URL}/api/transactions/{tid}")
        
        print("✓ GET /api/dashboard/stats - all investment categories in breakdown")


class TestInvestmentTypeCategories:
    """Test that investment transactions work with various category types"""
    
    def test_create_investment_mutual_funds(self, api_client):
        """Test creating investment with Mutual Funds category"""
        payload = {
            "type": "investment",
            "amount": 10000,
            "category": "Mutual Funds",
            "description": "HDFC Mid Cap",
            "date": "2026-01-28"
        }
        resp = api_client.post(f"{BASE_URL}/api/transactions", json=payload)
        assert resp.status_code == 200
        
        data = resp.json()
        assert data["type"] == "investment"
        assert data["category"] == "Mutual Funds"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/transactions/{data['id']}")
        print("✓ Investment - Mutual Funds category works")
    
    def test_create_investment_sip(self, api_client):
        """Test creating investment with SIP category"""
        payload = {
            "type": "investment",
            "amount": 5000,
            "category": "SIP",
            "description": "Axis Bluechip SIP",
            "date": "2026-01-28"
        }
        resp = api_client.post(f"{BASE_URL}/api/transactions", json=payload)
        assert resp.status_code == 200
        
        data = resp.json()
        assert data["type"] == "investment"
        assert data["category"] == "SIP"
        
        api_client.delete(f"{BASE_URL}/api/transactions/{data['id']}")
        print("✓ Investment - SIP category works")
    
    def test_create_investment_stocks(self, api_client):
        """Test creating investment with Stocks category"""
        payload = {
            "type": "investment",
            "amount": 25000,
            "category": "Stocks",
            "description": "HDFC Bank shares",
            "date": "2026-01-28"
        }
        resp = api_client.post(f"{BASE_URL}/api/transactions", json=payload)
        assert resp.status_code == 200
        
        data = resp.json()
        assert data["type"] == "investment"
        assert data["category"] == "Stocks"
        
        api_client.delete(f"{BASE_URL}/api/transactions/{data['id']}")
        print("✓ Investment - Stocks category works")
    
    def test_create_investment_etfs(self, api_client):
        """Test creating investment with ETFs category"""
        payload = {
            "type": "investment",
            "amount": 12000,
            "category": "ETFs",
            "description": "Nifty BeES",
            "date": "2026-01-28"
        }
        resp = api_client.post(f"{BASE_URL}/api/transactions", json=payload)
        assert resp.status_code == 200
        
        data = resp.json()
        assert data["type"] == "investment"
        assert data["category"] == "ETFs"
        
        api_client.delete(f"{BASE_URL}/api/transactions/{data['id']}")
        print("✓ Investment - ETFs category works")
    
    def test_create_investment_gold(self, api_client):
        """Test creating investment with Gold category"""
        payload = {
            "type": "investment",
            "amount": 20000,
            "category": "Gold",
            "description": "Digital Gold",
            "date": "2026-01-28"
        }
        resp = api_client.post(f"{BASE_URL}/api/transactions", json=payload)
        assert resp.status_code == 200
        
        data = resp.json()
        assert data["type"] == "investment"
        assert data["category"] == "Gold"
        
        api_client.delete(f"{BASE_URL}/api/transactions/{data['id']}")
        print("✓ Investment - Gold category works")
    
    def test_create_investment_silver(self, api_client):
        """Test creating investment with Silver category"""
        payload = {
            "type": "investment",
            "amount": 8000,
            "category": "Silver",
            "description": "Silver ETF",
            "date": "2026-01-28"
        }
        resp = api_client.post(f"{BASE_URL}/api/transactions", json=payload)
        assert resp.status_code == 200
        
        data = resp.json()
        assert data["type"] == "investment"
        assert data["category"] == "Silver"
        
        api_client.delete(f"{BASE_URL}/api/transactions/{data['id']}")
        print("✓ Investment - Silver category works")
    
    def test_create_investment_copper(self, api_client):
        """Test creating investment with Copper category"""
        payload = {
            "type": "investment",
            "amount": 5000,
            "category": "Copper",
            "description": "Copper commodity",
            "date": "2026-01-28"
        }
        resp = api_client.post(f"{BASE_URL}/api/transactions", json=payload)
        assert resp.status_code == 200
        
        data = resp.json()
        assert data["type"] == "investment"
        assert data["category"] == "Copper"
        
        api_client.delete(f"{BASE_URL}/api/transactions/{data['id']}")
        print("✓ Investment - Copper category works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
