"""
Visor Finance App - Dashboard Redesign Tests (Iteration 2)
Tests for: New dashboard fields (savings, savings_rate, budget_items, invest_breakdown, monthly_savings)
and Financial Health breakdown
"""
import pytest
import requests
import os

# Use public backend URL
BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://experience-deploy.preview.emergentagent.com').rstrip('/')

@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session

@pytest.fixture
def demo_user_token(api_client):
    """Login with demo user and return token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "rajesh@visor.demo",
        "password": "Demo@123"
    })
    assert response.status_code == 200, f"Demo login failed: {response.text}"
    data = response.json()
    return data["token"]

# ══════════════════════════════════════
#  DASHBOARD REDESIGN TESTS
# ══════════════════════════════════════

class TestDashboardRedesign:
    """Test new dashboard fields for glassmorphism redesign"""
    
    def test_dashboard_stats_new_fields(self, api_client, demo_user_token):
        """Test that dashboard/stats returns all new fields"""
        response = api_client.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {demo_user_token}"}
        )
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        
        data = response.json()
        
        # Test new fields added for redesign
        new_fields = ["savings", "savings_rate", "expense_ratio", "investment_ratio", 
                     "budget_items", "invest_breakdown", "monthly_savings"]
        
        for field in new_fields:
            assert field in data, f"Missing new field: {field}"
        
        # Verify data types
        assert isinstance(data["savings"], (int, float)), "savings should be numeric"
        assert isinstance(data["savings_rate"], (int, float)), "savings_rate should be numeric"
        assert isinstance(data["expense_ratio"], (int, float)), "expense_ratio should be numeric"
        assert isinstance(data["investment_ratio"], (int, float)), "investment_ratio should be numeric"
        assert isinstance(data["monthly_savings"], (int, float)), "monthly_savings should be numeric"
        assert isinstance(data["budget_items"], list), "budget_items should be a list"
        assert isinstance(data["invest_breakdown"], dict), "invest_breakdown should be a dict"
        
        print(f"✓ All new dashboard fields present")
        print(f"  - Savings: ₹{data['savings']:,.2f}")
        print(f"  - Savings Rate: {data['savings_rate']}%")
        print(f"  - Expense Ratio: {data['expense_ratio']}%")
        print(f"  - Investment Ratio: {data['investment_ratio']}%")
        print(f"  - Monthly Savings: ₹{data['monthly_savings']:,.2f}")
    
    def test_budget_items_structure(self, api_client, demo_user_token):
        """Test budget_items array has correct structure"""
        response = api_client.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {demo_user_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        budget_items = data["budget_items"]
        
        if len(budget_items) > 0:
            # Check first item structure
            item = budget_items[0]
            assert "category" in item, "budget_item should have category"
            assert "amount" in item, "budget_item should have amount"
            assert "percentage" in item, "budget_item should have percentage"
            
            assert isinstance(item["category"], str)
            assert isinstance(item["amount"], (int, float))
            assert isinstance(item["percentage"], (int, float))
            
            # Percentage should be between 0-100
            assert 0 <= item["percentage"] <= 100, "percentage should be 0-100"
            
            print(f"✓ budget_items structure correct, {len(budget_items)} categories")
            for item in budget_items[:3]:  # Print first 3
                print(f"  - {item['category']}: ₹{item['amount']:,.0f} ({item['percentage']}%)")
        else:
            print("✓ budget_items is empty (no expenses yet)")
    
    def test_invest_breakdown_structure(self, api_client, demo_user_token):
        """Test invest_breakdown has correct structure"""
        response = api_client.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {demo_user_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        invest_breakdown = data["invest_breakdown"]
        
        if len(invest_breakdown) > 0:
            # Check structure
            for category, amount in invest_breakdown.items():
                assert isinstance(category, str), "category should be string"
                assert isinstance(amount, (int, float)), "amount should be numeric"
                assert amount >= 0, "amount should be non-negative"
            
            print(f"✓ invest_breakdown structure correct, {len(invest_breakdown)} categories")
            for cat, amt in list(invest_breakdown.items())[:3]:  # Print first 3
                print(f"  - {cat}: ₹{amt:,.0f}")
        else:
            print("✓ invest_breakdown is empty (no investments yet)")
    
    def test_waterfill_calculations(self, api_client, demo_user_token):
        """Test that percentages for waterfill cards are calculated correctly"""
        response = api_client.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {demo_user_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        
        # Calculate expected percentages
        total_income = data["total_income"]
        if total_income > 0:
            # Expense ratio should match total_expenses / total_income
            expected_expense_ratio = (data["total_expenses"] / total_income) * 100
            assert abs(data["expense_ratio"] - expected_expense_ratio) < 0.2, "expense_ratio calculation error"
            
            # Investment ratio should match total_investments / total_income
            expected_investment_ratio = (data["total_investments"] / total_income) * 100
            assert abs(data["investment_ratio"] - expected_investment_ratio) < 0.2, "investment_ratio calculation error"
            
            # Savings rate should be (income - expenses - investments) / income
            expected_savings_rate = ((total_income - data["total_expenses"] - data["total_investments"]) / total_income) * 100
            assert abs(data["savings_rate"] - expected_savings_rate) < 0.2, "savings_rate calculation error"
            
            print("✓ Waterfill percentage calculations correct")
            print(f"  - Income remaining (drain): {100 - data['expense_ratio']:.1f}%")
            print(f"  - Expenses (fill): {data['expense_ratio']:.1f}%")
            print(f"  - Savings (drain): {data['savings_rate']:.1f}%")
            print(f"  - Invested (drain): {data['investment_ratio']:.1f}%")
        else:
            print("✓ No income data for percentage calculation")

class TestHealthScoreBreakdown:
    """Test financial health score breakdown for redesign"""
    
    def test_health_score_breakdown_structure(self, api_client, demo_user_token):
        """Test that health-score returns breakdown object"""
        response = api_client.get(
            f"{BASE_URL}/api/health-score",
            headers={"Authorization": f"Bearer {demo_user_token}"}
        )
        assert response.status_code == 200, f"Health score failed: {response.text}"
        
        data = response.json()
        
        # Check breakdown field exists
        assert "breakdown" in data, "Missing breakdown field"
        breakdown = data["breakdown"]
        
        # Check breakdown structure
        required_breakdown_fields = ["savings", "investments", "spending", "goals"]
        for field in required_breakdown_fields:
            assert field in breakdown, f"Missing breakdown field: {field}"
            assert isinstance(breakdown[field], (int, float)), f"{field} should be numeric"
            assert 0 <= breakdown[field] <= 100, f"{field} should be between 0-100"
        
        print(f"✓ Health score breakdown structure correct")
        print(f"  - Overall: {data['overall_score']:.1f}/100 ({data['grade']})")
        print(f"  - Savings: {breakdown['savings']:.1f}")
        print(f"  - Investments: {breakdown['investments']:.1f}")
        print(f"  - Spending: {breakdown['spending']:.1f}")
        print(f"  - Goals: {breakdown['goals']:.1f}")
    
    def test_health_score_values(self, api_client, demo_user_token):
        """Test health score values are within valid ranges"""
        response = api_client.get(
            f"{BASE_URL}/api/health-score",
            headers={"Authorization": f"Bearer {demo_user_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        
        # Overall score should be 0-100
        assert 0 <= data["overall_score"] <= 100, "overall_score out of range"
        
        # Grade should match score
        score = data["overall_score"]
        grade = data["grade"]
        
        if score >= 80:
            assert grade == "Excellent", f"Grade mismatch for score {score}"
        elif score >= 65:
            assert grade == "Good", f"Grade mismatch for score {score}"
        elif score >= 45:
            assert grade == "Fair", f"Grade mismatch for score {score}"
        elif score >= 25:
            assert grade == "Needs Work", f"Grade mismatch for score {score}"
        else:
            assert grade == "Critical", f"Grade mismatch for score {score}"
        
        print(f"✓ Health score values valid: {score:.1f}/100 = {grade}")
