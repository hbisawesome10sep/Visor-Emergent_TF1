# CHANGELOG — Visor Finance

## v3.1.0 (March 18, 2026)

### Share My Score Feature
- **Share My Score** — Beautiful shareable card for Financial Health Score
  - Captures 8-dimension score as PNG image with branded Visor layout
  - Share via WhatsApp, Instagram, or any app using native share sheet
  - Dark theme card with score ring, dimension bars, Visor branding

### Phase 2: Credit Card Enhancements
- **Due Date Calendar** — View all CC payment due dates with smart reminders
  - Urgency levels: critical (1 day), warning (3 days), upcoming (7 days), normal
  - Shows outstanding, minimum due, and reminder messages
- **Interest Calculator** — "Minimum Payment Trap" calculator
  - Enter outstanding balance, see total interest over time if paying only minimum
  - Shows months to clear, total paid, interest as % of principal
  - Per-card calculation using card-specific interest rates
- **Rewards Tracker** — Track points, cashback, and miles
  - Total points and INR equivalent across all cards
  - Per-card breakdown with category analysis
  - 6-month reward trend visualization
  - Card benefits display
- **Best Card Recommender** — AI-powered (GPT-4o) card selection
  - Enter transaction category, amount, and merchant
  - Get ranked recommendations with points earned, value, and utilization impact
  - AI generates personalized recommendation text
- **Tab Navigation** — 5 tabs in Credit Cards screen: My Cards, Dues, Rewards, Interest, Best Card

### Backend Endpoints Added
- `GET /api/credit-cards/due-calendar`
- `POST /api/credit-cards/interest-calculator`
- `GET /api/credit-cards/rewards`
- `POST /api/credit-cards/recommend`

### Testing
- 29/29 Phase 2 tests passed (100%)
- 31/31 Phase 1 tests passed (100%)
- Test files: `/app/backend/tests/test_cc_analytics_phase2.py`

---

## v3.0.0 (March 18, 2026)

### Dashboard Overhaul
- **Financial Health Score V2** — 8-dimension scoring system (0-1000 scale) with flip card UI
  - Dimensions: Savings Rate, Debt Load, Investment Rate, Emergency Fund, CC Utilization, Goal Progress, Insurance Cover, Net Worth Growth
  - Weighted composite score with grade (Excellent/Good/Fair/Needs Work/Critical)
  - Animated progress bars per dimension + improvement tips
- **Net Worth Card** — Real-time calculation from app data (Assets - Liabilities)
  - Breakdown: Bank Balance, Investments vs Loans, CC Outstanding
- **Investment Summary Card** — Portfolio snapshot with XIRR calculation
  - Shows total invested, current value, absolute returns, P&L
- **Upcoming Dues Card** — CC + Loan EMI due dates with urgency indicators
  - Smart sorting by days until due (critical/warning/upcoming/normal)
- **AI Insight Card** — GPT-4o powered personalized financial advice
  - Uses real user data (income, expenses, goals, investments, top spending categories)
  - SEBI disclaimer included

### Bug Fixes
- **FAB Button Fix** — Replaced `TouchableOpacity` with `Pressable` + `pointerEvents="box-none"` wrapper on Transactions screen for reliable touch handling across platforms

### New Features
- **Insurance CRUD** — Full Create/Read/Update/Delete for insurance policies
  - Supports: term_life, health, life, vehicle, home policy types
  - Used in Financial Health Score (Insurance Cover dimension)

### Backend Endpoints Added
- `GET /api/dashboard/financial-health-v2`
- `GET /api/dashboard/net-worth`
- `GET /api/dashboard/investment-summary`
- `GET /api/dashboard/upcoming-dues`
- `GET /api/dashboard/ai-insight`
- `GET /api/insurance`
- `POST /api/insurance`
- `PUT /api/insurance/{policy_id}`
- `DELETE /api/insurance/{policy_id}`

### Testing
- 31/31 backend tests passed (100%)
- Test file: `/app/backend/tests/test_dashboard_v2_insurance.py`

---

## v2.3.1 (March 17, 2026)
- Refactored investments.tsx (1982 -> 1686 lines)
- Extracted 4 components: PortfolioOverviewCard, HoldingsSection, RiskProfileCard, RecurringInvestmentsSection

## v2.3.0 (March 17, 2026)
- Refactored visor_ai.py (835 -> 277 lines, split into services/)
- Refactored bank_statements.py (2808 -> 294 lines, split into parsers/)
- Extracted investments.tsx types to shared module

## v2.2.4 (March 17, 2026)
- Token expiry extended (7d -> 30d) + auto-logout on 401
- Removed hardcoded fake percentages from dashboard
- Removed fake fallback data from insights
- Added 401 token expired handling for uploads
