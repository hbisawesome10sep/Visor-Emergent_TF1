"""
Visor AI P1 Features - Financial Personality Engine & Tax Knowledge Base Tests

P1-1: Financial Personality Engine
- GET /api/visor-ai/personality: Computes and returns full personality profile
- GET /api/visor-ai/personality/cached: Returns cached personality without recomputing
- Personality context injection into AI chat

P1-2: Tax Knowledge Base (RAG-lite)
- Tax queries trigger relevant section injection
- Non-tax queries should NOT trigger tax knowledge injection
- Direct unit tests for detect_tax_sections() and get_tax_knowledge_context()

Regression: P0 features still work (multi-model routing, persistent memory)
"""
import pytest
import requests
import os
import sys
import time

# Add backend to path for direct imports
sys.path.insert(0, '/app/backend')

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
#  P1-1: FINANCIAL PERSONALITY ENGINE - GET /api/visor-ai/personality
# ══════════════════════════════════════════════════════════════════════════════

class TestFinancialPersonalityCompute:
    """Test GET /api/visor-ai/personality endpoint - computes full personality"""

    def test_personality_endpoint_exists(self, api_client, auth_headers):
        """Personality endpoint should exist and return 200"""
        response = api_client.get(
            f"{BASE_URL}/api/visor-ai/personality",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200, f"Personality GET failed: {response.text}"
        print("✓ Personality endpoint exists and returns 200")

    def test_personality_has_spending_archetype(self, api_client, auth_headers):
        """Personality should have spending_archetype field"""
        response = api_client.get(
            f"{BASE_URL}/api/visor-ai/personality",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "spending_archetype" in data, "Should have spending_archetype"
        assert "spending_description" in data, "Should have spending_description"
        
        valid_archetypes = ["Frugal Saver", "Balanced Spender", "Lifestyle Spender", "Living on the Edge", "Unknown"]
        assert data["spending_archetype"] in valid_archetypes, f"Invalid archetype: {data['spending_archetype']}"
        
        print(f"✓ Spending Archetype: {data['spending_archetype']}")
        print(f"  Description: {data['spending_description']}")

    def test_personality_has_savings_consistency(self, api_client, auth_headers):
        """Personality should have savings_consistency field"""
        response = api_client.get(
            f"{BASE_URL}/api/visor-ai/personality",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "savings_consistency" in data, "Should have savings_consistency"
        assert "savings_description" in data, "Should have savings_description"
        assert "savings_trend" in data, "Should have savings_trend"
        
        valid_consistency = ["Disciplined", "Steady", "Improving", "Irregular", "Insufficient Data"]
        assert data["savings_consistency"] in valid_consistency, f"Invalid consistency: {data['savings_consistency']}"
        
        print(f"✓ Savings Consistency: {data['savings_consistency']} (trend: {data['savings_trend']})")

    def test_personality_has_investment_behavior(self, api_client, auth_headers):
        """Personality should have investment_behavior field"""
        response = api_client.get(
            f"{BASE_URL}/api/visor-ai/personality",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "investment_behavior" in data, "Should have investment_behavior"
        assert "investment_description" in data, "Should have investment_description"
        
        valid_behaviors = ["Non-Investor", "Passive Investor", "Active Investor", "Aggressive Builder", "Beginner", "Unknown"]
        assert data["investment_behavior"] in valid_behaviors, f"Invalid behavior: {data['investment_behavior']}"
        
        print(f"✓ Investment Behavior: {data['investment_behavior']}")
        print(f"  Description: {data['investment_description']}")

    def test_personality_has_life_stage(self, api_client, auth_headers):
        """Personality should have life_stage field"""
        response = api_client.get(
            f"{BASE_URL}/api/visor-ai/personality",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "life_stage" in data, "Should have life_stage"
        assert "life_stage_description" in data, "Should have life_stage_description"
        
        valid_stages = ["Early Career", "Family Builder", "Peak Earner", "Wealth Accumulator", "Growth Phase", "Getting Started"]
        assert data["life_stage"] in valid_stages, f"Invalid life stage: {data['life_stage']}"
        
        print(f"✓ Life Stage: {data['life_stage']}")
        print(f"  Description: {data['life_stage_description']}")

    def test_personality_has_strengths_and_blind_spots(self, api_client, auth_headers):
        """Personality should have strengths and blind_spots arrays"""
        response = api_client.get(
            f"{BASE_URL}/api/visor-ai/personality",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "strengths" in data, "Should have strengths"
        assert "blind_spots" in data, "Should have blind_spots"
        assert isinstance(data["strengths"], list), "strengths should be a list"
        assert isinstance(data["blind_spots"], list), "blind_spots should be a list"
        
        print(f"✓ Strengths: {data['strengths']}")
        print(f"✓ Blind Spots: {data['blind_spots']}")

    def test_personality_has_metrics(self, api_client, auth_headers):
        """Personality should have metrics object with financial ratios"""
        response = api_client.get(
            f"{BASE_URL}/api/visor-ai/personality",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "metrics" in data, "Should have metrics"
        
        metrics = data["metrics"]
        expected_metrics = ["savings_rate", "investment_rate", "discretionary_ratio", 
                          "num_holdings", "active_sips", "asset_classes"]
        
        for metric in expected_metrics:
            assert metric in metrics, f"metrics should have {metric}"
        
        print(f"✓ Metrics: savings_rate={metrics.get('savings_rate')}%, investment_rate={metrics.get('investment_rate')}%")
        print(f"  Holdings: {metrics.get('num_holdings')}, SIPs: {metrics.get('active_sips')}, Asset Classes: {metrics.get('asset_classes')}")

    def test_personality_has_top_expense_categories(self, api_client, auth_headers):
        """Personality should have top_expense_categories array"""
        response = api_client.get(
            f"{BASE_URL}/api/visor-ai/personality",
            headers=auth_headers,
            timeout=30
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "top_expense_categories" in data, "Should have top_expense_categories"
        assert isinstance(data["top_expense_categories"], list), "top_expense_categories should be a list"
        
        # Each category should have category name and amount
        for cat in data["top_expense_categories"]:
            assert "category" in cat, "Each expense category should have 'category' field"
            assert "amount" in cat, "Each expense category should have 'amount' field"
        
        print(f"✓ Top Expense Categories: {len(data['top_expense_categories'])} categories")
        for cat in data["top_expense_categories"][:3]:
            print(f"  - {cat['category']}: ₹{cat['amount']:,.0f}")


# ══════════════════════════════════════════════════════════════════════════════
#  P1-1: FINANCIAL PERSONALITY ENGINE - GET /api/visor-ai/personality/cached
# ══════════════════════════════════════════════════════════════════════════════

class TestFinancialPersonalityCached:
    """Test GET /api/visor-ai/personality/cached endpoint"""

    def test_cached_personality_endpoint_exists(self, api_client, auth_headers):
        """Cached personality endpoint should exist"""
        response = api_client.get(
            f"{BASE_URL}/api/visor-ai/personality/cached",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 200, f"Cached personality GET failed: {response.text}"
        print("✓ Cached personality endpoint exists")

    def test_cached_returns_same_data_as_compute(self, api_client, auth_headers):
        """Cached personality should return same data as computed personality"""
        # First compute personality
        compute_response = api_client.get(
            f"{BASE_URL}/api/visor-ai/personality",
            headers=auth_headers,
            timeout=30
        )
        assert compute_response.status_code == 200
        computed = compute_response.json()
        
        # Then get cached
        cached_response = api_client.get(
            f"{BASE_URL}/api/visor-ai/personality/cached",
            headers=auth_headers,
            timeout=10
        )
        assert cached_response.status_code == 200
        cached = cached_response.json()
        
        # Should have same core fields
        if "message" not in cached:  # If not "No personality computed yet"
            assert cached["spending_archetype"] == computed["spending_archetype"], "Cached should match computed"
            assert cached["savings_consistency"] == computed["savings_consistency"], "Cached should match computed"
            assert cached["investment_behavior"] == computed["investment_behavior"], "Cached should match computed"
            print(f"✓ Cached personality matches computed personality")
        else:
            print(f"⚠ No cached personality yet: {cached['message']}")

    def test_cached_is_faster_than_compute(self, api_client, auth_headers):
        """Cached endpoint should be faster than compute endpoint"""
        import time
        
        # Time the compute endpoint
        start = time.time()
        api_client.get(f"{BASE_URL}/api/visor-ai/personality", headers=auth_headers, timeout=30)
        compute_time = time.time() - start
        
        # Time the cached endpoint
        start = time.time()
        api_client.get(f"{BASE_URL}/api/visor-ai/personality/cached", headers=auth_headers, timeout=10)
        cached_time = time.time() - start
        
        print(f"✓ Compute time: {compute_time:.2f}s, Cached time: {cached_time:.2f}s")
        
        # Cached should be faster (or at least not significantly slower)
        assert cached_time <= compute_time + 0.5, "Cached should not be slower than compute"


# ══════════════════════════════════════════════════════════════════════════════
#  P1-2: TAX KNOWLEDGE BASE - Unit Tests for detect_tax_sections()
# ══════════════════════════════════════════════════════════════════════════════

class TestTaxKnowledgeBaseDetection:
    """Unit tests for tax knowledge base detection logic (no LLM needed)"""

    def test_detect_80c_query(self):
        """80C queries should be detected"""
        from services.tax_knowledge_base import detect_tax_sections
        
        test_queries = [
            "80C mein kitna invest?",
            "How to save tax under 80C?",
            "ELSS vs PPF which is better?",
            "What is the 80C limit?",
        ]
        
        for query in test_queries:
            sections = detect_tax_sections(query)
            assert "80c" in sections, f"Query '{query}' should detect 80c section"
            print(f"✓ '{query}' → detected: {sections}")

    def test_detect_nps_query(self):
        """NPS queries should detect 80CCD sections"""
        from services.tax_knowledge_base import detect_tax_sections
        
        test_queries = [
            "NPS tax benefit?",
            "80CCD(1B) kya hai?",
            "National pension scheme deduction",
        ]
        
        for query in test_queries:
            sections = detect_tax_sections(query)
            assert any(s in sections for s in ["80ccd1b", "80ccd2"]), f"Query '{query}' should detect NPS sections"
            print(f"✓ '{query}' → detected: {sections}")

    def test_detect_hra_query(self):
        """HRA queries should be detected"""
        from services.tax_knowledge_base import detect_tax_sections
        
        test_queries = [
            "HRA exemption?",
            "House rent allowance calculation",
            "10(13A) kya hai?",
        ]
        
        for query in test_queries:
            sections = detect_tax_sections(query)
            assert "hra_10_13a" in sections, f"Query '{query}' should detect HRA section"
            print(f"✓ '{query}' → detected: {sections}")

    def test_detect_regime_comparison_query(self):
        """Regime comparison queries should be detected"""
        from services.tax_knowledge_base import detect_tax_sections
        
        test_queries = [
            "new vs old regime?",
            "Which regime is better?",
            "konsa regime choose karu?",
        ]
        
        for query in test_queries:
            sections = detect_tax_sections(query)
            assert "new_vs_old_regime" in sections, f"Query '{query}' should detect regime section"
            print(f"✓ '{query}' → detected: {sections}")

    def test_detect_capital_gains_query(self):
        """Capital gains queries should be detected"""
        from services.tax_knowledge_base import detect_tax_sections
        
        test_queries = [
            "capital gains tax?",
            "LTCG on mutual funds?",
            "STCG rate kya hai?",
        ]
        
        for query in test_queries:
            sections = detect_tax_sections(query)
            assert "capital_gains" in sections, f"Query '{query}' should detect capital gains section"
            print(f"✓ '{query}' → detected: {sections}")

    def test_non_tax_queries_not_detected(self):
        """Non-tax queries should NOT trigger tax detection"""
        from services.tax_knowledge_base import detect_tax_sections
        
        non_tax_queries = [
            "gold price?",
            "Hi",
            "What is SIP?",
            "How is the weather?",
            "Thanks",
            "Good morning",
        ]
        
        for query in non_tax_queries:
            sections = detect_tax_sections(query)
            assert len(sections) == 0, f"Non-tax query '{query}' should NOT detect any sections, got: {sections}"
            print(f"✓ '{query}' → no tax sections detected (correct)")


# ══════════════════════════════════════════════════════════════════════════════
#  P1-2: TAX KNOWLEDGE BASE - Unit Tests for get_tax_knowledge_context()
# ══════════════════════════════════════════════════════════════════════════════

class TestTaxKnowledgeBaseContext:
    """Unit tests for tax knowledge context generation (no LLM needed)"""

    def test_80c_context_has_limit(self):
        """80C context should include the Rs 1.5L limit"""
        from services.tax_knowledge_base import get_tax_knowledge_context
        
        context = get_tax_knowledge_context("80C mein kitna invest?")
        
        assert "TAX KNOWLEDGE BASE" in context, "Should have TAX KNOWLEDGE BASE header"
        assert "1,50,000" in context or "150000" in context or "1.5" in context, "Should mention 80C limit"
        assert "Section 80C" in context, "Should mention Section 80C"
        
        print(f"✓ 80C context generated ({len(context)} chars)")
        print(f"  Preview: {context[:200]}...")

    def test_nps_context_has_additional_deduction(self):
        """NPS context should mention the additional Rs 50K deduction"""
        from services.tax_knowledge_base import get_tax_knowledge_context
        
        context = get_tax_knowledge_context("NPS tax benefit?")
        
        assert "TAX KNOWLEDGE BASE" in context, "Should have TAX KNOWLEDGE BASE header"
        assert "50,000" in context or "50000" in context, "Should mention Rs 50K additional deduction"
        
        print(f"✓ NPS context generated ({len(context)} chars)")

    def test_hra_context_has_calculation(self):
        """HRA context should include calculation conditions"""
        from services.tax_knowledge_base import get_tax_knowledge_context
        
        context = get_tax_knowledge_context("HRA exemption?")
        
        assert "TAX KNOWLEDGE BASE" in context, "Should have TAX KNOWLEDGE BASE header"
        assert "Condition" in context or "50%" in context or "40%" in context, "Should mention HRA calculation"
        
        print(f"✓ HRA context generated ({len(context)} chars)")

    def test_regime_context_has_slabs(self):
        """Regime comparison context should include tax slabs"""
        from services.tax_knowledge_base import get_tax_knowledge_context
        
        context = get_tax_knowledge_context("new vs old regime?")
        
        assert "TAX KNOWLEDGE BASE" in context, "Should have TAX KNOWLEDGE BASE header"
        assert "New Regime" in context or "Old Regime" in context, "Should mention regimes"
        
        print(f"✓ Regime comparison context generated ({len(context)} chars)")

    def test_capital_gains_context_has_rates(self):
        """Capital gains context should include STCG/LTCG rates"""
        from services.tax_knowledge_base import get_tax_knowledge_context
        
        context = get_tax_knowledge_context("capital gains tax?")
        
        assert "TAX KNOWLEDGE BASE" in context, "Should have TAX KNOWLEDGE BASE header"
        assert "Capital Gains" in context, "Should mention Capital Gains"
        
        print(f"✓ Capital gains context generated ({len(context)} chars)")

    def test_non_tax_query_returns_empty(self):
        """Non-tax queries should return empty context"""
        from services.tax_knowledge_base import get_tax_knowledge_context
        
        non_tax_queries = ["gold price?", "Hi", "What is SIP?"]
        
        for query in non_tax_queries:
            context = get_tax_knowledge_context(query)
            assert context == "", f"Non-tax query '{query}' should return empty context, got: {context[:50]}..."
            print(f"✓ '{query}' → empty context (correct)")


# ══════════════════════════════════════════════════════════════════════════════
#  P1-2: TAX KNOWLEDGE BASE - Specific Tax Query Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestTaxKnowledgeSpecificQueries:
    """Test specific tax queries mentioned in requirements"""

    def test_80c_kitna_invest(self):
        """Test '80C mein kitna invest?' query"""
        from services.tax_knowledge_base import detect_tax_sections, get_tax_knowledge_context
        
        query = "80C mein kitna invest?"
        sections = detect_tax_sections(query)
        context = get_tax_knowledge_context(query)
        
        assert "80c" in sections, "Should detect 80C section"
        assert len(context) > 0, "Should generate context"
        print(f"✓ '80C mein kitna invest?' → sections: {sections}")

    def test_nps_tax_benefit(self):
        """Test 'NPS tax benefit?' query"""
        from services.tax_knowledge_base import detect_tax_sections, get_tax_knowledge_context
        
        query = "NPS tax benefit?"
        sections = detect_tax_sections(query)
        context = get_tax_knowledge_context(query)
        
        assert any(s in sections for s in ["80ccd1b", "80ccd2"]), "Should detect NPS sections"
        assert len(context) > 0, "Should generate context"
        print(f"✓ 'NPS tax benefit?' → sections: {sections}")

    def test_hra_exemption(self):
        """Test 'HRA exemption?' query"""
        from services.tax_knowledge_base import detect_tax_sections, get_tax_knowledge_context
        
        query = "HRA exemption?"
        sections = detect_tax_sections(query)
        context = get_tax_knowledge_context(query)
        
        assert "hra_10_13a" in sections, "Should detect HRA section"
        assert len(context) > 0, "Should generate context"
        print(f"✓ 'HRA exemption?' → sections: {sections}")

    def test_new_vs_old_regime(self):
        """Test 'new vs old regime?' query"""
        from services.tax_knowledge_base import detect_tax_sections, get_tax_knowledge_context
        
        query = "new vs old regime?"
        sections = detect_tax_sections(query)
        context = get_tax_knowledge_context(query)
        
        assert "new_vs_old_regime" in sections, "Should detect regime section"
        assert len(context) > 0, "Should generate context"
        print(f"✓ 'new vs old regime?' → sections: {sections}")

    def test_capital_gains_tax(self):
        """Test 'capital gains tax?' query"""
        from services.tax_knowledge_base import detect_tax_sections, get_tax_knowledge_context
        
        query = "capital gains tax?"
        sections = detect_tax_sections(query)
        context = get_tax_knowledge_context(query)
        
        assert "capital_gains" in sections, "Should detect capital gains section"
        assert len(context) > 0, "Should generate context"
        print(f"✓ 'capital gains tax?' → sections: {sections}")


# ══════════════════════════════════════════════════════════════════════════════
#  REGRESSION: P0 Features Still Work
# ══════════════════════════════════════════════════════════════════════════════

class TestP0Regression:
    """Regression tests for P0 features (multi-model routing, persistent memory)"""

    def test_chat_returns_model_used(self, api_client, auth_headers):
        """Chat should return model_used field (P0 feature)"""
        response = api_client.post(
            f"{BASE_URL}/api/visor-ai/chat",
            headers=auth_headers,
            json={"message": "Hi"},
            timeout=30
        )
        
        # Handle budget exceeded error gracefully
        if response.status_code == 200:
            data = response.json()
            assert "model_used" in data, "Response should have model_used field"
            print(f"✓ Chat returns model_used: {data['model_used']}")
        elif "budget" in response.text.lower() or "exceeded" in response.text.lower():
            pytest.skip("LLM budget exceeded - skipping chat test")
        else:
            assert response.status_code == 200, f"Chat failed: {response.text}"

    def test_memory_endpoint_works(self, api_client, auth_headers):
        """Memory endpoint should still work (P0 feature)"""
        response = api_client.get(
            f"{BASE_URL}/api/visor-ai/memory",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Memory GET failed: {response.text}"
        
        data = response.json()
        assert "user_id" in data, "Memory should have user_id"
        assert "topics" in data, "Memory should have topics"
        print(f"✓ Memory endpoint works, conversation_count: {data.get('conversation_count', 0)}")

    def test_history_endpoint_works(self, api_client, auth_headers):
        """History endpoint should still work"""
        response = api_client.get(
            f"{BASE_URL}/api/visor-ai/history",
            headers=auth_headers
        )
        assert response.status_code == 200, f"History GET failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "History should be a list"
        print(f"✓ History endpoint works, {len(data)} messages")


# ══════════════════════════════════════════════════════════════════════════════
#  AUTHENTICATION TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestPersonalityAuthentication:
    """Authentication tests for personality endpoints"""

    def test_personality_requires_auth(self, api_client):
        """Personality GET should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/visor-ai/personality")
        assert response.status_code == 401, "Personality GET should require auth"
        print("✓ Personality GET requires authentication")

    def test_cached_personality_requires_auth(self, api_client):
        """Cached personality GET should require authentication"""
        response = api_client.get(f"{BASE_URL}/api/visor-ai/personality/cached")
        assert response.status_code == 401, "Cached personality GET should require auth"
        print("✓ Cached personality GET requires authentication")


# ══════════════════════════════════════════════════════════════════════════════
#  PERSONALITY CONTEXT INJECTION TEST (via visor_engine inspection)
# ══════════════════════════════════════════════════════════════════════════════

class TestPersonalityContextInjection:
    """Test that personality context is properly formatted for injection"""

    def test_personality_context_format(self):
        """Test get_personality_context() returns proper format"""
        from services.financial_personality import get_personality_context
        
        # Create a mock personality
        mock_personality = {
            "spending_archetype": "Balanced Spender",
            "spending_description": "Healthy balance between enjoying life and saving",
            "savings_consistency": "Steady",
            "savings_trend": "stable",
            "investment_behavior": "Active Investor",
            "investment_description": "Growing portfolio with 5 holdings and 2 SIPs",
            "life_stage": "Growth Phase",
            "life_stage_description": "Active income growth",
            "strengths": ["Strong savings discipline", "Regular SIP investing"],
            "blind_spots": ["Portfolio concentrated in one asset class"],
        }
        
        context = get_personality_context(mock_personality)
        
        assert "FINANCIAL PERSONALITY" in context, "Should have FINANCIAL PERSONALITY header"
        assert "Archetype" in context, "Should mention Archetype"
        assert "Balanced Spender" in context, "Should include archetype value"
        assert "Strengths" in context, "Should mention Strengths"
        assert "Blind Spots" in context, "Should mention Blind Spots"
        
        print(f"✓ Personality context format is correct ({len(context)} chars)")
        print(f"  Preview: {context[:200]}...")

    def test_empty_personality_returns_empty_context(self):
        """Empty or unknown personality should return empty context"""
        from services.financial_personality import get_personality_context
        
        # Test with None
        context = get_personality_context(None)
        assert context == "", "None personality should return empty context"
        
        # Test with Unknown archetype
        unknown_personality = {"spending_archetype": "Unknown"}
        context = get_personality_context(unknown_personality)
        assert context == "", "Unknown personality should return empty context"
        
        print("✓ Empty/unknown personality returns empty context")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
