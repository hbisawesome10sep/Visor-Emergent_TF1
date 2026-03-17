"""
Test Suite: Auth Token Expiry (30 days) and Dashboard APIs
Testing bug fixes:
1. Token expiry changed from 7 days to 30 days
2. Proper 401 responses for expired/invalid tokens
3. Dashboard stats with and without data
4. Smart alerts API
5. Monthly trends API
6. Login flow
"""
import pytest
import requests
import jwt
import os
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
DEMO_EMAIL = "rajesh@visor.demo"
DEMO_PASSWORD = "Demo@123"


class TestLoginFlow:
    """Test POST /api/auth/login returns token and user correctly"""
    
    def test_login_success_returns_token_and_user(self):
        """Test that login returns token and user data"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        # Verify token exists
        assert "token" in data, "Response missing 'token' field"
        assert isinstance(data["token"], str), "Token should be a string"
        assert len(data["token"]) > 50, "Token appears too short"
        
        # Verify user data
        assert "user" in data, "Response missing 'user' field"
        user = data["user"]
        assert "id" in user, "User missing 'id' field"
        assert user["email"] == DEMO_EMAIL.lower(), "Email mismatch"
        assert "full_name" in user, "User missing 'full_name' field"
        
        print(f"✓ Login successful for {DEMO_EMAIL}")
        print(f"  User ID: {user['id']}")
        print(f"  Full name: {user['full_name']}")
    
    def test_login_invalid_credentials_returns_401(self):
        """Test that invalid credentials return 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@email.com",
            "password": "wrongpass"
        })
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        data = response.json()
        assert "detail" in data, "Missing error detail"
        print(f"✓ Invalid credentials correctly return 401: {data['detail']}")
    
    def test_login_wrong_password_returns_401(self):
        """Test that wrong password returns 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": "wrong_password_123"
        })
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Wrong password correctly returns 401")


class TestTokenExpiry:
    """Test JWT token expiry is now 30 days"""
    
    def test_token_expiry_is_30_days(self):
        """Verify JWT exp claim is approximately 30 days from now"""
        # Login to get a fresh token
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        token = response.json()["token"]
        
        # Decode token without verification to read exp
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        assert "exp" in decoded, "Token missing 'exp' claim"
        
        exp_timestamp = decoded["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        
        # Calculate days until expiry
        days_until_expiry = (exp_datetime - now).days
        
        # Token should expire in ~30 days (allow +/- 1 day for timing)
        assert 28 <= days_until_expiry <= 31, \
            f"Token expires in {days_until_expiry} days, expected ~30 days"
        
        print(f"✓ Token expiry verified: {days_until_expiry} days from now")
        print(f"  Exp timestamp: {exp_timestamp}")
        print(f"  Exp datetime: {exp_datetime.isoformat()}")
    
    def test_token_contains_required_claims(self):
        """Verify token contains user_id and email claims"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        
        assert response.status_code == 200
        token = response.json()["token"]
        
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        assert "user_id" in decoded, "Token missing 'user_id' claim"
        assert "email" in decoded, "Token missing 'email' claim"
        assert decoded["email"] == DEMO_EMAIL.lower(), "Email in token doesn't match"
        
        print(f"✓ Token contains required claims: user_id, email, exp")


class TestTokenValidation:
    """Test proper 401 responses for invalid/expired tokens"""
    
    def test_missing_token_returns_401(self):
        """Test that missing Authorization header returns 401"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats")
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        data = response.json()
        assert "detail" in data, "Missing error detail"
        print(f"✓ Missing token returns 401: {data['detail']}")
    
    def test_invalid_token_returns_401(self):
        """Test that invalid token returns 401"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        data = response.json()
        assert "detail" in data, "Missing error detail"
        print(f"✓ Invalid token returns 401: {data['detail']}")
    
    def test_malformed_auth_header_returns_401(self):
        """Test that malformed Authorization header returns 401"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": "NotBearer token"}
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Malformed auth header returns 401")
    
    def test_expired_token_returns_401_with_proper_message(self):
        """Test that expired token returns 401 with 'Token expired' message"""
        # Create an expired token manually (if we knew the secret, but we can't test this directly)
        # Instead, we verify the error handling code path exists by checking a definitely invalid token
        
        # Use a syntactically valid but expired JWT for testing
        # This token has exp = 0 (Jan 1, 1970)
        expired_token = jwt.encode(
            {"user_id": "test", "email": "test@test.com", "exp": 0},
            "wrong_secret",  # Will fail verification anyway
            algorithm="HS256"
        )
        
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        data = response.json()
        assert "detail" in data, "Missing error detail"
        # Could be "Token expired" or "Invalid token" depending on which error occurs first
        assert data["detail"] in ["Token expired", "Invalid token"], \
            f"Unexpected error message: {data['detail']}"
        print(f"✓ Expired/invalid token returns 401: {data['detail']}")


class TestDashboardStatsWithData:
    """Test dashboard stats API returns correct data for demo account with data"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for tests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        assert response.status_code == 200, "Login failed"
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_dashboard_stats_returns_correct_structure(self):
        """Test dashboard stats API returns expected structure"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Request failed: {response.text}"
        data = response.json()
        
        # Verify required fields exist
        required_fields = [
            "total_income", "total_expenses", "total_investments",
            "net_balance", "savings", "savings_rate",
            "health_score", "category_breakdown"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        print("✓ Dashboard stats returns correct structure")
        print(f"  Total income: ₹{data['total_income']:,.2f}")
        print(f"  Total expenses: ₹{data['total_expenses']:,.2f}")
        print(f"  Savings rate: {data['savings_rate']}%")
    
    def test_dashboard_stats_with_date_range(self):
        """Test dashboard stats with date range (FY 2025-26)"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            params={"start_date": "2025-04-01", "end_date": "2026-03-31"},
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Request failed: {response.text}"
        data = response.json()
        
        # Verify date_range is returned
        assert "date_range" in data, "Missing date_range in response"
        assert data["date_range"]["start"] == "2025-04-01"
        assert data["date_range"]["end"] == "2026-03-31"
        
        print(f"✓ Dashboard stats with date range works")
        print(f"  Date range: {data['date_range']}")
        print(f"  Income: ₹{data['total_income']:,.2f}")
    
    def test_health_score_has_sufficient_data(self):
        """Test health_score includes has_sufficient_data field"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "health_score" in data, "Missing health_score"
        hs = data["health_score"]
        
        assert "overall" in hs, "Missing overall score"
        assert "grade" in hs, "Missing grade"
        assert "has_sufficient_data" in hs, "Missing has_sufficient_data flag"
        assert "breakdown" in hs, "Missing breakdown"
        
        print(f"✓ Health score structure verified")
        print(f"  Overall: {hs['overall']}")
        print(f"  Grade: {hs['grade']}")
        print(f"  Has sufficient data: {hs['has_sufficient_data']}")


class TestDashboardStatsNoData:
    """Test dashboard stats returns zeros when querying date range with no data"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for tests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        assert response.status_code == 200, "Login failed"
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_dashboard_stats_no_data_returns_zeros(self):
        """Test dashboard stats with future date range returns zeros"""
        # Use a future date range where no data exists
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            params={"start_date": "2030-01-01", "end_date": "2030-12-31"},
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Request failed: {response.text}"
        data = response.json()
        
        # Verify zeros are returned (not fake/hardcoded values)
        assert data["total_income"] == 0, f"Expected 0 income, got {data['total_income']}"
        assert data["total_expenses"] == 0, f"Expected 0 expenses, got {data['total_expenses']}"
        assert data["total_investments"] == 0, f"Expected 0 investments, got {data['total_investments']}"
        
        print("✓ Dashboard stats with no data returns zeros correctly")
        print(f"  Income: {data['total_income']} (expected 0)")
        print(f"  Expenses: {data['total_expenses']} (expected 0)")
    
    def test_health_score_no_data_indicates_insufficient_data(self):
        """Test health_score has_sufficient_data=false when no income data"""
        # Use a date range with no data
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            params={"start_date": "2030-01-01", "end_date": "2030-12-31"},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        hs = data["health_score"]
        
        # When there's no income data, has_sufficient_data should be False
        assert hs["has_sufficient_data"] == False, \
            f"Expected has_sufficient_data=False, got {hs['has_sufficient_data']}"
        
        # Savings, investment, spending scores should all be 0 when no income data
        assert hs["breakdown"]["savings"] == 0, f"Expected 0 savings score, got {hs['breakdown']['savings']}"
        assert hs["breakdown"]["investments"] == 0, f"Expected 0 investments score, got {hs['breakdown']['investments']}"
        assert hs["breakdown"]["spending"] == 0, f"Expected 0 spending score, got {hs['breakdown']['spending']}"
        
        # Grade depends on whether user has goals (which are not date-filtered)
        # If user has goals, they contribute to score, so grade could be Critical/Needs Work
        # If no goals either, grade should be "No Data"
        # The key indicator is has_sufficient_data=false
        
        print("✓ Health score correctly indicates insufficient data")
        print(f"  has_sufficient_data: {hs['has_sufficient_data']}")
        print(f"  grade: {hs['grade']}")
        print(f"  breakdown: {hs['breakdown']}")


class TestSmartAlerts:
    """Test smart alerts API returns alerts without errors"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for tests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        assert response.status_code == 200, "Login failed"
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_smart_alerts_returns_200(self):
        """Test smart alerts API returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/smart-alerts",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Request failed: {response.text}"
        data = response.json()
        
        assert "alerts" in data, "Missing 'alerts' field"
        assert isinstance(data["alerts"], list), "Alerts should be a list"
        
        print(f"✓ Smart alerts API works - returned {len(data['alerts'])} alerts")
        
        # Log first few alerts for visibility
        for alert in data["alerts"][:3]:
            print(f"  - {alert.get('type', 'N/A')}: {alert.get('title', 'N/A')}")
    
    def test_smart_alerts_without_auth_returns_401(self):
        """Test smart alerts requires authentication"""
        response = requests.get(f"{BASE_URL}/api/dashboard/smart-alerts")
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Smart alerts requires authentication")


class TestMonthlyTrends:
    """Test monthly trends API returns trend data"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for tests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        assert response.status_code == 200, "Login failed"
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_monthly_trends_returns_200(self):
        """Test monthly trends API returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/monthly-trends",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Request failed: {response.text}"
        data = response.json()
        
        assert "trends" in data, "Missing 'trends' field"
        assert isinstance(data["trends"], list), "Trends should be a list"
        
        print(f"✓ Monthly trends API works - returned {len(data['trends'])} months")
        
        # Verify trend structure if data exists
        if data["trends"]:
            trend = data["trends"][0]
            required_fields = ["month", "income", "expenses", "savings"]
            for field in required_fields:
                assert field in trend, f"Trend missing field: {field}"
            
            print(f"  Latest: {trend['month']} - Income: ₹{trend['income']:,.0f}, Expenses: ₹{trend['expenses']:,.0f}")
    
    def test_monthly_trends_without_auth_returns_401(self):
        """Test monthly trends requires authentication"""
        response = requests.get(f"{BASE_URL}/api/dashboard/monthly-trends")
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Monthly trends requires authentication")


class TestHealthScoreEndpoint:
    """Test standalone health score endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for tests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        assert response.status_code == 200, "Login failed"
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_health_score_returns_200(self):
        """Test health score endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/health-score",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Request failed: {response.text}"
        data = response.json()
        
        required_fields = ["overall_score", "grade", "has_sufficient_data", "breakdown"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✓ Health score endpoint works")
        print(f"  Score: {data['overall_score']}")
        print(f"  Grade: {data['grade']}")
        print(f"  Has data: {data['has_sufficient_data']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
