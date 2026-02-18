# Visor Finance - Personal Finance Management App

## Problem Statement
Comprehensive personal finance management application for the Indian market with live market data, transaction tracking, investment monitoring, AI advisor, and security features.

## Tech Stack
- **Frontend**: React Native (Expo) with TypeScript
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **AI**: OpenAI GPT-4 via emergentintegrations

## Core Requirements
- Live Market Data (Nifty, Sensex, Gold, Silver) with GoldAPI.io
- Multi-factor authentication (PIN/Biometric)
- AES-256 field-level encryption for sensitive data
- Automated transaction import (Gmail/SMS parsing)
- Interactive Dashboard with trend analysis
- Investment tracking (Stocks, MFs, Goals)

## What's Been Implemented
### Phase 1 - Security (Partial)
- [x] PIN/Biometric app lock (SecurityContext, LockScreen, SecuritySetupScreen)
- [x] AES-256 encryption for PAN, Aadhaar (user PII)
- [x] AES-256 encryption for loan account_number
- [x] Demo user migration with encryption keys
- [ ] Extend encryption to transaction descriptions, holdings

### Phase 3/4 - Data Sources (Partial)
- [x] Gmail OAuth flow and email parsing endpoint
- [x] SMS parsing endpoint
- [ ] Verify parsed transactions save to DB correctly

### Core Features
- [x] Dashboard with frequency filters (Q/M/Y/Custom)
- [x] Transaction CRUD with categories
- [x] Investment tracking (Goals, Holdings, CAS upload)
- [x] AI Advisor chat
- [x] Live market data with GoldAPI.io (Gold/Silver) + yfinance
- [x] Books & Reports (P&L, Balance Sheet, Ledger)
- [x] Loan tracking with EMI schedules
- [x] Tax summary and capital gains

### Bug Fixes (Feb 18, 2026)
- [x] P0: Gold/Silver price accuracy - Added `import requests` for GoldAPI.io
- [x] Dashboard FAB: Replaced old quick-add modal with navigation to Transactions tab
- [x] Custom date range: Added safe date handling and improved error handling
- [x] iOS date picker bug fixed (previous session)

### New Features (Feb 18, 2026)
- [x] **Tax Planning Enhancement**: Added comprehensive Tax Deductions Browser modal
  - '+' icon on Tax Planning section header opens the browser
  - Shows all Chapter VI-A deductions (80C, 80D, 80CCD, 80E, 80G, HRA, etc.)
  - Each deduction has: Section code, one-liner, full description, eligibility, example, documents
  - 'i' icon opens detailed sub-modal with full explanation
  - Users can add deductions to their Tax Planning
  - Created: `/app/frontend/src/data/taxDeductions.ts`, `/app/frontend/src/components/TaxDeductionsModal.tsx`

- [x] **AI Contextual Awareness (Visor)**:
  - Added ScreenContext provider to track current screen
  - AI now receives screen context with every chat message
  - Visor can provide contextual responses based on which screen user is viewing
  - Updated: `ScreenContext.tsx`, `AIAdvisorChat.tsx`, backend `/api/ai/chat`

## Pending Tasks (Priority Order)
### P2
- [ ] Trend Analysis card flip animation (react-native-reanimated)

### In Progress
- [ ] Complete Data Source Integration (Gmail/SMS → save transactions to DB)
- [ ] Extend encryption to all financial endpoints
- [ ] Refactor investments.tsx into smaller components
- [ ] Split server.py into route modules (backend/routes/)

### Backlog
- [ ] Advanced AI Contextual Awareness
- [ ] Backend migration to Node.js

## Key API Endpoints
- `GET /api/market-data` - Live market data (GoldAPI.io + yfinance)
- `GET /api/dashboard/stats` - Dashboard statistics with date filtering
- `POST /api/auth/login` - Auth with encryption key handling
- `GET/POST /api/loans` - Loan CRUD with account_number encryption
- `POST /api/gmail/sync` - Gmail email parsing
- `POST /api/sms/parse` - SMS parsing

## Credentials
- Demo User: rajesh@visor.demo / Demo@123
- Demo User 2: priya@visor.demo / Demo@456
- API keys in backend/.env (GOLDAPI_KEY, Google OAuth, EMERGENT_LLM_KEY)
