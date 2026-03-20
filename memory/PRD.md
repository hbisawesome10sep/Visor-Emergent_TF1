# VISOR FINANCE — Product Requirements Document (PRD)
**Version**: 3.0 — Full Rewrite  
**Last Updated**: March 20, 2026  
**Status**: Active Development  

---

## 1. Original Problem Statement

Build a **comprehensive personal finance management application** named **Visor**, tailored exclusively for Indian accounting standards and Indian users. The app covers:

- Real-time financial dashboard with AI-generated health scoring
- Transaction management (income, expense, investment) with categories
- Credit card tracking with statement import, due dates, rewards, and interest calculator
- EMI (Equated Monthly Installment) tracking and prepayment analysis
- SIP (Systematic Investment Plan) management with goal mapping
- Investment portfolio (Stocks + Mutual Funds) with live prices from XLSX statement import
- Tax planning (80C, 80D deductions, advance tax alerts)
- AI-powered voice assistant (Visor AI) with STT/TTS via ElevenLabs
- Financial goals with Jar-style visual progress
- Net worth tracking across assets and liabilities

---

## 2. User Personas

| Persona | Description |
|---|---|
| **Primary User** | Indian individual investor (25–45 age), salaried or self-employed, actively managing investments, credit cards, and tax |
| **Secondary User** | Small business owner / freelancer tracking income, expenses, and tax liabilities |
| **Demo User** | `rajesh@visor.demo` / `Demo@123` — pre-seeded with realistic Indian financial data |
| **Real Data User** | `raj@visor.best` / `Demo@123` — has uploaded actual Groww/Zerodha XLSX statements |

---

## 3. Tech Stack

| Layer | Technology | Details |
|---|---|---|
| **Frontend** | React Native (Expo SDK 52) + TypeScript | Web + iOS + Android via Expo Go |
| **Backend** | FastAPI (Python 3.11) | Async, Motor MongoDB driver |
| **Database** | MongoDB | 27+ collections, field-level encryption for PII |
| **AI Engine** | OpenAI GPT-5.2 (via `emergentintegrations`) | Emergent Universal LLM Key |
| **Voice STT** | ElevenLabs Speech-to-Text | Multilingual, Hindi/English |
| **Voice TTS** | ElevenLabs Text-to-Speech | Streaming audio responses |
| **Market Data** | Yahoo Finance (`yfinance`) | NSE/BSE live stock prices |
| **MF Data** | `mfapi.in` | Free public API for Indian MF NAVs |
| **Gold/Silver** | GoldAPI.io | INR-denominated spot prices |
| **Encryption** | AES-256-GCM | PAN, Aadhaar, DOB, account numbers |
| **Auth** | JWT (HS256, 30-day expiry) + bcrypt | PIN lock via `react-native-keychain` |
| **Tunnel** | Cloudflared (Quick Tunnel) | `trycloudflare.com` URL for Expo Go |
| **UI Framework** | Custom design system | DM Sans font, jewel-tone accent palette |

### Design System
- **Primary font**: DM Sans (all weights)
- **Accent palette**: `Emerald (#10B981)`, `Ruby (#EF4444)`, `Amber (#F59E0B)`, `Sapphire (#3B82F6)`, `Violet (#8B5CF6)`, `Teal (#14B8A6)`
- **Theme**: Dark/Light with iOS-style `useColorScheme` + manual toggle
- **Icons**: `@expo/vector-icons` (MaterialCommunityIcons) + Lucide React
- **Animations**: React Native `Animated` API + `expo-linear-gradient`

---

## 4. App Architecture

```
/app
├── backend/
│   ├── server.py                    # FastAPI app, daily scheduler
│   ├── routes/
│   │   ├── auth.py                  # Login, register, PIN
│   │   ├── transactions.py          # CRUD, bulk import, CSV/PDF
│   │   ├── dashboard.py             # Stats, health score, net worth, insights
│   │   ├── goals.py                 # Financial goals CRUD
│   │   ├── credit_cards.py          # CC management, statements, rewards
│   │   ├── loans.py                 # EMI/loan tracking
│   │   ├── recurring.py             # Recurring transactions (SIPs, EMIs)
│   │   ├── holdings.py              # Portfolio holdings CRUD + live prices
│   │   ├── statement_upload.py      # Groww/Zerodha XLSX parser + SIP suggestions
│   │   ├── emi_analytics.py         # EMI overview, prepayment, P vs I
│   │   ├── sip_analytics.py         # SIP overview, goal mapping, link/unlink
│   │   ├── portfolio_rebalancing.py # Portfolio allocation + rebalancing suggestions
│   │   ├── market_data.py           # Nifty, SENSEX, Bank Nifty, Gold, Silver
│   │   ├── visor_ai.py              # AI chat + voice chat endpoint
│   │   ├── tax.py                   # Tax deductions, 80C/80D tracker
│   │   ├── settings.py              # User settings, risk profile, Gmail sync
│   │   ├── exports.py               # PDF/CSV export endpoints
│   │   ├── expo_qr.py               # Expo Go QR page + /api/expo/status
│   │   └── bookkeeping.py           # Business P&L ledger
│   ├── services/
│   │   ├── statement_parser.py      # XLSX parsers for Groww MF + Zerodha Stocks
│   │   └── holdings_price_updater.py # Live price fetch (yfinance + mfapi.in)
│   ├── middleware/
│   │   └── auth_middleware.py       # JWT verification
│   └── requirements.txt
├── frontend/
│   ├── app/(tabs)/
│   │   ├── index.tsx                # Dashboard screen (~1973 lines)
│   │   ├── transactions.tsx         # Transactions screen (~2412 lines)
│   │   ├── insights.tsx             # Insights + Financial Health
│   │   ├── investments.tsx          # Investment portfolio (~1895 lines)
│   │   └── tax.tsx                  # Tax planning screen
│   ├── src/
│   │   ├── components/
│   │   │   ├── dashboard/           # InvestmentSummaryCard, FinancialGoals, etc.
│   │   │   ├── emi-sip/             # GoalMapper, WealthProjector, SIPDashboard
│   │   │   ├── investments/         # StockHoldingsCard, MutualFundHoldingsCard
│   │   │   ├── JarProgressView.tsx  # Animated jar fill progress visualization
│   │   │   ├── TrendChart.tsx       # SVG line chart for trends
│   │   │   └── MonthlyTrendCard.tsx # Monthly bar chart with savings rate
│   │   ├── context/
│   │   │   ├── AuthContext.tsx      # JWT auth state + token management
│   │   │   ├── ThemeContext.tsx     # Dark/Light theme toggle
│   │   │   └── SecurityContext.tsx  # PIN lock state
│   │   └── utils/
│   │       ├── api.ts               # Typed API request helper
│   │       ├── formatters.ts        # INR formatting utilities
│   │       └── theme.ts             # Color constants (Accent palette)
└── memory/
    ├── PRD.md                       # This file
    ├── CHANGELOG.md                 # Append-only change log
    └── ROADMAP.md                   # Prioritized backlog
```

---

## 5. Feature Inventory — Completed

### 5.1 Authentication & Security
| Feature | Details |
|---|---|
| Register / Login | Email + password, bcrypt hash, JWT 30-day token |
| PIN Lock | 4-digit PIN gate on app resume, stored in device keychain |
| PII Encryption | AES-256-GCM for PAN, Aadhaar, DOB, account numbers at rest |
| Auto-logout | Token expiry detection with graceful redirect |
| Delete Account | Full data purge endpoint + confirmation modal |

### 5.2 Dashboard (index.tsx)
| Feature | Details |
|---|---|
| Period Filter | Q / M / Y / All toggles; drives all dashboard data |
| Stats Bar | Income, Expenses, Net, Investments for selected period |
| Trend Analysis Card | SVG line chart (Income + Expenses + Investments) with smart X-axis decimation by frequency (Fixed March 20) |
| Smart Insights (flip) | Tap card to flip → AI-generated bullet insights |
| Financial Health Score | 0–100 composite score (savings, investments, spending, goals) |
| Spending Breakdown | Category pie chart with colour-coded legend |
| Investment Summary | Current value, invested amount, P&L, XIRR |
| Net Worth Card | Assets − Liabilities snapshot |
| Financial Goals (Jar) | Jar-style animated fill for each goal with progress % |
| Upcoming Dues | Next EMI / SIP / recurring payment reminders |
| AI Insight Banner | Daily AI-generated one-liner about finances |
| Share Score | Share financial health score as image card |
| Market Ticker | Live Nifty 50, SENSEX, BankNifty, Gold, Silver |

### 5.3 Transactions (transactions.tsx)
| Feature | Details |
|---|---|
| Period Filter | Q / M / Y / All / **C (Custom date range)** toggle (Added March 20) |
| Custom Date Range | From + To date pickers with Apply button; Android native + iOS modal pickers |
| Transaction Types | Income / Expense / Investment / Credit Card |
| Categories | 20+ Indian-context categories (UPI, NEFT, ATM, etc.) |
| Split Transactions | Split a transaction across N people |
| Recurring Detection | Auto-detect EMI/SIP patterns, flag for review |
| Bulk Import | CSV upload + PDF statement parsing |
| Search & Filter | Full-text search + category filter pills |
| Tax Eligibility | Inline hint for 80C/80D-eligible transactions |
| Payment Mode | Cash, UPI, Net Banking, Credit Card, Debit Card |

### 5.4 Investments (investments.tsx)
| Feature | Details |
|---|---|
| Portfolio Overview | Allocation donut chart (Stocks, MF, FD, Gold, etc.) |
| Stock Holdings Card | Per-holding: name, ticker, qty, buy price, current value, P&L, P&L% |
| Mutual Fund Holdings Card | Per-holding: name, ISIN, units, buy NAV, current NAV, P&L |
| Live Prices | "Live Prices" button → calls `/api/holdings/refresh-prices` using yfinance + mfapi.in |
| Daily Auto-Refresh | Background scheduler in server.py refreshes all holdings prices after market close |
| Import Statement | Upload Groww XLSX (MF) or Zerodha XLSX (Stocks) → auto-parses and upserts holdings |
| Clear All Holdings | Button to wipe all holdings for user |
| Auto SIP Suggestions | On MF statement upload → auto-creates pending SIP suggestions |
| Portfolio Rebalancing | Target allocation vs current + rebalancing recommendations |
| Wealth Projector | SIP + lump sum future value calculator with CAGR assumptions |
| SIP Dashboard | Active SIPs, total monthly outflow, XIRR, next payment dates |
| Goal Mapping | Map SIPs to financial goals; shortfall analysis (moved to screen bottom, March 20) |
| Unmapped SIPs | Horizontal scroll chips for linking (Fixed March 20) |
| Financial Goals (Jar) | Jar goals with invest-screen context |
| Holdings Header | Clean 2-row header: title + Live Prices pill | Import Statement button (Fixed March 20) |

### 5.5 Credit Cards
| Feature | Details |
|---|---|
| Card List | All credit cards with limit, used, available, due date |
| Statement Import | PDF / CSV parser for HDFC, ICICI, SBI Card, Axis, Kotak |
| Payment Calendar | Visual calendar showing due dates and payment history |
| Interest Calculator | APR-based daily/monthly interest simulation |
| Rewards Tracker | Points balance, redemption history, expiry alerts |
| AI Card Recommender | AI recommends best card for a given spend category |
| Credit Utilisation | % utilisation with risk colour coding |

### 5.6 EMI & Loans
| Feature | Details |
|---|---|
| Loan Tracker | Home, Car, Personal, Education loans with balance |
| EMI Schedule | Month-by-month P vs I breakdown |
| Prepayment Simulator | Impact of lump-sum prepayment on tenure/interest saved |
| EMI Overview | Total monthly EMI outflow, total outstanding |
| Foreclosure Calculator | Cost to close loan early |

### 5.7 SIP Analytics
| Feature | Details |
|---|---|
| SIP List | All active SIPs with fund name, amount, start date, goal |
| Monthly Outflow | Total SIP debit per month |
| XIRR per SIP | Individual return calculation |
| Goal Mapper | Map/unlink SIPs to goals; see shortfall per goal |
| Wealth Projector | Future value at various CAGR rates (8%, 10%, 12%, 15%) |

### 5.8 Insights Screen
| Feature | Details |
|---|---|
| Financial Health Score | 0–100 composite score with category breakdown |
| Score Breakdown | Savings rate, investment rate, spending pattern, goal progress |
| Actionable Insights | AI-generated suggestions with priority labels |
| Monthly Savings Trend | 6-month bar chart with savings rate % per month |
| Portfolio XIRR | Overall annualised return across all investments |

### 5.9 Tax Screen
| Feature | Details |
|---|---|
| 80C Tracker | PPF, ELSS, LIC, tuition fees — progress towards ₹1.5L limit |
| 80D Tracker | Health insurance premium deductions |
| HRA Calculator | HRA exemption computation |
| Tax Summary | Estimated tax liability for the FY |
| Deduction Suggestions | AI suggestions to optimise deductions |

### 5.10 Settings Screen
| Feature | Details |
|---|---|
| Profile Edit | Name, DOB, PAN (encrypted), Aadhaar (encrypted) |
| Security | PIN enable/disable, biometrics |
| Theme | Dark / Light / System toggle |
| Risk Profile | Questionnaire-driven risk tolerance (Conservative/Moderate/Aggressive) |
| Investment Preferences | Expected return %, home purchase timeline, etc. |
| Statement Import | Credit card statement PDF/CSV upload |
| Data Export | Transactions CSV / PDF export |
| Gmail Sync | OAuth-based email scan for bank transaction emails |
| Delete Account | Full data purge |
| **Mobile Preview (QR)** | "Preview on Mobile (Expo Go)" button → opens `/api/expo/qr` (Added March 20) |
| App Info | Version, build info |

### 5.11 Voice AI (Visor AI)
| Feature | Details |
|---|---|
| Text Chat | Multi-turn conversation with full financial context injection |
| Voice Chat | ElevenLabs STT → GPT-5.2 → ElevenLabs TTS pipeline |
| Multilingual | Hindi + English; ticker detection in both languages |
| Financial Context | User's balance, recent transactions, holdings, goals injected into system prompt |
| FAB Button | Floating action button on Dashboard; accessible from any tab |

### 5.12 Expo Go QR Preview
| Feature | Details |
|---|---|
| QR Code Page | `/api/expo/qr` — auto-refreshing HTML page (15s interval) |
| Cloudflare Tunnel | `pete-tunes-ordering-functional.trycloudflare.com` |
| Status Check | `/api/expo/status` returns JSON with tunnel URL + is_active |
| Tabs | "Expo Go (Mobile)" and "Web Preview" tabs on the page |
| App Link | "Preview on Mobile" button in Settings → opens the QR page (Added March 20) |

---

## 6. Key API Endpoints

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login, returns JWT token |
| GET | `/api/auth/me` | Get current user profile |
| PUT | `/api/auth/profile` | Update profile |
| DELETE | `/api/auth/delete-account` | Full account deletion |
| POST | `/api/auth/set-pin` | Set PIN |
| POST | `/api/auth/verify-pin` | Verify PIN |

### Dashboard
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/dashboard/stats` | Period stats (income, expenses, trend_data, health_score) |
| GET | `/api/dashboard/financial-health-v2` | Detailed health score breakdown |
| GET | `/api/dashboard/investment-summary` | Investment card data |
| GET | `/api/dashboard/net-worth` | Net worth (assets − liabilities) |
| GET | `/api/dashboard/ai-insight` | Daily AI insight (cached 1hr) |
| GET | `/api/dashboard/upcoming-dues` | Next EMI/SIP/CC payments |

### Transactions
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/transactions` | List with filter (type, category, start/end date, search) |
| POST | `/api/transactions` | Create transaction |
| PUT | `/api/transactions/{id}` | Update transaction |
| DELETE | `/api/transactions/{id}` | Delete transaction |
| POST | `/api/transactions/bulk-import` | CSV bulk import |
| GET | `/api/transactions/flagged` | Potential EMI/SIP transactions |

### Investments & Holdings
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/holdings` | All holdings |
| POST | `/api/holdings` | Add manual holding |
| GET | `/api/holdings/live` | Holdings with live prices |
| POST | `/api/holdings/refresh-prices` | Trigger live price refresh |
| DELETE | `/api/holdings/clear-all` | Delete all holdings |
| POST | `/api/upload-statement` | Upload Groww/Zerodha XLSX |
| GET | `/api/portfolio-overview` | Allocation breakdown |
| GET | `/api/portfolio-rebalancing` | Rebalancing suggestions |
| GET | `/api/market-data` | Live Nifty/Gold/Silver |

### Goals
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/goals` | List goals |
| POST | `/api/goals` | Create goal |
| PUT | `/api/goals/{id}` | Update goal |
| DELETE | `/api/goals/{id}` | Delete goal |

### SIP Analytics
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/sip-analytics/goal-map` | SIP-to-goal mapping analysis |
| POST | `/api/sip-analytics/link-sip` | Link SIP to goal |
| POST | `/api/sip-analytics/unlink-sip` | Unlink SIP from goal |
| GET | `/api/sip-suggestions` | Pending SIP suggestions |
| PUT | `/api/sip-suggestions/{id}/approve` | Approve SIP suggestion |
| DELETE | `/api/sip-suggestions/{id}` | Dismiss suggestion |

### EMI Analytics
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/emi-analytics/overview` | EMI summary + all loans |
| POST | `/api/emi-analytics/prepayment` | Prepayment simulation |

### AI & Voice
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/visor-ai/chat` | Text chat with AI |
| POST | `/api/visor-ai/voice-chat` | Voice chat (STT+TTS pipeline) |

### Expo Preview
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/expo/qr` | HTML QR code page (auto-refresh) |
| GET | `/api/expo/status` | JSON tunnel status |

---

## 7. Database Schema (MongoDB Collections)

### Core Collections
| Collection | Key Fields |
|---|---|
| `users` | `email`, `hashed_password`, `name`, `pin_hash`, `settings`, `created_at` |
| `transactions` | `user_id`, `type`, `amount`, `category`, `date`, `description`, `payment_mode`, `is_recurring`, `is_split` |
| `goals` | `user_id`, `title`, `target_amount`, `current_amount`, `deadline`, `category` |
| `holdings` | `user_id`, `name`, `ticker`, `isin`, `category`, `quantity`, `buy_price`, `current_price`, `price_updated_at` |
| `loans` | `user_id`, `name`, `type`, `principal`, `outstanding`, `emi_amount`, `interest_rate`, `tenure_months` |
| `credit_cards` | `user_id`, `name`, `bank`, `limit`, `current_balance`, `due_date`, `billing_cycle` |
| `recurring_transactions` | `user_id`, `name`, `amount`, `category`, `frequency`, `next_date`, `goal_id` (nullable) |
| `bank_accounts` | `user_id`, `bank`, `account_type`, `balance`, `account_number` (encrypted) |

### Analytics Collections
| Collection | Key Fields |
|---|---|
| `risk_profiles` | `user_id`, `risk_tolerance`, `investment_horizon`, `expected_return` |
| `sip_suggestions` | `user_id`, `name`, `amount`, `status` (pending/approved/dismissed) |
| `user_tax_deductions` | `user_id`, `section`, `description`, `amount`, `financial_year` |
| `market_data` | `ticker`, `price`, `updated_at` (cached 30 min) |
| `visor_chat` | `user_id`, `session_id`, `role`, `content`, `created_at` |
| `fixed_assets` | `user_id`, `name`, `type`, `purchase_value`, `current_value` |

---

## 8. Environment Configuration

### Backend `.env`
| Variable | Purpose |
|---|---|
| `MONGO_URL` | MongoDB connection string |
| `DB_NAME` | Database name (`visor_finance`) |
| `JWT_SECRET` | JWT signing secret (HS256) |
| `EMERGENT_LLM_KEY` | Universal LLM key for GPT-5.2, Claude, Gemini |
| `ENCRYPTION_MASTER_KEY` | AES-256 master key for PII encryption |
| `GOLDAPI_KEY` | Gold/Silver spot price API |
| `ELEVENLABS_API_KEY` | ElevenLabs STT/TTS |

### Frontend `.env`
| Variable | Purpose |
|---|---|
| `EXPO_PUBLIC_BACKEND_URL` | Backend API base URL (external) |
| `EXPO_PACKAGER_PROXY_URL` | Cloudflare tunnel URL for Expo Go |

---

## 9. Third-Party Integrations

| Integration | Library / API | Purpose |
|---|---|---|
| OpenAI GPT-5.2 | `emergentintegrations` | Visor AI chat, insights, recommendations |
| ElevenLabs | `elevenlabs` Python SDK | Voice STT + TTS |
| Yahoo Finance | `yfinance` | Live NSE/BSE stock prices |
| mfapi.in | `requests` | Indian Mutual Fund NAV data |
| GoldAPI.io | `requests` | Live Gold/Silver INR prices |
| Cloudflare Tunnel | `cloudflared` binary | Expo Go mobile preview tunnel |

---

## 10. Test Credentials

| Account | Email | Password | Purpose |
|---|---|---|---|
| Demo | `rajesh@visor.demo` | `Demo@123` | Pre-seeded demo data |
| Real Data | `raj@visor.best` | `Demo@123` | Uploaded Groww/Zerodha statements |

**Expo Go Preview URL**: `https://portfolio-polish-9.preview.emergentagent.com/api/expo/qr`

---

## 11. Backlog (Prioritized)

### P0 — Blocker
- [ ] None currently

### P1 — High Priority
- [ ] Convert FinancialHealthScore card to flip card (detailed breakdown on back)
- [ ] Streaming TTS for faster voice response perceived latency
- [ ] Refactor `investments.tsx` (1800+ lines) → component modules
- [ ] Refactor `index.tsx` (1972 lines) → component modules
- [ ] Fix remaining UI bugs from screenshots (Share button, Plan button, ActionableInsights)

### P2 — Medium Priority
- [ ] Advanced Tax Module (Phase 4): tax-loss harvesting, advance tax alerts, ITR summary
- [ ] Gmail Integration: OAuth scan of bank emails → auto-import transactions
- [ ] Export: Consolidated PDF portfolio statement
- [ ] Bookkeeping Module: Business P&L ledger for freelancers/SMBs

### P3 — Nice to Have
- [ ] Voice Cloning with ElevenLabs for custom Visor persona
- [ ] "Share with Friends" referral feature
- [ ] WhatsApp/Telegram bot integration for quick transaction logging
- [ ] Multi-currency support for NRI users
- [ ] Bank Statement PDF auto-import (ICICI, HDFC, SBI)

---

## 12. Known Issues & Technical Debt

| Issue | File | Priority | Status |
|---|---|---|---|
| `investments.tsx` >1800 lines | `app/(tabs)/investments.tsx` | P1 | Not started |
| `index.tsx` >1970 lines | `app/(tabs)/index.tsx` | P2 | Not started |
| `transactions.tsx` >2400 lines | `app/(tabs)/transactions.tsx` | P2 | Not started |
| `settings.tsx` >2000 lines | `app/(tabs)/settings.tsx` | P2 | Not started |
| Animated.View web rendering | `investments.tsx` FAB | P3 | Won't fix (user confirmed) |
| expo-av deprecation warnings | Multiple files | P3 | Low priority |

---

## 13. Recently Completed Work (March 2026)

| Date | Change |
|---|---|
| Mar 20 | Custom date range (C) added to Transactions period toggle |
| Mar 20 | Holdings header restructured to 2-row layout (title + buttons) |
| Mar 20 | GoalMapper moved to bottom of Invest screen |
| Mar 20 | Unmapped SIPs changed to horizontal scroll chips |
| Mar 20 | Trend Analysis X-axis: smart decimation + frequency-aware labels |
| Mar 20 | Expo Go QR link added to Settings screen |
| Mar 20 | PRD v3.0 full rewrite (this file) |
| Mar 19 | Expo Go QR page rebuilt with Cloudflare tunnel |
| Mar 19 | Clear All Holdings button made visible on Invest screen |
| Mar 19 | Mutual Fund valuation bug fixed (Regular vs Direct plan matching) |
| Mar 19 | Auto SIP suggestions on MF statement upload |
| Mar 19 | Daily background price refresh scheduler added |
