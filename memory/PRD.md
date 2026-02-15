# Visor - AI-Powered Personal Finance Manager

## Product Overview
Visor is a comprehensive, mobile-first personal finance management application tailored for the Indian market. It combines automated transaction tracking, AI-powered financial insights (GPT-5.2), and goal tracking with a premium iOS-inspired glass UI that works seamlessly across phones, tablets (iPad), and laptops.

## Target Audience
Tech-savvy Indian users aged 22-40 who use multiple financial channels (banks, UPI) and want automated tracking with intelligent guidance.

## Core Features

### 1. Authentication & Security
- Custom JWT-based authentication with Indian compliance fields (DOB, PAN, Aadhaar)
- Secure password hashing with bcrypt
- 7-day token expiry
- **Demo Accounts:**
  - Rajesh Kumar: `rajesh@visor.demo` / `Demo@123` (PAN: ABCDE1234F, Aadhaar: ****9012)
  - Priya Sharma: `priya@visor.demo` / `Demo@456` (PAN: FGHIJ5678K, Aadhaar: ****1098)

### 2. Financial Dashboard
- Net balance overview with monthly breakdown (Income/Expenses/Investments)
- Financial Health Score (0-100) with grade (Excellent/Good/Fair/Needs Work/Critical)
- Expense breakdown with visual bar charts
- Recent transactions feed
- Pull-to-refresh for real-time updates

### 3. Transaction Management
- Full CRUD operations for Income, Expense, and Investment transactions
- Category-based organization (20+ categories covering Indian financial context)
- Filter by type (All/Income/Expense/Investment)
- Bottom sheet modal for adding transactions
- Indian Rupee (₹) formatting with Indian numbering system (lakhs, crores)

### 4. AI Financial Advisor (GPT-5.2)
- Real-time AI chat powered by OpenAI GPT-5.2 via Emergent LLM Key
- Context-aware: analyzes user's actual financial data before responding
- Indian finance focus: tax laws (Section 80C/80D), investment instruments (PPF, NPS, ELSS, SIP, FD)
- Quick prompts for common financial questions
- Persistent chat history

### 5. Financial Goals
- Create and track financial goals with target/current amounts
- Progress visualization with color-coded bars
- Overall goal progress summary
- Edit and delete goals
- Categories: Safety, Travel, Purchase, Property, Education, Retirement, Wedding

### 6. Settings & Personalization
- Profile display with masked Aadhaar
- Theme toggle: Light / Dark / System
- App info and configuration

## Tech Stack
- **Frontend:** React Native (Expo SDK 54), TypeScript, Expo Router
- **Backend:** FastAPI (Python), MongoDB (Motor async driver)
- **AI:** OpenAI GPT-5.2 via emergentintegrations library
- **Auth:** JWT with bcrypt password hashing
- **State:** AsyncStorage for auth persistence

## Design System
- **Primary Color:** Emerald Green (#059669 light / #10B981 dark)
- **Secondary Color:** Indigo (#4338CA light / #6366F1 dark)
- **Glass UI:** Semi-transparent surfaces with rounded corners (16-24px radius)
- **Fonts:** System for UI, SpaceMono for financial data
- **Spacing:** 8pt grid system

## API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/register | Create new account |
| POST | /api/auth/login | Login with credentials |
| GET | /api/auth/profile | Get user profile |
| GET | /api/transactions | List transactions (with filters) |
| POST | /api/transactions | Create transaction |
| DELETE | /api/transactions/{id} | Delete transaction |
| GET | /api/goals | List goals |
| POST | /api/goals | Create goal |
| PUT | /api/goals/{id} | Update goal |
| DELETE | /api/goals/{id} | Delete goal |
| GET | /api/dashboard/stats | Dashboard statistics |
| GET | /api/health-score | Financial health score |
| POST | /api/ai/chat | AI advisor chat |
| GET | /api/ai/history | Chat history |
| DELETE | /api/ai/history | Clear chat history |

## Future Enhancements
- SMS transaction parsing for Indian banks (SBI, HDFC, ICICI, etc.)
- Biometric authentication (WebAuthn)
- Investment portfolio tracking with real-time market data
- Budget planning with alerts
- Export data as PDF/CSV
- Push notifications for spending alerts
- Premium subscription with advanced AI features
