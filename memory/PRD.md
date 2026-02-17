# Visor - AI-Powered Finance Manager PRD

## Product Overview
Visor is a personal finance management app built with React Native/Expo (frontend) and FastAPI/MongoDB (backend) for Indian users.

## Architecture
- **Frontend**: Expo, React Native, TypeScript, expo-router, DM Sans font
- **Backend**: Python, FastAPI, MongoDB
- **AI**: OpenAI GPT-5.2 via Emergent Integrations (with risk profile context)
- **Market Data**: Yahoo Finance (yfinance) — LIVE Indian market data

## Core Features
- Auth (login/register), Dashboard (health score, liquid fill cards, charts, date filters, FAB)
- Transactions (CRUD with PUT/POST/DELETE, dropdown categories, optional descriptions, calendar date picker)
- Insights (6 animated cards, national averages, AI recommendations)
- Investments (Indian Markets live data, portfolio overview, holdings management, asset allocation, risk profile, goals, tax saving)
- Settings (theme toggle, profile, export), Bookkeeping, AI Advisor chat

## Invest Screen Layout (v6 — Feb 17, 2026)
1. **Indian Markets** — Live Nifty 50, SENSEX, Nifty Bank, Gold, Silver via yfinance
2. **Portfolio Overview** — Invested vs Current Value, category breakdown (includes holdings)
3. **My Holdings** — Manual add + CAS PDF upload, live prices from yfinance
4. **Asset Allocation** — Donut pie chart
5. **Risk Profile & Strategy** — 12-question behavioral finance assessment, persisted to DB, score breakdown bars, strategy allocation
6. **Tax Saving** — Section 80C progress
7. **Financial Goals** — CRUD with progress tracking

## Key API Endpoints
- `GET /api/market-data` — Live Indian market data
- `GET /api/portfolio-overview` — Invested vs current value (includes holdings)
- `GET/POST /api/holdings` — Holdings CRUD
- `GET /api/holdings/live` — Holdings with live prices
- `POST /api/holdings/upload-cas` — CAS PDF upload
- `GET/POST /api/risk-profile` — Risk profile CRUD (12-question assessment)
- `POST /api/ai/chat` — AI advisor (includes risk profile in context)
- CRUD: `/api/transactions`, `/api/goals`

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
- ✅ Phase 3: Risk Appetite Questionnaire (12 behavioral finance questions, backend persistence, AI integration, score breakdown)

## Prioritized Backlog

### P0 (Next)
- Phase 4: Tax Planning (Chapter VI deductions, 80C/80D tracking)
- Phase 5: Transaction Buy/Sell + Capital Gains Tax

### P1
- Recurring Transactions (monthly SIPs)

### P2
- Backend migration: Python/FastAPI → Node.js/Express/PostgreSQL
- Enhanced micro-animations
- Push notifications for budget alerts
