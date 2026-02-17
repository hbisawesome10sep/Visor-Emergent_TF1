import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, RefreshControl,
  ActivityIndicator, Dimensions, Platform, StatusBar, Animated, Modal,
  TextInput, KeyboardAvoidingView, Alert,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import Svg, { Circle, G } from 'react-native-svg';
import { useAuth } from '../../src/context/AuthContext';
import { useTheme } from '../../src/context/ThemeContext';
import { Accent } from '../../src/utils/theme';
import { apiRequest } from '../../src/utils/api';
import { formatINR, formatINRShort, getCategoryColor, getCategoryIcon } from '../../src/utils/formatters';
import PieChart from '../../src/components/PieChart';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// ── Investment asset categories for allocation pie chart ──
const ASSET_CATEGORIES: Record<string, { label: string; color: string }> = {
  'Stocks': { label: 'Stocks', color: Accent.sapphire },
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

// ── Goal categories ──
const GOAL_CATS = ['Safety', 'Travel', 'Purchase', 'Property', 'Education', 'Retirement', 'Wedding', 'Other'];

// ── Types ──
type MarketItem = {
  key: string; name: string; price: number; change: number;
  change_percent: number; prev_close: number; icon: string; last_updated: string;
};
type Goal = {
  id: string; title: string; target_amount: number; current_amount: number;
  deadline: string; category: string;
};
type DashboardStats = {
  total_income: number; total_expenses: number; total_investments: number;
  invest_breakdown: Record<string, number>;
};

type PortfolioData = {
  total_invested: number;
  total_current_value: number;
  total_gain_loss: number;
  total_gain_loss_pct: number;
  categories: Array<{
    category: string; invested: number; current_value: number;
    gain_loss: number; gain_loss_pct: number; transactions: number;
  }>;
};

type Holding = {
  id: string; name: string; ticker: string; isin: string; category: string;
  quantity: number; buy_price: number; buy_date: string; source: string;
  current_price: number; invested_value: number; current_value: number;
  gain_loss: number; gain_loss_pct: number;
};
type HoldingsData = {
  holdings: Holding[];
  summary: { total_invested: number; total_current: number; total_gain_loss: number; total_gain_loss_pct: number; count: number };
};

const HOLDING_CATS = ['Stock', 'Mutual Fund', 'ETF', 'Gold', 'Silver', 'Bond', 'Other'];
const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

export default function InvestmentsScreen() {
  const { token } = useAuth();
  const { colors, isDark } = useTheme();
  const insets = useSafeAreaInsets();
  const HEADER_HEIGHT = 70 + insets.top;

  const [marketData, setMarketData] = useState<MarketItem[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [portfolio, setPortfolio] = useState<PortfolioData | null>(null);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showRiskModal, setShowRiskModal] = useState(false);
  const [showGoalModal, setShowGoalModal] = useState(false);
  const [editGoal, setEditGoal] = useState<Goal | null>(null);
  const [riskStep, setRiskStep] = useState(0);
  const [riskAnswers, setRiskAnswers] = useState<number[]>([]);
  const [riskProfile, setRiskProfile] = useState<'Conservative' | 'Moderate' | 'Aggressive'>('Moderate');
  const [goalForm, setGoalForm] = useState({ title: '', target_amount: '', current_amount: '0', deadline: '', category: 'Safety' });
  const [saving, setSaving] = useState(false);
  const [holdingsData, setHoldingsData] = useState<HoldingsData | null>(null);
  const [showHoldingModal, setShowHoldingModal] = useState(false);
  const [showCasModal, setShowCasModal] = useState(false);
  const [holdingForm, setHoldingForm] = useState({ name: '', ticker: '', isin: '', category: 'Stock', quantity: '', buy_price: '', buy_date: '' });
  const [casPassword, setCasPassword] = useState('');

  const fadeAnim = useRef(new Animated.Value(0)).current;

  const fetchData = useCallback(async () => {
    if (!token) return;
    try {
      const [statsData, goalsData, mktData, portfolioData, holdingsLive] = await Promise.all([
        apiRequest('/dashboard/stats', { token }),
        apiRequest('/goals', { token }),
        apiRequest('/market-data', {}),
        apiRequest('/portfolio-overview', { token }),
        apiRequest('/holdings/live', { token }),
      ]);
      setStats(statsData);
      setGoals(goalsData);
      setMarketData(mktData || []);
      setPortfolio(portfolioData);
      setHoldingsData(holdingsLive);
      Animated.timing(fadeAnim, { toValue: 1, duration: 500, useNativeDriver: true }).start();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const onRefresh = () => { setRefreshing(true); fetchData(); };

  // ── Goal handlers ──
  const openAddGoal = () => {
    setEditGoal(null);
    setGoalForm({ title: '', target_amount: '', current_amount: '0', deadline: '', category: 'Safety' });
    setShowGoalModal(true);
  };
  const openEditGoal = (g: Goal) => {
    setEditGoal(g);
    setGoalForm({ title: g.title, target_amount: g.target_amount.toString(), current_amount: g.current_amount.toString(), deadline: g.deadline, category: g.category });
    setShowGoalModal(true);
  };
  const handleSaveGoal = async () => {
    if (!goalForm.title || !goalForm.target_amount || !goalForm.category) { Alert.alert('Error', 'Please fill required fields'); return; }
    setSaving(true);
    try {
      const body = { title: goalForm.title, target_amount: parseFloat(goalForm.target_amount), current_amount: parseFloat(goalForm.current_amount || '0'), deadline: goalForm.deadline || '2026-12-31', category: goalForm.category };
      if (editGoal) { await apiRequest(`/goals/${editGoal.id}`, { method: 'PUT', token, body }); }
      else { await apiRequest('/goals', { method: 'POST', token, body }); }
      setShowGoalModal(false);
      fetchData();
    } catch (e: any) { Alert.alert('Error', e.message); }
    finally { setSaving(false); }
  };
  const handleDeleteGoal = (id: string, title: string) => {
    Alert.alert('Delete Goal', `Delete "${title}"?`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: async () => { await apiRequest(`/goals/${id}`, { method: 'DELETE', token }); fetchData(); } },
    ]);
  };

  // ── Risk assessment (simple 3-question version for now) ──
  const RISK_QUESTIONS = [
    { question: 'What is your investment time horizon?', options: [{ label: 'Short (1-3 years)', value: 1 }, { label: 'Medium (3-7 years)', value: 2 }, { label: 'Long (7+ years)', value: 3 }] },
    { question: 'How would you react if your portfolio dropped 20%?', options: [{ label: 'Sell everything', value: 1 }, { label: 'Sell some', value: 2 }, { label: 'Hold and wait', value: 3 }, { label: 'Buy more', value: 4 }] },
    { question: 'What percentage of income can you invest?', options: [{ label: 'Less than 10%', value: 1 }, { label: '10-20%', value: 2 }, { label: '20-30%', value: 3 }, { label: 'More than 30%', value: 4 }] },
  ];
  const handleRiskAnswer = (value: number) => {
    const newAnswers = [...riskAnswers, value];
    setRiskAnswers(newAnswers);
    if (riskStep < RISK_QUESTIONS.length - 1) { setRiskStep(riskStep + 1); }
    else {
      const avg = newAnswers.reduce((s, a) => s + a, 0) / newAnswers.length;
      setRiskProfile(avg <= 1.5 ? 'Conservative' : avg <= 2.8 ? 'Moderate' : 'Aggressive');
      setShowRiskModal(false); setRiskStep(0); setRiskAnswers([]);
    }
  };

  // ── Holdings handlers ──
  const openAddHolding = () => {
    setHoldingForm({ name: '', ticker: '', isin: '', category: 'Stock', quantity: '', buy_price: '', buy_date: '' });
    setShowHoldingModal(true);
  };
  const handleSaveHolding = async () => {
    if (!holdingForm.name || !holdingForm.quantity || !holdingForm.buy_price) { Alert.alert('Error', 'Name, Quantity, and Buy Price are required'); return; }
    setSaving(true);
    try {
      await apiRequest('/holdings', { method: 'POST', token, body: {
        name: holdingForm.name, ticker: holdingForm.ticker, isin: holdingForm.isin,
        category: holdingForm.category, quantity: parseFloat(holdingForm.quantity),
        buy_price: parseFloat(holdingForm.buy_price), buy_date: holdingForm.buy_date,
      }});
      setShowHoldingModal(false);
      fetchData();
    } catch (e: any) { Alert.alert('Error', e.message); }
    finally { setSaving(false); }
  };
  const handleDeleteHolding = (id: string, name: string) => {
    Alert.alert('Delete Holding', `Remove "${name}"?`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: async () => { await apiRequest(`/holdings/${id}`, { method: 'DELETE', token }); fetchData(); } },
    ]);
  };
  const handleCasUpload = async () => {
    try {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '.pdf';
      input.onchange = async (e: any) => {
        const file = e.target?.files?.[0];
        if (!file) return;
        setSaving(true);
        try {
          const formData = new FormData();
          formData.append('file', file);
          formData.append('password', casPassword);
          const resp = await fetch(`${BACKEND_URL}/api/holdings/upload-cas`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData,
          });
          const data = await resp.json();
          if (!resp.ok) throw new Error(data.detail || 'Upload failed');
          Alert.alert('Success', data.message);
          setShowCasModal(false);
          setCasPassword('');
          fetchData();
        } catch (err: any) {
          Alert.alert('Upload Error', err.message || 'Failed to parse CAS');
        } finally { setSaving(false); }
      };
      input.click();
    } catch (e: any) { Alert.alert('Error', 'File upload is not supported on this platform'); }
  };

  // ── Computed values ──
  const totalInvested = portfolio?.total_invested || stats?.total_investments || 0;
  const allocation = stats?.invest_breakdown || {};

  // Build allocation data for pie chart - prefer portfolio categories if available
  const pieData = portfolio?.categories?.length
    ? portfolio.categories.map(cat => ({
        category: ASSET_CATEGORIES[cat.category]?.label || cat.category,
        amount: cat.invested,
        color: ASSET_CATEGORIES[cat.category]?.color || '#94A3B8',
      }))
    : Object.entries(allocation).filter(([_, amt]) => amt > 0).map(([cat, amt]) => ({
        category: ASSET_CATEGORIES[cat]?.label || cat,
        amount: amt,
        color: ASSET_CATEGORIES[cat]?.color || '#94A3B8',
      }));

  // Strategy based on risk
  const strategies = {
    Conservative: { name: 'Safe Harbor', allocation: [{ name: 'Debt', p: 60, c: Accent.emerald }, { name: 'Equity', p: 25, c: Accent.sapphire }, { name: 'Gold', p: 15, c: Accent.amber }] },
    Moderate: { name: 'Balanced Growth', allocation: [{ name: 'Equity', p: 40, c: Accent.sapphire }, { name: 'Debt', p: 30, c: Accent.emerald }, { name: 'Gold', p: 15, c: Accent.amber }, { name: 'Alt', p: 15, c: Accent.amethyst }] },
    Aggressive: { name: 'High Growth', allocation: [{ name: 'Equity', p: 70, c: Accent.sapphire }, { name: 'Alt', p: 15, c: Accent.amethyst }, { name: 'Debt', p: 10, c: Accent.emerald }, { name: 'Gold', p: 5, c: Accent.amber }] },
  };
  const currentStrategy = strategies[riskProfile];

  // Market data last updated
  const lastUpdatedStr = marketData.length > 0 ? (() => {
    const d = new Date(marketData[0].last_updated);
    const istOffset = 5.5 * 60 * 60 * 1000;
    const ist = new Date(d.getTime() + istOffset);
    return ist.toLocaleString('en-IN', { hour: '2-digit', minute: '2-digit', day: 'numeric', month: 'short' });
  })() : '';

  // Tax saving
  const section80CUsed = Math.min(totalInvested * 0.4, 150000);

  // Goals summary
  const totalGoalTarget = goals.reduce((s, g) => s + g.target_amount, 0);
  const totalGoalCurrent = goals.reduce((s, g) => s + g.current_amount, 0);
  const overallGoalProgress = totalGoalTarget > 0 ? (totalGoalCurrent / totalGoalTarget) * 100 : 0;

  // ── Helper: format price for markets (Indian comma system) ──
  const fmtPrice = (p: number) => {
    const num = Math.round(p);
    const str = num.toString();
    const digits = str.split('').reverse();
    let formatted = '';
    for (let i = 0; i < digits.length; i++) {
      if (i === 3 || (i > 3 && (i - 3) % 2 === 0)) formatted = ',' + formatted;
      formatted = digits[i] + formatted;
    }
    return formatted;
  };

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: colors.background }]}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#F97316" />
          <Text style={[styles.loadingText, { color: colors.textSecondary }]}>Loading investments...</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <StatusBar barStyle={isDark ? 'light-content' : 'dark-content'} />

      {/* ═══ HEADER ═══ */}
      <View style={[styles.stickyHeader, { paddingTop: insets.top, backgroundColor: isDark ? '#000000' : '#FFFFFF' }]}>
        <View style={[styles.headerContent, { backgroundColor: isDark ? '#000000' : '#FFFFFF', borderBottomColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)' }]}>
          <View style={styles.headerLeft}>
            <Text data-testid="invest-header-title" style={[styles.headerTitle, { color: isDark ? Accent.amber : '#D97706' }]}>Invest</Text>
            <Text style={[styles.headerSubtitle, { color: colors.textSecondary }]}>Markets & Portfolio</Text>
          </View>
          <TouchableOpacity data-testid="invest-refresh-btn" style={[styles.refreshBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)' }]} onPress={onRefresh}>
            <MaterialCommunityIcons name="refresh" size={20} color="#F97316" />
          </TouchableOpacity>
        </View>
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={[styles.scrollContent, { paddingTop: HEADER_HEIGHT + 12 }]}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#F97316" />}
        showsVerticalScrollIndicator={false}
      >
        {/* ═══════════════════════════════════════════════════════════
             SECTION 1: INDIAN MARKETS (TOP)
           ═══════════════════════════════════════════════════════════ */}
        <View style={styles.marketSection}>
          <View style={styles.marketSectionHeader}>
            <Text data-testid="markets-section-title" style={[styles.sectionTitle, { color: colors.textPrimary, marginBottom: 0 }]}>Indian Markets</Text>
            {lastUpdatedStr ? (
              <Text style={[styles.updatedAt, { color: colors.textSecondary }]}>Live  {lastUpdatedStr}</Text>
            ) : null}
          </View>

          <View data-testid="market-cards-grid" style={[styles.marketTable, {
            backgroundColor: isDark ? 'rgba(10,10,11,0.9)' : '#FFFFFF',
            borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
          }]}>
            {marketData.map((item, idx) => {
              const isUp = item.change_percent >= 0;
              const isLast = idx === marketData.length - 1;
              const isIndex = !item.key.includes('gold') && !item.key.includes('silver');
              return (
                <View key={item.key} data-testid={`market-card-${item.key}`} style={[styles.marketRow, !isLast && { borderBottomWidth: 1, borderBottomColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)' }]}>
                  <View style={styles.marketRowLeft}>
                    <View style={[styles.marketDot, { backgroundColor: isUp ? Accent.emerald : Accent.ruby }]} />
                    <View>
                      <Text style={[styles.marketRowName, { color: colors.textPrimary }]}>{item.name}</Text>
                      <Text style={[styles.marketRowSub, { color: colors.textSecondary }]}>
                        {isIndex ? 'Index' : item.key.includes('gold') ? '24K / 10g' : '999 / 1Kg'}
                      </Text>
                    </View>
                  </View>
                  <View style={styles.marketRowRight}>
                    <Text data-testid={`market-price-${item.key}`} style={[styles.marketRowPrice, { color: colors.textPrimary }]}>
                      {isIndex ? '' : '₹'}{fmtPrice(item.price)}
                    </Text>
                    <View style={styles.marketRowChangeWrap}>
                      <MaterialCommunityIcons name={isUp ? 'triangle' : 'triangle-down'} size={10} color={isUp ? Accent.emerald : Accent.ruby} />
                      <Text style={[styles.marketRowChange, { color: isUp ? Accent.emerald : Accent.ruby }]}>
                        {fmtPrice(Math.abs(Math.round(item.change)))} ({Math.abs(item.change_percent).toFixed(2)}%)
                      </Text>
                    </View>
                  </View>
                </View>
              );
            })}
          </View>
        </View>

        {/* ═══════════════════════════════════════════════════════════
             SECTION 2: PORTFOLIO OVERVIEW
           ═══════════════════════════════════════════════════════════ */}
        <Text data-testid="portfolio-section-title" style={[styles.sectionTitle, { color: colors.textPrimary, marginTop: 28 }]}>Portfolio Overview</Text>

        {portfolio && portfolio.total_invested > 0 && (
          <View data-testid="portfolio-card" style={[styles.portfolioCard, {
            backgroundColor: isDark ? 'rgba(10,10,11,0.9)' : '#FFFFFF',
            borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
          }]}>
            <View style={styles.portfolioSummaryRow}>
              <View style={{ flex: 1 }}>
                <Text style={[styles.portfolioSmallLabel, { color: colors.textSecondary }]}>Invested</Text>
                <Text data-testid="portfolio-invested-value" style={[styles.portfolioMainNum, { color: colors.textPrimary }]}>
                  {formatINR(portfolio.total_invested)}
                </Text>
              </View>
              <View style={[styles.portfolioDivider, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]} />
              <View style={{ flex: 1, alignItems: 'flex-end' }}>
                <Text style={[styles.portfolioSmallLabel, { color: colors.textSecondary }]}>Current Value</Text>
                <Text data-testid="portfolio-current-value" style={[styles.portfolioMainNum, { color: colors.textPrimary }]}>
                  {formatINR(portfolio.total_current_value)}
                </Text>
              </View>
            </View>
            <View style={[styles.gainLossBadge, {
              backgroundColor: portfolio.total_gain_loss >= 0 ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
            }]}>
              <MaterialCommunityIcons
                name={portfolio.total_gain_loss >= 0 ? 'trending-up' : 'trending-down'}
                size={16}
                color={portfolio.total_gain_loss >= 0 ? Accent.emerald : Accent.ruby}
              />
              <Text data-testid="portfolio-gain-loss" style={[styles.gainLossText, {
                color: portfolio.total_gain_loss >= 0 ? Accent.emerald : Accent.ruby,
              }]}>
                {portfolio.total_gain_loss >= 0 ? '+' : ''}{formatINR(portfolio.total_gain_loss)} ({portfolio.total_gain_loss >= 0 ? '+' : ''}{portfolio.total_gain_loss_pct.toFixed(2)}%)
              </Text>
            </View>
            <View style={[styles.categoryBreakdownHeader, { borderTopColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)' }]}>
              <Text style={[styles.breakdownHeaderText, { color: colors.textSecondary, flex: 1 }]}>Category</Text>
              <Text style={[styles.breakdownHeaderText, { color: colors.textSecondary, width: 80, textAlign: 'right' as any }]}>Invested</Text>
              <Text style={[styles.breakdownHeaderText, { color: colors.textSecondary, width: 80, textAlign: 'right' as any }]}>Current</Text>
              <Text style={[styles.breakdownHeaderText, { color: colors.textSecondary, width: 70, textAlign: 'right' as any }]}>Return</Text>
            </View>
            {portfolio.categories.map((cat, idx) => (
              <View key={cat.category} data-testid={`portfolio-cat-${cat.category}`} style={[styles.categoryRow, idx < portfolio.categories.length - 1 && { borderBottomWidth: 1, borderBottomColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.03)' }]}>
                <View style={{ flex: 1, flexDirection: 'row' as any, alignItems: 'center' as any, gap: 8 }}>
                  <View style={[styles.catDot, { backgroundColor: ASSET_CATEGORIES[cat.category]?.color || '#94A3B8' }]} />
                  <View>
                    <Text style={[styles.catName, { color: colors.textPrimary }]}>{cat.category}</Text>
                    <Text style={[styles.catTxnCount, { color: colors.textSecondary }]}>{cat.transactions} txn{cat.transactions > 1 ? 's' : ''}</Text>
                  </View>
                </View>
                <Text style={[styles.catNum, { color: colors.textSecondary, width: 80 }]}>{formatINRShort(cat.invested)}</Text>
                <Text style={[styles.catNum, { color: colors.textPrimary, width: 80 }]}>{formatINRShort(cat.current_value)}</Text>
                <Text style={[styles.catReturn, { color: cat.gain_loss >= 0 ? Accent.emerald : Accent.ruby, width: 70 }]}>
                  {cat.gain_loss >= 0 ? '+' : ''}{cat.gain_loss_pct.toFixed(1)}%
                </Text>
              </View>
            ))}
          </View>
        )}

        {(!portfolio || portfolio.total_invested === 0) && (
          <View style={[styles.emptyPortfolio, { backgroundColor: isDark ? 'rgba(10,10,11,0.9)' : '#FFFFFF', borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)' }]}>
            <MaterialCommunityIcons name="wallet-outline" size={36} color={colors.textSecondary} />
            <Text style={[styles.emptyGoalsTitle, { color: colors.textPrimary }]}>No investments yet</Text>
            <Text style={[styles.emptyGoalsSubtitle, { color: colors.textSecondary }]}>Add investment transactions to track your portfolio</Text>
          </View>
        )}

        {/* ═══════════════════════════════════════════════════════════
             SECTION 2.5: MY HOLDINGS (Manual + CAS)
           ═══════════════════════════════════════════════════════════ */}
        <View style={styles.sectionHeader}>
          <Text data-testid="holdings-section-title" style={[styles.sectionTitle, { color: colors.textPrimary, marginBottom: 0 }]}>My Holdings</Text>
          <View style={{ flexDirection: 'row' as any, gap: 8 }}>
            <TouchableOpacity data-testid="upload-cas-btn" style={[styles.casBtn, { borderColor: '#F97316' }]} onPress={() => setShowCasModal(true)}>
              <MaterialCommunityIcons name="file-upload-outline" size={14} color="#F97316" />
              <Text style={[styles.casBtnText, { color: '#F97316' }]}>CAS</Text>
            </TouchableOpacity>
            <TouchableOpacity data-testid="add-holding-btn" style={[styles.addGoalBtn, { backgroundColor: '#F97316' }]} onPress={openAddHolding}>
              <MaterialCommunityIcons name="plus" size={14} color="#fff" />
              <Text style={styles.addGoalText}>Add</Text>
            </TouchableOpacity>
          </View>
        </View>

        {holdingsData && holdingsData.holdings.length > 0 ? (
          <View data-testid="holdings-card" style={[styles.holdingsCard, {
            backgroundColor: isDark ? 'rgba(10,10,11,0.9)' : '#FFFFFF',
            borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
          }]}>
            {/* Holdings summary */}
            <View style={styles.holdingsSummaryRow}>
              <View>
                <Text style={[styles.portfolioSmallLabel, { color: colors.textSecondary }]}>Holdings Value</Text>
                <Text style={[styles.holdingsSummaryNum, { color: colors.textPrimary }]}>{formatINR(holdingsData.summary.total_current)}</Text>
              </View>
              <View style={[styles.gainLossBadge, {
                backgroundColor: holdingsData.summary.total_gain_loss >= 0 ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
                marginHorizontal: 0, marginBottom: 0,
              }]}>
                <Text style={[styles.gainLossText, {
                  color: holdingsData.summary.total_gain_loss >= 0 ? Accent.emerald : Accent.ruby,
                }]}>
                  {holdingsData.summary.total_gain_loss >= 0 ? '+' : ''}{holdingsData.summary.total_gain_loss_pct.toFixed(2)}%
                </Text>
              </View>
            </View>

            {/* Holdings list */}
            {holdingsData.holdings.map((h, idx) => {
              const isGain = h.gain_loss >= 0;
              const isLast = idx === holdingsData.holdings.length - 1;
              return (
                <TouchableOpacity key={h.id} data-testid={`holding-row-${h.id}`}
                  style={[styles.holdingRow, !isLast && { borderBottomWidth: 1, borderBottomColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.03)' }]}
                  onLongPress={() => handleDeleteHolding(h.id, h.name)}>
                  <View style={{ flex: 1 }}>
                    <Text style={[styles.holdingName, { color: colors.textPrimary }]} numberOfLines={1}>{h.name}</Text>
                    <Text style={[styles.holdingSub, { color: colors.textSecondary }]}>
                      {h.quantity} {h.category === 'Mutual Fund' ? 'units' : 'shares'} @ {fmtPrice(Math.round(h.buy_price))}
                    </Text>
                  </View>
                  <View style={{ alignItems: 'flex-end' as any }}>
                    <Text style={[styles.holdingValue, { color: colors.textPrimary }]}>{formatINRShort(h.current_value)}</Text>
                    <Text style={[styles.holdingGain, { color: isGain ? Accent.emerald : Accent.ruby }]}>
                      {isGain ? '+' : ''}{h.gain_loss_pct.toFixed(1)}%
                    </Text>
                  </View>
                </TouchableOpacity>
              );
            })}
          </View>
        ) : (
          <View style={[styles.emptyPortfolio, { backgroundColor: isDark ? 'rgba(10,10,11,0.9)' : '#FFFFFF', borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)' }]}>
            <MaterialCommunityIcons name="briefcase-outline" size={36} color={colors.textSecondary} />
            <Text style={[styles.emptyGoalsTitle, { color: colors.textPrimary }]}>No holdings added</Text>
            <Text style={[styles.emptyGoalsSubtitle, { color: colors.textSecondary }]}>Add stocks and mutual funds manually or upload your CAS statement</Text>
          </View>
        )}

        {/* ═══════════════════════════════════════════════════════════
             SECTION 3: ASSET ALLOCATION (Pie Chart)
           ═══════════════════════════════════════════════════════════ */}
        <Text data-testid="allocation-section-title" style={[styles.sectionTitle, { color: colors.textPrimary }]}>Asset Allocation</Text>
        <View data-testid="allocation-card" style={[styles.glassCard, {
          backgroundColor: isDark ? 'rgba(10, 10, 11, 0.85)' : 'rgba(255, 255, 255, 0.85)',
          borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
        }]}>
          {pieData.length > 0 ? (
            <>
              <View style={styles.pieContainer}>
                <PieChart data={pieData} size={170} colors={colors} isDark={isDark} />
              </View>
              <View style={styles.legendGrid}>
                {pieData.map((item, idx) => {
                  const pct = totalInvested > 0 ? ((item.amount / totalInvested) * 100).toFixed(1) : '0';
                  return (
                    <View key={idx} data-testid={`allocation-legend-${item.category}`} style={styles.legendItem}>
                      <View style={[styles.legendDot, { backgroundColor: item.color }]} />
                      <Text style={[styles.legendName, { color: colors.textPrimary }]}>{item.category}</Text>
                      <Text style={[styles.legendPercent, { color: colors.textSecondary }]}>{pct}%</Text>
                      <Text style={[styles.legendAmount, { color: colors.textSecondary }]}>{formatINRShort(item.amount)}</Text>
                    </View>
                  );
                })}
              </View>
            </>
          ) : (
            <View style={styles.emptyPie}>
              <MaterialCommunityIcons name="chart-pie" size={40} color={colors.textSecondary} />
              <Text style={[styles.emptyPieText, { color: colors.textSecondary }]}>Add investment transactions to see allocation</Text>
            </View>
          )}
        </View>

        {/* ═══════════════════════════════════════════════════════════
             SECTION 4: RISK PROFILE & STRATEGY
           ═══════════════════════════════════════════════════════════ */}
        <Text data-testid="risk-section-title" style={[styles.sectionTitle, { color: colors.textPrimary }]}>Risk Profile & Strategy</Text>
        <View data-testid="risk-card" style={[styles.riskCard, {
          backgroundColor: isDark ? 'rgba(10, 10, 11, 0.85)' : 'rgba(255, 255, 255, 0.85)',
          borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
        }]}>
          <View style={styles.riskHeader}>
            <View style={[styles.riskBadge, {
              backgroundColor: riskProfile === 'Conservative' ? 'rgba(59,130,246,0.15)' : riskProfile === 'Moderate' ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)',
            }]}>
              <MaterialCommunityIcons
                name={riskProfile === 'Conservative' ? 'shield-check' : riskProfile === 'Moderate' ? 'scale-balance' : 'rocket-launch'}
                size={20}
                color={riskProfile === 'Conservative' ? Accent.sapphire : riskProfile === 'Moderate' ? Accent.amber : Accent.ruby}
              />
              <Text data-testid="risk-profile-label" style={[styles.riskBadgeText, { color: riskProfile === 'Conservative' ? Accent.sapphire : riskProfile === 'Moderate' ? Accent.amber : Accent.ruby }]}>
                {riskProfile}
              </Text>
            </View>
            <TouchableOpacity data-testid="risk-retake-btn" style={[styles.retakeBtn, { borderColor: colors.border }]} onPress={() => { setShowRiskModal(true); setRiskStep(0); setRiskAnswers([]); }}>
              <Text style={[styles.retakeBtnText, { color: colors.textSecondary }]}>Retake Assessment</Text>
            </TouchableOpacity>
          </View>
          <Text style={[styles.strategyName, { color: colors.textPrimary }]}>{currentStrategy.name} Strategy</Text>
          <View style={styles.strategyBar}>
            {currentStrategy.allocation.map((item, i) => (
              <View key={i} style={[styles.strategySegment, { width: `${item.p}%`, backgroundColor: item.c }]}>
                {item.p >= 15 && <Text style={styles.strategySegmentText}>{item.p}%</Text>}
              </View>
            ))}
          </View>
          <View style={styles.strategyLegend}>
            {currentStrategy.allocation.map((item, i) => (
              <View key={i} style={styles.strategyLegendItem}>
                <View style={[styles.strategyLegendDot, { backgroundColor: item.c }]} />
                <Text style={[styles.strategyLegendText, { color: colors.textSecondary }]}>{item.name} ({item.p}%)</Text>
              </View>
            ))}
          </View>
        </View>

        {/* ═══════════════════════════════════════════════════════════
             SECTION 5: TAX SAVING (80C)
           ═══════════════════════════════════════════════════════════ */}
        <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Tax Saving</Text>
        <View style={[styles.glassCard, {
          backgroundColor: isDark ? 'rgba(10, 10, 11, 0.85)' : 'rgba(255, 255, 255, 0.85)',
          borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
        }]}>
          <View style={styles.taxHeader}>
            <View>
              <Text style={[styles.taxTitle, { color: colors.textPrimary }]}>Section 80C</Text>
              <Text style={[styles.taxUsed, { color: colors.textSecondary }]}>{formatINRShort(section80CUsed)} / 1.5L</Text>
            </View>
            <View style={[styles.taxPercentBadge, { backgroundColor: section80CUsed >= 150000 ? 'rgba(16,185,129,0.1)' : 'rgba(245,158,11,0.1)' }]}>
              <Text style={[styles.taxPercentText, { color: section80CUsed >= 150000 ? Accent.emerald : Accent.amber }]}>
                {((section80CUsed / 150000) * 100).toFixed(0)}%
              </Text>
            </View>
          </View>
          <View style={[styles.taxBarBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
            <View style={[styles.taxBarFill, { width: `${Math.min((section80CUsed / 150000) * 100, 100)}%`, backgroundColor: '#F97316' }]} />
          </View>
        </View>

        {/* ═══════════════════════════════════════════════════════════
             SECTION 6: FINANCIAL GOALS
           ═══════════════════════════════════════════════════════════ */}
        <View style={styles.sectionHeader}>
          <Text style={[styles.sectionTitle, { color: colors.textPrimary, marginBottom: 0 }]}>Financial Goals</Text>
          <TouchableOpacity data-testid="add-goal-btn" style={[styles.addGoalBtn, { backgroundColor: '#F97316' }]} onPress={openAddGoal}>
            <MaterialCommunityIcons name="plus" size={16} color="#fff" />
            <Text style={styles.addGoalText}>Add</Text>
          </TouchableOpacity>
        </View>

        {goals.length === 0 ? (
          <View style={[styles.emptyGoals, { backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)', borderColor: colors.border }]}>
            <MaterialCommunityIcons name="flag-variant-outline" size={36} color={colors.textSecondary} />
            <Text style={[styles.emptyGoalsTitle, { color: colors.textPrimary }]}>No goals yet</Text>
            <Text style={[styles.emptyGoalsSubtitle, { color: colors.textSecondary }]}>Set financial goals to track your progress</Text>
          </View>
        ) : (
          <>
            {goals.length > 0 && (
              <View style={[styles.goalsOverviewCard, {
                backgroundColor: isDark ? 'rgba(249,115,22,0.1)' : 'rgba(249,115,22,0.06)',
                borderColor: isDark ? 'rgba(249,115,22,0.2)' : 'rgba(249,115,22,0.15)',
              }]}>
                <View style={styles.goalsOverviewRow}>
                  <View>
                    <Text style={[styles.goalsOverviewLabel, { color: colors.textSecondary }]}>Overall Progress</Text>
                    <Text style={[styles.goalsOverviewAmount, { color: colors.textPrimary }]}>{formatINRShort(totalGoalCurrent)} / {formatINRShort(totalGoalTarget)}</Text>
                  </View>
                  <View style={[styles.goalsPercentBadge, { backgroundColor: overallGoalProgress >= 50 ? 'rgba(16,185,129,0.15)' : 'rgba(249,115,22,0.15)' }]}>
                    <Text style={[styles.goalsPercentText, { color: overallGoalProgress >= 50 ? Accent.emerald : '#F97316' }]}>{overallGoalProgress.toFixed(0)}%</Text>
                  </View>
                </View>
                <View style={[styles.goalsProgressBar, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)' }]}>
                  <View style={[styles.goalsProgressFill, { width: `${Math.min(overallGoalProgress, 100)}%`, backgroundColor: '#F97316' }]} />
                </View>
              </View>
            )}
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.goalsScroll}>
              {goals.map(goal => {
                const progress = goal.target_amount > 0 ? (goal.current_amount / goal.target_amount) * 100 : 0;
                const progressColor = progress >= 75 ? Accent.emerald : progress >= 40 ? Accent.amber : Accent.ruby;
                return (
                  <TouchableOpacity key={goal.id} data-testid={`goal-card-${goal.id}`} style={[styles.goalCard, {
                    backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.9)',
                    borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
                  }]} onPress={() => openEditGoal(goal)} onLongPress={() => handleDeleteGoal(goal.id, goal.title)}>
                    <View style={styles.goalCardHeader}>
                      <View style={[styles.goalIconWrap, { backgroundColor: `${getCategoryColor(goal.category, isDark)}20` }]}>
                        <MaterialCommunityIcons name={getCategoryIcon(goal.category) as any} size={16} color={getCategoryColor(goal.category, isDark)} />
                      </View>
                      <Text style={[styles.goalPercent, { color: progressColor }]}>{progress.toFixed(0)}%</Text>
                    </View>
                    <Text style={[styles.goalTitle, { color: colors.textPrimary }]} numberOfLines={1}>{goal.title}</Text>
                    <View style={[styles.goalBarBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)' }]}>
                      <View style={[styles.goalBarFill, { width: `${Math.min(progress, 100)}%`, backgroundColor: progressColor }]} />
                    </View>
                    <Text style={[styles.goalAmounts, { color: colors.textSecondary }]}>{formatINRShort(goal.current_amount)} / {formatINRShort(goal.target_amount)}</Text>
                  </TouchableOpacity>
                );
              })}
            </ScrollView>
          </>
        )}

        <View style={{ height: 100 }} />
      </ScrollView>

      {/* ═══ ADD GOAL FAB ═══ */}
      <TouchableOpacity data-testid="goal-fab" style={styles.fab} onPress={openAddGoal}>
        <LinearGradient colors={['#EA580C', Accent.ruby]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.fabGradient}>
          <MaterialCommunityIcons name="plus" size={28} color="#fff" />
        </LinearGradient>
      </TouchableOpacity>

      {/* ═══ GOAL MODAL ═══ */}
      <Modal visible={showGoalModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.modalKav}>
            <View style={[styles.modalContent, { backgroundColor: colors.surface }]}>
              <View style={styles.modalHandle} />
              <View style={styles.modalHeader}>
                <Text style={[styles.modalTitle, { color: colors.textPrimary }]}>{editGoal ? 'Edit Goal' : 'New Goal'}</Text>
                <TouchableOpacity data-testid="goal-modal-close" onPress={() => setShowGoalModal(false)}>
                  <MaterialCommunityIcons name="close" size={24} color={colors.textSecondary} />
                </TouchableOpacity>
              </View>
              <TextInput data-testid="goal-title-input" style={[styles.input, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                value={goalForm.title} onChangeText={v => setGoalForm(p => ({ ...p, title: v }))} placeholder="Goal title" placeholderTextColor={colors.textSecondary} />
              <View style={styles.inputRow}>
                <TextInput data-testid="goal-target-input" style={[styles.input, styles.halfInput, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                  value={goalForm.target_amount} onChangeText={v => setGoalForm(p => ({ ...p, target_amount: v }))} placeholder="Target" placeholderTextColor={colors.textSecondary} keyboardType="decimal-pad" />
                <TextInput data-testid="goal-current-input" style={[styles.input, styles.halfInput, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                  value={goalForm.current_amount} onChangeText={v => setGoalForm(p => ({ ...p, current_amount: v }))} placeholder="Saved" placeholderTextColor={colors.textSecondary} keyboardType="decimal-pad" />
              </View>
              <TextInput data-testid="goal-deadline-input" style={[styles.input, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                value={goalForm.deadline} onChangeText={v => setGoalForm(p => ({ ...p, deadline: v }))} placeholder="Deadline (YYYY-MM-DD)" placeholderTextColor={colors.textSecondary} />
              <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>Category</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.catScroll}>
                {GOAL_CATS.map(c => (
                  <TouchableOpacity key={c} data-testid={`goal-cat-${c}`} style={[styles.catChip, {
                    backgroundColor: goalForm.category === c ? '#F97316' : colors.background,
                    borderColor: goalForm.category === c ? '#F97316' : colors.border,
                  }]} onPress={() => setGoalForm(p => ({ ...p, category: c }))}>
                    <Text style={{ color: goalForm.category === c ? '#fff' : colors.textSecondary, fontSize: 13 }}>{c}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
              <TouchableOpacity data-testid="goal-save-btn" style={styles.saveBtn} onPress={handleSaveGoal} disabled={saving}>
                <LinearGradient colors={['#EA580C', Accent.ruby]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.saveBtnGradient}>
                  {saving ? <ActivityIndicator color="#fff" /> : <Text style={styles.saveBtnText}>{editGoal ? 'Update Goal' : 'Create Goal'}</Text>}
                </LinearGradient>
              </TouchableOpacity>
            </View>
          </KeyboardAvoidingView>
        </View>
      </Modal>

      {/* ═══ RISK MODAL ═══ */}
      <Modal visible={showRiskModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, { backgroundColor: colors.surface }]}>
            <View style={styles.modalHandle} />
            <View style={styles.modalHeader}>
              <Text style={[styles.modalTitle, { color: colors.textPrimary }]}>Risk Assessment</Text>
              <TouchableOpacity data-testid="risk-modal-close" onPress={() => setShowRiskModal(false)}>
                <MaterialCommunityIcons name="close" size={24} color={colors.textSecondary} />
              </TouchableOpacity>
            </View>
            <View style={styles.progressRow}>
              {RISK_QUESTIONS.map((_, i) => (
                <View key={i} style={[styles.progressDot, { backgroundColor: i <= riskStep ? '#F97316' : colors.border, width: i === riskStep ? 24 : 8 }]} />
              ))}
            </View>
            <Text style={[styles.questionText, { color: colors.textPrimary }]}>{RISK_QUESTIONS[riskStep].question}</Text>
            <View style={styles.optionsContainer}>
              {RISK_QUESTIONS[riskStep].options.map((opt, i) => (
                <TouchableOpacity key={i} data-testid={`risk-option-${i}`} style={[styles.optionBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)', borderColor: colors.border }]}
                  onPress={() => handleRiskAnswer(opt.value)}>
                  <Text style={[styles.optionText, { color: colors.textPrimary }]}>{opt.label}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        </View>
      </Modal>

      {/* ═══ ADD HOLDING MODAL ═══ */}
      <Modal visible={showHoldingModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.modalKav}>
            <View style={[styles.modalContent, { backgroundColor: colors.surface }]}>
              <View style={styles.modalHandle} />
              <View style={styles.modalHeader}>
                <Text style={[styles.modalTitle, { color: colors.textPrimary }]}>Add Holding</Text>
                <TouchableOpacity data-testid="holding-modal-close" onPress={() => setShowHoldingModal(false)}>
                  <MaterialCommunityIcons name="close" size={24} color={colors.textSecondary} />
                </TouchableOpacity>
              </View>
              <TextInput data-testid="holding-name-input" style={[styles.input, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                value={holdingForm.name} onChangeText={v => setHoldingForm(p => ({ ...p, name: v }))} placeholder="Name (e.g. Reliance Industries)" placeholderTextColor={colors.textSecondary} />
              <View style={styles.inputRow}>
                <TextInput data-testid="holding-ticker-input" style={[styles.input, styles.halfInput, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                  value={holdingForm.ticker} onChangeText={v => setHoldingForm(p => ({ ...p, ticker: v }))} placeholder="Ticker (e.g. RELIANCE.NS)" placeholderTextColor={colors.textSecondary} autoCapitalize="characters" />
                <TextInput data-testid="holding-isin-input" style={[styles.input, styles.halfInput, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                  value={holdingForm.isin} onChangeText={v => setHoldingForm(p => ({ ...p, isin: v }))} placeholder="ISIN (optional)" placeholderTextColor={colors.textSecondary} />
              </View>
              <View style={styles.inputRow}>
                <TextInput data-testid="holding-qty-input" style={[styles.input, styles.halfInput, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                  value={holdingForm.quantity} onChangeText={v => setHoldingForm(p => ({ ...p, quantity: v }))} placeholder="Quantity" placeholderTextColor={colors.textSecondary} keyboardType="decimal-pad" />
                <TextInput data-testid="holding-price-input" style={[styles.input, styles.halfInput, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                  value={holdingForm.buy_price} onChangeText={v => setHoldingForm(p => ({ ...p, buy_price: v }))} placeholder="Buy Price" placeholderTextColor={colors.textSecondary} keyboardType="decimal-pad" />
              </View>
              <TextInput data-testid="holding-date-input" style={[styles.input, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                value={holdingForm.buy_date} onChangeText={v => setHoldingForm(p => ({ ...p, buy_date: v }))} placeholder="Buy Date (YYYY-MM-DD)" placeholderTextColor={colors.textSecondary} />
              <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>Category</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.catScroll}>
                {HOLDING_CATS.map(c => (
                  <TouchableOpacity key={c} data-testid={`holding-cat-${c}`} style={[styles.catChip, {
                    backgroundColor: holdingForm.category === c ? '#F97316' : colors.background,
                    borderColor: holdingForm.category === c ? '#F97316' : colors.border,
                  }]} onPress={() => setHoldingForm(p => ({ ...p, category: c }))}>
                    <Text style={{ color: holdingForm.category === c ? '#fff' : colors.textSecondary, fontSize: 13 }}>{c}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
              <TouchableOpacity data-testid="holding-save-btn" style={styles.saveBtn} onPress={handleSaveHolding} disabled={saving}>
                <LinearGradient colors={['#EA580C', Accent.ruby]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.saveBtnGradient}>
                  {saving ? <ActivityIndicator color="#fff" /> : <Text style={styles.saveBtnText}>Add Holding</Text>}
                </LinearGradient>
              </TouchableOpacity>
            </View>
          </KeyboardAvoidingView>
        </View>
      </Modal>

      {/* ═══ CAS UPLOAD MODAL ═══ */}
      <Modal visible={showCasModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, { backgroundColor: colors.surface }]}>
            <View style={styles.modalHandle} />
            <View style={styles.modalHeader}>
              <Text style={[styles.modalTitle, { color: colors.textPrimary }]}>Upload CAS Statement</Text>
              <TouchableOpacity data-testid="cas-modal-close" onPress={() => setShowCasModal(false)}>
                <MaterialCommunityIcons name="close" size={24} color={colors.textSecondary} />
              </TouchableOpacity>
            </View>
            <Text style={[styles.casDesc, { color: colors.textSecondary }]}>
              Upload your NSDL/CDSL Consolidated Account Statement (CAS) PDF to auto-import your holdings.
            </Text>
            <TextInput data-testid="cas-password-input" style={[styles.input, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
              value={casPassword} onChangeText={setCasPassword} placeholder="PDF Password (if any)" placeholderTextColor={colors.textSecondary} secureTextEntry />
            <TouchableOpacity data-testid="cas-upload-btn" style={styles.saveBtn} onPress={handleCasUpload} disabled={saving}>
              <LinearGradient colors={['#EA580C', Accent.ruby]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.saveBtnGradient}>
                {saving ? <ActivityIndicator color="#fff" /> : (
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                    <MaterialCommunityIcons name="file-upload-outline" size={20} color="#fff" />
                    <Text style={styles.saveBtnText}>Choose PDF & Upload</Text>
                  </View>
                )}
              </LinearGradient>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 12 },
  loadingText: { fontSize: 14 },

  // Header
  stickyHeader: { position: 'absolute', top: 0, left: 0, right: 0, zIndex: 100 },
  headerContent: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 20, paddingVertical: 12, borderBottomWidth: 1 },
  headerLeft: { flex: 1 },
  headerTitle: { fontSize: 24, fontFamily: 'DM Sans', fontWeight: '700' as any, letterSpacing: -0.5 },
  headerSubtitle: { fontSize: 13, marginTop: 2 },
  refreshBtn: { width: 40, height: 40, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },

  // Scroll
  scrollView: { flex: 1 },
  scrollContent: { paddingHorizontal: 20 },

  // Section
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  sectionTitle: { fontSize: 18, fontFamily: 'DM Sans', fontWeight: '700' as any, marginBottom: 14, letterSpacing: -0.3 },
  updatedAt: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '500' as any },

  // ── Market Section ──
  marketSection: { marginBottom: 24 },
  marketSectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  marketTable: { borderRadius: 18, borderWidth: 1, overflow: 'hidden' },
  marketRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 18, paddingVertical: 16 },
  marketRowLeft: { flexDirection: 'row', alignItems: 'center', gap: 12, flex: 1 },
  marketDot: { width: 8, height: 8, borderRadius: 4 },
  marketRowName: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '700' as any, letterSpacing: -0.2 },
  marketRowSub: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '500' as any, marginTop: 1 },
  marketRowRight: { alignItems: 'flex-end' },
  marketRowPrice: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '700' as any, letterSpacing: -0.3 },
  marketRowChangeWrap: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 2 },
  marketRowChange: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600' as any },

  // ── Portfolio ──
  portfolioCard: { borderRadius: 18, borderWidth: 1, overflow: 'hidden', marginBottom: 24 },
  portfolioSummaryRow: { flexDirection: 'row', alignItems: 'center', padding: 20, paddingBottom: 16 },
  portfolioDivider: { width: 1, height: 40, marginHorizontal: 16 },
  portfolioSmallLabel: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '600' as any, textTransform: 'uppercase', letterSpacing: 0.5 },
  portfolioMainNum: { fontSize: 22, fontFamily: 'DM Sans', fontWeight: '700' as any, letterSpacing: -0.5, marginTop: 4 },
  gainLossBadge: { flexDirection: 'row', alignItems: 'center', gap: 8, marginHorizontal: 20, marginBottom: 16, paddingHorizontal: 14, paddingVertical: 8, borderRadius: 12, alignSelf: 'flex-start' },
  gainLossText: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' as any },
  categoryBreakdownHeader: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 20, paddingVertical: 10, borderTopWidth: 1 },
  breakdownHeaderText: { fontSize: 10, fontFamily: 'DM Sans', fontWeight: '600' as any, textTransform: 'uppercase', letterSpacing: 0.5 },
  categoryRow: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 20, paddingVertical: 14 },
  catDot: { width: 8, height: 8, borderRadius: 4 },
  catName: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '600' as any },
  catTxnCount: { fontSize: 10, fontFamily: 'DM Sans', fontWeight: '500' as any, marginTop: 1 },
  catNum: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '600' as any, textAlign: 'right' },
  catReturn: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' as any, textAlign: 'right' },
  emptyPortfolio: { alignItems: 'center', padding: 28, borderRadius: 18, borderWidth: 1, marginBottom: 24 },

  // ── Glass Card ──
  glassCard: { borderRadius: 20, padding: 20, borderWidth: 1, marginBottom: 20 },

  // ── Pie Chart ──
  pieContainer: { alignItems: 'center', marginBottom: 20 },
  legendGrid: { gap: 10 },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  legendDot: { width: 10, height: 10, borderRadius: 5 },
  legendName: { flex: 1, fontSize: 13, fontFamily: 'DM Sans', fontWeight: '600' as any },
  legendPercent: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '700' as any, width: 40, textAlign: 'right' },
  legendAmount: { fontSize: 12, width: 60, textAlign: 'right' },
  emptyPie: { alignItems: 'center', padding: 32, gap: 10 },
  emptyPieText: { fontSize: 13, textAlign: 'center' },

  // ── Risk Profile ──
  riskCard: { borderRadius: 20, padding: 20, borderWidth: 1, marginBottom: 20 },
  riskHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  riskBadge: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 14, paddingVertical: 8, borderRadius: 14 },
  riskBadgeText: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700' as any },
  retakeBtn: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 12, borderWidth: 1 },
  retakeBtnText: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600' as any },
  strategyName: { fontSize: 17, fontFamily: 'DM Sans', fontWeight: '700' as any, marginBottom: 14 },
  strategyBar: { flexDirection: 'row', height: 22, borderRadius: 11, overflow: 'hidden', marginBottom: 12 },
  strategySegment: { justifyContent: 'center', alignItems: 'center' },
  strategySegmentText: { fontSize: 10, fontFamily: 'DM Sans', fontWeight: '700' as any, color: '#fff' },
  strategyLegend: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  strategyLegendItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  strategyLegendDot: { width: 8, height: 8, borderRadius: 4 },
  strategyLegendText: { fontSize: 12 },

  // ── Tax ──
  taxHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  taxTitle: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '700' as any },
  taxUsed: { fontSize: 12, marginTop: 2 },
  taxPercentBadge: { paddingHorizontal: 10, paddingVertical: 6, borderRadius: 10 },
  taxPercentText: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' as any },
  taxBarBg: { height: 8, borderRadius: 4, overflow: 'hidden' },
  taxBarFill: { height: '100%', borderRadius: 4 },

  // ── Goals ──
  addGoalBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 14, paddingVertical: 8, borderRadius: 12 },
  addGoalText: { color: '#fff', fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' as any },
  goalsOverviewCard: { borderRadius: 16, padding: 16, borderWidth: 1, marginBottom: 14 },
  goalsOverviewRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  goalsOverviewLabel: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600' as any },
  goalsOverviewAmount: { fontSize: 17, fontFamily: 'DM Sans', fontWeight: '700' as any, marginTop: 2 },
  goalsPercentBadge: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 12 },
  goalsPercentText: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700' as any },
  goalsProgressBar: { height: 6, borderRadius: 3, overflow: 'hidden' },
  goalsProgressFill: { height: '100%', borderRadius: 3 },
  emptyGoals: { alignItems: 'center', padding: 28, borderRadius: 18, borderWidth: 1, marginBottom: 16 },
  emptyGoalsTitle: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '700' as any, marginTop: 10 },
  emptyGoalsSubtitle: { fontSize: 12, marginTop: 4 },
  goalsScroll: { marginBottom: 8 },
  goalCard: { width: 155, padding: 14, borderRadius: 16, borderWidth: 1, marginRight: 10 },
  goalCardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  goalIconWrap: { width: 34, height: 34, borderRadius: 10, justifyContent: 'center', alignItems: 'center' },
  goalPercent: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' as any },
  goalTitle: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' as any, marginBottom: 8 },
  goalBarBg: { height: 5, borderRadius: 3, overflow: 'hidden', marginBottom: 6 },
  goalBarFill: { height: '100%', borderRadius: 3 },
  goalAmounts: { fontSize: 10 },

  // ── FAB ──
  fab: { position: 'absolute', right: 20, bottom: 90, zIndex: 99999, borderRadius: 24, shadowColor: '#EA580C', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 8, elevation: 6, borderWidth: 1, borderColor: 'rgba(255,255,255,0.2)' },
  fabGradient: { width: 52, height: 52, borderRadius: 26, justifyContent: 'center', alignItems: 'center' },

  // ── Modals ──
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modalKav: { maxHeight: '90%' },
  modalContent: { borderTopLeftRadius: 28, borderTopRightRadius: 28, padding: 24, paddingBottom: 40 },
  modalHandle: { width: 40, height: 4, borderRadius: 2, backgroundColor: '#CBD5E1', alignSelf: 'center', marginBottom: 16 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  modalTitle: { fontSize: 20, fontFamily: 'DM Sans', fontWeight: '700' as any },
  input: { height: 52, borderRadius: 14, borderWidth: 1, paddingHorizontal: 16, fontSize: 15, marginBottom: 12 },
  inputRow: { flexDirection: 'row', gap: 10 },
  halfInput: { flex: 1 },
  fieldLabel: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '600' as any, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8 },
  catScroll: { maxHeight: 40, marginBottom: 16 },
  catChip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 16, borderWidth: 1, marginRight: 8 },
  saveBtn: { borderRadius: 999, overflow: 'hidden', marginTop: 8 },
  saveBtnGradient: { height: 56, justifyContent: 'center', alignItems: 'center' },
  saveBtnText: { color: '#fff', fontSize: 17, fontFamily: 'DM Sans', fontWeight: '700' as any },
  progressRow: { flexDirection: 'row', gap: 6, marginBottom: 20, justifyContent: 'center' },
  progressDot: { height: 6, borderRadius: 3 },
  questionText: { fontSize: 18, fontFamily: 'DM Sans', fontWeight: '700' as any, textAlign: 'center', marginBottom: 24, lineHeight: 26 },
  optionsContainer: { gap: 10 },
  optionBtn: { padding: 16, borderRadius: 14, borderWidth: 1 },
  optionText: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '500' as any, textAlign: 'center' },
});
