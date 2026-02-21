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
| **PDF Parsing** | pdfplumber |
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

### Phase 5: Bank Statement Upload & Parsing — ✅ DONE (Feb 21, 2026)
- Upload PDF/CSV/Excel bank statements (max 10MB)
- Auto-add bank account from statement if not exists
- Parse transactions from statement with column auto-detection
- **Perspective reversal**: bank credit → user income, bank debit → user expense
- Auto-categorization based on keywords (ZOMATO → Food & Dining, IRCTC → Travel, etc.)
- Auto-create transactions + journal entries
- Duplicate detection to prevent re-imports
- Frontend UI in Settings → Banking tab with file picker and upload modal

### Bug Fixes Applied (Feb 21, 2026)
- Fixed `GET /api/holdings/live` (405 → 200)
- Fixed `GET /api/portfolio-rebalancing` (404 → 200)
- Fixed Tax screen duplicate auto-detected section
- Fixed auth encryption crash (`InvalidTag` → graceful fallback)

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

### Phase 5 Endpoints
- Bank Statement Upload: POST `/api/bank-statements/upload` (multipart/form-data)
- Import History: GET `/api/bank-statements/history`

---

## Test Results
- **Phase 5 (Feb 21, 2026)**: 12/13 backend tests passed, Frontend UI verified
- **Phase 3+4 (Feb 21, 2026)**: 24/24 backend tests passed
- **Phase 1+2 (Feb 21, 2026)**: 25/25 backend tests passed
- **Post-Refactor Regression (Feb 21, 2026)**: 49/49 tests passed

## Test Credentials
- **Email**: rajesh@visor.demo / **Password**: Demo@123

---

## Upcoming/Future Tasks
1. **Frontend for Bank Statement Upload Enhancements** — P2
   - Add file drag-and-drop support (web)
   - Show import progress for large files
   
2. **Frontend Component Refactoring** — P2
   - Break down large screen components (tax.tsx, investments.tsx)
   
3. **Google OAuth Fix** — P2 (Blocked)
   - Fix `redirect_uri_mismatch` for Gmail integration

4. **Always-Visible Search Bar on Transactions** — P2
   - Make search bar always visible instead of toggle

---

*Document last updated: February 21, 2026*
