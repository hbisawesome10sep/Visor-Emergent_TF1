import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, StyleSheet, RefreshControl, ActivityIndicator,
  TouchableOpacity, Dimensions, Modal, TextInput, Alert,
  KeyboardAvoidingView, Platform, StatusBar, Animated,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { BlurView } from 'expo-blur';
import { useRouter } from 'expo-router';

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

const { width: SCREEN_WIDTH } = Dimensions.get('window');

const EXPENSE_CATS = ['Rent', 'Groceries', 'Food', 'Transport', 'Shopping', 'Utilities', 'Entertainment', 'Health', 'EMI', 'Other'];
const INCOME_CATS = ['Salary', 'Freelance', 'Bonus', 'Interest', 'Dividend', 'Other'];
const INVEST_CATS = ['SIP', 'PPF', 'Stocks', 'Mutual Funds', 'FD', 'Gold', 'NPS', 'Other'];
const GOAL_CATS = ['Safety', 'Travel', 'Purchase', 'Property', 'Other'];

type FrequencyOption = 'Quarter' | 'Month' | 'Year';

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

export default function DashboardScreen() {
  const { user, token } = useAuth();
  const { colors, isDark, setThemeMode } = useTheme();
  const router = useRouter();

  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedFrequency, setSelectedFrequency] = useState<FrequencyOption>('Month');
  const [showTxnModal, setShowTxnModal] = useState(false);
  const [showGoalModal, setShowGoalModal] = useState(false);
  const [txnForm, setTxnForm] = useState({ type: 'expense', amount: '', category: '', description: '', date: '' });
  const [goalForm, setGoalForm] = useState({ title: '', target_amount: '', category: 'Safety' });
  const [saving, setSaving] = useState(false);

  const fetchData = useCallback(async () => {
    if (!token) return;
    try {
      const [s, g] = await Promise.all([
        apiRequest('/dashboard/stats', { token }),
        apiRequest('/goals', { token }),
      ]);
      setStats(s);
      setGoals(g);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchData();
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

  // Calculate values for liquid fill cards
  const incomeTarget = stats?.total_income || 1;
  const expensePercent = Math.min(((stats?.total_expenses || 0) / incomeTarget) * 100, 100);
  const savingsRate = stats?.savings_rate || 0;

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
  ];

  const cats = txnForm.type === 'income' ? INCOME_CATS : txnForm.type === 'investment' ? INVEST_CATS : EXPENSE_CATS;
  const frequencies: FrequencyOption[] = ['Quarter', 'Month', 'Year'];

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <StatusBar barStyle={isDark ? 'light-content' : 'dark-content'} />

      {/* Sticky Glass Header */}
      <View style={styles.stickyHeader}>
        <BlurView
          intensity={isDark ? 50 : 70}
          tint={isDark ? 'dark' : 'light'}
          style={[
            styles.headerBlur,
            {
              backgroundColor: isDark ? 'rgba(30, 41, 59, 0.7)' : 'rgba(255, 255, 255, 0.7)',
              borderBottomColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)',
            },
          ]}
        >
          <SafeAreaView edges={['top']} style={styles.headerSafeArea}>
            <View style={styles.headerContent}>
              <View style={styles.headerLeft}>
                <View style={styles.greetingRow}>
                  <LinearGradient
                    colors={['#3B82F6', '#6366F1']}
                    start={{ x: 0, y: 0 }}
                    end={{ x: 1, y: 0 }}
                    style={styles.gradientTextBg}
                  >
                    <Text style={styles.greetingGradient}>{getGreeting()}</Text>
                  </LinearGradient>
                  <Text style={[styles.greetingName, { color: colors.textPrimary }]}>
                    , {user?.full_name?.split(' ')[0] || 'User'}
                  </Text>
                </View>
                <Text style={[styles.monthYear, { color: colors.textSecondary }]}>
                  {getCurrentMonthYear()}
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
                      onPress={() => setSelectedFrequency(freq)}
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
                    color={isDark ? '#FBBF24' : '#6366F1'}
                  />
                </TouchableOpacity>
              </View>
            </View>
          </SafeAreaView>
        </BlurView>
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />
        }
        showsVerticalScrollIndicator={false}
      >
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
              gradient={['#10B981', '#059669']}
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
              gradient={['#F43F5E', '#E11D48']}
              icon="arrow-up-circle"
              onPress={() => router.push('/(tabs)/transactions')}
              colors={colors}
              isDark={isDark}
            />
            <LiquidFillCard
              title="Savings Rate"
              amount={`${savingsRate.toFixed(0)}%`}
              fillPercent={savingsRate}
              gradient={['#3B82F6', '#6366F1']}
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
                backgroundColor: isDark ? 'rgba(30, 41, 59, 0.8)' : 'rgba(255, 255, 255, 0.85)',
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
              backgroundColor: isDark ? 'rgba(30, 41, 59, 0.8)' : 'rgba(255, 255, 255, 0.85)',
              borderColor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)',
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
                backgroundColor: isDark ? 'rgba(30, 41, 59, 0.8)' : 'rgba(255, 255, 255, 0.85)',
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
              backgroundColor: isDark ? 'rgba(30, 41, 59, 0.8)' : 'rgba(255, 255, 255, 0.85)',
              borderColor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)',
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

        <View style={{ height: 120 }} />
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
                        fontWeight: '600',
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
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  safe: { flex: 1 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },

  // Sticky Header
  stickyHeader: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    zIndex: 100,
  },
  headerBlur: {
    borderBottomWidth: 1,
  },
  headerSafeArea: {
    paddingHorizontal: 16,
    paddingBottom: 12,
  },
  headerContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: Platform.OS === 'android' ? 8 : 0,
  },
  headerLeft: {
    flex: 1,
  },
  greetingRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  gradientTextBg: {
    borderRadius: 6,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  greetingGradient: {
    fontSize: 17,
    fontWeight: '700',
    color: '#fff',
  },
  greetingName: {
    fontSize: 17,
    fontWeight: '800',
  },
  monthYear: {
    fontSize: 13,
    fontWeight: '500',
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
    fontWeight: '700',
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
    paddingTop: Platform.OS === 'ios' ? 120 : 100,
    paddingHorizontal: 16,
  },

  // Section
  section: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
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
    fontSize: 17,
    fontWeight: '700',
  },
  viewAllLink: {
    fontSize: 14,
    fontWeight: '600',
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
    fontWeight: '500',
  },
  legendAmt: {
    fontSize: 12,
    fontWeight: '600',
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
    fontWeight: '600',
  },
  txnMeta: {
    fontSize: 12,
    marginTop: 2,
  },
  txnAmount: {
    fontSize: 15,
    fontWeight: '700',
  },

  // Goals
  emptyGoals: {
    alignItems: 'center',
    paddingVertical: 32,
  },
  emptyTitle: {
    fontSize: 16,
    fontWeight: '700',
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
    fontWeight: '600',
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
    fontWeight: '700',
  },
  goalCategory: {
    fontSize: 12,
    marginTop: 2,
  },
  goalPercent: {
    fontSize: 16,
    fontWeight: '800',
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
    fontWeight: '500',
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
    fontWeight: '700',
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
    fontWeight: '800',
  },
  amountInput: {
    flex: 1,
    fontSize: 28,
    fontWeight: '800',
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
    fontWeight: '700',
  },
});
