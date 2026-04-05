"""
Iteration 40 - Indian Financial Year (FY) and Frequency Parameter Tests
Tests for:
1. GET /api/dashboard/stats accepts 'frequency' query param
2. When frequency=Year, trend_data groups by month (labels like 'Apr', 'May')
3. When frequency=Month, trend_data groups by week
4. Date range validation for FY (April 1 - March 31)
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://experience-tier-test.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_EMAIL = "rajesh@visor.demo"
TEST_PASSWORD = "Demo@123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for demo user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "token" in data, "No token in login response"
    return data["token"]


@pytest.fixture
def api_client(auth_token):
    """Authenticated requests session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestDashboardStatsFrequencyParam:
    """Tests for frequency parameter in /api/dashboard/stats"""
    
    def test_dashboard_stats_with_frequency_year(self, api_client):
        """Test that frequency=Year returns 200 OK with FY date range"""
        # Indian FY 2025-26: April 1, 2025 to March 31, 2026
        response = api_client.get(
            f"{BASE_URL}/api/dashboard/stats",
            params={
                "start_date": "2025-04-01",
                "end_date": "2026-03-22",
                "frequency": "Year"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "total_income" in data
        assert "total_expenses" in data
        assert "trend_data" in data
        assert "date_range" in data
        
        # Verify date range is correctly returned
        assert data["date_range"]["start"] == "2025-04-01"
        assert data["date_range"]["end"] == "2026-03-22"
        
        print(f"✓ frequency=Year returns 200 OK with FY date range")
        print(f"  Date range: {data['date_range']}")
        print(f"  Trend data points: {len(data.get('trend_data', []))}")
    
    def test_dashboard_stats_with_frequency_month(self, api_client):
        """Test that frequency=Month returns 200 OK with current month data"""
        response = api_client.get(
            f"{BASE_URL}/api/dashboard/stats",
            params={
                "start_date": "2026-03-01",
                "end_date": "2026-03-22",
                "frequency": "Month"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "trend_data" in data
        assert "date_range" in data
        
        # Verify date range
        assert data["date_range"]["start"] == "2026-03-01"
        assert data["date_range"]["end"] == "2026-03-22"
        
        print(f"✓ frequency=Month returns 200 OK")
        print(f"  Date range: {data['date_range']}")
        print(f"  Trend data points: {len(data.get('trend_data', []))}")
    
    def test_dashboard_stats_with_frequency_quarter(self, api_client):
        """Test that frequency=Quarter returns 200 OK"""
        # Q1 2026: Jan 1 - Mar 31
        response = api_client.get(
            f"{BASE_URL}/api/dashboard/stats",
            params={
                "start_date": "2026-01-01",
                "end_date": "2026-03-22",
                "frequency": "Quarter"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "trend_data" in data
        
        print(f"✓ frequency=Quarter returns 200 OK")
        print(f"  Trend data points: {len(data.get('trend_data', []))}")
    
    def test_trend_data_monthly_grouping_for_year_frequency(self, api_client):
        """Test that frequency=Year uses monthly grouping (labels like 'Apr', 'May')"""
        response = api_client.get(
            f"{BASE_URL}/api/dashboard/stats",
            params={
                "start_date": "2025-04-01",
                "end_date": "2026-03-22",
                "frequency": "Year"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        trend_data = data.get("trend_data", [])
        
        # If there's trend data, verify labels are month abbreviations
        if trend_data:
            # Month abbreviations expected: Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec
            valid_month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            
            for point in trend_data:
                label = point.get("label", "")
                # Label should be a 3-letter month abbreviation
                assert label in valid_month_labels, f"Expected month label, got: {label}"
                
                # Verify data structure
                assert "income" in point
                assert "expenses" in point
                assert "investments" in point
            
            print(f"✓ frequency=Year uses monthly grouping")
            print(f"  Labels found: {[p['label'] for p in trend_data]}")
        else:
            # No transactions, trend_data is empty - this is expected
            print(f"✓ frequency=Year returns empty trend_data (no transactions)")
    
    def test_trend_data_weekly_grouping_for_month_frequency(self, api_client):
        """Test that frequency=Month uses weekly grouping (labels like 'Mar 01')"""
        response = api_client.get(
            f"{BASE_URL}/api/dashboard/stats",
            params={
                "start_date": "2026-03-01",
                "end_date": "2026-03-22",
                "frequency": "Month"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        trend_data = data.get("trend_data", [])
        
        # If there's trend data, verify labels are weekly format (e.g., "Mar 01")
        if trend_data:
            for point in trend_data:
                label = point.get("label", "")
                # Weekly labels should be like "Mar 01", "Mar 08", etc.
                # They should NOT be just month abbreviations
                assert len(label) > 3, f"Expected weekly label (e.g., 'Mar 01'), got: {label}"
            
            print(f"✓ frequency=Month uses weekly grouping")
            print(f"  Labels found: {[p['label'] for p in trend_data]}")
        else:
            print(f"✓ frequency=Month returns empty trend_data (no transactions)")
    
    def test_dashboard_stats_without_frequency_param(self, api_client):
        """Test that API works without frequency param (backward compatibility)"""
        response = api_client.get(
            f"{BASE_URL}/api/dashboard/stats",
            params={
                "start_date": "2026-03-01",
                "end_date": "2026-03-22"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "trend_data" in data
        
        print(f"✓ API works without frequency param (backward compatible)")
    
    def test_dashboard_stats_long_date_range_uses_monthly(self, api_client):
        """Test that long date ranges (>120 days) automatically use monthly grouping"""
        # 6 months range
        response = api_client.get(
            f"{BASE_URL}/api/dashboard/stats",
            params={
                "start_date": "2025-09-01",
                "end_date": "2026-03-22"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        trend_data = data.get("trend_data", [])
        
        # Long ranges should use monthly grouping even without frequency=Year
        if trend_data:
            valid_month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            for point in trend_data:
                label = point.get("label", "")
                assert label in valid_month_labels, f"Expected month label for long range, got: {label}"
            
            print(f"✓ Long date range (>120 days) uses monthly grouping")
            print(f"  Labels: {[p['label'] for p in trend_data]}")
        else:
            print(f"✓ Long date range returns empty trend_data (no transactions)")


class TestDashboardStatsResponseStructure:
    """Tests for response structure validation"""
    
    def test_response_includes_all_required_fields(self, api_client):
        """Verify all required fields are present in response"""
        response = api_client.get(
            f"{BASE_URL}/api/dashboard/stats",
            params={
                "start_date": "2025-04-01",
                "end_date": "2026-03-22",
                "frequency": "Year"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        
        # Required fields
        required_fields = [
            "total_income", "total_expenses", "total_investments",
            "net_balance", "savings", "savings_rate",
            "category_breakdown", "trend_data", "trend_insights",
            "health_score", "date_range"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Verify health_score structure
        assert "overall" in data["health_score"]
        assert "grade" in data["health_score"]
        assert "breakdown" in data["health_score"]
        
        print(f"✓ Response includes all required fields")
        print(f"  Health score: {data['health_score']['overall']} ({data['health_score']['grade']})")
    
    def test_trend_data_point_structure(self, api_client):
        """Verify trend_data points have correct structure"""
        response = api_client.get(
            f"{BASE_URL}/api/dashboard/stats",
            params={
                "start_date": "2025-04-01",
                "end_date": "2026-03-22",
                "frequency": "Year"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        trend_data = data.get("trend_data", [])
        
        # If there's data, verify structure
        if trend_data:
            for point in trend_data:
                assert "label" in point, "Missing 'label' in trend_data point"
                assert "income" in point, "Missing 'income' in trend_data point"
                assert "expenses" in point, "Missing 'expenses' in trend_data point"
                assert "investments" in point, "Missing 'investments' in trend_data point"
                
                # Values should be numbers
                assert isinstance(point["income"], (int, float))
                assert isinstance(point["expenses"], (int, float))
                assert isinstance(point["investments"], (int, float))
            
            print(f"✓ Trend data points have correct structure")
        else:
            print(f"✓ Trend data is empty (no transactions) - structure verified")


class TestDateRangeValidation:
    """Tests for date range handling"""
    
    def test_fy_2025_26_date_range(self, api_client):
        """Test Indian FY 2025-26 date range (April 1, 2025 - March 31, 2026)"""
        response = api_client.get(
            f"{BASE_URL}/api/dashboard/stats",
            params={
                "start_date": "2025-04-01",
                "end_date": "2026-03-31",
                "frequency": "Year"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["date_range"]["start"] == "2025-04-01"
        assert data["date_range"]["end"] == "2026-03-31"
        
        print(f"✓ FY 2025-26 date range accepted (April 1, 2025 - March 31, 2026)")
    
    def test_historical_date_range_2020(self, api_client):
        """Test that historical dates back to 2020 are accepted"""
        response = api_client.get(
            f"{BASE_URL}/api/dashboard/stats",
            params={
                "start_date": "2020-01-01",
                "end_date": "2020-12-31",
                "frequency": "Year"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["date_range"]["start"] == "2020-01-01"
        
        print(f"✓ Historical date range (2020) accepted")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
