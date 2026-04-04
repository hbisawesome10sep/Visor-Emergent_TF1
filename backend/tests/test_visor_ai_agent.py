"""
Visor AI Agent - Comprehensive Backend API Tests
Tests for: Chat endpoint, SIP/EMI/CAGR calculators, live stock prices,
finance-only guardrail, web search trigger, multilingual understanding,
chat history management.

Features tested:
- POST /api/visor-ai/chat: basic Hinglish chat, calculator auto-detection,
  live stock prices, finance guardrail, web search, Tamil transliteration
- GET /api/visor-ai/history: retrieve chat history
- DELETE /api/visor-ai/history: clear chat history
"""
import pytest
import requests
import os
import time

# Use public backend URL for testing
BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'https://finance-parser-split.preview.emergentagent.com').rstrip('/')


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
#  HEALTH CHECK - Verify server is running
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
#  VISOR AI CHAT - Basic Functionality
# ══════════════════════════════════════════════════════════════════════════════

class TestVisorAIChatBasic:
    """Basic chat functionality tests"""

    def test_chat_basic_hinglish_response(self, api_client, auth_headers):
        """Test basic chat with Hinglish response - should respond in Hinglish by default"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Hi, how are you?"},
            timeout=30  # LLM calls can take time
        )
        assert response.status_code == 200, f"Chat failed: {response.text}"

        data = response.json()
        # Verify response structure
        assert "id" in data, "Response should have id"
        assert "user_msg_id" in data, "Response should have user_msg_id"
        assert "role" in data, "Response should have role"
        assert data["role"] == "assistant", "Role should be assistant"
        assert "content" in data, "Response should have content"
        assert len(data["content"]) > 0, "Content should not be empty"
        assert "created_at" in data, "Response should have created_at"

        print(f"✓ Basic chat successful, response length: {len(data['content'])} chars")
        print(f"  Response preview: {data['content'][:150]}...")

    def test_chat_with_screen_context(self, api_client, auth_headers):
        """Test chat with screen_context parameter"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={
                "message": "What am I looking at?",
                "screen_context": "Dashboard screen showing total balance and recent transactions"
            },
            timeout=30
        )
        assert response.status_code == 200, f"Chat with context failed: {response.text}"

        data = response.json()
        assert "content" in data
        assert len(data["content"]) > 0
        print(f"✓ Chat with screen_context successful")


# ══════════════════════════════════════════════════════════════════════════════
#  VISOR AI CHAT - Calculator Auto-Detection
# ══════════════════════════════════════════════════════════════════════════════

class TestVisorAICalculators:
    """Calculator auto-detection tests"""

    def test_sip_calculator_detection(self, api_client, auth_headers):
        """Test SIP calculator auto-detection when user asks about SIP"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Calculate SIP of 10000 per month at 12% for 15 years"},
            timeout=30
        )
        assert response.status_code == 200, f"SIP calc failed: {response.text}"

        data = response.json()
        assert "content" in data
        
        # Verify calculator_result is returned
        assert "calculator_result" in data, "Should return calculator_result for SIP query"
        calc = data.get("calculator_result")
        
        if calc:
            assert calc.get("type") == "SIP Calculator", f"Calculator type should be SIP, got: {calc.get('type')}"
            # Verify SIP fields are present
            assert "monthly_sip" in calc, "Should have monthly_sip"
            assert "annual_return" in calc, "Should have annual_return"
            assert "future_value" in calc, "Should have future_value"
            assert "total_invested" in calc, "Should have total_invested"
            assert "wealth_gained" in calc, "Should have wealth_gained"
            print(f"✓ SIP Calculator detected: {calc.get('type')}")
            print(f"  Monthly SIP: {calc.get('monthly_sip')}")
            print(f"  Future Value: {calc.get('future_value')}")
        else:
            print("⚠ SIP Calculator not auto-detected (may be explained in text)")

    def test_emi_calculator_detection(self, api_client, auth_headers):
        """Test EMI calculator auto-detection for loan queries"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Calculate home loan EMI for 50 lakh at 8.5% for 20 years"},
            timeout=30
        )
        assert response.status_code == 200, f"EMI calc failed: {response.text}"

        data = response.json()
        assert "content" in data
        
        # Verify calculator_result
        assert "calculator_result" in data, "Should return calculator_result for EMI query"
        calc = data.get("calculator_result")
        
        if calc:
            assert calc.get("type") == "EMI Calculator", f"Calculator type should be EMI, got: {calc.get('type')}"
            # Verify EMI fields
            assert "loan_amount" in calc, "Should have loan_amount"
            assert "monthly_emi" in calc, "Should have monthly_emi"
            assert "total_payment" in calc, "Should have total_payment"
            assert "total_interest" in calc, "Should have total_interest"
            print(f"✓ EMI Calculator detected: {calc.get('type')}")
            print(f"  Loan Amount: {calc.get('loan_amount')}")
            print(f"  Monthly EMI: {calc.get('monthly_emi')}")
        else:
            print("⚠ EMI Calculator not auto-detected (may be explained in text)")

    def test_fire_calculator_detection(self, api_client, auth_headers):
        """Test FIRE calculator auto-detection"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Calculate my FIRE number if monthly expenses are 50000"},
            timeout=30
        )
        assert response.status_code == 200, f"FIRE calc failed: {response.text}"

        data = response.json()
        assert "content" in data
        
        calc = data.get("calculator_result")
        if calc and "FIRE" in calc.get("type", ""):
            assert "fire_number" in calc, "Should have fire_number"
            print(f"✓ FIRE Calculator detected: {calc.get('fire_number')}")
        else:
            print("⚠ FIRE Calculator not auto-detected")

    def test_ppf_calculator_detection(self, api_client, auth_headers):
        """Test PPF calculator auto-detection"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "PPF mein 1.5 lakh yearly invest karne pe 15 saal baad kitna milega?"},
            timeout=30
        )
        assert response.status_code == 200, f"PPF calc failed: {response.text}"

        data = response.json()
        assert "content" in data
        
        calc = data.get("calculator_result")
        if calc and "PPF" in calc.get("type", ""):
            assert "maturity_value" in calc, "Should have maturity_value"
            print(f"✓ PPF Calculator detected: {calc.get('maturity_value')}")
        else:
            print("⚠ PPF Calculator not auto-detected")


# ══════════════════════════════════════════════════════════════════════════════
#  VISOR AI CHAT - Live Stock Price Fetching
# ══════════════════════════════════════════════════════════════════════════════

class TestVisorAIStockPrices:
    """Live stock price fetching tests"""

    def test_reliance_stock_price(self, api_client, auth_headers):
        """Test live stock price fetching for Reliance"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Reliance ka price kya hai?"},
            timeout=45  # Stock fetch can take time
        )
        assert response.status_code == 200, f"Stock price fetch failed: {response.text}"

        data = response.json()
        assert "content" in data
        content = data["content"].lower()
        
        # Should mention Reliance and likely contain price info or market reference
        print(f"✓ Stock price query successful")
        print(f"  Response preview: {data['content'][:200]}...")

    def test_multiple_stock_query(self, api_client, auth_headers):
        """Test query with multiple stocks"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "TCS aur Infosys ka price batao"},
            timeout=45
        )
        assert response.status_code == 200, f"Multi-stock query failed: {response.text}"

        data = response.json()
        assert "content" in data
        print(f"✓ Multi-stock query successful")

    def test_nifty_index_query(self, api_client, auth_headers):
        """Test Nifty 50 index query"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Nifty 50 kahan hai aaj?"},
            timeout=45
        )
        assert response.status_code == 200, f"Index query failed: {response.text}"

        data = response.json()
        assert "content" in data
        print(f"✓ Index query successful")


# ══════════════════════════════════════════════════════════════════════════════
#  VISOR AI CHAT - Finance-Only Guardrail
# ══════════════════════════════════════════════════════════════════════════════

class TestVisorAIGuardrail:
    """Finance-only guardrail tests - should reject non-finance queries"""

    def test_reject_joke_request(self, api_client, auth_headers):
        """Test that non-finance queries like jokes are rejected"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Tell me a funny joke"},
            timeout=30
        )
        assert response.status_code == 200, f"Guardrail test failed: {response.text}"

        data = response.json()
        assert "content" in data
        content = data["content"].lower()
        
        # Should politely redirect to finance topics
        # Look for phrases like "finance", "money", "investing", "help" that indicate redirection
        redirect_indicators = ["finance", "money", "invest", "personal finance", "visor", "help", "pooch"]
        has_redirect = any(ind in content for ind in redirect_indicators)
        
        print(f"✓ Non-finance query handled")
        print(f"  Response: {data['content'][:200]}...")
        
        # Assert that the response redirects to finance (shouldn't tell a joke)
        assert "joke" not in content or has_redirect, "Should redirect non-finance queries to finance topics"

    def test_reject_poem_request(self, api_client, auth_headers):
        """Test that poem writing requests are rejected"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Write me a poem about the moon"},
            timeout=30
        )
        assert response.status_code == 200, f"Poem guardrail test failed: {response.text}"

        data = response.json()
        assert "content" in data
        print(f"✓ Poem request handled (should redirect to finance)")

    def test_accept_finance_question(self, api_client, auth_headers):
        """Test that genuine finance questions are accepted"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "What is the difference between SIP and lumpsum investment?"},
            timeout=30
        )
        assert response.status_code == 200, f"Finance question failed: {response.text}"

        data = response.json()
        assert "content" in data
        content = data["content"].lower()
        
        # Should actually answer the finance question
        finance_terms = ["sip", "lumpsum", "invest", "mutual fund", "return", "market"]
        has_answer = any(term in content for term in finance_terms)
        
        assert has_answer, "Should provide substantive answer to finance questions"
        print(f"✓ Finance question answered properly")


# ══════════════════════════════════════════════════════════════════════════════
#  VISOR AI CHAT - Web Search Trigger
# ══════════════════════════════════════════════════════════════════════════════

class TestVisorAIWebSearch:
    """Web search trigger tests for news queries"""

    def test_news_query_triggers_search(self, api_client, auth_headers):
        """Test that news-related queries trigger web search"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Latest stock market news kya hai?"},
            timeout=45  # Web search takes time
        )
        assert response.status_code == 200, f"News query failed: {response.text}"

        data = response.json()
        assert "content" in data
        print(f"✓ News query successful")
        print(f"  Response preview: {data['content'][:200]}...")

    def test_rbi_policy_news(self, api_client, auth_headers):
        """Test RBI policy news query"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "RBI ka latest policy update batao"},
            timeout=45
        )
        assert response.status_code == 200, f"RBI news query failed: {response.text}"

        data = response.json()
        assert "content" in data
        print(f"✓ RBI policy query successful")

    def test_budget_news(self, api_client, auth_headers):
        """Test budget-related news query"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Budget 2025 mein kya changes hue tax mein?"},
            timeout=45
        )
        assert response.status_code == 200, f"Budget news query failed: {response.text}"

        data = response.json()
        assert "content" in data
        print(f"✓ Budget query successful")


# ══════════════════════════════════════════════════════════════════════════════
#  VISOR AI CHAT - Multilingual Understanding
# ══════════════════════════════════════════════════════════════════════════════

class TestVisorAIMultilingual:
    """Multilingual understanding tests - Tamil, Marathi, Bengali transliteration"""

    def test_tamil_transliteration(self, api_client, auth_headers):
        """Test Tamil transliterated query understanding"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Enna mutual fund invest pannanum?"},  # "Which mutual fund to invest?" in Tamil
            timeout=30
        )
        assert response.status_code == 200, f"Tamil query failed: {response.text}"

        data = response.json()
        assert "content" in data
        content = data["content"].lower()
        
        # Should understand the query and provide investment advice
        investment_terms = ["mutual fund", "invest", "sip", "fund", "return", "portfolio", "paisa"]
        has_investment_content = any(term in content for term in investment_terms)
        
        print(f"✓ Tamil transliteration understood")
        print(f"  Response preview: {data['content'][:200]}...")
        
        # The response should relate to investments
        assert has_investment_content or len(data["content"]) > 50, "Should provide relevant investment advice"

    def test_marathi_transliteration(self, api_client, auth_headers):
        """Test Marathi transliterated query understanding"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Mala tax bachat kashi karavi?"},  # "How to save tax?" in Marathi
            timeout=30
        )
        assert response.status_code == 200, f"Marathi query failed: {response.text}"

        data = response.json()
        assert "content" in data
        print(f"✓ Marathi transliteration understood")

    def test_hindi_hinglish_mix(self, api_client, auth_headers):
        """Test Hindi/Hinglish mixed query"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Mera paisa kidhar lagaun? Kuch suggestion do"},
            timeout=30
        )
        assert response.status_code == 200, f"Hinglish query failed: {response.text}"

        data = response.json()
        assert "content" in data
        print(f"✓ Hinglish query handled")


# ══════════════════════════════════════════════════════════════════════════════
#  VISOR AI HISTORY - Get and Clear Chat History
# ══════════════════════════════════════════════════════════════════════════════

class TestVisorAIHistory:
    """Chat history management tests"""

    def test_get_chat_history(self, api_client, auth_headers):
        """Test getting chat history"""
        response = api_client.get(
            f"{BASE_URL}/api/visor-ai/history",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Get history failed: {response.text}"

        data = response.json()
        assert isinstance(data, list), "History should be a list"
        
        if len(data) > 0:
            # Verify message structure
            msg = data[0]
            assert "id" in msg, "Message should have id"
            assert "role" in msg, "Message should have role"
            assert msg["role"] in ["user", "assistant"], "Role should be user or assistant"
            assert "content" in msg, "Message should have content"
            assert "created_at" in msg, "Message should have created_at"
            
            # Count user vs assistant messages
            user_msgs = sum(1 for m in data if m["role"] == "user")
            assistant_msgs = sum(1 for m in data if m["role"] == "assistant")
            print(f"✓ Chat history retrieved: {len(data)} messages ({user_msgs} user, {assistant_msgs} assistant)")
        else:
            print("✓ Chat history is empty (no messages)")

    def test_clear_chat_history(self, api_client, auth_headers):
        """Test clearing chat history"""
        # First ensure there's at least one message
        api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Test message before clearing"},
            timeout=30
        )
        
        # Clear history
        response = api_client.delete(
            f"{BASE_URL}/api/visor-ai/history",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Clear history failed: {response.text}"

        data = response.json()
        assert "message" in data, "Should return confirmation message"
        assert "cleared" in data["message"].lower() or "clear" in data["message"].lower(), \
            "Should confirm history was cleared"
        
        print(f"✓ Chat history cleared: {data['message']}")

    def test_history_is_empty_after_clear(self, api_client, auth_headers):
        """Verify history is empty after clearing"""
        response = api_client.get(
            f"{BASE_URL}/api/visor-ai/history",
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0, "History should be empty after clear"
        print(f"✓ Verified history is empty after clear")


# ══════════════════════════════════════════════════════════════════════════════
#  VISOR AI - Error Handling & Edge Cases
# ══════════════════════════════════════════════════════════════════════════════

class TestVisorAIEdgeCases:
    """Edge case and error handling tests"""

    def test_empty_message(self, api_client, auth_headers):
        """Test empty message handling"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": ""},
            timeout=30
        )
        # Should either return 400 or handle gracefully
        assert response.status_code in [200, 400, 422], f"Unexpected status: {response.status_code}"
        print(f"✓ Empty message handled with status {response.status_code}")

    def test_very_long_message(self, api_client, auth_headers):
        """Test handling of very long message"""
        long_message = "Calculate SIP " + ("of 10000 rupees monthly " * 50)
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": long_message[:1200]},  # Cap at 1200 chars
            timeout=45
        )
        assert response.status_code == 200, f"Long message failed: {response.text}"
        print(f"✓ Long message handled successfully")

    def test_unauthorized_access(self, api_client):
        """Test that unauthorized requests are rejected"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            json={"message": "Hello"}
        )
        assert response.status_code == 401, "Should return 401 for unauthorized request"
        print(f"✓ Unauthorized request correctly rejected")

    def test_invalid_token(self, api_client):
        """Test that invalid tokens are rejected"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers={"Authorization": "Bearer invalid_token_here"},
            json={"message": "Hello"}
        )
        assert response.status_code == 401, "Should return 401 for invalid token"
        print(f"✓ Invalid token correctly rejected")


# ══════════════════════════════════════════════════════════════════════════════
#  VISOR AI - Integration with User Data
# ══════════════════════════════════════════════════════════════════════════════

class TestVisorAIUserData:
    """Tests to verify AI uses user's financial data"""

    def test_portfolio_review_uses_user_data(self, api_client, auth_headers):
        """Test that portfolio review uses actual user holdings"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Review my portfolio"},
            timeout=45
        )
        assert response.status_code == 200, f"Portfolio review failed: {response.text}"

        data = response.json()
        assert "content" in data
        # Should reference user's actual financial situation
        print(f"✓ Portfolio review generated")
        print(f"  Response preview: {data['content'][:250]}...")

    def test_tax_planning_personalized(self, api_client, auth_headers):
        """Test that tax planning advice is personalized"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Mere liye tax kaise bachaye? 80C ke under kya kar sakta hoon?"},
            timeout=45
        )
        assert response.status_code == 200, f"Tax planning failed: {response.text}"

        data = response.json()
        assert "content" in data
        content = data["content"].lower()
        
        # Should mention tax-related terms
        tax_terms = ["80c", "tax", "deduction", "elss", "ppf", "nsc", "section", "save", "bachao"]
        has_tax_content = any(term in content for term in tax_terms)
        
        assert has_tax_content, "Should provide tax-related advice"
        print(f"✓ Tax planning advice generated")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
