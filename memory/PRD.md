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

## Code Architecture (Post-Refactoring)

```
/app
├── backend
│   ├── auth.py              # Auth middleware/utilities
│   ├── config.py            # App configuration
│   ├── database.py          # MongoDB connection
│   ├── models.py            # Data models
│   ├── seed_data.py         # Demo data seeding
│   ├── server.py            # Modular FastAPI server (107 lines)
│   ├── routes/
│   │   ├── ai_advisor.py
│   │   ├── ai_chat.py
│   │   ├── assets.py
│   │   ├── auth.py
│   │   ├── bookkeeping.py
│   │   ├── dashboard.py
│   │   ├── gmail.py
│   │   ├── goals.py
│   │   ├── holdings.py
│   │   ├── loans.py
│   │   ├── market_data.py
│   │   ├── portfolio.py
│   │   ├── recurring.py
│   │   ├── risk_profile.py
│   │   ├── tax.py
│   │   └── transactions.py
│   └── tests/
│       ├── test_modular_refactor.py
│       └── test_full_regression.py
└── frontend
    └── ... (React Native / Expo)
```

---

## Feature Inventory

### 1. Onboarding & Authentication — ✅ DONE

| Feature | Status |
|---------|--------|
| Introduction/Landing page with feature showcase | Done |
| Email + Password registration | Done |
| JWT-based login with token persistence | Done |
| 4-digit PIN setup (per-user, persistent across sessions) | Done |
| Biometric authentication (Fingerprint / Face ID) | Done |
| Auto-lock after 5 minutes of inactivity | Done |
| Security state persisted per user account | Done |

### 2. Dashboard — ✅ DONE

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

### 3. Transaction Management — ✅ DONE

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
| Tax Eligibility Hint | Done |

### 4. Investment Tracking — ✅ DONE

| Feature | Status |
|---------|--------|
| Live Indian Markets — Nifty 50, SENSEX, Nifty Bank, Gold, Silver | Done |
| Force-refresh on every screen open | Done |
| Portfolio overview with total value, gain/loss, returns % | Done |
| Holdings breakdown with live P&L | Done |
| Asset allocation pie chart | Done |
| Risk profiling questionnaire | Done |
| Portfolio rebalancing suggestions | Done |
| SIP/Recurring investment tracker | Done |
| Financial Goals with targets and deadlines | Done |
| Add/Edit holdings | Done |

### 5. Tax Hub — ✅ DONE

| Feature | Status |
|---------|--------|
| Chapter VI-A deductions browser | Done |
| Auto-Detected Deductions from Transactions | Done |
| Capital Gains (STCG/LTCG) | Done |
| Income Tax Calculator (Old vs New Regime) | Done |
| FY-aware filtering | Done |

### 6. AI Financial Advisor — "Visor" — ✅ DONE

| Feature | Status |
|---------|--------|
| Conversational AI chat interface | Done |
| Screen-context awareness | Done |
| Live price lookup | Done |
| Indian commodity prices | Done |
| Conversational memory | Done |
| Individual message deletion | Done |
| Finance-only guardrails | Done |
| Powered by OpenAI GPT-5.2 | Done |

### 7. Books & Reports — ✅ DONE

| Feature | Status |
|---------|--------|
| General Ledger, P&L, Balance Sheet | Done |
| Budget Tracker, Asset Register, Loan Tracker | Done |
| Export to Excel, PDF, CSV, JSON | Done |

### 8. Settings — ✅ DONE
### 9. Data Security & Encryption — ✅ DONE
### 10. Cross-Platform Polish — ✅ DONE

---

## API Surface (All routes prefixed with /api)

All endpoints defined in modular route files under `/app/backend/routes/`.
**Regression tested: 49/49 tests passed (100%) — Feb 21, 2026**

---

## Roadmap & Backlog

### P0 — Completed
- ~~Backend Monolith Refactoring~~ ✅ (Feb 21, 2026)
- ~~Full Regression Test~~ ✅ (Feb 21, 2026 — 49/49 passed)
- ~~Field-Level Encryption~~ ✅

### P1 — Pending
- Google OAuth `redirect_uri_mismatch` fix for Gmail auto-import
- Frontend component refactoring (tax.tsx, investments.tsx)
- User's upcoming "bigger task" (TBD)

### P2 — Future
- Backend migration from Python/FastAPI to Node.js
- Enhanced auto-deduction engine
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
| OpenAI GPT-5.2 | AI financial advisor (via Emergent Key) | Active |
| google-api-python-client | Gmail transaction parsing | Blocked (OAuth error) |
| expo-local-authentication | Biometric auth | Active |
| pdfplumber | Bank statement PDF parsing | Partial |

---

## Test Credentials
- **Email**: rajesh@visor.demo
- **Password**: Demo@123

---

*Document last updated: February 21, 2026*
