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
| **Authentication** | JWT + Biometric |
| **Deployment** | Expo Tunnel (Preview), Expo Go (Mobile) |

---

## Code Architecture

```
/app
├── backend
│   ├── auth.py, config.py, database.py, models.py, seed_data.py
│   ├── server.py (Modular loader - 107 lines)
│   ├── routes/
│   │   ├── auth.py, transactions.py, holdings.py
│   │   ├── bank_accounts.py    ← NEW (Phase 1)
│   │   ├── journal.py          ← NEW (Phase 2)
│   │   ├── bookkeeping.py      ← UPDATED (Double-entry P&L, BS)
│   │   ├── dashboard.py, tax.py, ai_chat.py, ai_advisor.py
│   │   ├── market_data.py, goals.py, loans.py, assets.py
│   │   ├── portfolio.py, risk_profile.py, recurring.py, gmail.py
│   │   └── (other routes...)
│   └── tests/
│       └── test_phase1_2_bookkeeping.py
└── frontend
    └── app/(tabs)/
        ├── transactions.tsx  ← UPDATED (Mode of Payment dropdown)
        ├── settings.tsx      ← UPDATED (Banking tab)
        └── books.tsx         ← UPDATED (Journal tab, search, individual ledgers)
```

---

## Feature Status

### Phase 1: Bank Accounts + Mode of Payment — ✅ DONE (Feb 21, 2026)
- Bank Accounts CRUD in Settings (30 Indian banks preset)
- Add/Edit/Delete individual accounts, Delete All
- Set default bank account
- Account number encryption at rest
- Mode of Payment/Receipt dropdown in transaction entry
- Defaults to user's default bank or Cash
- Transaction search includes payment_account_name

### Phase 2: Double-Entry Accounting Engine — ✅ DONE (Feb 21, 2026)
- Chart of Accounts: Personal/Real/Nominal classification
- Auto-generated journal entries from every transaction
- Correct debit/credit per Indian accounting rules:
  - Income: Dr. Cash/Bank, Cr. Category (Nominal/Income)
  - Expense: Dr. Category (Nominal/Expense), Cr. Cash/Bank
  - Investment: Dr. Category (Real/Asset), Cr. Cash/Bank
- Journal tab in Books & Reports with search
- Individual account ledgers with running balance
- Ledger export (CSV)
- P&L Statement from Nominal accounts (Ind AS)
- Balance Sheet from Real + Personal accounts
- General Ledger from journal entries

### Phase 3: Individual Ledger Enhancements — PENDING
- PDF export via server-side generation
- Alpha-numeric search bar in Transactions screen
- Date range filters (Current FY, Previous FY, Custom)

### Phase 4: P&L + Balance Sheet Polish — PENDING
- Asset/Liability auto-journaling (adding asset/liability auto-creates journal + ledger)
- Bank account selection when adding Asset/Liability

### Phase 5: Bank Statement Upload & Parsing — PENDING
- Upload PDF/CSV/Excel bank statements (max 1 year)
- Auto-add bank account from statement
- Parse all transactions from statement
- Reverse bank's debit/credit to user's perspective
- Auto-create transactions + journal entries + ledgers

---

## DB Collections

| Collection | Purpose |
|-----------|---------|
| users | User accounts with encrypted PII |
| transactions | All financial transactions (income/expense/investment) with payment_mode |
| bank_accounts | User's bank accounts (encrypted account numbers) |
| journal_entries | Double-entry journal entries linked to transactions |
| holdings | Investment holdings |
| goals | Financial goals |
| loans | Loan tracking with EMI schedules |
| fixed_assets | Fixed asset register |
| ai_chat_messages | AI advisor conversations |
| market_data | Cached market prices |

---

## API Surface

### New Endpoints (Phase 1+2)
- `GET /api/bank-accounts` — List user's bank accounts
- `POST /api/bank-accounts` — Create bank account
- `PUT /api/bank-accounts/{id}` — Update bank account
- `DELETE /api/bank-accounts/{id}` — Delete bank account
- `DELETE /api/bank-accounts` — Delete all bank accounts
- `PUT /api/bank-accounts/{id}/set-default` — Set default
- `GET /api/bank-accounts/banks-list` — 30 Indian banks
- `GET /api/journal` — Journal entries with search/filter/pagination
- `GET /api/journal/accounts` — All unique accounts with totals
- `GET /api/journal/ledger/{account_name}` — Individual ledger

### Updated Endpoints
- `POST/PUT /api/transactions` — Now accepts payment_mode, payment_account_name
- `GET /api/transactions?search=` — Now searches payment_account_name too
- `GET /api/books/pnl` — Now derived from journal entries
- `GET /api/books/balance-sheet` — Now derived from journal entries
- `GET /api/books/ledger` — Now from journal entries with search

---

## Test Results
- **Phase 1+2 (Feb 21, 2026)**: 25/25 backend tests passed, frontend verified
- **Post-Refactor Regression (Feb 21, 2026)**: 49/49 backend tests passed

---

## Test Credentials
- **Email**: rajesh@visor.demo
- **Password**: Demo@123

---

*Document last updated: February 21, 2026*
