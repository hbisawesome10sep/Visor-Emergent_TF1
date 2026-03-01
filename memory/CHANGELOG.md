# Visor Finance — CHANGELOG

## v2.2.0 — March 1, 2026 — Tax Auto-Detect Bulk Scan
### New Features
- `POST /api/tax-planning/scan` — Bulk scan ALL user data to auto-detect tax deductions
- Scans: transactions (keyword matching), ELSS holdings (80C), SIPs (80C, 80CCD1B, 80D), home loans (80C principal + 24b interest)
- Idempotent — re-scanning doesn't create duplicates
- "Scan All Data" button in Tax screen's Auto-Deductions section
- Scan result banner showing count and amount of new deductions found
- Full CRUD on auto-detected deductions (edit amount, dismiss/delete)

### Files Modified
- `/app/backend/routes/tax.py` (added bulk_scan_tax_deductions endpoint)
- `/app/frontend/src/components/tax/AutoDeductionsSection.tsx` (scan button + result UI)
- `/app/frontend/app/(tabs)/tax.tsx` (scan state + handler)

### Testing
- 16/16 backend tests pass (100%)
- Verified: scan, idempotency, CRUD, 404 handling, auth, + Visor AI regression

---

## v2.1.0 — March 1, 2026 — Visor AI Agent
### New Features
- Unified Visor AI Agent (`/api/visor-ai/chat`) — India-first financial companion powered by GPT-5.2
- 22 Indian language support (transliterated text understood in English script)
- Default language: Hinglish, adapts to user's language
- 9 built-in financial calculators: SIP, Step-up SIP, EMI, CAGR, FD, PPF, FIRE, HRA, Gratuity
- Auto-calculator detection from natural conversation
- Live stock prices for 80+ Indian stocks/indices + Gold/Silver
- Web search for financial news/current affairs (DuckDuckGo)
- Full app-data awareness (portfolio, transactions, goals, SIPs, credit cards, loans, tax, budgets)
- Finance-only guardrail (politely rejects non-finance queries)
- Financial disclaimer auto-appended on advice
- Redesigned chat UI with friendly coin icon, categorized quick prompts, rich markdown rendering
- Calculator result cards rendered inline in chat
- "Visor soch raha hai..." thinking indicator
- Chat history management (GET/DELETE endpoints)

### Files Added
- `/app/backend/routes/visor_ai.py` (unified AI agent)
- `/app/backend/tests/test_visor_ai_agent.py` (28 tests)

### Files Modified
- `/app/frontend/src/components/AIAdvisorChat.tsx` (complete redesign)
- `/app/backend/server.py` (router registration)

### Testing
- 28/28 backend tests pass (100%)
- Features verified: Hinglish chat, SIP/EMI/FIRE/PPF calculators, live prices, finance guardrail, web search, Tamil/Marathi transliteration, chat history CRUD

---

## v2.0.1 — March 1, 2026 — eCAS Bug Fix
### Bug Fixes
- Fixed critical bug where eCAS parser set `invested_value` to `0.0`, making it identical to `current_value`
- Parser now sums purchase transaction amounts + estimates opening balance cost using first available NAV
- 5/5 unit tests pass

### Files Modified
- `/app/backend/routes/holdings.py` (parser fix in `_parse_cas_text`)

### Files Added
- `/app/backend/tests/test_ecas_parser.py` (5 regression tests)
