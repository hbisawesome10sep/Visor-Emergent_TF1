# Visor - AI-Powered Finance Manager PRD

## Product Overview
Visor is a personal finance management application built with React Native/Expo (frontend) and FastAPI/MongoDB (backend). It helps Indian users track income, expenses, investments, and provides AI-powered financial insights.

## Architecture
- **Frontend**: Expo, React Native, TypeScript, expo-router
- **Backend**: Python, FastAPI, MongoDB
- **AI**: OpenAI GPT-4 via Emergent Integrations (AI Financial Advisor)

## Core Features (Implemented)
- **Auth**: Login/Register with demo accounts
- **Dashboard**: Financial health score ring, liquid fill overview cards (Income/Expense/Savings), pie chart, trend chart, recent transactions, goals, date range filter (M/Q/Y/Custom)
- **Transactions**: CRUD, category filters, search, grouped by date
- **Insights**: 6 insight cards with animated gradients, national average comparisons, AI recommendations
- **Investments**: Portfolio tracking, asset allocation, Indian markets data, financial goals
- **Settings**: Theme toggle (Light/Dark/System), profile, data export/delete
- **Bookkeeping**: Reports and bookkeeping module
- **AI Advisor**: Chat-based financial advisor with calculator tools

## Visual Design System (Visor 2.0 — Implemented Feb 2026)
### Color Palette
- **Dark Mode**: True black (#000000) background, pure white (#FFFFFF) text
- **Light Mode**: Pure white (#FFFFFF) background, deep black (#09090B) text
- **Neon Accents**: Green (#39FF14), Red (#FF073A), Orange (#FF6B00), Cyan (#00FFD1), Blue (#00B4FF), Purple (#B026FF), Yellow (#FFE600)

### Typography
- **Headings/Numbers**: Space Grotesk (400-700)
- **Body/Labels**: Outfit (400-800)
- Loaded via Google Fonts CDN (web) / expo-google-fonts (native)

### Components
- Liquid Fill Cards with animated gradient backgrounds
- Neon glow effects on active states (tab bar, cards)
- Consistent card styling with dark glass surfaces

## Test Credentials
- User 1: rajesh@visor.demo / Demo@123
- User 2: priya@visor.demo / Demo@456

## Prioritized Backlog
### P1 - Next Up
- Backend migration: Python/FastAPI → Node.js/Express/PostgreSQL (deferred, discuss with user)

### P2 - Future
- Enhanced animations and micro-interactions
- Custom financial goal setting improvements
- Push notifications for budget alerts
- Data export enhancements
