"""
Test Credit Card Analytics - Phase 2 Endpoints
==============================================
Testing the 4 new CC analytics features:
1. Due Date Calendar with smart reminders
2. Interest Calculator (minimum payment scenario)
3. Rewards Tracker (points/cashback/miles)
4. Best Card Recommender (AI-powered via GPT-4o)

Test Credentials: rajesh@visor.demo / Demo@123
"""

import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Fixtures
@pytest.fixture(scope="module")
def api_session():
    """Shared requests session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token(api_session):
    """Get authentication token for demo user."""
    response = api_session.post(f"{BASE_URL}/api/auth/login", json={
        "email": "rajesh@visor.demo",
        "password": "Demo@123"
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "token" in data, "No token in login response"
    return data["token"]


@pytest.fixture(scope="module")
def authenticated_session(api_session, auth_token):
    """Session with auth header."""
    api_session.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_session


# ==============================================================================
# Authentication Tests - Verify all endpoints require authentication
# ==============================================================================

class TestAuthRequired:
    """Verify all CC analytics endpoints require Bearer token auth."""
    
    def test_due_calendar_requires_auth(self, api_session):
        """Due calendar endpoint should return 401 without auth."""
        response = requests.get(f"{BASE_URL}/api/credit-cards/due-calendar")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Due calendar returns 401 for unauthenticated requests")
    
    def test_interest_calculator_requires_auth(self, api_session):
        """Interest calculator endpoint should return 401 without auth."""
        response = requests.post(f"{BASE_URL}/api/credit-cards/interest-calculator", json={"outstanding": 10000})
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Interest calculator returns 401 for unauthenticated requests")
    
    def test_rewards_tracker_requires_auth(self, api_session):
        """Rewards tracker endpoint should return 401 without auth."""
        response = requests.get(f"{BASE_URL}/api/credit-cards/rewards")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Rewards tracker returns 401 for unauthenticated requests")
    
    def test_recommender_requires_auth(self, api_session):
        """Card recommender endpoint should return 401 without auth."""
        response = requests.post(f"{BASE_URL}/api/credit-cards/recommend", json={"category": "Shopping", "amount": 1000})
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Card recommender returns 401 for unauthenticated requests")


# ==============================================================================
# Due Date Calendar Tests
# ==============================================================================

class TestDueCalendar:
    """Test the Due Date Calendar endpoint."""
    
    def test_due_calendar_returns_calendar_array(self, authenticated_session):
        """GET /api/credit-cards/due-calendar should return calendar array."""
        response = authenticated_session.get(f"{BASE_URL}/api/credit-cards/due-calendar")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "calendar" in data, "Response must contain 'calendar' key"
        assert isinstance(data["calendar"], list), "'calendar' must be an array"
        print(f"✓ Due calendar returns calendar array with {len(data['calendar'])} cards")
    
    def test_due_calendar_entry_structure(self, authenticated_session):
        """Each calendar entry should have required fields."""
        response = authenticated_session.get(f"{BASE_URL}/api/credit-cards/due-calendar")
        assert response.status_code == 200
        
        data = response.json()
        if not data["calendar"]:
            pytest.skip("No credit cards found for user")
        
        entry = data["calendar"][0]
        
        # Required fields
        required_fields = [
            "card_id", "card_name", "issuer", "last_four",
            "due_day", "billing_day", "next_due_date", 
            "days_until_due", "outstanding", "minimum_due",
            "reminders", "urgency"
        ]
        
        for field in required_fields:
            assert field in entry, f"Missing required field: {field}"
        
        # Validate data types
        assert isinstance(entry["days_until_due"], int), "days_until_due should be int"
        assert isinstance(entry["outstanding"], (int, float)), "outstanding should be numeric"
        assert isinstance(entry["minimum_due"], (int, float)), "minimum_due should be numeric"
        assert isinstance(entry["reminders"], list), "reminders should be array"
        assert entry["urgency"] in ["critical", "warning", "upcoming", "normal"], f"Invalid urgency: {entry['urgency']}"
        
        print(f"✓ Calendar entry structure validated: {entry['card_name']}")
        print(f"  - Days until due: {entry['days_until_due']}")
        print(f"  - Outstanding: ₹{entry['outstanding']}")
        print(f"  - Minimum due: ₹{entry['minimum_due']}")
        print(f"  - Urgency: {entry['urgency']}")
    
    def test_due_calendar_reminders_format(self, authenticated_session):
        """Reminders should have type and message."""
        response = authenticated_session.get(f"{BASE_URL}/api/credit-cards/due-calendar")
        assert response.status_code == 200
        
        data = response.json()
        if not data["calendar"]:
            pytest.skip("No credit cards found for user")
        
        # Find an entry with reminders
        entries_with_reminders = [e for e in data["calendar"] if e["reminders"]]
        if not entries_with_reminders:
            print("✓ No reminders found (all dues > 7 days away)")
            return
        
        entry = entries_with_reminders[0]
        for reminder in entry["reminders"]:
            assert "type" in reminder, "Reminder must have 'type'"
            assert "message" in reminder, "Reminder must have 'message'"
            assert reminder["type"] in ["critical", "warning", "upcoming"], f"Invalid reminder type: {reminder['type']}"
        
        print(f"✓ Reminders validated for {entry['card_name']}: {entry['reminders']}")
    
    def test_due_calendar_sorted_by_days_until(self, authenticated_session):
        """Calendar should be sorted by days_until_due ascending."""
        response = authenticated_session.get(f"{BASE_URL}/api/credit-cards/due-calendar")
        assert response.status_code == 200
        
        data = response.json()
        if len(data["calendar"]) < 2:
            pytest.skip("Not enough cards to verify sorting")
        
        days_list = [entry["days_until_due"] for entry in data["calendar"]]
        assert days_list == sorted(days_list), f"Calendar not sorted: {days_list}"
        print(f"✓ Calendar sorted by days_until_due: {days_list}")


# ==============================================================================
# Interest Calculator Tests
# ==============================================================================

class TestInterestCalculator:
    """Test the Interest Calculator endpoint."""
    
    def test_interest_calculator_basic(self, authenticated_session):
        """POST /api/credit-cards/interest-calculator with outstanding amount."""
        response = authenticated_session.post(
            f"{BASE_URL}/api/credit-cards/interest-calculator",
            json={"outstanding": 50000}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "summary" in data, "Response must contain 'summary'"
        assert "schedule" in data, "Response must contain 'schedule'"
        print("✓ Interest calculator returns summary and schedule")
    
    def test_interest_calculator_summary_structure(self, authenticated_session):
        """Summary should contain all required fields."""
        response = authenticated_session.post(
            f"{BASE_URL}/api/credit-cards/interest-calculator",
            json={"outstanding": 50000}
        )
        assert response.status_code == 200
        
        data = response.json()
        summary = data["summary"]
        
        required_fields = [
            "original_amount", "total_interest", "total_paid",
            "months_to_clear", "interest_pct_of_principal", "monthly_rate"
        ]
        
        for field in required_fields:
            assert field in summary, f"Missing field in summary: {field}"
        
        # Validate values
        assert summary["original_amount"] == 50000, "Original amount should match input"
        assert summary["total_interest"] > 0, "Total interest should be positive"
        assert summary["total_paid"] > summary["original_amount"], "Total paid should be more than principal"
        assert summary["months_to_clear"] > 0, "Months to clear should be positive"
        
        print(f"✓ Interest calculator summary validated:")
        print(f"  - Original: ₹{summary['original_amount']}")
        print(f"  - Total Interest: ₹{summary['total_interest']}")
        print(f"  - Total Paid: ₹{summary['total_paid']}")
        print(f"  - Months to clear: {summary['months_to_clear']}")
        print(f"  - Interest % of principal: {summary['interest_pct_of_principal']}%")
    
    def test_interest_calculator_schedule_entries(self, authenticated_session):
        """Schedule should contain monthly payment entries."""
        response = authenticated_session.post(
            f"{BASE_URL}/api/credit-cards/interest-calculator",
            json={"outstanding": 10000}
        )
        assert response.status_code == 200
        
        data = response.json()
        schedule = data["schedule"]
        
        assert len(schedule) > 0, "Schedule should have entries"
        
        # Check first entry structure
        entry = schedule[0]
        required_fields = ["month", "opening_balance", "interest", "payment", "closing_balance"]
        for field in required_fields:
            assert field in entry, f"Missing field in schedule entry: {field}"
        
        assert entry["month"] == 1, "First entry should be month 1"
        print(f"✓ Interest calculator schedule validated with {len(schedule)} entries")
    
    def test_interest_calculator_zero_outstanding(self, authenticated_session):
        """Zero outstanding should return error/empty result."""
        response = authenticated_session.post(
            f"{BASE_URL}/api/credit-cards/interest-calculator",
            json={"outstanding": 0}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Should return error or empty schedule
        assert "error" in data or len(data.get("schedule", [])) == 0, "Zero outstanding should return error or empty schedule"
        print("✓ Zero outstanding handled correctly")
    
    def test_interest_calculator_with_card_id(self, authenticated_session):
        """Interest calculator should use card-specific rate when card_id provided."""
        # First get a card_id
        calendar_response = authenticated_session.get(f"{BASE_URL}/api/credit-cards/due-calendar")
        if calendar_response.status_code != 200 or not calendar_response.json().get("calendar"):
            pytest.skip("No credit cards found")
        
        card = calendar_response.json()["calendar"][0]
        card_id = card["card_id"]
        
        response = authenticated_session.post(
            f"{BASE_URL}/api/credit-cards/interest-calculator",
            json={"outstanding": 30000, "card_id": card_id}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "summary" in data
        assert "monthly_rate" in data["summary"]
        print(f"✓ Interest calculator with card_id '{card_id}' returned rate: {data['summary']['monthly_rate']}%")
    
    def test_interest_calculator_custom_rate(self, authenticated_session):
        """Interest calculator should accept custom monthly_rate."""
        response = authenticated_session.post(
            f"{BASE_URL}/api/credit-cards/interest-calculator",
            json={"outstanding": 20000, "monthly_rate": 2.5}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["summary"]["monthly_rate"] == 2.5, "Should use provided rate"
        print("✓ Interest calculator accepts custom monthly_rate")


# ==============================================================================
# Rewards Tracker Tests
# ==============================================================================

class TestRewardsTracker:
    """Test the Rewards Tracker endpoint."""
    
    def test_rewards_tracker_basic(self, authenticated_session):
        """GET /api/credit-cards/rewards should return rewards data."""
        response = authenticated_session.get(f"{BASE_URL}/api/credit-cards/rewards")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "total_points" in data, "Response must contain 'total_points'"
        assert "total_rupee_value" in data, "Response must contain 'total_rupee_value'"
        assert "cards" in data, "Response must contain 'cards'"
        print(f"✓ Rewards tracker returns data: {data['total_points']} points (₹{data['total_rupee_value']})")
    
    def test_rewards_tracker_card_breakdown(self, authenticated_session):
        """Each card should have rewards breakdown."""
        response = authenticated_session.get(f"{BASE_URL}/api/credit-cards/rewards")
        assert response.status_code == 200
        
        data = response.json()
        if not data["cards"]:
            pytest.skip("No credit cards found")
        
        card = data["cards"][0]
        required_fields = [
            "card_id", "card_name", "last_four", "total_spend",
            "reward_points", "rupee_value", "point_value",
            "benefits", "categories", "monthly_trend"
        ]
        
        for field in required_fields:
            assert field in card, f"Missing field in card breakdown: {field}"
        
        assert isinstance(card["benefits"], list), "benefits should be array"
        assert isinstance(card["categories"], dict), "categories should be object"
        assert isinstance(card["monthly_trend"], list), "monthly_trend should be array"
        
        print(f"✓ Card rewards breakdown validated for {card['card_name']}")
        print(f"  - Total spend: ₹{card['total_spend']}")
        print(f"  - Reward points: {card['reward_points']}")
        print(f"  - Rupee value: ₹{card['rupee_value']}")
    
    def test_rewards_tracker_categories(self, authenticated_session):
        """Categories breakdown should have spend and points."""
        response = authenticated_session.get(f"{BASE_URL}/api/credit-cards/rewards")
        assert response.status_code == 200
        
        data = response.json()
        if not data["cards"]:
            pytest.skip("No credit cards found")
        
        card = data["cards"][0]
        categories = card["categories"]
        
        if categories:
            for cat_name, cat_data in categories.items():
                assert "spend" in cat_data, f"Category {cat_name} missing 'spend'"
                assert "points" in cat_data, f"Category {cat_name} missing 'points'"
            print(f"✓ Category breakdown validated: {list(categories.keys())}")
        else:
            print("✓ No category breakdown (no transactions)")
    
    def test_rewards_tracker_monthly_trend(self, authenticated_session):
        """Monthly trend should have 6 months of data."""
        response = authenticated_session.get(f"{BASE_URL}/api/credit-cards/rewards")
        assert response.status_code == 200
        
        data = response.json()
        if not data["cards"]:
            pytest.skip("No credit cards found")
        
        card = data["cards"][0]
        trend = card["monthly_trend"]
        
        assert len(trend) == 6, f"Expected 6 months trend, got {len(trend)}"
        
        for entry in trend:
            assert "month" in entry, "Trend entry missing 'month'"
            assert "points" in entry, "Trend entry missing 'points'"
            assert "spend" in entry, "Trend entry missing 'spend'"
        
        print(f"✓ Monthly trend validated: {[t['month'] for t in trend]}")
    
    def test_rewards_totals_match_sum(self, authenticated_session):
        """Total points and value should match sum of cards."""
        response = authenticated_session.get(f"{BASE_URL}/api/credit-cards/rewards")
        assert response.status_code == 200
        
        data = response.json()
        if not data["cards"]:
            pytest.skip("No credit cards found")
        
        calculated_points = sum(c["reward_points"] for c in data["cards"])
        calculated_value = sum(c["rupee_value"] for c in data["cards"])
        
        assert abs(data["total_points"] - calculated_points) < 1, "Total points mismatch"
        assert abs(data["total_rupee_value"] - calculated_value) < 1, "Total value mismatch"
        print(f"✓ Totals match: {data['total_points']} points, ₹{data['total_rupee_value']}")


# ==============================================================================
# Card Recommender Tests
# ==============================================================================

class TestCardRecommender:
    """Test the Best Card Recommender endpoint."""
    
    def test_recommender_basic(self, authenticated_session):
        """POST /api/credit-cards/recommend should return recommendations."""
        response = authenticated_session.post(
            f"{BASE_URL}/api/credit-cards/recommend",
            json={"category": "Shopping", "amount": 5000}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "recommendations" in data, "Response must contain 'recommendations'"
        assert "best_card" in data, "Response must contain 'best_card'"
        assert "ai_recommendation" in data, "Response must contain 'ai_recommendation'"
        assert "transaction" in data, "Response must contain 'transaction'"
        print(f"✓ Card recommender returns {len(data['recommendations'])} recommendations")
    
    def test_recommender_recommendation_structure(self, authenticated_session):
        """Each recommendation should have required fields."""
        response = authenticated_session.post(
            f"{BASE_URL}/api/credit-cards/recommend",
            json={"category": "Dining", "amount": 2000}
        )
        assert response.status_code == 200
        
        data = response.json()
        if not data["recommendations"]:
            pytest.skip("No recommendations returned (no active cards)")
        
        rec = data["recommendations"][0]
        required_fields = [
            "card_id", "card_name", "last_four", "issuer",
            "points_earned", "value_earned", "reward_note",
            "utilization_after", "credit_available", "score"
        ]
        
        for field in required_fields:
            assert field in rec, f"Missing field in recommendation: {field}"
        
        print(f"✓ Recommendation structure validated:")
        print(f"  - Best card: {rec['card_name']}")
        print(f"  - Points earned: {rec['points_earned']}")
        print(f"  - Value earned: ₹{rec['value_earned']}")
        print(f"  - Score: {rec['score']}")
    
    def test_recommender_ranked_by_score(self, authenticated_session):
        """Recommendations should be ranked by score descending."""
        response = authenticated_session.post(
            f"{BASE_URL}/api/credit-cards/recommend",
            json={"category": "Travel", "amount": 10000}
        )
        assert response.status_code == 200
        
        data = response.json()
        if len(data["recommendations"]) < 2:
            pytest.skip("Not enough cards to verify ranking")
        
        scores = [r["score"] for r in data["recommendations"]]
        assert scores == sorted(scores, reverse=True), f"Not sorted by score: {scores}"
        print(f"✓ Recommendations ranked by score: {scores}")
    
    def test_recommender_ai_recommendation_text(self, authenticated_session):
        """AI recommendation should be a non-empty string."""
        response = authenticated_session.post(
            f"{BASE_URL}/api/credit-cards/recommend",
            json={"category": "Shopping", "amount": 3000}
        )
        assert response.status_code == 200
        
        data = response.json()
        ai_text = data["ai_recommendation"]
        
        assert isinstance(ai_text, str), "AI recommendation should be a string"
        assert len(ai_text) > 0, "AI recommendation should not be empty"
        print(f"✓ AI recommendation (first 200 chars): {ai_text[:200]}...")
    
    def test_recommender_best_card_matches_first(self, authenticated_session):
        """best_card should match first recommendation."""
        response = authenticated_session.post(
            f"{BASE_URL}/api/credit-cards/recommend",
            json={"category": "Groceries", "amount": 1500}
        )
        assert response.status_code == 200
        
        data = response.json()
        if not data["recommendations"]:
            pytest.skip("No recommendations returned")
        
        assert data["best_card"]["card_id"] == data["recommendations"][0]["card_id"], "best_card should match first recommendation"
        print(f"✓ best_card matches first recommendation: {data['best_card']['card_name']}")
    
    def test_recommender_transaction_echo(self, authenticated_session):
        """Transaction details should be echoed back."""
        payload = {"category": "Fuel", "amount": 2500, "merchant": "HP Petrol"}
        response = authenticated_session.post(
            f"{BASE_URL}/api/credit-cards/recommend",
            json=payload
        )
        assert response.status_code == 200
        
        data = response.json()
        txn = data["transaction"]
        
        assert txn["category"] == "Fuel", "Category should be echoed"
        assert txn["amount"] == 2500, "Amount should be echoed"
        assert txn["merchant"] == "HP Petrol", "Merchant should be echoed"
        print(f"✓ Transaction echoed: {txn}")
    
    def test_recommender_different_categories(self, authenticated_session):
        """Test different category recommendations."""
        categories = ["Shopping", "Dining", "Travel", "Fuel", "Entertainment", "Groceries"]
        
        for category in categories:
            response = authenticated_session.post(
                f"{BASE_URL}/api/credit-cards/recommend",
                json={"category": category, "amount": 1000}
            )
            assert response.status_code == 200, f"Failed for category {category}"
        
        print(f"✓ Recommender works for all categories: {categories}")
    
    def test_recommender_no_active_cards(self, authenticated_session):
        """Should handle case when no active cards exist gracefully."""
        # We can't easily test this without modifying user data
        # Just verify the endpoint doesn't crash with a valid request
        response = authenticated_session.post(
            f"{BASE_URL}/api/credit-cards/recommend",
            json={"category": "Other", "amount": 100}
        )
        assert response.status_code == 200
        print("✓ Recommender handles requests gracefully")


# ==============================================================================
# Integration Tests
# ==============================================================================

class TestCCAnalyticsIntegration:
    """Integration tests across CC analytics endpoints."""
    
    def test_all_endpoints_work_together(self, authenticated_session):
        """Verify all 4 CC analytics endpoints return data."""
        # Due Calendar
        cal_response = authenticated_session.get(f"{BASE_URL}/api/credit-cards/due-calendar")
        assert cal_response.status_code == 200
        cal_data = cal_response.json()
        
        # Rewards Tracker
        rewards_response = authenticated_session.get(f"{BASE_URL}/api/credit-cards/rewards")
        assert rewards_response.status_code == 200
        rewards_data = rewards_response.json()
        
        # Interest Calculator
        interest_response = authenticated_session.post(
            f"{BASE_URL}/api/credit-cards/interest-calculator",
            json={"outstanding": 25000}
        )
        assert interest_response.status_code == 200
        interest_data = interest_response.json()
        
        # Card Recommender
        rec_response = authenticated_session.post(
            f"{BASE_URL}/api/credit-cards/recommend",
            json={"category": "Shopping", "amount": 5000}
        )
        assert rec_response.status_code == 200
        rec_data = rec_response.json()
        
        print("✓ All 4 CC analytics endpoints working:")
        print(f"  - Due Calendar: {len(cal_data['calendar'])} cards")
        print(f"  - Rewards: {rewards_data['total_points']} points")
        print(f"  - Interest Calc: {interest_data['summary']['months_to_clear']} months")
        print(f"  - Recommender: {len(rec_data['recommendations'])} options")
    
    def test_card_ids_consistent_across_endpoints(self, authenticated_session):
        """Card IDs should be consistent across endpoints."""
        # Get card IDs from due calendar
        cal_response = authenticated_session.get(f"{BASE_URL}/api/credit-cards/due-calendar")
        cal_cards = {c["card_id"] for c in cal_response.json()["calendar"]}
        
        # Get card IDs from rewards
        rewards_response = authenticated_session.get(f"{BASE_URL}/api/credit-cards/rewards")
        rewards_cards = {c["card_id"] for c in rewards_response.json()["cards"]}
        
        # Get card IDs from recommender
        rec_response = authenticated_session.post(
            f"{BASE_URL}/api/credit-cards/recommend",
            json={"category": "Shopping", "amount": 1000}
        )
        rec_cards = {c["card_id"] for c in rec_response.json()["recommendations"]}
        
        # All should have same card IDs
        assert cal_cards == rewards_cards, f"Calendar vs Rewards mismatch: {cal_cards} vs {rewards_cards}"
        assert cal_cards == rec_cards, f"Calendar vs Recommender mismatch: {cal_cards} vs {rec_cards}"
        
        print(f"✓ Card IDs consistent across all endpoints: {cal_cards}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
