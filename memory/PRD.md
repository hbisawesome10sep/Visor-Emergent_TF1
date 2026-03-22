# VISOR FINANCE — PRD v3.1

## Product Overview
Visor is an AI-powered Indian personal finance app (React Native Expo + FastAPI + MongoDB) that tracks investments, transactions, credit cards, goals, and provides AI insights.

---

## Completed Features (Cumulative)

### Core
- [x] Auth (JWT), PIN lock, demo accounts
- [x] Dashboard with Financial Health Score, Overview cards, Trend Analysis, AI Insights
- [x] Transactions: CRUD, bulk import (bank statement CSV/PDF), Custom date range filter
- [x] Investments: Holdings, SIP tracking, Goal mapping, Live prices (yfinance)
- [x] Credit Cards: Add/manage cards, statement upload, utilization tracking
- [x] AI Advisor Chat (GPT-5.2 via Emergent LLM Key)
- [x] Voice interaction (ElevenLabs TTS)
- [x] Tax Module (Phase 1-3: Old/New regime, HRA, 80C/80D)
- [x] Settings: Profile, Dark mode, Export, Bank statement upload
- [x] Expo Go QR auto-refresh webpage (`/api/expo/qr`)

### v3.1 Changes (March 22, 2026)
- [x] **Groww Stock Statement Support**: ISIN → NSE/BSE ticker resolution via yfinance. All 26 stocks resolved correctly. Tickers cached in DB after first resolution.
- [x] **Zerodha Multi-Sheet Statement Support**: Parses Equity, Mutual Funds, and Combined sheets from a single Zerodha XLSX. Stocks get `.NS` tickers, MFs get ISIN for NAV lookup. Correctly skips Combined sheet when specific sheets are available.
- [x] **Category Detection Fix**: Sheet name takes priority over statement_type for multi-sheet files (Equity sheet → Stock, MF sheet → Mutual Fund).
- [x] **MF Ticker Fix**: Mutual Funds now always use ISIN for NAV lookup (mfapi.in) instead of the fund name from Symbol column.
- [x] **ISIN Fallback for Failed Tickers**: When a stock ticker fails in yfinance (e.g., hyphenated `TATAGOLD-E`), falls back to ISIN resolution (TATAGOLD-E → INF277KA1976 → TATAGOLD.NS).
- [x] **Bank Statement Upload Fix**: Missing `detect_header_columns` import in `pdf_parsers.py` fixed.
- [x] **HDFC Bank Statement Parser Overhaul**:
  - Multi-line narration collection (was only reading first line, missing UPI ID/merchant info)
  - `clean_hdfc_description()` rewritten with 15+ transaction type handlers
  - Generic "UPI Transfer" reduced from 322 to 0 occurrences
  - Reference numbers extracted and stored for deduplication
  - Known merchant detection (50+ Indian merchants: Swiggy, Zomato, Cred, Amazon, etc.)
- [x] **Duplicate Detection Fixed**: Now uses ref_number (unique per bank txn) instead of aggressive description[:30] matching. Result: 433 of 456 imported (was ~50 before).
- [x] **Auto-Categorization Enhanced**: Added Credit Card (Cred, Slice), Entertainment (Dream11), Transport (Mumbai Metro), UPI Payment (Paytm, PhonePe), Transfer fallback for person-to-person UPI.
- [x] **Portfolio Overview Card Scaling**: Added `numberOfLines={1}` + `adjustsFontSizeToFit` to prevent text wrapping on smaller screens.
- [x] **SIP Date Picker iOS Fix**: Increased picker height from 130px to 200px to show year column on iOS.
- [x] **Flippable Investment Summary Card**: Dashboard Investment card now flips to show:
  - Asset allocation breakdown with horizontal bars
  - AI-generated daily investment insight (GPT-4o, cached 24h)
- [x] **Investment Amount Alignment**: Dashboard Overview "Investments" card now uses `portfolio_invested` (from holdings) instead of transaction-based total, aligning with Investment Summary Card.
- [x] **Bank Statement Parser Refinements (Session Mar 22, 2026)**:
  - ICICI: Complete text-extraction rewrite for interleaved blocks
  - SBI: Rewrote `clean_sbi_description` to prevent truncation
  - Union Bank: Multi-line continuation extraction (e.g., `/Salary`)
  - Axis Bank: Handle "F07 Cred", Card Charges, bypass payment gateways
  - PNB: Fixed NEFT company name indices, RTGS/cheque cleanup
  - **Canara Bank**: Fully rewrote `clean_canara_description` — RTGS/NEFT now extract actual company names via IFSC regex, IMPS shows bank+last4, cheque returns show payee, all 51 test transactions clean
  - **Bank of Baroda**: Complete rewrite of `parse_bob_pdf` — switched from text-based to TABLE extraction for ground-truth debit/credit columns (fixing 8+ wrong debit/credit classifications). Added gap-filling text pass for page-boundary entries. Rewrote `clean_bob_description` for UPI, NEFT, ACH-DR, ECS, NRP, IMPS patterns. CredClub→Cred. 25/25 transactions verified, balance matches to the penny (25,073.92).
  - **Kotak Bank**: Complete rewrite of `parse_kotak_text_format` — switched to word-position-based column extraction with **balance-delta** approach. pdfplumber's (Dr)/(Cr) suffixes were unreliable due to multi-line column alignment issues, so amounts and debit/credit are now computed from balance differences. Rewrote `clean_kotak_description` to cleanly extract UPI payees without Chq/Ref column noise. 43/43 transactions verified, balance matches exactly (11,406.54).
  - **Bank Detection Fix**: Added Canara, Union, IDBI to `detect_bank` priority patterns (was misdetecting Canara as HDFC). Added BARB0 IFSC pattern for BOB detection (was falling to Yes Bank). Added "cust.reln.no" for Kotak (bank name not present in statement text).
  - **Categorization Fix**: Fixed "cred" keyword false-positive on "credit" (Clearing Credit no longer miscategorized as Credit Card). Added IMPS/cheque/RTGS charges to Bank Charges category
- [x] **Clear All Transactions Feature** (Mar 22, 2026):
  - Backend: `DELETE /api/clear-all-transactions` — clears all transactions, credit card transactions, bank accounts, journal entries, statement hashes
  - Frontend: "Data Management" section in Settings > Banking with red "Clear All Transactions" button + confirmation dialog with detailed warning
- [x] **Credit Card Benefits Tab** (Mar 22, 2026):
  - Backend: `GET /api/credit-cards/{card_id}/benefits` (AI-powered via GPT-5.2) + `GET /api/credit-cards/all-benefits`
  - Frontend: New "Benefits" tab in Credit Cards screen with expand/collapse per card, "Fetch Benefits with AI" button, cached benefits display with category icons, AI disclaimer
  - Benefits cached in `card_benefits_cache` MongoDB collection to avoid repeated AI calls
- [x] **Dashboard Financial Year & Date Range Fix** (Mar 22, 2026):
  - 'Y' toggle now shows Indian Financial Year (April 1 – March 31) instead of calendar year. Header and date indicator display "FY 2025-26" format
  - Backend: `/api/dashboard/stats` accepts `frequency` param. When `frequency=Year` (or date span >120 days), trend data groups by month (labels: Apr, May, …) instead of weekly
  - Custom date range picker `minimumDate` changed from `userCreatedAt` (was limiting to Feb 2026) to January 1, 2020, so users can pick dates back to 2020
  - Trend Analysis X-axis shows month labels (Apr, May, Jun, …) for full FY when Y is selected

---

## Architecture

```
/app
├── backend/
│   ├── server.py
│   ├── config.py
│   ├── routes/
│   │   ├── dashboard.py, dashboard_v2.py
│   │   ├── holdings.py
│   │   ├── bank_statements.py
│   │   ├── statement_upload.py
│   │   ├── credit_cards.py
│   │   ├── ai_advisor.py
│   │   └── expo_qr.py
│   ├── services/
│   │   ├── statement_parser.py
│   │   ├── holdings_price_updater.py
│   │   └── isin_resolver.py (NEW)
│   └── parsers/
│       ├── pdf_parsers.py (REWRITTEN: HDFC parser)
│       ├── csv_excel.py
│       └── utils.py (ENHANCED: categorization)
├── frontend/
│   ├── app/(tabs)/
│   │   ├── index.tsx (Dashboard)
│   │   ├── investments.tsx (Date picker fix)
│   │   ├── transactions.tsx
│   │   └── settings.tsx
│   └── src/components/
│       ├── dashboard/
│       │   └── InvestmentSummaryCard.tsx (REWRITTEN: flippable)
│       └── investments/
│           ├── PortfolioOverviewCard.tsx (scaling fix)
│           └── UploadDropdown.tsx (DO NOT MODIFY)
└── memory/PRD.md
```

---

## Pending Issues

| # | Issue | Priority | Status |
|---|-------|----------|--------|
| 1 | iOS Document Picker crash | P0 | USER VERIFICATION PENDING |
| 2 | "Share" button cut off on Share Score screen | P1 | NOT STARTED |
| 3 | "Plan" button poorly styled in ActionableInsights | P1 | NOT STARTED |
| 4 | Misaligned "Add Goal" button on Dashboard | P2 | NOT STARTED |

---

## Upcoming Tasks

| # | Task | Priority |
|---|------|----------|
| 1 | Refactor `pdf_parsers.py` (2800+ lines → `/parsers/banks/` per-bank files) | P1 |
| 2 | FinancialHealthScore → Flip Card (detailed breakdown on back) | P1 |
| 3 | Streaming TTS for faster perceived voice response | P1 |
| 4 | Refactor investments.tsx (~1900 lines → modules) | P1 |
| 5 | Refactor index.tsx (~2000 lines → modules) | P1 |

## Future/Backlog

| # | Task | Priority |
|---|------|----------|
| 1 | Advanced Tax Module (Phase 4) | P2 |
| 2 | Gmail Integration for auto-importing bank emails | P2 |
| 3 | Voice Cloning (ElevenLabs custom persona) | P3 |
| 4 | "Share with Friends" referral feature | P3 |
| 5 | WhatsApp/Telegram bot for transaction logging | P3 |
| 6 | Multi-currency for NRI users | P3 |

---

## Key API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/dashboard/stats` | GET | Dashboard stats (accepts `frequency` param: Month/Quarter/Year/Custom; Year uses FY monthly grouping) |
| `/api/dashboard/investment-summary` | GET | Investment summary with allocation breakdown |
| `/api/dashboard/investment-insight` | GET | AI-generated investment insight (cached 24h) |
| `/api/holdings/refresh-prices` | POST | Refresh live prices (resolves ISINs for Groww stocks) |
| `/api/bank-statements/upload` | POST | Upload bank statement PDF/CSV |
| `/api/upload-statement` | POST | Upload stock/MF statement |
| `/api/expo/qr` | GET | Auto-refreshing QR code webpage |

## Credentials
- Demo: `rajesh@visor.demo` / `Demo@123`
- QR: `https://visor-finance-3.preview.emergentagent.com/api/expo/qr`
