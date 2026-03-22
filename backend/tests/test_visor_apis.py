"""
Visor Finance App - Backend API Tests
Tests for: Auth, Transactions, Goals, Dashboard, Health Score, AI Chat
"""
import pytest
import requests
import os
from datetime import datetime

# Use public backend URL for testing
BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://payee-master.preview.emergentagent.com').rstrip('/')

@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session

@pytest.fixture
def demo_user_token(api_client):
    """Login with demo user and return token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "rajesh@visor.demo",
        "password": "Demo@123"
    })
    assert response.status_code == 200, f"Demo login failed: {response.text}"
    data = response.json()
    return data["token"]

@pytest.fixture
def test_user_credentials(api_client):
    """Create a test user and return credentials"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    email = f"TEST_user_{timestamp}@visor.test"
    password = "Test@1234"
    
    response = api_client.post(f"{BASE_URL}/api/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "TEST User",
        "dob": "1995-01-01",
        "pan": "TESTPAN123",
        "aadhaar": "123456789012"
    })
    
    if response.status_code == 201 or response.status_code == 200:
        data = response.json()
        return {"email": email, "password": password, "token": data["token"], "user_id": data["user"]["id"]}
    else:
        pytest.skip(f"Could not create test user: {response.text}")

# ══════════════════════════════════════
#  AUTH TESTS
# ══════════════════════════════════════

class TestAuth:
    """Authentication endpoint tests"""
    
    def test_login_with_demo_account(self, api_client):
        """Test login with demo account rajesh@visor.demo"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "rajesh@visor.demo",
            "password": "Demo@123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        assert "token" in data, "Token not in response"
        assert "user" in data, "User not in response"
        assert data["user"]["email"] == "rajesh@visor.demo"
        assert data["user"]["full_name"] == "Rajesh Kumar"
        print(f"✓ Login successful for {data['user']['email']}")
    
    def test_login_invalid_credentials(self, api_client):
        """Test login with invalid credentials"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401, "Should return 401 for invalid credentials"
        print("✓ Invalid credentials correctly rejected")
    
    def test_register_new_user(self, api_client):
        """Test user registration"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "email": f"TEST_newuser_{timestamp}@test.com",
            "password": "SecurePass123!",
            "full_name": "TEST New User",
            "dob": "1990-05-15",
            "pan": "ABCDE1234F",
            "aadhaar": "123456789012"
        })
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert "token" in data
            assert "user" in data
            assert data["user"]["pan"] == "ABCDE1234F"
            assert len(data["user"]["aadhaar_last4"]) == 4
            print(f"✓ User registration successful: {data['user']['email']}")
        else:
            pytest.fail(f"Registration failed: {response.status_code} - {response.text}")
    
    def test_get_profile(self, api_client, demo_user_token):
        """Test getting user profile"""
        response = api_client.get(
            f"{BASE_URL}/api/auth/profile",
            headers={"Authorization": f"Bearer {demo_user_token}"}
        )
        assert response.status_code == 200, f"Profile fetch failed: {response.text}"
        
        data = response.json()
        assert data["email"] == "rajesh@visor.demo"
        assert "full_name" in data
        assert "dob" in data
        assert "pan" in data
        print(f"✓ Profile retrieved: {data['full_name']}")

# ══════════════════════════════════════
#  DASHBOARD & HEALTH SCORE TESTS
# ══════════════════════════════════════

class TestDashboard:
    """Dashboard and health score tests"""
    
    def test_dashboard_stats(self, api_client, demo_user_token):
        """Test dashboard stats endpoint"""
        response = api_client.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {demo_user_token}"}
        )
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        
        data = response.json()
        # Verify expected fields
        required_fields = [
            "total_income", "total_expenses", "total_investments", "net_balance",
            "category_breakdown", "recent_transactions", "monthly_income",
            "monthly_expenses", "monthly_investments", "goal_count", "transaction_count"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        # Verify data types
        assert isinstance(data["total_income"], (int, float))
        assert isinstance(data["net_balance"], (int, float))
        assert isinstance(data["category_breakdown"], dict)
        assert isinstance(data["recent_transactions"], list)
        print(f"✓ Dashboard stats: Net balance = ₹{data['net_balance']:,.2f}")
    
    def test_health_score(self, api_client, demo_user_token):
        """Test financial health score endpoint"""
        response = api_client.get(
            f"{BASE_URL}/api/health-score",
            headers={"Authorization": f"Bearer {demo_user_token}"}
        )
        assert response.status_code == 200, f"Health score failed: {response.text}"
        
        data = response.json()
        required_fields = ["overall_score", "grade", "savings_rate", "investment_rate", "expense_ratio"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        # Verify score is between 0-100
        assert 0 <= data["overall_score"] <= 100, "Score should be 0-100"
        assert data["grade"] in ["Excellent", "Good", "Fair", "Needs Work", "Critical"]
        print(f"✓ Health Score: {data['overall_score']}/100 - {data['grade']}")

# ══════════════════════════════════════
#  TRANSACTION TESTS
# ══════════════════════════════════════

class TestTransactions:
    """Transaction CRUD tests"""
    
    def test_get_transactions(self, api_client, demo_user_token):
        """Test getting all transactions"""
        response = api_client.get(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {demo_user_token}"}
        )
        assert response.status_code == 200, f"Get transactions failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            txn = data[0]
            assert "id" in txn
            assert "type" in txn
            assert "amount" in txn
            assert "category" in txn
            print(f"✓ Retrieved {len(data)} transactions")
        else:
            print("✓ No transactions (empty list)")
    
    def test_get_transactions_with_filter(self, api_client, demo_user_token):
        """Test transaction filtering by type"""
        for txn_type in ["income", "expense", "investment"]:
            response = api_client.get(
                f"{BASE_URL}/api/transactions?type={txn_type}",
                headers={"Authorization": f"Bearer {demo_user_token}"}
            )
            assert response.status_code == 200
            data = response.json()
            # Verify all transactions match filter
            for txn in data:
                assert txn["type"] == txn_type
            print(f"✓ Filter {txn_type}: {len(data)} transactions")
    
    def test_create_transaction_and_verify(self, api_client, test_user_credentials):
        """Test creating a transaction and verify persistence"""
        token = test_user_credentials["token"]
        
        # Create transaction
        create_response = api_client.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "type": "expense",
                "amount": 500.50,
                "category": "Food",
                "description": "TEST_transaction - Lunch",
                "date": "2026-02-15"
            }
        )
        assert create_response.status_code in [200, 201], f"Create failed: {create_response.text}"
        
        created_txn = create_response.json()
        assert created_txn["amount"] == 500.50
        assert created_txn["type"] == "expense"
        txn_id = created_txn["id"]
        print(f"✓ Transaction created: {txn_id}")
        
        # Verify persistence by getting all transactions
        get_response = api_client.get(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert get_response.status_code == 200
        all_txns = get_response.json()
        assert any(t["id"] == txn_id for t in all_txns), "Created transaction not found in GET"
        print("✓ Transaction persisted successfully")
    
    def test_delete_transaction(self, api_client, test_user_credentials):
        """Test deleting a transaction"""
        token = test_user_credentials["token"]
        
        # Create a transaction to delete
        create_response = api_client.post(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "type": "expense",
                "amount": 100,
                "category": "Other",
                "description": "TEST_to_delete",
                "date": "2026-02-15"
            }
        )
        assert create_response.status_code in [200, 201]
        txn_id = create_response.json()["id"]
        
        # Delete transaction
        delete_response = api_client.delete(
            f"{BASE_URL}/api/transactions/{txn_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert delete_response.status_code == 200
        print(f"✓ Transaction deleted: {txn_id}")

# ══════════════════════════════════════
#  GOAL TESTS
# ══════════════════════════════════════

class TestGoals:
    """Goal CRUD tests"""
    
    def test_get_goals(self, api_client, demo_user_token):
        """Test getting all goals"""
        response = api_client.get(
            f"{BASE_URL}/api/goals",
            headers={"Authorization": f"Bearer {demo_user_token}"}
        )
        assert response.status_code == 200, f"Get goals failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            goal = data[0]
            assert "id" in goal
            assert "title" in goal
            assert "target_amount" in goal
            assert "current_amount" in goal
            print(f"✓ Retrieved {len(data)} goals")
        else:
            print("✓ No goals (empty list)")
    
    def test_create_goal_and_verify(self, api_client, test_user_credentials):
        """Test creating a goal and verify persistence"""
        token = test_user_credentials["token"]
        
        # Create goal
        create_response = api_client.post(
            f"{BASE_URL}/api/goals",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "TEST_goal - Emergency Fund",
                "target_amount": 100000,
                "current_amount": 25000,
                "deadline": "2026-12-31",
                "category": "Safety"
            }
        )
        assert create_response.status_code in [200, 201], f"Create goal failed: {create_response.text}"
        
        created_goal = create_response.json()
        assert created_goal["title"] == "TEST_goal - Emergency Fund"
        assert created_goal["target_amount"] == 100000
        goal_id = created_goal["id"]
        print(f"✓ Goal created: {goal_id}")
        
        # Verify persistence
        get_response = api_client.get(
            f"{BASE_URL}/api/goals",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert get_response.status_code == 200
        all_goals = get_response.json()
        assert any(g["id"] == goal_id for g in all_goals), "Created goal not found in GET"
        print("✓ Goal persisted successfully")
    
    def test_update_goal_and_verify(self, api_client, test_user_credentials):
        """Test updating a goal and verify changes"""
        token = test_user_credentials["token"]
        
        # Create goal first
        create_response = api_client.post(
            f"{BASE_URL}/api/goals",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "TEST_to_update",
                "target_amount": 50000,
                "current_amount": 10000,
                "deadline": "2026-06-30",
                "category": "Travel"
            }
        )
        assert create_response.status_code in [200, 201]
        goal_id = create_response.json()["id"]
        
        # Update goal
        update_response = api_client.put(
            f"{BASE_URL}/api/goals/{goal_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_amount": 20000,
                "title": "TEST_updated_title"
            }
        )
        assert update_response.status_code == 200, f"Update failed: {update_response.text}"
        
        updated_goal = update_response.json()
        assert updated_goal["current_amount"] == 20000
        assert updated_goal["title"] == "TEST_updated_title"
        print(f"✓ Goal updated successfully: {goal_id}")
    
    def test_delete_goal(self, api_client, test_user_credentials):
        """Test deleting a goal"""
        token = test_user_credentials["token"]
        
        # Create goal to delete
        create_response = api_client.post(
            f"{BASE_URL}/api/goals",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "TEST_to_delete",
                "target_amount": 10000,
                "current_amount": 0,
                "deadline": "2026-12-31",
                "category": "Other"
            }
        )
        assert create_response.status_code in [200, 201]
        goal_id = create_response.json()["id"]
        
        # Delete goal
        delete_response = api_client.delete(
            f"{BASE_URL}/api/goals/{goal_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert delete_response.status_code == 200
        print(f"✓ Goal deleted: {goal_id}")

# ══════════════════════════════════════
#  AI CHAT TESTS
# ══════════════════════════════════════

class TestAIChat:
    """AI chat endpoint tests"""
    
    def test_send_chat_message(self, api_client, demo_user_token):
        """Test sending a message to AI advisor"""
        response = api_client.post(
            f"{BASE_URL}/api/ai/chat",
            headers={"Authorization": f"Bearer {demo_user_token}"},
            json={"message": "Give me a quick savings tip in one sentence"}
        )
        assert response.status_code == 200, f"AI chat failed: {response.text}"
        
        data = response.json()
        assert "content" in data
        assert "role" in data
        assert data["role"] == "assistant"
        assert len(data["content"]) > 0
        print(f"✓ AI response received: {data['content'][:100]}...")
    
    def test_get_chat_history(self, api_client, demo_user_token):
        """Test getting chat history"""
        response = api_client.get(
            f"{BASE_URL}/api/ai/history",
            headers={"Authorization": f"Bearer {demo_user_token}"}
        )
        assert response.status_code == 200, f"Chat history failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Chat history retrieved: {len(data)} messages")
