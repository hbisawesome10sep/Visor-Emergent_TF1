# Visor - AI-Powered Finance Manager PRD

## Product Overview
Visor is a personal finance management app built with React Native/Expo (frontend) and FastAPI/MongoDB (backend) for Indian users.

## Architecture
- **Frontend**: Expo, React Native, TypeScript, expo-router, DM Sans font
- **Backend**: Python, FastAPI, MongoDB
- **AI**: OpenAI GPT-4 via Emergent Integrations
- **Market Data**: Yahoo Finance (yfinance) — LIVE Indian market data, no API key needed. Scheduled 4x daily IST: 9:25, 11:30, 12:30, 15:15. Gold/Silver converted from international USD price to domestic INR with import duty premiums (Gold: 8.2%, Silver: 20.9%).

## Core Features
- Auth (login/register), Dashboard (health score, liquid fill cards, charts, date filters, FAB)
- Transactions (CRUD with PUT/POST/DELETE, dropdown categories, optional descriptions, calendar date picker)
- Insights (6 animated cards, national averages, AI recommendations)
- Investments (Indian Markets live data, portfolio overview with invested vs current value, holdings management, asset allocation pie chart, risk profile, goals, tax saving)
- Settings (theme toggle, profile, export), Bookkeeping, AI Advisor chat

## Invest Screen Layout (v5 — Feb 17, 2026)
1. **Indian Markets** (TOP) — Clean table-row layout: Nifty 50, SENSEX, Nifty Bank, Gold (10g/24K), Silver (1Kg/999) with LIVE pricing from Yahoo Finance
2. **Portfolio Overview** — Invested vs Current Value with gain/loss %, category-wise breakdown (SIP, PPF, Stock, Mutual Fund) with invested, current, and return columns. **Now includes holdings data** merged with transaction-based investments. Category names normalized (Stocks→Stock, etc.)
3. **My Holdings** — Manual entry (Add button) and CAS PDF upload. Shows individual holdings with live prices, gain/loss %. Summary card with total holdings value and overall return.
4. **Asset Allocation** — Donut pie chart of all investment categories
5. **Risk Profile & Strategy** — Assessment + recommended allocation strategy
6. **Tax Saving** — Section 80C progress
7. **Financial Goals** — CRUD with progress tracking

## Key API Endpoints
- `GET /api/market-data` — Returns cached LIVE Indian market data (no auth)
- `POST /api/market-data/refresh` — Trigger manual refresh (auth required)
- `GET /api/portfolio-overview` — Returns invested vs current value per category, includes holdings data (auth required)
- `GET /api/holdings` — List user's holdings (auth required)
- `GET /api/holdings/live` — Holdings with live prices and summary (auth required)
- `POST /api/holdings` — Create a new holding (auth required)
- `PUT /api/holdings/{id}` — Update a holding (auth required)
- `DELETE /api/holdings/{id}` — Delete a holding (auth required)
- `POST /api/holdings/upload-cas` — Upload CAS PDF to import holdings (auth required)
- `DELETE /api/holdings/clear-all` — Remove all holdings (auth required)
- `GET /api/dashboard/stats` — Dashboard stats with invest_breakdown
- CRUD: `/api/transactions`, `/api/goals`

## DB Schema
- **holdings**: `{ _id, user_id, name, ticker, isin, category, quantity, buy_price, buy_date, source, created_at }`
- **transactions**: `{ _id, user_id, amount, type, category, date, description }`
- **market_data**: `{ symbol/key, name, price, change, change_percent, prev_close, last_updated }`
- **goals**: `{ _id, user_id, title, target_amount, current_amount, deadline, category }`

## Test Credentials
- rajesh@visor.demo / Demo@123

## Completed (as of Feb 17, 2026)
- ✅ Phase 1: Live Indian Markets data (yfinance)
- ✅ Phase 2: Portfolio Overview (invested vs current value)
- ✅ Phase 2.5: Holdings Management (manual add + CAS upload) — Backend CRUD + Frontend UI + Modals
- ✅ Holdings integrated into Portfolio Overview calculations
- ✅ Category normalization (Stocks→Stock, Fixed Deposit→FD, Mutual Funds→Mutual Fund)
- ✅ Backend tests: 15/15 passing

## Prioritized Backlog

### P0 (Next)
- Phase 3: Risk Profile Assessment (10-15 behavioral finance questions + Visor AI integration)
- Phase 4: Tax Planning (Chapter VI deductions, 80C/80D tracking)
- Phase 5: Transaction Buy/Sell + Capital Gains Tax

### P1
- Recurring Transactions (monthly SIPs)

### P2
- Backend migration: Python/FastAPI → Node.js/Express/PostgreSQL
- Enhanced micro-animations
- Push notifications for budget alerts
