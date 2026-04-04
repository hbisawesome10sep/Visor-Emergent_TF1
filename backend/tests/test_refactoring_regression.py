"""
Refactoring Regression Tests - Post Module Split
=================================================
Tests ALL endpoints listed in the review request to verify refactoring didn't break functionality.

Refactored modules tested:
- visor_ai.py: Now imports from services/visor_calculators.py, services/visor_helpers.py, services/visor_prompt.py
- bank_statements.py: Now imports from parsers/utils.py, parsers/csv_excel.py, parsers/pdf_parsers.py

All 16 endpoints from review request:
1. POST /api/auth/login — login works, returns token (30-day expiry)
2. GET /api/dashboard/stats — returns income, expenses, health_score
3. GET /api/dashboard/monthly-trends — returns monthly trends array
4. GET /api/dashboard/smart-alerts — returns alerts
5. GET /api/visor-ai/history — returns chat history (refactored module)
6. POST /api/visor-ai/chat — send a message, get AI response (refactored calculators + helpers)
7. GET /api/bank-statements/history — returns import history (refactored parsers module)
8. POST /api/bank-statements/recategorize — re-categorize transactions (uses refactored categorize_transaction)
9. GET /api/goals — returns goals list
10. GET /api/holdings — returns holdings data
11. GET /api/recurring — returns SIP/recurring data
12. GET /api/transactions — returns transactions list
13. GET /api/market-data — returns live market data
14. GET /api/tax-summary — returns tax summary
15. GET /api/credit-cards — returns credit cards list
16. Verify expired/invalid token returns 401 (not 500)
"""

import pytest
import requests
import os
import time
import base64
import json

# Use the public URL
BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://finance-parser-split.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_EMAIL = "rajesh@visor.demo"
TEST_PASSWORD = "Demo@123"


# ═══════════════════════════════════════════════════════════════════════════════
#  1. AUTH MODULE - Login with 30-day token
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthLogin:
    """Test POST /api/auth/login - verify token and 30-day expiry"""
    
    def test_login_returns_token(self):
        """Test that login returns a valid JWT token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "token" in data, "No token in login response"
        assert "user" in data, "No user in login response"
        assert data["user"]["email"] == TEST_EMAIL
        assert "id" in data["user"]
        
    def test_token_expiry_is_30_days(self):
        """Verify token expiry is approximately 30 days"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        token = response.json()["token"]
        
        # Decode JWT payload (second part)
        parts = token.split(".")
        assert len(parts) == 3, "Invalid JWT format"
        
        # Add padding to base64 payload
        payload_b64 = parts[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
            
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        
        # Check expiry is ~30 days from now
        assert "exp" in payload, "No expiry in token"
        current_time = int(time.time())
        exp_time = payload["exp"]
        days_until_expiry = (exp_time - current_time) / (24 * 60 * 60)
        
        # Should be between 29-31 days
        assert 29 <= days_until_expiry <= 31, f"Token expires in {days_until_expiry:.1f} days, expected ~30"
        print(f"Token expires in {days_until_expiry:.1f} days - PASS")


# ═══════════════════════════════════════════════════════════════════════════════
#  2-4. DASHBOARD MODULE - Stats, Monthly Trends, Smart Alerts
# ═══════════════════════════════════════════════════════════════════════════════

class TestDashboard:
    """Test Dashboard endpoints"""
    
    def test_dashboard_stats(self, auth_token):
        """Test GET /api/dashboard/stats - returns income, expenses, health_score"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers)
        
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        data = response.json()
        
        # Verify required fields
        assert "total_income" in data, "Missing total_income"
        assert "total_expenses" in data, "Missing total_expenses"
        assert "health_score" in data, "Missing health_score"
        assert "net_balance" in data, "Missing net_balance"
        print(f"Dashboard stats: income={data['total_income']}, expenses={data['total_expenses']}, health_score={data['health_score']}")
        
    def test_dashboard_monthly_trends(self, auth_token):
        """Test GET /api/dashboard/monthly-trends - returns monthly trends array"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/dashboard/monthly-trends", headers=headers)
        
        assert response.status_code == 200, f"Monthly trends failed: {response.text}"
        data = response.json()
        
        # Returns object with "trends" array
        assert "trends" in data, f"Missing 'trends' key in response"
        trends = data["trends"]
        assert isinstance(trends, list), f"Expected list, got {type(trends)}"
        if trends:
            assert "month" in trends[0], "Missing month in trend data"
        print(f"Monthly trends: {len(trends)} months of data")
        
    def test_dashboard_smart_alerts(self, auth_token):
        """Test GET /api/dashboard/smart-alerts - returns alerts"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/dashboard/smart-alerts", headers=headers)
        
        assert response.status_code == 200, f"Smart alerts failed: {response.text}"
        data = response.json()
        
        # Returns object with "alerts" array
        assert "alerts" in data, f"Missing 'alerts' key in response"
        alerts = data["alerts"]
        assert isinstance(alerts, list), f"Expected list, got {type(alerts)}"
        print(f"Smart alerts: {len(alerts)} alerts returned")


# ═══════════════════════════════════════════════════════════════════════════════
#  5-6. VISOR AI MODULE (REFACTORED) - History and Chat
# ═══════════════════════════════════════════════════════════════════════════════

class TestVisorAI:
    """Test Visor AI endpoints - REFACTORED module using services/ helpers"""
    
    def test_visor_ai_history(self, auth_token):
        """Test GET /api/visor-ai/history - returns chat history"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/visor-ai/history", headers=headers)
        
        assert response.status_code == 200, f"Visor AI history failed: {response.text}"
        data = response.json()
        
        # Should return list of messages
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        if data:
            assert "role" in data[0], "Missing role in chat message"
            assert "content" in data[0], "Missing content in chat message"
        print(f"Visor AI history: {len(data)} messages")
        
    def test_visor_ai_chat_simple(self, auth_token):
        """Test POST /api/visor-ai/chat - send message, get AI response"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Simple question about savings rate (uses refactored calculators + helpers)
        payload = {
            "message": "What is my savings rate?"
        }
        
        # AI calls may take 5-10 seconds due to LLM
        response = requests.post(
            f"{BASE_URL}/api/visor-ai/chat", 
            json=payload, 
            headers=headers,
            timeout=30
        )
        
        assert response.status_code == 200, f"Visor AI chat failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "id" in data, "Missing id in response"
        assert "role" in data, "Missing role in response"
        assert data["role"] == "assistant", f"Expected assistant role, got {data['role']}"
        assert "content" in data, "Missing content in response"
        assert len(data["content"]) > 0, "Empty response content"
        
        print(f"Visor AI chat response (first 200 chars): {data['content'][:200]}...")

    def test_visor_ai_chat_with_calculator(self, auth_token):
        """Test POST /api/visor-ai/chat with calculator intent (SIP)"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # SIP calculation question - should trigger auto_calculate
        payload = {
            "message": "Calculate SIP for 10000 per month at 12% for 10 years"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/visor-ai/chat", 
            json=payload, 
            headers=headers,
            timeout=30
        )
        
        assert response.status_code == 200, f"Visor AI SIP calc failed: {response.text}"
        data = response.json()
        
        assert "content" in data
        # May have calculator_result if detected
        if "calculator_result" in data and data["calculator_result"]:
            print(f"Calculator result detected: {data['calculator_result']}")
        print(f"Visor AI SIP response received successfully")


# ═══════════════════════════════════════════════════════════════════════════════
#  7-8. BANK STATEMENTS MODULE (REFACTORED) - History and Recategorize
# ═══════════════════════════════════════════════════════════════════════════════

class TestBankStatements:
    """Test Bank Statement endpoints - REFACTORED module using parsers/"""
    
    def test_bank_statements_history(self, auth_token):
        """Test GET /api/bank-statements/history - returns import history"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/bank-statements/history", headers=headers)
        
        assert response.status_code == 200, f"Bank statement history failed: {response.text}"
        data = response.json()
        
        # Should have imports array
        assert "imports" in data, "Missing imports in response"
        assert isinstance(data["imports"], list), f"Expected list, got {type(data['imports'])}"
        print(f"Bank statement history: {len(data['imports'])} imported accounts")
        
    def test_bank_statements_recategorize(self, auth_token):
        """Test POST /api/bank-statements/recategorize - re-categorize transactions"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(f"{BASE_URL}/api/bank-statements/recategorize", headers=headers)
        
        assert response.status_code == 200, f"Recategorize failed: {response.text}"
        data = response.json()
        
        # Should return recategorization stats
        assert "message" in data, "Missing message in response"
        assert "updated" in data or "unchanged" in data, "Missing update stats"
        print(f"Recategorize result: {data}")


# ═══════════════════════════════════════════════════════════════════════════════
#  9-15. OTHER ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestOtherEndpoints:
    """Test other major endpoints"""
    
    def test_get_goals(self, auth_token):
        """Test GET /api/goals - returns goals list"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/goals", headers=headers)
        
        assert response.status_code == 200, f"Goals failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"Goals: {len(data)} goals returned")
        
    def test_get_holdings(self, auth_token):
        """Test GET /api/holdings - returns holdings data"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/holdings", headers=headers)
        
        assert response.status_code == 200, f"Holdings failed: {response.text}"
        data = response.json()
        assert "holdings" in data, "Missing holdings in response"
        assert "summary" in data, "Missing summary in response"
        print(f"Holdings: {len(data['holdings'])} holdings, invested={data['summary'].get('total_invested', 0)}")
        
    def test_get_recurring(self, auth_token):
        """Test GET /api/recurring - returns SIP/recurring data"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/recurring", headers=headers)
        
        assert response.status_code == 200, f"Recurring failed: {response.text}"
        data = response.json()
        assert "recurring" in data, "Missing recurring in response"
        assert "summary" in data, "Missing summary in response"
        print(f"Recurring: {len(data['recurring'])} recurring items")
        
    def test_get_transactions(self, auth_token):
        """Test GET /api/transactions - returns transactions list"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/transactions", headers=headers)
        
        assert response.status_code == 200, f"Transactions failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"Transactions: {len(data)} transactions returned")
        
    def test_get_market_data(self):
        """Test GET /api/market-data - returns live market data (no auth required)"""
        response = requests.get(f"{BASE_URL}/api/market-data")
        
        assert response.status_code == 200, f"Market data failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        # Should have key indices like Nifty 50, Sensex
        keys = [item.get("key", "") for item in data]
        print(f"Market data: {len(data)} items, keys: {keys[:5]}")
        
    def test_get_tax_summary(self, auth_token):
        """Test GET /api/tax-summary - returns tax summary"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/tax-summary", headers=headers)
        
        assert response.status_code == 200, f"Tax summary failed: {response.text}"
        data = response.json()
        assert "sections" in data, "Missing sections in response"
        assert "total_deductions" in data, "Missing total_deductions in response"
        print(f"Tax summary: total_deductions={data.get('total_deductions', 0)}, fy={data.get('fy', 'N/A')}")
        
    def test_get_credit_cards(self, auth_token):
        """Test GET /api/credit-cards - returns credit cards list"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/credit-cards", headers=headers)
        
        assert response.status_code == 200, f"Credit cards failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"Credit cards: {len(data)} cards returned")


# ═══════════════════════════════════════════════════════════════════════════════
#  16. TOKEN VALIDATION - Invalid/Expired Token Returns 401 (not 500)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTokenValidation:
    """Verify invalid/expired tokens return 401, not 500"""
    
    def test_missing_auth_header(self):
        """Test that missing Authorization header returns 401"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code in [401, 403, 422], f"Expected 401/403/422, got {response.status_code}"
        print(f"Missing auth header: {response.status_code} - PASS")
        
    def test_invalid_token_returns_401(self):
        """Test that invalid token returns 401 (not 500)"""
        headers = {"Authorization": "Bearer invalid_token_12345"}
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers)
        
        assert response.status_code == 401, f"Expected 401 for invalid token, got {response.status_code}: {response.text}"
        print(f"Invalid token: {response.status_code} - PASS")
        
    def test_malformed_header_returns_401(self):
        """Test that malformed Authorization header returns 401"""
        headers = {"Authorization": "NotBearer token123"}
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers)
        
        assert response.status_code in [401, 403], f"Expected 401/403 for malformed header, got {response.status_code}"
        print(f"Malformed header: {response.status_code} - PASS")
        
    def test_expired_token_format_returns_401(self):
        """Test that expired-looking token returns 401 (not 500)"""
        # Create a token with exp in the past (manually crafted JWT-like string)
        # This is a base64 encoded {"exp": 1000000000} which is year 2001
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjEwMDAwMDAwMDAsInVzZXJfaWQiOiJ0ZXN0In0.fake_signature"
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers)
        
        # Should NOT be 500 - either 401 for invalid or expired
        assert response.status_code != 500, f"Got 500 error for expired token - should be 401"
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"Expired token format: {response.status_code} - PASS")
        
    def test_empty_token_returns_401(self):
        """Test that empty Bearer token returns 401"""
        headers = {"Authorization": "Bearer "}
        response = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers)
        
        assert response.status_code in [401, 422], f"Expected 401/422 for empty token, got {response.status_code}"
        print(f"Empty token: {response.status_code} - PASS")


# ═══════════════════════════════════════════════════════════════════════════════
#  HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════════════════

class TestHealthCheck:
    """Test health endpoint"""
    
    def test_health_endpoint(self):
        """Test GET /api/health"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("Health check: PASS")


# ═══════════════════════════════════════════════════════════════════════════════
#  FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def auth_token():
    """Get authentication token for test session"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        token = response.json()["token"]
        print(f"Auth token obtained successfully")
        return token
    pytest.skip("Authentication failed - cannot proceed with tests")


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
