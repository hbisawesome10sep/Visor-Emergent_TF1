# VISOR FINANCE — Product Requirements Document (PRD)
**Version**: 2.2  
**Last Updated**: March 19, 2026  
**Status**: Active Development  

---

## 1. Original Problem Statement

Build a comprehensive personal finance management application named **Visor**, tailored for Indian accounting standards. The app covers dashboard analytics, credit card management, EMI/SIP tracking, investment portfolio management, tax planning, bookkeeping, and AI-powered financial advice — all within a premium mobile-first experience.

---

## 2. User Personas

| Persona | Description |
|---|---|
| **Primary** | Indian individual investors (25-45 age) managing personal finances, investments, taxes, and credit cards |
| **Secondary** | Small business owners/freelancers tracking income, expenses, and tax liabilities |
| **Demo User** | `rajesh@visor.demo` / `Demo@123` — pre-seeded with realistic Indian financial data |

---

## 3. Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React Native (Expo SDK 52) with TypeScript |
| **Backend** | FastAPI (Python 3.11) |
| **Database** | MongoDB (via Motor async driver) |
| **AI Engine** | OpenAI GPT-5.2 via `emergentintegrations` library (Emergent LLM Key) |
| **Market Data** | GoldAPI.io (Gold/Silver INR prices), Yahoo Finance (NSE/BSE stocks, indices) |
| **Encryption** | AES-256-GCM field-level encryption for PII (PAN, Aadhaar, DOB) |
| **Auth** | JWT (HS256, 30-day expiry), bcrypt password hashing |
| **Tunnel** | Cloudflared (Cloudflare Quick Tunnel) for Expo Go mobile preview |
| **UI Framework** | Custom design system with DM Sans font, Jewel-tone accent palette |

---

## 4. Implementation Status

### COMPLETED
- [x] Phase 0: Bug Fixes (FAB button, statement upload)
- [x] Phase 1: Dashboard V2 (Health Score, Net Worth, XIRR, AI Insight, Share Score)
- [x] Phase 2: Credit Card Enhancements (Calendar, Interest Calc, Rewards, AI Recommender)
- [x] Phase 3: EMI & SIP Analytics (P vs I, Prepayment, Wealth Projector, Goal Mapper)
- [x] UI/UX Overhaul: Jar goals, dashboard reorder, AI icon, consistent colors
- [x] Landing Page: Full-featured marketing page
- [x] Expo QR Page: Auto-refreshing QR code for Expo Go preview (rebuilt March 19)
- [x] Voice AI: ElevenLabs STT/TTS + Hindi/multilingual ticker detection
- [x] Investment Screen Overhaul: Portfolio data fix, Stock/MF holdings cards, UploadDropdown
- [x] Groww MF Statement Parser: XLSX parser with per-holding XIRR
- [x] Zerodha Stock Statement Parser: XLSX parser
- [x] Clear All Holdings button: Visible on main Invest screen (fixed March 19)
- [x] Expo Go QR Code Page: Rebuilt with tabs (Mobile/Web), auto-refresh, cloudflare tunnel (March 19)
- [x] Fixed POST /api/holdings missing decorator (March 19)

### NOT STARTED
- [ ] Phase 4: Advanced Tax Screen (Tax-loss Harvesting, Advance Tax alerts)
- [ ] Streaming TTS for faster voice response
- [ ] Gmail Integration (auto-import transactions from email)
- [ ] Voice Cloning with ElevenLabs
- [ ] Dashboard refactoring (index.tsx is 1972 lines)
- [ ] Investments refactoring (investments.tsx is 1800+ lines)
- [ ] "Share with Friends" referral feature

---

## 5. Key API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/login` | Login, returns JWT |
| POST | `/api/upload-statement` | Upload Groww/Zerodha XLSX statement |
| DELETE | `/api/holdings/clear-all` | Delete all holdings for user |
| POST | `/api/holdings` | Add manual holding |
| GET | `/api/holdings` | List holdings |
| GET | `/api/portfolio-overview` | Portfolio allocation |
| GET | `/api/dashboard/investment-summary` | Investment summary + XIRR |
| GET | `/api/expo/qr` | Expo Go QR code page |
| GET | `/api/expo/status` | Tunnel status JSON |
| POST | `/api/visor-ai/chat` | AI chat with full context |
| POST | `/api/visor-ai/voice-chat` | Voice chat (STT/TTS) |

---

## 6. Environment Configuration

### Backend `.env`
| Variable | Purpose |
|---|---|
| `MONGO_URL` | MongoDB connection string |
| `DB_NAME` | Database name (`visor_finance`) |
| `JWT_SECRET` | JWT signing secret |
| `EMERGENT_LLM_KEY` | Universal LLM key for GPT-5.2 |
| `ENCRYPTION_MASTER_KEY` | AES-256 master key for PII encryption |
| `GOLDAPI_KEY` | Gold/Silver price API key |

### Frontend `.env`
| Variable | Purpose |
|---|---|
| `EXPO_PUBLIC_BACKEND_URL` | Backend API base URL |
| `EXPO_PACKAGER_PROXY_URL` | Cloudflare tunnel URL for Expo Go |

---

## 7. Database Schema (27 MongoDB Collections)

Key collections: `users`, `transactions`, `goals`, `holdings`, `loans`, `credit_cards`, `recurring_transactions`, `bank_accounts`, `fixed_assets`, `risk_profiles`, `market_data`, `visor_chat`, `user_tax_deductions`

---

## 8. Test Credentials
- **Demo User**: `rajesh@visor.demo` / `Demo@123`
