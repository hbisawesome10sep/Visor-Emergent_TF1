# Visor - AI-Powered Finance Manager PRD

## Product Overview
Visor is a personal finance management app built with React Native/Expo (frontend) and FastAPI/MongoDB (backend) for Indian users.

## Architecture
- **Frontend**: Expo, React Native, TypeScript, expo-router, DM Sans font
- **Backend**: Python, FastAPI, MongoDB
- **AI**: OpenAI GPT-4 via Emergent Integrations

## Core Features
- Auth (login/register), Dashboard (health score, liquid fill cards, charts, date filters, FAB)
- Transactions (CRUD with PUT/POST/DELETE, dropdown categories, optional descriptions, calendar date picker)
- Insights (6 animated cards, national averages, AI recommendations)
- Investments (portfolio linked to investment transactions, goals, Indian markets)
- Settings (theme toggle, profile, export), Bookkeeping, AI Advisor chat

## Visual Design (v2.1 — Refined Jewel Tones)
- Dark: True black (#000000), Light: Pure white (#FFFFFF)
- Accents: Emerald, Ruby, Amber, Teal, Sapphire, Amethyst, Rose
- Font: DM Sans (400-700)

## Transaction Form (v2 — Feb 2026)
- **Category Dropdown**: 27 expense, 13 income, 18 investment categories with icons
- **Description**: Optional, context-specific suggestions per type
- **Date**: Native calendar picker (HTML input type=date on web)
- **Investment Linkage**: Investment transactions auto-reflect in Invest screen via invest_breakdown

## Test Credentials
- rajesh@visor.demo / Demo@123

## Prioritized Backlog
### P1
- PAN-based auto-fetch of holdings (requires market data provider integration)
- Backend migration discussion: Python/FastAPI → Node.js/Express/PostgreSQL

### P2
- Enhanced micro-animations
- Push notifications for budget alerts
