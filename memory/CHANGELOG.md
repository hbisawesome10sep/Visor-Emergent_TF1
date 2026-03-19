# VISOR FINANCE — Changelog

## March 19, 2026 — Visor AI Voice Conversation
- **Voice Chat Endpoint**: New `POST /api/visor-ai/voice-chat` — accepts audio, transcribes via ElevenLabs STT (Scribe v1), processes through same GPT-5.2 pipeline, returns text + TTS audio (ElevenLabs Multilingual v2)
- **Shared AI Engine**: Extracted core Visor AI pipeline into `/app/backend/services/visor_engine.py` — shared by text and voice endpoints for identical intelligence
- **Frontend Voice UI**: Mic button, recording overlay with timer, audio playback button on AI voice responses, voice badge on user messages
- **Unified History**: Voice and text messages stored in same `visor_chat` collection with `input_type` metadata
- **Dependencies**: Added `elevenlabs` (backend), `expo-av` (frontend)

## March 18, 2026 (Session 7)
### Color & QR Fixes
- Unified goal category colors across Dashboard (`formatters.ts`) and Invest screen (`GoalsSection.tsx`)
- Added goal categories (Safety, Purchase, Property, Retirement, Wedding) to shared color map
- Rebuilt Expo Go QR code page (`/api/expo/qr`) with JS-based QR generation, auto-refresh, correct tunnel detection

### UI/UX Overhaul
- Created `JarProgressView.tsx` — SVG jar visualization for goal progress
- Dashboard layout rework: Goals above Transactions, Net Worth below Trends, Dues below Credit Cards
- Fixed Share Score modal scroll issue
- Smart Alerts navigation to relevant tabs
- Consistent Financial Health V2 Card across Dashboard and Insights
- New cute robot icon for Visor AI agent
- Investment card layout fix (Current Value alignment)

### Feature Enhancements
- SIP-Goal Link/Unlink endpoints (`link-sip`, `unlink-sip`)
- Redesigned GoalMapper with linking UI
- Enhanced Visor AI system prompt for data-driven responses

### Landing Page
- New comprehensive landing page at `/app/frontend/app/index.tsx`
- Sections: Hero, Stats, Health Score, 12-Feature Grid, AI Section, Jar Goals, Security, CTA

### Testing
- 53/53 backend tests passed (iteration_34)

## March 17, 2026 (Session 6)
### Phase 3: EMI & SIP Analytics — COMPLETE
- Principal vs Interest Split (overview + per-loan)
- Prepayment Calculator (tenure vs EMI reduction)
- Wealth Projector (3 scenarios: 8%/12%/15%)
- Goal Mapper (SIP-to-goal mapping with gap analysis)
- 7 new API endpoints in emi_sip_analytics.py

## March 16, 2026 (Session 5)
### Phase 2: Credit Card Enhancements — COMPLETE
- Due Date Calendar with smart reminders
- Interest Calculator (minimum payment trap)
- Rewards Tracker (points, cashback, miles)
- Best Card Recommender (AI-powered via GPT-4o)

## March 15, 2026 (Session 4)
### Phase 1: Dashboard V2 — COMPLETE
- Financial Health Score V2 (gamified 0-1000, 8 dimensions)
- Upcoming Dues card
- Investment Summary with XIRR
- Net Worth calculation
- AI Insight (GPT-4o powered)
- Share My Score feature

## Earlier Sessions
- Phase 0: Bug fixes (FAB button, bank statement upload)
- Core CRUD: Transactions, Goals, Holdings, Loans, Credit Cards
- Bookkeeping: Double-entry journal, ledger, P&L, balance sheet
- Tax Planning: Old/New regime, deductions, capital gains
- Security: AES-256-GCM encryption, PIN lock
- Bank statement parsing (SBI, HDFC, ICICI, Axis, Kotak)
