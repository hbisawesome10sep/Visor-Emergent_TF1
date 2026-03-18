# VISOR FINANCE - Product Requirements Document

## Original Problem Statement
Build a comprehensive personal finance management application named Visor, tailored for Indian accounting standards. The app covers dashboard analytics, credit card management, EMI/SIP tracking, tax planning, and AI-powered financial advice.

## Tech Stack
- **Frontend**: React Native (Expo) with TypeScript
- **Backend**: FastAPI (Python) with MongoDB
- **AI**: OpenAI GPT-4o via emergentintegrations (Emergent LLM Key)
- **Libraries**: react-native-view-shot, pdfplumber, pandas

## User Personas
- Indian individual investors managing personal finances
- Demo user: `rajesh@visor.demo` / `Demo@123`

---

## Implementation Status

### Phase 0: Bug Fixes - DONE
- [x] Fixed unresponsive "+" FAB button (Pressable)
- [x] Fixed bank statement upload backend error
- [ ] Expo Go Deep Link on iOS (P2 - deferred)

### Phase 1: Dashboard Overhaul - DONE
- [x] Financial Health Score V2 (gamified 0-1000 score, 8 dimensions)
- [x] Upcoming Dues card (CC + loan due dates)
- [x] Investment Summary card (total invested, current value, XIRR)
- [x] Net Worth card (assets minus liabilities)
- [x] AI Insight card (GPT-4o powered)
- [x] "Share My Score" feature (react-native-view-shot)

### Phase 2: Credit Card Enhancements - DONE
- [x] Due Date Calendar
- [x] Interest Calculator
- [x] Rewards Tracker
- [x] Best Card Recommender (AI-powered)

### Phase 3: EMI & SIP Tracking - DONE (Mar 18, 2026)
- [x] Principal vs Interest Split (overview + per-loan breakdown)
- [x] Prepayment Calculator (tenure/EMI reduction, savings comparison)
- [x] Wealth Projector (3 scenarios: conservative 8%, moderate 12%, aggressive 15%)
- [x] Goal Mapper (SIP-to-goal mapping, gap analysis, shortfall detection)
- Backend: 5 new endpoints in `/app/backend/routes/emi_sip_analytics.py`
- Frontend: 4 new components in `/app/frontend/src/components/emi-sip/`
- Testing: 34/34 backend tests passed (100%)

### Phase 4: Tax Screen & Bookkeeping - NOT STARTED
- [ ] Tax-loss Harvesting alerts
- [ ] Advance Tax calculation and alerts
- [ ] Enhanced double-entry bookkeeping

### Phase 5: Visor AI Agent - NOT STARTED
- [ ] Context-aware financial AI companion (chat)
- [ ] Web search integration
- [ ] Financial calculators

### Phase 6: Gmail Integration - NOT STARTED
- [ ] Auto-import transactions from email

---

## API Endpoints

### Phase 3 (New)
| Endpoint | Method | Description |
|---|---|---|
| `/api/emi-analytics/overview` | GET | P vs I split, loan breakdown, timeline |
| `/api/emi-analytics/prepayment` | POST | Prepayment savings calculator |
| `/api/sip-analytics/dashboard` | GET | SIP performance analytics |
| `/api/sip-analytics/wealth-projection` | POST | Wealth projection (3 scenarios) |
| `/api/sip-analytics/goal-map` | POST | SIP-to-goal mapping with gap analysis |

### Phase 2
| `/api/credit-cards-v2/due-calendar` | GET |
| `/api/credit-cards-v2/rewards-summary` | GET |
| `/api/credit-cards-v2/interest-calculator` | POST |
| `/api/credit-cards-v2/best-card-recommender` | POST |

### Phase 1
| `/api/dashboard-v2/financial-health` | GET |
| `/api/dashboard-v2/upcoming-dues` | GET |
| `/api/dashboard-v2/investment-summary` | GET |
| `/api/dashboard-v2/net-worth` | GET |
| `/api/dashboard-v2/ai-insight` | GET |

---

## Code Architecture
```
/app/backend/routes/
  emi_sip_analytics.py    # Phase 3: EMI & SIP analytics
  credit_cards_v2.py      # Phase 2: CC analytics
  dashboard_v2.py         # Phase 1: Dashboard V2
  loans.py, holdings.py, recurring.py  # Core CRUD

/app/frontend/src/components/
  emi-sip/                # Phase 3 components
    PrincipalInterestSplit.tsx
    PrepaymentCalculator.tsx
    WealthProjector.tsx
    GoalMapper.tsx
  credit-cards/           # Phase 2 components
  dashboard/              # Phase 1 components
  share/                  # Share feature
```

## Refactoring Backlog
- `investments.tsx` is ~1700+ lines, needs component extraction
