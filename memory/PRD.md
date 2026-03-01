# VISOR FINANCE — Product Requirements Document
**Version**: 2.0.1 | **Last Updated**: March 1, 2026 | **Platform**: iOS · Android · Web

---

## 1. WHAT IS VISOR?

**Visor Finance** is a comprehensive personal finance management app built specifically for Indians. It automates bookkeeping (Indian double-entry standards), imports bank & credit card statements from 15+ banks, tracks investments, optimises income tax, and delivers AI-powered financial insights — all in one app.

### Problems It Solves
| Problem | Visor's Solution |
|---------|-----------------|
| No visibility into spending | Categorised transactions from every bank & CC |
| Multiple fragmented apps | One app: banking + investing + taxes + books |
| No proper books of accounts | Automated double-entry Journal, Ledger, P&L, Balance Sheet |
| Missed tax savings | Auto-detection of 80C, 80D deductions with smart alerts |
| Credit card debt blind spot | Dedicated CC management with liability-based bookkeeping |
| EMI/SIP tracking gaps | Auto-detection + tracker dashboard |
| No financial guidance | GPT-powered AI advisor embedded in app |

---

## 2. CURRENT BUILD STATUS

| Area | Status | Version Introduced |
|------|--------|-------------------|
| Core Bookkeeping (Double Entry) | ✅ Complete | v1.0 |
| Transaction Import (Bank Statements) | ✅ Complete | v1.0 |
| Investments & Portfolio | ✅ Complete | v1.0 |
| Tax Planning | ✅ Complete | v1.1 |
| AI Advisor Chat | ✅ Complete | v1.1 |
| PDF/Excel Exports | ✅ Complete | v1.2 |
| Insights Overhaul (Monthly Trends + Smart Alerts) | ✅ Complete | v1.2 |
| Credit Card Management (CRUD + Transactions) | ✅ Complete | v1.3 |
| CC Statement Parser (separate from bank parser) | ✅ Complete | v2.0 |
| CC Settings Tab (separate from Banking) | ✅ Complete | v2.0 |
| CC Double-Entry Bookkeeping (liability-based) | ✅ Complete | v2.0 |
| Flagged Transactions (EMI/SIP review) | ✅ Complete | v1.3 |
| EMI Tracker Dashboard | ✅ Complete | v1.3 |
| SIP Auto-Detection from CC/Bank Statements | ✅ Complete | v1.3 |
| Manual CC Transaction Entry | ✅ Complete | v2.0 |
| eCAS Upload & Parsing (CAMS/NSDL) | ✅ Complete | v2.0 |
| SIP Auto-Detection from eCAS | ✅ Complete | v2.0 |
| eCAS Invested Value Calculation Fix | ✅ Complete (Mar 1 2026) | v2.0.1 |
| Dashboard CC Summary Card | ✅ Complete | v2.0 |

---

## 3. FEATURE SPECIFICATIONS

### 3.1 DASHBOARD (Home)

| Feature | Description | Status |
|---------|-------------|--------|
| Financial Health Score | Animated circular score (0–100), grade-badged (Excellent / Good / Fair / Needs Work / Critical) | ✅ |
| Overview Cards | Horizontal scroll: Total Income, Total Expenses, Investments, **CC Spend** (4th card when CC added) | ✅ |
| Credit Cards Section | Always-visible block showing Outstanding, Limit, Utilization % + bar. Empty state: "Add a card" CTA | ✅ |
| Expense Breakdown | Animated donut chart + category legend | ✅ |
| Recent Transactions | Last 5–10 transactions with amount, category, date | ✅ |
| Period Selector | Q (quarter), M (month), Y (year), C (custom) | ✅ |
| Monthly Trend Chart | 6-month income vs expense bar chart | ✅ |
| Smart Alerts | Overspending, savings drop, budget breach alerts | ✅ |

---

### 3.2 TRANSACTIONS

| Feature | Description | Status |
|---------|-------------|--------|
| Transaction List | Full list with search, filter by category, date, mode of payment | ✅ |
| Source Toggle | Switch between **Bank/UPI** and **Credit Card** transaction views | ✅ |
| Auto-Categorisation | Keyword + ML-based category detection | ✅ |
| Manual Override | Change category inline | ✅ |
| Flagged Transactions | Banner with count of EMI/SIP candidates needing approval | ✅ |
| Flagged Review Modal | Bottom sheet: Approve as EMI / Approve as SIP / Not Recurring | ✅ |
| Recurring Detection | Auto-flags transactions matching EMI/SIP patterns | ✅ |

---

### 3.3 CREDIT CARDS *(Separate from Bank Accounts)*

#### 3.3.1 Card Management (Settings → Cards tab)
| Feature | Description | Status |
|---------|-------------|--------|
| Add Credit Card | Card name, issuer, last 4 digits, credit limit, billing cycle, due date | ✅ |
| Edit / Delete Card | Full CRUD | ✅ |
| Utilization Bars | Per-card utilization % shown in Settings → Cards | ✅ |
| Outstanding Tracking | Auto-updated as transactions are recorded | ✅ |

#### 3.3.2 CC Statement Parsing *(Completely separate engine from bank statements)*
| Feature | Description | Status |
|---------|-------------|--------|
| Dedicated Parser (`cc_statements.py`) | Separate file, separate logic, separate DB collection | ✅ |
| Supported Formats | PDF (table extraction + text fallback), CSV, Excel (.xlsx) | ✅ |
| Issuer Detection | Auto-detect from PDF content or manual selection | ✅ |
| Supported Issuers | HDFC, ICICI, SBI Card, Axis, Kotak, IndusInd, SC, RBL, YES, AMEX, Citi, HSBC | ✅ |
| Billing Period Tag | Label imported transactions with billing cycle | ✅ |
| PDF Password Support | Decrypt password-protected CC PDFs | ✅ |
| Duplicate Detection | Skip transactions already imported | ✅ |
| Import History | Log of all past CC statement imports | ✅ |

#### 3.3.3 CC Double-Entry Bookkeeping *(Different from bank bookkeeping)*
| Transaction Type | Debit Account | Credit Account | Notes |
|-----------------|---------------|----------------|-------|
| Purchase | Expense A/c (category-specific) | CC Payable — [Card Name] | CC is LIABILITY, not Asset |
| Payment (bank→CC) | CC Payable — [Card Name] | Bank Account | Reduces CC liability |
| Interest / Fee | Finance Charges | CC Payable — [Card Name] | |
| Cashback / Reward | CC Payable — [Card Name] | Other Income | |
| EMI (CC) | EMI Expenses | CC Payable — [Card Name] | |

> **Key distinction from bank bookkeeping**: Bank account is an ASSET (deposit = Dr Bank, withdrawal = Cr Bank). Credit Card is a LIABILITY (purchase = Cr CC Payable, payment = Dr CC Payable).

#### 3.3.4 Manual CC Transaction Entry
| Feature | Description | Status |
|---------|-------------|--------|
| Quick Add Banner | Green "Record a Transaction" banner on Credit Cards screen | ✅ |
| Per-Card Buttons | "Add Expense" and "Record Payment" on each card row | ✅ |
| Entry Form | Type toggle, Card selector, Amount, Description, Merchant, Category, Date | ✅ |
| Journal Auto-Creation | Creates double-entry journal on submission | ✅ |

---

### 3.4 EMI TRACKER

| Feature | Description | Status |
|---------|-------------|--------|
| EMI Tracker Card | Card in Investments tab → opens tracker modal | ✅ |
| EMI Tracker Modal | Active EMIs list, monthly total, progress bars, upcoming payments | ✅ |
| EMI Sources | Bank loans + CC EMIs both included in monthly total | ✅ |
| Auto-Detection | Flagged from bank & CC statement imports | ✅ |
| Health Score Impact | EMI obligations factored into Financial Health calculation | ✅ |

---

### 3.5 INVESTMENTS & PORTFOLIO

| Feature | Description | Status |
|---------|-------------|--------|
| Portfolio Overview | Total invested vs current value, gain/loss, % return | ✅ |
| Holdings Tracker | Stock/MF/ETF/Gold per holding | ✅ |
| CAS Import | CAMS/Karvy CAS statement upload & parse | ✅ |
| Asset Allocation | Donut chart by category | ✅ |
| Recurring Investments (SIP) | Track all active SIPs, pause/resume | ✅ |
| Auto-Detected SIP Badge | "Auto" purple badge on SIPs detected from statements | ✅ |
| Market Ticker | Live Nifty 50, SENSEX, Nifty Bank, Gold, Silver | ✅ |
| What-If Simulator | Project returns under different scenarios | ✅ |
| Goals Tracker | Set + track financial goals with progress | ✅ |
| Loan / EMI Management | Track all loans, paid interest, outstanding | ✅ |
| Focus Refresh | Investments screen re-fetches data when navigated back to | ✅ |

---

### 3.6 BOOKS & REPORTS

| Feature | Description | Status |
|---------|-------------|--------|
| Journal Entries | Auto-generated from every transaction import | ✅ |
| General Ledger | Account-wise, date-sortable | ✅ |
| Trial Balance | Debit = Credit verification | ✅ |
| Profit & Loss | Revenue - Expenses by period | ✅ |
| Balance Sheet | Assets, Liabilities, Capital | ✅ |
| PDF Export | Professional formatted (ReportLab) | ✅ |
| Excel Export | Multi-sheet workbook (openpyxl) | ✅ |
| Date Range Filter | Any custom FY or date window | ✅ |
| CC Bookkeeping Integration | CC Payable ledger auto-maintained | ✅ |

---

### 3.7 TAX PLANNING

| Feature | Description | Status |
|---------|-------------|--------|
| Tax Calculator | Old Regime vs New Regime comparison | ✅ |
| Auto Deduction Detection | 80C, 80D, 80CCC, 80CCD, HRA, LTA from transactions | ✅ |
| Deduction Approval Flow | Approve / Dismiss auto-detected deductions | ✅ |
| Manual Deduction Entry | Add 80C, 80D etc. manually with amounts | ✅ |
| Capital Gains | LTCG / STCG from investment disposals | ✅ |
| Smart Tax Alerts | "₹14.5K eligible. Tap to review" floating bar | ✅ |
| Section Limit Tracking | Real-time % utilised of 80C (₹1.5L), 80D (₹25K), NPS etc. | ✅ |

---

### 3.8 SETTINGS

#### Settings Tabs (9 tabs)
| Tab | Contents |
|-----|----------|
| **Account** | Profile info, name, PAN, mobile |
| **Security** | PIN, biometric, auto-lock |
| **Banking** | Bank accounts (CRUD), bank statement upload (PDF/CSV/Excel) |
| **Cards** *(new)* | Credit card management, CC statement import (separate parser), CC bookkeeping info |
| **Sources** | Gmail integration (coming soon) |
| **Alerts** | Notification preferences |
| **Financial** | Risk profile, investment preferences |
| **Theme** | Light / Dark mode toggle |
| **Data** | Export data, delete account |

#### Cards Tab — Detail
| Section | Feature | Status |
|---------|---------|--------|
| Info Block | CC Double-Entry Logic explanation | ✅ |
| Manage Cards | Links to `/credit-cards` screen | ✅ |
| Your Cards | Per-card utilization bars | ✅ |
| Import Statement | Issuer select, billing period, PDF password, file picker | ✅ |
| Import History | Last 20 imports with txn count and date | ✅ |

---

### 3.9 INSIGHTS

| Feature | Description | Status |
|---------|-------------|--------|
| Health Score Breakdown | Score components: Savings Rate, Investment Rate, Expense Control, Goal Progress | ✅ |
| Monthly Trends | 6-month income vs expense trend chart | ✅ |
| Category Analysis | Top spending categories | ✅ |
| Smart Alerts | Auto-generated alerts (overspend, savings drop, budget breach) | ✅ |
| AI Advisor Chat | GPT-powered financial Q&A with context | ✅ |

---

## 4. SUPPORTED BANKS & CREDIT CARD ISSUERS

### 4.1 Bank Statement Parsing (`bank_statements.py`)
| Bank | PDF | CSV | Excel |
|------|-----|-----|-------|
| HDFC Bank | ✅ | ✅ | ✅ |
| ICICI Bank | ✅ | ✅ | ✅ |
| SBI | ✅ | ✅ | ✅ |
| Axis Bank | ✅ | ✅ | — |
| Kotak | ✅ | ✅ | — |
| IndusInd | ✅ | — | — |
| Yes Bank | ✅ | — | — |
| IDFC First | ✅ | — | — |
| Federal Bank | ✅ | — | — |
| Bank of Baroda | ✅ | — | — |
| PNB | ✅ | — | — |
| Canara Bank | ✅ | — | — |

### 4.2 Credit Card Statement Parsing (`cc_statements.py`) *(Separate Parser)*
| Issuer | PDF | CSV | Excel |
|--------|-----|-----|-------|
| HDFC Credit Card | ✅ | ✅ | ✅ |
| ICICI Credit Card | ✅ | ✅ | ✅ |
| SBI Card | ✅ | ✅ | ✅ |
| Axis Bank CC | ✅ | ✅ | — |
| Kotak CC | ✅ | ✅ | — |
| IndusInd CC | ✅ | — | — |
| Standard Chartered | ✅ | — | — |
| RBL Bank CC | ✅ | — | — |
| YES Bank CC | ✅ | — | — |
| American Express | ✅ | ✅ | — |
| Citibank CC | ✅ | ✅ | — |
| HSBC CC | ✅ | — | — |
| Generic Fallback | ✅ | ✅ | ✅ |

---

## 5. DATA ARCHITECTURE

### 5.1 Key Collections (MongoDB)
| Collection | Purpose |
|-----------|---------|
| `users` | Auth, profile, preferences |
| `transactions` | Bank/UPI transactions (imported + manual) |
| `credit_cards` | Credit card metadata (CRUD) |
| `credit_card_transactions` | CC purchases, payments, fees |
| `cc_statement_history` | CC import log |
| `journal_entries` | All double-entry records (bank + CC) |
| `bank_accounts` | Bank account details |
| `holdings` | Investment positions |
| `recurring_transactions` | SIPs + auto-detected recurring payments |
| `goals` | Financial goals + progress |
| `loans` | Loan details + EMI schedule |
| `tax_deductions` | Manual + auto-detected deductions |

### 5.2 Core CC Schemas
```json
// credit_cards
{
  "id": "uuid",
  "user_id": "uuid",
  "card_name": "HDFC Regalia",
  "issuer": "HDFC",
  "last_four": "1234",
  "credit_limit": 200000,
  "billing_cycle_day": 5,
  "due_day": 20,
  "current_outstanding": 36000,
  "available_credit": 164000
}

// credit_card_transactions
{
  "id": "uuid",
  "user_id": "uuid",
  "card_id": "uuid",
  "card_name": "HDFC Regalia",
  "date": "2026-02-20",
  "description": "Zomato Order",
  "merchant": "Zomato",
  "amount": 450.00,
  "type": "purchase",          // purchase | payment | fee | emi | cashback | cash_advance
  "category": "Food & Dining",
  "billing_period": "Feb 2026",
  "source": "statement",       // statement | manual
  "is_emi": false,
  "is_sip": false,
  "flagged_for_review": false
}
```

---

## 6. API ENDPOINTS REFERENCE

### 6.1 Auth
- `POST /api/auth/login`
- `POST /api/auth/register`

### 6.2 Dashboard
- `GET /api/dashboard/stats` — includes `credit_card_summary` object
- `GET /api/dashboard/monthly-trends`

### 6.3 Transactions
- `GET /api/transactions`
- `POST /api/transactions`
- `GET /api/transactions/flagged` — EMI/SIP candidates for review
- `POST /api/transactions/flagged/{id}/approve`
- `POST /api/transactions/flagged/{id}/reject`

### 6.4 Credit Cards
- `GET /api/credit-cards`
- `POST /api/credit-cards`
- `PUT /api/credit-cards/{id}`
- `DELETE /api/credit-cards/{id}`
- `GET /api/credit-card-transactions`
- `POST /api/credit-card-transactions`
- `GET /api/flagged-transactions` — CC EMI/SIP candidates

### 6.5 CC Statements *(Separate from bank statements)*
- `POST /api/cc-statements/upload` — upload + parse + journal
- `GET /api/cc-statements/history` — import log

### 6.6 Bank Statements *(Bank only)*
- `POST /api/bank-statements/upload`
- `GET /api/bank-statements/history`

### 6.7 Books
- `GET /api/journal`
- `GET /api/ledger`
- `GET /api/trial-balance`
- `GET /api/profit-loss`
- `GET /api/balance-sheet`
- `GET /api/export/{book_type}/{format}` — PDF or Excel

### 6.8 Investments
- `GET /api/holdings`
- `POST /api/holdings`
- `GET /api/recurring` — SIPs (includes `auto_detected` flag)
- `POST /api/recurring`
- `GET /api/emi-tracker/dashboard`
- `GET /api/goals`
- `POST /api/goals`

### 6.9 Tax
- `GET /api/tax-calculator`
- `GET /api/tax-summary`
- `GET /api/auto-tax-deductions`
- `GET /api/user-tax-deductions`

---

## 7. BACKLOG (PRIORITISED)

### P0 — Critical / Next Sprint
| Feature | Notes |
|---------|-------|
| CC Statement Preview before import | Show first 5 parsed rows, user confirms before saving to DB |
| Real CC statement testing | Test HDFC / ICICI PDFs against parser, fix edge cases |
| CC transactions in Transactions screen | CC transactions visible in the "Credit Card" toggle view |

### P1 — High Priority
| Feature | Notes |
|---------|-------|
| CC bookkeeping in Books screen | CC Payable ledger visible in Ledger view |
| Transactions screen CC view | Show CC transactions when "Credit Card" toggle is selected |
| Due date reminders | "Due in X days" badge on cards in the Credit Cards screen |
| CC spending analytics | Category breakdown for CC-only transactions in Insights |
| More CC statement formats | Kotak, Citi, AMEX edge cases |

### P2 — Medium Priority
| Feature | Notes |
|---------|-------|
| Gmail Auto-Import | Parse transaction emails from Gmail |
| Statement Preview step | Show parsed rows before importing (CC + Bank) |
| Net Worth calculation | Include CC liabilities in net worth |
| Split transactions | Split a single entry across multiple categories |
| Anomaly detection | Flag unusual spending spikes |

### P3 — Future / Backlog
| Feature | Notes |
|---------|-------|
| Family accounts | Share books with spouse/family |
| Account Aggregator API | Auto-fetch bank data (AA framework) |
| Refactor `bank_statements.py` | Break 2500-line file into parsers module |
| Refactor `investments.tsx` | 1900-line file → split into sub-components |
| iOS native distribution | App Store submission |
| Android Play Store | Play Store submission |

---

## 8. KNOWN ISSUES & TECH DEBT

| Issue | Severity | Notes |
|-------|----------|-------|
| Metro cache stale bundle | Medium | Requires `rm -rf .metro-cache` + restart on major changes |
| `shadow*` prop deprecations | Low | Expo web warns; no functional impact |
| CC transactions not yet in Transactions toggle | Medium | `source === "credit_card"` view needs CC txn fetch |
| `bank_statements.py` is 2500+ lines | Low | Refactor to `/parsers/` module in future sprint |
| `investments.tsx` is 1900+ lines | Low | Split into sub-components in future sprint |

---

## 9. TECH STACK

| Layer | Technology |
|-------|-----------|
| Mobile/Web App | React Native + Expo Router |
| UI Components | Custom + Shadcn/UI |
| Backend API | FastAPI (Python 3.11) |
| Database | MongoDB (Motor async driver) |
| Authentication | JWT (HS256) + Biometrics (expo-local-authentication) |
| AI / LLM | GPT via Emergent Universal Key |
| PDF Parsing | pdfplumber |
| Excel Parsing | openpyxl + pandas |
| PDF Generation | ReportLab |
| Market Data | Yahoo Finance + Gold/Silver APIs |
| CC Parser | Dedicated `cc_statements.py` (separate from bank) |

---

## 10. CHANGELOG

### v2.0.0 — February 24, 2026
- ✅ **Credit Cards Settings Tab** — Separate "Cards" tab in Settings, completely independent of "Banking" tab
- ✅ **CC Statement Parser** — Dedicated `cc_statements.py` with issuer detection, PDF/CSV/Excel support for 12+ issuers
- ✅ **CC Double-Entry Bookkeeping** — Liability-based journal entries (Purchase → Dr Expense / Cr CC Payable; Payment → Dr CC Payable / Cr Bank)
- ✅ **CC Import History** — `GET /api/cc-statements/history` endpoint
- ✅ **CC Bookkeeping Info Block** — Visible in Settings → Cards explaining accounting rules
- ✅ **Dashboard CC Card** — Always-visible Credit Cards section (shows stats or "Add card" empty state)
- ✅ **Modal Translucency** — Frosted glass backdrop (`rgba(0,0,0,0.62)` + `blur(12px)`) on all bottom sheets
- ✅ **Credit Cards Screen Back Button** — Navigation back arrow added
- ✅ **Short Amount Format** — ₹2.0L format (not ₹2,00,000.00) throughout CC screens

### v1.3.0 — February 24, 2026
- ✅ **EMI Tracker Card** in Investments tab
- ✅ **Manual CC Transaction Entry** form with type toggle and category pills
- ✅ **SIP Auto-Tracking** — Approved SIPs from flagged transactions appear in Investments with "Auto" badge
- ✅ **useFocusEffect** in Investments — re-fetches on tab focus
- ✅ **CC EMI in monthly total** bugfix (`loans.py`)

### v1.2.0 — February 23, 2026
- ✅ **PDF/Excel Exports** for Journal, Ledger, P&L, Balance Sheet
- ✅ **Insights Overhaul** — Monthly Trends chart + Smart Alerts component
- ✅ **Credit Card CRUD** — Add/Edit/Delete credit cards
- ✅ **CC Transaction Backend** — Full CRUD for CC transactions
- ✅ **Flagged Transactions** — EMI/SIP auto-detection + approval modal
- ✅ **Transaction Source Toggle** — Bank/UPI ↔ Credit Card view

---

## 11. DEMO ACCOUNTS

| Account | Email | Password | Purpose |
|---------|-------|----------|---------|
| Rajesh Kumar | rajesh@visor.demo | Demo@123 | Primary demo — has transactions, investments, tax data |
| Priya Sharma | priya@visor.demo | Demo@456 | Secondary demo |

---

*© 2026 Visor Finance. All rights reserved.*
