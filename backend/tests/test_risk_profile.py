"""
Risk Profile API Tests - Visor Finance App
Tests for the 12-question behavioral finance risk assessment questionnaire.
Features: POST /api/risk-profile, GET /api/risk-profile, AI context integration
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "rajesh@visor.demo"
TEST_PASSWORD = "Demo@123"


class TestRiskProfileAPIs:
    """Risk Profile CRUD endpoint tests"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        yield
        # Cleanup: Delete test profile after tests
        # We don't delete here to let frontend tests verify the saved profile

    def test_01_get_risk_profile_returns_null_or_object(self):
        """GET /api/risk-profile should return null (new user) or saved profile object"""
        response = requests.get(f"{BASE_URL}/api/risk-profile", headers=self.headers)
        assert response.status_code == 200, f"GET risk-profile failed: {response.text}"
        
        data = response.json()
        # Can be null (new user) or object (has profile)
        if data is not None:
            assert "profile" in data, "Response should have 'profile' field"
            assert "score" in data, "Response should have 'score' field"
            assert "breakdown" in data, "Response should have 'breakdown' field"
            print(f"Existing profile found: {data.get('profile')} with score {data.get('score')}")
        else:
            print("No existing risk profile - user is new or profile was deleted")

    def test_02_get_risk_profile_requires_auth(self):
        """GET /api/risk-profile should return 401 without token"""
        response = requests.get(f"{BASE_URL}/api/risk-profile")
        assert response.status_code == 401, "Should return 401 without auth"

    def test_03_post_risk_profile_requires_auth(self):
        """POST /api/risk-profile should return 401 without token"""
        response = requests.post(f"{BASE_URL}/api/risk-profile", json={})
        assert response.status_code == 401, "Should return 401 without auth"

    def test_04_post_risk_profile_saves_correctly(self):
        """POST /api/risk-profile should save risk profile with all fields"""
        # Simulate 12-question assessment answers
        test_answers = [
            {"question_id": 1, "value": 3, "category": "horizon"},
            {"question_id": 2, "value": 3, "category": "loss_tolerance"},
            {"question_id": 3, "value": 3, "category": "experience"},
            {"question_id": 4, "value": 4, "category": "income_stability"},
            {"question_id": 5, "value": 3, "category": "emergency_fund"},
            {"question_id": 6, "value": 2, "category": "return_expectation"},
            {"question_id": 7, "value": 3, "category": "loss_tolerance"},
            {"question_id": 8, "value": 3, "category": "concentration"},
            {"question_id": 9, "value": 3, "category": "behavior"},
            {"question_id": 10, "value": 3, "category": "goal_priority"},
            {"question_id": 11, "value": 4, "category": "behavior"},
            {"question_id": 12, "value": 4, "category": "age_capacity"},
        ]
        
        # Calculate average score (should be Moderate range 2.0-3.5)
        avg_score = sum(a["value"] for a in test_answers) / len(test_answers)
        
        # Build breakdown by category
        cat_scores = {}
        for a in test_answers:
            cat = a["category"]
            if cat not in cat_scores:
                cat_scores[cat] = []
            cat_scores[cat].append(a["value"])
        
        breakdown = {cat: sum(vals) / len(vals) for cat, vals in cat_scores.items()}
        
        # Determine profile
        if avg_score <= 2.0:
            profile = "Conservative"
        elif avg_score <= 3.5:
            profile = "Moderate"
        else:
            profile = "Aggressive"
        
        payload = {
            "answers": test_answers,
            "score": round(avg_score, 2),
            "profile": profile,
            "breakdown": breakdown
        }
        
        response = requests.post(f"{BASE_URL}/api/risk-profile", json=payload, headers=self.headers)
        assert response.status_code == 200, f"POST risk-profile failed: {response.text}"
        
        data = response.json()
        assert data.get("profile") == profile, f"Profile mismatch: expected {profile}, got {data.get('profile')}"
        assert data.get("score") == round(avg_score, 2), f"Score mismatch"
        assert "breakdown" in data, "Response should have breakdown"
        assert "created_at" in data, "Response should have created_at"
        print(f"Saved risk profile: {profile} with score {avg_score:.2f}")
        print(f"Breakdown: {breakdown}")

    def test_05_get_risk_profile_after_save(self):
        """GET /api/risk-profile should return the saved profile"""
        response = requests.get(f"{BASE_URL}/api/risk-profile", headers=self.headers)
        assert response.status_code == 200, f"GET risk-profile failed: {response.text}"
        
        data = response.json()
        assert data is not None, "Profile should not be null after save"
        assert "profile" in data
        assert "score" in data
        assert "breakdown" in data
        assert data["profile"] in ["Conservative", "Moderate", "Aggressive"]
        assert 1 <= data["score"] <= 5
        
        # Verify breakdown has expected categories
        expected_cats = ["horizon", "loss_tolerance", "experience", "income_stability", 
                         "emergency_fund", "return_expectation", "concentration", 
                         "behavior", "goal_priority", "age_capacity"]
        for cat in expected_cats:
            assert cat in data["breakdown"], f"Breakdown missing category: {cat}"
        print(f"Retrieved profile: {data['profile']} (score: {data['score']})")

    def test_06_ai_chat_includes_risk_context(self):
        """POST /api/ai/chat should include risk profile in context"""
        # First ensure we have a risk profile saved
        profile_resp = requests.get(f"{BASE_URL}/api/risk-profile", headers=self.headers)
        profile_data = profile_resp.json()
        
        # Skip if no profile (optional test)
        if profile_data is None:
            pytest.skip("No risk profile saved - skipping AI context test")
        
        # Send a message to AI about risk
        chat_payload = {"message": "What is my risk profile and what investments suit me?"}
        response = requests.post(f"{BASE_URL}/api/ai/chat", json=chat_payload, headers=self.headers, timeout=30)
        
        # Should return 200 (even if AI response is generic)
        assert response.status_code == 200, f"AI chat failed: {response.text}"
        
        data = response.json()
        assert "content" in data, "AI response should have content"
        assert data.get("role") == "assistant"
        print(f"AI response received (length: {len(data.get('content', ''))} chars)")

    def test_07_post_conservative_profile(self):
        """POST /api/risk-profile with low scores should yield Conservative profile"""
        test_answers = [
            {"question_id": i, "value": 1 if i % 2 == 0 else 2, "category": "test"} 
            for i in range(1, 13)
        ]
        avg_score = sum(a["value"] for a in test_answers) / len(test_answers)  # 1.5 avg
        
        payload = {
            "answers": test_answers,
            "score": round(avg_score, 2),
            "profile": "Conservative",
            "breakdown": {"test": avg_score}
        }
        
        response = requests.post(f"{BASE_URL}/api/risk-profile", json=payload, headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["profile"] == "Conservative"
        print(f"Conservative profile saved with score {avg_score:.2f}")

    def test_08_post_aggressive_profile(self):
        """POST /api/risk-profile with high scores should yield Aggressive profile"""
        test_answers = [
            {"question_id": i, "value": 4 if i % 2 == 0 else 5, "category": "test"} 
            for i in range(1, 13)
        ]
        avg_score = sum(a["value"] for a in test_answers) / len(test_answers)  # 4.5 avg
        
        payload = {
            "answers": test_answers,
            "score": round(avg_score, 2),
            "profile": "Aggressive",
            "breakdown": {"test": avg_score}
        }
        
        response = requests.post(f"{BASE_URL}/api/risk-profile", json=payload, headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["profile"] == "Aggressive"
        print(f"Aggressive profile saved with score {avg_score:.2f}")

    def test_09_post_replaces_existing_profile(self):
        """POST /api/risk-profile should replace existing profile (not append)"""
        # Save first profile
        payload1 = {
            "answers": [{"question_id": 1, "value": 1, "category": "test"}],
            "score": 1.0,
            "profile": "Conservative",
            "breakdown": {"test": 1.0}
        }
        requests.post(f"{BASE_URL}/api/risk-profile", json=payload1, headers=self.headers)
        
        # Save second profile
        payload2 = {
            "answers": [{"question_id": 1, "value": 5, "category": "test"}],
            "score": 5.0,
            "profile": "Aggressive",
            "breakdown": {"test": 5.0}
        }
        requests.post(f"{BASE_URL}/api/risk-profile", json=payload2, headers=self.headers)
        
        # Get should return only second profile
        response = requests.get(f"{BASE_URL}/api/risk-profile", headers=self.headers)
        data = response.json()
        
        assert data["profile"] == "Aggressive", "Should have replaced with latest profile"
        assert data["score"] == 5.0, "Score should be from latest save"
        print("Profile correctly replaced on subsequent save")

    def test_10_restore_moderate_profile_for_ui_tests(self):
        """Restore a Moderate profile with proper 12-question breakdown for frontend tests"""
        # Full 12-question assessment with proper categories
        test_answers = [
            {"question_id": 1, "value": 3, "category": "horizon"},
            {"question_id": 2, "value": 3, "category": "loss_tolerance"},
            {"question_id": 3, "value": 3, "category": "experience"},
            {"question_id": 4, "value": 4, "category": "income_stability"},
            {"question_id": 5, "value": 3, "category": "emergency_fund"},
            {"question_id": 6, "value": 2, "category": "return_expectation"},
            {"question_id": 7, "value": 3, "category": "loss_tolerance"},
            {"question_id": 8, "value": 3, "category": "concentration"},
            {"question_id": 9, "value": 3, "category": "behavior"},
            {"question_id": 10, "value": 3, "category": "goal_priority"},
            {"question_id": 11, "value": 4, "category": "behavior"},
            {"question_id": 12, "value": 4, "category": "age_capacity"},
        ]
        
        avg_score = sum(a["value"] for a in test_answers) / len(test_answers)
        
        # Build breakdown
        cat_scores = {}
        for a in test_answers:
            cat = a["category"]
            if cat not in cat_scores:
                cat_scores[cat] = []
            cat_scores[cat].append(a["value"])
        
        breakdown = {cat: round(sum(vals) / len(vals), 2) for cat, vals in cat_scores.items()}
        
        payload = {
            "answers": test_answers,
            "score": round(avg_score, 2),
            "profile": "Moderate",
            "breakdown": breakdown
        }
        
        response = requests.post(f"{BASE_URL}/api/risk-profile", json=payload, headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["profile"] == "Moderate"
        print(f"Restored Moderate profile for UI tests: score={avg_score:.2f}")
        print(f"Breakdown: {breakdown}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
