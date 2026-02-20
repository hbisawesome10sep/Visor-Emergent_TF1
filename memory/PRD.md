# Visor Finance — Product Requirements Document

---

## Executive Summary

**Visor** is a comprehensive personal finance management application built for Indian users. It combines real-time market tracking, intelligent tax planning, AI-powered advisory, and bank-grade security into a single mobile experience. The app empowers users to track every rupee, plan investments, calculate taxes across regimes, and make data-driven financial decisions — all from their phone.

---

## Vision & Problem Statement

Indian individuals juggle multiple financial instruments — savings accounts, PPF, ELSS, NPS, insurance, loans, and more — across different platforms with no unified view. Tax planning is typically an end-of-year scramble. Visor solves this by providing a **single, intelligent dashboard** that tracks all finances, auto-detects tax-saving opportunities from daily transactions, and offers AI-powered contextual advice.

---

## Target Users

- Salaried professionals (25-45 age group) in India
- Individuals managing personal investments and tax planning
- Users who want a unified view of income, expenses, investments, and tax liability
- First-time investors seeking guided financial planning

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Mobile App** | React Native (Expo SDK 54) |
| **Backend API** | Python FastAPI |
| **Database** | MongoDB |
| **AI Engine** | OpenAI GPT-5.2 (via Emergent Universal Key) |
| **Market Data** | yfinance (Equities/Indices), GoldAPI.io (Precious Metals) |
| **Authentication** | JWT + Biometric (PIN + Fingerprint/Face ID) |
| **File System** | expo-file-system (Export/Share) |
| **Deployment** | Expo Tunnel (Preview), Expo Go (Mobile) |

---

## Feature Inventory

### 1. Onboarding & Authentication

| Feature | Status |
|---------|--------|
| Introduction/Landing page with feature showcase | Done |
| Email + Password registration | Done |
| JWT-based login with token persistence | Done |
| 4-digit PIN setup (per-user, persistent across sessions) | Done |
| Biometric authentication (Fingerprint / Face ID) | Done |
| Auto-lock after 5 minutes of inactivity | Done |
| Security state persisted per user account | Done |

**Flow**: Landing Page → Sign Up / Log In → PIN + Biometric Setup (first time only) → Dashboard

---

### 2. Dashboard

| Feature | Status |
|---------|--------|
| Financial Health Score | Done |
| Income / Expense / Investment summary cards | Done |
| Net worth calculation | Done |
| Date range filtering (Week, Month, 3M, 6M, Year, Custom) | Done |
| Custom date range with native calendar picker (iOS + Android) | Done |
| Trend Analysis — flippable graphical line chart | Done |
| Quick access to Settings via gear icon (top-right) | Done |
| Dark / Light theme toggle | Done |

---

### 3. Transaction Management

| Feature | Status |
|---------|--------|
| Full CRUD (Create, Read, Update, Delete) | Done |
| Categories: 15+ expense, 8+ income, 10+ investment types | Done |
| Quick-fill description suggestions | Done |
| Split transaction support | Done |
| Recurring transaction toggle (Daily/Weekly/Monthly/Yearly) | Done |
| Notes field | Done |
| Date selection via native calendar picker | Done |
| Buy/Sell mode for investment transactions | Done |
| **Tax Eligibility Hint** — real-time banner showing if a transaction qualifies for tax deduction (e.g., "PF Contribution → Section 80C") | Done |

---

### 4. Investment Tracking

| Feature | Status |
|---------|--------|
| **Live Indian Markets** — Nifty 50, SENSEX, Nifty Bank, Gold (10g), Silver (1Kg) | Done |
| Force-refresh on every screen open (always live prices) | Done |
| Portfolio overview with total value, gain/loss, and returns % | Done |
| Holdings breakdown — individual stocks, MFs, ETFs with live P&L | Done |
| Asset allocation pie chart | Done |
| Risk profiling questionnaire with strategy recommendations | Done |
| Portfolio rebalancing suggestions | Done |
| SIP/Recurring investment tracker | Done |
| Financial Goals — set targets, track progress, deadline with calendar | Done |
| Add/Edit holdings with buy date, units, price per unit | Done |

---

### 5. Tax Hub (Dedicated Screen)

The Tax screen is the centrepiece intelligence layer of Visor. It operates on an **Assessment Year (A.Y.) / Financial Year (F.Y.)** basis.

#### 5a. Tax Planning

| Feature | Status |
|---------|--------|
| Chapter VI-A deductions browser (80C, 80D, 80E, 80G, etc.) | Done |
| Searchable deduction catalog with full descriptions, limits, eligibility, examples, and required documents | Done |
| User-added deductions with invested amount and progress bars | Done |
| **Auto-Detected Deductions from Transactions** | Done |
| Tax saved estimates (20%/30% slab) | Done |
| FY-aware filtering | Done |

#### 5b. Auto Tax Deduction Detection Engine

| Capability | Detail |
|------------|--------|
| Detection method | Category-based + Description/Notes keyword analysis |
| Supported sections | 80C, 80D, 80CCD(1B), 80E, 80G, 80GG, 80TTA, 24(b) |
| Detection examples | PPF → 80C, Health Insurance → 80D, "Education loan" → 80E, "Donation to PM CARES" → 80G |
| FY validation | Only transactions dated within the selected FY are considered |
| Cascade behavior | Create txn → auto-create deduction; Delete txn → auto-remove deduction; Edit txn → re-evaluate |
| User override | Edit auto-detected amount or dismiss entirely |
| Priority logic | Description keywords take priority over generic category mapping |

#### 5c. Capital Gains

| Feature | Status |
|---------|--------|
| STCG / LTCG breakdown | Done |
| Individual gain/loss items with holding period | Done |
| Tax liability per item (STCG equity 20%, LTCG equity 12.5% above 1.25L) | Done |

#### 5d. Income Tax Calculator

| Feature | Status |
|---------|--------|
| Old Regime vs New Regime toggle | Done |
| FY/AY selector (2025-26, 2024-25, 2023-24) | Done |
| Income summary (salary + other sources) | Done |
| Deductions breakdown per regime | Done |
| Slab-wise tax computation | Done |
| Rebate u/s 87A | Done |
| Surcharge (progressive 10%-37%) | Done |
| Health & Education Cess (4%) | Done |
| Capital gains tax addition | Done |
| Effective tax rate | Done |
| Side-by-side regime comparison with savings recommendation | Done |

**Tax Slabs Implemented**:
- **Old Regime**: 0-2.5L@0%, 2.5-5L@5%, 5-10L@20%, 10L+@30% | Std Deduction: 50K | Rebate: up to 5L income → 12,500
- **New Regime (Budget 2025)**: 0-4L@0%, 4-8L@5%, 8-12L@10%, 12-16L@15%, 16-20L@20%, 20-24L@25%, 24L+@30% | Std Deduction: 75K | Rebate: up to 12L income → 60,000

---

### 6. AI Financial Advisor — "Visor"

| Feature | Status |
|---------|--------|
| Conversational AI chat interface | Done |
| Screen-context awareness (Dashboard, Transactions, Investments, Tax, etc.) | Done |
| Personalised advice based on user's actual financial data | Done |
| Tax planning guidance on the Tax screen | Done |
| **STRICT finance-only guardrails** — refuses all non-finance queries (medical, recipes, etc.) | Done |
| **Live price lookup** — real-time stock, MF, ETF, index, and commodity prices via yfinance | Done |
| **Indian commodity prices** — Gold (per 10g) and Silver (per Kg) from app's GoldAPI data, not COMEX USD | Done |
| **Conversational memory** — last 10 messages included as context for follow-up questions | Done |
| **Individual message deletion** — long-press (Pressable) on any message to delete it, server-synced IDs | Done |
| **Professional AI identity** — never reveals internal systems, feeds, APIs, or ticker symbols | Done |
| **Stop-words filter** — prevents common English words from being treated as stock tickers | Done |
| Coverage: 70+ Indian stocks, Nifty/SENSEX/Bank Nifty indices, Gold, Silver, Copper, Crude, ETFs | Done |
| Powered by OpenAI GPT-5.2 | Done |

---

### 7. Books & Reports

| Feature | Status |
|---------|--------|
| General Ledger | Done |
| Profit & Loss Statement | Done |
| Balance Sheet | Done |
| Budget Tracker | Done |
| Asset Register | Done |
| Loan Tracker | Done |
| Custom date range filtering | Done |
| **Export to Excel (.xlsx)** | Done |
| **Export to PDF** | Done |
| **Export to CSV** (client-side) | Done |
| **Export to JSON** (client-side) | Done |

---

### 8. Settings

| Feature | Status |
|---------|--------|
| Profile management | Done |
| PIN change | Done |
| Biometric toggle | Done |
| Security reset | Done |
| Accessed via gear icon on Dashboard | Done |

---

### 9. Data Security & Encryption

| Feature | Status |
|---------|--------|
| AES-256-GCM field-level encryption for all PII | Done |
| Per-user Data Encryption Keys (DEK) | Done |
| Encrypted fields: `full_name`, `dob`, `pan`, `aadhaar` | Done |
| Encrypted fields: loan `account_number` | Done |
| Gmail OAuth tokens encrypted at rest (`access_token`, `refresh_token`, `client_secret`) | Done |
| Universal migration — encrypts ALL existing users on startup | Done |
| Auto-decrypt in `get_current_user` middleware for seamless downstream use | Done |
| `is_encrypted` flag in profile response | Done |

---

### 9. Cross-Platform Polish

| Item | Status |
|------|--------|
| Dark mode + Light mode with full theme consistency | Done |
| iOS DateTimePicker — inline spinner with themeVariant inside modals | Done |
| Android DateTimePicker — native dialog popup | Done |
| iOS nested modal fix (TaxDeductionsModal detail view) | Done |
| expo-file-system migration to legacy API for exports | Done |

---

## API Surface (25+ Endpoints)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/auth/login` | POST | User authentication |
| `/api/auth/register` | POST | User registration |
| `/api/dashboard/stats` | GET | Dashboard summary |
| `/api/transactions` | GET/POST | List & create transactions |
| `/api/transactions/{id}` | PUT/DELETE | Update & delete transactions |
| `/api/holdings/live` | GET | Live holdings with current prices |
| `/api/market-data` | GET | Indian market indices (force refresh supported) |
| `/api/portfolio-overview` | GET | Portfolio value & returns |
| `/api/portfolio-rebalancing` | GET | Rebalancing suggestions |
| `/api/goals` | GET/POST | Financial goals |
| `/api/risk-profile` | GET/POST | Risk assessment |
| `/api/recurring` | GET | Recurring transactions |
| `/api/tax-summary` | GET | Tax deduction summary |
| `/api/capital-gains` | GET | Capital gains breakdown |
| `/api/tax-calculator` | GET | Full tax computation (Old + New regime) |
| `/api/user-tax-deductions` | GET/POST/PUT/DELETE | Manual tax deductions CRUD |
| `/api/auto-tax-deductions` | GET | Auto-detected deductions (FY-filtered) |
| `/api/auto-tax-deductions/{id}` | PUT/DELETE | Edit/dismiss auto deductions |
| `/api/calculate-tax` | POST | Standalone tax calculation |
| `/api/ai/chat` | POST | AI advisor conversation |
| `/api/books/export/{report}/{format}` | GET | Export reports (Excel/PDF) |

---

## App Navigation

```
Landing Page (intro)
  ├── Log In → Dashboard
  └── Sign Up → Security Setup → Dashboard

Bottom Tab Navigation:
  ├── Dashboard    (Home, Stats, Charts, Settings gear)
  ├── Transactions (CRUD, Categories, Tax Hints)
  ├── Insights     (Analytics, Trends)
  ├── Invest       (Markets, Holdings, Goals, SIPs)
  └── Tax          (Planning, Capital Gains, Calculator)

Other Screens:
  ├── Settings     (via gear icon on Dashboard)
  ├── Books & Reports (via Insights or direct)
  └── AI Visor     (floating chat, context-aware)
```

---

## Data Model (MongoDB Collections)

| Collection | Purpose |
|------------|---------|
| `users` | User accounts, profile, encrypted PII |
| `transactions` | All income/expense/investment entries |
| `holdings` | Investment holdings with buy details |
| `goals` | Financial targets with deadlines |
| `market_data` | Cached live market prices |
| `user_tax_deductions` | Manually added tax deductions |
| `auto_tax_deductions` | Auto-detected deductions linked to transactions |
| `risk_profiles` | User risk assessment results |
| `assets` | Physical asset register |
| `loans` | Loan tracking entries |

---

## Roadmap & Backlog

### P0 — High Priority (Next Up)
- **Data Source Integration**: Auto-import transactions by parsing Gmail and SMS messages
- **Field-Level Encryption**: Encrypt all PII (Aadhaar, PAN, account numbers) at rest

### P1 — Medium Priority
- Refactor `server.py` into modular route files (`routes/transactions.py`, `routes/tax.py`, `routes/ai.py`)
- Break down large frontend files into smaller components
- Enhanced AI advisor with portfolio-specific recommendations

### P2 — Low Priority / Future
- Backend migration from Python/FastAPI to Node.js
- Budget planning and forecasting
- Multi-currency support
- Family/household financial management
- Bank statement PDF auto-parser
- Push notifications for bill reminders and market alerts

---

## 3rd Party Integrations

| Service | Purpose | Status |
|---------|---------|--------|
| yfinance | Nifty 50, SENSEX, Nifty Bank live prices | Active |
| GoldAPI.io | Gold & Silver live prices | Active |
| OpenAI GPT-4 | AI financial advisor | Active |
| google-api-python-client | Gmail transaction parsing | Partial |
| expo-local-authentication | Biometric auth (Fingerprint/Face ID) | Active |
| pdfplumber | Bank statement PDF parsing | Partial |
| @react-native-community/datetimepicker | Native date selection | Active |

---

## Test Credentials
- **Email**: rajesh@visor.demo
- **Password**: Demo@123

---

*Document last updated: February 20, 2026*
