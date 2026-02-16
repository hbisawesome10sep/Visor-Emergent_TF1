// Visor 2.0 — Cyber-Fintech Luxury Theme
// True Black + Pure White + Neon Accents with Bloom

// Neon palette (shared between themes for card fills, indicators, etc.)
export const Neon = {
  green: '#39FF14',
  red: '#FF073A',
  orange: '#FF6B00',
  cyan: '#00FFD1',
  blue: '#00B4FF',
  purple: '#B026FF',
  yellow: '#FFE600',
} as const;

export const Colors = {
  light: {
    background: '#FFFFFF',
    surface: '#F7F7F8',
    primary: '#008F7A',
    primaryLight: '#DFFFF8',
    secondary: '#7C3AED',
    secondaryLight: '#F0E6FF',
    textPrimary: '#09090B',
    textSecondary: '#52525B',
    border: '#E4E4E7',
    success: '#059669',
    warning: '#D97706',
    error: '#DC2626',
    glassBg: 'rgba(255, 255, 255, 0.88)',
    glassBorder: 'rgba(0, 0, 0, 0.06)',
    income: '#059669',
    expense: '#DC2626',
    investment: '#0369A1',
    tabBar: '#FFFFFF',
    tabBarBorder: '#E4E4E7',
    cardShadow: '#000000',
  },
  dark: {
    background: '#000000',
    surface: '#0A0A0B',
    primary: '#00FFD1',
    primaryLight: '#003D33',
    secondary: '#B026FF',
    secondaryLight: '#1F0A33',
    textPrimary: '#FFFFFF',
    textSecondary: '#71717A',
    border: '#27272A',
    success: '#39FF14',
    warning: '#FFE600',
    error: '#FF073A',
    glassBg: 'rgba(10, 10, 11, 0.85)',
    glassBorder: 'rgba(255, 255, 255, 0.06)',
    income: '#39FF14',
    expense: '#FF073A',
    investment: '#00B4FF',
    tabBar: '#000000',
    tabBarBorder: '#18181B',
    cardShadow: '#00FFD1',
  },
};

export type ThemeColors = typeof Colors.light;
