# Visor Finance — Product Requirements Document

---

## Executive Summary

**Visor** is a comprehensive personal finance management application built for Indian users. It combines real-time market tracking, intelligent tax planning, AI-powered advisory, bank-grade security, and a **proper Indian Double-Entry Accounting System** into a single mobile experience.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Mobile App** | React Native (Expo SDK 54) |
| **Backend API** | Python FastAPI |
| **Database** | MongoDB |
| **AI Engine** | OpenAI GPT-5.2 (via Emergent Universal Key) |
| **Market Data** | yfinance, GoldAPI.io |
| **PDF Generation** | ReportLab |
| **Authentication** | JWT + Biometric |

---

## Feature Status

### Phase 1: Bank Accounts + Mode of Payment — ✅ DONE (Feb 21, 2026)
- Bank Accounts CRUD in Settings (30 Indian banks preset)
- Mode of Payment/Receipt dropdown in transaction entry
- Default bank account support

### Phase 2: Double-Entry Accounting Engine — ✅ DONE (Feb 21, 2026)
- Chart of Accounts: Personal/Real/Nominal classification
- Auto-generated journal entries from every transaction
- Journal tab in Books & Reports with search
- Individual account ledgers with running balance
- P&L and Balance Sheet from Nominal/Real/Personal accounts

### Phase 3: Ledger Enhancements — ✅ DONE (Feb 21, 2026)
- Server-side PDF export for individual ledgers (ReportLab)
- Ledger search across all accounts
- Date range filtering on ledgers

### Phase 4: Asset Auto-Journaling — ✅ DONE (Feb 21, 2026)
- Asset form has "Paid From" dropdown (Cash + bank accounts)
- Auto-creates journal entry on asset creation (Dr. Asset, Cr. Cash/Bank)
- Auto-deletes journal entries on asset deletion

### Bug Fixes Applied (Feb 21, 2026)
- Fixed `GET /api/holdings/live` (405 → 200)
- Fixed `GET /api/portfolio-rebalancing` (404 → 200)
- Fixed Tax screen duplicate auto-detected section
- Fixed auth encryption crash (`InvalidTag` → graceful fallback)

### Phase 5: Bank Statement Upload & Parsing — PENDING
- Upload PDF/CSV/Excel bank statements (max 1 year)
- Auto-add bank account from statement
- Parse transactions from statement
- Reverse bank debit/credit to user perspective
- Auto-create transactions + journal entries + ledgers

---

## API Surface

### Phase 1+2 Endpoints
- Bank Accounts: GET/POST/PUT/DELETE `/api/bank-accounts`
- Journal: GET `/api/journal`, `/api/journal/accounts`, `/api/journal/ledger/{name}`
- Updated: POST/PUT `/api/transactions` (payment_mode support)
- Updated: GET `/api/books/pnl`, `/api/books/balance-sheet`, `/api/books/ledger`

### Phase 3+4 Endpoints
- PDF Export: GET `/api/journal/ledger-pdf/{account_name}`
- Holdings Live: GET `/api/holdings/live`
- Rebalancing: GET `/api/portfolio-rebalancing`
- Updated: POST `/api/assets` (payment_mode + auto-journal)

---

## Test Results
- **Phase 3+4 (Feb 21, 2026)**: 24/24 backend tests passed
- **Phase 1+2 (Feb 21, 2026)**: 25/25 backend tests passed
- **Post-Refactor Regression (Feb 21, 2026)**: 49/49 tests passed

## Test Credentials
- **Email**: rajesh@visor.demo / **Password**: Demo@123

---

*Document last updated: February 21, 2026*
