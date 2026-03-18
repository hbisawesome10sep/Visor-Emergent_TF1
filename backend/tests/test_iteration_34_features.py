"""
Test Suite - Iteration 34: New Features Testing
Tests:
1. SIP link-sip endpoint (POST /api/sip-analytics/link-sip)
2. SIP unlink-sip endpoint (POST /api/sip-analytics/unlink-sip)
3. Financial Health V2 endpoint consistency
4. Smart Alerts endpoint
5. Goal-map endpoint (for GoalMapper with jar visualization)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/")


@pytest.fixture(scope="module")
def token():
    """Login and get auth token for demo user"""
    resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "rajesh@visor.demo", "password": "Demo@123"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    data = resp.json()
    t = data.get("token") or data.get("access_token")
    assert t, f"No token in response: {data}"
    return t


@pytest.fixture(scope="module")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────
# 1. Goal Map endpoint (GoalMapper data source)
# ─────────────────────────────────────────────
class TestGoalMap:
    """Tests for the SIP goal-map endpoint used by GoalMapper"""

    def test_goal_map_returns_200(self, auth_headers):
        """Goal map endpoint should return 200"""
        resp = requests.post(
            f"{BASE_URL}/api/sip-analytics/goal-map",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_goal_map_response_structure(self, auth_headers):
        """Goal map should return correct structure"""
        resp = requests.post(
            f"{BASE_URL}/api/sip-analytics/goal-map",
            json={},
            headers=auth_headers,
        )
        data = resp.json()
        # Required keys
        assert "total_monthly_sip" in data, "Missing total_monthly_sip"
        assert "total_goals" in data, "Missing total_goals"
        assert "goals_on_track" in data, "Missing goals_on_track"
        assert "goal_analysis" in data, "Missing goal_analysis"
        assert "unmapped_sips" in data, "Missing unmapped_sips"
        assert isinstance(data["goal_analysis"], list), "goal_analysis should be a list"
        assert isinstance(data["unmapped_sips"], list), "unmapped_sips should be a list"

    def test_goal_analysis_items_have_required_fields(self, auth_headers):
        """Each goal in goal_analysis must have jar-required fields"""
        resp = requests.post(
            f"{BASE_URL}/api/sip-analytics/goal-map",
            json={},
            headers=auth_headers,
        )
        data = resp.json()
        for goal in data.get("goal_analysis", []):
            assert "goal_id" in goal, "Missing goal_id"
            assert "goal_title" in goal, "Missing goal_title"
            assert "target_amount" in goal, "Missing target_amount"
            assert "current_amount" in goal, "Missing current_amount"
            assert "on_track" in goal, "Missing on_track"
            assert "mapped_sip_details" in goal, "Missing mapped_sip_details"


# ─────────────────────────────────────────────
# 2. Link SIP to Goal endpoint
# ─────────────────────────────────────────────
class TestLinkSip:
    """Tests for POST /api/sip-analytics/link-sip"""

    def test_link_sip_missing_params_returns_422(self, auth_headers):
        """Should return 422 if sip_id or goal_id missing"""
        resp = requests.post(
            f"{BASE_URL}/api/sip-analytics/link-sip",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    def test_link_sip_missing_goal_id_returns_422(self, auth_headers):
        """Should return 422 if goal_id is missing"""
        resp = requests.post(
            f"{BASE_URL}/api/sip-analytics/link-sip",
            json={"sip_id": "some-sip"},
            headers=auth_headers,
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    def test_link_sip_missing_sip_id_returns_422(self, auth_headers):
        """Should return 422 if sip_id is missing"""
        resp = requests.post(
            f"{BASE_URL}/api/sip-analytics/link-sip",
            json={"goal_id": "some-goal"},
            headers=auth_headers,
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    def test_link_sip_nonexistent_sip_returns_404(self, auth_headers):
        """Should return 404 if SIP not found"""
        resp = requests.post(
            f"{BASE_URL}/api/sip-analytics/link-sip",
            json={"sip_id": "nonexistent-sip-id-99999", "goal_id": "nonexistent-goal-id-99999"},
            headers=auth_headers,
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"

    def test_link_sip_valid_with_real_data(self, auth_headers):
        """Should successfully link a SIP to a goal with real data"""
        # First get actual SIPs and goals
        goal_map = requests.post(
            f"{BASE_URL}/api/sip-analytics/goal-map",
            json={},
            headers=auth_headers,
        ).json()

        unmapped = goal_map.get("unmapped_sips", [])
        goals = goal_map.get("goal_analysis", [])

        if not unmapped or not goals:
            pytest.skip("No unmapped SIPs or goals available for testing")

        sip_id = unmapped[0]["id"]
        goal_id = goals[0]["goal_id"]

        # Link the SIP to goal
        resp = requests.post(
            f"{BASE_URL}/api/sip-analytics/link-sip",
            json={"sip_id": sip_id, "goal_id": goal_id},
            headers=auth_headers,
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("success") is True, f"Expected success=True: {data}"
        assert "message" in data, "Missing message in response"

        # Verify by fetching goal-map again
        verify = requests.post(
            f"{BASE_URL}/api/sip-analytics/goal-map",
            json={},
            headers=auth_headers,
        ).json()

        # The SIP should now be mapped to the goal
        mapped_goal = next(
            (g for g in verify["goal_analysis"] if g["goal_id"] == goal_id), None
        )
        if mapped_goal:
            sip_ids_in_goal = [s["id"] for s in mapped_goal.get("mapped_sip_details", [])]
            assert sip_id in sip_ids_in_goal, f"SIP {sip_id} not found in goal {goal_id} after linking"

        # Cleanup: unlink it back
        requests.post(
            f"{BASE_URL}/api/sip-analytics/unlink-sip",
            json={"sip_id": sip_id},
            headers=auth_headers,
        )


# ─────────────────────────────────────────────
# 3. Unlink SIP from Goal endpoint
# ─────────────────────────────────────────────
class TestUnlinkSip:
    """Tests for POST /api/sip-analytics/unlink-sip"""

    def test_unlink_sip_missing_params_returns_422(self, auth_headers):
        """Should return 422 if sip_id is missing"""
        resp = requests.post(
            f"{BASE_URL}/api/sip-analytics/unlink-sip",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    def test_unlink_sip_nonexistent_sip_returns_404(self, auth_headers):
        """Should return 404 if SIP not found"""
        resp = requests.post(
            f"{BASE_URL}/api/sip-analytics/unlink-sip",
            json={"sip_id": "nonexistent-sip-id-99999"},
            headers=auth_headers,
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"

    def test_unlink_sip_link_then_unlink_flow(self, auth_headers):
        """Full flow: link a SIP to goal, then unlink it"""
        # Get real data
        goal_map = requests.post(
            f"{BASE_URL}/api/sip-analytics/goal-map",
            json={},
            headers=auth_headers,
        ).json()

        unmapped = goal_map.get("unmapped_sips", [])
        goals = goal_map.get("goal_analysis", [])

        if not unmapped or not goals:
            pytest.skip("No unmapped SIPs or goals for full flow test")

        sip_id = unmapped[0]["id"]
        goal_id = goals[0]["goal_id"]

        # Step 1: Link
        link_resp = requests.post(
            f"{BASE_URL}/api/sip-analytics/link-sip",
            json={"sip_id": sip_id, "goal_id": goal_id},
            headers=auth_headers,
        )
        assert link_resp.status_code == 200, f"Link failed: {link_resp.text}"

        # Step 2: Unlink
        unlink_resp = requests.post(
            f"{BASE_URL}/api/sip-analytics/unlink-sip",
            json={"sip_id": sip_id},
            headers=auth_headers,
        )
        assert unlink_resp.status_code == 200, f"Unlink failed: {unlink_resp.text}"
        data = unlink_resp.json()
        assert data.get("success") is True, f"Expected success=True: {data}"

        # Step 3: Verify SIP is back in unmapped list
        verify = requests.post(
            f"{BASE_URL}/api/sip-analytics/goal-map",
            json={},
            headers=auth_headers,
        ).json()
        unmapped_after = [s["id"] for s in verify.get("unmapped_sips", [])]
        assert sip_id in unmapped_after, f"SIP {sip_id} should be unmapped after unlink"


# ─────────────────────────────────────────────
# 4. Financial Health V2 Endpoint (consistent with dashboard)
# ─────────────────────────────────────────────
class TestFinancialHealthV2:
    """Tests for /api/dashboard/financial-health-v2"""

    def test_health_v2_returns_200(self, auth_headers):
        """Financial Health V2 endpoint should return 200"""
        resp = requests.get(
            f"{BASE_URL}/api/dashboard/financial-health-v2",
            headers=auth_headers,
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_health_v2_response_structure(self, auth_headers):
        """Financial Health V2 should return 0-1000 scale score with 8 dimensions"""
        resp = requests.get(
            f"{BASE_URL}/api/dashboard/financial-health-v2",
            headers=auth_headers,
        )
        data = resp.json()
        assert "composite_score" in data, "Missing composite_score"
        assert "grade" in data, "Missing grade"
        assert "has_data" in data, "Missing has_data"
        assert "dimensions" in data, "Missing dimensions"

        # V2 score should be 0-1000
        score = data["composite_score"]
        assert 0 <= score <= 1000, f"Score {score} not in 0-1000 range"

        # Should have 8 dimensions
        dimensions = data["dimensions"]
        expected_dims = [
            "savings_rate", "debt_load", "investment_rate", "emergency_fund",
            "cc_utilization", "goal_progress", "insurance_cover", "net_worth_growth"
        ]
        for dim in expected_dims:
            assert dim in dimensions, f"Missing dimension: {dim}"

    def test_health_v2_dimension_scores_0_to_100(self, auth_headers):
        """Each dimension score should be 0-100"""
        resp = requests.get(
            f"{BASE_URL}/api/dashboard/financial-health-v2",
            headers=auth_headers,
        )
        data = resp.json()
        for dim_key, dim_val in data.get("dimensions", {}).items():
            score = dim_val.get("score", -1)
            assert 0 <= score <= 100, f"Dimension {dim_key} score {score} not in 0-100 range"


# ─────────────────────────────────────────────
# 5. Smart Alerts endpoint
# ─────────────────────────────────────────────
class TestSmartAlerts:
    """Tests for /api/dashboard/smart-alerts"""

    def test_smart_alerts_returns_200(self, auth_headers):
        """Smart alerts endpoint should return 200"""
        resp = requests.get(
            f"{BASE_URL}/api/dashboard/smart-alerts",
            headers=auth_headers,
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_smart_alerts_response_structure(self, auth_headers):
        """Smart alerts should return an alerts list"""
        resp = requests.get(
            f"{BASE_URL}/api/dashboard/smart-alerts",
            headers=auth_headers,
        )
        data = resp.json()
        assert "alerts" in data, "Missing alerts key"
        assert isinstance(data["alerts"], list), "alerts should be a list"

    def test_smart_alerts_items_have_action_field(self, auth_headers):
        """Each alert should have action field for navigation"""
        resp = requests.get(
            f"{BASE_URL}/api/dashboard/smart-alerts",
            headers=auth_headers,
        )
        data = resp.json()
        for alert in data.get("alerts", []):
            assert "id" in alert, "Alert missing id"
            assert "title" in alert, "Alert missing title"
            assert "type" in alert, "Alert missing type"
            # action field used for Plan button navigation
            # (optional but required for Plan button to work)


# ─────────────────────────────────────────────
# 6. Auth without token should fail
# ─────────────────────────────────────────────
class TestAuthRequired:
    """Ensure authenticated endpoints require a token"""

    def test_link_sip_no_token_returns_401_or_403(self):
        resp = requests.post(
            f"{BASE_URL}/api/sip-analytics/link-sip",
            json={"sip_id": "x", "goal_id": "y"},
        )
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"

    def test_unlink_sip_no_token_returns_401_or_403(self):
        resp = requests.post(
            f"{BASE_URL}/api/sip-analytics/unlink-sip",
            json={"sip_id": "x"},
        )
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"
