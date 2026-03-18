export const formatINR = (amount: number): string => {
  const isNegative = amount < 0;
  const absAmount = Math.abs(amount);
  const [whole, decimal] = absAmount.toFixed(2).split('.');
  const digits = whole.split('').reverse();
  let formatted = '';
  for (let i = 0; i < digits.length; i++) {
    if (i === 3 || (i > 3 && (i - 3) % 2 === 0)) {
      formatted = ',' + formatted;
    }
    formatted = digits[i] + formatted;
  }
  return `${isNegative ? '-' : ''}₹${formatted}.${decimal}`;
};

export const formatINRShort = (amount: number): string => {
  const abs = Math.abs(amount);
  const sign = amount < 0 ? '-' : '';
  if (abs >= 10000000) return `${sign}₹${(abs / 10000000).toFixed(1)}Cr`;
  if (abs >= 100000) return `${sign}₹${(abs / 100000).toFixed(1)}L`;
  if (abs >= 1000) return `${sign}₹${(abs / 1000).toFixed(1)}K`;
  return `${sign}₹${abs.toFixed(0)}`;
};

// Get IST-based greeting
export const getGreeting = (): string => {
  // Get current time in IST (UTC+5:30)
  const now = new Date();
  const utc = now.getTime() + now.getTimezoneOffset() * 60000;
  const istOffset = 5.5 * 60 * 60 * 1000; // IST is UTC+5:30
  const istTime = new Date(utc + istOffset);
  const hour = istTime.getHours();
  
  if (hour >= 5 && hour < 12) return 'Good Morning';
  if (hour >= 12 && hour < 17) return 'Good Afternoon';
  // Evening extends until midnight, no "Good Night"
  return 'Good Evening';
};

// Get current month and year
export const getCurrentMonthYear = (): string => {
  const months = ['January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'];
  const now = new Date();
  return `${months[now.getMonth()]} ${now.getFullYear()}`;
};

export const getCategoryIcon = (category: string): string => {
  const icons: Record<string, string> = {
    // Income
    'Salary': 'briefcase', 'Business Income': 'store', 'Freelance': 'laptop',
    'Consulting': 'account-tie', 'Interest': 'percent', 'Dividends': 'cash-multiple',
    'Rental Income': 'home-account', 'Bonus': 'gift', 'Commission': 'handshake',
    'Capital Gains': 'trending-up', 'Pension': 'account-clock', 'Refund': 'cash-refund',
    // Expense
    'Groceries': 'cart', 'Rent': 'home', 'Food & Dining': 'food-fork-drink',
    'Transport': 'car', 'Fuel': 'gas-station', 'Shopping': 'shopping',
    'Utilities': 'flash', 'Electricity': 'lightning-bolt', 'Water': 'water',
    'Internet': 'wifi', 'Mobile Recharge': 'cellphone', 'Entertainment': 'play-circle',
    'Health': 'heart-pulse', 'Medicine': 'pill', 'Insurance': 'shield-check',
    'Education': 'school', 'EMI': 'bank', 'Loan Repayment': 'bank-transfer',
    'Subscriptions': 'youtube-subscription', 'Personal Care': 'face-man-shimmer',
    'Clothing': 'tshirt-crew', 'Home Maintenance': 'wrench', 'Travel': 'airplane',
    'Gifts': 'gift', 'Donations': 'hand-heart', 'Taxes': 'file-document',
    // Investment
    'Mutual Funds': 'finance', 'SIP': 'chart-line', 'Stocks': 'chart-areaspline',
    'ETFs': 'chart-bar', 'Fixed Deposit': 'lock', 'PPF': 'shield-check',
    'NPS': 'account-cash', 'EPF': 'piggy-bank', 'Gold': 'diamond-stone',
    'Silver': 'diamond-outline', 'Copper': 'circle-double', 'Bonds': 'file-certificate',
    'Real Estate': 'home-city', 'Crypto': 'bitcoin', 'ULIP': 'umbrella',
    'Sovereign Gold Bond': 'star-circle', 'Government Securities': 'bank',
    // Fallback
    'Food': 'food', 'Other': 'dots-horizontal',
  };
  return icons[category] || 'circle';
};

export const getCategoryColor = (category: string, isDark: boolean): string => {
  const colors: Record<string, string> = {
    // Income
    'Salary': '#059669', 'Business Income': '#047857', 'Freelance': '#0EA5E9',
    'Consulting': '#0284C7', 'Interest': '#06B6D4', 'Dividends': '#84CC16',
    'Rental Income': '#D97706', 'Bonus': '#F59E0B', 'Commission': '#10B981',
    'Capital Gains': '#22C55E', 'Pension': '#14B8A6', 'Refund': '#6366F1',
    // Expense
    'Groceries': '#F59E0B', 'Rent': '#EF4444', 'Food & Dining': '#F97316',
    'Transport': '#3B82F6', 'Fuel': '#64748B', 'Shopping': '#EC4899',
    'Utilities': '#8B5CF6', 'Electricity': '#FBBF24', 'Water': '#0EA5E9',
    'Internet': '#6366F1', 'Mobile Recharge': '#A855F7', 'Entertainment': '#F59E0B',
    'Health': '#10B981', 'Medicine': '#14B8A6', 'Insurance': '#059669',
    'Education': '#3B82F6', 'EMI': '#DC2626', 'Loan Repayment': '#B91C1C',
    'Subscriptions': '#7C3AED', 'Personal Care': '#EC4899', 'Clothing': '#D946EF',
    'Home Maintenance': '#78716C', 'Travel': '#0EA5E9', 'Gifts': '#F43F5E',
    'Donations': '#10B981', 'Taxes': '#64748B',
    // Investment
    'Mutual Funds': '#3B82F6', 'SIP': '#6366F1', 'Stocks': '#8B5CF6',
    'ETFs': '#2563EB', 'Fixed Deposit': '#0891B2', 'PPF': '#059669',
    'NPS': '#22C55E', 'EPF': '#14B8A6', 'Gold': '#EAB308',
    'Silver': '#94A3B8', 'Copper': '#D97706', 'Bonds': '#0284C7',
    'Real Estate': '#78716C', 'Crypto': '#F59E0B', 'ULIP': '#7C3AED',
    'Sovereign Gold Bond': '#CA8A04', 'Government Securities': '#0369A1',
    // Goal categories (must match GoalsSection.tsx)
    'Safety': '#10B981', 'Purchase': '#F59E0B', 'Property': '#78716C',
    'Retirement': '#14B8A6', 'Wedding': '#EC4899',
    // Fallback
    'Food': '#F97316', 'Other': isDark ? '#94A3B8' : '#64748B',
  };
  return colors[category] || (isDark ? '#94A3B8' : '#64748B');
};

// Format date as "Feb 10"
export const formatShortDate = (dateStr: string): string => {
  const date = new Date(dateStr);
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${months[date.getMonth()]} ${date.getDate()}`;
};
