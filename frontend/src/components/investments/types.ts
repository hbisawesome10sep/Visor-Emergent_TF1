/**
 * Investment Screen — Shared Types & Constants
 */
import { Accent } from '../../utils/theme';

// ── Types ──
export type MarketItem = {
  key: string; name: string; price: number; change: number;
  change_percent: number; prev_close: number; icon: string; last_updated: string;
};

export type Goal = {
  id: string; title: string; target_amount: number; current_amount: number;
  deadline: string; category: string;
};

export type DashboardStats = {
  total_income: number; total_expenses: number; total_investments: number;
  invest_breakdown: Record<string, number>;
};

export type PortfolioData = {
  total_invested: number;
  total_current_value: number;
  total_gain_loss: number;
  total_gain_loss_pct: number;
  categories: Array<{
    category: string; invested: number; current_value: number;
    gain_loss: number; gain_loss_pct: number; transactions: number;
  }>;
};

export type Holding = {
  id: string; name: string; ticker: string; isin: string; category: string;
  quantity: number; buy_price: number; buy_date: string; source: string;
  current_price: number; invested_value: number; current_value: number;
  gain_loss: number; gain_loss_pct: number;
};

export type HoldingsData = {
  holdings: Holding[];
  summary: {
    total_invested: number; total_current_value: number;
    total_gain_loss: number; total_gain_loss_pct: number; holding_count: number;
  };
};

export type RecurringTransaction = {
  id: string; name: string; amount: number; frequency: string;
  category: string; start_date: string; end_date: string | null;
  day_of_month: number; notes: string | null; is_active: boolean;
  next_execution: string; total_invested: number; execution_count: number;
  upcoming: Array<{ date: string; amount: number; status: string }>;
};

export type RecurringData = {
  recurring: RecurringTransaction[];
  summary: {
    total_count: number; active_count: number;
    monthly_commitment: number; categories: string[];
  };
};

// ── Constants ──
export const ASSET_CATEGORIES: Record<string, { label: string; color: string }> = {
  'Stock': { label: 'Stocks', color: Accent.sapphire },
  'Stocks': { label: 'Stocks', color: Accent.sapphire },
  'Mutual Fund': { label: 'Mutual Funds', color: Accent.amethyst },
  'Mutual Funds': { label: 'Mutual Funds', color: Accent.amethyst },
  'SIP': { label: 'SIP', color: '#6366F1' },
  'FD': { label: 'Fixed Deposits', color: '#0891B2' },
  'Fixed Deposit': { label: 'Fixed Deposits', color: '#0891B2' },
  'PPF': { label: 'PPF', color: '#14B8A6' },
  'Gold': { label: 'Gold', color: '#EAB308' },
  'Sovereign Gold Bond': { label: 'Gold', color: '#CA8A04' },
  'Silver': { label: 'Silver', color: '#94A3B8' },
  'NPS': { label: 'NPS', color: Accent.emerald },
  'EPF': { label: 'EPF', color: '#14B8A6' },
  'Crypto': { label: 'Crypto', color: '#F59E0B' },
  'ETFs': { label: 'ETFs', color: '#2563EB' },
  'Bonds': { label: 'Bonds', color: '#0284C7' },
  'Real Estate': { label: 'Real Estate', color: '#78716C' },
  'ULIP': { label: 'ULIP', color: '#7C3AED' },
};

export const GOAL_CATS = ['Safety', 'Travel', 'Purchase', 'Property', 'Education', 'Retirement', 'Wedding', 'Other'];
export const HOLDING_CATS = ['Stock', 'Mutual Fund', 'ETF', 'Gold', 'Silver', 'Bond', 'Other'];
export const SIP_CATS = ['SIP', 'PPF', 'NPS', 'EPF', 'ELSS', 'Insurance', 'FD', 'Gold', 'Other'];
export const SIP_FREQUENCIES = ['monthly', 'weekly', 'quarterly', 'yearly'];

export const RISK_QUESTIONS = [
  { id: 1, category: 'horizon', question: 'What is your primary investment time horizon?', options: [
    { label: '< 1 year', value: 1 }, { label: '1-3 years', value: 2 }, { label: '3-7 years', value: 3 }, { label: '7-15 years', value: 4 }, { label: '15+ years', value: 5 }
  ]},
  { id: 2, category: 'loss_tolerance', question: 'If your portfolio dropped 25% in a month, what would you do?', options: [
    { label: 'Sell everything immediately', value: 1 }, { label: 'Sell half to limit damage', value: 2 }, { label: 'Hold and wait for recovery', value: 3 }, { label: 'Buy more at lower prices', value: 5 }
  ]},
  { id: 3, category: 'experience', question: 'How much investment experience do you have?', options: [
    { label: "None — I'm new to investing", value: 1 }, { label: 'Beginner (FDs, PPF only)', value: 2 }, { label: 'Intermediate (MFs, SIPs)', value: 3 }, { label: 'Advanced (Stocks, F&O, crypto)', value: 5 }
  ]},
  { id: 4, category: 'income_stability', question: 'How stable is your primary source of income?', options: [
    { label: 'Unstable / Freelance', value: 1 }, { label: 'Somewhat stable', value: 2 }, { label: 'Stable salaried job', value: 4 }, { label: 'Multiple income streams', value: 5 }
  ]},
  { id: 5, category: 'emergency_fund', question: 'How many months of expenses do you have as an emergency fund?', options: [
    { label: 'None', value: 1 }, { label: '1-3 months', value: 2 }, { label: '3-6 months', value: 3 }, { label: '6-12 months', value: 4 }, { label: '12+ months', value: 5 }
  ]},
  { id: 6, category: 'return_expectation', question: 'What annual return do you expect from your investments?', options: [
    { label: '6-8% (FD-like safety)', value: 1 }, { label: '8-12% (Balanced growth)', value: 2 }, { label: '12-18% (Equity-like returns)', value: 4 }, { label: '18%+ (High growth, high risk)', value: 5 }
  ]},
  { id: 7, category: 'loss_tolerance', question: 'What is the maximum portfolio loss you can stomach in a year?', options: [
    { label: "0% — I can't afford any loss", value: 1 }, { label: 'Up to 10%', value: 2 }, { label: 'Up to 20%', value: 3 }, { label: 'Up to 30%', value: 4 }, { label: '30%+ if long-term gains are high', value: 5 }
  ]},
  { id: 8, category: 'concentration', question: 'How comfortable are you putting 50%+ of your portfolio in equities?', options: [
    { label: 'Very uncomfortable', value: 1 }, { label: 'Slightly uncomfortable', value: 2 }, { label: 'Neutral', value: 3 }, { label: 'Comfortable', value: 4 }, { label: 'Very comfortable', value: 5 }
  ]},
  { id: 9, category: 'behavior', question: 'When markets are at all-time highs, what do you typically do?', options: [
    { label: 'Sell and book profits', value: 2 }, { label: 'Stop investing and wait', value: 1 }, { label: 'Continue my SIPs normally', value: 3 }, { label: 'Invest more aggressively', value: 5 }
  ]},
  { id: 10, category: 'goal_priority', question: 'What matters more to you in investing?', options: [
    { label: 'Capital preservation above all', value: 1 }, { label: 'Steady income with low risk', value: 2 }, { label: 'Balance of growth and safety', value: 3 }, { label: 'Maximum growth, even with volatility', value: 5 }
  ]},
  { id: 11, category: 'behavior', question: "A friend recommends a \"hot stock tip\". What do you do?", options: [
    { label: 'Ignore it completely', value: 3 }, { label: 'Research before acting', value: 4 }, { label: 'Invest a small amount to test', value: 2 }, { label: 'Go all-in if it sounds good', value: 1 }
  ]},
  { id: 12, category: 'age_capacity', question: 'What is your age group?', options: [
    { label: '18-25', value: 5 }, { label: '26-35', value: 4 }, { label: '36-45', value: 3 }, { label: '46-55', value: 2 }, { label: '55+', value: 1 }
  ]},
];

export const RISK_CATEGORY_LABELS: Record<string, string> = {
  horizon: 'Time Horizon', loss_tolerance: 'Loss Tolerance', experience: 'Experience',
  income_stability: 'Income Stability', emergency_fund: 'Emergency Fund',
  return_expectation: 'Return Expectation', concentration: 'Equity Comfort',
  behavior: 'Behavioral Discipline', goal_priority: 'Goal Priority', age_capacity: 'Age Capacity',
};

export const RISK_CATEGORY_DISPLAY: Record<string, string> = {
  horizon: 'Investment Horizon', loss_tolerance: 'Risk Tolerance', experience: 'Experience',
  income_stability: 'Financial Stability', emergency_fund: 'Safety Net',
  return_expectation: 'Expectations', concentration: 'Portfolio Comfort',
  behavior: 'Behavioral Finance', goal_priority: 'Goal Alignment', age_capacity: 'Demographics',
};
