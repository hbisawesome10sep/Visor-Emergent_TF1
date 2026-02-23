# Visor Finance - Complete Product Requirements Document
## Personal Finance Management App for India

---

## 🎯 Product Vision
Visor Finance is a comprehensive personal finance management application designed specifically for Indian users. It combines intelligent bank statement parsing, double-entry bookkeeping (Indian accounting standards), investment tracking, tax planning, and AI-powered financial insights to help users take complete control of their financial life.

---

## 📱 Platform
- **Mobile App**: React Native + Expo (iOS & Android)
- **Backend**: FastAPI + MongoDB
- **Authentication**: JWT-based auth with biometric support

---

## 🏗️ Core Features

### 1. Dashboard (Home Screen)
**Purpose**: At-a-glance view of financial health

| Feature | Description | Status |
|---------|-------------|--------|
| Financial Health Score | Animated circular score (0-100) with grade badges | ✅ Implemented |
| Net Worth Overview | Total assets - liabilities | ✅ Implemented |
| Income vs Expenses | Monthly/yearly comparison with trend charts | ✅ Implemented |
| Recent Transactions | Last 5-10 transactions with quick actions | ✅ Implemented |
| Quick Stats Cards | Savings rate, investment rate, expense ratio | ✅ Implemented |
| Period Selector | Week/Month/Year/Custom date range | ✅ Implemented |

### 2. Transactions
**Purpose**: View, categorize, and manage all financial transactions

| Feature | Description | Status |
|---------|-------------|--------|
| Transaction List | Filterable, searchable list of all transactions | ✅ Implemented |
| Auto-Categorization | AI-powered category detection | ✅ Implemented |
| Manual Categorization | Override auto-detected categories | ✅ Implemented |
| Bulk Import | Import from bank statements | ✅ Implemented |
| Split Transactions | Split single transaction into multiple categories | 🔄 Planned |
| Recurring Detection | Auto-detect recurring payments | ✅ Implemented |

### 3. Investments & Portfolio
**Purpose**: Track all investments and net worth

| Feature | Description | Status |
|---------|-------------|--------|
| Portfolio Overview | Total invested vs current value with gain/loss | ✅ Implemented |
| Holdings Tracker | Individual stock/MF/ETF holdings | ✅ Implemented |
| CAS Import | Upload CAMS/Karvy CAS statements | ✅ Implemented |
| Asset Allocation | Pie chart of asset categories | ✅ Implemented |
| SIP Tracker | Track all active SIPs | ✅ Implemented |
| Market Ticker | Live Nifty, Sensex, Gold, Silver prices | ✅ Implemented |
| What-If Simulator | Project future returns with scenarios | ✅ Implemented |
| Goals Tracker | Set and track financial goals | ✅ Implemented |
| Loan Management | Track loans, EMIs, interest paid | ✅ Implemented |

### 4. Books & Reports (Double-Entry Bookkeeping)
**Purpose**: Indian accounting standards compliant bookkeeping

| Feature | Description | Status |
|---------|-------------|--------|
| Journal Entries | Auto-generated from transactions | ✅ Implemented |
| General Ledger | Account-wise transaction ledger | ✅ Implemented |
| Trial Balance | Verify debit = credit | ✅ Implemented |
| Profit & Loss | Income statement by period | ✅ Implemented |
| Balance Sheet | Assets, Liabilities, Capital | ✅ Implemented |
| Export (CSV/JSON) | Download reports | ✅ Implemented |
| Export (PDF/Excel) | Professional formatted exports | 🔄 Planned |
| Account Search | Search by account name | ✅ Implemented |
| Date Range Filter | Custom FY or date range | ✅ Implemented |

### 5. Tax Planning
**Purpose**: Optimize tax liability under Indian Income Tax Act

| Feature | Description | Status |
|---------|-------------|--------|
| Tax Calculator | Calculate tax based on regime (Old/New) | ✅ Implemented |
| Regime Comparison | Compare old vs new regime savings | ✅ Implemented |
| Auto Deduction Detection | Detect 80C, 80D, etc. from transactions | ✅ Implemented |
| Deduction Floating Bar | Quick view of detected deductions | ✅ NEW |
| Smart Tax Notifications | Alerts when close to maximizing limits | ✅ NEW |
| Deduction Approval | Approve/dismiss auto-detected deductions | ✅ NEW |
| Manual Deductions | Add deductions manually | ✅ Implemented |
| Capital Gains | Track LTCG/STCG from investments | ✅ Implemented |
| Tax Saving Tips | AI-powered suggestions | ✅ Implemented |
| Section Limits | Real-time tracking of 80C (₹1.5L), 80D (₹25K), etc. | ✅ NEW |

### 6. Insights (AI-Powered Analytics)
**Purpose**: Deep understanding of financial habits

| Feature | Description | Status |
|---------|-------------|--------|
| Financial Health Score | Detailed breakdown with grades | ✅ Redesigned |
| Spending Patterns | Category-wise spending analysis | ✅ Implemented |
| Income Analysis | Source-wise income breakdown | ✅ Implemented |
| Trend Charts | Month-over-month comparisons | ✅ Implemented |
| AI Advisor Chat | GPT-powered financial Q&A | ✅ Implemented |
| Savings Suggestions | Personalized recommendations | ✅ Implemented |
| Anomaly Detection | Unusual spending alerts | 🔄 Planned |

### 7. Settings & Banking
**Purpose**: Configure app and manage bank connections

| Feature | Description | Status |
|---------|-------------|--------|
| Bank Accounts | Add/edit/delete bank accounts | ✅ Implemented |
| Statement Upload | PDF/CSV/Excel statement import | ✅ Implemented |
| Password-Protected PDFs | Decrypt and parse | ✅ Implemented |
| Multi-Bank Support | 15+ Indian banks supported | ✅ Implemented |
| Gmail Integration | Auto-import from email | 🔄 In Progress |
| Profile Settings | Name, email, preferences | ✅ Implemented |
| Theme Toggle | Light/Dark mode | ✅ Implemented |
| Data Export | Export all user data | ✅ Implemented |
| Account Deletion | Complete data removal | ✅ Implemented |
| Biometric Lock | Fingerprint/Face ID security | ✅ Implemented |

---

## 🏦 Supported Banks (Statement Parsing)

| Bank | PDF | CSV | Excel | Status |
|------|-----|-----|-------|--------|
| HDFC Bank | ✅ | ✅ | ✅ | Implemented |
| ICICI Bank | ✅ | ✅ | ✅ | Implemented |
| SBI | ✅ | ✅ | ✅ | Implemented |
| Axis Bank | ✅ | ✅ | - | Implemented |
| Kotak | ✅ | ✅ | - | Implemented |
| IndusInd | ✅ | - | - | Implemented |
| Yes Bank | ✅ | - | - | Implemented |
| IDFC First | ✅ | - | - | Implemented |
| Federal Bank | ✅ | - | - | Implemented |
| Bank of Baroda | ✅ | - | - | Implemented |
| PNB | ✅ | - | - | Implemented |
| Canara Bank | ✅ | - | - | Implemented |
| Union Bank | ✅ | - | - | Planned |
| RBL Bank | ✅ | - | - | Planned |

---

## 📊 Financial Health Score Calculation

The Financial Health Score (0-100) is calculated based on 4 key metrics:

| Metric | Weight | Ideal Target | Calculation |
|--------|--------|--------------|-------------|
| Savings Rate | 25% | ≥20% of income | (Monthly Savings / Income) × 100 |
| Investment Rate | 25% | ≥15% of income | (Monthly Investments / Income) × 100 |
| Expense Control | 25% | ≤70% of income | 100 - (Expenses / Income × 100) |
| Goal Progress | 25% | On track to meet goals | Average progress across all goals |

**Grade Scale**:
- 🏆 **Excellent** (80-100): Outstanding financial habits
- 💪 **Good** (65-79): Great progress, minor improvements possible
- 📈 **Fair** (50-64): Building momentum, stay consistent
- 💡 **Needs Work** (35-49): Focus on savings & reducing expenses
- 🎯 **Critical** (<35): Prioritize emergency fund

---

## 🎬 Video Content Strategy (Educational)

### Video Series: "Master Your Money"

| Episode | Topic | Duration | Status |
|---------|-------|----------|--------|
| 1 | App Introduction & Setup | 3-5 min | 📝 Planned |
| 2 | Uploading Your First Bank Statement | 2-3 min | 📝 Planned |
| 3 | Understanding Your Financial Health Score | 3-4 min | 📝 Planned |
| 4 | Setting Up Investment Tracking | 4-5 min | 📝 Planned |
| 5 | Tax Planning Made Easy (80C, 80D Explained) | 5-7 min | 📝 Planned |
| 6 | Reading Your P/L and Balance Sheet | 4-5 min | 📝 Planned |
| 7 | Setting and Achieving Financial Goals | 3-4 min | 📝 Planned |
| 8 | AI Advisor: Ask Anything About Finance | 3-4 min | 📝 Planned |

### In-App Video Integration

| Feature | Description | Priority |
|---------|-------------|----------|
| Onboarding Videos | Quick tutorial on first launch | P1 |
| Contextual Help | "?" icon with short explainer videos | P2 |
| Feature Tours | Animated walkthroughs for new features | P2 |
| Tax Guide Videos | Section-wise tax saving tutorials | P1 |
| Investment Education | Asset class explainers | P2 |

---

## 🔐 Security & Privacy

| Feature | Description | Status |
|---------|-------------|--------|
| JWT Authentication | Secure token-based auth | ✅ |
| Biometric Lock | Face ID / Fingerprint | ✅ |
| Data Encryption | At-rest encryption for sensitive data | ✅ |
| No Third-Party Sharing | User data never sold | ✅ |
| Local Processing | Statement parsing done server-side | ✅ |
| Secure API | HTTPS only, rate limiting | ✅ |

---

## 📈 Roadmap

### Phase 1 - Core (COMPLETED) ✅
- [x] User Authentication
- [x] Bank Statement Parsing (15+ banks)
- [x] Transaction Management
- [x] Double-Entry Bookkeeping
- [x] Basic Tax Planning
- [x] Investment Tracking
- [x] Financial Health Score

### Phase 2 - Intelligence (IN PROGRESS) 🔄
- [x] AI Financial Advisor
- [x] Smart Tax Notifications
- [x] Auto Deduction Detection
- [x] Financial Health Card Redesign
- [ ] Deep Insights Overhaul
- [ ] Anomaly Detection

### Phase 3 - Automation (PLANNED) 📝
- [ ] Gmail Integration
- [ ] Auto Bank Sync (Account Aggregator)
- [ ] Bill Payment Reminders
- [ ] Investment Rebalancing Alerts
- [ ] Tax Filing Integration

### Phase 4 - Premium (FUTURE) 🔮
- [ ] Family Finance (Multi-user)
- [ ] Business Expense Tracking
- [ ] CA/Accountant Sharing
- [ ] Advanced Tax Optimization
- [ ] Investment Recommendations

---

## 💰 Monetization Strategy

| Tier | Price | Features |
|------|-------|----------|
| **Free** | ₹0 | Basic tracking, 1 bank, limited history |
| **Pro** | ₹199/month | Unlimited banks, full history, exports |
| **Premium** | ₹499/month | AI advisor, family accounts, priority support |
| **Lifetime** | ₹4,999 | All Pro features forever |

---

## 🛠️ Technical Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    VISOR FINANCE APP                         │
├─────────────────────────────────────────────────────────────┤
│  Frontend (React Native + Expo)                              │
│  ├── Dashboard (index.tsx)                                   │
│  ├── Transactions (transactions.tsx)                         │
│  ├── Investments (investments.tsx)                           │
│  ├── Books & Reports (books.tsx)                             │
│  ├── Tax Planning (tax.tsx)                                  │
│  ├── Insights (insights.tsx)                                 │
│  └── Settings (settings.tsx)                                 │
├─────────────────────────────────────────────────────────────┤
│  Backend (FastAPI + Python)                                  │
│  ├── Auth & Users                                            │
│  ├── Bank Statement Parser (15+ banks)                       │
│  ├── Transaction Engine                                      │
│  ├── Bookkeeping (Journal, Ledger, P/L, BS)                  │
│  ├── Tax Calculator & Deduction Engine                       │
│  ├── Portfolio & Holdings                                    │
│  ├── Market Data (Live Prices)                               │
│  ├── AI Advisor (GPT Integration)                            │
│  └── Gmail Integration                                       │
├─────────────────────────────────────────────────────────────┤
│  Database (MongoDB)                                          │
│  ├── users, transactions, journal_entries                    │
│  ├── holdings, goals, recurring_transactions                 │
│  ├── tax_deductions, bank_accounts                           │
│  └── ai_chat_history                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 📞 Support & Contact

- **App Support**: In-app chat with AI advisor
- **Email**: support@visorfinance.app (placeholder)
- **Documentation**: In-app help section

---

## 📝 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | Jan 2026 | Initial release |
| 1.1.0 | Feb 2026 | Multi-bank support, tax planning |
| 1.2.0 | Feb 23, 2026 | Financial Health redesign, Smart Tax Notifications |

---

## 🎯 Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Daily Active Users | 10,000 | - |
| Bank Statements Parsed | 100,000 | - |
| Avg. Health Score Improvement | +15 points in 3 months | - |
| Tax Saved per User | ₹25,000 avg | - |
| App Store Rating | 4.5+ stars | - |

---

*Last Updated: February 23, 2026*
