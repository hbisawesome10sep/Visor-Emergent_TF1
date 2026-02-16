import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, StyleSheet, RefreshControl, ActivityIndicator,
  TouchableOpacity, Dimensions, Modal, TextInput, Alert,
  KeyboardAvoidingView, Platform, StatusBar,
} from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { BlurView } from 'expo-blur';
import { useRouter } from 'expo-router';
import Svg, { Circle, G } from 'react-native-svg';
import DateTimePicker from '@react-native-community/datetimepicker';

import { useAuth } from '../../src/context/AuthContext';
import { useTheme } from '../../src/context/ThemeContext';
import { apiRequest } from '../../src/utils/api';
import {
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
import { Accent } from '../../src/utils/theme';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

const EXPENSE_CATS = ['Rent', 'Groceries', 'Food', 'Transport', 'Shopping', 'Utilities', 'Entertainment', 'Health', 'EMI', 'Other'];
const INCOME_CATS = ['Salary', 'Freelance', 'Bonus', 'Interest', 'Dividend', 'Other'];
const INVEST_CATS = ['SIP', 'PPF', 'Stocks', 'Mutual Funds', 'FD', 'Gold', 'NPS', 'Other'];
const GOAL_CATS = ['Safety', 'Travel', 'Purchase', 'Property', 'Other'];

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
  const { colors, isDark, setThemeMode } = useTheme();
  const router = useRouter();
  const insets = useSafeAreaInsets();

  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedFrequency, setSelectedFrequency] = useState<FrequencyOption>('Month');
  const [showTxnModal, setShowTxnModal] = useState(false);
  const [showGoalModal, setShowGoalModal] = useState(false);
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [txnForm, setTxnForm] = useState({ type: 'expense', amount: '', category: '', description: '', date: '' });
  const [goalForm, setGoalForm] = useState({ title: '', target_amount: '', category: 'Safety' });
  const [saving, setSaving] = useState(false);
  
  // Calculate header height dynamically based on safe area
  const HEADER_HEIGHT = 70 + insets.top;
  const [showScoreBack, setShowScoreBack] = useState(false);
  const [userCreatedAt, setUserCreatedAt] = useState<string>('');
  
  // Date range state
  const [dateRange, setDateRange] = useState({
    start: new Date(new Date().getFullYear(), new Date().getMonth(), 1),
    end: new Date(),
  });
  // Custom date range input state - Date objects for calendar picker
  const [customStartDate, setCustomStartDate] = useState(new Date(new Date().getFullYear(), 0, 1));
  const [customEndDate, setCustomEndDate] = useState(new Date());
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
      
      const startStr = startDate.toISOString().split('T')[0];
      const endStr = endDate.toISOString().split('T')[0];
      
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
    } catch (e) {
      console.error(e);
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

  const handleAddTxn = async () => {
    if (!txnForm.amount || !txnForm.category || !txnForm.description) {
      Alert.alert('Error', 'Please fill all fields');
      return;
    }
    setSaving(true);
    try {
      const today = new Date().toISOString().split('T')[0];
      await apiRequest('/transactions', {
        method: 'POST',
        token,
        body: { ...txnForm, amount: parseFloat(txnForm.amount), date: txnForm.date || today },
      });
      setShowTxnModal(false);
      setTxnForm({ type: 'expense', amount: '', category: '', description: '', date: '' });
      fetchData();
    } catch (e: any) {
      Alert.alert('Error', e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleAddGoal = async () => {
    if (!goalForm.title || !goalForm.target_amount) {
      Alert.alert('Error', 'Please fill all fields');
      return;
    }
    setSaving(true);
    try {
      const deadline = new Date();
      deadline.setMonth(deadline.getMonth() + 6);
      await apiRequest('/goals', {
        method: 'POST',
        token,
        body: {
          title: goalForm.title,
          target_amount: parseFloat(goalForm.target_amount),
          current_amount: 0,
          deadline: deadline.toISOString().split('T')[0],
          category: goalForm.category,
        },
      });
      setShowGoalModal(false);
      setGoalForm({ title: '', target_amount: '', category: 'Safety' });
      fetchData();
    } catch (e: any) {
      Alert.alert('Error', e.message);
    } finally {
      setSaving(false);
    }
  };

  const toggleTheme = () => {
    setThemeMode(isDark ? 'light' : 'dark');
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

  // Prepare trend data
  const trendData = [
    { label: 'Jan', income: stats?.monthly_income || 0, expenses: stats?.monthly_expenses || 0 },
    { label: 'Feb', income: (stats?.monthly_income || 0) * 0.9, expenses: (stats?.monthly_expenses || 0) * 1.1 },
  ];

  const fabActions = [
    {
      icon: 'cash-minus',
      label: 'Add Expense',
      color: colors.expense,
      onPress: () => {
        setTxnForm((p) => ({ ...p, type: 'expense' }));
        setShowTxnModal(true);
      },
    },
    {
      icon: 'cash-plus',
      label: 'Add Income',
      color: colors.income,
      onPress: () => {
        setTxnForm((p) => ({ ...p, type: 'income' }));
        setShowTxnModal(true);
      },
    },
    {
      icon: 'flag-variant',
      label: 'Add Goal',
      color: colors.investment,
      onPress: () => setShowGoalModal(true),
    },
    {
      icon: 'book-open-page-variant',
      label: 'Books & Reports',
      color: Accent.amethyst,
      onPress: () => router.push('/books'),
    },
  ];

  const cats = txnForm.type === 'income' ? INCOME_CATS : txnForm.type === 'investment' ? INVEST_CATS : EXPENSE_CATS;
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
              borderBottomColor: isDark ? '#18181B' : '#E4E4E7',
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

            {/* Theme Toggle */}
            <TouchableOpacity
              style={[
                styles.themeBtn,
                { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.06)' },
              ]}
              onPress={toggleTheme}
            >
              <MaterialCommunityIcons
                name={isDark ? 'weather-sunny' : 'weather-night'}
                size={18}
                color={isDark ? '#FBBF24' : Accent.amethyst}
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

        {/* ═══ FINANCIAL HEALTH SCORE CARD ═══ */}
        <TouchableOpacity
          activeOpacity={0.95}
          onPress={() => setShowScoreBack(!showScoreBack)}
          style={[styles.healthScoreCard, {
            backgroundColor: isDark ? 'rgba(16, 185, 129, 0.1)' : 'rgba(16, 185, 129, 0.08)',
            borderColor: isDark ? 'rgba(16, 185, 129, 0.3)' : 'rgba(16, 185, 129, 0.2)',
          }]}
        >
          {/* Flip icon */}
          <TouchableOpacity 
            style={[styles.scoreFlipBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)' }]}
            onPress={() => setShowScoreBack(!showScoreBack)}
          >
            <MaterialCommunityIcons 
              name={showScoreBack ? "rotate-left" : "information-outline"} 
              size={16} 
              color={colors.textSecondary} 
            />
          </TouchableOpacity>

          {!showScoreBack ? (
            <View style={styles.healthScoreFront}>
              <View style={styles.scoreRow}>
                {/* Score Ring */}
                <View style={styles.scoreRingBox}>
                  <Svg width={90} height={90}>
                    <G rotation="-90" origin="45, 45">
                      <Circle cx="45" cy="45" r="38" stroke={isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)'} strokeWidth="8" fill="transparent" />
                      <Circle cx="45" cy="45" r="38" stroke={scoreColor} strokeWidth="8" fill="transparent" strokeLinecap="round"
                        strokeDasharray={`${2 * Math.PI * 38}`}
                        strokeDashoffset={(1 - healthScore / 100) * 2 * Math.PI * 38}
                      />
                    </G>
                  </Svg>
                  <View style={styles.scoreCenter}>
                    <Text style={[styles.scoreNum, { color: scoreColor }]}>{healthScore}</Text>
                    <Text style={[styles.scoreOf, { color: colors.textSecondary }]}>/100</Text>
                  </View>
                </View>

                {/* Score Info */}
                <View style={styles.scoreInfo}>
                  <Text style={[styles.scoreTitle, { color: colors.textPrimary }]}>Financial Health Score</Text>
                  <View style={[styles.scoreLabelBadge, { backgroundColor: `${scoreInfo.color}20` }]}>
                    <Text style={[styles.scoreLabelText, { color: scoreInfo.color }]}>{scoreInfo.label}</Text>
                  </View>
                  <Text style={[styles.scoreDesc, { color: colors.textSecondary }]}>
                    {healthScore >= 70 ? "Great habits!" : healthScore >= 50 ? "Room to improve" : "Needs attention"}
                  </Text>
                </View>
              </View>
            </View>
          ) : (
            <View style={styles.healthScoreBack}>
              <Text style={[styles.scoreBackTitle, { color: colors.textPrimary }]}>Score Breakdown</Text>
              <Text style={[styles.scoreBackDesc, { color: colors.textSecondary }]}>Based on RBI guidelines</Text>
              
              <View style={[styles.scoreBreakdown, { backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)' }]}>
                <View style={styles.breakdownRow}>
                  <Text style={[styles.breakdownLabel, { color: colors.textSecondary }]}>Savings</Text>
                  <Text style={[styles.breakdownValue, { color: colors.textPrimary }]}>{Math.round(breakdown.savings)}/100</Text>
                </View>
                <View style={styles.breakdownRow}>
                  <Text style={[styles.breakdownLabel, { color: colors.textSecondary }]}>Spending</Text>
                  <Text style={[styles.breakdownValue, { color: colors.textPrimary }]}>{Math.round(breakdown.spending)}/100</Text>
                </View>
                <View style={styles.breakdownRow}>
                  <Text style={[styles.breakdownLabel, { color: colors.textSecondary }]}>Investments</Text>
                  <Text style={[styles.breakdownValue, { color: colors.textPrimary }]}>{Math.round(breakdown.investments)}/100</Text>
                </View>
                <View style={styles.breakdownRow}>
                  <Text style={[styles.breakdownLabel, { color: colors.textSecondary }]}>Goals</Text>
                  <Text style={[styles.breakdownValue, { color: colors.textPrimary }]}>{Math.round(breakdown.goals)}/100</Text>
                </View>
                <View style={[styles.breakdownTotal, { borderTopColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)' }]}>
                  <Text style={[styles.breakdownTotalLabel, { color: colors.textPrimary }]}>Total</Text>
                  <Text style={[styles.breakdownTotalValue, { color: scoreColor }]}>{healthScore}/100</Text>
                </View>
              </View>
            </View>
          )}
        </TouchableOpacity>

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
              gradient={[Accent.emerald, Accent.teal]}
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
              gradient={[Accent.ruby, Accent.amber]}
              icon="arrow-up-circle"
              onPress={() => router.push('/(tabs)/transactions')}
              colors={colors}
              isDark={isDark}
            />
            <LiquidFillCard
              title="Savings Rate"
              amount={`${savingsRate.toFixed(0)}%`}
              fillPercent={savingsRate}
              gradient={[Accent.sapphire, Accent.amethyst]}
              icon="piggy-bank"
              colors={colors}
              isDark={isDark}
            />
          </ScrollView>
        </View>

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

        {/* ═══ TREND ANALYSIS ═══ */}
        <View
          style={[
            styles.glassCard,
            {
              backgroundColor: isDark ? 'rgba(10, 10, 11, 0.9)' : 'rgba(255, 255, 255, 0.95)',
              borderColor: isDark ? '#27272A' : '#E4E4E7',
            },
          ]}
        >
          <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>Trend Analysis</Text>
          <TrendChart data={trendData} colors={colors} isDark={isDark} />
        </View>

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
              borderColor: isDark ? '#27272A' : '#E4E4E7',
            },
          ]}
        >
          <View style={styles.cardHeader}>
            <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>Financial Goals</Text>
            <TouchableOpacity onPress={() => setShowGoalModal(true)}>
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
                onPress={() => setShowGoalModal(true)}
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

      {/* ═══ QUICK ADD TRANSACTION MODAL ═══ */}
      <Modal visible={showTxnModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <KeyboardAvoidingView
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
            style={styles.modalKav}
          >
            <View style={[styles.modalContent, { backgroundColor: colors.surface }]}>
              <View style={styles.modalHandle} />
              <View style={styles.modalHeader}>
                <Text style={[styles.modalTitle, { color: colors.textPrimary }]}>
                  Quick Add {txnForm.type.charAt(0).toUpperCase() + txnForm.type.slice(1)}
                </Text>
                <TouchableOpacity onPress={() => setShowTxnModal(false)}>
                  <MaterialCommunityIcons name="close" size={24} color={colors.textSecondary} />
                </TouchableOpacity>
              </View>

              {/* Type Tabs */}
              <View style={styles.typeRow}>
                {(['expense', 'income', 'investment'] as const).map((t) => (
                  <TouchableOpacity
                    key={t}
                    style={[
                      styles.typeTab,
                      {
                        backgroundColor:
                          txnForm.type === t
                            ? t === 'income'
                              ? colors.income
                              : t === 'investment'
                              ? colors.investment
                              : colors.expense
                            : colors.background,
                        borderColor: colors.border,
                      },
                    ]}
                    onPress={() => setTxnForm((p) => ({ ...p, type: t, category: '' }))}
                  >
                    <MaterialCommunityIcons
                      name={t === 'income' ? 'arrow-down' : t === 'investment' ? 'chart-line' : 'arrow-up'}
                      size={16}
                      color={txnForm.type === t ? '#fff' : colors.textSecondary}
                    />
                    <Text
                      style={{
                        fontSize: 13,
                        fontFamily: 'DM Sans', fontWeight: '600' as any,
                        color: txnForm.type === t ? '#fff' : colors.textSecondary,
                      }}
                    >
                      {t.charAt(0).toUpperCase() + t.slice(1)}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>

              {/* Amount */}
              <View
                style={[
                  styles.amountRow,
                  { borderColor: colors.border, backgroundColor: colors.background },
                ]}
              >
                <Text style={[styles.rupeeSymbol, { color: colors.primary }]}>₹</Text>
                <TextInput
                  style={[styles.amountInput, { color: colors.textPrimary }]}
                  value={txnForm.amount}
                  onChangeText={(v) => setTxnForm((p) => ({ ...p, amount: v }))}
                  placeholder="0"
                  placeholderTextColor={colors.textSecondary}
                  keyboardType="decimal-pad"
                />
              </View>

              {/* Categories */}
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.catScroll}>
                {cats.map((c) => (
                  <TouchableOpacity
                    key={c}
                    style={[
                      styles.catChip,
                      {
                        backgroundColor: txnForm.category === c ? colors.primary : colors.background,
                        borderColor: txnForm.category === c ? colors.primary : colors.border,
                      },
                    ]}
                    onPress={() => setTxnForm((p) => ({ ...p, category: c }))}
                  >
                    <Text
                      style={{
                        color: txnForm.category === c ? '#fff' : colors.textSecondary,
                        fontSize: 13,
                      }}
                    >
                      {c}
                    </Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>

              {/* Description */}
              <TextInput
                style={[
                  styles.descInput,
                  {
                    borderColor: colors.border,
                    backgroundColor: colors.background,
                    color: colors.textPrimary,
                  },
                ]}
                value={txnForm.description}
                onChangeText={(v) => setTxnForm((p) => ({ ...p, description: v }))}
                placeholder="What was this for?"
                placeholderTextColor={colors.textSecondary}
              />

              <TouchableOpacity
                style={[styles.saveBtn, { backgroundColor: colors.primary }]}
                onPress={handleAddTxn}
                disabled={saving}
              >
                {saving ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.saveBtnText}>
                    Add {txnForm.type.charAt(0).toUpperCase() + txnForm.type.slice(1)}
                  </Text>
                )}
              </TouchableOpacity>
            </View>
          </KeyboardAvoidingView>
        </View>
      </Modal>

      {/* ═══ ADD GOAL MODAL ═══ */}
      <Modal visible={showGoalModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <KeyboardAvoidingView
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
            style={styles.modalKav}
          >
            <View style={[styles.modalContent, { backgroundColor: colors.surface }]}>
              <View style={styles.modalHandle} />
              <View style={styles.modalHeader}>
                <Text style={[styles.modalTitle, { color: colors.textPrimary }]}>
                  Create New Goal
                </Text>
                <TouchableOpacity onPress={() => setShowGoalModal(false)}>
                  <MaterialCommunityIcons name="close" size={24} color={colors.textSecondary} />
                </TouchableOpacity>
              </View>

              {/* Goal Title */}
              <TextInput
                style={[
                  styles.descInput,
                  {
                    borderColor: colors.border,
                    backgroundColor: colors.background,
                    color: colors.textPrimary,
                    marginBottom: 12,
                  },
                ]}
                value={goalForm.title}
                onChangeText={(v) => setGoalForm((p) => ({ ...p, title: v }))}
                placeholder="Goal name (e.g., Emergency Fund)"
                placeholderTextColor={colors.textSecondary}
              />

              {/* Target Amount */}
              <View
                style={[
                  styles.amountRow,
                  { borderColor: colors.border, backgroundColor: colors.background },
                ]}
              >
                <Text style={[styles.rupeeSymbol, { color: colors.primary }]}>₹</Text>
                <TextInput
                  style={[styles.amountInput, { color: colors.textPrimary }]}
                  value={goalForm.target_amount}
                  onChangeText={(v) => setGoalForm((p) => ({ ...p, target_amount: v }))}
                  placeholder="Target amount"
                  placeholderTextColor={colors.textSecondary}
                  keyboardType="decimal-pad"
                />
              </View>

              {/* Categories */}
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.catScroll}>
                {GOAL_CATS.map((c) => (
                  <TouchableOpacity
                    key={c}
                    style={[
                      styles.catChip,
                      {
                        backgroundColor: goalForm.category === c ? colors.primary : colors.background,
                        borderColor: goalForm.category === c ? colors.primary : colors.border,
                      },
                    ]}
                    onPress={() => setGoalForm((p) => ({ ...p, category: c }))}
                  >
                    <Text
                      style={{
                        color: goalForm.category === c ? '#fff' : colors.textSecondary,
                        fontSize: 13,
                      }}
                    >
                      {c}
                    </Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>

              <TouchableOpacity
                style={[styles.saveBtn, { backgroundColor: colors.primary }]}
                onPress={handleAddGoal}
                disabled={saving}
              >
                {saving ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.saveBtnText}>Create Goal</Text>
                )}
              </TouchableOpacity>
            </View>
          </KeyboardAvoidingView>
        </View>
      </Modal>

      {/* ═══ CUSTOM DATE RANGE MODAL with Calendar Picker ═══ */}
      <Modal visible={showDatePicker} animationType="fade" transparent>
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, { backgroundColor: colors.surface, paddingBottom: 30 }]}>
            <View style={styles.modalHandle} />
            <View style={styles.modalHeader}>
              <Text style={[styles.modalTitle, { color: colors.textPrimary }]}>
                Custom Date Range
              </Text>
              <TouchableOpacity onPress={() => setShowDatePicker(false)}>
                <MaterialCommunityIcons name="close" size={24} color={colors.textSecondary} />
              </TouchableOpacity>
            </View>

            {userCreatedAt ? (
              <Text style={{ fontSize: 12, color: colors.textSecondary, paddingHorizontal: 20, marginBottom: 12 }}>
                Account created: {new Date(userCreatedAt).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
              </Text>
            ) : null}

            {/* Date Field Selectors */}
            <View style={{ flexDirection: 'row', paddingHorizontal: 20, gap: 12, marginBottom: 16 }}>
              <TouchableOpacity
                style={[{
                  flex: 1, padding: 14, borderRadius: 12, borderWidth: 2,
                  borderColor: activePickerField === 'start' ? colors.primary : colors.border,
                  backgroundColor: activePickerField === 'start' ? (colors.primary + '10') : colors.background,
                }]}
                onPress={() => setActivePickerField('start')}
              >
                <Text style={{ fontSize: 11, fontFamily: 'DM Sans', fontWeight: '600' as any, color: colors.textSecondary, marginBottom: 4 }}>FROM</Text>
                <Text style={{ fontSize: 16, fontFamily: 'DM Sans', fontWeight: '700' as any, color: colors.textPrimary }}>
                  {customStartDate.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
                </Text>
              </TouchableOpacity>
              
              <View style={{ justifyContent: 'center' }}>
                <MaterialCommunityIcons name="arrow-right" size={20} color={colors.textSecondary} />
              </View>
              
              <TouchableOpacity
                style={[{
                  flex: 1, padding: 14, borderRadius: 12, borderWidth: 2,
                  borderColor: activePickerField === 'end' ? colors.primary : colors.border,
                  backgroundColor: activePickerField === 'end' ? (colors.primary + '10') : colors.background,
                }]}
                onPress={() => setActivePickerField('end')}
              >
                <Text style={{ fontSize: 11, fontFamily: 'DM Sans', fontWeight: '600' as any, color: colors.textSecondary, marginBottom: 4 }}>TO</Text>
                <Text style={{ fontSize: 16, fontFamily: 'DM Sans', fontWeight: '700' as any, color: colors.textPrimary }}>
                  {customEndDate.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
                </Text>
              </TouchableOpacity>
            </View>

            {/* Calendar DateTimePicker */}
            <View style={{ alignItems: 'center', marginBottom: 16, backgroundColor: isDark ? colors.background : '#F8FAFC', marginHorizontal: 20, borderRadius: 12, padding: 8 }}>
              <DateTimePicker
                value={activePickerField === 'start' ? customStartDate : customEndDate}
                mode="date"
                display="spinner"
                minimumDate={userCreatedAt ? new Date(userCreatedAt) : new Date(2020, 0, 1)}
                maximumDate={new Date()}
                onChange={(event: any, date?: Date) => {
                  if (date) {
                    if (activePickerField === 'start') {
                      setCustomStartDate(date);
                    } else {
                      setCustomEndDate(date);
                    }
                  }
                }}
                themeVariant={isDark ? 'dark' : 'light'}
                style={{ width: '100%', height: 150 }}
              />
            </View>

            <View style={{ paddingHorizontal: 20 }}>
              <TouchableOpacity
                style={[styles.saveBtn, { backgroundColor: colors.primary }]}
                onPress={handleApplyCustomRange}
              >
                <MaterialCommunityIcons name="check" size={20} color="#FFF" />
                <Text style={[styles.saveBtnText, { marginLeft: 8 }]}>Apply Date Range</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
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
});
