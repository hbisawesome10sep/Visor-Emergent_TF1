# Visor Finance - Personal Finance Management App

## Original Problem Statement
Build a comprehensive personal finance management application for Indian users with live market data, investment tracking, tax planning, AI advisor, and automated transaction management.

## Core Architecture
- **Frontend**: React Native (Expo) mobile app
- **Backend**: Python FastAPI
- **Database**: MongoDB
- **AI**: OpenAI GPT-4 (via Emergent key)
- **Market Data**: yfinance, GoldAPI.io
- **Auth**: JWT-based with biometric support

## What's Been Implemented

### Phase 1: Core Features (Complete)
- User authentication (JWT + biometric)
- Dashboard with financial health score, income/expense/investment overview
- Transaction management (CRUD, categories, search)
- Investment tracking with live market data (Nifty, Sensex, Gold, Silver)
- Portfolio overview with gain/loss tracking
- Holdings breakdown (stocks, mutual funds, ETFs)
- Asset allocation pie chart
- Risk profiling and strategy recommendations
- SIP/recurring investment tracking
- Financial goals tracking
- AI Advisor "Visor" with contextual awareness
- Trend analysis with flippable graphical chart
- Books & Reports (P&L, Balance Sheet, etc.)
- Settings screen with profile management
- Dark/Light theme support

### Phase 2: Tax Hub (Feb 2026) (Complete)
- **New Tax tab** in bottom navigation (replaced Settings tab)
- **Settings moved** to gear icon on Dashboard top-right
- **Tax Planning section** (moved from Investments):
  - Chapter VI-A deductions browser modal
  - User-added deductions with progress tracking
  - Auto-detected deductions from transactions
  - Tax saved estimates (20%/30% slab)
- **Capital Gains/Loss section** (moved from Investments):
  - STCG/LTCG breakdown
  - Individual gain/loss items
  - Tax liability per item
- **Income Tax Calculator** (NEW):
  - Old Regime vs New Regime toggle
  - FY/AY selector (FY 2025-26, 2024-25, 2023-24)
  - Income summary (salary + other)
  - Deductions breakdown per regime
  - Slab-wise tax computation
  - Rebate u/s 87A calculation
  - Surcharge and 4% cess
  - Capital gains tax addition
  - Total tax liability
  - Effective tax rate
  - Side-by-side regime comparison
  - Savings recommendation
- **AI Contextual Awareness** updated for Tax screen

### Tax Rules Implemented (FY 2025-26 / AY 2026-27)
- **Old Regime**: ₹0-2.5L@0%, 2.5-5L@5%, 5-10L@20%, 10L+@30%
  - Standard Deduction: ₹50,000
  - Rebate u/s 87A: ≤₹5L → ₹12,500
  - Full Chapter VI-A deductions
- **New Regime (Budget 2025)**: ₹0-4L@0%, 4-8L@5%, 8-12L@10%, 12-16L@15%, 16-20L@20%, 20-24L@25%, 24L+@30%
  - Standard Deduction: ₹75,000
  - Rebate u/s 87A: ≤₹12L → ₹60,000
  - Limited deductions (NPS only)
- **Capital Gains**: STCG equity 20%, LTCG equity 12.5% (above ₹1.25L)
- **Surcharge**: Progressive rates 10%-37%
- **Cess**: 4% Health & Education

## Key API Endpoints
- `POST /api/auth/login` - Authentication
- `GET /api/dashboard/stats` - Dashboard statistics
- `GET /api/transactions` - Fetch transactions
- `GET /api/holdings/live` - Live holdings data
- `GET /api/market-data` - Indian market indices
- `GET /api/portfolio-overview` - Portfolio summary
- `GET /api/tax-summary` - Tax deduction summary
- `GET /api/capital-gains` - Capital gains breakdown
- `GET /api/tax-calculator?fy=2025-26` - **NEW** Income tax calculator
- `GET/POST/PUT/DELETE /api/user-tax-deductions` - User tax deductions CRUD
- `POST /api/ai/chat` - AI advisor with screen context
- `GET /api/goals` - Financial goals
- `GET /api/risk-profile` - Risk assessment

## Key Files
- `/app/backend/server.py` - Main backend (all APIs)
- `/app/frontend/app/(tabs)/tax.tsx` - **NEW** Tax screen
- `/app/frontend/app/(tabs)/index.tsx` - Dashboard
- `/app/frontend/app/(tabs)/investments.tsx` - Investments (tax sections removed)
- `/app/frontend/app/(tabs)/transactions.tsx` - Transactions
- `/app/frontend/app/(tabs)/settings.tsx` - Settings (hidden from tab bar)
- `/app/frontend/app/(tabs)/_layout.tsx` - Tab navigation
- `/app/frontend/src/components/TaxDeductionsModal.tsx` - Deductions browser
- `/app/frontend/src/context/ScreenContext.tsx` - AI screen awareness
- `/app/frontend/src/data/taxDeductions.ts` - Tax deduction data

## Prioritized Backlog

### P0 (High Priority)
- Custom Date Range bug on Dashboard (recurring issue)
- Data Source Integration (Phase 3/4) - Gmail/SMS auto-import
- Complete Data Encryption for all PII

### P1 (Medium Priority)
- Verify AI Contextual Awareness working on all screens
- Refactor server.py into route modules
- Refactor investments.tsx into smaller components

### P2 (Low Priority / Future)
- Backend migration to Node.js
- Advanced investment analytics
- Budget planning features

## 3rd Party Integrations
- GoldAPI.io (gold/silver prices)
- yfinance (stock/index data)
- OpenAI GPT-4 (AI advisor)
- google-api-python-client (Gmail)
- expo-local-authentication (biometric)
- pdfplumber (PDF parsing)

## Test Credentials
- Email: rajesh@visor.demo
- Password: Demo@123
