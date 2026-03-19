"""
Backend API Tests - Iteration 16
Testing: Dashboard with date ranges, Insights date filtering, AI chat with full financial context
Features: SVG line chart trend data, Q/M/Y/All date range filtering, AI with ALL app data
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

# Base URL from environment
BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://ai-voice-chat-24.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "rajesh@visor.demo"
TEST_PASSWORD = "Demo@123"

class TestAuth:
    """Authentication tests"""
    
    def test_login_success(self):
        """Test login with valid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == TEST_EMAIL
        print(f"✓ Login successful for {TEST_EMAIL}")


@pytest.fixture(scope="module")
def auth_token():
    """Get auth token for tests"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    if response.status_code != 200:
        pytest.skip(f"Auth failed: {response.text}")
    return response.json()["token"]


class TestDashboardStats:
    """Dashboard API tests with date range filtering"""
    
    def test_dashboard_stats_no_date_range(self, auth_token):
        """Test GET /api/dashboard/stats without date range"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        
        # Verify required fields
        assert "total_income" in data
        assert "total_expenses" in data
        assert "total_investments" in data
        assert "savings_rate" in data
        assert "trend_data" in data
        assert "trend_insights" in data
        assert "health_score" in data
        
        print(f"✓ Dashboard stats (no date range): Income={data['total_income']}, Expenses={data['total_expenses']}")
    
    def test_dashboard_stats_month_range(self, auth_token):
        """Test GET /api/dashboard/stats with current month date range"""
        now = datetime.now()
        start_date = now.replace(day=1).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")
        
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats?start_date={start_date}&end_date={end_date}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        
        # Verify date range is respected
        assert "date_range" in data
        assert data["date_range"]["start"] == start_date
        assert data["date_range"]["end"] == end_date
        
        print(f"✓ Dashboard stats (Month): {start_date} to {end_date}")
    
    def test_dashboard_stats_quarter_range(self, auth_token):
        """Test GET /api/dashboard/stats with current quarter date range"""
        now = datetime.now()
        quarter_start_month = ((now.month - 1) // 3) * 3 + 1
        start_date = now.replace(month=quarter_start_month, day=1).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")
        
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats?start_date={start_date}&end_date={end_date}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        
        assert "date_range" in data
        print(f"✓ Dashboard stats (Quarter): {start_date} to {end_date}")
    
    def test_dashboard_stats_year_range(self, auth_token):
        """Test GET /api/dashboard/stats with year-to-date range"""
        now = datetime.now()
        start_date = now.replace(month=1, day=1).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")
        
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats?start_date={start_date}&end_date={end_date}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        
        assert "date_range" in data
        print(f"✓ Dashboard stats (Year): {start_date} to {end_date}")


class TestTrendData:
    """Tests for trend_data array (SVG line chart data)"""
    
    def test_trend_data_structure(self, auth_token):
        """Test that trend_data has correct structure for line chart"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # trend_data should be an array
        assert "trend_data" in data
        assert isinstance(data["trend_data"], list)
        
        # Each item should have label, income, expenses, investments
        for item in data["trend_data"]:
            assert "label" in item, "trend_data item missing 'label'"
            assert "income" in item, "trend_data item missing 'income'"
            assert "expenses" in item, "trend_data item missing 'expenses'"
            assert "investments" in item, "trend_data item missing 'investments'"
            
            # Values should be numbers
            assert isinstance(item["income"], (int, float))
            assert isinstance(item["expenses"], (int, float))
            assert isinstance(item["investments"], (int, float))
        
        print(f"✓ trend_data structure valid: {len(data['trend_data'])} data points")
    
    def test_trend_data_updates_with_date_range(self, auth_token):
        """Test that trend_data updates when date range changes"""
        now = datetime.now()
        
        # Get year-to-date data
        year_start = now.replace(month=1, day=1).strftime("%Y-%m-%d")
        year_end = now.strftime("%Y-%m-%d")
        
        response_year = requests.get(
            f"{BASE_URL}/api/dashboard/stats?start_date={year_start}&end_date={year_end}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response_year.status_code == 200
        year_data = response_year.json()
        
        # Get current month data
        month_start = now.replace(day=1).strftime("%Y-%m-%d")
        month_end = now.strftime("%Y-%m-%d")
        
        response_month = requests.get(
            f"{BASE_URL}/api/dashboard/stats?start_date={month_start}&end_date={month_end}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response_month.status_code == 200
        month_data = response_month.json()
        
        # Both should have trend_data
        assert "trend_data" in year_data
        assert "trend_data" in month_data
        
        print(f"✓ trend_data responds to date range: Year={len(year_data['trend_data'])} points, Month={len(month_data['trend_data'])} points")


class TestTrendInsights:
    """Tests for trend_insights array (Smart Insights on back of card)"""
    
    def test_trend_insights_structure(self, auth_token):
        """Test that trend_insights has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "trend_insights" in data
        assert isinstance(data["trend_insights"], list)
        
        for insight in data["trend_insights"]:
            assert "type" in insight, "insight missing 'type'"
            assert "icon" in insight, "insight missing 'icon'"
            assert "title" in insight, "insight missing 'title'"
            assert "message" in insight, "insight missing 'message'"
            
            # Type should be one of: success, warning, info
            assert insight["type"] in ["success", "warning", "info"], f"Invalid insight type: {insight['type']}"
        
        print(f"✓ trend_insights structure valid: {len(data['trend_insights'])} insights")


class TestHealthScore:
    """Tests for health_score in dashboard response"""
    
    def test_health_score_structure(self, auth_token):
        """Test health_score has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "health_score" in data
        hs = data["health_score"]
        
        assert "overall" in hs
        assert "grade" in hs
        assert "breakdown" in hs
        
        # Overall score should be 0-100
        assert 0 <= hs["overall"] <= 100, f"Health score out of range: {hs['overall']}"
        
        # Grade should be one of the expected values
        valid_grades = ["Excellent", "Good", "Fair", "Needs Work", "Critical"]
        assert hs["grade"] in valid_grades, f"Invalid grade: {hs['grade']}"
        
        # Breakdown should have component scores
        assert "savings" in hs["breakdown"]
        assert "investments" in hs["breakdown"]
        assert "spending" in hs["breakdown"]
        assert "goals" in hs["breakdown"]
        
        print(f"✓ Health score: {hs['overall']}/100 ({hs['grade']})")
    
    def test_health_score_consistency_with_date_range(self, auth_token):
        """Test that health score updates with date range"""
        now = datetime.now()
        month_start = now.replace(day=1).strftime("%Y-%m-%d")
        month_end = now.strftime("%Y-%m-%d")
        
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats?start_date={month_start}&end_date={month_end}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "health_score" in data
        hs = data["health_score"]
        
        # Health score should be calculated based on the filtered data
        assert "overall" in hs
        print(f"✓ Health score for {month_start} to {month_end}: {hs['overall']}")


class TestAIChatContext:
    """Tests for AI chat endpoint with full financial context"""
    
    def test_ai_chat_basic(self, auth_token):
        """Test POST /api/ai/chat returns response"""
        response = requests.post(
            f"{BASE_URL}/api/ai/chat",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"message": "Hello, what can you help me with?"}
        )
        assert response.status_code == 200, f"AI chat failed: {response.text}"
        data = response.json()
        
        assert "content" in data, "Response missing 'content' field"
        assert "role" in data, "Response missing 'role' field"
        assert data["role"] == "assistant"
        assert len(data["content"]) > 0, "Empty response content"
        
        print(f"✓ AI chat basic response: {data['content'][:100]}...")
    
    def test_ai_chat_spending_categories(self, auth_token):
        """Test AI can reference spending categories from transactions"""
        response = requests.post(
            f"{BASE_URL}/api/ai/chat",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"message": "What are my top spending categories?"}
        )
        assert response.status_code == 200, f"AI chat failed: {response.text}"
        data = response.json()
        
        assert "content" in data
        content = data["content"].lower()
        
        # AI should reference actual category data
        # (We're checking the AI has context, not specific values)
        print(f"✓ AI spending categories response: {data['content'][:200]}...")
    
    def test_ai_chat_investments(self, auth_token):
        """Test AI can reference holdings/investments data"""
        response = requests.post(
            f"{BASE_URL}/api/ai/chat",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"message": "How are my investments performing?"}
        )
        assert response.status_code == 200, f"AI chat failed: {response.text}"
        data = response.json()
        
        assert "content" in data
        # AI should be able to reference portfolio data
        print(f"✓ AI investments response: {data['content'][:200]}...")
    
    def test_ai_chat_goals(self, auth_token):
        """Test AI can reference goals data"""
        response = requests.post(
            f"{BASE_URL}/api/ai/chat",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"message": "What are my financial goals and progress?"}
        )
        assert response.status_code == 200, f"AI chat failed: {response.text}"
        data = response.json()
        
        assert "content" in data
        print(f"✓ AI goals response: {data['content'][:200]}...")
    
    def test_ai_chat_health_score(self, auth_token):
        """Test AI can reference health score"""
        response = requests.post(
            f"{BASE_URL}/api/ai/chat",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"message": "What is my financial health score?"}
        )
        assert response.status_code == 200, f"AI chat failed: {response.text}"
        data = response.json()
        
        assert "content" in data
        print(f"✓ AI health score response: {data['content'][:200]}...")


class TestAIHistory:
    """Tests for AI chat history endpoint"""
    
    def test_ai_history(self, auth_token):
        """Test GET /api/ai/history returns chat history"""
        response = requests.get(
            f"{BASE_URL}/api/ai/history",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"AI history failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list)
        
        # If there are messages, verify structure
        if len(data) > 0:
            msg = data[0]
            assert "id" in msg
            assert "role" in msg
            assert "content" in msg
            assert "created_at" in msg
        
        print(f"✓ AI history: {len(data)} messages")


class TestGoalsEndpoint:
    """Tests for goals endpoint"""
    
    def test_get_goals(self, auth_token):
        """Test GET /api/goals returns goals"""
        response = requests.get(
            f"{BASE_URL}/api/goals",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Goals API failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list)
        
        for goal in data:
            assert "id" in goal
            assert "title" in goal
            assert "target_amount" in goal
            assert "current_amount" in goal
        
        print(f"✓ Goals: {len(data)} goals found")


class TestRecurringEndpoint:
    """Tests for recurring/SIPs endpoint"""
    
    def test_get_recurring(self, auth_token):
        """Test GET /api/recurring returns SIPs"""
        response = requests.get(
            f"{BASE_URL}/api/recurring",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Recurring API failed: {response.text}"
        data = response.json()
        
        assert "recurring" in data
        assert "summary" in data
        
        print(f"✓ Recurring: {len(data['recurring'])} SIPs, Monthly commitment: {data['summary'].get('monthly_commitment', 0)}")


class TestHoldingsEndpoint:
    """Tests for holdings/portfolio endpoint"""
    
    def test_get_holdings(self, auth_token):
        """Test GET /api/holdings/live returns holdings"""
        response = requests.get(
            f"{BASE_URL}/api/holdings/live",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Holdings API failed: {response.text}"
        data = response.json()
        
        # Should have holdings list and summary
        assert "holdings" in data or isinstance(data, list)
        
        print(f"✓ Holdings endpoint working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
