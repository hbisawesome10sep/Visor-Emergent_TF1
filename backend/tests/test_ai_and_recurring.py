"""
Test suite for AI Chat, Recurring Transactions (SIPs), and Transaction display issues
Testing the fixes for:
1. AI Bot showing 'Request failed' error
2. SIP transactions showing negative sign in Transactions list
3. SIP not appearing in Recurring Investments section
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "rajesh@visor.demo"
TEST_PASSWORD = "Demo@123"


class TestAuthentication:
    """Authentication tests to get token for subsequent tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        return data["token"]
    
    def test_login_success(self, auth_token):
        """Verify login works and returns token"""
        assert auth_token is not None
        assert len(auth_token) > 0
        print(f"✓ Login successful, token obtained")


class TestAIChatEndpoints:
    """Test AI Chat endpoints - POST /api/ai/chat and GET /api/ai/history"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Authentication failed")
        return response.json().get("token")
    
    def test_ai_chat_endpoint_exists(self, auth_token):
        """Test that POST /api/ai/chat endpoint exists and accepts requests"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(
            f"{BASE_URL}/api/ai/chat",
            json={"message": "Hello, what is my current savings rate?"},
            headers=headers
        )
        # Should not return 404 or 405
        assert response.status_code != 404, "AI chat endpoint not found (404)"
        assert response.status_code != 405, "AI chat endpoint method not allowed (405)"
        print(f"✓ AI chat endpoint exists, status: {response.status_code}")
    
    def test_ai_chat_response_structure(self, auth_token):
        """Test that AI chat returns proper response with 'content' field"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(
            f"{BASE_URL}/api/ai/chat",
            json={"message": "What is my savings rate?"},
            headers=headers,
            timeout=30  # AI responses can take time
        )
        
        # Check status code
        assert response.status_code == 200, f"AI chat failed with status {response.status_code}: {response.text}"
        
        # Check response structure
        data = response.json()
        assert "content" in data, f"Response missing 'content' field. Got: {data.keys()}"
        assert "role" in data, f"Response missing 'role' field. Got: {data.keys()}"
        assert data["role"] == "assistant", f"Expected role 'assistant', got: {data['role']}"
        assert len(data["content"]) > 0, "AI response content is empty"
        
        print(f"✓ AI chat response structure correct")
        print(f"  - role: {data['role']}")
        print(f"  - content length: {len(data['content'])} chars")
        print(f"  - content preview: {data['content'][:100]}...")
    
    def test_ai_history_endpoint(self, auth_token):
        """Test GET /api/ai/history returns chat history"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/ai/history",
            headers=headers
        )
        
        assert response.status_code == 200, f"AI history failed: {response.text}"
        data = response.json()
        
        # Should return a list
        assert isinstance(data, list), f"Expected list, got: {type(data)}"
        
        # If there are messages, verify structure
        if len(data) > 0:
            msg = data[0]
            assert "id" in msg, "Message missing 'id'"
            assert "role" in msg, "Message missing 'role'"
            assert "content" in msg, "Message missing 'content'"
            assert "created_at" in msg, "Message missing 'created_at'"
            print(f"✓ AI history returns {len(data)} messages with correct structure")
        else:
            print(f"✓ AI history endpoint works (empty history)")
    
    def test_ai_history_delete(self, auth_token):
        """Test DELETE /api/ai/history clears chat history"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.delete(
            f"{BASE_URL}/api/ai/history",
            headers=headers
        )
        
        assert response.status_code == 200, f"AI history delete failed: {response.text}"
        data = response.json()
        assert "message" in data, "Delete response missing 'message'"
        print(f"✓ AI history delete works: {data['message']}")


class TestRecurringTransactions:
    """Test Recurring Transactions (SIPs) endpoint - GET /api/recurring"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Authentication failed")
        return response.json().get("token")
    
    def test_recurring_endpoint_exists(self, auth_token):
        """Test that GET /api/recurring endpoint exists"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/recurring",
            headers=headers
        )
        
        assert response.status_code != 404, "Recurring endpoint not found (404)"
        assert response.status_code == 200, f"Recurring endpoint failed: {response.text}"
        print(f"✓ Recurring endpoint exists and returns 200")
    
    def test_recurring_response_structure(self, auth_token):
        """Test that recurring endpoint returns proper structure with 'recurring' list"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/recurring",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check top-level structure
        assert "recurring" in data, f"Response missing 'recurring' field. Got: {data.keys()}"
        assert "summary" in data, f"Response missing 'summary' field. Got: {data.keys()}"
        
        # Check recurring is a list
        assert isinstance(data["recurring"], list), f"'recurring' should be list, got: {type(data['recurring'])}"
        
        # Check summary structure
        summary = data["summary"]
        assert "total_count" in summary, "Summary missing 'total_count'"
        assert "active_count" in summary, "Summary missing 'active_count'"
        assert "monthly_commitment" in summary, "Summary missing 'monthly_commitment'"
        
        print(f"✓ Recurring response structure correct")
        print(f"  - Total SIPs: {summary['total_count']}")
        print(f"  - Active SIPs: {summary['active_count']}")
        print(f"  - Monthly commitment: ₹{summary['monthly_commitment']}")
    
    def test_recurring_items_structure(self, auth_token):
        """Test that each recurring item has required fields"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/recurring",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        recurring_list = data.get("recurring", [])
        
        if len(recurring_list) > 0:
            for idx, item in enumerate(recurring_list):
                assert "id" in item, f"Item {idx} missing 'id'"
                assert "name" in item, f"Item {idx} missing 'name'"
                assert "amount" in item, f"Item {idx} missing 'amount'"
                assert "frequency" in item, f"Item {idx} missing 'frequency'"
                assert "category" in item, f"Item {idx} missing 'category'"
                assert "is_active" in item, f"Item {idx} missing 'is_active'"
                
                print(f"  - SIP {idx+1}: {item['name']} - ₹{item['amount']} ({item['frequency']})")
            
            print(f"✓ All {len(recurring_list)} recurring items have correct structure")
        else:
            print(f"✓ Recurring endpoint works (no SIPs found)")


class TestTransactions:
    """Test Transactions endpoint - verify structure and amount display"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Authentication failed")
        return response.json().get("token")
    
    def test_transactions_endpoint(self, auth_token):
        """Test GET /api/transactions returns list"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/transactions",
            headers=headers
        )
        
        assert response.status_code == 200, f"Transactions failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), f"Expected list, got: {type(data)}"
        print(f"✓ Transactions endpoint returns {len(data)} transactions")
    
    def test_transaction_structure(self, auth_token):
        """Test that transactions have correct structure"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/transactions",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            txn = data[0]
            required_fields = ["id", "type", "amount", "category", "description", "date"]
            for field in required_fields:
                assert field in txn, f"Transaction missing '{field}'"
            
            # Verify amount is positive (backend stores positive amounts)
            assert txn["amount"] > 0, f"Transaction amount should be positive, got: {txn['amount']}"
            
            print(f"✓ Transaction structure correct")
            print(f"  - Sample: {txn['type']} - {txn['category']} - ₹{txn['amount']}")
    
    def test_investment_transactions_positive_amounts(self, auth_token):
        """Test that investment transactions have positive amounts in backend"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/transactions?type=investment",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        investment_count = 0
        for txn in data:
            assert txn["type"] == "investment", f"Filter not working, got type: {txn['type']}"
            assert txn["amount"] > 0, f"Investment amount should be positive, got: {txn['amount']}"
            investment_count += 1
        
        print(f"✓ All {investment_count} investment transactions have positive amounts")


class TestDashboardStats:
    """Test Dashboard Stats endpoint - verify investment totals"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Authentication failed")
        return response.json().get("token")
    
    def test_dashboard_stats_endpoint(self, auth_token):
        """Test GET /api/dashboard/stats returns proper structure"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=headers
        )
        
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        data = response.json()
        
        # Check required fields
        required_fields = ["total_income", "total_expenses", "total_investments", "net_balance"]
        for field in required_fields:
            assert field in data, f"Dashboard stats missing '{field}'"
        
        print(f"✓ Dashboard stats structure correct")
        print(f"  - Total Income: ₹{data['total_income']}")
        print(f"  - Total Expenses: ₹{data['total_expenses']}")
        print(f"  - Total Investments: ₹{data['total_investments']}")
        print(f"  - Net Balance: ₹{data['net_balance']}")
    
    def test_investment_breakdown(self, auth_token):
        """Test that invest_breakdown is present and correct"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "invest_breakdown" in data, "Dashboard stats missing 'invest_breakdown'"
        breakdown = data["invest_breakdown"]
        assert isinstance(breakdown, dict), f"invest_breakdown should be dict, got: {type(breakdown)}"
        
        if breakdown:
            print(f"✓ Investment breakdown:")
            for cat, amount in breakdown.items():
                print(f"  - {cat}: ₹{amount}")
        else:
            print(f"✓ invest_breakdown present (empty)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
