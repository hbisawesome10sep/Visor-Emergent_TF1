import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, StyleSheet, RefreshControl, ActivityIndicator,
  TouchableOpacity, Dimensions, Modal, Alert,
  Platform, StatusBar,
} from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { BlurView } from 'expo-blur';
import { useRouter } from 'expo-router';
import Svg, { Circle, G, Polyline, Line, Text as SvgText, Rect } from 'react-native-svg';
import DateTimePicker from '@react-native-community/datetimepicker';

import { useAuth } from '../../src/context/AuthContext';
import { useTheme } from '../../src/context/ThemeContext';
import { useScreenContext } from '../../src/context/ScreenContext';
import { apiRequest } from '../../src/utils/api';
import {
  formatINR,
  formatINRShort,
  getGreeting,
  getCurrentMonthYear,
  getCategoryColor,
  getCategoryIcon,
  formatShortDate,
} from '../../src/utils/formatters';
import LiquidFillCard from '../../src/components/LiquidFillCard';
import PieChart from '../../src/components/PieChart';
import TrendChart from '../../src/components/TrendChart';
import FAB from '../../src/components/FAB';
import { FinancialHealthCard } from '../../src/components/FinancialHealthCard';
import { Accent } from '../../src/utils/theme';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

type FrequencyOption = 'Quarter' | 'Month' | 'Year' | 'Custom';

type DashboardStats = {
  total_income: number;
  total_expenses: number;
  total_investments: number;
  net_balance: number;
  savings: number;
  savings_rate: number;
  expense_ratio: number;
  investment_ratio: number;
  category_breakdown: Record<string, number>;
  budget_items: Array<{ category: string; amount: number; percentage: number }>;
  invest_breakdown: Record<string, number>;
  recent_transactions: any[];
  monthly_income: number;
  monthly_expenses: number;
  monthly_investments: number;
  monthly_savings: number;
  goal_count: number;
  goal_progress: number;
  transaction_count: number;
  credit_card_summary?: {
    total_outstanding: number;
    total_limit: number;
    utilization: number;
    total_expenses: number;
    total_payments: number;
    monthly_expenses: number;
    cards_count: number;
  };
};

type Goal = {
  id: string;
  title: string;
  target_amount: number;
  current_amount: number;
  deadline: string;
  category: string;
};

// Health Score - now uses backend-provided score for consistency
function getScoreLabel(score: number): { label: string; color: string } {
  if (score >= 80) return { label: 'Excellent', color: Accent.emerald };
  if (score >= 65) return { label: 'Good', color: Accent.teal };
  if (score >= 50) return { label: 'Fair', color: Accent.amber };
  if (score >= 35) return { label: 'Needs Work', color: Accent.amber };
  return { label: 'Critical', color: Accent.ruby };
}

function getScoreColor(score: number): string {
  if (score >= 76) return Accent.emerald;
  if (score >= 61) return Accent.teal;
  if (score >= 41) return Accent.amber;
  return Accent.ruby;
}

export default function DashboardScreen() {
  const { user, token } = useAuth();
  const { colors, isDark } = useTheme();
  const { setCurrentScreen } = useScreenContext();
  const router = useRouter();
  const insets = useSafeAreaInsets();

  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedFrequency, setSelectedFrequency] = useState<FrequencyOption>('Month');

  // Set screen context for AI awareness
  useEffect(() => {
    setCurrentScreen('dashboard');
  }, [setCurrentScreen]);
  const [showDatePicker, setShowDatePicker] = useState(false);
  
  // Calculate header height dynamically based on safe area
  const HEADER_HEIGHT = 70 + insets.top;
  const [showScoreBack, setShowScoreBack] = useState(false);
  const [showTrendBack, setShowTrendBack] = useState(false);
  const [userCreatedAt, setUserCreatedAt] = useState<string>('');
  
  // Date range state
  const [dateRange, setDateRange] = useState({
    start: new Date(new Date().getFullYear(), new Date().getMonth(), 1),
    end: new Date(),
  });
  // Custom date range input state - Date objects for calendar picker
  const [customStartDate, setCustomStartDate] = useState(new Date(new Date().getFullYear(), 0, 1));
  const [customEndDate, setCustomEndDate] = useState(new Date());
  const [showNativePicker, setShowNativePicker] = useState(false);
  const [activePickerField, setActivePickerField] = useState<'start' | 'end'>('start');

  // Get date range based on frequency - no userCreatedAt constraint for Q/M/Y
  const getDateRangeForFrequency = (freq: FrequencyOption): { start: Date; end: Date } => {
    const now = new Date();
    let start: Date;
    let end = now;
    
    switch (freq) {
      case 'Quarter':
        start = new Date(now.getFullYear(), Math.floor(now.getMonth() / 3) * 3, 1);
        break;
      case 'Year':
        start = new Date(now.getFullYear(), 0, 1);
        break;
      case 'Custom':
        start = dateRange.start;
        end = dateRange.end;
        break;
      case 'Month':
      default:
        start = new Date(now.getFullYear(), now.getMonth(), 1);
        break;
    }
    
    return { start, end };
  };

  const fetchData = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      // Calculate date range inline to avoid stale closure issues
      const now = new Date();
      let startDate: Date;
      let endDate = now;
      
      switch (selectedFrequency) {
        case 'Quarter':
          startDate = new Date(now.getFullYear(), Math.floor(now.getMonth() / 3) * 3, 1);
          break;
        case 'Year':
          startDate = new Date(now.getFullYear(), 0, 1);
          break;
        case 'Custom':
          startDate = dateRange.start;
          endDate = dateRange.end;
          break;
        case 'Month':
        default:
          startDate = new Date(now.getFullYear(), now.getMonth(), 1);
          break;
      }
      
      // Safely format dates - fallback to current month if invalid
      const safeStart = isNaN(startDate.getTime()) ? new Date(now.getFullYear(), now.getMonth(), 1) : startDate;
      const safeEnd = isNaN(endDate.getTime()) ? now : endDate;
      const startStr = safeStart.toISOString().split('T')[0];
      const endStr = safeEnd.toISOString().split('T')[0];
      
      console.log(`[Dashboard] Fetching stats: ${selectedFrequency} | ${startStr} → ${endStr}`);
      
      const [s, g] = await Promise.all([
        apiRequest(`/dashboard/stats?start_date=${startStr}&end_date=${endStr}`, { token }),
        apiRequest('/goals', { token }),
      ]);
      setStats(s);
      setGoals(g);
      // Store user's created_at for date range limit
      if (s?.user_created_at) {
        setUserCreatedAt(s.user_created_at);
      }
    } catch (e: any) {
      console.warn('[Dashboard] Fetch error:', e?.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token, selectedFrequency, dateRange]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const handleFrequencyChange = (freq: FrequencyOption) => {
    if (freq === 'Custom') {
      // Pre-fill custom inputs with current date range
      const earliest = userCreatedAt ? new Date(userCreatedAt) : new Date(new Date().getFullYear(), 0, 1);
      setCustomStartDate(earliest);
      setCustomEndDate(new Date());
      setShowDatePicker(true);
    } else {
      setSelectedFrequency(freq);
    }
  };

  const handleApplyCustomRange = () => {
    if (customStartDate > customEndDate) {
      Alert.alert('Invalid Range', 'Start date must be before end date');
      return;
    }
    setDateRange({ start: customStartDate, end: customEndDate });
    setSelectedFrequency('Custom');
    setShowDatePicker(false);
  };

  const openDatePicker = (field: 'start' | 'end') => {
    setActivePickerField(field);
    setShowNativePicker(true);
  };

  const handleNativeDateChange = (event: any, selectedDate?: Date) => {
    // On Android, always dismiss first
    setShowNativePicker(false);
    if (event.type === 'dismissed' || !selectedDate) return;
    if (activePickerField === 'start') {
      setCustomStartDate(selectedDate);
    } else {
      setCustomEndDate(selectedDate);
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={[styles.safe, { backgroundColor: colors.background }]}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
      </SafeAreaView>
    );
  }

  // Calculate values
  const incomeTarget = stats?.total_income || 1;
  const expensePercent = Math.min(((stats?.total_expenses || 0) / incomeTarget) * 100, 100);
  const savingsRate = stats?.savings_rate || 0;
  const investmentRate = stats?.total_income ? (stats.total_investments / stats.total_income) * 100 : 0;
  const runwayMonths = stats?.total_expenses ? ((stats.total_income - stats.total_expenses) * 6) / stats.total_expenses : 0;

  // Health Score
  // Use backend-provided health score (consistent with Insights page)
  const healthScore = stats?.health_score?.overall ?? 0;
  const scoreInfo = getScoreLabel(healthScore);
  const scoreColor = getScoreColor(healthScore);
  const breakdown = stats?.health_score?.breakdown ?? { savings: 0, investments: 0, spending: 0, goals: 0 };

  // Prepare pie chart data
  const pieData = Object.entries(stats?.category_breakdown || {}).map(([category, amount]) => ({
    category,
    amount: amount as number,
    color: getCategoryColor(category, isDark),
  }));

  // Use real trend data from API or fallback to monthly data
  const trendData = stats?.trend_data && stats.trend_data.length > 0 
    ? stats.trend_data 
    : [
        { label: 'This Period', income: stats?.total_income || 0, expenses: stats?.total_expenses || 0, investments: stats?.total_investments || 0 },
      ];
  
  // Trend insights from API
  const trendInsights = stats?.trend_insights || [];

  const fabActions = [
    {
      icon: 'cash-minus',
      label: 'Add Expense',
      color: colors.expense,
      onPress: () => {
        router.push({ pathname: '/(tabs)/transactions', params: { type: 'expense', action: 'add' } });
      },
    },
    {
      icon: 'cash-plus',
      label: 'Add Income',
      color: colors.income,
      onPress: () => {
        router.push({ pathname: '/(tabs)/transactions', params: { type: 'income', action: 'add' } });
      },
    },
    {
      icon: 'flag-variant',
      label: 'Add Goal',
      color: colors.investment,
      onPress: () => router.push('/(tabs)/investments'),
    },
    {
      icon: 'book-open-page-variant',
      label: 'Books & Reports',
      color: Accent.amethyst,
      onPress: () => router.push('/books'),
    },
  ];

  const frequencies: FrequencyOption[] = ['Quarter', 'Month', 'Year', 'Custom'];

  // Format current date range display
  const range = getDateRangeForFrequency(selectedFrequency);
  const rangeDisplay = selectedFrequency === 'Month' 
    ? getCurrentMonthYear()
    : selectedFrequency === 'Quarter'
    ? `Q${Math.floor(new Date().getMonth() / 3) + 1} ${new Date().getFullYear()}`
    : selectedFrequency === 'Year'
    ? `${new Date().getFullYear()}`
    : `${range.start.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })} - ${range.end.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}`;

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <StatusBar barStyle={isDark ? 'light-content' : 'dark-content'} />

      {/* Header */}
      <View style={[styles.stickyHeader, { paddingTop: insets.top, backgroundColor: isDark ? '#000000' : '#FFFFFF' }]}>
        <View
          style={[
            styles.headerContent,
            {
              backgroundColor: isDark ? '#000000' : '#FFFFFF',
              borderBottomColor: isDark ? '#1F2937' : '#E5E7EB',
            },
          ]}
        >
          <View style={styles.headerLeft}>
            <View style={styles.greetingRow}>
              <Text style={[styles.greetingText, { color: colors.primary }]}>{getGreeting()}</Text>
              <Text style={[styles.greetingName, { color: colors.textPrimary }]}>
                , {user?.full_name?.split(' ')[0] || 'User'}
              </Text>
            </View>
            <Text style={[styles.monthYear, { color: colors.textSecondary }]}>
              {rangeDisplay}
            </Text>
          </View>

          <View style={styles.headerRight}>
            {/* Frequency Selector */}
            <View
              style={[
                styles.frequencyPills,
                { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' },
              ]}
            >
              {frequencies.map((freq) => (
                <TouchableOpacity
                  key={freq}
                  style={[
                    styles.freqPill,
                    selectedFrequency === freq && { backgroundColor: colors.primary },
                  ]}
                  onPress={() => handleFrequencyChange(freq)}
                >
                  <Text
                    style={[
                      styles.freqText,
                      { color: selectedFrequency === freq ? '#fff' : colors.textSecondary },
                    ]}
                  >
                    {freq.charAt(0)}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* Settings */}
            <TouchableOpacity
              data-testid="settings-btn"
              style={[
                styles.themeBtn,
                { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.06)' },
              ]}
              onPress={() => router.push('/(tabs)/settings')}
            >
              <MaterialCommunityIcons
                name="cog-outline"
                size={18}
                color={isDark ? '#9CA3AF' : '#6B7280'}
              />
            </TouchableOpacity>
          </View>
        </View>
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={[styles.scrollContent, { paddingTop: HEADER_HEIGHT + 16 }]}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />
        }
        showsVerticalScrollIndicator={false}
      >
        {/* Active date range indicator */}
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', marginBottom: 8, marginTop: 4 }}>
          <MaterialCommunityIcons name="calendar-range" size={14} color={colors.textSecondary} />
          <Text style={{ fontSize: 12, color: colors.textSecondary, marginLeft: 6, fontFamily: 'DM Sans', fontWeight: '500' as any }}>
            {selectedFrequency === 'Custom' 
              ? `${dateRange.start.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })} - ${dateRange.end.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}`
              : selectedFrequency === 'Month'
              ? new Date().toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })
              : selectedFrequency === 'Quarter'
              ? `Q${Math.floor(new Date().getMonth() / 3) + 1} ${new Date().getFullYear()}`
              : `Year ${new Date().getFullYear()}`
            }
          </Text>
        </View>

        {/* ═══ FINANCIAL HEALTH SCORE CARD (New Redesigned) ═══ */}
        <FinancialHealthCard
          data={{
            overall_score: healthScore,
            grade: scoreInfo.label,
            has_sufficient_data: stats?.health_score?.has_sufficient_data ?? (stats?.total_income > 0),
            savings_rate: stats?.savings_rate || 0,
            investment_rate: stats?.investment_ratio || 0,
            expense_ratio: stats?.expense_ratio || 0,
            goal_progress: stats?.goal_progress || 0,
            breakdown: breakdown,
          }}
          isDark={isDark}
          colors={colors}
        />

        {/* ═══ OVERVIEW CARDS (Liquid Fill) ═══ */}
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Overview</Text>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.cardsRow}
          >
            <LiquidFillCard
              title="Total Income"
              amount={formatINRShort(stats?.total_income || 0)}
              percentChange={12.5}
              fillPercent={100 - expensePercent}
              gradient={[Accent.emerald, '#047857']}
              icon="arrow-down-circle"
              onPress={() => router.push('/(tabs)/transactions')}
              colors={colors}
              isDark={isDark}
            />
            <LiquidFillCard
              title="Total Expenses"
              amount={formatINRShort(stats?.total_expenses || 0)}
              percentChange={-8.2}
              fillPercent={expensePercent}
              gradient={[Accent.ruby, Accent.rose]}
              icon="arrow-up-circle"
              onPress={() => router.push('/(tabs)/transactions')}
              colors={colors}
              isDark={isDark}
            />
            <LiquidFillCard
              title="Investments"
              amount={formatINRShort(stats?.total_investments || 0)}
              fillPercent={Math.min(100, ((stats?.total_investments || 0) / (stats?.total_income || 1)) * 100)}
              gradient={[Accent.sapphire, '#4F46E5']}
              icon="trending-up"
              onPress={() => router.push('/(tabs)/investments')}
              colors={colors}
              isDark={isDark}
            />
            {stats?.credit_card_summary && stats.credit_card_summary.cards_count > 0 && (
              <LiquidFillCard
                title="CC Spend"
                amount={formatINRShort(stats.credit_card_summary.total_outstanding)}
                fillPercent={Math.min(100, stats.credit_card_summary.utilization)}
                gradient={['#7C3AED', '#6366F1']}
                icon="credit-card"
                onPress={() => router.push('/credit-cards')}
                colors={colors}
                isDark={isDark}
              />
            )}
          </ScrollView>
        </View>

        {/* ═══ CREDIT CARD SECTION ═══ */}
        <TouchableOpacity
          testID="dashboard-cc-section"
          activeOpacity={0.88}
          onPress={() => router.push('/credit-cards')}
          style={[styles.glassCard, styles.ccSection, {
            backgroundColor: isDark ? 'rgba(10,10,11,0.9)' : 'rgba(255,255,255,0.85)',
            borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
          }]}
        >
          {/* Section header row */}
          <View style={styles.ccSectionHeader}>
            <View style={styles.ccSectionLeft}>
              <View style={[styles.ccSectionIcon, { backgroundColor: 'rgba(99,102,241,0.18)' }]}>
                <MaterialCommunityIcons name="credit-card-multiple-outline" size={18} color="#818CF8" />
              </View>
              <Text style={[styles.ccSectionTitle, { color: colors.textPrimary }]}>Credit Cards</Text>
            </View>
            <View style={styles.ccManageRow}>
              <Text style={styles.ccManageText}>Manage</Text>
              <MaterialCommunityIcons name="chevron-right" size={16} color="#818CF8" />
            </View>
          </View>

          {stats?.credit_card_summary && stats.credit_card_summary.cards_count > 0 ? (
            /* Has cards — show stats */
            <>
              <View style={styles.ccStatsRow}>
                <View style={styles.ccStatItem}>
                  <Text style={[styles.ccStatLabel, { color: colors.textSecondary }]}>Outstanding</Text>
                  <Text style={[styles.ccStatAmount, { color: '#F87171' }]}>
                    {formatINRShort(stats.credit_card_summary.total_outstanding)}
                  </Text>
                </View>
                <View style={[styles.ccStatDivider, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.07)' }]} />
                <View style={styles.ccStatItem}>
                  <Text style={[styles.ccStatLabel, { color: colors.textSecondary }]}>Credit Limit</Text>
                  <Text style={[styles.ccStatAmount, { color: colors.textPrimary }]}>
                    {formatINRShort(stats.credit_card_summary.total_limit)}
                  </Text>
                </View>
                <View style={[styles.ccStatDivider, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.07)' }]} />
                <View style={styles.ccStatItem}>
                  <Text style={[styles.ccStatLabel, { color: colors.textSecondary }]}>Utilization</Text>
                  <Text style={[styles.ccStatAmount, {
                    color: stats.credit_card_summary.utilization >= 80 ? '#F87171'
                      : stats.credit_card_summary.utilization >= 50 ? '#FBBF24'
                      : '#34D399',
                  }]}>
                    {stats.credit_card_summary.utilization.toFixed(1)}%
                  </Text>
                </View>
              </View>
              {/* Utilization bar */}
              <View style={[styles.ccUtilBar, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
                <View style={[styles.ccUtilFill, {
                  width: `${Math.min(stats.credit_card_summary.utilization, 100)}%` as any,
                  backgroundColor: stats.credit_card_summary.utilization >= 80 ? '#F87171'
                    : stats.credit_card_summary.utilization >= 50 ? '#FBBF24'
                    : '#34D399',
                }]} />
              </View>
              <Text style={[styles.ccCardCount, { color: colors.textSecondary }]}>
                {stats.credit_card_summary.cards_count} card{stats.credit_card_summary.cards_count > 1 ? 's' : ''} linked
              </Text>
            </>
          ) : (
            /* No cards — empty state */
            <View style={styles.ccEmptyState}>
              <MaterialCommunityIcons name="credit-card-plus-outline" size={28} color="#818CF8" style={{ marginBottom: 8 }} />
              <Text style={[styles.ccEmptyTitle, { color: colors.textPrimary }]}>No Credit Cards Linked</Text>
              <Text style={[styles.ccEmptySubtitle, { color: colors.textSecondary }]}>
                Add your cards to track spending & utilization
              </Text>
            </View>
          )}
        </TouchableOpacity>

        {/* ═══ EXPENSE BREAKDOWN (Pie Chart) ═══ */}
        {pieData.length > 0 && (
          <View
            style={[
              styles.glassCard,
              {
                backgroundColor: isDark ? 'rgba(10, 10, 11, 0.9)' : 'rgba(255, 255, 255, 0.85)',
                borderColor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)',
              },
            ]}
          >
            <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>Expense Breakdown</Text>
            <View style={styles.pieContainer}>
              <PieChart data={pieData} size={160} colors={colors} isDark={isDark} />
              <View style={styles.pieLegend}>
                {pieData.slice(0, 5).map((item) => (
                  <View key={item.category} style={styles.legendRow}>
                    <View style={[styles.legendDot, { backgroundColor: item.color }]} />
                    <Text
                      style={[styles.legendCat, { color: colors.textPrimary }]}
                      numberOfLines={1}
                    >
                      {item.category}
                    </Text>
                    <Text style={[styles.legendAmt, { color: colors.textSecondary }]}>
                      {formatINRShort(item.amount)}
                    </Text>
                  </View>
                ))}
              </View>
            </View>
          </View>
        )}

        {/* ═══ TREND ANALYSIS (Redesigned) ═══ */}
        <TouchableOpacity
          activeOpacity={0.95}
          onPress={() => setShowTrendBack(!showTrendBack)}
          style={[
            styles.trendCard,
            {
              backgroundColor: isDark ? 'rgba(10, 10, 11, 0.95)' : 'rgba(255, 255, 255, 0.98)',
              borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
            },
          ]}
        >
          {!showTrendBack ? (
            <>
              {/* Front: Line Chart */}
              <View style={styles.trendHeader}>
                <View>
                  <Text style={[styles.trendTitle, { color: colors.textPrimary }]}>Trend Analysis</Text>
                  <Text style={[styles.trendSubtitle, { color: colors.textSecondary }]}>
                    {selectedFrequency === 'Month' ? 'This Month' : selectedFrequency === 'Quarter' ? 'This Quarter' : selectedFrequency === 'Year' ? 'This Year' : 'All Time'} · Tap for insights
                  </Text>
                </View>
                <TouchableOpacity 
                  style={[styles.trendFlipBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.04)' }]}
                  onPress={() => setShowTrendBack(true)}
                >
                  <MaterialCommunityIcons name="lightbulb-outline" size={16} color={Accent.amber} />
                  <Text style={[styles.trendFlipText, { color: Accent.amber }]}>Insights</Text>
                </TouchableOpacity>
              </View>

              {/* SVG Line Chart */}
              {(() => {
                const chartW = SCREEN_WIDTH - 72;
                const chartH = 160;
                const padL = 45, padR = 10, padT = 10, padB = 28;
                const drawW = chartW - padL - padR;
                const drawH = chartH - padT - padB;

                const points = trendData.length > 0 ? trendData : [{ label: '-', income: 0, expenses: 0, investments: 0 }];
                const allVals = points.flatMap((p: any) => [p.income, p.expenses, p.investments]);
                const maxVal = Math.max(...allVals, 1);

                const toX = (i: number) => padL + (points.length > 1 ? (i / (points.length - 1)) * drawW : drawW / 2);
                const toY = (v: number) => padT + drawH - (v / maxVal) * drawH;

                const makeLine = (key: string) => points.map((p: any, i: number) => `${toX(i)},${toY(p[key])}`).join(' ');
                const gridLines = [0, 0.25, 0.5, 0.75, 1].map(f => Math.round(maxVal * f));

                return (
                  <View style={{ marginTop: 4, marginBottom: 4 }}>
                    <Svg width={chartW} height={chartH}>
                      {/* Grid lines */}
                      {gridLines.map((val, i) => (
                        <G key={i}>
                          <Line x1={padL} y1={toY(val)} x2={chartW - padR} y2={toY(val)} stroke={isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'} strokeWidth={1} />
                          <SvgText x={padL - 4} y={toY(val) + 3} fill={isDark ? 'rgba(255,255,255,0.35)' : 'rgba(0,0,0,0.35)'} fontSize={9} textAnchor="end">
                            {val >= 1000 ? `${(val/1000).toFixed(0)}K` : `${val}`}
                          </SvgText>
                        </G>
                      ))}
                      {/* Income line */}
                      <Polyline points={makeLine('income')} fill="none" stroke={Accent.emerald} strokeWidth={2.5} strokeLinejoin="round" strokeLinecap="round" />
                      {/* Expenses line */}
                      <Polyline points={makeLine('expenses')} fill="none" stroke={Accent.ruby} strokeWidth={2.5} strokeLinejoin="round" strokeLinecap="round" />
                      {/* Investments line */}
                      <Polyline points={makeLine('investments')} fill="none" stroke={Accent.sapphire} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" strokeDasharray="4,3" />
                      {/* X-axis labels */}
                      {points.map((p: any, i: number) => (
                        <SvgText key={i} x={toX(i)} y={chartH - 4} fill={isDark ? 'rgba(255,255,255,0.45)' : 'rgba(0,0,0,0.45)'} fontSize={9} textAnchor="middle">
                          {p.label}
                        </SvgText>
                      ))}
                      {/* Data dots */}
                      {points.map((p: any, i: number) => (
                        <G key={`dots-${i}`}>
                          <Circle cx={toX(i)} cy={toY(p.income)} r={3} fill={Accent.emerald} />
                          <Circle cx={toX(i)} cy={toY(p.expenses)} r={3} fill={Accent.ruby} />
                          <Circle cx={toX(i)} cy={toY(p.investments)} r={2.5} fill={Accent.sapphire} />
                        </G>
                      ))}
                    </Svg>
                    {/* Legend */}
                    <View style={{ flexDirection: 'row', justifyContent: 'center', gap: 16, marginTop: 6 }}>
                      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                        <View style={{ width: 10, height: 3, borderRadius: 2, backgroundColor: Accent.emerald }} />
                        <Text style={{ fontSize: 10, color: colors.textSecondary }}>Income</Text>
                      </View>
                      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                        <View style={{ width: 10, height: 3, borderRadius: 2, backgroundColor: Accent.ruby }} />
                        <Text style={{ fontSize: 10, color: colors.textSecondary }}>Expenses</Text>
                      </View>
                      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                        <View style={{ width: 10, height: 3, borderRadius: 2, backgroundColor: Accent.sapphire, opacity: 0.7 }} />
                        <Text style={{ fontSize: 10, color: colors.textSecondary }}>Investments</Text>
                      </View>
                    </View>
                  </View>
                );
              })()}
            </>
          ) : (
            <>
              {/* Back: Smart Insights */}
              <View style={styles.trendHeader}>
                <View>
                  <Text style={[styles.trendTitle, { color: colors.textPrimary }]}>Smart Insights</Text>
                  <Text style={[styles.trendSubtitle, { color: colors.textSecondary }]}>
                    {selectedFrequency === 'Month' ? 'This Month' : selectedFrequency === 'Quarter' ? 'This Quarter' : selectedFrequency === 'Year' ? 'This Year' : 'All Time'}
                  </Text>
                </View>
                <TouchableOpacity 
                  style={[styles.trendFlipBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.04)' }]}
                  onPress={() => setShowTrendBack(false)}
                >
                  <MaterialCommunityIcons name="chart-bar" size={16} color={Accent.sapphire} />
                  <Text style={[styles.trendFlipText, { color: Accent.sapphire }]}>Summary</Text>
                </TouchableOpacity>
              </View>

              {trendInsights.length > 0 ? (
                <View style={styles.trendInsightsList}>
                  {trendInsights.slice(0, 4).map((insight: any, idx: number) => (
                    <View 
                      key={idx} 
                      style={[
                        styles.trendInsightItem, 
                        { 
                          backgroundColor: insight.type === 'success' 
                            ? isDark ? 'rgba(16, 185, 129, 0.08)' : 'rgba(16, 185, 129, 0.06)'
                            : insight.type === 'warning'
                            ? isDark ? 'rgba(245, 158, 11, 0.08)' : 'rgba(245, 158, 11, 0.06)'
                            : isDark ? 'rgba(59, 130, 246, 0.08)' : 'rgba(59, 130, 246, 0.06)',
                        }
                      ]}
                    >
                      <View style={[styles.trendInsightIcon, {
                        backgroundColor: insight.type === 'success' 
                          ? 'rgba(16, 185, 129, 0.15)'
                          : insight.type === 'warning'
                          ? 'rgba(245, 158, 11, 0.15)'
                          : 'rgba(59, 130, 246, 0.15)',
                      }]}>
                        <MaterialCommunityIcons 
                          name={insight.icon || 'information'} 
                          size={16} 
                          color={insight.type === 'success' ? Accent.emerald : insight.type === 'warning' ? Accent.amber : Accent.sapphire}
                        />
                      </View>
                      <View style={{ flex: 1 }}>
                        <Text style={[styles.trendInsightTitle, { color: colors.textPrimary }]}>{insight.title}</Text>
                        <Text style={[styles.trendInsightMsg, { color: colors.textSecondary }]} numberOfLines={2}>{insight.message}</Text>
                      </View>
                    </View>
                  ))}
                </View>
              ) : (
                <View style={styles.trendEmptyState}>
                  <MaterialCommunityIcons name="lightbulb-off-outline" size={32} color={colors.textSecondary} />
                  <Text style={[styles.trendEmptyText, { color: colors.textSecondary }]}>
                    Add more transactions to see personalized insights
                  </Text>
                </View>
              )}
            </>
          )}
        </TouchableOpacity>

        {/* ═══ RECENT TRANSACTIONS ═══ */}
        {stats && stats.recent_transactions.length > 0 && (
          <View
            style={[
              styles.glassCard,
              {
                backgroundColor: isDark ? 'rgba(10, 10, 11, 0.9)' : 'rgba(255, 255, 255, 0.85)',
                borderColor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)',
              },
            ]}
          >
            <View style={styles.cardHeader}>
              <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>
                Recent Transactions
              </Text>
              <TouchableOpacity onPress={() => router.push('/(tabs)/transactions')}>
                <Text style={[styles.viewAllLink, { color: colors.primary }]}>View All</Text>
              </TouchableOpacity>
            </View>
            {stats.recent_transactions.map((txn: any, index: number) => (
              <View
                key={txn.id}
                style={[
                  styles.txnRow,
                  {
                    borderBottomColor: colors.border,
                    borderBottomWidth: index < stats.recent_transactions.length - 1 ? 0.5 : 0,
                  },
                ]}
              >
                <View
                  style={[
                    styles.txnIconWrap,
                    {
                      backgroundColor:
                        txn.type === 'income'
                          ? isDark
                            ? '#064E3B'
                            : '#D1FAE5'
                          : txn.type === 'investment'
                          ? isDark
                            ? '#312E81'
                            : '#E0E7FF'
                          : isDark
                          ? '#7F1D1D'
                          : '#FEE2E2',
                    },
                  ]}
                >
                  <MaterialCommunityIcons
                    name={getCategoryIcon(txn.category)}
                    size={18}
                    color={
                      txn.type === 'income'
                        ? colors.income
                        : txn.type === 'investment'
                        ? colors.investment
                        : colors.expense
                    }
                  />
                </View>
                <View style={styles.txnInfo}>
                  <Text style={[styles.txnTitle, { color: colors.textPrimary }]} numberOfLines={1}>
                    {txn.description}
                  </Text>
                  <Text style={[styles.txnMeta, { color: colors.textSecondary }]}>
                    {txn.category} • {formatShortDate(txn.date)}
                  </Text>
                </View>
                <Text
                  style={[
                    styles.txnAmount,
                    {
                      color:
                        txn.type === 'income'
                          ? colors.income
                          : txn.type === 'investment'
                          ? colors.investment
                          : colors.expense,
                    },
                  ]}
                >
                  {txn.type === 'income' ? '+' : txn.type === 'investment' ? '' : '-'}
                  {formatINRShort(txn.amount)}
                </Text>
              </View>
            ))}
          </View>
        )}

        {/* ═══ FINANCIAL GOALS ═══ */}
        <View
          style={[
            styles.glassCard,
            {
              backgroundColor: isDark ? 'rgba(10, 10, 11, 0.9)' : 'rgba(255, 255, 255, 0.95)',
              borderColor: isDark ? '#1F2937' : '#E5E7EB',
            },
          ]}
        >
          <View style={styles.cardHeader}>
            <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>Financial Goals</Text>
            <TouchableOpacity onPress={() => router.push('/(tabs)/investments')}>
              <Text style={[styles.viewAllLink, { color: colors.primary }]}>+ Add Goal</Text>
            </TouchableOpacity>
          </View>

          {goals.length === 0 ? (
            <View style={styles.emptyGoals}>
              <MaterialCommunityIcons
                name="flag-variant-outline"
                size={48}
                color={colors.textSecondary}
              />
              <Text style={[styles.emptyTitle, { color: colors.textPrimary }]}>
                No financial goals yet
              </Text>
              <Text style={[styles.emptySubtitle, { color: colors.textSecondary }]}>
                Set goals to track your savings progress
              </Text>
              <TouchableOpacity
                style={[styles.emptyBtn, { backgroundColor: colors.primary }]}
                onPress={() => router.push('/(tabs)/investments')}
              >
                <Text style={styles.emptyBtnText}>Create Your First Goal</Text>
              </TouchableOpacity>
            </View>
          ) : (
            goals.map((goal) => {
              const progress = Math.min((goal.current_amount / goal.target_amount) * 100, 100);
              const remaining = goal.target_amount - goal.current_amount;
              return (
                <View
                  key={goal.id}
                  style={[
                    styles.goalCard,
                    {
                      backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
                    },
                  ]}
                >
                  <View style={styles.goalTop}>
                    <View
                      style={[
                        styles.goalIconWrap,
                        { backgroundColor: getCategoryColor(goal.category, isDark) + '20' },
                      ]}
                    >
                      <MaterialCommunityIcons
                        name={getCategoryIcon(goal.category)}
                        size={18}
                        color={getCategoryColor(goal.category, isDark)}
                      />
                    </View>
                    <View style={styles.goalInfo}>
                      <Text style={[styles.goalTitle, { color: colors.textPrimary }]}>
                        {goal.title}
                      </Text>
                      <Text style={[styles.goalCategory, { color: colors.textSecondary }]}>
                        {goal.category}
                      </Text>
                    </View>
                    <Text style={[styles.goalPercent, { color: colors.primary }]}>
                      {progress.toFixed(0)}%
                    </Text>
                  </View>
                  <View
                    style={[
                      styles.goalBarTrack,
                      { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' },
                    ]}
                  >
                    <View
                      style={[
                        styles.goalBarFill,
                        { width: `${progress}%`, backgroundColor: colors.primary },
                      ]}
                    />
                  </View>
                  <View style={styles.goalBottom}>
                    <Text style={[styles.goalAmounts, { color: colors.textSecondary }]}>
                      {formatINRShort(goal.current_amount)} / {formatINRShort(goal.target_amount)}
                    </Text>
                    <Text style={[styles.goalRemaining, { color: colors.textSecondary }]}>
                      {formatINRShort(remaining)} remaining
                    </Text>
                  </View>
                </View>
              );
            })
          )}
        </View>

        <View style={{ height: 140 }} />
      </ScrollView>

      {/* ═══ FLOATING ACTION BUTTON ═══ */}
      <FAB actions={fabActions} colors={colors} isDark={isDark} />

      {/* ═══ CUSTOM DATE RANGE MODAL ═══ */}
      <Modal visible={showDatePicker} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, { backgroundColor: colors.surface, paddingBottom: 30 }]}>
            <View style={styles.modalHandle} />
            <View style={styles.modalHeader}>
              <Text style={[styles.modalTitle, { color: colors.textPrimary }]}>
                Custom Date Range
              </Text>
              <TouchableOpacity data-testid="close-date-picker" onPress={() => { setShowDatePicker(false); setShowNativePicker(false); }}>
                <MaterialCommunityIcons name="close" size={24} color={colors.textSecondary} />
              </TouchableOpacity>
            </View>

            <Text style={{ fontSize: 12, color: colors.textSecondary, paddingHorizontal: 20, marginBottom: 16 }}>
              Tap a date to change it
            </Text>

            {/* FROM / TO Selectors */}
            <View style={{ flexDirection: 'row', paddingHorizontal: 20, gap: 12, marginBottom: 24 }}>
              <TouchableOpacity
                data-testid="custom-from-btn"
                style={[{
                  flex: 1, padding: 16, borderRadius: 14, borderWidth: 2,
                  borderColor: (showNativePicker && activePickerField === 'start') ? colors.primary : (colors.primary + '60'),
                  backgroundColor: colors.primary + '10',
                }]}
                onPress={() => openDatePicker('start')}
                activeOpacity={0.7}
              >
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <MaterialCommunityIcons name="calendar-start" size={16} color={colors.primary} />
                  <Text style={{ fontSize: 11, fontFamily: 'DM Sans', fontWeight: '700', color: colors.primary, textTransform: 'uppercase', letterSpacing: 0.5 }}>From</Text>
                </View>
                <Text style={{ fontSize: 18, fontFamily: 'DM Sans', fontWeight: '800', color: colors.textPrimary }}>
                  {customStartDate.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}
                </Text>
                <Text style={{ fontSize: 12, fontFamily: 'DM Sans', color: colors.textSecondary, marginTop: 2 }}>
                  {customStartDate.getFullYear()}
                </Text>
              </TouchableOpacity>

              <View style={{ justifyContent: 'center' }}>
                <MaterialCommunityIcons name="arrow-right" size={20} color={colors.textSecondary} />
              </View>

              <TouchableOpacity
                data-testid="custom-to-btn"
                style={[{
                  flex: 1, padding: 16, borderRadius: 14, borderWidth: 2,
                  borderColor: (showNativePicker && activePickerField === 'end') ? Accent.amber : (Accent.amber + '60'),
                  backgroundColor: Accent.amber + '10',
                }]}
                onPress={() => openDatePicker('end')}
                activeOpacity={0.7}
              >
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <MaterialCommunityIcons name="calendar-end" size={16} color={Accent.amber} />
                  <Text style={{ fontSize: 11, fontFamily: 'DM Sans', fontWeight: '700', color: Accent.amber, textTransform: 'uppercase', letterSpacing: 0.5 }}>To</Text>
                </View>
                <Text style={{ fontSize: 18, fontFamily: 'DM Sans', fontWeight: '800', color: colors.textPrimary }}>
                  {customEndDate.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}
                </Text>
                <Text style={{ fontSize: 12, fontFamily: 'DM Sans', color: colors.textSecondary, marginTop: 2 }}>
                  {customEndDate.getFullYear()}
                </Text>
              </TouchableOpacity>
            </View>

            {/* ═══ INLINE iOS DATE PICKER (shown inside this modal) ═══ */}
            {showNativePicker && Platform.OS === 'ios' && (
              <View style={{ borderTopWidth: 1, borderTopColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)', marginHorizontal: 20, paddingTop: 8 }}>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <Text style={{ fontSize: 13, color: colors.primary, fontFamily: 'DM Sans', fontWeight: '700' }}>
                    {activePickerField === 'start' ? 'Select From Date' : 'Select To Date'}
                  </Text>
                  <TouchableOpacity onPress={() => setShowNativePicker(false)} style={{ paddingHorizontal: 12, paddingVertical: 6, backgroundColor: colors.primary, borderRadius: 8 }}>
                    <Text style={{ fontSize: 13, color: '#fff', fontFamily: 'DM Sans', fontWeight: '700' }}>Done</Text>
                  </TouchableOpacity>
                </View>
                <DateTimePicker
                  value={activePickerField === 'start' ? customStartDate : customEndDate}
                  mode="date"
                  display="spinner"
                  themeVariant={isDark ? 'dark' : 'light'}
                  minimumDate={userCreatedAt ? new Date(userCreatedAt) : new Date(2020, 0, 1)}
                  maximumDate={new Date()}
                  onChange={(event: any, date?: Date) => {
                    if (date) {
                      if (activePickerField === 'start') setCustomStartDate(date);
                      else setCustomEndDate(date);
                    }
                  }}
                  style={{ height: 150 }}
                />
              </View>
            )}

            {/* Duration display */}
            {customStartDate <= customEndDate && !showNativePicker && (
              <View style={{ alignItems: 'center', marginBottom: 20 }}>
                <Text style={{ fontSize: 12, fontFamily: 'DM Sans', color: colors.textSecondary }}>
                  {Math.ceil((customEndDate.getTime() - customStartDate.getTime()) / (1000 * 60 * 60 * 24))} days selected
                </Text>
              </View>
            )}
            {customStartDate > customEndDate && !showNativePicker && (
              <View style={{ alignItems: 'center', marginBottom: 20, flexDirection: 'row', justifyContent: 'center', gap: 6 }}>
                <MaterialCommunityIcons name="alert-circle-outline" size={14} color="#EF4444" />
                <Text style={{ fontSize: 12, fontFamily: 'DM Sans', color: '#EF4444', fontWeight: '600' }}>
                  Start date must be before end date
                </Text>
              </View>
            )}

            {/* Apply Button */}
            {!showNativePicker && (
              <View style={{ paddingHorizontal: 20 }}>
                <TouchableOpacity
                  data-testid="apply-date-range-btn"
                  style={[styles.saveBtn, { backgroundColor: customStartDate <= customEndDate ? colors.primary : colors.border }]}
                  onPress={handleApplyCustomRange}
                  disabled={customStartDate > customEndDate}
                >
                  <MaterialCommunityIcons name="check" size={20} color="#FFF" />
                  <Text style={[styles.saveBtnText, { marginLeft: 8 }]}>Apply Date Range</Text>
                </TouchableOpacity>
              </View>
            )}
          </View>
        </View>
      </Modal>

      {/* ═══ NATIVE DATE PICKER (Android only - shows as dialog) ═══ */}
      {showNativePicker && Platform.OS === 'android' && (
        <DateTimePicker
          value={activePickerField === 'start' ? customStartDate : customEndDate}
          mode="date"
          display="default"
          minimumDate={userCreatedAt ? new Date(userCreatedAt) : new Date(2020, 0, 1)}
          maximumDate={new Date()}
          onChange={handleNativeDateChange}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  safe: { flex: 1 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },

  // Clean Header
  stickyHeader: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    zIndex: 100,
  },
  headerContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
  },
  headerLeft: {
    flex: 1,
  },
  greetingRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  greetingText: {
    fontSize: 17,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
  },
  greetingName: {
    fontSize: 17,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
  },
  monthYear: {
    fontSize: 12,
    fontFamily: 'DM Sans', fontWeight: '500' as any,
    marginTop: 2,
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  frequencyPills: {
    flexDirection: 'row',
    borderRadius: 10,
    padding: 3,
  },
  freqPill: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
  },
  freqText: {
    fontSize: 12,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
  },
  themeBtn: {
    width: 36,
    height: 36,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },

  // Scroll
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: 16,
    paddingBottom: 100,
  },

  // Health Score Card
  healthScoreCard: {
    borderRadius: 20,
    padding: 16,
    borderWidth: 2,
    marginBottom: 20,
  },
  scoreFlipBtn: {
    position: 'absolute',
    top: 12,
    right: 12,
    width: 28,
    height: 28,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 10,
  },
  healthScoreFront: {
    minHeight: 80,
  },
  scoreRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
  },
  scoreRingBox: {
    width: 90,
    height: 90,
    position: 'relative',
  },
  scoreCenter: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
  },
  scoreNum: {
    fontSize: 26,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
    letterSpacing: -1,
  },
  scoreOf: {
    fontSize: 11,
    fontFamily: 'DM Sans', fontWeight: '600' as any,
  },
  scoreInfo: {
    flex: 1,
    gap: 4,
  },
  scoreTitle: {
    fontSize: 15,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
  },
  scoreLabelBadge: {
    alignSelf: 'flex-start',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 10,
  },
  scoreLabelText: {
    fontSize: 11,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
  },
  scoreDesc: {
    fontSize: 12,
  },
  healthScoreBack: {
    minHeight: 80,
  },
  scoreBackTitle: {
    fontSize: 15,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
    marginBottom: 2,
  },
  scoreBackDesc: {
    fontSize: 11,
    marginBottom: 10,
  },
  scoreBreakdown: {
    borderRadius: 10,
    padding: 10,
  },
  breakdownRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 6,
  },
  breakdownLabel: {
    fontSize: 12,
  },
  breakdownValue: {
    fontSize: 12,
    fontFamily: 'DM Sans', fontWeight: '600' as any,
  },
  breakdownTotal: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 8,
    marginTop: 4,
    borderTopWidth: 1,
  },
  breakdownTotalLabel: {
    fontSize: 13,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
  },
  breakdownTotalValue: {
    fontSize: 16,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
  },

  // Section
  section: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
    letterSpacing: -0.3,
    marginBottom: 14,
  },

  // Cards Row
  cardsRow: {
    flexDirection: 'row',
    gap: 12,
    paddingRight: 16,
  },

  // Glass Card
  glassCard: {
    borderRadius: 24,
    padding: 20,
    borderWidth: 1,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 16,
    elevation: 5,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  cardTitle: {
    fontSize: 16,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
    letterSpacing: -0.3,
  },
  viewAllLink: {
    fontSize: 13,
    fontFamily: 'DM Sans', fontWeight: '600' as any,
  },

  // Pie Chart
  pieContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 20,
  },
  pieLegend: {
    flex: 1,
    gap: 8,
  },
  legendRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  legendDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  legendCat: {
    flex: 1,
    fontSize: 13,
    fontFamily: 'DM Sans', fontWeight: '500' as any,
  },
  legendAmt: {
    fontSize: 12,
    fontFamily: 'DM Sans', fontWeight: '600' as any,
  },

  // Transactions
  txnRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    gap: 12,
  },
  txnIconWrap: {
    width: 42,
    height: 42,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
  },
  txnInfo: {
    flex: 1,
  },
  txnTitle: {
    fontSize: 14,
    fontFamily: 'DM Sans', fontWeight: '600' as any,
  },
  txnMeta: {
    fontSize: 12,
    marginTop: 2,
  },
  txnAmount: {
    fontSize: 15,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
  },

  // Goals
  emptyGoals: {
    alignItems: 'center',
    paddingVertical: 32,
  },
  emptyTitle: {
    fontSize: 16,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
    marginTop: 12,
  },
  emptySubtitle: {
    fontSize: 13,
    marginTop: 4,
    textAlign: 'center',
  },
  emptyBtn: {
    marginTop: 16,
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 12,
  },
  emptyBtnText: {
    color: '#fff',
    fontSize: 14,
    fontFamily: 'DM Sans', fontWeight: '600' as any,
  },
  goalCard: {
    padding: 14,
    borderRadius: 14,
    marginBottom: 10,
  },
  goalTop: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  goalIconWrap: {
    width: 40,
    height: 40,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  goalInfo: {
    flex: 1,
  },
  goalTitle: {
    fontSize: 14,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
  },
  goalCategory: {
    fontSize: 12,
    marginTop: 2,
  },
  goalPercent: {
    fontSize: 16,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
  },
  goalBarTrack: {
    height: 4,
    borderRadius: 2,
    marginTop: 12,
    overflow: 'hidden',
  },
  goalBarFill: {
    height: '100%',
    borderRadius: 2,
  },
  goalBottom: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 8,
  },
  goalAmounts: {
    fontSize: 12,
    fontFamily: 'DM Sans', fontWeight: '500' as any,
  },
  goalRemaining: {
    fontSize: 12,
  },

  // Modal
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalKav: {
    maxHeight: '85%',
  },
  modalContent: {
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    padding: 24,
    paddingBottom: 40,
  },
  modalHandle: {
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: '#CBD5E1',
    alignSelf: 'center',
    marginBottom: 16,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  modalTitle: {
    fontSize: 20,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
  },
  typeRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 20,
  },
  typeTab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 12,
    borderRadius: 14,
    borderWidth: 1,
  },
  amountRow: {
    flexDirection: 'row',
    alignItems: 'center',
    height: 60,
    borderRadius: 16,
    borderWidth: 1,
    marginBottom: 16,
    paddingHorizontal: 16,
  },
  rupeeSymbol: {
    fontSize: 24,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
  },
  amountInput: {
    flex: 1,
    fontSize: 28,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
    paddingHorizontal: 8,
    height: '100%',
  },
  catScroll: {
    maxHeight: 40,
    marginBottom: 16,
  },
  catChip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 16,
    borderWidth: 1,
    marginRight: 8,
  },
  descInput: {
    height: 48,
    borderRadius: 14,
    borderWidth: 1,
    paddingHorizontal: 16,
    fontSize: 15,
    marginBottom: 16,
  },
  saveBtn: {
    height: 56,
    borderRadius: 999,
    justifyContent: 'center',
    alignItems: 'center',
  },
  saveBtnText: {
    color: '#fff',
    fontSize: 17,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
  },
  
  // Redesigned Trend Analysis card styles
  trendCard: {
    borderRadius: 20,
    padding: 16,
    borderWidth: 1,
    marginBottom: 16,
  },
  trendHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 16,
  },
  trendTitle: {
    fontSize: 18,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
    letterSpacing: -0.3,
  },
  trendSubtitle: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    marginTop: 2,
  },
  trendFlipBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 20,
  },
  trendFlipText: {
    fontSize: 12,
    fontFamily: 'DM Sans', fontWeight: '600' as any,
  },
  trendStatsRow: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 12,
  },
  trendStatBox: {
    flex: 1,
    alignItems: 'center',
    padding: 12,
    borderRadius: 14,
    gap: 4,
  },
  trendStatLabel: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    marginTop: 4,
  },
  trendStatValue: {
    fontSize: 15,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
  },
  trendSavingsBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 14,
    borderRadius: 14,
  },
  trendSavingsLabel: {
    fontSize: 12,
    fontFamily: 'DM Sans',
  },
  trendSavingsValue: {
    fontSize: 18,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
    marginTop: 2,
  },
  trendMetricRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderRadius: 12,
  },
  trendMetricLabel: {
    fontSize: 14,
    fontFamily: 'DM Sans', fontWeight: '500' as any,
  },
  trendMetricValue: {
    fontSize: 16,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
  },
  trendInsightsList: {
    gap: 8,
  },
  trendInsightItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    padding: 12,
    borderRadius: 12,
    gap: 10,
  },
  trendInsightIcon: {
    width: 32,
    height: 32,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  trendInsightTitle: {
    fontSize: 13,
    fontFamily: 'DM Sans', fontWeight: '600' as any,
    marginBottom: 2,
  },
  trendInsightMsg: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    lineHeight: 16,
  },
  trendEmptyState: {
    alignItems: 'center',
    paddingVertical: 24,
    gap: 10,
  },
  trendEmptyText: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    textAlign: 'center',
  },
  
  // Legacy styles kept for compatibility
  cardSubtitle: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    marginBottom: 4,
  },
  insightItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
  },
  insightTitle: {
    fontSize: 13,
    fontFamily: 'DM Sans', fontWeight: '600' as any,
    marginBottom: 2,
  },
  insightMessage: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    lineHeight: 16,
  },
  emptyText: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    textAlign: 'center',
  },

  // ── Credit Card Summary Card ──
  ccSummaryCard: {
    marginHorizontal: 20,
    marginBottom: 16,
    borderRadius: 16,
    borderWidth: 1,
    padding: 14,
  },

  // ── CC Section (always-visible dashboard block) ──
  ccSection: {
    marginHorizontal: 20,
    marginBottom: 16,
    padding: 16,
  },
  ccSectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 14,
  },
  ccSectionLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  ccSectionIcon: {
    width: 34,
    height: 34,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ccSectionTitle: {
    fontSize: 15,
    fontFamily: 'DM Sans',
    fontWeight: '700' as any,
  },
  ccManageRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
  },
  ccManageText: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    fontWeight: '600' as any,
    color: '#818CF8',
  },
  ccStatsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  ccStatItem: {
    flex: 1,
    alignItems: 'center',
  },
  ccStatDivider: {
    width: 1,
    height: 30,
  },
  ccStatLabel: {
    fontSize: 10,
    fontFamily: 'DM Sans',
    marginBottom: 3,
    textTransform: 'uppercase' as any,
    letterSpacing: 0.4,
  },
  ccStatAmount: {
    fontSize: 16,
    fontFamily: 'DM Sans',
    fontWeight: '700' as any,
  },
  ccUtilBar: {
    height: 4,
    borderRadius: 2,
    overflow: 'hidden',
    marginBottom: 8,
  },
  ccUtilFill: {
    height: '100%',
    borderRadius: 2,
  },
  ccCardCount: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    textAlign: 'right' as any,
  },
  ccEmptyState: {
    alignItems: 'center',
    paddingVertical: 8,
  },
  ccEmptyTitle: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    fontWeight: '600' as any,
    marginBottom: 4,
  },
  ccEmptySubtitle: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    textAlign: 'center' as any,
    lineHeight: 17,
  },
  ccSummaryHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 14,
  },
  ccSummaryLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  ccSummaryIconWrap: {
    width: 36,
    height: 36,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ccSummaryTitle: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    fontWeight: '700' as any,
  },
  ccSummarySubtitle: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    marginTop: 1,
  },
  ccSummaryStats: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  ccSummaryStat: {
    flex: 1,
    alignItems: 'center',
  },
  ccSummaryDivider: {
    width: 1,
    height: 32,
  },
  ccSummaryStatLabel: {
    fontSize: 10,
    fontFamily: 'DM Sans',
    marginBottom: 4,
  },
  ccSummaryStatValue: {
    fontSize: 15,
    fontFamily: 'DM Sans',
    fontWeight: '700' as any,
  },
  ccUtilizationBar: {
    height: 5,
    borderRadius: 3,
    overflow: 'hidden',
  },
  ccUtilizationFill: {
    height: '100%',
    borderRadius: 3,
  },
});
