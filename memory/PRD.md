# Visor - AI-Powered Finance Manager PRD

## Product Overview
Full-stack personal finance manager for Indian users. React Native (Expo) frontend + FastAPI backend + MongoDB.

## What's Implemented
- **Authentication**: JWT-based login/register
- **Dashboard**: Overview cards, expense breakdown pie chart, Financial Health Score, date range selector (Q/M/Y/C), SVG line chart trend analysis (flippable), recent transactions, financial goals
- **Transactions**: CRUD, buy/sell toggle for investments, units/price_per_unit, date picker
- **Investments**: Holdings display, eCAS upload/parsing, clear holdings, tax planning, capital gains (STCG/LTCG), financial goals, SIPs, What-If Simulator (extracted component)
- **Insights**: Date range selector (Q/M/Y/All), health score (synced with Dashboard), savings rate, EMI ratio, investment rate, spending breakdown, compare card, AI recommendations
- **AI Bot (Visor)**: Full context awareness - reads all user data (transactions, holdings, goals, budgets, loans, SIPs, capital gains, monthly trends, health score, portfolio)
- **Settings**: Theme toggle, profile management

## Component Architecture (Refactored)
```
/app/frontend/src/components/
  HealthScoreCard.tsx      - Flippable health score with breakdown
  SpendingBreakdownCard.tsx - Category-based spending bars
  CompareCard.tsx           - vs Indian national averages
  AIRecommendations.tsx     - Personalized AI tips
  WhatIfSimulator.tsx       - Allocation scenario simulator
  AIAdvisorChat.tsx         - AI chat component
  PieChart.tsx              - SVG pie chart
  TrendChart.tsx            - Chart helper
```

## Key Files
- `/app/backend/server.py` - All API routes
- `/app/frontend/app/(tabs)/index.tsx` - Dashboard (1825 lines)
- `/app/frontend/app/(tabs)/transactions.tsx` - Transactions
- `/app/frontend/app/(tabs)/investments.tsx` - Investments (1948 lines)
- `/app/frontend/app/(tabs)/insights.tsx` - Insights (1034 lines)

## Remaining Tasks
### P1
- Further refactoring of index.tsx (extract overview cards, chart section)
- Unused styles cleanup in investments.tsx and insights.tsx

### P2
- AI Contextual Screen Awareness (pass current screen view to AI)
- Backend stack migration (Python/FastAPI to Node.js)
- Enhanced micro-animations
- Push notifications for budget alerts
