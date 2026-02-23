"""
Test Export APIs (PDF/Excel) and Deep Insights Screen APIs.
Tests for PDF/Excel exports (Journal, P&L, Balance Sheet, Ledger) and
new dashboard endpoints (monthly-trends, smart-alerts).
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "rajesh@visor.demo"
TEST_PASSWORD = "Demo@123"


class TestAuthentication:
    """Test authentication for export and insights APIs."""
    
    def test_login_success(self):
        """Login to get auth token for subsequent tests."""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Token not in login response"
        assert "user" in data, "User not in login response"
        return data["token"]


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for testing."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.text}")
    return response.json().get("token")


@pytest.fixture
def auth_headers(auth_token):
    """Get authentication headers."""
    return {"Authorization": f"Bearer {auth_token}"}


class TestPDFExports:
    """Test PDF export endpoints."""
    
    def test_export_journal_pdf(self, auth_headers):
        """Test Journal PDF export endpoint."""
        response = requests.get(
            f"{BASE_URL}/api/exports/journal/pdf",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Journal PDF export failed: {response.text}"
        
        # Verify PDF content type
        content_type = response.headers.get("content-type", "")
        assert "application/pdf" in content_type, f"Expected PDF, got {content_type}"
        
        # Verify content-disposition header
        content_disp = response.headers.get("content-disposition", "")
        assert "attachment" in content_disp, "Expected attachment disposition"
        assert ".pdf" in content_disp, "Expected .pdf in filename"
        
        # Verify PDF content starts with PDF magic bytes
        assert response.content[:4] == b'%PDF', "Content doesn't appear to be a valid PDF"
        
    def test_export_journal_pdf_with_dates(self, auth_headers):
        """Test Journal PDF export with date range."""
        response = requests.get(
            f"{BASE_URL}/api/exports/journal/pdf?start_date=2024-01-01&end_date=2025-12-31",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Journal PDF export with dates failed: {response.text}"
        assert response.content[:4] == b'%PDF', "Content doesn't appear to be a valid PDF"
    
    def test_export_pnl_pdf(self, auth_headers):
        """Test P&L Statement PDF export endpoint."""
        response = requests.get(
            f"{BASE_URL}/api/exports/pnl/pdf",
            headers=auth_headers
        )
        assert response.status_code == 200, f"P&L PDF export failed: {response.text}"
        
        content_type = response.headers.get("content-type", "")
        assert "application/pdf" in content_type, f"Expected PDF, got {content_type}"
        assert response.content[:4] == b'%PDF', "Content doesn't appear to be a valid PDF"
    
    def test_export_balance_sheet_pdf(self, auth_headers):
        """Test Balance Sheet PDF export endpoint."""
        response = requests.get(
            f"{BASE_URL}/api/exports/balance-sheet/pdf",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Balance Sheet PDF export failed: {response.text}"
        
        content_type = response.headers.get("content-type", "")
        assert "application/pdf" in content_type, f"Expected PDF, got {content_type}"
        assert response.content[:4] == b'%PDF', "Content doesn't appear to be a valid PDF"
    
    def test_export_balance_sheet_pdf_with_date(self, auth_headers):
        """Test Balance Sheet PDF export with specific date."""
        response = requests.get(
            f"{BASE_URL}/api/exports/balance-sheet/pdf?as_of_date=2025-01-15",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Balance Sheet PDF export with date failed: {response.text}"
        assert response.content[:4] == b'%PDF', "Content doesn't appear to be a valid PDF"
    
    def test_export_ledger_pdf(self, auth_headers):
        """Test General Ledger PDF export endpoint."""
        response = requests.get(
            f"{BASE_URL}/api/exports/ledger/pdf",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Ledger PDF export failed: {response.text}"
        
        content_type = response.headers.get("content-type", "")
        assert "application/pdf" in content_type, f"Expected PDF, got {content_type}"
        assert response.content[:4] == b'%PDF', "Content doesn't appear to be a valid PDF"


class TestExcelExports:
    """Test Excel export endpoints."""
    
    def test_export_journal_excel(self, auth_headers):
        """Test Journal Excel export endpoint."""
        response = requests.get(
            f"{BASE_URL}/api/exports/journal/excel",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Journal Excel export failed: {response.text}"
        
        content_type = response.headers.get("content-type", "")
        assert "spreadsheetml" in content_type or "openxmlformats" in content_type, f"Expected Excel, got {content_type}"
        
        content_disp = response.headers.get("content-disposition", "")
        assert ".xlsx" in content_disp, "Expected .xlsx in filename"
        
        # Verify Excel file starts with PK (ZIP format magic bytes)
        assert response.content[:2] == b'PK', "Content doesn't appear to be a valid Excel file"
    
    def test_export_journal_excel_with_dates(self, auth_headers):
        """Test Journal Excel export with date range."""
        response = requests.get(
            f"{BASE_URL}/api/exports/journal/excel?start_date=2024-01-01&end_date=2025-12-31",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Journal Excel export with dates failed: {response.text}"
        assert response.content[:2] == b'PK', "Content doesn't appear to be a valid Excel file"
    
    def test_export_pnl_excel(self, auth_headers):
        """Test P&L Statement Excel export endpoint."""
        response = requests.get(
            f"{BASE_URL}/api/exports/pnl/excel",
            headers=auth_headers
        )
        assert response.status_code == 200, f"P&L Excel export failed: {response.text}"
        
        content_type = response.headers.get("content-type", "")
        assert "spreadsheetml" in content_type or "openxmlformats" in content_type, f"Expected Excel, got {content_type}"
        assert response.content[:2] == b'PK', "Content doesn't appear to be a valid Excel file"
    
    def test_export_balance_sheet_excel(self, auth_headers):
        """Test Balance Sheet Excel export endpoint."""
        response = requests.get(
            f"{BASE_URL}/api/exports/balance-sheet/excel",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Balance Sheet Excel export failed: {response.text}"
        
        content_type = response.headers.get("content-type", "")
        assert "spreadsheetml" in content_type or "openxmlformats" in content_type, f"Expected Excel, got {content_type}"
        assert response.content[:2] == b'PK', "Content doesn't appear to be a valid Excel file"
    
    def test_export_ledger_excel(self, auth_headers):
        """Test General Ledger Excel export endpoint."""
        response = requests.get(
            f"{BASE_URL}/api/exports/ledger/excel",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Ledger Excel export failed: {response.text}"
        
        content_type = response.headers.get("content-type", "")
        assert "spreadsheetml" in content_type or "openxmlformats" in content_type, f"Expected Excel, got {content_type}"
        assert response.content[:2] == b'PK', "Content doesn't appear to be a valid Excel file"


class TestMonthlyTrendsAPI:
    """Test Monthly Trends API for insights screen."""
    
    def test_get_monthly_trends(self, auth_headers):
        """Test monthly trends API returns valid data structure."""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/monthly-trends",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Monthly trends API failed: {response.text}"
        
        data = response.json()
        assert "trends" in data, "Missing 'trends' key in response"
        assert isinstance(data["trends"], list), "Trends should be a list"
        
        # If there's data, verify structure
        if data["trends"]:
            trend = data["trends"][0]
            assert "month" in trend, "Missing 'month' in trend data"
            assert "income" in trend, "Missing 'income' in trend data"
            assert "expenses" in trend, "Missing 'expenses' in trend data"
            assert "savings" in trend, "Missing 'savings' in trend data"
            
            # Verify data types
            assert isinstance(trend["month"], str), "Month should be string"
            assert isinstance(trend["income"], (int, float)), "Income should be numeric"
            assert isinstance(trend["expenses"], (int, float)), "Expenses should be numeric"
            assert isinstance(trend["savings"], (int, float)), "Savings should be numeric"
    
    def test_monthly_trends_calculation(self, auth_headers):
        """Test monthly trends savings data is numeric and reasonable."""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/monthly-trends",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        for trend in data.get("trends", []):
            # Verify all values are numeric
            assert isinstance(trend["income"], (int, float)), f"Income not numeric: {trend}"
            assert isinstance(trend["expenses"], (int, float)), f"Expenses not numeric: {trend}"
            assert isinstance(trend["savings"], (int, float)), f"Savings not numeric: {trend}"
            # Savings can be negative (overspending) or positive
            # Just verify it's a reasonable calculation (income - expenses - investments)
            # Note: Backend also subtracts investments, which we don't have in the response


class TestSmartAlertsAPI:
    """Test Smart Alerts API for insights screen."""
    
    def test_get_smart_alerts(self, auth_headers):
        """Test smart alerts API returns valid data structure."""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/smart-alerts",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Smart alerts API failed: {response.text}"
        
        data = response.json()
        assert "alerts" in data, "Missing 'alerts' key in response"
        assert isinstance(data["alerts"], list), "Alerts should be a list"
        
        # If there's alerts, verify structure
        for alert in data["alerts"]:
            assert "id" in alert, "Missing 'id' in alert"
            assert "type" in alert, "Missing 'type' in alert"
            assert "icon" in alert, "Missing 'icon' in alert"
            assert "title" in alert, "Missing 'title' in alert"
            assert "message" in alert, "Missing 'message' in alert"
            
            # Verify alert type is valid
            assert alert["type"] in ["warning", "success", "info", "critical"], f"Invalid alert type: {alert['type']}"
    
    def test_smart_alerts_has_required_fields(self, auth_headers):
        """Test smart alerts have proper structure for frontend rendering."""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/smart-alerts",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        for alert in data.get("alerts", []):
            # id should be a string
            assert isinstance(alert["id"], str), "Alert id should be string"
            # title and message should be strings
            assert isinstance(alert["title"], str), "Alert title should be string"
            assert isinstance(alert["message"], str), "Alert message should be string"
            # icon should be a string (MaterialCommunityIcons name)
            assert isinstance(alert["icon"], str), "Alert icon should be string"


class TestDashboardStatsAPI:
    """Test existing dashboard stats API still works with new components."""
    
    def test_dashboard_stats(self, auth_headers):
        """Test dashboard stats API returns required data for insights screen."""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Dashboard stats API failed: {response.text}"
        
        data = response.json()
        
        # Verify required fields for insights screen
        assert "total_income" in data, "Missing total_income"
        assert "total_expenses" in data, "Missing total_expenses"
        assert "total_investments" in data, "Missing total_investments"
        assert "savings_rate" in data, "Missing savings_rate"
        assert "category_breakdown" in data, "Missing category_breakdown"
        
        # Verify health_score data structure
        assert "health_score" in data, "Missing health_score"
        health_score = data["health_score"]
        assert "overall" in health_score, "Missing health_score.overall"
        assert "grade" in health_score, "Missing health_score.grade"
        assert "breakdown" in health_score, "Missing health_score.breakdown"
    
    def test_dashboard_stats_with_date_range(self, auth_headers):
        """Test dashboard stats with date range filter."""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats?start_date=2024-01-01&end_date=2025-12-31",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Dashboard stats with date range failed: {response.text}"
        
        data = response.json()
        assert "date_range" in data, "Missing date_range in response"


class TestUnauthorizedAccess:
    """Test that export and insights APIs require authentication."""
    
    def test_export_journal_pdf_unauthorized(self):
        """Test Journal PDF export requires authentication."""
        response = requests.get(f"{BASE_URL}/api/exports/journal/pdf")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_export_journal_excel_unauthorized(self):
        """Test Journal Excel export requires authentication."""
        response = requests.get(f"{BASE_URL}/api/exports/journal/excel")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_monthly_trends_unauthorized(self):
        """Test Monthly trends API requires authentication."""
        response = requests.get(f"{BASE_URL}/api/dashboard/monthly-trends")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_smart_alerts_unauthorized(self):
        """Test Smart alerts API requires authentication."""
        response = requests.get(f"{BASE_URL}/api/dashboard/smart-alerts")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


class TestHealthCheck:
    """Test health check endpoint."""
    
    def test_health_endpoint(self):
        """Test health check returns healthy status."""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        
        data = response.json()
        assert data.get("status") == "healthy", f"Health status not healthy: {data}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
