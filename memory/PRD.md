# Visor - AI-Powered Finance Manager PRD

## Product Overview
Visor is a personal finance management app built with React Native/Expo (frontend) and FastAPI/MongoDB (backend) for Indian users.

## Architecture
- **Frontend**: Expo, React Native, TypeScript, expo-router
- **Backend**: Python, FastAPI, MongoDB
- **AI**: OpenAI GPT-4 via Emergent Integrations

## Core Features (Implemented)
- Auth (login/register), Dashboard (health score, liquid fill cards, charts, date filters, FAB)
- Transactions (CRUD, filters, search), Insights (6 animated cards, national averages, AI recs)
- Investments (portfolio, goals, Indian markets), Settings (theme toggle, profile, export)
- Bookkeeping, AI Advisor chat

## Visual Design System (v2.1 — Feb 2026)
### Color Palette — Refined Jewel Tones
- **Dark Mode**: True black (#000000), white text (#F9FAFB)
- **Light Mode**: Pure white (#FFFFFF), deep black text (#111827)
- **Accent (Jewel Tones)**: Emerald (#10B981), Ruby (#EF4444), Amber (#F59E0B), Teal (#14B8A6), Sapphire (#3B82F6), Amethyst (#8B5CF6), Rose (#F43F5E)

### Typography — DM Sans
- Single font family: DM Sans (400-700), loaded via Google Fonts CDN (web) / expo-google-fonts (native)
- Clean, geometric, professional fintech feel

### Card Gradients (Liquid Fill)
- Income: Emerald → Deep Green (#047857)
- Expenses: Ruby → Rose
- Savings: Sapphire → Indigo (#4F46E5)
- No bloom/glow effects — refined shadows only

## Test Credentials
- rajesh@visor.demo / Demo@123
- priya@visor.demo / Demo@456

## Prioritized Backlog
### P1
- Backend migration discussion: Python/FastAPI → Node.js/Express/PostgreSQL

### P2
- Enhanced micro-animations
- Push notifications for budget alerts
- Data export improvements
