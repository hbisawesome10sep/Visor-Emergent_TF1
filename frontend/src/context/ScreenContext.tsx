/**
 * Screen Context Provider
 * Tracks the current active screen for AI contextual awareness
 */

import React, { createContext, useContext, useState, useCallback } from 'react';

export type ScreenName = 
  | 'dashboard'
  | 'transactions'
  | 'investments'
  | 'tax'
  | 'settings'
  | 'books'
  | 'advisor'
  | 'unknown';

type ScreenContextData = {
  currentScreen: ScreenName;
  screenParams: Record<string, any>;
  screenHistory: ScreenName[];
  setCurrentScreen: (screen: ScreenName, params?: Record<string, any>) => void;
  getScreenContext: () => string;
};

const ScreenContext = createContext<ScreenContextData | undefined>(undefined);

export function ScreenProvider({ children }: { children: React.ReactNode }) {
  const [currentScreen, setCurrentScreenState] = useState<ScreenName>('dashboard');
  const [screenParams, setScreenParams] = useState<Record<string, any>>({});
  const [screenHistory, setScreenHistory] = useState<ScreenName[]>(['dashboard']);

  const setCurrentScreen = useCallback((screen: ScreenName, params: Record<string, any> = {}) => {
    setCurrentScreenState(screen);
    setScreenParams(params);
    setScreenHistory(prev => {
      // Keep last 5 screens for history
      const newHistory = [...prev, screen].slice(-5);
      return newHistory;
    });
  }, []);

  // Generate a context string for the AI based on current screen
  const getScreenContext = useCallback(() => {
    const contextMap: Record<ScreenName, string> = {
      dashboard: `User is on the DASHBOARD screen viewing:
- Financial health score and overview cards
- Income, expenses, and investments summary
- Expense breakdown pie chart
- Trend analysis with insights
- Recent transactions list
- Financial goals progress
The user may be looking at their overall financial picture and want personalized advice.`,

      transactions: `User is on the TRANSACTIONS screen viewing:
- Full list of their income, expense, and investment transactions
- Search and filter capabilities
- Category-wise breakdown
- Ability to add, edit, or delete transactions
The user may want to discuss specific transactions, categorization, or spending patterns.`,

      investments: `User is on the INVESTMENTS screen viewing:
- Live Indian market data (Nifty, Sensex, Gold, Silver prices)
- Portfolio overview with gain/loss tracking
- Holdings breakdown (stocks, mutual funds, ETFs)
- Asset allocation pie chart
- Risk profile and recommended strategy
- SIPs and recurring investments
- Financial goals
The user may want investment advice or portfolio rebalancing suggestions.`,

      tax: `User is on the TAX screen viewing:
- Tax Planning section with Chapter VI-A deductions (80C, 80D, etc.)
- User's selected deductions with progress tracking
- Auto-detected deductions from transactions
- Capital Gains/Loss summary (STCG and LTCG)
- Income Tax Calculator with Old vs New Regime comparison
- Slab-wise tax breakdown
- Total tax liability and effective tax rate
- Financial Year / Assessment Year selector
This is the comprehensive tax hub. The user wants tax planning help, regime comparison advice, deduction recommendations, or understanding of their tax liability. Provide advice like an experienced Chartered Accountant.`,

      settings: `User is on the SETTINGS screen viewing:
- Profile information
- App preferences
- Security settings (PIN/Biometric)
- Data management options
- Linked accounts
The user may want to update their profile, change settings, or manage their data.`,

      books: `User is on the BOOKS & REPORTS screen viewing:
- Profit & Loss statement
- Balance sheet
- Expense ledger
- Fixed assets register
- Loan/EMI schedules
The user may want help understanding their financial statements or accounting queries.`,

      advisor: `User is actively chatting with the AI advisor.
They are seeking financial guidance and should receive personalized, actionable advice.`,

      unknown: `User is navigating the app. Provide general financial assistance.`,
    };

    const context = contextMap[currentScreen] || contextMap.unknown;
    
    // Add recent navigation context
    const recentScreens = screenHistory.slice(-3);
    const navigationContext = recentScreens.length > 1
      ? `\nRecent navigation: ${recentScreens.join(' → ')}`
      : '';

    return context + navigationContext;
  }, [currentScreen, screenHistory]);

  return (
    <ScreenContext.Provider value={{
      currentScreen,
      screenParams,
      screenHistory,
      setCurrentScreen,
      getScreenContext,
    }}>
      {children}
    </ScreenContext.Provider>
  );
}

export function useScreenContext() {
  const context = useContext(ScreenContext);
  if (!context) {
    throw new Error('useScreenContext must be used within a ScreenProvider');
  }
  return context;
}
