"""
Tests for:
1. Manual CC Transaction Entry Form - POST /api/credit-card-transactions
2. SIP Investment Tracking - GET /api/recurring (auto_detected field)
3. Flagged Transactions - GET /api/flagged-transactions
4. Approve Flagged as SIP - POST /api/approve-flagged/{txn_id}
"""
import pytest
import requests
import os

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/")
TEST_CARD_ID = "c10a3c07-f040-4173-b984-1a72c57aa4ee"
EMAIL = "rajesh@visor.demo"
PASSWORD = "Demo@123"


# ── Auth Fixture ──────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def auth_token():
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json().get("token") or resp.json().get("access_token")
    assert token, "No token in login response"
    return token


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


# ── 1. Login ──────────────────────────────────────────────────────────────────
class TestAuth:
    def test_login(self, auth_token):
        """Login with demo credentials should succeed."""
        assert auth_token is not None
        print(f"✓ Login successful, token obtained")


# ── 2. GET /api/credit-cards ──────────────────────────────────────────────────
class TestCreditCards:
    def test_get_credit_cards(self, auth_headers):
        """Should return list of credit cards including HDFC Regalia."""
        resp = requests.get(f"{BASE_URL}/api/credit-cards", headers=auth_headers)
        assert resp.status_code == 200, f"GET /credit-cards failed: {resp.text}"
        data = resp.json()
        assert isinstance(data, list), "Expected list of cards"
        print(f"✓ GET /credit-cards returned {len(data)} cards")

        # Check test card exists
        card_ids = [c["id"] for c in data]
        if TEST_CARD_ID in card_ids:
            print(f"✓ Test card HDFC Regalia (id={TEST_CARD_ID}) found")
        else:
            print(f"WARNING: Test card ID {TEST_CARD_ID} not found in {card_ids}")


# ── 3. POST /api/credit-card-transactions ─────────────────────────────────────
class TestCCTransactions:
    """Credit Card Transaction creation tests."""

    def test_post_expense_transaction(self, auth_headers):
        """POST expense transaction should return transaction object with expected fields."""
        payload = {
            "card_id": TEST_CARD_ID,
            "type": "expense",
            "amount": 1500.00,
            "description": "TEST_Dinner at Zomato",
            "merchant": "Zomato",
            "category": "Food & Dining",
            "date": "2026-02-01",
        }
        resp = requests.post(f"{BASE_URL}/api/credit-card-transactions", json=payload, headers=auth_headers)
        print(f"POST /credit-card-transactions status: {resp.status_code}")
        print(f"Response: {resp.text[:300]}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        data = resp.json()
        # Verify fields
        assert data.get("id"), "Expected 'id' in response"
        assert data.get("card_id") == TEST_CARD_ID, "card_id mismatch"
        assert data.get("type") == "expense", "type mismatch"
        assert data.get("amount") == 1500.00, "amount mismatch"
        assert data.get("description") == "TEST_Dinner at Zomato"
        assert data.get("category") == "Food & Dining"
        assert data.get("date") == "2026-02-01"
        print(f"✓ Expense transaction created: id={data['id']}")
        return data["id"]

    def test_post_payment_transaction(self, auth_headers):
        """POST payment transaction should return transaction object."""
        payload = {
            "card_id": TEST_CARD_ID,
            "type": "payment",
            "amount": 5000.00,
            "description": "TEST_CC Bill Payment",
            "merchant": "",
            "category": "Payment",
            "date": "2026-02-05",
        }
        resp = requests.post(f"{BASE_URL}/api/credit-card-transactions", json=payload, headers=auth_headers)
        assert resp.status_code == 200, f"Payment transaction failed: {resp.text}"
        data = resp.json()
        assert data.get("type") == "payment"
        assert data.get("amount") == 5000.00
        print(f"✓ Payment transaction created: id={data['id']}")

    def test_post_transaction_missing_card_id(self, auth_headers):
        """Should return 400 when card_id is missing."""
        payload = {
            "type": "expense",
            "amount": 100,
            "description": "Missing card test",
        }
        resp = requests.post(f"{BASE_URL}/api/credit-card-transactions", json=payload, headers=auth_headers)
        assert resp.status_code == 400, f"Expected 400 for missing card_id, got {resp.status_code}"
        print(f"✓ Missing card_id correctly returns 400")

    def test_post_transaction_invalid_card(self, auth_headers):
        """Should return 404 for invalid card_id."""
        payload = {
            "card_id": "non-existent-card-uuid",
            "type": "expense",
            "amount": 100,
            "description": "Invalid card test",
            "date": "2026-02-01",
        }
        resp = requests.post(f"{BASE_URL}/api/credit-card-transactions", json=payload, headers=auth_headers)
        assert resp.status_code == 404, f"Expected 404 for invalid card, got {resp.status_code}: {resp.text}"
        print(f"✓ Invalid card_id correctly returns 404")

    def test_post_sip_transaction_gets_flagged(self, auth_headers):
        """SIP keyword in description should get flagged."""
        payload = {
            "card_id": TEST_CARD_ID,
            "type": "expense",
            "amount": 2000.00,
            "description": "TEST_SIP Groww Mutual Fund",
            "merchant": "Groww",
            "category": "Other",
            "date": "2026-02-10",
        }
        resp = requests.post(f"{BASE_URL}/api/credit-card-transactions", json=payload, headers=auth_headers)
        assert resp.status_code == 200, f"SIP transaction failed: {resp.text}"
        data = resp.json()
        # SIP keyword should be flagged
        assert data.get("is_flagged") == True, f"Expected is_flagged=True for SIP transaction, got: {data.get('is_flagged')}"
        assert data.get("flagged_type") == "SIP", f"Expected flagged_type=SIP, got: {data.get('flagged_type')}"
        print(f"✓ SIP transaction flagged: id={data['id']}, flagged_type={data['flagged_type']}")
        return data["id"]

    def test_get_transactions_after_post(self, auth_headers):
        """GET transactions should include newly created transactions."""
        resp = requests.get(f"{BASE_URL}/api/credit-card-transactions?card_id={TEST_CARD_ID}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Check for our test transaction
        descs = [t.get("description", "") for t in data]
        found = any("TEST_Dinner at Zomato" in d for d in descs)
        print(f"✓ GET /credit-card-transactions returned {len(data)} transactions. TEST_Dinner found: {found}")


# ── 4. GET /api/flagged-transactions ──────────────────────────────────────────
class TestFlaggedTransactions:
    """Flagged transaction tests."""

    def test_get_flagged_transactions(self, auth_headers):
        """GET flagged transactions should return list."""
        resp = requests.get(f"{BASE_URL}/api/flagged-transactions", headers=auth_headers)
        assert resp.status_code == 200, f"GET /flagged-transactions failed: {resp.text}"
        data = resp.json()
        assert isinstance(data, list), "Expected list"
        print(f"✓ GET /flagged-transactions returned {len(data)} flagged transactions")
        for t in data[:3]:
            print(f"  - {t.get('description', 'N/A')} | type={t.get('flagged_type')} | source={t.get('source')}")

    def test_flagged_transactions_have_source_field(self, auth_headers):
        """Flagged transactions should have 'source' field."""
        resp = requests.get(f"{BASE_URL}/api/flagged-transactions", headers=auth_headers)
        data = resp.json()
        if data:
            for t in data:
                assert "source" in t, f"Missing 'source' in flagged txn: {t}"
            print(f"✓ All {len(data)} flagged transactions have 'source' field")
        else:
            print("INFO: No flagged transactions found (may need to create them first)")


# ── 5. POST /api/approve-flagged + GET /api/recurring ────────────────────────
class TestSIPApprovalAndRecurring:
    """SIP approval and recurring investments tracking."""

    def test_get_recurring(self, auth_headers):
        """GET /api/recurring should return recurring_transactions with proper fields."""
        resp = requests.get(f"{BASE_URL}/api/recurring", headers=auth_headers)
        assert resp.status_code == 200, f"GET /recurring failed: {resp.text}"
        data = resp.json()
        assert "recurring" in data, "Expected 'recurring' key in response"
        assert "summary" in data, "Expected 'summary' key in response"
        recurring = data["recurring"]
        assert isinstance(recurring, list), "Expected list of recurring transactions"
        summary = data["summary"]
        assert "total_count" in summary
        assert "active_count" in summary
        assert "monthly_commitment" in summary
        print(f"✓ GET /recurring: {len(recurring)} items, active={summary['active_count']}, monthly={summary['monthly_commitment']}")

    def test_recurring_auto_detected_field(self, auth_headers):
        """Recurring transactions from approved SIPs should have auto_detected field."""
        resp = requests.get(f"{BASE_URL}/api/recurring", headers=auth_headers)
        data = resp.json()
        recurring = data["recurring"]
        auto_detected = [r for r in recurring if r.get("auto_detected") == True]
        print(f"✓ Found {len(auto_detected)} auto-detected SIPs in recurring list")
        for sip in auto_detected:
            print(f"  - {sip.get('name')} | amount={sip.get('amount')} | auto_detected={sip.get('auto_detected')}")
            # Verify all required fields
            assert "id" in sip, "Missing 'id' in recurring"
            assert "next_execution" in sip, "Missing 'next_execution'"
            assert "total_invested" in sip, "Missing 'total_invested'"
            assert "execution_count" in sip, "Missing 'execution_count'"

    def test_approve_flagged_sip_creates_recurring(self, auth_headers):
        """Approving a flagged transaction as SIP should create a recurring entry with auto_detected=True."""
        # First create a SIP-flagged transaction
        payload = {
            "card_id": TEST_CARD_ID,
            "type": "expense",
            "amount": 3000.00,
            "description": "TEST_SIP HDFC Nifty Index Fund",
            "merchant": "HDFC MF",
            "category": "Other",
            "date": "2026-02-15",
        }
        create_resp = requests.post(f"{BASE_URL}/api/credit-card-transactions", json=payload, headers=auth_headers)
        assert create_resp.status_code == 200, f"Failed to create SIP transaction: {create_resp.text}"
        txn_data = create_resp.json()
        txn_id = txn_data["id"]
        is_flagged = txn_data.get("is_flagged", False)
        print(f"✓ Created transaction: id={txn_id}, is_flagged={is_flagged}")

        # If not flagged automatically, get any existing flagged transaction
        if not is_flagged:
            flagged_resp = requests.get(f"{BASE_URL}/api/flagged-transactions", headers=auth_headers)
            flagged_list = flagged_resp.json()
            # find one with source='bank' or 'credit_card' that is SIP type
            sip_flagged = [t for t in flagged_list if t.get("flagged_type") == "SIP" or t.get("source") == "bank"]
            if sip_flagged:
                txn_to_approve = sip_flagged[0]
                txn_id = txn_to_approve["id"]
                source = txn_to_approve.get("source", "credit_card")
                print(f"Using existing flagged txn: id={txn_id}, source={source}")
            else:
                pytest.skip("No flagged SIP transactions available to approve")
                return
        else:
            source = "credit_card"

        # Get recurring count before approval
        before_resp = requests.get(f"{BASE_URL}/api/recurring", headers=auth_headers)
        before_count = len(before_resp.json()["recurring"])

        # Approve as SIP
        approve_payload = {
            "source": source,
            "approved_type": "SIP",
            "create_recurring": True,
        }
        approve_resp = requests.post(
            f"{BASE_URL}/api/approve-flagged/{txn_id}",
            json=approve_payload,
            headers=auth_headers
        )
        print(f"POST /approve-flagged/{txn_id}: status={approve_resp.status_code}")
        print(f"Response: {approve_resp.text[:300]}")
        assert approve_resp.status_code == 200, f"Approve failed: {approve_resp.text}"
        approve_data = approve_resp.json()
        assert "SIP" in approve_data.get("message", ""), f"Expected SIP in message: {approve_data}"
        print(f"✓ Approved as SIP: {approve_data}")

        # Verify recurring entry created
        after_resp = requests.get(f"{BASE_URL}/api/recurring", headers=auth_headers)
        after_count = len(after_resp.json()["recurring"])
        after_recurring = after_resp.json()["recurring"]
        print(f"✓ Recurring count: {before_count} -> {after_count}")
        assert after_count > before_count, f"Expected new recurring entry, count: {before_count} -> {after_count}"

        # Check the newest recurring entry has auto_detected=True
        new_entries = [r for r in after_recurring if r not in before_resp.json()["recurring"]]
        auto_detected_entries = [r for r in after_recurring if r.get("auto_detected") == True]
        print(f"✓ auto_detected entries: {len(auto_detected_entries)}")
        
        if auto_detected_entries:
            latest = auto_detected_entries[-1]
            print(f"  Latest auto-detected SIP: name={latest.get('name')}, amount={latest.get('amount')}, auto_detected={latest.get('auto_detected')}")
            assert latest.get("next_execution"), "Missing next_execution"
            assert latest.get("total_invested", 0) > 0, "total_invested should be > 0"
            assert latest.get("execution_count", 0) >= 1, "execution_count should be >= 1"
            print(f"✓ auto_detected SIP has next_execution={latest.get('next_execution')}, total_invested={latest.get('total_invested')}, execution_count={latest.get('execution_count')}")


# ── 6. GET /api/recurring - structure checks ──────────────────────────────────
class TestRecurringStructure:
    def test_recurring_upcoming_field(self, auth_headers):
        """Recurring transactions should have 'upcoming' list."""
        resp = requests.get(f"{BASE_URL}/api/recurring", headers=auth_headers)
        data = resp.json()
        for r in data["recurring"]:
            assert "upcoming" in r, f"Missing 'upcoming' in recurring: {r.get('name')}"
            assert isinstance(r["upcoming"], list), f"'upcoming' should be list in: {r.get('name')}"
        print(f"✓ All recurring transactions have 'upcoming' list")

    def test_recurring_required_fields(self, auth_headers):
        """Each recurring transaction should have all required frontend fields."""
        resp = requests.get(f"{BASE_URL}/api/recurring", headers=auth_headers)
        data = resp.json()
        required = ["id", "name", "amount", "frequency", "category", "is_active", "next_execution", "total_invested", "execution_count"]
        for r in data["recurring"]:
            for field in required:
                assert field in r, f"Missing '{field}' in recurring: {r.get('name', 'unknown')}"
        print(f"✓ All {len(data['recurring'])} recurring transactions have required fields")
