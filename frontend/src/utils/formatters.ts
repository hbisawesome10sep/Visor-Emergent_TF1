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
  if (hour >= 17 && hour < 21) return 'Good Evening';
  return 'Good Night';
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
    'Salary': 'briefcase',
    'Freelance': 'laptop',
    'Bonus': 'gift',
    'Interest': 'percent',
    'Dividend': 'cash-multiple',
    'Rent': 'home',
    'Groceries': 'cart',
    'Food': 'food',
    'Transport': 'car',
    'Shopping': 'shopping',
    'Utilities': 'flash',
    'Entertainment': 'play-circle',
    'Health': 'heart-pulse',
    'Education': 'school',
    'EMI': 'bank',
    'SIP': 'chart-line',
    'PPF': 'shield-check',
    'Stocks': 'chart-areaspline',
    'Mutual Funds': 'finance',
    'FD': 'lock',
    'Gold': 'diamond-stone',
    'NPS': 'account-cash',
    'Safety': 'shield',
    'Travel': 'airplane',
    'Purchase': 'tag',
    'Property': 'home-city',
    'Other': 'dots-horizontal',
  };
  return icons[category] || 'circle';
};

export const getCategoryColor = (category: string, isDark: boolean): string => {
  const colors: Record<string, string> = {
    'Rent': '#EF4444',
    'Groceries': '#F59E0B',
    'Food': '#F97316',
    'Transport': '#3B82F6',
    'Shopping': '#EC4899',
    'Utilities': '#8B5CF6',
    'Entertainment': '#FBBF24',
    'Health': '#10B981',
    'Education': '#14B8A6',
    'EMI': '#DC2626',
    'Salary': '#059669',
    'Freelance': '#0EA5E9',
    'Bonus': '#D97706',
    'Interest': '#06B6D4',
    'Dividend': '#84CC16',
    'SIP': '#6366F1',
    'PPF': '#059669',
    'Stocks': '#8B5CF6',
    'Mutual Funds': '#3B82F6',
    'FD': '#0891B2',
    'Gold': '#EAB308',
    'NPS': '#22C55E',
    'Other': isDark ? '#94A3B8' : '#64748B',
  };
  return colors[category] || (isDark ? '#94A3B8' : '#64748B');
};

// Format date as "Feb 10"
export const formatShortDate = (dateStr: string): string => {
  const date = new Date(dateStr);
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${months[date.getMonth()]} ${date.getDate()}`;
};
