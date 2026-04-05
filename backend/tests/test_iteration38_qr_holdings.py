"""
Iteration 38 - QR Page and Holdings Clear Button Tests
Tests:
1. GET /api/expo/status - Tunnel status API
2. GET /api/expo/qr - QR page HTML response
3. GET /api/holdings - Holdings list
4. POST /api/holdings - Create holding manually
5. DELETE /api/holdings/clear-all - Clear all holdings
6. GET /api/portfolio-overview - Portfolio summary
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://experience-deploy.preview.emergentagent.com').rstrip('/')


class TestExpoQREndpoints:
    """Tests for Expo QR page and status endpoints"""
    
    def test_expo_status_returns_expected_fields(self):
        """GET /api/expo/status should return hostname, exp_url, https_url, is_active"""
        response = requests.get(f"{BASE_URL}/api/expo/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "hostname" in data, "Missing 'hostname' field"
        assert "exp_url" in data, "Missing 'exp_url' field"
        assert "https_url" in data, "Missing 'https_url' field"
        assert "is_active" in data, "Missing 'is_active' field"
        
        # Verify structure
        if data["hostname"]:
            assert data["exp_url"].startswith("exp://"), f"exp_url should start with exp://, got {data['exp_url']}"
            assert data["https_url"].startswith("https://"), f"https_url should start with https://, got {data['https_url']}"
        
        print(f"✓ Expo status: hostname={data['hostname']}, is_active={data['is_active']}")
    
    def test_expo_qr_page_returns_html(self):
        """GET /api/expo/qr should return HTML page with QR code"""
        response = requests.get(f"{BASE_URL}/api/expo/qr")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        
        html = response.text
        # Check for essential HTML elements
        assert "<title>Visor Finance" in html, "Missing page title"
        assert "Expo Go (Mobile)" in html, "Missing Expo Go tab"
        assert "Web Preview" in html, "Missing Web Preview tab"
        assert "qr-canvas" in html, "Missing QR canvas element"
        assert "status-dot" in html, "Missing tunnel status indicator"
        assert "Open in Expo Go" in html, "Missing Open button"
        
        print("✓ QR page HTML contains all expected elements")


class TestHoldingsAPI:
    """Tests for Holdings CRUD operations"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "rajesh@visor.demo",
            "password": "Demo@123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["token"]
    
    def test_get_holdings_returns_structure(self, auth_token):
        """GET /api/holdings should return holdings array and summary"""
        response = requests.get(
            f"{BASE_URL}/api/holdings",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "holdings" in data, "Missing 'holdings' array"
        assert "summary" in data, "Missing 'summary' object"
        assert isinstance(data["holdings"], list)
        
        # Check summary structure
        summary = data["summary"]
        assert "total_invested" in summary
        assert "total_current_value" in summary
        assert "total_gain_loss" in summary
        assert "holding_count" in summary
        
        print(f"✓ Holdings API: {len(data['holdings'])} holdings, total invested: {summary['total_invested']}")
    
    def test_create_holding_manually(self, auth_token):
        """POST /api/holdings should create a new holding"""
        holding_data = {
            "name": "TEST_TCS Limited",
            "ticker": "TCS.NS",
            "isin": "INE467B01029",
            "category": "Stock",
            "quantity": 5,
            "buy_price": 4000,
            "buy_date": "2025-03-01"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/holdings",
            headers={"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"},
            json=holding_data
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == holding_data["name"]
        assert data["ticker"] == holding_data["ticker"]
        assert data["quantity"] == holding_data["quantity"]
        assert data["buy_price"] == holding_data["buy_price"]
        assert "id" in data
        assert data["source"] == "manual"
        
        print(f"✓ Created holding: {data['name']} (ID: {data['id']})")
        return data["id"]
    
    def test_portfolio_overview_returns_categories(self, auth_token):
        """GET /api/portfolio-overview should return portfolio summary with categories"""
        response = requests.get(
            f"{BASE_URL}/api/portfolio-overview",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "total_invested" in data
        assert "total_current_value" in data
        assert "total_gain_loss" in data
        assert "total_gain_loss_pct" in data
        assert "categories" in data
        assert "last_updated" in data
        
        # Categories should be an array
        assert isinstance(data["categories"], list)
        
        # If categories exist, check structure
        if data["categories"]:
            cat = data["categories"][0]
            assert "category" in cat
            assert "invested" in cat
            assert "current_value" in cat
            assert "gain_loss" in cat
        
        print(f"✓ Portfolio Overview: Invested={data['total_invested']}, Current={data['total_current_value']}, Categories={len(data['categories'])}")
    
    def test_clear_all_holdings_endpoint_exists(self, auth_token):
        """DELETE /api/holdings/clear-all endpoint should be accessible (don't actually delete)"""
        # Just verify the endpoint exists by checking authentication
        response = requests.delete(
            f"{BASE_URL}/api/holdings/clear-all",
            headers={"Authorization": "Bearer invalid_token"}
        )
        # Should return 401 for invalid token, not 404 (endpoint not found)
        assert response.status_code in [401, 403], f"Expected 401/403 for invalid auth, got {response.status_code}"
        
        print("✓ Clear all holdings endpoint exists and requires authentication")


class TestHoldingsClearFlow:
    """Test the full clear holdings flow (creates test data, then clears)"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "rajesh@visor.demo",
            "password": "Demo@123"
        })
        return response.json()["token"]
    
    def test_clear_holdings_works(self, auth_token):
        """DELETE /api/holdings/clear-all should delete all holdings"""
        # First create a test holding
        holding_data = {
            "name": "TEST_ClearTest Stock",
            "ticker": "CLEARTEST.NS",
            "isin": "CLEARTEST001",
            "category": "Stock",
            "quantity": 1,
            "buy_price": 100,
            "buy_date": "2025-01-01"
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/holdings",
            headers={"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"},
            json=holding_data
        )
        assert create_resp.status_code == 200
        
        # Get holdings count before clear
        holdings_before = requests.get(
            f"{BASE_URL}/api/holdings",
            headers={"Authorization": f"Bearer {auth_token}"}
        ).json()
        count_before = len(holdings_before["holdings"])
        print(f"Holdings before clear: {count_before}")
        
        # Clear all holdings
        clear_resp = requests.delete(
            f"{BASE_URL}/api/holdings/clear-all",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert clear_resp.status_code == 200
        
        data = clear_resp.json()
        assert "message" in data
        assert "deleted" in data
        assert data["deleted"] >= 0
        
        print(f"✓ Clear all holdings: {data['message']}")
        
        # Verify holdings are cleared
        holdings_after = requests.get(
            f"{BASE_URL}/api/holdings",
            headers={"Authorization": f"Bearer {auth_token}"}
        ).json()
        assert len(holdings_after["holdings"]) == 0, "Holdings should be empty after clear"
        
        print("✓ Verified: All holdings cleared successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
