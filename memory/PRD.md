# Visor - AI-Powered Finance Manager PRD

## Product Overview
Full-stack personal finance manager for Indian users. React Native (Expo) frontend + FastAPI backend + MongoDB.

## Core Requirements
- Dashboard with date-range-filtered stats, expense breakdown, trend analysis
- Transaction management with buy/sell investment support, capital gains
- AI-powered financial advisor (Visor AI) with full app data context
- Investment portfolio management with eCAS upload
- Financial goals tracking
- Insights with date range filtering

## What's Implemented
- **Authentication**: JWT-based login/register
- **Dashboard**: Overview cards, expense breakdown pie chart, Financial Health Score, date range selector (Q/M/Y/C), SVG line chart trend analysis (flippable), recent transactions, financial goals
- **Transactions**: CRUD, buy/sell toggle for investments, units/price_per_unit, date picker
- **Investments**: Holdings display, eCAS upload/parsing, clear holdings, tax planning, capital gains (STCG/LTCG), financial goals, SIPs
- **Insights**: Date range selector (Q/M/Y/All), health score, savings rate, EMI ratio, investment rate, spending breakdown, AI recommendations
- **AI Bot (Visor)**: Full context awareness - reads all user data (transactions, holdings, goals, budgets, loans, SIPs, capital gains, monthly trends, health score, portfolio)
- **Settings**: Theme toggle, profile management

## Architecture
- Frontend: React Native Expo (web + mobile), TypeScript
- Backend: FastAPI (Python), MongoDB
- AI: OpenAI GPT-5.2 via emergentintegrations
- Charts: react-native-svg (SVG Polyline/Line/Circle)
- Market Data: yfinance
- PDF: pdfplumber, pikepdf

## Date Range Filtering
Both Dashboard and Insights support Q/M/Y/C (Custom=All) date filtering. The same API endpoint (`/api/dashboard/stats`) is used with date params.

## Key Files
- `/app/backend/server.py` - All API routes
- `/app/frontend/app/(tabs)/index.tsx` - Dashboard
- `/app/frontend/app/(tabs)/transactions.tsx` - Transactions
- `/app/frontend/app/(tabs)/investments.tsx` - Investments
- `/app/frontend/app/(tabs)/insights.tsx` - Insights

## Remaining Tasks
### P1
- Refactor `investments.tsx` into smaller components
- Refactor `insights.tsx` into smaller components

### P2
- AI Contextual Screen Awareness (pass current screen view to AI)
- Backend stack migration (Python/FastAPI to Node.js)
- Enhanced micro-animations
- Push notifications for budget alerts
