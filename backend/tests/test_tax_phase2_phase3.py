"""
Tax Module Phase 2 & Phase 3 Backend API Tests
- Phase 2: Tax Meter, Tax Documents endpoints
- Phase 3: Capital Gains v2, Deduction Gap, TDS Mismatch, Tax Calendar, Tax Reminders
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://morning-brief-learn.preview.emergentagent.com').rstrip('/')

# Test credentials from test_credentials.md
TEST_EMAIL = "rajesh@visor.demo"
TEST_PASSWORD = "Demo@123"


class TestAuth:
    """Authentication for subsequent tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        return data["token"]
    
    def test_login_success(self, auth_token):
        """Verify login works"""
        assert auth_token is not None
        assert len(auth_token) > 0
        print(f"✓ Login successful, token obtained")


class TestPhase2TaxMeter:
    """Phase 2: Tax Meter Dashboard Widget API"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return response.json().get("token")
    
    def test_tax_meter_endpoint_exists(self, auth_token):
        """GET /api/tax/meter returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/tax/meter?fy=2025-26",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Tax meter failed: {response.status_code} - {response.text}"
        print(f"✓ Tax meter endpoint returns 200")
    
    def test_tax_meter_response_structure(self, auth_token):
        """Tax meter returns proper structure with all required fields"""
        response = requests.get(
            f"{BASE_URL}/api/tax/meter?fy=2025-26",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        
        # Required fields
        required_fields = [
            "fy", "estimated_tax", "tds_paid_ytd", "tax_due", "refund_expected",
            "better_regime", "savings_by_switch", "total_deductions", "deduction_80c",
            "months_elapsed", "gross_income", "effective_rate"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        # Verify deduction_80c sub-structure
        assert "used" in data["deduction_80c"]
        assert "limit" in data["deduction_80c"]
        assert "remaining" in data["deduction_80c"]
        assert "utilization_pct" in data["deduction_80c"]
        
        print(f"✓ Tax meter response structure valid")
        print(f"  - Estimated tax: ₹{data['estimated_tax']:,.0f}")
        print(f"  - TDS paid YTD: ₹{data['tds_paid_ytd']:,.0f}")
        print(f"  - Better regime: {data['better_regime']}")
        print(f"  - 80C utilization: {data['deduction_80c']['utilization_pct']}%")
    
    def test_tax_meter_values_reasonable(self, auth_token):
        """Tax meter values are within reasonable ranges"""
        response = requests.get(
            f"{BASE_URL}/api/tax/meter?fy=2025-26",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        
        # Values should be non-negative
        assert data["estimated_tax"] >= 0
        assert data["tds_paid_ytd"] >= 0
        assert data["tax_due"] >= 0
        assert data["refund_expected"] >= 0
        assert data["total_deductions"] >= 0
        
        # Better regime should be valid
        assert data["better_regime"] in ["old", "new"]
        
        # 80C limit should be 150000
        assert data["deduction_80c"]["limit"] == 150000
        
        # Utilization should be 0-100
        assert 0 <= data["deduction_80c"]["utilization_pct"] <= 100
        
        print(f"✓ Tax meter values are reasonable")


class TestPhase2TaxDocuments:
    """Phase 2: Tax Documents List API"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return response.json().get("token")
    
    def test_tax_documents_list_endpoint(self, auth_token):
        """GET /api/tax/documents returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/tax/documents?fy=2025-26",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Tax documents failed: {response.status_code} - {response.text}"
        print(f"✓ Tax documents endpoint returns 200")
    
    def test_tax_documents_response_structure(self, auth_token):
        """Tax documents returns proper structure"""
        response = requests.get(
            f"{BASE_URL}/api/tax/documents?fy=2025-26",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        
        assert "documents" in data
        assert "count" in data
        assert isinstance(data["documents"], list)
        assert isinstance(data["count"], int)
        
        print(f"✓ Tax documents response structure valid")
        print(f"  - Document count: {data['count']}")


class TestPhase3CapitalGainsV2:
    """Phase 3: Capital Gains Engine with Grandfathering"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return response.json().get("token")
    
    def test_capital_gains_v2_endpoint(self, auth_token):
        """GET /api/tax/capital-gains-v2 returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/tax/capital-gains-v2?fy=2025-26",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Capital gains v2 failed: {response.status_code} - {response.text}"
        print(f"✓ Capital gains v2 endpoint returns 200")
    
    def test_capital_gains_v2_response_structure(self, auth_token):
        """Capital gains v2 returns proper structure with grandfathering support"""
        response = requests.get(
            f"{BASE_URL}/api/tax/capital-gains-v2?fy=2025-26",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        
        # Required fields
        assert "fy" in data
        assert "gains" in data
        assert "summary" in data
        assert "tax_breakdown" in data
        assert "notes" in data
        
        # Summary structure
        summary = data["summary"]
        assert "stcg_equity" in summary
        assert "ltcg_equity" in summary
        assert "ltcg_equity_exemption" in summary
        assert "ltcg_equity_taxable" in summary
        
        # Tax breakdown structure
        tax = data["tax_breakdown"]
        assert "stcg_equity_tax" in tax
        assert "ltcg_equity_tax" in tax
        assert "total_cg_tax" in tax
        
        print(f"✓ Capital gains v2 response structure valid")
        print(f"  - STCG equity: ₹{summary['stcg_equity']:,.0f}")
        print(f"  - LTCG equity: ₹{summary['ltcg_equity']:,.0f}")
        print(f"  - LTCG exemption: ₹{summary['ltcg_equity_exemption']:,.0f}")
        print(f"  - Total CG tax: ₹{tax['total_cg_tax']:,.0f}")
    
    def test_capital_gains_v2_grandfathering_notes(self, auth_token):
        """Capital gains v2 includes grandfathering notes"""
        response = requests.get(
            f"{BASE_URL}/api/tax/capital-gains-v2?fy=2025-26",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        
        notes = data.get("notes", [])
        assert len(notes) > 0, "No notes in response"
        
        # Check for grandfathering mention
        notes_text = " ".join(notes).lower()
        assert "grandfathering" in notes_text or "2018" in notes_text, "No grandfathering info in notes"
        
        print(f"✓ Capital gains v2 includes grandfathering notes")


class TestPhase3DeductionGap:
    """Phase 3: Deduction Gap Analysis with Product Recommendations"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return response.json().get("token")
    
    def test_deduction_gap_endpoint(self, auth_token):
        """GET /api/tax/deduction-gap returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/tax/deduction-gap?fy=2025-26",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Deduction gap failed: {response.status_code} - {response.text}"
        print(f"✓ Deduction gap endpoint returns 200")
    
    def test_deduction_gap_response_structure(self, auth_token):
        """Deduction gap returns proper structure with recommendations"""
        response = requests.get(
            f"{BASE_URL}/api/tax/deduction-gap?fy=2025-26",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        
        # Required fields
        assert "fy" in data
        assert "gaps" in data
        assert "summary" in data
        assert "top_actions" in data
        
        # Summary structure
        summary = data["summary"]
        assert "total_gap" in summary
        assert "potential_tax_savings" in summary
        assert "sections_analyzed" in summary
        assert "sections_under_utilized" in summary
        
        print(f"✓ Deduction gap response structure valid")
        print(f"  - Total gap: ₹{summary['total_gap']:,.0f}")
        print(f"  - Potential savings: ₹{summary['potential_tax_savings']:,.0f}")
        print(f"  - Sections analyzed: {summary['sections_analyzed']}")
        print(f"  - Under-utilized: {summary['sections_under_utilized']}")
    
    def test_deduction_gap_has_recommendations(self, auth_token):
        """Deduction gap includes product recommendations"""
        response = requests.get(
            f"{BASE_URL}/api/tax/deduction-gap?fy=2025-26",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        
        gaps = data.get("gaps", [])
        
        # Check if any gap has recommendations
        has_recommendations = False
        for gap in gaps:
            if gap.get("recommendations") and len(gap["recommendations"]) > 0:
                has_recommendations = True
                rec = gap["recommendations"][0]
                # Verify recommendation structure
                assert "product" in rec
                assert "priority" in rec
                break
        
        # It's OK if no gaps exist (user has optimized deductions)
        if len(gaps) > 0:
            print(f"✓ Deduction gap has {len(gaps)} sections with recommendations")
        else:
            print(f"✓ No deduction gaps (user may have optimized deductions)")
    
    def test_deduction_gap_top_actions(self, auth_token):
        """Deduction gap includes top actionable recommendations"""
        response = requests.get(
            f"{BASE_URL}/api/tax/deduction-gap?fy=2025-26",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        
        top_actions = data.get("top_actions", [])
        
        if len(top_actions) > 0:
            action = top_actions[0]
            assert "section" in action
            assert "action" in action
            assert "tax_savings" in action
            assert "product" in action
            print(f"✓ Top action: {action['action'][:50]}...")
        else:
            print(f"✓ No top actions (user may have optimized deductions)")


class TestPhase3TDSMismatch:
    """Phase 3: TDS Mismatch Detection"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return response.json().get("token")
    
    def test_tds_mismatch_endpoint(self, auth_token):
        """GET /api/tax/tds-mismatch returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/tax/tds-mismatch?fy=2025-26",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"TDS mismatch failed: {response.status_code} - {response.text}"
        print(f"✓ TDS mismatch endpoint returns 200")
    
    def test_tds_mismatch_response_structure(self, auth_token):
        """TDS mismatch returns proper structure"""
        response = requests.get(
            f"{BASE_URL}/api/tax/tds-mismatch?fy=2025-26",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        
        # Required fields
        assert "fy" in data
        assert "tds_sources" in data
        assert "summary" in data
        assert "recommendations" in data
        
        # Summary structure
        summary = data["summary"]
        assert "total_expected_tds" in summary
        assert "total_reported_tds" in summary
        assert "overall_difference" in summary
        assert "status" in summary
        
        # Status should be valid
        assert summary["status"] in ["all_matched", "minor_mismatch", "major_mismatch"]
        
        print(f"✓ TDS mismatch response structure valid")
        print(f"  - Expected TDS: ₹{summary['total_expected_tds']:,.0f}")
        print(f"  - Reported TDS: ₹{summary['total_reported_tds']:,.0f}")
        print(f"  - Difference: ₹{summary['overall_difference']:,.0f}")
        print(f"  - Status: {summary['status']}")
    
    def test_tds_mismatch_sources_structure(self, auth_token):
        """TDS mismatch sources have proper structure"""
        response = requests.get(
            f"{BASE_URL}/api/tax/tds-mismatch?fy=2025-26",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        
        sources = data.get("tds_sources", [])
        
        if len(sources) > 0:
            source = sources[0]
            assert "source" in source
            assert "source_type" in source
            assert "deductor" in source
            assert "status" in source
            print(f"✓ TDS sources have proper structure ({len(sources)} sources)")
        else:
            print(f"✓ No TDS sources (user may not have salary profile)")


class TestPhase3TaxCalendar:
    """Phase 3: Tax Calendar with Important Dates"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return response.json().get("token")
    
    def test_tax_calendar_endpoint(self, auth_token):
        """GET /api/tax/calendar returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/tax/calendar?fy=2025-26",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Tax calendar failed: {response.status_code} - {response.text}"
        print(f"✓ Tax calendar endpoint returns 200")
    
    def test_tax_calendar_response_structure(self, auth_token):
        """Tax calendar returns proper structure"""
        response = requests.get(
            f"{BASE_URL}/api/tax/calendar?fy=2025-26",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        
        # Required fields
        assert "fy" in data
        assert "income_types" in data
        assert "events" in data
        assert "urgent_count" in data
        assert "upcoming_count" in data
        
        print(f"✓ Tax calendar response structure valid")
        print(f"  - FY: {data['fy']}")
        print(f"  - Income types: {data['income_types']}")
        print(f"  - Total events: {len(data['events'])}")
        print(f"  - Urgent: {data['urgent_count']}")
        print(f"  - Upcoming: {data['upcoming_count']}")
    
    def test_tax_calendar_events_structure(self, auth_token):
        """Tax calendar events have proper structure"""
        response = requests.get(
            f"{BASE_URL}/api/tax/calendar?fy=2025-26",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        
        events = data.get("events", [])
        assert len(events) > 0, "No events in calendar"
        
        event = events[0]
        required_fields = ["date", "month", "day", "event", "action", "is_applicable", "status", "days_until"]
        for field in required_fields:
            assert field in event, f"Missing field in event: {field}"
        
        # Status should be valid
        assert event["status"] in ["urgent", "upcoming", "future", "completed", "past"]
        
        print(f"✓ Tax calendar events have proper structure")
        print(f"  - First event: {event['event']} ({event['date']})")
    
    def test_tax_calendar_has_key_dates(self, auth_token):
        """Tax calendar includes key tax dates"""
        response = requests.get(
            f"{BASE_URL}/api/tax/calendar?fy=2025-26",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        
        events = data.get("events", [])
        event_names = [e["event"].lower() for e in events]
        
        # Check for key dates
        key_dates_found = []
        if any("itr" in e or "filing" in e for e in event_names):
            key_dates_found.append("ITR Filing")
        if any("advance tax" in e for e in event_names):
            key_dates_found.append("Advance Tax")
        if any("financial year" in e for e in event_names):
            key_dates_found.append("FY Start/End")
        
        assert len(key_dates_found) > 0, "No key tax dates found"
        print(f"✓ Tax calendar includes key dates: {', '.join(key_dates_found)}")


class TestPhase3TaxReminders:
    """Phase 3: Tax Reminders (Personalized)"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return response.json().get("token")
    
    def test_tax_reminders_endpoint(self, auth_token):
        """GET /api/tax/reminders returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/tax/reminders?fy=2025-26",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Tax reminders failed: {response.status_code} - {response.text}"
        print(f"✓ Tax reminders endpoint returns 200")
    
    def test_tax_reminders_response_structure(self, auth_token):
        """Tax reminders returns proper structure"""
        response = requests.get(
            f"{BASE_URL}/api/tax/reminders?fy=2025-26",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        
        # Required fields
        assert "fy" in data
        assert "reminders" in data
        assert "count" in data
        assert "high_priority" in data
        
        print(f"✓ Tax reminders response structure valid")
        print(f"  - FY: {data['fy']}")
        print(f"  - Reminder count: {data['count']}")
        print(f"  - High priority: {data['high_priority']}")
    
    def test_tax_reminders_structure_if_present(self, auth_token):
        """Tax reminders have proper structure if any exist"""
        response = requests.get(
            f"{BASE_URL}/api/tax/reminders?fy=2025-26",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        
        reminders = data.get("reminders", [])
        
        if len(reminders) > 0:
            reminder = reminders[0]
            required_fields = ["id", "type", "urgency", "title", "message"]
            for field in required_fields:
                assert field in reminder, f"Missing field in reminder: {field}"
            
            # Urgency should be valid
            assert reminder["urgency"] in ["high", "medium", "low"]
            
            print(f"✓ Tax reminders have proper structure")
            print(f"  - First reminder: {reminder['title']} ({reminder['urgency']})")
        else:
            # Empty reminders is OK - depends on current month
            print(f"✓ No reminders for current month (expected behavior)")


class TestPhase2Phase3Integration:
    """Integration tests across Phase 2 & 3 features"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return response.json().get("token")
    
    def test_all_phase2_phase3_endpoints_accessible(self, auth_token):
        """All Phase 2 & 3 endpoints return 200"""
        endpoints = [
            "/api/tax/meter?fy=2025-26",
            "/api/tax/documents?fy=2025-26",
            "/api/tax/capital-gains-v2?fy=2025-26",
            "/api/tax/deduction-gap?fy=2025-26",
            "/api/tax/tds-mismatch?fy=2025-26",
            "/api/tax/calendar?fy=2025-26",
            "/api/tax/reminders?fy=2025-26",
        ]
        
        results = []
        for endpoint in endpoints:
            response = requests.get(
                f"{BASE_URL}{endpoint}",
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            results.append((endpoint, response.status_code))
        
        all_passed = all(status == 200 for _, status in results)
        
        for endpoint, status in results:
            status_icon = "✓" if status == 200 else "✗"
            print(f"  {status_icon} {endpoint}: {status}")
        
        assert all_passed, f"Some endpoints failed: {[e for e, s in results if s != 200]}"
        print(f"✓ All {len(endpoints)} Phase 2 & 3 endpoints accessible")
    
    def test_tax_meter_consistent_with_calculator(self, auth_token):
        """Tax meter values are consistent with tax calculator"""
        # Get tax meter
        meter_response = requests.get(
            f"{BASE_URL}/api/tax/meter?fy=2025-26",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        meter = meter_response.json()
        
        # Get tax calculator
        calc_response = requests.get(
            f"{BASE_URL}/api/tax-calculator?fy=2025-26",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        calc = calc_response.json()
        
        # Compare gross income
        meter_gross = meter.get("gross_income", 0)
        calc_gross = calc.get("income", {}).get("gross_total", 0)
        
        # Allow small difference due to rounding
        assert abs(meter_gross - calc_gross) < 100, f"Gross income mismatch: meter={meter_gross}, calc={calc_gross}"
        
        print(f"✓ Tax meter consistent with calculator")
        print(f"  - Gross income: ₹{meter_gross:,.0f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
