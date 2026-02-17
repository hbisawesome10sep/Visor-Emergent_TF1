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
- Investments (Indian Markets live data, portfolio overview with invested vs current value, asset allocation pie chart, risk profile, goals, tax saving)
- Settings (theme toggle, profile, export), Bookkeeping, AI Advisor chat

## Invest Screen Layout (v4 — Feb 17, 2026)
1. **Indian Markets** (TOP) — Clean table-row layout: Nifty 50, SENSEX, Nifty Bank, Gold (10g/24K), Silver (1Kg/999) with LIVE pricing from Yahoo Finance
2. **Portfolio Overview** — Invested vs Current Value with gain/loss %, category-wise breakdown (SIP, PPF, Stocks etc) with invested, current, and return columns. Returns calculated using: Nifty performance for equities, fixed interest rates for FD/PPF/NPS, commodity prices for Gold/Silver
3. **Asset Allocation** — Donut pie chart of all investment categories
4. **Risk Profile & Strategy** — Assessment + recommended allocation strategy
5. **Tax Saving** — Section 80C progress
6. **Financial Goals** — CRUD with progress tracking

## Key API Endpoints
- `GET /api/market-data` — Returns cached LIVE Indian market data (no auth)
- `POST /api/market-data/refresh` — Trigger manual refresh (auth required)
- `GET /api/portfolio-overview` — Returns invested vs current value per category (auth required)
- `GET /api/dashboard/stats` — Dashboard stats with invest_breakdown
- CRUD: `/api/transactions`, `/api/goals`

## Test Credentials
- rajesh@visor.demo / Demo@123

## Prioritized Backlog

### P0 (In Progress)
- Phase 3: Risk Profile Assessment (10-15 behavioral finance questions + Visor AI integration)
- Phase 4: Tax Planning (Chapter VI deductions)
- Phase 5: Transaction Buy/Sell + Capital Gains Tax

### P1
- Recurring Transactions (monthly SIPs)
- PAN-based auto-fetch of holdings

### P2
- Backend migration: Python/FastAPI → Node.js/Express/PostgreSQL
- Enhanced micro-animations
- Push notifications for budget alerts
