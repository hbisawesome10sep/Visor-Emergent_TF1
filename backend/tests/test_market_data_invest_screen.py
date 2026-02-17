"""
Backend API tests for Market Data and Invest Screen Phase 1
Tests:
- GET /api/market-data - 5 market items with all required fields
- POST /api/market-data/refresh - requires auth, triggers refresh
- GET /api/dashboard/stats - includes invest_breakdown for portfolio overview
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "rajesh@visor.demo"
TEST_PASSWORD = "Demo@123"


class TestMarketDataAPI:
    """Tests for market data endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token for authenticated requests"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_market_data_returns_list(self):
        """GET /api/market-data should return a list"""
        response = requests.get(f"{BASE_URL}/api/market-data")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_market_data_returns_5_items(self):
        """Market data should include 5 items (Nifty 50, SENSEX, Nifty Bank, Gold, Silver)"""
        response = requests.get(f"{BASE_URL}/api/market-data")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5, f"Expected 5 market items, got {len(data)}"
    
    def test_market_data_has_required_keys(self):
        """Each market item should have all required keys"""
        response = requests.get(f"{BASE_URL}/api/market-data")
        assert response.status_code == 200
        data = response.json()
        
        required_keys = ['key', 'name', 'price', 'change', 'change_percent', 'prev_close', 'icon', 'last_updated']
        for item in data:
            for key in required_keys:
                assert key in item, f"Missing key '{key}' in market item {item.get('key')}"
    
    def test_market_data_keys_correct(self):
        """Market data should have correct item keys"""
        response = requests.get(f"{BASE_URL}/api/market-data")
        assert response.status_code == 200
        data = response.json()
        
        expected_keys = {'nifty_50', 'sensex', 'nifty_bank', 'gold_10g', 'silver_1kg'}
        actual_keys = {item['key'] for item in data}
        assert actual_keys == expected_keys, f"Expected keys {expected_keys}, got {actual_keys}"
    
    def test_market_data_nifty_50(self):
        """Verify Nifty 50 data structure and values"""
        response = requests.get(f"{BASE_URL}/api/market-data")
        data = response.json()
        
        nifty_50 = next((item for item in data if item['key'] == 'nifty_50'), None)
        assert nifty_50 is not None, "Nifty 50 not found"
        assert nifty_50['name'] == "Nifty 50"
        assert nifty_50['icon'] == "chart-line"
        assert isinstance(nifty_50['price'], (int, float))
        assert nifty_50['price'] > 0
        assert isinstance(nifty_50['change'], (int, float))
        assert isinstance(nifty_50['change_percent'], (int, float))
    
    def test_market_data_sensex(self):
        """Verify SENSEX data structure"""
        response = requests.get(f"{BASE_URL}/api/market-data")
        data = response.json()
        
        sensex = next((item for item in data if item['key'] == 'sensex'), None)
        assert sensex is not None, "SENSEX not found"
        assert sensex['name'] == "SENSEX"
        assert sensex['icon'] == "chart-areaspline"
        assert isinstance(sensex['price'], (int, float))
    
    def test_market_data_nifty_bank(self):
        """Verify Nifty Bank data structure"""
        response = requests.get(f"{BASE_URL}/api/market-data")
        data = response.json()
        
        nifty_bank = next((item for item in data if item['key'] == 'nifty_bank'), None)
        assert nifty_bank is not None, "Nifty Bank not found"
        assert nifty_bank['name'] == "Nifty Bank"
        assert nifty_bank['icon'] == "bank"
    
    def test_market_data_gold(self):
        """Verify Gold (10g) data structure"""
        response = requests.get(f"{BASE_URL}/api/market-data")
        data = response.json()
        
        gold = next((item for item in data if item['key'] == 'gold_10g'), None)
        assert gold is not None, "Gold not found"
        assert gold['name'] == "Gold (10g)"
        assert gold['icon'] == "diamond-stone"
    
    def test_market_data_silver(self):
        """Verify Silver (1Kg) data structure"""
        response = requests.get(f"{BASE_URL}/api/market-data")
        data = response.json()
        
        silver = next((item for item in data if item['key'] == 'silver_1kg'), None)
        assert silver is not None, "Silver not found"
        assert silver['name'] == "Silver (1Kg)"
        assert silver['icon'] == "diamond-outline"
        # Silver 1Kg should be > 100000 INR
        assert silver['price'] > 100000, f"Silver price {silver['price']} seems too low for 1Kg"
    
    def test_market_data_no_auth_required(self):
        """Market data should be public (no auth needed)"""
        response = requests.get(f"{BASE_URL}/api/market-data")
        assert response.status_code == 200


class TestMarketDataRefreshAPI:
    """Tests for market data refresh endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_refresh_requires_auth(self):
        """POST /api/market-data/refresh should require authentication"""
        response = requests.post(f"{BASE_URL}/api/market-data/refresh")
        assert response.status_code == 401
        assert "Not authenticated" in response.json().get("detail", "")
    
    def test_refresh_with_auth_succeeds(self, auth_token):
        """POST /api/market-data/refresh with valid auth should return 200"""
        response = requests.post(
            f"{BASE_URL}/api/market-data/refresh",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "refresh triggered" in data["message"].lower()
    
    def test_refresh_with_invalid_token(self):
        """POST /api/market-data/refresh with invalid token should return 401"""
        response = requests.post(
            f"{BASE_URL}/api/market-data/refresh",
            headers={"Authorization": "Bearer invalid_token_xyz"}
        )
        assert response.status_code == 401


class TestDashboardStatsForInvestScreen:
    """Tests for dashboard/stats API that powers Portfolio Overview and Asset Allocation"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_dashboard_stats_requires_auth(self):
        """Dashboard stats should require authentication"""
        response = requests.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 401
    
    def test_dashboard_stats_returns_invest_breakdown(self, auth_token):
        """Dashboard stats should include invest_breakdown for pie chart"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "invest_breakdown" in data, "invest_breakdown field missing"
        assert isinstance(data["invest_breakdown"], dict)
    
    def test_dashboard_stats_total_investments(self, auth_token):
        """Dashboard stats should include total_investments"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "total_investments" in data
        assert isinstance(data["total_investments"], (int, float))
        assert data["total_investments"] >= 0
    
    def test_invest_breakdown_matches_total(self, auth_token):
        """invest_breakdown sum should match total_investments"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        breakdown_sum = sum(data.get("invest_breakdown", {}).values())
        total = data.get("total_investments", 0)
        
        # Allow small floating point difference
        assert abs(breakdown_sum - total) < 0.01, \
            f"invest_breakdown sum ({breakdown_sum}) doesn't match total_investments ({total})"
    
    def test_dashboard_stats_has_demo_data(self, auth_token):
        """Demo user should have seeded investment data"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Demo user Rajesh should have investments
        assert data.get("total_investments", 0) > 0, \
            "Demo user should have seeded investment data"
    
    def test_dashboard_includes_category_breakdown(self, auth_token):
        """Dashboard should include category_breakdown for expenses"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "category_breakdown" in data


class TestGoalsAPI:
    """Tests for financial goals API used in Invest screen"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_goals_list(self, auth_token):
        """GET /api/goals should return list"""
        response = requests.get(
            f"{BASE_URL}/api/goals",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_goals_requires_auth(self):
        """Goals endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/goals")
        assert response.status_code == 401
    
    def test_create_goal(self, auth_token):
        """Create a new financial goal"""
        goal_data = {
            "title": "TEST_Emergency Fund",
            "target_amount": 300000,
            "current_amount": 50000,
            "deadline": "2026-12-31",
            "category": "Safety"
        }
        response = requests.post(
            f"{BASE_URL}/api/goals",
            json=goal_data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["title"] == goal_data["title"]
        assert data["target_amount"] == goal_data["target_amount"]
        assert "id" in data
        
        # Cleanup
        goal_id = data["id"]
        requests.delete(
            f"{BASE_URL}/api/goals/{goal_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
    
    def test_update_goal(self, auth_token):
        """Update an existing goal"""
        # Create goal first
        create_response = requests.post(
            f"{BASE_URL}/api/goals",
            json={"title": "TEST_Update Goal", "target_amount": 100000, "deadline": "2026-12-31", "category": "Safety"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert create_response.status_code == 200
        goal_id = create_response.json()["id"]
        
        # Update
        update_response = requests.put(
            f"{BASE_URL}/api/goals/{goal_id}",
            json={"current_amount": 25000},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert update_response.status_code == 200
        assert update_response.json()["current_amount"] == 25000
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/goals/{goal_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
    
    def test_delete_goal(self, auth_token):
        """Delete a goal"""
        # Create goal
        create_response = requests.post(
            f"{BASE_URL}/api/goals",
            json={"title": "TEST_Delete Goal", "target_amount": 50000, "deadline": "2026-12-31", "category": "Other"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert create_response.status_code == 200
        goal_id = create_response.json()["id"]
        
        # Delete
        delete_response = requests.delete(
            f"{BASE_URL}/api/goals/{goal_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert delete_response.status_code == 200
        
        # Verify deleted
        get_response = requests.get(
            f"{BASE_URL}/api/goals",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        goal_ids = [g["id"] for g in get_response.json()]
        assert goal_id not in goal_ids


class TestAuthLogin:
    """Test login with provided credentials"""
    
    def test_login_demo_user(self):
        """Login with rajesh@visor.demo / Demo@123"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "rajesh@visor.demo", "password": "Demo@123"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == "rajesh@visor.demo"
        assert data["user"]["full_name"] == "Rajesh Kumar"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
