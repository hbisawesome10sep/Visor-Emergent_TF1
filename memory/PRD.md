# Visor - AI-Powered Finance Manager PRD

## Product Overview
Visor is a personal finance management app built with React Native/Expo (frontend) and FastAPI/MongoDB (backend) for Indian users.

## Architecture
- **Frontend**: Expo, React Native, TypeScript, expo-router, DM Sans font
- **Backend**: Python, FastAPI, MongoDB
- **AI**: OpenAI GPT-5.2 via Emergent Integrations (with risk profile context)
- **Market Data**: Yahoo Finance (yfinance) — LIVE Indian market data

## Invest Screen Layout (v8 — Feb 17, 2026)
1. **Indian Markets** — Live Nifty 50, SENSEX, Nifty Bank, Gold, Silver
2. **Portfolio Overview** — Invested vs Current Value, category breakdown (includes holdings)
3. **My Holdings** — Manual add + CAS PDF upload, live prices
4. **Asset Allocation** — Donut pie chart
5. **Risk Profile & Strategy** — 12-question behavioral finance assessment, score breakdown bars
6. **Tax Planning** — Multi-section (80C, 80D, 80CCD1B, 80E, 80TTA), auto-mapped, progress bars, tax saved estimates
7. **Rebalancing Actions** — Actual vs target allocation bars, specific reduce/increase suggestions
8. **What-If Simulator** — Interactive sliders (Equity/Debt/Gold/Alt), projected returns, volatility, Sharpe ratio, 5y/10y portfolio projections
9. **Financial Goals** — CRUD with progress tracking

## Key API Endpoints
- `GET /api/market-data` — Live Indian market data
- `GET /api/portfolio-overview` — Invested vs current value (includes holdings)
- `GET/POST /api/holdings` — Holdings CRUD
- `GET /api/holdings/live` — Holdings with live prices
- `POST /api/holdings/upload-cas` — CAS PDF upload
- `GET/POST /api/risk-profile` — Risk profile CRUD
- `GET /api/tax-summary` — Tax deductions by section
- `GET /api/portfolio-rebalancing` — Actual vs target allocation with actions
- `POST /api/ai/chat` — AI advisor (includes risk profile in context)

## DB Schema
- **holdings**: `{ _id, user_id, name, ticker, isin, category, quantity, buy_price, buy_date, source, created_at }`
- **risk_profiles**: `{ _id, user_id, answers[], score, profile, breakdown{}, created_at }`
- **transactions**: `{ _id, user_id, amount, type, category, date, description }`
- **market_data**: `{ key, name, price, change, change_percent, prev_close, last_updated }`

## Test Credentials
- rajesh@visor.demo / Demo@123

## Completed
- ✅ Phase 1: Live Indian Markets (yfinance)
- ✅ Phase 2: Portfolio Overview (invested vs current)
- ✅ Phase 2.5: Holdings Management (manual + CAS upload)
- ✅ Holdings integrated into Portfolio Overview
- ✅ Phase 3: Risk Appetite Questionnaire (12 questions, backend persistence, AI integration)
- ✅ Phase 4: Tax Planning (80C/80D/80CCD1B/80E/80TTA, auto-mapping, tax saved estimates)
- ✅ Phase 4.5: Portfolio Rebalancing (actual vs target allocation, actionable suggestions)
- ✅ Phase 4.6: What-If Simulator (interactive sliders, projected returns/volatility/Sharpe, 5y/10y projections)
- ✅ Recurring Transactions (SIPs) - Full CRUD, pause/resume, manual execution (Feb 17, 2026)
- ✅ Bug Fix: AI Chat endpoint alignment (Feb 17, 2026)
- ✅ Bug Fix: Investment transactions display without negative sign (Feb 17, 2026)

## Prioritized Backlog

### P0 (Next)
- eCAS Statement parsing improvements (user can provide sample file for exact field extraction)
- Transaction Buy/Sell toggle + Capital Gains Tax calculation

### P1
- Component Refactoring: Break down investments.tsx (~1800 lines) into smaller components

### P2
- Backend migration: Python/FastAPI → Node.js/Express/PostgreSQL
- Enhanced micro-animations
- Push notifications for budget alerts
