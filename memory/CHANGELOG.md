# Visor Finance — CHANGELOG

## v2.3.0 — March 17, 2026 — Major Refactoring (Code Architecture)
### Refactoring
- **visor_ai.py** (835→277 lines, -67%): Extracted calculators → `services/visor_calculators.py`, helpers → `services/visor_helpers.py`, system prompt → `services/visor_prompt.py`
- **bank_statements.py** (2808→294 lines, -90%): Extracted utils → `parsers/utils.py`, CSV/Excel → `parsers/csv_excel.py`, PDF parsers → `parsers/pdf_parsers.py`
- **investments.tsx** (2116→1981 lines): Extracted types, constants, risk questions → `components/investments/types.ts`

### New Modules Created
- `/app/backend/services/` — Visor AI business logic (calculators, helpers, prompt)
- `/app/backend/parsers/` — Bank statement parsing (utils, CSV/Excel, PDF parsers)
- `/app/frontend/src/components/investments/types.ts` — Shared investment types & constants

### Testing
- 23/23 regression tests passed (100%)
- All 16 API endpoints verified working post-refactoring

---


## v2.2.4 — March 17, 2026 — Token Expiry & Empty State Fixes
### Bug Fixes
- **Token Expired Crash**: Extended JWT token validity from 7 days to 30 days (`auth.py`)
- **Auto-Logout on 401**: App now automatically logs out and redirects to login when token expires, instead of crashing (`api.ts`, `AuthContext.tsx`)
- **Fake Dashboard Percentages**: Removed hardcoded `12.5%` and `8.2%` from dashboard overview cards — no longer shows misleading numbers when data is empty (`index.tsx`)
- **Insights Fake Fallback Data**: Removed fake ₹1.5L/₹95K fallback data from insights page — shows zeros and empty states instead of fake numbers when there's no real data (`insights.tsx`)
- **Upload 401 Handling**: Bank statement and CC statement uploads now detect expired tokens and show "Session expired" instead of generic error (`settings.tsx`)

### Files Modified
- `/app/backend/auth.py` (token expiry 7d → 30d)
- `/app/frontend/src/utils/api.ts` (auto-logout on 401)
- `/app/frontend/src/context/AuthContext.tsx` (token-expired handler registration)
- `/app/frontend/app/(tabs)/index.tsx` (removed hardcoded percentChange)
- `/app/frontend/app/(tabs)/insights.tsx` (removed fake data fallbacks)
- `/app/frontend/app/(tabs)/settings.tsx` (401 handling for uploads)

### Testing
- 19/19 backend tests pass (100%)

---


## v2.2.1 — March 1, 2026 — UI/UX Polish & Bug Fixes
### Bug Fixes
- **Absurd percentages in Insights**: Clamped savings rate to [-100%, 100%] range across backend (`dashboard.py`) and frontend (`insights.tsx`, `MonthlyTrendCard.tsx`)
- **Emergency fund negative months**: Capped at 0 minimum (was showing -45.8 months)
- **Smart Alerts**: Backend now returns sensible values instead of extreme negatives

### UI/UX Improvements
- **Visor AI icon**: Changed from hand-coin to premium "shield-star" icon
- **"Tera Finance Buddy" → "Your Finance Companion"**: Professional subtitle
- **AI tone**: Rewritten system prompt — polished, warm but professional Hinglish. No more street slang
- **Chat bubbles**: iOS glassmorphism style with subtle borders and rounded corners
- **Welcome text**: Professional English/Hinglish mix
- **Disclaimer**: Professional English
- **Input placeholder**: "Ask anything about finance..."
- **Thinking indicator**: "Visor is thinking..."

### Files Modified
- `/app/backend/routes/visor_ai.py` (system prompt rewrite)
- `/app/backend/routes/dashboard.py` (savings rate & emergency fund clamping)
- `/app/frontend/src/components/AIAdvisorChat.tsx` (icon, text, bubble styles)
- `/app/frontend/src/components/MonthlyTrendCard.tsx` (savings rate clamping)
- `/app/frontend/app/(tabs)/insights.tsx` (savings rate & runway clamping)

---

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
