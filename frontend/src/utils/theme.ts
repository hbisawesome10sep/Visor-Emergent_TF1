// Visor 2.0 — Premium Fintech Theme
// True Black + Pure White + Refined Jewel Tones

// Accent palette for cards, indicators, fills
export const Accent = {
  emerald: '#10B981',
  ruby: '#EF4444',
  amber: '#F59E0B',
  teal: '#14B8A6',
  sapphire: '#3B82F6',
  amethyst: '#8B5CF6',
  rose: '#F43F5E',
} as const;

export const Colors = {
  light: {
    background: '#FFFFFF',
    surface: '#F9FAFB',
    card: '#FFFFFF',
    primary: '#059669',
    primaryLight: '#ECFDF5',
    secondary: '#7C3AED',
    secondaryLight: '#F5F3FF',
    textPrimary: '#111827',
    textSecondary: '#6B7280',
    border: '#E5E7EB',
    success: '#059669',
    warning: '#D97706',
    error: '#DC2626',
    glassBg: 'rgba(255, 255, 255, 0.92)',
    glassBorder: 'rgba(0, 0, 0, 0.06)',
    income: '#059669',
    expense: '#DC2626',
    investment: '#2563EB',
    tabBar: '#FFFFFF',
    tabBarBorder: '#E5E7EB',
    cardShadow: '#000000',
  },
  dark: {
    background: '#000000',
    surface: '#0A0A0A',
    card: '#161616',
    primary: '#10B981',
    primaryLight: '#064E3B',
    secondary: '#8B5CF6',
    secondaryLight: '#1E1338',
    textPrimary: '#F9FAFB',
    textSecondary: '#9CA3AF',
    border: '#1F2937',
    success: '#10B981',
    warning: '#F59E0B',
    error: '#EF4444',
    glassBg: 'rgba(10, 10, 10, 0.88)',
    glassBorder: 'rgba(255, 255, 255, 0.06)',
    income: '#10B981',
    expense: '#EF4444',
    investment: '#3B82F6',
    tabBar: '#000000',
    tabBarBorder: '#1F2937',
    cardShadow: '#10B981',
  },
};

export type ThemeColors = typeof Colors.light;
