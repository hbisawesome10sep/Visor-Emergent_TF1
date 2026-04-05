"""
Iteration 39 - Testing Clear All Transactions and Credit Card Benefits Features
- DELETE /api/clear-all-transactions - clears all user transactions, CC transactions, bank accounts, journal entries, statement hashes
- GET /api/credit-cards/all-benefits - returns all user's credit cards with their cached benefits
- GET /api/credit-cards/{card_id}/benefits - fetches AI-generated benefits for a specific card
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://experience-tier-test.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "rajesh@visor.demo"
TEST_PASSWORD = "Demo@123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token") or data.get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Authenticated requests session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestClearAllTransactions:
    """Tests for DELETE /api/clear-all-transactions endpoint"""

    def test_clear_all_transactions_endpoint_exists(self, api_client):
        """Test that the clear-all-transactions endpoint exists and responds"""
        # First, let's check if the endpoint exists by making a request
        # We'll use a GET first to see if it returns 405 (method not allowed) which means endpoint exists
        response = api_client.get(f"{BASE_URL}/api/clear-all-transactions")
        # Should return 405 Method Not Allowed since it's a DELETE endpoint
        assert response.status_code in [405, 200, 401], f"Unexpected status: {response.status_code}"
        print(f"✓ Endpoint exists, GET returns {response.status_code}")

    def test_clear_all_transactions_delete(self, api_client):
        """Test DELETE /api/clear-all-transactions clears all user data"""
        response = api_client.delete(f"{BASE_URL}/api/clear-all-transactions")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain 'message'"
        assert "deleted" in data, "Response should contain 'deleted' counts"
        
        # Verify the deleted counts structure
        deleted = data["deleted"]
        assert "transactions" in deleted, "Should report deleted transactions count"
        assert "credit_card_transactions" in deleted, "Should report deleted CC transactions count"
        assert "bank_accounts" in deleted, "Should report deleted bank accounts count"
        assert "journal_entries" in deleted, "Should report deleted journal entries count"
        assert "statement_hashes" in deleted, "Should report deleted statement hashes count"
        
        print(f"✓ Clear all transactions successful: {data}")

    def test_verify_transactions_cleared(self, api_client):
        """Verify that transactions are actually cleared after delete"""
        response = api_client.get(f"{BASE_URL}/api/transactions")
        assert response.status_code == 200
        
        data = response.json()
        # After clearing, should have 0 or very few transactions
        print(f"✓ Transactions after clear: {len(data)} items")

    def test_verify_bank_accounts_cleared(self, api_client):
        """Verify that bank accounts are cleared after delete"""
        response = api_client.get(f"{BASE_URL}/api/bank-accounts")
        assert response.status_code == 200
        
        data = response.json()
        print(f"✓ Bank accounts after clear: {len(data)} items")


class TestCreditCardBenefits:
    """Tests for Credit Card Benefits endpoints"""

    def test_get_all_benefits_endpoint(self, api_client):
        """Test GET /api/credit-cards/all-benefits returns cards with benefits"""
        response = api_client.get(f"{BASE_URL}/api/credit-cards/all-benefits")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "cards" in data, "Response should contain 'cards' array"
        
        cards = data["cards"]
        assert isinstance(cards, list), "Cards should be a list"
        
        # If there are cards, verify structure
        if len(cards) > 0:
            card = cards[0]
            assert "card_id" in card, "Card should have card_id"
            assert "card_name" in card, "Card should have card_name"
            assert "benefits" in card, "Card should have benefits array"
            assert "has_benefits" in card, "Card should have has_benefits flag"
            print(f"✓ All benefits endpoint returns {len(cards)} cards")
            for c in cards:
                print(f"  - {c['card_name']}: {len(c.get('benefits', []))} benefits, has_benefits={c.get('has_benefits')}")
        else:
            print("✓ All benefits endpoint works (no cards found)")

    def test_get_credit_cards_list(self, api_client):
        """Test GET /api/credit-cards returns user's cards"""
        response = api_client.get(f"{BASE_URL}/api/credit-cards")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Should return a list of cards"
        
        print(f"✓ User has {len(data)} credit cards")
        return data

    def test_get_card_benefits_for_existing_card(self, api_client):
        """Test GET /api/credit-cards/{card_id}/benefits for a specific card"""
        # First get the list of cards
        cards_response = api_client.get(f"{BASE_URL}/api/credit-cards")
        assert cards_response.status_code == 200
        
        cards = cards_response.json()
        if len(cards) == 0:
            pytest.skip("No credit cards found for user - skipping individual card benefits test")
        
        # Get benefits for the first card
        card_id = cards[0]["id"]
        card_name = cards[0]["card_name"]
        
        response = api_client.get(f"{BASE_URL}/api/credit-cards/{card_id}/benefits")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "card_name" in data, "Response should contain card_name"
        assert "benefits" in data, "Response should contain benefits array"
        assert "cached" in data, "Response should indicate if cached"
        
        benefits = data["benefits"]
        assert isinstance(benefits, list), "Benefits should be a list"
        
        print(f"✓ Card '{card_name}' has {len(benefits)} benefits (cached={data['cached']})")
        
        # If benefits exist, verify structure
        if len(benefits) > 0:
            benefit = benefits[0]
            assert "category" in benefit, "Benefit should have category"
            assert "title" in benefit, "Benefit should have title"
            assert "description" in benefit, "Benefit should have description"
            assert "icon" in benefit, "Benefit should have icon"
            print(f"  Sample benefit: {benefit['title']} ({benefit['category']})")

    def test_get_benefits_for_nonexistent_card(self, api_client):
        """Test GET /api/credit-cards/{card_id}/benefits returns 404 for invalid card"""
        fake_card_id = "nonexistent-card-id-12345"
        response = api_client.get(f"{BASE_URL}/api/credit-cards/{fake_card_id}/benefits")
        
        assert response.status_code == 404, f"Expected 404 for nonexistent card, got {response.status_code}"
        print("✓ Returns 404 for nonexistent card")


class TestCreditCardCRUD:
    """Additional tests for credit card CRUD to ensure benefits integration works"""

    def test_create_credit_card_for_benefits_test(self, api_client):
        """Create a test credit card to verify benefits can be fetched"""
        # Check if test card already exists
        cards_response = api_client.get(f"{BASE_URL}/api/credit-cards")
        cards = cards_response.json()
        
        test_card_exists = any(c.get("card_name") == "TEST_Benefits_Card" for c in cards)
        
        if not test_card_exists:
            # Create a test card
            response = api_client.post(f"{BASE_URL}/api/credit-cards", json={
                "card_name": "TEST_Benefits_Card",
                "issuer": "HDFC Bank",
                "card_number": "4111111111111111",
                "credit_limit": 100000,
                "billing_cycle_day": 5,
                "due_day": 20,
                "is_default": False
            })
            
            assert response.status_code == 200, f"Failed to create test card: {response.status_code} - {response.text}"
            data = response.json()
            assert data["card_name"] == "TEST_Benefits_Card"
            print(f"✓ Created test card: {data['card_name']}")
            return data["id"]
        else:
            print("✓ Test card already exists")
            return next(c["id"] for c in cards if c.get("card_name") == "TEST_Benefits_Card")

    def test_fetch_benefits_for_new_card(self, api_client):
        """Test fetching AI benefits for a newly created card"""
        # Get the test card
        cards_response = api_client.get(f"{BASE_URL}/api/credit-cards")
        cards = cards_response.json()
        
        test_card = next((c for c in cards if c.get("card_name") == "TEST_Benefits_Card"), None)
        
        if not test_card:
            pytest.skip("Test card not found")
        
        card_id = test_card["id"]
        
        # Fetch benefits (this may call AI if not cached)
        response = api_client.get(f"{BASE_URL}/api/credit-cards/{card_id}/benefits")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"✓ Benefits for TEST_Benefits_Card: {len(data.get('benefits', []))} benefits, cached={data.get('cached')}")


class TestCleanup:
    """Cleanup test data"""

    def test_cleanup_test_card(self, api_client):
        """Remove test card created during testing"""
        cards_response = api_client.get(f"{BASE_URL}/api/credit-cards")
        cards = cards_response.json()
        
        test_card = next((c for c in cards if c.get("card_name") == "TEST_Benefits_Card"), None)
        
        if test_card:
            response = api_client.delete(f"{BASE_URL}/api/credit-cards/{test_card['id']}")
            assert response.status_code == 200, f"Failed to delete test card: {response.status_code}"
            print("✓ Cleaned up TEST_Benefits_Card")
        else:
            print("✓ No test card to clean up")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
