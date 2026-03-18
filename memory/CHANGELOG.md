# CHANGELOG

## March 18, 2026 - Phase 3: EMI & SIP Tracking (COMPLETE)

### Backend
- Created `/app/backend/routes/emi_sip_analytics.py` with 5 new endpoints:
  - `GET /api/emi-analytics/overview` - Aggregated P vs I split across all loans, per-loan breakdown, monthly amortization timeline
  - `POST /api/emi-analytics/prepayment` - Prepayment calculator supporting both "reduce tenure" and "reduce EMI" modes with savings comparison
  - `GET /api/sip-analytics/dashboard` - SIP performance analytics with discipline score, category allocation
  - `POST /api/sip-analytics/wealth-projection` - Future wealth projection with conservative (8%), moderate (12%), aggressive (15%) scenarios + custom rate
  - `POST /api/sip-analytics/goal-map` - Maps SIPs to financial goals with gap analysis and shortfall detection
- Registered `emi_sip_analytics_router` in `server.py`
- Created demo Home Loan (50L, 8.5%, 240 months) for testing

### Frontend
- Created 4 new components under `/app/frontend/src/components/emi-sip/`:
  - `PrincipalInterestSplit.tsx` - Visual P vs I breakdown with stacked bar, per-loan expandable cards
  - `PrepaymentCalculator.tsx` - Interactive calculator with loan selector, tenure/EMI toggle, savings comparison table
  - `WealthProjector.tsx` - Year selector, custom SIP/return inputs, scenario tabs with visual comparison bars, year-by-year milestones
  - `GoalMapper.tsx` - Goal cards with progress bars, shortfall warnings, unmapped SIP section
- Integrated all 4 components into `investments.tsx` under "EMI Analytics" and "SIP Analytics" sections

### Testing
- 34/34 backend tests passed (100%) - iteration_33.json
- Edge cases tested: zero prepayment, full prepayment, invalid loan_id, unauthenticated requests
- Data consistency verified across all endpoints

---

## Previous Sessions

### Phase 0 - Bug Fixes
- Fixed "+" FAB button (TouchableOpacity -> Pressable)
- Fixed bank statement upload backend NameError

### Phase 1 - Dashboard Overhaul
- Financial Health V2, Upcoming Dues, Net Worth, Investment Summary, AI Insight cards
- Share My Score feature

### Phase 2 - Credit Card Enhancements
- Due Calendar, Interest Calculator, Rewards Tracker, Best Card Recommender
- Tabbed interface on credit-cards screen

### Infrastructure
- Metro bundler cache resolution
- EMI Tracker Modal (831 lines)
- Market data integration, portfolio analytics
