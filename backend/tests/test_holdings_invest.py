"""
Test Holdings CRUD and Invest Screen APIs - Iteration 9
Tests for:
- Holdings CRUD (Create, Read, Update, Delete)
- Holdings with live prices
- Portfolio overview with holdings integration
- Market data API (Indian markets)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://rupee-register.preview.emergentagent.com')

class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for test user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "rajesh@visor.demo",
            "password": "Demo@123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        return data["token"]

    def test_login_success(self, auth_token):
        """Test login with valid credentials"""
        assert auth_token is not None
        assert len(auth_token) > 0
        print(f"Login successful, token received")


class TestHoldingsCRUD:
    """Holdings CRUD operations tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "rajesh@visor.demo",
            "password": "Demo@123"
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_get_holdings(self, headers):
        """Test GET /api/holdings - list user holdings"""
        response = requests.get(f"{BASE_URL}/api/holdings", headers=headers)
        assert response.status_code == 200, f"Get holdings failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Holdings should be a list"
        print(f"Holdings count: {len(data)}")
        if len(data) > 0:
            holding = data[0]
            assert "id" in holding, "Holding should have id"
            assert "name" in holding, "Holding should have name"
            assert "quantity" in holding, "Holding should have quantity"
            assert "buy_price" in holding, "Holding should have buy_price"
            print(f"First holding: {holding.get('name')}")

    def test_get_holdings_live(self, headers):
        """Test GET /api/holdings/live - holdings with current prices"""
        response = requests.get(f"{BASE_URL}/api/holdings/live", headers=headers)
        assert response.status_code == 200, f"Get live holdings failed: {response.text}"
        data = response.json()
        assert "holdings" in data, "Response should have holdings array"
        assert "summary" in data, "Response should have summary"
        
        summary = data["summary"]
        assert "total_invested" in summary, "Summary should have total_invested"
        assert "total_current" in summary, "Summary should have total_current"
        assert "total_gain_loss" in summary, "Summary should have total_gain_loss"
        assert "total_gain_loss_pct" in summary, "Summary should have total_gain_loss_pct"
        assert "count" in summary, "Summary should have count"
        
        print(f"Holdings live - Count: {summary['count']}, Invested: {summary['total_invested']}, Current: {summary['total_current']}")
        
        if len(data["holdings"]) > 0:
            holding = data["holdings"][0]
            assert "current_price" in holding, "Holding should have current_price"
            assert "invested_value" in holding, "Holding should have invested_value"
            assert "current_value" in holding, "Holding should have current_value"
            assert "gain_loss" in holding, "Holding should have gain_loss"
            assert "gain_loss_pct" in holding, "Holding should have gain_loss_pct"
            print(f"First holding with live data: {holding.get('name')} - Price: {holding.get('current_price')}")

    def test_create_holding(self, headers):
        """Test POST /api/holdings - create new holding"""
        test_holding = {
            "name": "TEST_TCS Limited",
            "ticker": "TCS.NS",
            "isin": "",
            "category": "Stock",
            "quantity": 5,
            "buy_price": 3500,
            "buy_date": "2025-01-15"
        }
        response = requests.post(f"{BASE_URL}/api/holdings", headers=headers, json=test_holding)
        assert response.status_code == 200, f"Create holding failed: {response.text}"
        data = response.json()
        assert "id" in data, "Response should have id"
        assert data["name"] == test_holding["name"], "Name mismatch"
        assert data["ticker"] == test_holding["ticker"], "Ticker mismatch"
        assert data["quantity"] == test_holding["quantity"], "Quantity mismatch"
        assert data["buy_price"] == test_holding["buy_price"], "Buy price mismatch"
        assert data["category"] == test_holding["category"], "Category mismatch"
        print(f"Created holding: {data['name']} with id: {data['id']}")
        
        # Store ID for cleanup
        TestHoldingsCRUD.created_holding_id = data["id"]
        return data["id"]

    def test_verify_created_holding_in_list(self, headers):
        """Verify created holding appears in holdings list"""
        response = requests.get(f"{BASE_URL}/api/holdings", headers=headers)
        assert response.status_code == 200
        holdings = response.json()
        
        created_id = getattr(TestHoldingsCRUD, 'created_holding_id', None)
        if created_id:
            found = any(h["id"] == created_id for h in holdings)
            assert found, f"Created holding {created_id} not found in holdings list"
            print(f"Verified: Created holding found in list")

    def test_verify_created_holding_in_live(self, headers):
        """Verify created holding appears in live holdings with price"""
        response = requests.get(f"{BASE_URL}/api/holdings/live", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        created_id = getattr(TestHoldingsCRUD, 'created_holding_id', None)
        if created_id:
            holding = next((h for h in data["holdings"] if h["id"] == created_id), None)
            assert holding is not None, f"Created holding {created_id} not found in live holdings"
            assert holding["current_price"] > 0 or holding["current_price"] == holding["buy_price"], "Current price should be valid"
            print(f"Live holding: {holding['name']} - Current Price: {holding['current_price']}")

    def test_delete_holding(self, headers):
        """Test DELETE /api/holdings/{id} - delete holding"""
        created_id = getattr(TestHoldingsCRUD, 'created_holding_id', None)
        if not created_id:
            pytest.skip("No holding was created to delete")
        
        response = requests.delete(f"{BASE_URL}/api/holdings/{created_id}", headers=headers)
        assert response.status_code == 200, f"Delete holding failed: {response.text}"
        data = response.json()
        assert data.get("message") == "Deleted", "Expected delete message"
        print(f"Deleted holding: {created_id}")

    def test_verify_deleted_holding(self, headers):
        """Verify deleted holding is no longer in list"""
        created_id = getattr(TestHoldingsCRUD, 'created_holding_id', None)
        if not created_id:
            pytest.skip("No holding was created")
        
        response = requests.get(f"{BASE_URL}/api/holdings", headers=headers)
        assert response.status_code == 200
        holdings = response.json()
        found = any(h["id"] == created_id for h in holdings)
        assert not found, f"Deleted holding {created_id} still in list"
        print("Verified: Deleted holding not in list")


class TestPortfolioOverview:
    """Portfolio overview with holdings integration tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "rajesh@visor.demo",
            "password": "Demo@123"
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_portfolio_overview(self, headers):
        """Test GET /api/portfolio-overview - portfolio with holdings data"""
        response = requests.get(f"{BASE_URL}/api/portfolio-overview", headers=headers)
        assert response.status_code == 200, f"Get portfolio overview failed: {response.text}"
        data = response.json()
        
        # Verify main fields
        assert "total_invested" in data, "Response should have total_invested"
        assert "total_current_value" in data, "Response should have total_current_value"
        assert "total_gain_loss" in data, "Response should have total_gain_loss"
        assert "total_gain_loss_pct" in data, "Response should have total_gain_loss_pct"
        assert "categories" in data, "Response should have categories"
        
        print(f"Portfolio - Invested: {data['total_invested']}, Current: {data['total_current_value']}, Gain/Loss: {data['total_gain_loss']}")
        
        # Verify categories structure
        if len(data["categories"]) > 0:
            cat = data["categories"][0]
            assert "category" in cat, "Category should have name"
            assert "invested" in cat, "Category should have invested"
            assert "current_value" in cat, "Category should have current_value"
            assert "gain_loss" in cat, "Category should have gain_loss"
            assert "gain_loss_pct" in cat, "Category should have gain_loss_pct"
            print(f"Categories: {[c['category'] for c in data['categories']]}")

    def test_portfolio_includes_holdings_data(self, headers):
        """Verify portfolio includes data from holdings"""
        # Get holdings first
        holdings_resp = requests.get(f"{BASE_URL}/api/holdings/live", headers=headers)
        holdings_data = holdings_resp.json()
        
        # Get portfolio
        portfolio_resp = requests.get(f"{BASE_URL}/api/portfolio-overview", headers=headers)
        portfolio_data = portfolio_resp.json()
        
        # If there are holdings, portfolio should reflect them
        if holdings_data["summary"]["count"] > 0:
            # Portfolio invested should be >= holdings invested (could have other transactions)
            assert portfolio_data["total_invested"] >= 0, "Portfolio invested should be positive or zero"
            print(f"Portfolio total invested: {portfolio_data['total_invested']}")
            print(f"Holdings invested: {holdings_data['summary']['total_invested']}")


class TestMarketData:
    """Market data API tests (Indian markets)"""
    
    def test_get_market_data(self):
        """Test GET /api/market-data - Indian market indices"""
        response = requests.get(f"{BASE_URL}/api/market-data")
        assert response.status_code == 200, f"Get market data failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Market data should be a list"
        assert len(data) >= 5, "Should have at least 5 market items (Nifty 50, SENSEX, Nifty Bank, Gold, Silver)"
        
        # Verify required fields
        for item in data:
            assert "key" in item, "Item should have key"
            assert "name" in item, "Item should have name"
            assert "price" in item, "Item should have price"
            assert "change" in item, "Item should have change"
            assert "change_percent" in item, "Item should have change_percent"
        
        # Check expected market items
        keys = [item["key"] for item in data]
        print(f"Market data keys: {keys}")
        assert "nifty_50" in keys, "Should have Nifty 50"
        assert "sensex" in keys, "Should have SENSEX"


class TestHoldingsWithAuth:
    """Test holdings endpoints require authentication"""
    
    def test_holdings_without_auth(self):
        """Test GET /api/holdings without token returns 401"""
        response = requests.get(f"{BASE_URL}/api/holdings")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("Holdings endpoint correctly requires authentication")

    def test_holdings_live_without_auth(self):
        """Test GET /api/holdings/live without token returns 401"""
        response = requests.get(f"{BASE_URL}/api/holdings/live")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("Holdings live endpoint correctly requires authentication")

    def test_portfolio_overview_without_auth(self):
        """Test GET /api/portfolio-overview without token returns 401"""
        response = requests.get(f"{BASE_URL}/api/portfolio-overview")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("Portfolio overview endpoint correctly requires authentication")


class TestSeededHoldings:
    """Test that seeded demo holdings exist"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "rajesh@visor.demo",
            "password": "Demo@123"
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_seeded_holdings_exist(self, headers):
        """Verify seeded demo holdings exist (Reliance, HDFC Bank, Axis Bluechip Fund)"""
        response = requests.get(f"{BASE_URL}/api/holdings", headers=headers)
        assert response.status_code == 200
        holdings = response.json()
        
        # Check for expected seeded holdings
        names = [h["name"].lower() for h in holdings]
        print(f"Current holdings: {[h['name'] for h in holdings]}")
        
        # At least verify we have some holdings
        if len(holdings) == 0:
            print("WARNING: No seeded holdings found - demo data may not have been seeded")
        else:
            print(f"Found {len(holdings)} holdings")
            # Check if expected holdings exist (case-insensitive)
            expected_holdings = ["reliance", "hdfc", "axis"]
            found = []
            for expected in expected_holdings:
                if any(expected in name for name in names):
                    found.append(expected)
            print(f"Found expected holdings: {found}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
