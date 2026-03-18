"""
Test Tax Deductions Browser and AI Screen Context Features
Iteration 18 - Testing:
1. Tax Deductions data structure and API
2. AI Chat screen_context parameter
3. Dashboard Custom Date Range
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://visor-preview.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "rajesh@visor.demo"
TEST_PASSWORD = "Demo@123"


class TestAuthentication:
    """Authentication tests"""
    
    def test_login_success(self):
        """Test login with demo credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert "user" in data, "No user in response"
        print(f"✓ Login successful for {TEST_EMAIL}")
        return data["token"]


class TestAIScreenContext:
    """Test AI Chat with screen_context parameter"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_ai_chat_without_screen_context(self, auth_token):
        """Test AI chat works without screen_context (backward compatibility)"""
        response = requests.post(
            f"{BASE_URL}/api/ai/chat",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"message": "What is my savings rate?"}
        )
        assert response.status_code == 200, f"AI chat failed: {response.text}"
        data = response.json()
        assert "content" in data, "No content in AI response"
        assert len(data["content"]) > 0, "Empty AI response"
        print(f"✓ AI chat without screen_context works")
        print(f"  Response preview: {data['content'][:100]}...")
    
    def test_ai_chat_with_dashboard_context(self, auth_token):
        """Test AI chat with dashboard screen context"""
        dashboard_context = """User is on the DASHBOARD screen viewing:
- Financial health score and overview cards
- Income, expenses, and investments summary
- Expense breakdown pie chart
- Trend analysis with insights
- Recent transactions list
- Financial goals progress
The user may be looking at their overall financial picture and want personalized advice."""
        
        response = requests.post(
            f"{BASE_URL}/api/ai/chat",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "message": "What should I focus on?",
                "screen_context": dashboard_context
            }
        )
        assert response.status_code == 200, f"AI chat with context failed: {response.text}"
        data = response.json()
        assert "content" in data, "No content in AI response"
        print(f"✓ AI chat with dashboard context works")
        print(f"  Response preview: {data['content'][:150]}...")
    
    def test_ai_chat_with_investments_context(self, auth_token):
        """Test AI chat with investments screen context"""
        investments_context = """User is on the INVESTMENTS screen viewing:
- Live Indian market data (Nifty, Sensex, Gold, Silver prices)
- Portfolio overview with gain/loss tracking
- Holdings breakdown (stocks, mutual funds, ETFs)
- Asset allocation pie chart
- Risk profile and recommended strategy
- SIPs and recurring investments
- Tax planning section (80C, 80D deductions)
- Capital gains tax estimates
- Financial goals
The user may want investment advice, tax planning help, or portfolio rebalancing suggestions."""
        
        response = requests.post(
            f"{BASE_URL}/api/ai/chat",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "message": "How can I save more tax?",
                "screen_context": investments_context
            }
        )
        assert response.status_code == 200, f"AI chat with investments context failed: {response.text}"
        data = response.json()
        assert "content" in data, "No content in AI response"
        # Check if response mentions tax-related terms
        content_lower = data["content"].lower()
        tax_terms = ["80c", "80d", "tax", "deduction", "section", "invest"]
        has_tax_term = any(term in content_lower for term in tax_terms)
        print(f"✓ AI chat with investments context works")
        print(f"  Contains tax-related terms: {has_tax_term}")
        print(f"  Response preview: {data['content'][:150]}...")


class TestDashboardDateRange:
    """Test Dashboard stats with custom date range"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_dashboard_stats_no_date_range(self, auth_token):
        """Test dashboard stats without date range (all data)"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        data = response.json()
        assert "total_income" in data, "Missing total_income"
        assert "total_expenses" in data, "Missing total_expenses"
        assert "health_score" in data, "Missing health_score"
        print(f"✓ Dashboard stats without date range works")
        print(f"  Total Income: ₹{data['total_income']:,.2f}")
        print(f"  Total Expenses: ₹{data['total_expenses']:,.2f}")
    
    def test_dashboard_stats_with_month_range(self, auth_token):
        """Test dashboard stats with current month date range"""
        from datetime import datetime
        now = datetime.now()
        start_date = f"{now.year}-{now.month:02d}-01"
        end_date = now.strftime("%Y-%m-%d")
        
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats?start_date={start_date}&end_date={end_date}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Dashboard stats with month range failed: {response.text}"
        data = response.json()
        assert "date_range" in data, "Missing date_range in response"
        if data["date_range"]:
            assert data["date_range"]["start"] == start_date, "Start date mismatch"
            assert data["date_range"]["end"] == end_date, "End date mismatch"
        print(f"✓ Dashboard stats with month range works")
        print(f"  Date range: {start_date} to {end_date}")
    
    def test_dashboard_stats_with_custom_range(self, auth_token):
        """Test dashboard stats with custom date range"""
        start_date = "2025-01-01"
        end_date = "2025-12-31"
        
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats?start_date={start_date}&end_date={end_date}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Dashboard stats with custom range failed: {response.text}"
        data = response.json()
        assert "trend_data" in data, "Missing trend_data"
        assert "trend_insights" in data, "Missing trend_insights"
        print(f"✓ Dashboard stats with custom range works")
        print(f"  Trend data points: {len(data.get('trend_data', []))}")
        print(f"  Trend insights: {len(data.get('trend_insights', []))}")


class TestTaxSummaryAPI:
    """Test Tax Summary API (used by Tax Planning section)"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_tax_summary_endpoint(self, auth_token):
        """Test tax summary endpoint returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/tax-summary",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Tax summary failed: {response.text}"
        data = response.json()
        
        # Check required fields
        assert "sections" in data, "Missing sections"
        assert "total_deductions" in data, "Missing total_deductions"
        assert "tax_saved_30_slab" in data, "Missing tax_saved_30_slab"
        assert "tax_saved_20_slab" in data, "Missing tax_saved_20_slab"
        assert "fy" in data, "Missing fy (financial year)"
        
        print(f"✓ Tax summary endpoint works")
        print(f"  Financial Year: {data['fy']}")
        print(f"  Total Deductions: ₹{data['total_deductions']:,.2f}")
        print(f"  Tax Saved (30% slab): ₹{data['tax_saved_30_slab']:,.2f}")
        print(f"  Sections count: {len(data['sections'])}")
        
        # Check section structure
        for section in data["sections"]:
            assert "section" in section, "Section missing 'section' field"
            assert "label" in section, "Section missing 'label' field"
            assert "limit" in section, "Section missing 'limit' field"
            assert "used" in section, "Section missing 'used' field"
            print(f"    - {section['label']}: ₹{section['used']:,.0f} / ₹{section['limit']:,.0f}")
    
    def test_capital_gains_endpoint(self, auth_token):
        """Test capital gains endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/capital-gains",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Capital gains failed: {response.text}"
        data = response.json()
        
        assert "gains" in data, "Missing gains"
        assert "summary" in data, "Missing summary"
        assert "notes" in data, "Missing notes"
        assert "fy" in data, "Missing fy"
        
        summary = data["summary"]
        assert "total_stcg" in summary, "Missing total_stcg"
        assert "total_ltcg" in summary, "Missing total_ltcg"
        assert "ltcg_exemption" in summary, "Missing ltcg_exemption"
        
        print(f"✓ Capital gains endpoint works")
        print(f"  STCG: ₹{summary['total_stcg']:,.2f}")
        print(f"  LTCG: ₹{summary['total_ltcg']:,.2f}")
        print(f"  LTCG Exemption: ₹{summary['ltcg_exemption']:,.2f}")


class TestRecurringInvestments:
    """Test Recurring Investments (SIPs) API"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_recurring_list(self, auth_token):
        """Test recurring investments list"""
        response = requests.get(
            f"{BASE_URL}/api/recurring",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Recurring list failed: {response.text}"
        data = response.json()
        
        assert "recurring" in data, "Missing recurring list"
        assert "summary" in data, "Missing summary"
        
        summary = data["summary"]
        assert "total_count" in summary, "Missing total_count"
        assert "active_count" in summary, "Missing active_count"
        assert "monthly_commitment" in summary, "Missing monthly_commitment"
        
        print(f"✓ Recurring investments list works")
        print(f"  Total SIPs: {summary['total_count']}")
        print(f"  Active SIPs: {summary['active_count']}")
        print(f"  Monthly Commitment: ₹{summary['monthly_commitment']:,.2f}")


class TestPortfolioRebalancing:
    """Test Portfolio Rebalancing API"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_rebalancing_endpoint(self, auth_token):
        """Test portfolio rebalancing endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/portfolio-rebalancing",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Rebalancing failed: {response.text}"
        data = response.json()
        
        assert "profile" in data, "Missing profile"
        assert "target" in data, "Missing target allocation"
        assert "actual" in data, "Missing actual allocation"
        
        print(f"✓ Portfolio rebalancing endpoint works")
        print(f"  Risk Profile: {data['profile']}")
        print(f"  Strategy: {data.get('strategy_name', 'N/A')}")
        print(f"  Total Portfolio: ₹{data.get('total', 0):,.2f}")
        
        if data.get("actions"):
            print(f"  Rebalancing Actions: {len(data['actions'])}")
            for action in data["actions"][:3]:
                print(f"    - {action.get('suggestion', 'N/A')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
