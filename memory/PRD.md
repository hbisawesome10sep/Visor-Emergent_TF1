# VISOR FINANCE — Product Requirements Document (PRD)
**Version**: 2.0  
**Last Updated**: March 18, 2026  
**Status**: Active Development  

---

## 1. Original Problem Statement

Build a comprehensive personal finance management application named **Visor**, tailored for Indian accounting standards. The app covers dashboard analytics, credit card management, EMI/SIP tracking, investment portfolio management, tax planning, bookkeeping, and AI-powered financial advice — all within a premium mobile-first experience.

---

## 2. User Personas

| Persona | Description |
|---|---|
| **Primary** | Indian individual investors (25-45 age) managing personal finances, investments, taxes, and credit cards |
| **Secondary** | Small business owners/freelancers tracking income, expenses, and tax liabilities |
| **Demo User** | `rajesh@visor.demo` / `Demo@123` — pre-seeded with realistic Indian financial data |

---

## 3. Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React Native (Expo SDK 52) with TypeScript |
| **Backend** | FastAPI (Python 3.11) |
| **Database** | MongoDB (via Motor async driver) |
| **AI Engine** | OpenAI GPT-5.2 via `emergentintegrations` library (Emergent LLM Key) |
| **Market Data** | GoldAPI.io (Gold/Silver INR prices), Yahoo Finance (NSE/BSE stocks, indices) |
| **Encryption** | AES-256-GCM field-level encryption for PII (PAN, Aadhaar, DOB) |
| **Auth** | JWT (HS256, 30-day expiry), bcrypt password hashing |
| **Tunnel** | Cloudflared (Cloudflare Quick Tunnel) for Expo Go mobile preview |
| **UI Framework** | Custom design system with DM Sans font, Jewel-tone accent palette (Emerald, Ruby, Amber, Sapphire, Amethyst, Teal, Rose), True Black / Pure White theme |

### Key Libraries
- **Backend**: `pdfplumber`, `pandas`, `openpyxl` (statement parsing), `yfinance` (stock data), `ddgs` (DuckDuckGo web search), `cryptography` (AES-256-GCM), `dateutil`, `bcrypt`, `pyjwt`
- **Frontend**: `react-native-view-shot` (share feature), `react-native-svg` (jar visualizations), `expo-router` (file-based routing), `@expo/vector-icons`

---

## 4. Architecture Overview

### 4.1 System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    VISOR FINANCE ARCHITECTURE                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    HTTPS/WSS     ┌─────────────────────────┐   │
│  │  Expo Go    │ ──────────────── │  Cloudflared Tunnel     │   │
│  │  (iOS/And)  │                  │  (*.trycloudflare.com)  │   │
│  └─────────────┘                  └────────┬────────────────┘   │
│                                            │                     │
│  ┌─────────────┐                  ┌────────▼────────────────┐   │
│  │  Web Browser │ ──── /api/* ──── │  Nginx Ingress (K8s)   │   │
│  │  (Preview)   │                  │  Port 3000 → Expo Web  │   │
│  └─────────────┘                  │  /api/* → Port 8001     │   │
│                                   └────────┬────────────────┘   │
│                                            │                     │
│           ┌────────────────────────────────┼──────────┐          │
│           │                                │          │          │
│  ┌────────▼─────────┐           ┌──────────▼───────┐  │          │
│  │  Expo Dev Server  │           │  FastAPI Backend │  │          │
│  │  (Metro Bundler)  │           │  (Uvicorn 8001)  │  │          │
│  │  Port 3000        │           │  Hot Reload       │  │          │
│  └──────────────────┘           └──────────┬───────┘  │          │
│                                            │          │          │
│                                   ┌────────▼───────┐  │          │
│                                   │    MongoDB     │  │          │
│                                   │  27 Collections│  │          │
│                                   │  localhost:27017│  │          │
│                                   └────────────────┘  │          │
│           └───────────────────────────────────────────┘          │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    EXTERNAL SERVICES                        │ │
│  │  • OpenAI GPT-5.2 (via Emergent LLM Key)                   │ │
│  │  • GoldAPI.io (Gold/Silver prices in INR)                   │ │
│  │  • Yahoo Finance (NSE/BSE stocks, indices, ETFs)            │ │
│  │  • DuckDuckGo Search (financial news for AI context)        │ │
│  │  • Google OAuth (Gmail integration — planned)               │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 Backend Architecture

```
/app/backend/
├── server.py                    # FastAPI app, router registration, startup lifecycle
├── config.py                    # Environment variables, constants
├── database.py                  # Motor async MongoDB client
├── auth.py                      # JWT auth, bcrypt, auto-decrypt PII middleware
├── encryption.py                # AES-256-GCM field-level encryption (DEK per user)
├── models.py                    # 20+ Pydantic models for request/response validation
├── seed_data.py                 # Demo data seeder (2 users, transactions, goals, etc.)
├── bank_parser.py               # Bank statement parsing orchestrator
├── indian_commodity_prices.py   # Gold/Silver INR price helpers
├── parsers/
│   ├── pdf_parsers.py           # PDF statement parsers (SBI, HDFC, ICICI, Axis, etc.)
│   ├── csv_excel.py             # CSV/Excel statement import
│   └── utils.py                 # Parsing utilities
├── services/
│   ├── visor_prompt.py          # Visor AI system prompt (149 lines of India-specific instructions)
│   ├── visor_helpers.py         # Ticker detection, live prices, web search, auto-calculator
│   └── visor_calculators.py     # 9 financial calculators (SIP, EMI, CAGR, FIRE, PPF, HRA, etc.)
├── routes/                      # 26 route modules, 130+ API endpoints
│   ├── auth.py                  # Register, login, profile, delete account
│   ├── transactions.py          # CRUD + flagging + approval workflow
│   ├── goals.py                 # Financial goals CRUD
│   ├── dashboard.py             # V1 dashboard (stats, trends, alerts)
│   ├── dashboard_v2.py          # V2 dashboard (health score, net worth, XIRR, AI insight)
│   ├── credit_cards.py          # Credit card CRUD + statement upload
│   ├── cc_analytics.py          # Due calendar, interest calc, rewards, AI recommender
│   ├── cc_statements.py         # Credit card statement parsing
│   ├── emi_sip_analytics.py     # EMI/SIP analytics, prepayment, wealth projector, goal mapping
│   ├── holdings.py              # Investment holdings CRUD + CAS upload
│   ├── loans.py                 # Loan CRUD + EMI schedule generation
│   ├── recurring.py             # Recurring transactions (SIPs, subscriptions)
│   ├── tax.py                   # Tax calculator, tax summary, capital gains
│   ├── market_data.py           # Live market data (Gold, Silver, Nifty, Sensex) + scheduler
│   ├── portfolio.py             # Portfolio overview + rebalancing suggestions
│   ├── risk_profile.py          # Risk assessment questionnaire
│   ├── bookkeeping.py           # Double-entry bookkeeping (chart of accounts, P&L, balance sheet)
│   ├── journal.py               # Journal entries + ledger
│   ├── bank_accounts.py         # Bank account management
│   ├── bank_statements.py       # Bank statement upload + parsing
│   ├── assets.py                # Fixed asset management with depreciation
│   ├── exports.py               # PDF/Excel export (balance sheet, P&L, ledger)
│   ├── visor_ai.py              # Visor AI chat endpoint (context-aware, multi-data-source)
│   ├── ai_chat.py               # Legacy AI chat
│   ├── ai_advisor.py            # AI advisor with calculator integration
│   ├── gmail.py                 # Gmail OAuth + transaction sync (planned)
│   └── expo_qr.py               # Expo Go QR code page for mobile preview
└── tests/                       # 30+ test files
```

### 4.3 Frontend Architecture

```
/app/frontend/
├── app/                          # Expo Router (file-based routing)
│   ├── _layout.tsx               # Root layout (auth guard, theme provider, fonts)
│   ├── index.tsx                 # Landing page (marketing/feature showcase)
│   ├── +html.tsx                 # Web HTML template
│   ├── (auth)/
│   │   ├── login.tsx             # Login screen (email/password)
│   │   └── register.tsx          # Registration (full_name, email, password, PAN, Aadhaar, DOB)
│   ├── (tabs)/
│   │   ├── _layout.tsx           # Tab navigation (Home, Transactions, Invest, Insights, Settings)
│   │   ├── index.tsx             # Main Dashboard (1972 lines — Financial Health, Overview, 
│   │   │                         #   Credit Cards, Goals, Transactions, Trends, Net Worth, AI)
│   │   ├── transactions.tsx      # Transaction list + add/edit + bank statement upload
│   │   ├── investments.tsx       # Holdings, SIPs, Goals, Risk Profile, Market Ticker
│   │   ├── insights.tsx          # Financial Health Score, Smart Alerts, Trend Analysis
│   │   ├── tax.tsx               # Tax calculator, deductions, capital gains
│   │   └── settings.tsx          # Profile, security, theme, export, AI chat, danger zone
│   ├── credit-cards.tsx          # Credit card management screen
│   └── books.tsx                 # Bookkeeping (journal, ledger, P&L, balance sheet)
├── src/
│   ├── components/
│   │   ├── AIAdvisorChat.tsx     # Visor AI chat interface (cute robot icon)
│   │   ├── JarProgressView.tsx   # SVG jar visualization for goal progress
│   │   ├── PieChart.tsx          # Custom SVG pie chart
│   │   ├── TrendChart.tsx        # SVG trend/line chart
│   │   ├── FAB.tsx               # Floating action button
│   │   ├── LockScreen.tsx        # PIN/biometric lock screen
│   │   ├── SecuritySetupScreen.tsx # Security setup flow
│   │   ├── dashboard/
│   │   │   ├── FinancialHealthV2Card.tsx  # Gamified 0-1000 health score
│   │   │   ├── AIInsightCard.tsx          # AI-powered daily insight
│   │   │   ├── InvestmentSummaryCard.tsx  # Portfolio value + XIRR
│   │   │   ├── NetWorthCard.tsx           # Assets - Liabilities
│   │   │   ├── UpcomingDuesCard.tsx       # CC + Loan due dates
│   │   │   └── ShareScoreCard.tsx         # Share financial health score image
│   │   ├── investments/
│   │   │   ├── GoalsSection.tsx           # Financial goals with Jar visualization
│   │   │   ├── HoldingsSection.tsx        # Investment holdings table
│   │   │   ├── PortfolioOverviewCard.tsx  # Portfolio allocation chart
│   │   │   ├── RiskProfileCard.tsx        # Risk assessment display
│   │   │   ├── RecurringInvestmentsSection.tsx # SIPs + recurring
│   │   │   └── MarketTickerBar.tsx        # Live market data ticker
│   │   ├── credit-cards/
│   │   │   ├── DueCalendarSection.tsx     # Visual due date calendar
│   │   │   ├── InterestCalculator.tsx     # Minimum payment trap calculator
│   │   │   ├── RewardsTracker.tsx         # Points/cashback tracking
│   │   │   └── CardRecommender.tsx        # AI-powered card recommendation
│   │   ├── emi-sip/
│   │   │   ├── PrincipalInterestSplit.tsx # P vs I visualization
│   │   │   ├── PrepaymentCalculator.tsx   # Loan prepayment scenarios
│   │   │   ├── WealthProjector.tsx        # 3-scenario wealth projection
│   │   │   └── GoalMapper.tsx             # SIP-to-goal mapping + link/unlink
│   │   └── tax/
│   │       ├── SmartTaxNotifications.tsx   # Tax alerts & reminders
│   │       ├── AutoDeductionsSection.tsx   # Auto-detected deductions
│   │       ├── CapitalGainsSection.tsx     # STCG/LTCG tracking
│   │       ├── DeductionFloatingBar.tsx    # Tax savings progress bar
│   │       └── UserDeductionsSection.tsx   # Manual deduction entry
│   ├── context/
│   │   ├── AuthContext.tsx        # Auth state, token management, auto-logout
│   │   ├── ThemeContext.tsx       # Dark/Light theme with system detection
│   │   ├── SecurityContext.tsx    # PIN lock, biometric auth
│   │   └── ScreenContext.tsx      # Screen tracking for AI context
│   └── utils/
│       ├── api.ts                 # API client (auto-prefixes /api, auto-logout on 401)
│       ├── theme.ts               # Color system (Accent palette + Light/Dark themes)
│       ├── formatters.ts          # INR formatting, category colors/icons, date utils
│       └── fonts.ts               # DM Sans font loading
```

---

## 5. Database Schema (27 MongoDB Collections)

| Collection | Purpose | Key Fields |
|---|---|---|
| `users` | User accounts | `id`, `email`, `password_hash`, `full_name`, `pan` (encrypted), `aadhaar` (encrypted), `dob` (encrypted), `encryption_key` (DEK) |
| `transactions` | Income/Expense/Investment entries | `id`, `user_id`, `type`, `amount`, `category`, `date`, `payment_mode`, `is_flagged`, `is_recurring` |
| `goals` | Financial goals | `id`, `user_id`, `title`, `target_amount`, `current_amount`, `deadline`, `category` |
| `holdings` | Investment portfolio | `id`, `user_id`, `name`, `ticker`, `category`, `quantity`, `buy_price`, `invested_value`, `current_value` |
| `loans` | Active loans/EMIs | `id`, `user_id`, `name`, `loan_type`, `principal_amount`, `interest_rate`, `tenure_months`, `emi_amount`, `outstanding_principal` |
| `credit_cards` | Credit card details | `id`, `user_id`, `card_name`, `credit_limit`, `outstanding`, `due_date`, `interest_rate` |
| `credit_card_transactions` | CC transaction history | `id`, `user_id`, `card_id`, `amount`, `merchant`, `category`, `date` |
| `recurring_transactions` | SIPs, subscriptions | `id`, `user_id`, `name`, `amount`, `frequency`, `category`, `is_active` |
| `bank_accounts` | Linked bank accounts | `id`, `user_id`, `bank_name`, `balance`, `account_type` |
| `fixed_assets` | Physical assets (property, vehicle, gold) | `id`, `user_id`, `name`, `purchase_value`, `current_value`, `depreciation_rate` |
| `insurance_policies` | Insurance policies | `id`, `user_id`, `policy_name`, `type`, `premium`, `coverage` |
| `risk_profiles` | Risk assessment results | `user_id`, `profile`, `score`, `breakdown`, `answers` |
| `market_data` | Cached market prices | `key`, `price`, `change`, `change_pct`, `updated_at` |
| `budgets` | Category budgets | `user_id`, `category`, `limit`, `spent` |
| `visor_chat` | AI chat history | `id`, `user_id`, `role`, `content`, `created_at` |
| `chat_history` | Legacy AI chat | `id`, `user_id`, `messages` |
| `user_tax_deductions` | Manual tax deductions | `id`, `user_id`, `section`, `name`, `invested_amount` |
| `auto_tax_deductions` | Auto-detected deductions | `id`, `user_id`, `section`, `name`, `amount` |
| `journal_entries` | Double-entry bookkeeping | `id`, `user_id`, `date`, `entries` (debit/credit array) |
| `sip_suggestions` | AI-generated SIP suggestions | `id`, `user_id`, `fund_name`, `amount`, `rationale` |
| `cc_statement_history` | CC statement upload log | `id`, `user_id`, `filename`, `status`, `transactions_imported` |
| `gmail_tokens` | Gmail OAuth tokens (encrypted) | `user_id`, `access_token`, `refresh_token` |
| `gmail_oauth_states` | OAuth state parameters | `state`, `user_id` |
| `gmail_synced_msgs` | Synced Gmail message IDs | `user_id`, `message_id` |
| `gmail_sync_log` | Gmail sync history | `user_id`, `synced_at`, `count` |

---

## 6. Security Architecture

### 6.1 Data Encryption
- **At-Rest Encryption**: AES-256-GCM with per-user Data Encryption Keys (DEK)
- **Master Key**: Environment variable `ENCRYPTION_MASTER_KEY` encrypts/decrypts user DEKs
- **Encrypted Fields**: PAN, Aadhaar, DOB, Full Name, Loan account numbers, Gmail tokens
- **Pattern**: `ENC:` prefix on encrypted values; auto-decrypted in auth middleware

### 6.2 Authentication
- **JWT tokens** with HS256 signing, 30-day expiry
- **bcrypt** password hashing with automatic salt
- **Auto-logout**: Frontend detects 401 responses and triggers logout
- **PIN Lock**: Optional 4-digit PIN with biometric fallback (via SecurityContext)

### 6.3 API Security
- All endpoints require `Authorization: Bearer <token>` header
- User data isolation: every query filters by `user_id`
- CORS: Fully open for development (to be restricted in production)

---

## 7. Feature Details

### 7.1 Dashboard (Phase 1) — COMPLETE

**Financial Health Score V2** (0-1000 scale, 8 dimensions):
- Savings Rate (150 pts) — compares income vs expenses
- Investment Allocation (150 pts) — % of income invested
- Debt Management (125 pts) — EMI-to-income ratio
- Goal Progress (125 pts) — savings vs targets
- Spending Discipline (125 pts) — budget adherence
- Emergency Fund (125 pts) — months of expenses covered
- Diversification (100 pts) — asset class spread
- Insurance Coverage (100 pts) — policy adequacy

**Dashboard Components**:
| Component | Description |
|---|---|
| Financial Health V2 Card | Animated gauge, 8-dimension breakdown, share-as-image |
| Overview Section | Income/Expense/Investment/Savings stat cards with period toggle |
| Financial Goals | Jar-shaped SVG fill visualization, category colors, add/edit |
| Recent Transactions | Last 5 transactions with category icons and colors |
| Credit Cards Summary | Outstanding, limit, utilization bar, card count |
| Upcoming Dues | Next CC and loan payments due with countdown |
| Trend Analysis | Monthly income vs expense line chart (6 months) |
| Net Worth Card | Total assets minus liabilities with breakdown |
| Investment Summary | Total invested, current value, gain/loss, XIRR |
| AI Insight Card | GPT-5.2 generated personalized financial tip |

### 7.2 Credit Card Management (Phase 2) — COMPLETE

| Feature | Description |
|---|---|
| Card CRUD | Add/edit/delete credit cards with full details |
| Statement Upload | Parse CC statements (PDF) to auto-import transactions |
| Due Date Calendar | Visual calendar showing all CC due dates with countdown |
| Interest Calculator | Shows cost of minimum payments (the "minimum payment trap") |
| Rewards Tracker | Track points, cashback, miles across cards with INR equivalent |
| Best Card Recommender | AI-powered recommendation based on spending patterns |

### 7.3 EMI & SIP Analytics (Phase 3) — COMPLETE

| Feature | Description |
|---|---|
| Principal vs Interest Split | Visual breakdown of P vs I across all loans + per-loan |
| Prepayment Calculator | Compare tenure reduction vs EMI reduction, see total savings |
| SIP Analytics Dashboard | Track all active SIPs, total invested, projected value |
| Wealth Projector | 3-scenario projection (Conservative 8%, Moderate 12%, Aggressive 15%) |
| Goal Mapper | Map SIPs to financial goals, detect shortfalls, gap analysis |
| SIP-Goal Link/Unlink | Associate specific SIPs with goals via dedicated API endpoints |

### 7.4 Investments Screen — COMPLETE

| Component | Description |
|---|---|
| Market Ticker Bar | Live scrolling bar: Nifty 50, Sensex, Bank Nifty, Gold, Silver |
| Portfolio Overview | Allocation pie chart, total value, gain/loss |
| Holdings Table | Per-holding details with P&L, quantity, buy price |
| CAS Upload | Upload CAMS/KFintech CAS PDF to auto-import MF holdings |
| Risk Profile | 10-question assessment → Conservative/Moderate/Aggressive profile |
| Financial Goals | Jar visualization, category-based coloring, deadline tracking |
| Recurring Investments | Active SIPs and recurring investment summary |

### 7.5 Tax Planning Screen — COMPLETE

| Feature | Description |
|---|---|
| Tax Calculator | Old vs New regime comparison with recommendation |
| Tax Summary | Section-wise deduction breakdown (80C, 80D, 80E, etc.) |
| User Deductions | Manual entry of tax-saving investments |
| Auto Deductions | Auto-detected deductions from transaction history |
| Capital Gains | STCG/LTCG tracking from holdings data |
| Smart Tax Notifications | Alerts for advance tax deadlines, section limits |
| Deduction Progress Bar | Visual progress toward 80C and other section limits |
| Tax Planning Scan | AI-powered scan to find optimization opportunities |

### 7.6 Bookkeeping (Books Screen) — COMPLETE

| Feature | Description |
|---|---|
| Journal Entries | Double-entry journal with debit/credit validation |
| Chart of Accounts | Assets, Liabilities, Income, Expense, Equity accounts |
| General Ledger | Per-account transaction history with running balance |
| Profit & Loss | Income vs Expense statement for any period |
| Balance Sheet | Assets = Liabilities + Equity snapshot |
| PDF/Excel Export | Professional export of all financial statements |

### 7.7 Transaction Management — COMPLETE

| Feature | Description |
|---|---|
| Add Transaction | Type (income/expense/investment), category, amount, date, payment mode |
| Bank Statement Upload | Parse PDF/CSV statements from SBI, HDFC, ICICI, Axis, Kotak, etc. |
| Smart Flagging | Auto-flag suspicious/duplicate transactions |
| Flagged Review | Approve or reject flagged transactions |
| Recurring Detection | Auto-detect recurring patterns (SIPs, subscriptions) |
| Category Management | 40+ predefined categories with custom icons and colors |

### 7.8 Settings & Security — COMPLETE

| Feature | Description |
|---|---|
| Profile Management | View/edit profile, PAN/Aadhaar display (masked) |
| Theme Toggle | Dark/Light mode with system preference detection |
| PIN Lock | 4-digit PIN setup with biometric authentication |
| Data Export | Export all financial data as structured report |
| Visor AI Chat | Quick access to AI advisor from settings |
| Danger Zone | Delete account with confirmation |

### 7.9 Landing Page — COMPLETE

Full-featured marketing page with:
- Hero section with gradient animation
- Stats bar (users, assets tracked, calculations, languages)
- Feature showcase (12-feature grid)
- Financial Health Score preview
- Visor AI section with example conversations
- Jar Goals visualization showcase
- Security section highlighting encryption
- Call-to-action sections

---

## 8. Visor AI Agent — Detailed Architecture

### 8.1 Overview

The Visor AI Agent is an **India-first, multilingual, context-aware financial companion** that provides personalized financial advice based on the user's complete financial picture. It is NOT a generic chatbot — it has deep access to the user's actual financial data and can perform live market lookups and financial calculations.

### 8.2 LLM Configuration

| Parameter | Value |
|---|---|
| **Model** | OpenAI GPT-5.2 |
| **Access** | Via `emergentintegrations` library using Emergent LLM Key |
| **Session Management** | `LlmChat` class with user-specific session ID (`visor-{user_id}-{date}`) |
| **System Prompt** | 149 lines of India-specific financial instructions (see 8.4) |

### 8.3 Data Pipeline (How Visor AI Gets Context)

When a user sends a message to Visor AI, the following happens in sequence:

```
User Message
    │
    ▼
┌────────────────────────────────────────────────────────┐
│  STEP 1: SAVE USER MESSAGE                             │
│  → Stored in `visor_chat` collection with user_id      │
└────────────────────┬───────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────┐
│  STEP 2: GATHER COMPLETE FINANCIAL PROFILE             │
│  11 parallel MongoDB queries:                          │
│  ┌──────────────────────────────────────────────┐      │
│  │ • transactions (last 500)                     │     │
│  │ • goals                                       │     │
│  │ • risk_profiles                               │     │
│  │ • holdings (up to 100)                        │     │
│  │ • recurring_transactions (SIPs)               │     │
│  │ • budgets                                     │     │
│  │ • loans                                       │     │
│  │ • credit_cards                                │     │
│  │ • bank_accounts                               │     │
│  │ • fixed_assets                                │     │
│  │ • user_tax_deductions                         │     │
│  └──────────────────────────────────────────────┘      │
│  All fetched via asyncio.gather() for speed            │
└────────────────────┬───────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────┐
│  STEP 3: BUILD FINANCIAL CONTEXT STRING                │
│                                                        │
│  Computed metrics:                                     │
│  • Total Income, Expenses, Savings Rate               │
│  • Portfolio value (invested vs current), gain/loss %  │
│  • Category-wise expense breakdown (top 5)             │
│  • Monthly trends (last 6 months)                      │
│  • Per-holding P&L summary (top 15 holdings)           │
│  • Goals progress (current/target for each)            │
│  • SIP list with amounts and frequencies               │
│  • Budget utilization per category                     │
│  • Loan details with EMI and interest rates            │
│  • Credit card balances and limits                     │
│  • Bank account balances                               │
│  • Fixed asset values                                  │
│  • Tax deduction claims                                │
│  • Risk profile (score and type)                       │
│  • Recent 8 transactions                               │
│                                                        │
│  Also includes: screen_context (which app screen       │
│  the user is currently on)                             │
└────────────────────┬───────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────┐
│  STEP 4: LIVE MARKET PRICES (if tickers detected)      │
│                                                        │
│  Ticker Detection:                                     │
│  • TICKER_MAP: 70+ Indian companies/indices mapped     │
│    (e.g., "reliance" → "RELIANCE.NS",                  │
│     "gold" → "INDIAN_MARKET:Gold")                     │
│  • Pattern matching on user message text               │
│  • Direct symbol detection (3-15 char uppercase)       │
│  • Stop word filtering (200+ words including Hindi)    │
│                                                        │
│  Price Sources:                                        │
│  • Indian commodities → MongoDB market_data cache      │
│    (Gold, Silver — refreshed from GoldAPI.io)          │
│  • Stocks/Indices → Yahoo Finance (yfinance library)   │
│    via ThreadPoolExecutor (non-blocking)               │
│  • Returns: price, change, change%, market cap         │
└────────────────────┬───────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────┐
│  STEP 5: WEB SEARCH FOR NEWS (if news trigger found)   │
│                                                        │
│  Trigger words (English + Hindi):                      │
│  "news", "khabar", "latest", "aaj", "budget", "rbi",  │
│  "sebi", "ipo", "quarterly", "results", "taza", etc.  │
│                                                        │
│  Process:                                              │
│  1. Translate Hindi words to English                   │
│  2. DuckDuckGo text search (top 5 results)             │
│  3. Format as "RECENT FINANCIAL NEWS & UPDATES"        │
└────────────────────┬───────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────┐
│  STEP 6: AUTO-CALCULATOR (if calculation detected)     │
│                                                        │
│  Intent detection via regex on user message:           │
│  • SIP Calculator (with step-up option)                │
│  • EMI Calculator (home/car/personal loan)             │
│  • Compound Interest / FD Calculator                   │
│  • CAGR Calculator                                     │
│  • FIRE Number Calculator                              │
│  • PPF Calculator                                      │
│  • HRA Exemption Calculator                            │
│  • Gratuity Calculator                                 │
│  • Section 80C Tax Savings Calculator                  │
│                                                        │
│  Number extraction handles: lakhs, crores, k notation  │
│  Example: "5 lakh SIP" → ₹500,000                     │
└────────────────────┬───────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────┐
│  STEP 7: CHAT HISTORY (last 12 messages)               │
│  → Loaded from visor_chat collection for continuity    │
└────────────────────┬───────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────┐
│  STEP 8: SEND TO GPT-5.2                               │
│                                                        │
│  Full prompt = System Prompt                           │
│               + Financial Profile Context              │
│               + Live Prices (if any)                   │
│               + News Context (if any)                  │
│               + Calculator Results (if any)            │
│               + Chat History (last 12)                 │
│               + "User: {message}"                      │
│                                                        │
│  LLM Library: emergentintegrations.llm.chat            │
│  Class: LlmChat(api_key, session_id, system_message)   │
│  Model: .with_model("openai", "gpt-5.2")              │
│  Call: await chat.send_message(UserMessage(text=...))   │
└────────────────────┬───────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────┐
│  STEP 9: SAVE & RETURN RESPONSE                        │
│  → AI response stored in visor_chat collection         │
│  → Returns: response text, calculator result, metadata │
└────────────────────────────────────────────────────────┘
```

### 8.4 System Prompt Design

The Visor AI system prompt (`/app/backend/services/visor_prompt.py`) is a 149-line instruction set that defines:

**Identity & Personality**:
- Warm, professional "finance companion" — NOT a chatbot
- Default language: Professional Hinglish (Hindi + English mix)
- Never exposes internal systems, APIs, or technical details

**Multilingual Capability**:
- Understands all 22 scheduled Indian languages in TRANSLITERATED English script
- Examples: Tamil ("enna mutual fund invest pannanum?"), Bengali ("amar portfolio ki bhalo ache?")
- Adapts response language based on user's language after 2+ messages

**India-Specific Financial Knowledge**:
- Income Tax Act 1961 — ALL major sections (80C through 80U, 10(10D), 10(13A), 24(b))
- Old vs New Tax Regime comparison with personalized recommendation
- Capital Gains: STCG (111A, 15%), LTCG (112A, 12.5% above Rs 1.25L)
- All investment types: MFs, PPF (7.1%), EPF (8.25%), NPS, SGBs, REITs, InvITs, Crypto (30% VDA tax)
- Banking: FD/RD rates, DICGC ₹5L insurance, term/health/ULIP analysis
- Regulatory bodies: SEBI, RBI, IRDAI, PFRDA, AMFI
- Regional concepts: chit funds, hundi, committee/kitty, bishi
- Budget 2025-26 changes

**Data-Driven Response Rules**:
- MUST cite real numbers from user's data
- MUST benchmark against Indian standards (savings rate >20% = good, etc.)
- MUST lead with user's #1 priority gap
- MUST show math briefly
- MUST give specific next steps (how much, which instrument, when)

**Calculator Awareness**:
- Knows about all 9 built-in calculators
- Integrates calculator results naturally into conversational responses

### 8.5 Visor AI Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/visor-ai/chat` | POST | Main chat endpoint — full context pipeline described above |
| `/api/visor-ai/history` | GET | Retrieve all chat messages for the user (sorted by time) |
| `/api/visor-ai/history` | DELETE | Clear all chat history for the user |
| `/api/visor-ai/message/{id}` | DELETE | Delete a specific message |

### 8.6 Fallback Behavior

If the LLM call fails (network error, rate limit, etc.), Visor returns a pre-defined fallback tip:
> "Abhi connection mein thoda issue aa raha hai. Ek baar phir try kar. Tab tak ye tip le: Apne monthly expenses review kar aur jo subscriptions use nahi ho rahe, unhe cancel kar — chhoti savings bhi badi hoti hain!"

---

### 8.8 Voice Conversation Capability (NEW — March 19, 2026)

**Architecture**: Voice Skin over Existing Pipeline (Approach A)

```
User Speaks → [ElevenLabs STT] → Text → [Existing Visor AI Pipeline] → AI Text → [ElevenLabs TTS] → User Hears
```

**Key Design Decisions**:
- Voice uses the **exact same** GPT-5.2 pipeline as text — same context, same guardrails, same calculators
- Unified chat history: voice and text messages stored in the same `visor_chat` collection with `input_type` field
- AI speaks back ONLY when user sends a voice message; text input → text response only
- Both push-to-hold and tap-to-toggle mic input supported

**Speech-to-Text (STT)**:
- Provider: ElevenLabs Scribe v1 (`scribe_v1`)
- Supports Hindi, English, Tamil, Telugu, Bengali, Marathi, Gujarati, and other Indian languages
- Handles Hinglish code-mixing
- **Multilingual ticker detection**: When STT outputs Devanagari/regional scripts, the `_transliterate_hindi()` function converts Hindi financial terms to English equivalents before ticker detection. The `TICKER_MAP` also includes direct Devanagari keyword entries for 50+ terms (stocks, commodities, indices) plus Tamil, Telugu, Bengali, Marathi, and Gujarati commodity keywords.

**Text-to-Speech (TTS)**:
- Provider: ElevenLabs Multilingual v2 (`eleven_multilingual_v2`)
- Voice: Daniel — Steady Broadcaster (`onwK4e9ZLuTAKqWW03F9`) — calm, professional
- Voice Settings: stability=0.6, similarity_boost=0.75, style=0.3, speaker_boost=true

**New Backend Files**:
- `/app/backend/services/visor_engine.py` — Extracted shared AI processing pipeline (used by both text + voice endpoints)
- `/app/backend/routes/visor_voice.py` — Voice chat endpoint (STT → engine → TTS)
- Refactored `/app/backend/routes/visor_ai.py` to use shared engine

**New API Endpoint**:
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/visor-ai/voice-chat` | Multipart: audio_file + screen_context → returns text + base64 audio |

**Frontend Changes** (AIAdvisorChat.tsx):
- Mic button next to send button (tap-to-toggle + hold-to-send)
- Recording overlay with timer and cancel option
- Audio playback button on AI voice responses
- Voice badge indicator on user voice messages
- Uses `expo-av` for audio recording and playback

**3rd Party Integration**:
- ElevenLabs API (Starter plan, API key in backend .env)
- `pip install elevenlabs` + `yarn add expo-av`



## 9. Complete API Endpoint Reference

### Authentication (2 endpoints)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login, returns JWT |
| GET | `/api/auth/profile` | Get user profile |
| DELETE | `/api/auth/delete-account` | Delete account + all data |

### Transactions (6 endpoints)
| POST | `/api/transactions` | Create transaction |
| GET | `/api/transactions` | List transactions |
| PUT | `/api/transactions/{id}` | Update transaction |
| DELETE | `/api/transactions/{id}` | Delete transaction |
| POST | `/api/approve-flagged/{id}` | Approve flagged transaction |
| POST | `/api/reject-flagged/{id}` | Reject flagged transaction |
| GET | `/api/flagged-transactions` | List flagged transactions |

### Goals (4 endpoints)
| POST | `/api/goals` | Create goal |
| GET | `/api/goals` | List goals |
| PUT | `/api/goals/{id}` | Update goal |
| DELETE | `/api/goals/{id}` | Delete goal |

### Dashboard (8 endpoints)
| GET | `/api/dashboard/stats` | Overview stats |
| GET | `/api/dashboard/monthly-trends` | Monthly income/expense trends |
| GET | `/api/dashboard/smart-alerts` | Smart financial alerts |
| GET | `/api/dashboard/financial-health-v2` | 8-dimension health score |
| GET | `/api/dashboard/net-worth` | Net worth breakdown |
| GET | `/api/dashboard/investment-summary` | Investment summary + XIRR |
| GET | `/api/dashboard/upcoming-dues` | CC + Loan due dates |
| GET | `/api/dashboard/ai-insight` | GPT-5.2 personalized insight |

### Credit Cards (11 endpoints)
| POST | `/api/credit-cards` | Add credit card |
| GET | `/api/credit-cards` | List credit cards |
| PUT | `/api/credit-cards/{id}` | Update credit card |
| DELETE | `/api/credit-cards/{id}` | Delete credit card |
| GET | `/api/credit-cards/due-calendar` | Due date calendar |
| POST | `/api/credit-cards/interest-calculator` | Interest calculation |
| GET | `/api/credit-cards/rewards` | Rewards summary |
| POST | `/api/credit-cards/recommend` | AI card recommender |

### EMI & SIP Analytics (7 endpoints)
| GET | `/api/emi-analytics/overview` | P vs I split, loan breakdown |
| POST | `/api/emi-analytics/prepayment` | Prepayment savings calculator |
| GET | `/api/sip-analytics/dashboard` | SIP performance analytics |
| POST | `/api/sip-analytics/wealth-projection` | 3-scenario projection |
| POST | `/api/sip-analytics/goal-map` | SIP-to-goal mapping |
| POST | `/api/sip-analytics/link-sip` | Link SIP to goal |
| POST | `/api/sip-analytics/unlink-sip` | Unlink SIP from goal |

### Holdings & Portfolio (6 endpoints)
| POST | `/api/holdings/upload-cas` | Upload CAS PDF |
| GET | `/api/holdings` | List holdings |
| GET | `/api/holdings/live` | Holdings with live prices |
| PUT | `/api/holdings/{id}` | Update holding |
| DELETE | `/api/holdings/{id}` | Delete holding |
| GET | `/api/portfolio-overview` | Portfolio allocation |
| GET | `/api/portfolio-rebalancing` | Rebalancing suggestions |

### Tax (6 endpoints)
| GET | `/api/tax-calculator` | Old vs New regime comparison |
| GET | `/api/tax-summary` | Tax deduction summary |
| GET | `/api/capital-gains` | Capital gains (STCG/LTCG) |
| POST | `/api/tax-planning/scan` | AI tax optimization scan |

### Market Data (2 endpoints)
| GET | `/api/market-data` | All market data (indices, commodities) |
| POST | `/api/market-data/refresh` | Force refresh prices |

### Bookkeeping & Exports (10+ endpoints)
| GET | `/api/books/balance-sheet` | Balance sheet |
| GET | `/api/books/pnl` | Profit & Loss statement |
| GET | `/api/books/ledger` | General ledger |
| GET | `/api/journal` | Journal entries |
| GET | `/api/balance-sheet/pdf` | Export balance sheet as PDF |
| GET | `/api/pnl/pdf` | Export P&L as PDF |
| GET | `/api/ledger/pdf` | Export ledger as PDF |
| GET | `/api/balance-sheet/excel` | Export balance sheet as Excel |

### Visor AI (4 endpoints)
| POST | `/api/visor-ai/chat` | AI chat with full financial context |
| GET | `/api/visor-ai/history` | Chat history |
| DELETE | `/api/visor-ai/history` | Clear history |
| DELETE | `/api/visor-ai/message/{id}` | Delete message |

---

## 10. Implementation Status

### COMPLETED
- [x] Phase 0: Bug Fixes (FAB button, statement upload)
- [x] Phase 1: Dashboard V2 (Health Score, Net Worth, XIRR, AI Insight, Share Score)
- [x] Phase 2: Credit Card Enhancements (Calendar, Interest Calc, Rewards, AI Recommender)
- [x] Phase 3: EMI & SIP Analytics (P vs I, Prepayment, Wealth Projector, Goal Mapper)
- [x] UI/UX Overhaul: Jar goals, dashboard reorder, AI icon, consistent colors
- [x] Landing Page: Full-featured marketing page
- [x] Expo QR Page: Auto-refreshing QR code for Expo Go preview
- [x] Color Consistency: Goal categories unified across Dashboard and Invest screen

### NOT STARTED
- [ ] Phase 4: Advanced Tax Screen (Tax-loss Harvesting, Advance Tax alerts)
- [ ] Phase 5: Enhanced Visor AI (web search integration, deeper context)
- [ ] Phase 6: Gmail Integration (auto-import transactions from email)
- [ ] Dashboard refactoring (index.tsx is 1972 lines)
- [ ] Investments refactoring (investments.tsx is 1734 lines)

---

## 11. Environment Configuration

### Backend `.env`
| Variable | Purpose |
|---|---|
| `MONGO_URL` | MongoDB connection string |
| `DB_NAME` | Database name (`visor_finance`) |
| `JWT_SECRET` | JWT signing secret |
| `EMERGENT_LLM_KEY` | Universal LLM key for GPT-5.2 |
| `ENCRYPTION_MASTER_KEY` | AES-256 master key for PII encryption |
| `GOLDAPI_KEY` | Gold/Silver price API key |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth secret |

### Frontend `.env`
| Variable | Purpose |
|---|---|
| `EXPO_PUBLIC_BACKEND_URL` | Backend API base URL |
| `REACT_NATIVE_PACKAGER_HOSTNAME` | Cloudflare tunnel hostname for Expo Go |
| `EXPO_PACKAGER_PROXY_URL` | Full tunnel URL |

---

## 12. Market Data Scheduler

The backend runs a background market data refresh scheduler:
- **Schedule**: 4 times daily at IST 09:25, 11:30, 12:30, 15:15 (Indian market hours)
- **Sources**: GoldAPI.io (Gold 24K 10g, Silver 1Kg), Yahoo Finance (Nifty 50, Sensex, Bank Nifty)
- **Storage**: Cached in `market_data` MongoDB collection
- **Domestic Premium**: Gold +7.5%, Silver +15.5% (for import duties/GST)
