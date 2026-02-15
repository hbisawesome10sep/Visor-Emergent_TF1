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

export const getGreeting = (): string => {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good Morning';
  if (hour < 17) return 'Good Afternoon';
  return 'Good Evening';
};

export const getCategoryIcon = (category: string): string => {
  const icons: Record<string, string> = {
    'Salary': 'briefcase',
    'Freelance': 'laptop',
    'Bonus': 'gift',
    'Rent': 'home',
    'Groceries': 'cart',
    'Food': 'food',
    'Transport': 'car',
    'Shopping': 'shopping',
    'Utilities': 'flash',
    'Entertainment': 'play-circle',
    'Health': 'heart-pulse',
    'EMI': 'bank',
    'SIP': 'chart-line',
    'PPF': 'shield-check',
    'Stocks': 'chart-areaspline',
    'Mutual Funds': 'finance',
    'FD': 'lock',
    'Gold': 'diamond-stone',
    'Safety': 'shield',
    'Travel': 'airplane',
    'Purchase': 'tag',
    'Property': 'home-city',
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
    'Entertainment': '#06B6D4',
    'Health': '#10B981',
    'EMI': '#DC2626',
    'Salary': '#059669',
    'Freelance': '#0EA5E9',
    'Bonus': '#D97706',
    'SIP': '#6366F1',
    'PPF': '#059669',
    'Stocks': '#8B5CF6',
    'Mutual Funds': '#3B82F6',
    'FD': '#0891B2',
    'Gold': '#EAB308',
  };
  return colors[category] || (isDark ? '#94A3B8' : '#64748B');
};
