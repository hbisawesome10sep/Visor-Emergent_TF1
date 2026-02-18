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
- [x] AI Advisor chat with contextual awareness
- [x] Live market data with GoldAPI.io (Gold/Silver) + yfinance
- [x] Books & Reports (P&L, Balance Sheet, Ledger)
- [x] Loan tracking with EMI schedules
- [x] Tax summary and capital gains
- [x] Trend Analysis card with flip animation

### Session Feb 18, 2026 - COMPLETED ✅

#### Tax Planning Enhancement
- [x] **Tax Deductions Browser Modal**: Comprehensive modal with 25+ Chapter VI-A deductions
  - Category filters (Popular, Investments, Insurance, Savings, Housing, Medical, Donations)
  - Horizontal pill-style filter buttons (fixed styling)
  - Search functionality
  - Detail modal with one-liner, full description, eligibility, example, documents
  - Files: `/app/frontend/src/data/taxDeductions.ts`, `/app/frontend/src/components/TaxDeductionsModal.tsx`

- [x] **User Tax Deductions Backend API**:
  - `GET /api/user-tax-deductions` - Get user's selected deductions
  - `POST /api/user-tax-deductions` - Add new deduction to planning
  - `PUT /api/user-tax-deductions/{id}` - Update invested amount
  - `DELETE /api/user-tax-deductions/{id}` - Remove deduction

- [x] **Tax Planning Section Enhancement**:
  - '+' icon on Tax Planning header opens deductions browser
  - "Your Selected Deductions" section shows user-added deductions with edit/delete buttons
  - Progress bar showing invested vs limit
  - Edit modal to update invested amount
  - **Smart Auto-detection**: Only shows "Auto-detected from Transactions" when qualifying transactions exist (hides empty ₹0 sections)

- [x] **AI Contextual Awareness (Visor)**:
  - ScreenContext provider to track current screen
  - AI receives screen context with every chat message
  - Contextual responses based on user's current view
  - Files: `ScreenContext.tsx`, `AIAdvisorChat.tsx`, backend `/api/ai/chat`

- [x] **Trend Analysis Card**: Flip animation working

## Pending Tasks (Priority Order)

### In Progress
- [ ] Complete Data Source Integration (Gmail/SMS → save transactions to DB)
- [ ] Extend encryption to all financial endpoints

### Backlog
- [ ] Refactor investments.tsx into smaller components
- [ ] Split server.py into route modules (backend/routes/)
- [ ] Backend migration to Node.js

## Key API Endpoints
- `GET /api/market-data` - Live market data (GoldAPI.io + yfinance)
- `GET /api/dashboard/stats` - Dashboard statistics with date filtering
- `POST /api/auth/login` - Auth with encryption key handling
- `GET/POST /api/loans` - Loan CRUD with account_number encryption
- `POST /api/gmail/sync` - Gmail email parsing
- `POST /api/sms/parse` - SMS parsing
- `GET/POST/PUT/DELETE /api/user-tax-deductions` - User tax deduction management
- `POST /api/ai/chat` - AI advisor with screen context

## Credentials
- Demo User: rajesh@visor.demo / Demo@123
- Demo User 2: priya@visor.demo / Demo@456
- API keys in backend/.env (GOLDAPI_KEY, Google OAuth, EMERGENT_LLM_KEY)

## Files Modified This Session
- `/app/frontend/src/data/taxDeductions.ts` - NEW: Comprehensive tax deductions data (25+ deductions)
- `/app/frontend/src/components/TaxDeductionsModal.tsx` - NEW: Tax deductions browser modal
- `/app/frontend/src/context/ScreenContext.tsx` - NEW: Screen tracking for AI awareness
- `/app/frontend/app/(tabs)/investments.tsx` - MODIFIED: Tax Planning section with smart auto-detection
- `/app/frontend/app/(tabs)/index.tsx` - MODIFIED: Added ScreenContext
- `/app/frontend/app/(tabs)/transactions.tsx` - MODIFIED: Added ScreenContext
- `/app/frontend/app/_layout.tsx` - MODIFIED: Added ScreenProvider
- `/app/frontend/src/components/AIAdvisorChat.tsx` - MODIFIED: Send screen context
- `/app/backend/server.py` - MODIFIED: User tax deductions API endpoints + uuid4 import fix
