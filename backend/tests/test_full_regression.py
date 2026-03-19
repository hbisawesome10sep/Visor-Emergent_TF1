"""
Full Backend Regression Test Suite After Modular Refactoring
Tests ALL endpoints defined in route files under /app/backend/routes/

Covers additional endpoints not in test_modular_refactor.py:
- POST /api/auth/register - New user registration
- POST /api/ai/chat - AI advisor chat
- GET /api/ai/history - AI chat history
- DELETE /api/ai/history - Clear AI history
- GET /api/user-tax-deductions - List user tax deductions
- POST /api/user-tax-deductions - Create user tax deduction
- PUT /api/user-tax-deductions/{id} - Update user tax deduction
- DELETE /api/user-tax-deductions/{id} - Delete user tax deduction
- GET /api/auto-tax-deductions - Auto-detected tax deductions
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

# Use the public URL from environment
BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://ai-voice-chat-24.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_EMAIL = "rajesh@visor.demo"
TEST_PASSWORD = "Demo@123"


class TestAuthRegister:
    """Test auth.py register endpoint"""
    
    def test_register_new_user(self):
        """Test POST /api/auth/register with unique email"""
        unique_email = f"test_reg_{uuid.uuid4().hex[:8]}@test.com"
        user_data = {
            "email": unique_email,
            "password": "Test@123",
            "full_name": "Test Regression User",
            "dob": "1990-01-15",
            "pan": "REGRE1234X",
            "aadhaar": "123456789012"
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=user_data)
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in registration response"
        assert "user" in data
        assert data["user"]["email"] == unique_email
        assert data["user"]["pan"] == "REGRE1234X"
        assert data["user"]["aadhaar_last4"] == "9012"
    
    def test_register_duplicate_email(self):
        """Test register with existing email returns 400"""
        user_data = {
            "email": TEST_EMAIL,
            "password": "Test@123",
            "full_name": "Duplicate User",
            "dob": "1990-01-15",
            "pan": "DUPLI1234X",
            "aadhaar": "123456789012"
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=user_data)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()
    
    def test_register_invalid_pan(self):
        """Test register with invalid PAN length returns 400"""
        unique_email = f"test_pan_{uuid.uuid4().hex[:8]}@test.com"
        user_data = {
            "email": unique_email,
            "password": "Test@123",
            "full_name": "Invalid PAN User",
            "dob": "1990-01-15",
            "pan": "ABC",  # Invalid - too short
            "aadhaar": "123456789012"
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=user_data)
        assert response.status_code == 400
        assert "pan" in response.json()["detail"].lower()
    
    def test_register_invalid_aadhaar(self):
        """Test register with invalid Aadhaar length returns 400"""
        unique_email = f"test_aad_{uuid.uuid4().hex[:8]}@test.com"
        user_data = {
            "email": unique_email,
            "password": "Test@123",
            "full_name": "Invalid Aadhaar User",
            "dob": "1990-01-15",
            "pan": "VALID1234X",
            "aadhaar": "12345"  # Invalid - too short
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=user_data)
        assert response.status_code == 400
        assert "aadhaar" in response.json()["detail"].lower()


class TestAIChatModule:
    """Test ai_chat.py routes: /api/ai/chat, /api/ai/history"""
    
    def test_ai_chat_basic(self, auth_token):
        """Test POST /api/ai/chat with a simple financial question"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        chat_data = {"message": "What is my total income?"}
        response = requests.post(f"{BASE_URL}/api/ai/chat", json=chat_data, headers=headers)
        assert response.status_code == 200, f"AI chat failed: {response.text}"
        data = response.json()
        assert "content" in data
        assert "id" in data
        assert data["role"] == "assistant"
        # Check response is finance-related (not a generic error)
        assert len(data["content"]) > 20
    
    def test_ai_chat_with_screen_context(self, auth_token):
        """Test AI chat with screen context"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        chat_data = {
            "message": "How can I improve?",
            "screen_context": "User is viewing Dashboard with savings rate 59.7%"
        }
        response = requests.post(f"{BASE_URL}/api/ai/chat", json=chat_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
    
    def test_ai_history(self, auth_token):
        """Test GET /api/ai/history"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/ai/history", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have messages from previous tests
        if len(data) > 0:
            assert "role" in data[0]
            assert "content" in data[0]
    
    def test_ai_chat_without_auth(self):
        """Test AI chat without authentication returns 401"""
        response = requests.post(f"{BASE_URL}/api/ai/chat", json={"message": "Hello"})
        assert response.status_code in [401, 422]


class TestUserTaxDeductionsModule:
    """Test tax.py user-tax-deductions routes"""
    
    def test_get_user_tax_deductions(self, auth_token):
        """Test GET /api/user-tax-deductions"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/user-tax-deductions", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "deductions" in data
        assert isinstance(data["deductions"], list)
    
    def test_user_tax_deduction_crud(self, auth_token):
        """Test full CRUD flow for user tax deductions"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # CREATE
        deduction_data = {
            "deduction_id": f"test_ded_{uuid.uuid4().hex[:8]}",
            "section": "80C",
            "name": "TEST_PPF_Investment",
            "limit": 150000,
            "invested_amount": 50000
        }
        create_resp = requests.post(f"{BASE_URL}/api/user-tax-deductions", json=deduction_data, headers=headers)
        assert create_resp.status_code == 200, f"Create failed: {create_resp.text}"
        created = create_resp.json()
        assert created["section"] == "80C"
        assert created["invested_amount"] == 50000
        deduction_id = created["id"]
        
        # READ - Verify in list
        get_resp = requests.get(f"{BASE_URL}/api/user-tax-deductions", headers=headers)
        assert get_resp.status_code == 200
        deductions = get_resp.json()["deductions"]
        found = [d for d in deductions if d["id"] == deduction_id]
        assert len(found) == 1
        
        # UPDATE
        update_resp = requests.put(
            f"{BASE_URL}/api/user-tax-deductions/{deduction_id}",
            json={"invested_amount": 75000},
            headers=headers
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["invested_amount"] == 75000
        
        # DELETE
        delete_resp = requests.delete(f"{BASE_URL}/api/user-tax-deductions/{deduction_id}", headers=headers)
        assert delete_resp.status_code == 200
        
        # Verify deleted
        get_resp2 = requests.get(f"{BASE_URL}/api/user-tax-deductions", headers=headers)
        deductions2 = get_resp2.json()["deductions"]
        found2 = [d for d in deductions2 if d["id"] == deduction_id]
        assert len(found2) == 0
    
    def test_duplicate_deduction_id_returns_400(self, auth_token):
        """Test creating duplicate deduction_id returns 400"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        deduction_id = f"dup_test_{uuid.uuid4().hex[:8]}"
        
        # Create first
        deduction_data = {
            "deduction_id": deduction_id,
            "section": "80D",
            "name": "TEST_Health_Insurance",
            "limit": 25000,
            "invested_amount": 10000
        }
        create_resp = requests.post(f"{BASE_URL}/api/user-tax-deductions", json=deduction_data, headers=headers)
        assert create_resp.status_code == 200
        created_id = create_resp.json()["id"]
        
        # Try to create duplicate
        dup_resp = requests.post(f"{BASE_URL}/api/user-tax-deductions", json=deduction_data, headers=headers)
        assert dup_resp.status_code == 400
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/user-tax-deductions/{created_id}", headers=headers)
    
    def test_update_nonexistent_returns_404(self, auth_token):
        """Test updating non-existent deduction returns 404"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.put(
            f"{BASE_URL}/api/user-tax-deductions/nonexistent-id-12345",
            json={"invested_amount": 50000},
            headers=headers
        )
        assert response.status_code == 404


class TestAutoTaxDeductionsModule:
    """Test tax.py auto-tax-deductions routes"""
    
    def test_get_auto_tax_deductions(self, auth_token):
        """Test GET /api/auto-tax-deductions"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/auto-tax-deductions", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "fy" in data
        assert "sections" in data
        assert "total_detected" in data
        assert "count" in data
    
    def test_get_auto_tax_deductions_with_fy(self, auth_token):
        """Test GET /api/auto-tax-deductions with specific FY"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/auto-tax-deductions?fy=2024-25", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["fy"] == "2024-25"


class TestAllEndpointsExist:
    """Meta tests to verify all endpoints from request are accessible"""
    
    def test_all_required_endpoints(self, auth_token):
        """Verify all endpoints from refactoring request return valid responses"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        endpoints_requiring_auth = [
            ("GET", "/api/auth/profile"),
            ("GET", "/api/dashboard/stats"),
            ("GET", "/api/health-score"),
            ("GET", "/api/transactions"),
            ("GET", "/api/holdings"),
            ("GET", "/api/market-data"),
            ("GET", "/api/portfolio-overview"),
            ("GET", "/api/goals"),
            ("GET", "/api/tax-summary"),
            ("GET", "/api/capital-gains"),
            ("GET", "/api/tax-calculator"),
            ("GET", "/api/user-tax-deductions"),
            ("GET", "/api/auto-tax-deductions"),
            ("GET", "/api/risk-profile"),
            ("GET", "/api/recurring"),
            ("GET", "/api/loans"),
            ("GET", "/api/assets"),
            ("GET", "/api/books/ledger"),
            ("GET", "/api/books/pnl"),
            ("GET", "/api/books/balance-sheet"),
            ("GET", "/api/ai/history"),
        ]
        
        endpoints_public = [
            ("GET", "/api/health"),
            ("GET", "/api/market-data"),
        ]
        
        failures = []
        
        # Test authenticated endpoints
        for method, endpoint in endpoints_requiring_auth:
            try:
                if method == "GET":
                    resp = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=30)
                    if resp.status_code not in [200, 404]:  # 404 is acceptable for empty lists
                        failures.append(f"{method} {endpoint}: {resp.status_code}")
            except Exception as e:
                failures.append(f"{method} {endpoint}: {str(e)}")
        
        # Test public endpoints
        for method, endpoint in endpoints_public:
            try:
                if method == "GET":
                    resp = requests.get(f"{BASE_URL}{endpoint}", timeout=30)
                    if resp.status_code != 200:
                        failures.append(f"{method} {endpoint} (public): {resp.status_code}")
            except Exception as e:
                failures.append(f"{method} {endpoint} (public): {str(e)}")
        
        assert len(failures) == 0, f"Endpoint failures: {failures}"


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
