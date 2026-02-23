# Visor Finance - Personal Finance Management App

## Original Problem Statement
Build a comprehensive personal finance management application with focus on Indian accounting standards, including double-entry bookkeeping, bank statement parsing, tax planning, and financial insights.

## Current Architecture
```
/app
├── backend (FastAPI + MongoDB)
│   ├── routes/
│   │   ├── bank_statements.py   - Multi-bank statement parsing
│   │   ├── bookkeeping.py       - Ledger, P/L, Balance Sheet
│   │   ├── journal.py           - Journal entries
│   │   ├── tax.py               - Tax planning & auto-deductions
│   │   ├── dashboard.py         - Stats & health score
│   │   └── transactions.py      - Transaction management
│   └── main.py
└── frontend (React Native + Expo)
    ├── app/(tabs)/
    │   ├── index.tsx            - Dashboard
    │   ├── insights.tsx         - Financial insights
    │   ├── tax.tsx              - Tax planning
    │   ├── settings.tsx         - Settings & bank import
    │   └── books.tsx            - Books & reports
    └── src/components/
        ├── FinancialHealthCard.tsx  - NEW: Redesigned health score
        └── tax/
            ├── DeductionFloatingBar.tsx  - NEW: Tax deduction tracker
            └── AutoDeductionsSection.tsx
```

## What's Been Implemented (Feb 23, 2026)

### Bug Fixes
1. ✅ **Banking Dark Mode Text** - Input fields now show white text in dark mode
2. ✅ **Success Button Fix** - "Done" button in upload modal now properly visible
3. ✅ **Books Export Fix** - CSV/JSON export working, Excel/PDF shows "coming soon"
4. ✅ **Journal Export Support** - Added journal entries to export functionality
5. ✅ **Auth Token Fix** - Backend now supports both `user_id` and `sub` JWT claims
6. ✅ **Journal Entry Data Fix** - Fixed 111 entries missing debit/credit data

### New Features
1. ✅ **Financial Health Card Redesign** - Complete overhaul with:
   - Gradient backgrounds based on score
   - Animated score counter
   - Expandable breakdown with progress bars
   - Emoji-based grades (🏆 Excellent, 💪 Good, 📈 Fair, 💡 Needs Work, 🎯 Critical)
   - Actionable tips
   - Premium, colorful design

2. ✅ **Tax Deduction Floating Bar** - New feature with:
   - Summary bar at top of Tax tab
   - Shows detected deductions count and amount
   - Mini progress bars for top sections
   - Full details modal with approve/dismiss workflow
   - Section-wise breakdown with limits
   - Tax saving tips

## Prioritized Backlog

### P0 (Critical)
- [ ] Expo Go iOS QR scanning issue (workaround: use manual URL or PNG QR)

### P1 (High Priority)
- [ ] Deep Insights Screen Overhaul
- [ ] PDF/Excel export from backend
- [ ] Add support for more Indian banks

### P2 (Medium Priority)
- [ ] Gmail integration for transaction import
- [ ] Refactor investments.tsx (1900+ lines)
- [ ] Refactor bank_statements.py into parsers module

### P3 (Low Priority)
- [ ] Consider Node.js backend migration
- [ ] Enhanced auto-deduction engine

## Test Credentials
- **User Account**: harshbhati15987@gmail.com
- **Demo Account**: rajesh@visor.demo / Demo@123

## QR Code for Testing
https://rupee-books.preview.emergentagent.com/qr/ios-expo.png

## Known Issues
- Expo Go iOS QR scanning has caching issues with old ngrok URLs
- Workaround: Use PNG QR code image or manual URL entry
