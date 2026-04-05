# VISOR FINANCE — Comprehensive Product Document

**Version**: 3.3 | **Last Updated**: April 4, 2026
**Platform**: iOS & Android (React Native Expo) | **Backend**: FastAPI + MongoDB

---

## 1. Product Overview

Visor Finance is an AI-powered personal finance super-app designed specifically for Indian users. It consolidates banking, investments, credit cards, taxes, loans, and bookkeeping into a single mobile experience — powered by natural language AI that understands 22+ Indian languages.

**Tagline**: *Your AI-Powered Finance Companion for India*

---

## 2. Core Feature Modules

### 2.1 Smart Dashboard
The command center for your financial life, with real-time data across all modules.

- **Financial Health Score** (0–1000): A proprietary composite score computed from savings rate, expense ratio, investment diversity, debt-to-income ratio, and goal progress. Includes a visual donut chart and trend indicator (e.g., "4 pts this month").
- **Share My Score**: One-tap shareable financial health card for social bragging or accountability.
- **Overview Cards**: Three color-coded cards showing Total Income (green), Total Expenses (red), and Investments (blue) for the selected period. Each card shows a fill-percent bar relative to income.
- **Credit Card Summary**: Outstanding balance, total credit limit, utilization percentage with a color-coded progress bar (green < 50%, yellow 50–80%, red > 80%). Shows count of linked cards.
- **Trend Analysis Chart**: Interactive income vs. expenses vs. investments chart. Weekly bars for short periods, monthly bars for Financial Year view. Tap for AI-generated insights about spending patterns.
- **AI Daily Insight**: GPT-powered contextual financial tip card, refreshed daily, based on the user's actual transaction patterns and portfolio.
- **Net Worth Tracker**: Real-time calculation combining bank balances, investment portfolio value, fixed assets, minus outstanding loans and credit card debt.
- **Investment Summary (Flippable Card)**: Front shows portfolio value, total invested, and P&L. Flip to reveal:
  - Asset allocation breakdown (Stocks, MFs, Gold, FDs, etc.) with horizontal progress bars
  - AI-generated daily investment insight (GPT-4o, cached 24 hours)
- **Upcoming Dues**: Aggregated list of upcoming credit card due dates, SIP execution dates, EMI payments, and loan installments.
- **Recent Transactions**: Quick-view of the last 5 transactions with category icons and amounts.

**Period Selector**: Toggle between Q (Quarter), M (Month), Y (Financial Year: April 1 – March 31), and C (Custom date range). Custom date picker supports dates back to January 2020. The Y toggle shows Indian Financial Year labels like "FY 2025-26".

---

### 2.2 Bank Statement Import & Transaction Management

#### Supported Banks (PDF Parsing — 12 Banks)
Each bank has a purpose-built parser using the optimal extraction strategy:

| Bank | Strategy | Key Technique |
|------|----------|---------------|
| **HDFC Bank** | Text Extraction | Multi-line narration, 15+ transaction type handlers, 50+ merchant detection |
| **ICICI Bank** | Text Extraction | Interleaved block handling for mixed narration formats |
| **SBI** | Table + Text | Table extraction with text fallback, smart description truncation prevention |
| **Axis Bank** | Table + Text | Handles "F07 Cred", card charges, bypass payment gateways |
| **Kotak Mahindra** | Balance-Delta | Word-position column extraction; ignores unreliable Dr/Cr labels, computes type from balance changes |
| **Bank of Baroda** | Table Extraction | Ground-truth debit/credit columns from pdfplumber tables; gap-filling text pass for page boundaries |
| **Canara Bank** | Table + Text | IFSC regex for company names on RTGS/NEFT; IMPS shows bank+last4 |
| **Punjab National Bank** | Table Extraction | NEFT company name extraction, RTGS/cheque cleanup |
| **Union Bank** | Text Extraction | Multi-line continuation handling (e.g., salary narratives) |
| **IndusInd Bank** | Table Extraction | Standard pdfplumber table parsing |
| **Yes Bank** | Table Extraction | Standard pdfplumber table parsing |
| **IDBI Bank** | Table Extraction | Standard pdfplumber table parsing |

**Password-Protected PDFs**: Full support for encrypted bank statement PDFs.

#### Auto-Categorization Engine (30+ Categories)
Every imported transaction is automatically categorized using a 100+ keyword rule engine:

**Income**: Salary, Interest, Dividends, Refunds, Rental Income, Bank Transfer In
**Food**: Food & Dining (Swiggy, Zomato, restaurants), Groceries (BigBasket, Blinkit, Zepto, DMart)
**Transport**: Uber/Ola, Fuel (all oil companies), Metro, Parking/Toll, Flights (IndiGo, SpiceJet, MakeMyTrip)
**Utilities**: Electricity, Water, Gas, Internet, Mobile Recharge, DTH
**Entertainment**: Netflix, Hotstar, Spotify, YouTube Premium, Dream11, Bookmyshow
**Shopping**: Amazon, Flipkart, Myntra, Ajio, Decathlon, Croma
**Financial**: Insurance, EMI, Credit Card Payments, SIP, PPF, NPS, FD, Gold, Stocks
**Housing**: Rent, Society Maintenance
**Health**: Hospitals, Pharmacies (1mg, PharmEasy), Diagnostics
**Education**: Udemy, Coursera, BYJU's, Coaching
**Others**: Personal Care, Donations, Taxes & Fees, Bank Charges, Cash/ATM

**Known Merchant Detection**: 50+ Indian merchants recognized by name (Swiggy, Cred, Amazon, PhonePe, Paytm, Dream11, Mumbai Metro, etc.)

#### Duplicate Detection
Uses unique reference numbers (UTR for UPI, NEFT ref, RTGS ref) rather than description matching. Prevents re-import of the same statement while allowing legitimate similar transactions.

#### Transaction Management
- **CRUD Operations**: Create, read, update, delete individual transactions
- **Type Filters**: All, Income, Expense, Investment
- **Category Filters**: Quick-scroll chips for Rent, Food, Salary, SIP, Shopping, etc.
- **Search**: Full-text search across description, category, notes, and payment account
- **Custom Date Range**: Filter transactions by any date range (2020 onwards)
- **Server-Side Summary**: Income/Expenses/Net computed via MongoDB aggregation for accuracy regardless of list size
- **Recategorize All**: One-click re-run of the categorization engine on all imported transactions

---

### 2.3 Investment Tracking

#### Portfolio Overview
- **Total Invested vs Current Value**: Real-time P&L with absolute and percentage returns
- **Asset Allocation**: Visual breakdown by category (Stocks, Mutual Funds, Gold, FDs, etc.)
- **Live Market Ticker**: Scrolling bar showing Nifty 50, SENSEX, Nifty Bank, Gold (10g), Silver (1Kg) — live prices via yfinance + GoldAPI

#### Holdings Management
- **Stocks**: Live prices via yfinance (NSE/BSE tickers). Supports `.NS` and `.BO` suffixes.
- **Mutual Funds**: NAV lookup via mfapi.in using ISIN codes. Supports both direct and regular plans.
- **ISIN Resolution**: Automatic ISIN → ticker resolution with caching. Handles edge cases like hyphenated names (TATAGOLD-E → TATAGOLD.NS).
- **Refresh Prices**: One-tap live price update for entire portfolio.
- **Manual Holdings**: Add any holding manually with buy price, quantity, and date.
- **Clear All Holdings**: Bulk delete for re-import scenarios.

#### Statement Upload (Investment Statements)
- **Groww**: XLSX parsing with ISIN → NSE/BSE ticker resolution for all stocks
- **Zerodha**: Multi-sheet XLSX support — Equity, Mutual Funds, and Combined sheets parsed correctly
- **CAS (Consolidated Account Statement)**: CAMS/KFintech MF CAS upload support
- **Category Detection**: Sheet name takes priority for multi-sheet files (Equity → Stock, MF → Mutual Fund)

#### SIP Tracker
- **Active SIPs**: Track all Systematic Investment Plans with amount, frequency, and next execution date
- **SIP Suggestions**: AI-generated SIP recommendations based on portfolio gaps
- **Link to Goals**: Map SIPs to financial goals for progress tracking

#### Portfolio Analytics
- **Portfolio Rebalancing**: AI-powered suggestions comparing current vs. ideal allocation based on risk profile
- **Wealth Projector**: Project future portfolio value based on current SIPs and expected returns
- **Goal Mapper**: Link investments to specific financial goals and track progress

#### Risk Profile
- Questionnaire-based risk assessment (Conservative, Moderate, Aggressive)
- Risk score with breakdown across categories
- Personalized investment recommendations based on profile

---

### 2.4 Credit Card Management

#### Card Management
- **Add/Edit Cards**: Store card details (last 4 digits, issuer, network, credit limit, billing cycle)
- **Supported Issuers**: HDFC, ICICI, SBI, Axis, Kotak, IndusInd, Standard Chartered, RBL, Yes Bank, IDFC, Amex, Citibank, HSBC
- **Utilization Tracking**: Real-time credit utilization with color-coded alerts

#### Credit Card Statement Upload
- **PDF & CSV Support**: Auto-detect issuer from statement content
- **16 Issuer Parsers**: HDFC, ICICI, SBI, Axis, Kotak, IndusInd, Standard Chartered, RBL, Yes Bank, IDFC, Amex, Citi, HSBC + Generic fallback
- **Transaction Import**: Automatically categorize CC transactions with the same 30+ category engine

#### Credit Card Analytics
- **Due Calendar**: Visual calendar of upcoming payment due dates across all cards
- **Interest Calculator**: Calculate interest charges based on outstanding balance, rate, and payment plan
- **Rewards Tracker**: Track reward points across cards
- **Card Recommender**: AI-powered card recommendations based on spending patterns

#### AI-Powered Benefits Tab
- **Per-Card Benefits**: Fetch card-specific rewards (lounge access, fuel waivers, cashback rates, milestone rewards) using GPT-5.2
- **Cached Results**: Benefits cached in MongoDB to avoid repeated API calls
- **AI Disclaimer**: Clear indication that benefits are AI-generated and should be verified with the issuer

---

### 2.5 AI Financial Advisor (Visor AI)

#### Text Chat
- **GPT-5.2 Powered**: Full conversational financial advisor using OpenAI via Emergent LLM Key
- **Context-Aware**: Pulls user's actual financial data (transactions, portfolio, goals, loans) into every conversation for personalized advice
- **22 Indian Languages**: Understands queries in all 22 scheduled Indian languages, including transliterated text (e.g., "enna mutual fund invest pannanum?" in Tamil)
- **Default Hinglish**: Responds in professional Hinglish (Hindi-English mix) by default, adapts to user's language preference
- **Financial Calculator**: Built-in calculator triggered by mathematical queries (EMI, SIP returns, compound interest)
- **Live Market Data**: Can fetch and discuss current stock prices, indices, gold/silver rates
- **Web Search**: Financial news and research integration for up-to-date market commentary
- **Chat History**: Persistent conversation history with delete individual messages or clear all
- **Finance-Only Guardrail**: Strictly refuses non-financial queries

#### Voice Chat
- **Speech-to-Text**: ElevenLabs STT for accurate voice transcription
- **Text-to-Speech**: ElevenLabs TTS with multilingual v2 model for natural voice responses
- **Same AI Engine**: Voice queries processed through the same Visor AI engine as text chat
- **Audio Response**: Returns both text and audio (base64) for simultaneous display

---

### 2.6 Tax Module

#### Tax Summary
- **Old vs New Regime Comparison**: Side-by-side comparison showing which regime saves more
- **Automatic Slab Calculation**: Income tax computed for both regimes with applicable slabs (FY 2025-26 new regime: ₹4L nil, ₹8L 5%, ₹12L 10%, etc.)
- **Surcharge & Cess**: Health & Education Cess (4%) and surcharge automatically applied
- **Effective Tax Rate**: Shows actual tax percentage on total income

#### Phase 0: Income Profile (Added April 2026)
- **Tax Profile Setup**: Users select income types (Salaried, Freelancer, Business, Investor, Rental) which drive which tax modules are activated
- **Income Type Chips**: Multi-select UI with icons, saved to `tax_income_profiles` MongoDB collection
- **Prerequisite for all downstream tax calculations**

#### Phase 1: Salary-Based Tax Accuracy (Added April 2026)
- **Salary Profile Wizard** (3-step modal): Employer + city + state (Step 1), Monthly salary breakdown with auto-calculated gross (Step 2), EPF/Professional Tax/TDS/Housing deductions (Step 3)
  - Auto-detect metro vs non-metro city for HRA calculations
  - State-wise professional tax lookup (Maharashtra ₹2,400/yr, Karnataka ₹2,400/yr, TN ₹1,200/yr, etc.)
  - EPF auto-suggestion at 12% of Basic (capped at ₹1,800/month per EPFO ceiling)
  - Saved to `salary_profiles` MongoDB collection
- **HRA Auto-Calculation Card**: Expandable card showing 3-condition formula (Actual HRA, City% of Basic, Rent−10%Basic), highlights limiting condition in amber, shows landlord PAN warning if rent > ₹1L/year
- **Section 80C Limit Tracker**: Stacked progress bar (₹0 to ₹1.5L), instrument-wise breakdown (ELSS, EPF, LIC, PPF, NSC, etc.), NPS 80CCD(1B) ₹50K extra tracker below, status badge (optimized/good/under-utilized)
- **Enhanced Section Mapping**: Confidence scoring (0.55–0.95) on all auto-detected deductions, `POST /api/tax/remap-transactions` endpoint
- **Visor AI Context**: Salary profile + HRA exemption + income type injected into AI context for accurate tax Q&A

#### Deductions Management
- **Auto-Detected Deductions**: Transactions automatically scanned for tax-deductible payments (Insurance → 80C, Medical → 80D, Education Loan → 80E, HRA → 10(13A))
- **Manual Deductions**: Add custom deductions under any section (80C, 80D, 80E, 80G, 80TTA, 80GG, 24(b), etc.)
- **Smart Tax Notifications**: Alerts for missing deduction opportunities and approaching limits
- **Disclaimer Banner**: Minimal collapsible strip: "Estimates only — consult a CA for ITR filing"

#### Capital Gains
- **STCG & LTCG Tracking**: Short-term and long-term capital gains computed from investment holdings
- **Tax-Loss Harvesting**: Identify loss positions for potential tax offset
- **Section 111A / 112A**: Proper classification with applicable rates (20% STCG, 12.5% LTCG above ₹1.25L)

#### Tax Planning
- **AI Tax Scanner**: Scans all transactions and suggests potential deductions
- **Deduction Floating Bar**: Persistent summary bar showing total deductions claimed vs. available limits
- **Financial Year Aware**: All calculations aligned to Indian FY (April–March)

#### Upcoming Tax Module Phases
- **Phase 2** ✅ (Completed April 2026): Form 16 PDF parser, AIS/Form 26AS JSON/PDF parser, FD Interest Certificate parser, Real-time Tax Meter on Dashboard
- **Phase 3** ✅ (Completed April 2026): Capital Gains Engine with grandfathering, Deduction Gap Analysis with product recommendations, TDS Mismatch Detection, Tax Calendar & Proactive Reminders
- **Non-Salaried Profiles**: Freelancer (44ADA presumptive), Business Owner (44AD), Investor/F&O (speculative income, ITR-3), Rental Income (House Property formula)

#### Phase 2: Document Parsers & Tax Meter (Completed April 2026)
- **Form 16 PDF Parser** (`POST /api/tax/upload/form16`): Extracts salary components (Basic, HRA, LTA, Perquisites), deductions (80C, 80CCC, 80CCD, 80D, 80E, 80G, 80TTA, 24b), tax computation (total tax, TDS, surcharge, cess), employer info (name, TAN, PAN)
- **AIS / Form 26AS Parser** (`POST /api/tax/upload/ais`, `POST /api/tax/upload/form26as`): Extracts TDS details, SFT transactions, interest income, dividend income, supports both JSON and PDF formats
- **FD Interest Certificate Parser** (`POST /api/tax/upload/fd-certificate`): Extracts bank name, FD account, principal, interest earned, TDS deducted, auto-creates 80TTA deduction entry
- **Tax Meter Dashboard Widget**: Compact card showing estimated tax, TDS paid YTD, tax due/refund expected, 80C utilization progress, regime recommendation (old vs new), effective tax rate
- **Tax Documents Management** (`GET /api/tax/documents`, `DELETE /api/tax/documents/{id}`): List and manage uploaded tax documents

#### Phase 3: Advanced Tax Analytics (Completed April 2026)
- **Capital Gains Engine v2** (`GET /api/tax/capital-gains-v2`):
  - Grandfathering support for equity acquired before Feb 1, 2018 (Budget 2018)
  - FIFO cost basis matching for sell transactions
  - STCG (20% equity) and LTCG (12.5% above ₹1.25L exemption) computation
  - Asset classification by holding period (1 year equity, 2 years property/gold)
  - Detailed tax breakdown per gain with adjusted cost calculation
- **Deduction Gap Analysis** (`GET /api/tax/deduction-gap`):
  - Section-wise gap identification (80C, 80CCD1B, 80D, 80E, 80G, 24b, 80TTA)
  - Utilization percentage with status badges (optimized/good/under-utilized)
  - Product recommendations with lock-in periods, expected returns, and tax benefit notes
  - Top 3 actionable recommendations with potential tax savings at 30% slab
- **TDS Mismatch Detection** (`GET /api/tax/tds-mismatch`):
  - Compares employer TDS (from salary profile) with Form 26AS/AIS (uploaded documents)
  - Status classification: matched, minor_mismatch, major_mismatch, not_found_in_26as
  - Actionable recommendations for resolution
- **Tax Calendar** (`GET /api/tax/calendar`):
  - Full FY tax calendar (April–March) with important dates
  - Personalized to income type (advance tax dates only for business/freelancer/investor)
  - Status indicators: urgent, upcoming, future, past, completed
  - Next deadline preview with days remaining
- **Proactive Tax Reminders** (`GET /api/tax/reminders`):
  - Context-aware reminders based on user's data (80C remaining, ITR deadline, Form 16 collection)
  - Urgency levels: high, medium, low
  - Month-specific triggers (October–March for 80C, June–July for Form 16/ITR)
- **AI Context Integration**: Auto-detected deductions and uploaded documents injected into Visor AI context

---
### 2.7 Loan & EMI Management

#### Loan Tracker
- **Add Loans**: Home loan, car loan, personal loan, education loan, gold loan
- **Encrypted Storage**: Sensitive loan details (account numbers, lender info) encrypted with AES-256-GCM field-level encryption
- **EMI Calculator**: Standard EMI formula with monthly rate computation
- **Amortization Schedule**: Full EMI schedule showing principal vs interest split for every month

#### EMI Analytics
- **EMI Overview Dashboard**: Total EMIs, upcoming payments, portfolio interest rate
- **Prepayment Calculator**: See how extra payments reduce tenure and total interest
- **Principal-Interest Split**: Visual breakdown of where each EMI payment goes
- **EMI Tracker Dashboard**: Centralized view of all active EMIs across loans

---

### 2.8 Double-Entry Bookkeeping

#### Journal
- **Automatic Double-Entry**: Every transaction auto-generates proper journal entries (debit/credit pairs)
- **Account Categorization**: Assets, Liabilities, Income, Expenses, Equity
- **Filter by Date Range**: View journal entries for any period

#### Financial Statements
- **Profit & Loss Statement**: Income vs. expenses for any date range with gross/net profit
- **Balance Sheet**: Assets, liabilities, and equity as of any date. Includes bank balances, investments, loans payable
- **General Ledger**: Account-wise transaction history with running balances

#### Export
- **PDF Export**: Professional formatted PDF reports for Journal, P&L, Balance Sheet, and Ledger
- **Excel Export**: Full data export to XLSX for all four report types
- **Indian Rupee Formatting**: All amounts in ₹ with lakh/crore notation

---

### 2.9 Goals & Savings

- **Create Financial Goals**: Emergency Fund, House Down Payment, Car, Vacation, Retirement, Education, Wedding, etc.
- **Target Amount & Timeline**: Set goal amount and target date
- **Progress Tracking**: Visual progress bars and percentage completion
- **Link to Investments**: Map specific holdings or SIPs to goals
- **Dashboard Integration**: Goal progress visible on the main dashboard

---

### 2.10 Recurring Transactions

- **Track Recurring Payments**: Rent, subscriptions, SIPs, EMIs, utilities
- **Frequency Options**: Daily, weekly, monthly, quarterly, yearly
- **Auto-Execute**: Mark recurring transactions as executed with one tap
- **Pause/Resume**: Temporarily pause and resume recurring items
- **Next Execution Date**: Smart calculation of upcoming payment dates

---

### 2.11 Fixed Assets

- **Asset Registry**: Track property, vehicles, jewelry, electronics, and other fixed assets
- **Purchase Details**: Cost, purchase date, current estimated value
- **Net Worth Integration**: Fixed asset values included in net worth calculation

---

### 2.12 Insurance Policies

- **Policy Tracker**: Store life insurance, health insurance, vehicle insurance, and other policies
- **Premium Tracking**: Policy amount, premium, frequency, and next due date
- **Tax Integration**: Insurance premiums automatically eligible for Section 80C/80D deductions

---

### 2.13 Market Data

- **Live Indian Market Indices**: Nifty 50, SENSEX, Nifty Bank — real-time via yfinance
- **Gold & Silver Prices**: 10g gold and 1Kg silver in INR via GoldAPI.io with yfinance fallback
- **Auto-Refresh**: Market data cached and refreshed on dashboard load
- **Scrolling Ticker Bar**: Live prices displayed as a scrolling horizontal bar on the Investments screen

---

### 2.14 Settings & Data Management

- **Profile Management**: Name, email, PIN lock setup
- **Dark Mode**: Full dark theme support across all screens
- **Bank Account Management**: Add/edit/delete linked bank accounts, set default account
- **Bank Statement Upload**: Upload PDF bank statements directly from Settings
- **Data Management**: "Clear All Transactions" button with confirmation dialog — wipes all bank transactions, credit card transactions, bank accounts, journal entries, and statement hashes for a clean re-import
- **Delete Account**: Complete account deletion with all associated data

---

## 3. Security & Privacy

- **JWT Authentication**: Secure token-based authentication with expiry
- **PIN Lock**: Optional 4-digit PIN for app access (with skip option)
- **AES-256-GCM Encryption**: Field-level encryption for sensitive loan and account data using per-user Data Encryption Keys (DEK)
- **No Plain-Text Storage**: Sensitive fields encrypted at rest in MongoDB
- **Master Key Architecture**: User DEKs encrypted with a master key for key rotation capability

---

## 4. Technical Architecture

```
Frontend: React Native Expo (iOS + Android + Web)
Backend:  FastAPI (Python 3.11+)
Database: MongoDB (with Motor async driver)
AI:       GPT-5.2 + GPT-4o via Emergent LLM Key
Voice:    ElevenLabs (STT + TTS, multilingual v2)
Markets:  yfinance (stocks/indices) + mfapi.in (MF NAV) + GoldAPI.io (metals)
PDF:      pdfplumber (table + text extraction)
Exports:  ReportLab (PDF) + openpyxl (Excel)
Tunnel:   Cloudflare Quick Tunnels for Expo Go mobile preview
```

### API Surface
- **150+ REST endpoints** across 30 route modules
- **12 bank statement parsers** with bank-specific extraction strategies
- **16 credit card issuer parsers** (PDF + CSV)
- **5 investment statement parsers** (Groww, Zerodha, CAS, manual)

---

## 5. Integrations

| Integration | Purpose | Key |
|-------------|---------|-----|
| OpenAI GPT-5.2 | AI Advisor, Insights, Benefits, Tax Scanner | Emergent LLM Key |
| OpenAI GPT-4o | Investment Insights (cached 24h) | Emergent LLM Key |
| ElevenLabs | Voice chat (STT + TTS) | Emergent LLM Key |
| yfinance | Live stock prices, indices (Nifty, SENSEX) | Open Source |
| mfapi.in | Mutual Fund NAV lookup by ISIN | Public API |
| GoldAPI.io | Gold & Silver spot prices in INR | API Key |
| Cloudflare Tunnels | Expo Go mobile preview | Pre-configured |

---

## 6. Key Screens (for Landing Page Showcase)

1. **Dashboard** — Financial health score, overview cards, trend chart, AI insight, net worth, investment summary
2. **Transactions** — Searchable, filterable transaction list with auto-categorized bank imports
3. **Investments** — Portfolio overview, live holdings, SIP tracker, market ticker, risk profile
4. **Insights (AI Advisor)** — Conversational AI chat + voice assistant in 22 Indian languages
5. **Credit Cards** — Card management, statement upload, utilization tracking, AI benefits
6. **Tax** — Old vs New regime comparison, auto-detected deductions, capital gains
7. **Books** — Double-entry journal, P&L, balance sheet, ledger with PDF/Excel export
8. **Settings** — Profile, dark mode, bank accounts, data management

---

## 7. What Makes Visor Unique

- **India-First**: Built for Indian banking formats, tax laws (80C/80D/HRA), and financial products (SIP, NPS, PPF, SGBs)
- **12 Bank Parsers**: The deepest bank statement parsing in any Indian finance app — each bank has a custom-built parser, not a generic OCR
- **AI That Speaks Your Language**: Financial advice in Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, and 16 more languages — even transliterated in English script
- **Professional Hinglish**: The AI speaks like a real Indian financial advisor, not a robotic chatbot
- **Complete Financial Picture**: Transactions + Investments + Credit Cards + Loans + Tax + Insurance + Goals — all in one app
- **Double-Entry Bookkeeping**: Export-ready financial statements (P&L, Balance Sheet) — useful for freelancers and small business owners
- **Privacy-First**: AES-256-GCM encryption for sensitive data, no third-party analytics

---

## 8. Credentials

- **Demo Account**: `rajesh@visor.demo` / `Demo@123`
- **Expo Go QR**: `https://form-parser-preview.preview.emergentagent.com/api/expo/qr`

---

## 9. Upcoming Roadmap

| Priority | Feature |
|----------|---------|
| P0 | Refactor pdf_parsers.py (3000+ lines → modular per-bank files) |
| P1 | Streaming TTS for faster perceived voice response |
| P1 | Financial Health Score flip card (detailed breakdown on back) |
| P1 | Frontend refactoring (investments.tsx, index.tsx — 2000+ lines each) |
| P2 | Advanced Tax Module Phase 4 (ITR filing integration) |
| P2 | Gmail Integration for auto-importing bank transaction emails |
| P3 | Voice Cloning with ElevenLabs for a custom Visor persona |
| P3 | "Share with Friends" referral feature |
| P3 | WhatsApp/Telegram bot for transaction logging |
| P3 | Multi-currency support for NRI users |


---

## 10. Recent Changes (Changelog)

### Mar 28, 2026
- **Health Score + Insights FY Fix**: Health score varies with M/Q/Y/Custom period. Fixed Insights screen Year toggle to use Indian FY (Apr 1 – Mar 31). Fixed timezone bug (toISOString date shift).
- **Holdings P&L**: Updated all 12 holdings with realistic current values (Infosys -9.5% loss, Gold +29% gain, etc.)
- **Loans/EMIs**: Added 3 loans — Home (₹45L @8.5%), Car (₹10L @9.25%), Education (₹8L @10.5%) with EMI tracking
- **SIPs**: 4 recurring SIPs matching mutual fund holdings (Parag Parikh, Mirae, Axis ELSS, HDFC Mid-Cap)
- **Demo Seed**: 220 transactions (Oct 2025 – Mar 2026), 3 credit cards, 4 goals, 2 insurance policies

### Mar 22, 2026
- **Dashboard FY & Date Range Fix**: Y toggle shows Indian Financial Year (Apr 1 – Mar 31). Custom date picker supports 2020+. Backend groups trend data monthly for Year view.
- **Transaction Double-Counting Bug Fix**: Increased list limits to 5000, added server-side `/api/transactions/summary`.
- **Credit Card Benefits Tab**: AI-powered per-card benefits via GPT-5.2 with caching.
- **Clear All Transactions**: Data management feature in Settings.
- **Bank Parsers**: Rewrote Canara, BoB (table extraction), Kotak (balance-delta).
