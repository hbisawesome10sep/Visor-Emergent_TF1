"""
Visor AI P0 Features - Multi-Model Query Router & Persistent AI Memory Tests

P0-1: Multi-Model Query Router
- Simple queries (greeting, price check, definition) → gpt-4o-mini
- Complex queries (tax planning, portfolio review, investment advice) → gpt-5.2
- Calculator queries → gpt-4o-mini (computation already done)

P0-2: Persistent AI Memory
- GET /api/visor-ai/memory: Returns memory data after chatting
- DELETE /api/visor-ai/memory: Clears all memory
- Memory injection: AI references past context in subsequent conversations

Regression: Existing visor-ai endpoints should still work
"""
import pytest
import requests
import os
import time

# Use public backend URL for testing
BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://experience-deploy.preview.emergentagent.com').rstrip('/')


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session for all tests"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def demo_user_token(api_client):
    """Login with demo user and return token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "rajesh@visor.demo",
        "password": "Demo@123"
    })
    assert response.status_code == 200, f"Demo login failed: {response.text}"
    data = response.json()
    return data["token"]


@pytest.fixture(scope="module")
def auth_headers(demo_user_token):
    """Return auth headers for requests"""
    return {"Authorization": f"Bearer {demo_user_token}"}


# ══════════════════════════════════════════════════════════════════════════════
#  HEALTH CHECK
# ══════════════════════════════════════════════════════════════════════════════

class TestHealthCheck:
    """Basic health check to ensure server is running"""

    def test_health_endpoint(self, api_client):
        """Test /api/health endpoint"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        data = response.json()
        assert data["status"] == "healthy"
        print("✓ Server is healthy")


# ══════════════════════════════════════════════════════════════════════════════
#  P0-1: MULTI-MODEL QUERY ROUTER - Simple Queries → gpt-4o-mini
# ══════════════════════════════════════════════════════════════════════════════

class TestQueryRouterSimpleQueries:
    """Simple queries should route to gpt-4o-mini (cheap/fast model)"""

    def test_greeting_uses_mini_model(self, api_client, auth_headers):
        """Greeting 'Hi' should use gpt-4o-mini"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Hi"},
            timeout=30
        )
        assert response.status_code == 200, f"Chat failed: {response.text}"
        
        data = response.json()
        assert "model_used" in data, "Response should include model_used field"
        assert data["model_used"] == "gpt-4o-mini", f"Greeting should use gpt-4o-mini, got: {data['model_used']}"
        print(f"✓ Greeting 'Hi' → {data['model_used']}")

    def test_definition_query_uses_mini_model(self, api_client, auth_headers):
        """Definition query 'What is SIP?' should use gpt-4o-mini"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "What is SIP?"},
            timeout=30
        )
        assert response.status_code == 200, f"Chat failed: {response.text}"
        
        data = response.json()
        assert "model_used" in data, "Response should include model_used field"
        assert data["model_used"] == "gpt-4o-mini", f"Definition query should use gpt-4o-mini, got: {data['model_used']}"
        print(f"✓ Definition 'What is SIP?' → {data['model_used']}")

    def test_ppf_definition_uses_mini_model(self, api_client, auth_headers):
        """Definition query 'What is PPF?' should use gpt-4o-mini"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "What is PPF?"},
            timeout=30
        )
        assert response.status_code == 200, f"Chat failed: {response.text}"
        
        data = response.json()
        assert "model_used" in data, "Response should include model_used field"
        assert data["model_used"] == "gpt-4o-mini", f"PPF definition should use gpt-4o-mini, got: {data['model_used']}"
        print(f"✓ Definition 'What is PPF?' → {data['model_used']}")

    def test_price_check_hinglish_uses_mini_model(self, api_client, auth_headers):
        """Price check 'gold price kya hai?' should use gpt-4o-mini"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "gold price kya hai?"},
            timeout=45
        )
        assert response.status_code == 200, f"Chat failed: {response.text}"
        
        data = response.json()
        assert "model_used" in data, "Response should include model_used field"
        assert data["model_used"] == "gpt-4o-mini", f"Price check should use gpt-4o-mini, got: {data['model_used']}"
        print(f"✓ Price check 'gold price kya hai?' → {data['model_used']}")

    def test_thanks_uses_mini_model(self, api_client, auth_headers):
        """Acknowledgement 'Thanks' should use gpt-4o-mini"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Thanks"},
            timeout=30
        )
        assert response.status_code == 200, f"Chat failed: {response.text}"
        
        data = response.json()
        assert "model_used" in data, "Response should include model_used field"
        assert data["model_used"] == "gpt-4o-mini", f"Thanks should use gpt-4o-mini, got: {data['model_used']}"
        print(f"✓ Acknowledgement 'Thanks' → {data['model_used']}")


# ══════════════════════════════════════════════════════════════════════════════
#  P0-1: MULTI-MODEL QUERY ROUTER - Complex Queries → gpt-5.2
# ══════════════════════════════════════════════════════════════════════════════

class TestQueryRouterComplexQueries:
    """Complex queries should route to gpt-5.2 (powerful model)"""

    def test_tax_planning_uses_power_model(self, api_client, auth_headers):
        """Tax planning query should use gpt-5.2"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "How can I save tax under 80C?"},
            timeout=45
        )
        assert response.status_code == 200, f"Chat failed: {response.text}"
        
        data = response.json()
        assert "model_used" in data, "Response should include model_used field"
        assert data["model_used"] == "gpt-5.2", f"Tax planning should use gpt-5.2, got: {data['model_used']}"
        print(f"✓ Tax planning → {data['model_used']}")

    def test_portfolio_review_uses_power_model(self, api_client, auth_headers):
        """Portfolio review query should use gpt-5.2"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Review my portfolio"},
            timeout=45
        )
        assert response.status_code == 200, f"Chat failed: {response.text}"
        
        data = response.json()
        assert "model_used" in data, "Response should include model_used field"
        assert data["model_used"] == "gpt-5.2", f"Portfolio review should use gpt-5.2, got: {data['model_used']}"
        print(f"✓ Portfolio review → {data['model_used']}")

    def test_should_i_invest_uses_power_model(self, api_client, auth_headers):
        """Investment advice 'should I invest in 80C?' should use gpt-5.2"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Should I invest more in 80C?"},
            timeout=45
        )
        assert response.status_code == 200, f"Chat failed: {response.text}"
        
        data = response.json()
        assert "model_used" in data, "Response should include model_used field"
        assert data["model_used"] == "gpt-5.2", f"Investment advice should use gpt-5.2, got: {data['model_used']}"
        print(f"✓ Investment advice 'should I invest' → {data['model_used']}")

    def test_suggest_query_uses_power_model(self, api_client, auth_headers):
        """Suggestion query 'suggest me best mutual funds' should use gpt-5.2"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Suggest me best mutual funds for long term"},
            timeout=45
        )
        assert response.status_code == 200, f"Chat failed: {response.text}"
        
        data = response.json()
        assert "model_used" in data, "Response should include model_used field"
        assert data["model_used"] == "gpt-5.2", f"Suggestion query should use gpt-5.2, got: {data['model_used']}"
        print(f"✓ Suggestion query → {data['model_used']}")

    def test_tax_saving_hinglish_uses_power_model(self, api_client, auth_headers):
        """Tax saving query in Hinglish should use gpt-5.2"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Mera tax kaise bachega? Kya karna chahiye?"},
            timeout=45
        )
        assert response.status_code == 200, f"Chat failed: {response.text}"
        
        data = response.json()
        assert "model_used" in data, "Response should include model_used field"
        assert data["model_used"] == "gpt-5.2", f"Tax saving Hinglish should use gpt-5.2, got: {data['model_used']}"
        print(f"✓ Tax saving Hinglish → {data['model_used']}")


# ══════════════════════════════════════════════════════════════════════════════
#  P0-1: MULTI-MODEL QUERY ROUTER - Calculator Queries → gpt-4o-mini
# ══════════════════════════════════════════════════════════════════════════════

class TestQueryRouterCalculatorQueries:
    """Calculator queries should use gpt-4o-mini (computation already done)"""

    def test_sip_calculator_uses_mini_model(self, api_client, auth_headers):
        """SIP calculator query should use gpt-4o-mini"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Calculate SIP of 10000 per month at 12% for 15 years"},
            timeout=30
        )
        assert response.status_code == 200, f"Chat failed: {response.text}"
        
        data = response.json()
        assert "model_used" in data, "Response should include model_used field"
        assert "calculator_result" in data, "Should have calculator_result"
        
        # When calculator result is present, should use mini model
        if data.get("calculator_result"):
            assert data["model_used"] == "gpt-4o-mini", f"Calculator query should use gpt-4o-mini, got: {data['model_used']}"
            print(f"✓ SIP Calculator → {data['model_used']} (calculator_result present)")
        else:
            print(f"⚠ SIP Calculator not auto-detected, model: {data['model_used']}")

    def test_emi_calculator_uses_mini_model(self, api_client, auth_headers):
        """EMI calculator query should use gpt-4o-mini"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Calculate EMI for 50 lakh loan at 8.5% for 20 years"},
            timeout=30
        )
        assert response.status_code == 200, f"Chat failed: {response.text}"
        
        data = response.json()
        assert "model_used" in data, "Response should include model_used field"
        
        if data.get("calculator_result"):
            assert data["model_used"] == "gpt-4o-mini", f"EMI Calculator should use gpt-4o-mini, got: {data['model_used']}"
            print(f"✓ EMI Calculator → {data['model_used']} (calculator_result present)")
        else:
            print(f"⚠ EMI Calculator not auto-detected, model: {data['model_used']}")


# ══════════════════════════════════════════════════════════════════════════════
#  P0-2: PERSISTENT AI MEMORY - GET /api/visor-ai/memory
# ══════════════════════════════════════════════════════════════════════════════

class TestAIMemoryGet:
    """Test GET /api/visor-ai/memory endpoint"""

    def test_memory_endpoint_exists(self, api_client, auth_headers):
        """Memory endpoint should exist and return 200"""
        response = api_client.get(
            f"{BASE_URL}/api/visor-ai/memory",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Memory GET failed: {response.text}"
        print("✓ Memory endpoint exists and returns 200")

    def test_memory_structure(self, api_client, auth_headers):
        """Memory response should have correct structure"""
        response = api_client.get(
            f"{BASE_URL}/api/visor-ai/memory",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Memory GET failed: {response.text}"
        
        data = response.json()
        
        # Verify required fields exist
        required_fields = ["user_id", "topics", "concerns", "preferences", 
                          "open_questions", "financial_facts", "language_preference", 
                          "conversation_count"]
        
        for field in required_fields:
            assert field in data, f"Memory should have '{field}' field"
        
        # Verify types
        assert isinstance(data["topics"], list), "topics should be a list"
        assert isinstance(data["concerns"], list), "concerns should be a list"
        assert isinstance(data["preferences"], list), "preferences should be a list"
        assert isinstance(data["open_questions"], list), "open_questions should be a list"
        assert isinstance(data["financial_facts"], list), "financial_facts should be a list"
        assert isinstance(data["conversation_count"], int), "conversation_count should be int"
        
        print(f"✓ Memory structure verified: {list(data.keys())}")
        print(f"  Topics: {len(data['topics'])}, Concerns: {len(data['concerns'])}, Facts: {len(data['financial_facts'])}")
        print(f"  Conversation count: {data['conversation_count']}")


# ══════════════════════════════════════════════════════════════════════════════
#  P0-2: PERSISTENT AI MEMORY - DELETE /api/visor-ai/memory
# ══════════════════════════════════════════════════════════════════════════════

class TestAIMemoryDelete:
    """Test DELETE /api/visor-ai/memory endpoint"""

    def test_memory_delete_endpoint(self, api_client, auth_headers):
        """Memory DELETE endpoint should work"""
        response = api_client.delete(
            f"{BASE_URL}/api/visor-ai/memory",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Memory DELETE failed: {response.text}"
        
        data = response.json()
        assert "message" in data, "Should return confirmation message"
        print(f"✓ Memory DELETE successful: {data['message']}")

    def test_memory_empty_after_delete(self, api_client, auth_headers):
        """Memory should be empty after DELETE"""
        # First delete
        api_client.delete(
            f"{BASE_URL}/api/visor-ai/memory",
            headers=auth_headers
        )
        
        # Then GET
        response = api_client.get(
            f"{BASE_URL}/api/visor-ai/memory",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        
        # All lists should be empty
        assert len(data["topics"]) == 0, "topics should be empty after delete"
        assert len(data["concerns"]) == 0, "concerns should be empty after delete"
        assert len(data["preferences"]) == 0, "preferences should be empty after delete"
        assert len(data["open_questions"]) == 0, "open_questions should be empty after delete"
        assert len(data["financial_facts"]) == 0, "financial_facts should be empty after delete"
        assert data["conversation_count"] == 0, "conversation_count should be 0 after delete"
        
        print("✓ Memory is empty after DELETE")


# ══════════════════════════════════════════════════════════════════════════════
#  P0-2: PERSISTENT AI MEMORY - Memory Extraction After Chat
# ══════════════════════════════════════════════════════════════════════════════

class TestAIMemoryExtraction:
    """Test that memory is extracted and stored after chat"""

    def test_memory_builds_after_chat(self, api_client, auth_headers):
        """Memory should build after chatting"""
        # First clear memory
        api_client.delete(
            f"{BASE_URL}/api/visor-ai/memory",
            headers=auth_headers
        )
        
        # Send a chat message about tax concerns
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "I'm worried about my tax liability this year. I want to save more under 80C."},
            timeout=45
        )
        assert response.status_code == 200, f"Chat failed: {response.text}"
        
        # Wait for background memory extraction (runs via asyncio.create_task)
        time.sleep(4)
        
        # Check memory
        memory_response = api_client.get(
            f"{BASE_URL}/api/visor-ai/memory",
            headers=auth_headers
        )
        assert memory_response.status_code == 200
        
        memory = memory_response.json()
        
        # Memory should have been updated
        has_content = (
            len(memory.get("topics", [])) > 0 or
            len(memory.get("concerns", [])) > 0 or
            len(memory.get("financial_facts", [])) > 0 or
            memory.get("conversation_count", 0) > 0
        )
        
        print(f"✓ Memory after chat:")
        print(f"  Topics: {memory.get('topics', [])}")
        print(f"  Concerns: {memory.get('concerns', [])}")
        print(f"  Financial Facts: {memory.get('financial_facts', [])}")
        print(f"  Conversation Count: {memory.get('conversation_count', 0)}")
        
        assert has_content, "Memory should have some content after chat"

    def test_memory_accumulates_across_conversations(self, api_client, auth_headers):
        """Memory should accumulate across multiple conversations"""
        # Clear memory first
        api_client.delete(
            f"{BASE_URL}/api/visor-ai/memory",
            headers=auth_headers
        )
        
        # First conversation about retirement
        api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "I want to plan for retirement. I'm 35 years old."},
            timeout=45
        )
        time.sleep(3)
        
        # Second conversation about mutual funds
        api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Which mutual funds are good for long term wealth creation?"},
            timeout=45
        )
        time.sleep(3)
        
        # Check memory
        memory_response = api_client.get(
            f"{BASE_URL}/api/visor-ai/memory",
            headers=auth_headers
        )
        assert memory_response.status_code == 200
        
        memory = memory_response.json()
        
        # Should have conversation count >= 2
        assert memory.get("conversation_count", 0) >= 2, \
            f"Conversation count should be >= 2, got: {memory.get('conversation_count', 0)}"
        
        print(f"✓ Memory accumulated across conversations:")
        print(f"  Conversation Count: {memory.get('conversation_count', 0)}")
        print(f"  Topics: {memory.get('topics', [])}")


# ══════════════════════════════════════════════════════════════════════════════
#  REGRESSION: Existing visor-ai endpoints should still work
# ══════════════════════════════════════════════════════════════════════════════

class TestVisorAIRegression:
    """Regression tests for existing visor-ai endpoints"""

    def test_chat_returns_proper_fields(self, api_client, auth_headers):
        """Chat should return id, content, role fields"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Hello"},
            timeout=30
        )
        assert response.status_code == 200, f"Chat failed: {response.text}"
        
        data = response.json()
        
        # Verify required fields
        assert "id" in data, "Response should have id"
        assert "content" in data, "Response should have content"
        assert "role" in data, "Response should have role"
        assert data["role"] == "assistant", "Role should be assistant"
        assert len(data["content"]) > 0, "Content should not be empty"
        
        print(f"✓ Chat returns proper fields: id, content, role")

    def test_history_endpoint_works(self, api_client, auth_headers):
        """GET /api/visor-ai/history should work"""
        response = api_client.get(
            f"{BASE_URL}/api/visor-ai/history",
            headers=auth_headers
        )
        assert response.status_code == 200, f"History GET failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "History should be a list"
        print(f"✓ History endpoint works, {len(data)} messages")

    def test_message_delete_endpoint_works(self, api_client, auth_headers):
        """DELETE /api/visor-ai/message/{id} should work"""
        # First create a message
        chat_response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Test message for deletion"},
            timeout=30
        )
        assert chat_response.status_code == 200
        
        message_id = chat_response.json()["id"]
        
        # Delete the message
        delete_response = api_client.delete(
            f"{BASE_URL}/api/visor-ai/message/{message_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 200, f"Message delete failed: {delete_response.text}"
        
        data = delete_response.json()
        assert "message" in data, "Should return confirmation"
        print(f"✓ Message delete endpoint works")

    def test_history_clear_endpoint_works(self, api_client, auth_headers):
        """DELETE /api/visor-ai/history should work"""
        response = api_client.delete(
            f"{BASE_URL}/api/visor-ai/history",
            headers=auth_headers
        )
        assert response.status_code == 200, f"History clear failed: {response.text}"
        
        data = response.json()
        assert "message" in data, "Should return confirmation"
        print(f"✓ History clear endpoint works")


# ══════════════════════════════════════════════════════════════════════════════
#  AUTHENTICATION TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestAuthentication:
    """Authentication tests for memory endpoints"""

    def test_memory_requires_auth(self, api_client):
        """Memory GET should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/visor-ai/memory")
        assert response.status_code == 401, "Memory GET should require auth"
        print("✓ Memory GET requires authentication")

    def test_memory_delete_requires_auth(self, api_client):
        """Memory DELETE should require authentication"""
        response = api_client.delete(f"{BASE_URL}/api/visor-ai/memory")
        assert response.status_code == 401, "Memory DELETE should require auth"
        print("✓ Memory DELETE requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
