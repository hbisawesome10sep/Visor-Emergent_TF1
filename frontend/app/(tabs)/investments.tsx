import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, RefreshControl,
  ActivityIndicator, Dimensions, Platform, StatusBar, Animated, Modal,
  TextInput, KeyboardAvoidingView, Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import { LinearGradient } from 'expo-linear-gradient';
import Svg, { Circle, G, Path, Defs, LinearGradient as SvgLinearGradient, Stop } from 'react-native-svg';
import { useAuth } from '../../src/context/AuthContext';
import { useTheme } from '../../src/context/ThemeContext';
import { apiRequest } from '../../src/utils/api';
import { formatINRShort, getCategoryColor, getCategoryIcon } from '../../src/utils/formatters';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// Goal categories
const GOAL_CATS = ['Safety', 'Travel', 'Purchase', 'Property', 'Education', 'Retirement', 'Wedding', 'Other'];

// Investment categories
const INVEST_CATEGORIES = [
  { key: 'stocks', name: 'Stocks', color: '#3B82F6', icon: 'chart-areaspline' },
  { key: 'mutual_funds', name: 'Mutual Funds', color: '#8B5CF6', icon: 'chart-pie' },
  { key: 'fd', name: 'Fixed Deposits', color: '#10B981', icon: 'bank' },
  { key: 'ppf', name: 'PPF', color: '#14B8A6', icon: 'shield-check' },
  { key: 'gold', name: 'Gold', color: '#F59E0B', icon: 'diamond-stone' },
  { key: 'nps', name: 'NPS', color: '#6366F1', icon: 'account-cash' },
];

// Risk assessment questions
const RISK_QUESTIONS = [
  {
    question: 'What is your investment time horizon?',
    options: [
      { label: 'Short (1-3 years)', value: 1 },
      { label: 'Medium (3-7 years)', value: 2 },
      { label: 'Long (7+ years)', value: 3 },
    ],
  },
  {
    question: 'How would you react if your portfolio dropped 20%?',
    options: [
      { label: 'Sell everything', value: 1 },
      { label: 'Sell some', value: 2 },
      { label: 'Hold and wait', value: 3 },
      { label: 'Buy more', value: 4 },
    ],
  },
  {
    question: 'What percentage of income can you invest?',
    options: [
      { label: 'Less than 10%', value: 1 },
      { label: '10-20%', value: 2 },
      { label: '20-30%', value: 3 },
      { label: 'More than 30%', value: 4 },
    ],
  },
];

// Market indices
const MARKET_INDICES = [
  { name: 'Nifty 50', value: 22456.80, change: 1.23, up: true },
  { name: 'Sensex', value: 73890.45, change: 1.18, up: true },
  { name: 'Nifty Bank', value: 47234.65, change: -0.34, up: false },
  { name: 'Gold (10g)', value: 62450, change: 0.56, up: true },
];

type Goal = {
  id: string; title: string; target_amount: number; current_amount: number;
  deadline: string; category: string;
};

type DashboardStats = {
  total_income: number;
  total_expenses: number;
  total_investments: number;
  invest_breakdown: Record<string, number>;
};

export default function InvestmentsScreen() {
  const { token } = useAuth();
  const { colors, isDark } = useTheme();

  const [stats, setStats] = useState<DashboardStats | null>(null);
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

  const fadeAnim = useRef(new Animated.Value(0)).current;

  const fetchData = useCallback(async () => {
    if (!token) return;
    try {
      const [statsData, goalsData] = await Promise.all([
        apiRequest('/dashboard/stats', { token }),
        apiRequest('/goals', { token }),
      ]);
      setStats(statsData);
      setGoals(goalsData);
      Animated.timing(fadeAnim, { toValue: 1, duration: 500, useNativeDriver: true }).start();
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

  // Goal handlers
  const openAddGoal = () => {
    setEditGoal(null);
    setGoalForm({ title: '', target_amount: '', current_amount: '0', deadline: '', category: 'Safety' });
    setShowGoalModal(true);
  };

  const openEditGoal = (g: Goal) => {
    setEditGoal(g);
    setGoalForm({
      title: g.title,
      target_amount: g.target_amount.toString(),
      current_amount: g.current_amount.toString(),
      deadline: g.deadline,
      category: g.category,
    });
    setShowGoalModal(true);
  };

  const handleSaveGoal = async () => {
    if (!goalForm.title || !goalForm.target_amount || !goalForm.category) {
      Alert.alert('Error', 'Please fill required fields');
      return;
    }
    setSaving(true);
    try {
      const body = {
        title: goalForm.title,
        target_amount: parseFloat(goalForm.target_amount),
        current_amount: parseFloat(goalForm.current_amount || '0'),
        deadline: goalForm.deadline || '2026-12-31',
        category: goalForm.category,
      };
      if (editGoal) {
        await apiRequest(`/goals/${editGoal.id}`, { method: 'PUT', token, body });
      } else {
        await apiRequest('/goals', { method: 'POST', token, body });
      }
      setShowGoalModal(false);
      fetchData();
    } catch (e: any) {
      Alert.alert('Error', e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteGoal = (id: string, title: string) => {
    Alert.alert('Delete Goal', `Delete "${title}"?`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          await apiRequest(`/goals/${id}`, { method: 'DELETE', token });
          fetchData();
        },
      },
    ]);
  };

  // Risk assessment
  const handleRiskAnswer = (value: number) => {
    const newAnswers = [...riskAnswers, value];
    setRiskAnswers(newAnswers);
    if (riskStep < RISK_QUESTIONS.length - 1) {
      setRiskStep(riskStep + 1);
    } else {
      const total = newAnswers.reduce((s, a) => s + a, 0);
      const avg = total / newAnswers.length;
      const profile = avg <= 1.5 ? 'Conservative' : avg <= 2.8 ? 'Moderate' : 'Aggressive';
      setRiskProfile(profile);
      setShowRiskModal(false);
      setRiskStep(0);
      setRiskAnswers([]);
    }
  };

  // Calculations
  const totalInvested = stats?.total_investments || 0;
  const returns = Math.round(totalInvested * 0.127);
  const portfolioValue = totalInvested + returns;
  const xirr = 14.2;
  const monthlyChange = Math.round(portfolioValue * 0.0399);

  // Goals summary
  const totalGoalTarget = goals.reduce((s, g) => s + g.target_amount, 0);
  const totalGoalCurrent = goals.reduce((s, g) => s + g.current_amount, 0);
  const overallGoalProgress = totalGoalTarget > 0 ? (totalGoalCurrent / totalGoalTarget) * 100 : 0;

  // Asset allocation
  const allocation = stats?.invest_breakdown || {};
  const allocationData = INVEST_CATEGORIES.map(cat => ({
    ...cat,
    amount: allocation[cat.name] || allocation[cat.key] || 0,
  })).filter(a => a.amount > 0);

  const mockAllocation = allocationData.length === 0 ? [
    { ...INVEST_CATEGORIES[0], amount: totalInvested * 0.30 },
    { ...INVEST_CATEGORIES[1], amount: totalInvested * 0.35 },
    { ...INVEST_CATEGORIES[2], amount: totalInvested * 0.15 },
    { ...INVEST_CATEGORIES[3], amount: totalInvested * 0.10 },
    { ...INVEST_CATEGORIES[4], amount: totalInvested * 0.10 },
  ] : allocationData;

  const totalAllocation = mockAllocation.reduce((s, a) => s + a.amount, 0) || 1;

  // Strategy based on risk
  const strategies = {
    Conservative: { name: 'Safe Harbor', allocation: [{ name: 'Debt', p: 60, c: '#10B981' }, { name: 'Equity', p: 25, c: '#3B82F6' }, { name: 'Gold', p: 15, c: '#F59E0B' }] },
    Moderate: { name: 'Balanced Growth', allocation: [{ name: 'Equity', p: 40, c: '#3B82F6' }, { name: 'Debt', p: 30, c: '#10B981' }, { name: 'Gold', p: 15, c: '#F59E0B' }, { name: 'Alt', p: 15, c: '#8B5CF6' }] },
    Aggressive: { name: 'High Growth', allocation: [{ name: 'Equity', p: 70, c: '#3B82F6' }, { name: 'Alt', p: 15, c: '#8B5CF6' }, { name: 'Debt', p: 10, c: '#10B981' }, { name: 'Gold', p: 5, c: '#F59E0B' }] },
  };
  const currentStrategy = strategies[riskProfile];

  // Tax saving
  const section80CUsed = Math.min(totalInvested * 0.4, 150000);

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: colors.background }]}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#F97316" />
          <Text style={[styles.loadingText, { color: colors.textSecondary }]}>Loading...</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <StatusBar barStyle={isDark ? 'light-content' : 'dark-content'} />

      {/* ═══ HEADER ═══ */}
      <View style={styles.stickyHeader}>
        <BlurView
          intensity={isDark ? 50 : 70}
          tint={isDark ? 'dark' : 'light'}
          style={[styles.headerBlur, {
            backgroundColor: isDark ? 'rgba(30, 41, 59, 0.75)' : 'rgba(255, 255, 255, 0.75)',
            borderBottomColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)',
          }]}
        >
          <SafeAreaView edges={['top']} style={styles.headerSafeArea}>
            <View style={styles.headerContent}>
              <View style={styles.headerLeft}>
                <LinearGradient colors={['#EA580C', '#DC2626']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.gradientTitleBg}>
                  <Text style={styles.gradientTitle}>Investments</Text>
                </LinearGradient>
                <Text style={[styles.headerSubtitle, { color: colors.textSecondary }]}>Goals & Portfolio Management</Text>
              </View>
              <TouchableOpacity style={[styles.refreshBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)' }]} onPress={onRefresh}>
                <MaterialCommunityIcons name="refresh" size={20} color="#F97316" />
              </TouchableOpacity>
            </View>
          </SafeAreaView>
        </BlurView>
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#F97316" />}
        showsVerticalScrollIndicator={false}
      >
        {/* ═══ FINANCIAL GOALS SECTION ═══ */}
        <View style={styles.sectionHeader}>
          <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Financial Goals</Text>
          <TouchableOpacity style={[styles.addGoalBtn, { backgroundColor: '#F97316' }]} onPress={openAddGoal}>
            <MaterialCommunityIcons name="plus" size={18} color="#fff" />
            <Text style={styles.addGoalText}>Add Goal</Text>
          </TouchableOpacity>
        </View>

        {/* Goals Overview Card */}
        {goals.length > 0 && (
          <View style={[styles.goalsOverviewCard, {
            backgroundColor: isDark ? 'rgba(249, 115, 22, 0.1)' : 'rgba(249, 115, 22, 0.06)',
            borderColor: isDark ? 'rgba(249, 115, 22, 0.2)' : 'rgba(249, 115, 22, 0.15)',
          }]}>
            <View style={styles.goalsOverviewRow}>
              <View>
                <Text style={[styles.goalsOverviewLabel, { color: colors.textSecondary }]}>Total Goal Progress</Text>
                <Text style={[styles.goalsOverviewAmount, { color: colors.textPrimary }]}>
                  {formatINRShort(totalGoalCurrent)} / {formatINRShort(totalGoalTarget)}
                </Text>
              </View>
              <View style={[styles.goalsPercentBadge, { backgroundColor: overallGoalProgress >= 50 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(249, 115, 22, 0.15)' }]}>
                <Text style={[styles.goalsPercentText, { color: overallGoalProgress >= 50 ? '#10B981' : '#F97316' }]}>
                  {overallGoalProgress.toFixed(0)}%
                </Text>
              </View>
            </View>
            <View style={[styles.goalsProgressBar, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)' }]}>
              <View style={[styles.goalsProgressFill, { width: `${Math.min(overallGoalProgress, 100)}%`, backgroundColor: '#F97316' }]} />
            </View>
          </View>
        )}

        {/* Goals List */}
        {goals.length === 0 ? (
          <View style={[styles.emptyGoals, {
            backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
            borderColor: colors.border,
          }]}>
            <MaterialCommunityIcons name="flag-variant-outline" size={40} color={colors.textSecondary} />
            <Text style={[styles.emptyGoalsTitle, { color: colors.textPrimary }]}>No goals yet</Text>
            <Text style={[styles.emptyGoalsSubtitle, { color: colors.textSecondary }]}>Set financial goals to track progress</Text>
          </View>
        ) : (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.goalsScroll}>
            {goals.map(goal => {
              const progress = goal.target_amount > 0 ? (goal.current_amount / goal.target_amount) * 100 : 0;
              const progressColor = progress >= 75 ? '#10B981' : progress >= 40 ? '#F59E0B' : '#EF4444';
              return (
                <TouchableOpacity
                  key={goal.id}
                  style={[styles.goalCard, {
                    backgroundColor: isDark ? 'rgba(30, 41, 59, 0.7)' : 'rgba(255, 255, 255, 0.9)',
                    borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
                  }]}
                  onPress={() => openEditGoal(goal)}
                  onLongPress={() => handleDeleteGoal(goal.id, goal.title)}
                >
                  <View style={styles.goalCardHeader}>
                    <View style={[styles.goalIconWrap, { backgroundColor: `${getCategoryColor(goal.category, isDark)}20` }]}>
                      <MaterialCommunityIcons name={getCategoryIcon(goal.category) as any} size={18} color={getCategoryColor(goal.category, isDark)} />
                    </View>
                    <Text style={[styles.goalPercent, { color: progressColor }]}>{progress.toFixed(0)}%</Text>
                  </View>
                  <Text style={[styles.goalTitle, { color: colors.textPrimary }]} numberOfLines={1}>{goal.title}</Text>
                  <Text style={[styles.goalCategory, { color: colors.textSecondary }]}>{goal.category}</Text>
                  <View style={[styles.goalBarBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)' }]}>
                    <View style={[styles.goalBarFill, { width: `${Math.min(progress, 100)}%`, backgroundColor: progressColor }]} />
                  </View>
                  <Text style={[styles.goalAmounts, { color: colors.textSecondary }]}>
                    {formatINRShort(goal.current_amount)} / {formatINRShort(goal.target_amount)}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </ScrollView>
        )}

        {/* ═══ PORTFOLIO SUMMARY ═══ */}
        <Text style={[styles.sectionTitle, { color: colors.textPrimary, marginTop: 24 }]}>Portfolio Overview</Text>
        <Animated.View style={[styles.portfolioCard, {
          backgroundColor: isDark ? 'rgba(249, 115, 22, 0.08)' : 'rgba(249, 115, 22, 0.05)',
          borderColor: isDark ? 'rgba(249, 115, 22, 0.2)' : 'rgba(249, 115, 22, 0.15)',
          opacity: fadeAnim,
        }]}>
          <View style={styles.portfolioHeader}>
            <Text style={[styles.portfolioLabel, { color: colors.textSecondary }]}>Total Portfolio Value</Text>
            <View style={[styles.changeBadge, { backgroundColor: 'rgba(16, 185, 129, 0.1)' }]}>
              <MaterialCommunityIcons name="arrow-up" size={14} color="#10B981" />
              <Text style={[styles.changeText, { color: '#10B981' }]}>+3.99%</Text>
            </View>
          </View>
          <Text style={[styles.portfolioValue, { color: colors.textPrimary }]}>₹{portfolioValue.toLocaleString('en-IN')}</Text>
          <Text style={[styles.portfolioChange, { color: '#10B981' }]}>+₹{monthlyChange.toLocaleString('en-IN')} this month</Text>

          <View style={styles.summaryPillsRow}>
            <View style={[styles.summaryPill, { backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)' }]}>
              <Text style={[styles.pillLabel, { color: colors.textSecondary }]}>Invested</Text>
              <Text style={[styles.pillValue, { color: colors.textPrimary }]}>₹{formatINRShort(totalInvested)}</Text>
            </View>
            <View style={[styles.summaryPill, { backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)' }]}>
              <Text style={[styles.pillLabel, { color: colors.textSecondary }]}>Returns</Text>
              <Text style={[styles.pillValue, { color: '#10B981' }]}>+₹{formatINRShort(returns)}</Text>
            </View>
            <View style={[styles.summaryPill, { backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)' }]}>
              <Text style={[styles.pillLabel, { color: colors.textSecondary }]}>XIRR</Text>
              <Text style={[styles.pillValue, { color: '#10B981' }]}>{xirr}%</Text>
            </View>
          </View>
        </Animated.View>

        {/* ═══ ASSET ALLOCATION ═══ */}
        <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Asset Allocation</Text>
        <View style={[styles.glassCard, {
          backgroundColor: isDark ? 'rgba(30, 41, 59, 0.7)' : 'rgba(255, 255, 255, 0.85)',
          borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
        }]}>
          <View style={styles.donutContainer}>
            <Svg width={140} height={140}>
              <G rotation="-90" origin="70, 70">
                {mockAllocation.map((item, index) => {
                  const percent = (item.amount / totalAllocation) * 100;
                  const circumference = 2 * Math.PI * 50;
                  const offset = mockAllocation.slice(0, index).reduce((s, a) => s + (a.amount / totalAllocation) * circumference, 0);
                  return (
                    <Circle key={item.key} cx="70" cy="70" r="50" stroke={item.color} strokeWidth="20" fill="transparent"
                      strokeDasharray={`${(percent / 100) * circumference} ${circumference}`} strokeDashoffset={-offset} />
                  );
                })}
              </G>
            </Svg>
            <View style={styles.donutCenter}>
              <Text style={[styles.donutValue, { color: colors.textPrimary }]}>₹{formatINRShort(portfolioValue)}</Text>
            </View>
          </View>
          <View style={styles.legendGrid}>
            {mockAllocation.map(item => (
              <View key={item.key} style={styles.legendItem}>
                <View style={[styles.legendDot, { backgroundColor: item.color }]} />
                <Text style={[styles.legendName, { color: colors.textPrimary }]}>{item.name}</Text>
                <Text style={[styles.legendAmount, { color: colors.textSecondary }]}>{((item.amount / totalAllocation) * 100).toFixed(0)}%</Text>
              </View>
            ))}
          </View>
        </View>

        {/* ═══ INDIAN MARKETS ═══ */}
        <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Indian Markets</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.marketsScroll}>
          {MARKET_INDICES.map((idx, i) => (
            <View key={i} style={[styles.marketCard, {
              backgroundColor: isDark ? 'rgba(30, 41, 59, 0.7)' : 'rgba(255, 255, 255, 0.85)',
              borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
            }]}>
              <Text style={[styles.marketName, { color: colors.textSecondary }]}>{idx.name}</Text>
              <Text style={[styles.marketValue, { color: colors.textPrimary }]}>₹{idx.value.toLocaleString('en-IN')}</Text>
              <View style={[styles.marketChangeBadge, { backgroundColor: idx.up ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)' }]}>
                <MaterialCommunityIcons name={idx.up ? 'arrow-up' : 'arrow-down'} size={12} color={idx.up ? '#10B981' : '#EF4444'} />
                <Text style={[styles.marketChangeText, { color: idx.up ? '#10B981' : '#EF4444' }]}>{idx.change}%</Text>
              </View>
            </View>
          ))}
        </ScrollView>

        {/* ═══ RISK PROFILE ═══ */}
        <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Risk Profile & Strategy</Text>
        <View style={[styles.riskCard, {
          backgroundColor: isDark ? 'rgba(30, 41, 59, 0.7)' : 'rgba(255, 255, 255, 0.85)',
          borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
        }]}>
          <View style={styles.riskHeader}>
            <View style={[styles.riskBadge, {
              backgroundColor: riskProfile === 'Conservative' ? 'rgba(59, 130, 246, 0.15)' : riskProfile === 'Moderate' ? 'rgba(245, 158, 11, 0.15)' : 'rgba(239, 68, 68, 0.15)',
            }]}>
              <MaterialCommunityIcons
                name={riskProfile === 'Conservative' ? 'shield-check' : riskProfile === 'Moderate' ? 'scale-balance' : 'rocket-launch'}
                size={20} color={riskProfile === 'Conservative' ? '#3B82F6' : riskProfile === 'Moderate' ? '#F59E0B' : '#EF4444'} />
              <Text style={[styles.riskBadgeText, { color: riskProfile === 'Conservative' ? '#3B82F6' : riskProfile === 'Moderate' ? '#F59E0B' : '#EF4444' }]}>
                {riskProfile}
              </Text>
            </View>
            <TouchableOpacity style={[styles.retakeBtn, { borderColor: colors.border }]} onPress={() => { setShowRiskModal(true); setRiskStep(0); setRiskAnswers([]); }}>
              <Text style={[styles.retakeBtnText, { color: colors.textSecondary }]}>Retake</Text>
            </TouchableOpacity>
          </View>
          <Text style={[styles.strategyName, { color: colors.textPrimary }]}>{currentStrategy.name} Strategy</Text>
          <View style={styles.allocationBar}>
            {currentStrategy.allocation.map((item, i) => (
              <View key={i} style={[styles.allocationSegment, { width: `${item.p}%`, backgroundColor: item.c }]}>
                {item.p >= 15 && <Text style={styles.allocationSegmentText}>{item.p}%</Text>}
              </View>
            ))}
          </View>
          <View style={styles.allocationLegend}>
            {currentStrategy.allocation.map((item, i) => (
              <View key={i} style={styles.allocationLegendItem}>
                <View style={[styles.allocationLegendDot, { backgroundColor: item.c }]} />
                <Text style={[styles.allocationLegendText, { color: colors.textSecondary }]}>{item.name}</Text>
              </View>
            ))}
          </View>
        </View>

        {/* ═══ TAX SAVING ═══ */}
        <View style={[styles.glassCard, {
          backgroundColor: isDark ? 'rgba(30, 41, 59, 0.7)' : 'rgba(255, 255, 255, 0.85)',
          borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
        }]}>
          <View style={styles.taxHeader}>
            <View>
              <Text style={[styles.taxTitle, { color: colors.textPrimary }]}>Section 80C</Text>
              <Text style={[styles.taxUsed, { color: colors.textSecondary }]}>₹{formatINRShort(section80CUsed)} / ₹1.5L</Text>
            </View>
            <View style={[styles.taxPercentBadge, { backgroundColor: section80CUsed >= 150000 ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)' }]}>
              <Text style={[styles.taxPercentText, { color: section80CUsed >= 150000 ? '#10B981' : '#F59E0B' }]}>
                {((section80CUsed / 150000) * 100).toFixed(0)}%
              </Text>
            </View>
          </View>
          <View style={[styles.taxBarBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
            <View style={[styles.taxBarFill, { width: `${Math.min((section80CUsed / 150000) * 100, 100)}%`, backgroundColor: '#F97316' }]} />
          </View>
        </View>

        <View style={{ height: 100 }} />
      </ScrollView>

      {/* ═══ ADD GOAL FAB ═══ */}
      <TouchableOpacity style={styles.fab} onPress={openAddGoal}>
        <LinearGradient colors={['#EA580C', '#DC2626']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.fabGradient}>
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
                <TouchableOpacity onPress={() => setShowGoalModal(false)}>
                  <MaterialCommunityIcons name="close" size={24} color={colors.textSecondary} />
                </TouchableOpacity>
              </View>

              <TextInput
                style={[styles.input, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                value={goalForm.title}
                onChangeText={v => setGoalForm(p => ({ ...p, title: v }))}
                placeholder="Goal title (e.g., Emergency Fund)"
                placeholderTextColor={colors.textSecondary}
              />
              <View style={styles.inputRow}>
                <TextInput
                  style={[styles.input, styles.halfInput, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                  value={goalForm.target_amount}
                  onChangeText={v => setGoalForm(p => ({ ...p, target_amount: v }))}
                  placeholder="Target ₹"
                  placeholderTextColor={colors.textSecondary}
                  keyboardType="decimal-pad"
                />
                <TextInput
                  style={[styles.input, styles.halfInput, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                  value={goalForm.current_amount}
                  onChangeText={v => setGoalForm(p => ({ ...p, current_amount: v }))}
                  placeholder="Saved ₹"
                  placeholderTextColor={colors.textSecondary}
                  keyboardType="decimal-pad"
                />
              </View>
              <TextInput
                style={[styles.input, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                value={goalForm.deadline}
                onChangeText={v => setGoalForm(p => ({ ...p, deadline: v }))}
                placeholder="Deadline (YYYY-MM-DD)"
                placeholderTextColor={colors.textSecondary}
              />
              <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>Category</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.catScroll}>
                {GOAL_CATS.map(c => (
                  <TouchableOpacity key={c} style={[styles.catChip, {
                    backgroundColor: goalForm.category === c ? '#F97316' : colors.background,
                    borderColor: goalForm.category === c ? '#F97316' : colors.border,
                  }]} onPress={() => setGoalForm(p => ({ ...p, category: c }))}>
                    <Text style={{ color: goalForm.category === c ? '#fff' : colors.textSecondary, fontSize: 13 }}>{c}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>

              <TouchableOpacity style={styles.saveBtn} onPress={handleSaveGoal} disabled={saving}>
                <LinearGradient colors={['#EA580C', '#DC2626']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.saveBtnGradient}>
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
              <TouchableOpacity onPress={() => setShowRiskModal(false)}>
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
                <TouchableOpacity key={i} style={[styles.optionBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)', borderColor: colors.border }]}
                  onPress={() => handleRiskAnswer(opt.value)}>
                  <Text style={[styles.optionText, { color: colors.textPrimary }]}>{opt.label}</Text>
                </TouchableOpacity>
              ))}
            </View>
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
  headerBlur: { borderBottomWidth: 1 },
  headerSafeArea: { paddingHorizontal: 16, paddingBottom: 12 },
  headerContent: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', paddingTop: Platform.OS === 'android' ? 8 : 0 },
  headerLeft: { flex: 1 },
  gradientTitleBg: { alignSelf: 'flex-start', borderRadius: 8, paddingHorizontal: 10, paddingVertical: 4 },
  gradientTitle: { fontSize: 22, fontWeight: '800', color: '#fff' },
  headerSubtitle: { fontSize: 12, marginTop: 4 },
  refreshBtn: { width: 40, height: 40, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },

  // Scroll
  scrollView: { flex: 1 },
  scrollContent: { paddingTop: Platform.OS === 'ios' ? 120 : 100, paddingHorizontal: 16 },

  // Section
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  sectionTitle: { fontSize: 18, fontWeight: '700', marginBottom: 14 },
  addGoalBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 14, paddingVertical: 8, borderRadius: 12 },
  addGoalText: { color: '#fff', fontSize: 13, fontWeight: '700' },

  // Goals Overview
  goalsOverviewCard: { borderRadius: 18, padding: 16, borderWidth: 1.5, marginBottom: 16 },
  goalsOverviewRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  goalsOverviewLabel: { fontSize: 12, fontWeight: '600' },
  goalsOverviewAmount: { fontSize: 18, fontWeight: '800', marginTop: 2 },
  goalsPercentBadge: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 12 },
  goalsPercentText: { fontSize: 14, fontWeight: '800' },
  goalsProgressBar: { height: 8, borderRadius: 4, overflow: 'hidden' },
  goalsProgressFill: { height: '100%', borderRadius: 4 },

  // Empty Goals
  emptyGoals: { alignItems: 'center', padding: 32, borderRadius: 18, borderWidth: 1, marginBottom: 16 },
  emptyGoalsTitle: { fontSize: 16, fontWeight: '700', marginTop: 12 },
  emptyGoalsSubtitle: { fontSize: 13, marginTop: 4 },

  // Goals Scroll
  goalsScroll: { marginBottom: 8 },
  goalCard: { width: 160, padding: 14, borderRadius: 18, borderWidth: 1, marginRight: 12 },
  goalCardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  goalIconWrap: { width: 36, height: 36, borderRadius: 10, justifyContent: 'center', alignItems: 'center' },
  goalPercent: { fontSize: 14, fontWeight: '800' },
  goalTitle: { fontSize: 14, fontWeight: '700', marginBottom: 2 },
  goalCategory: { fontSize: 11, marginBottom: 10 },
  goalBarBg: { height: 6, borderRadius: 3, overflow: 'hidden', marginBottom: 6 },
  goalBarFill: { height: '100%', borderRadius: 3 },
  goalAmounts: { fontSize: 11 },

  // Portfolio
  portfolioCard: { borderRadius: 24, padding: 20, borderWidth: 2, marginBottom: 20 },
  portfolioHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  portfolioLabel: { fontSize: 13, fontWeight: '600' },
  changeBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  changeText: { fontSize: 12, fontWeight: '700' },
  portfolioValue: { fontSize: 34, fontWeight: '900', letterSpacing: -2 },
  portfolioChange: { fontSize: 14, fontWeight: '600', marginTop: 4 },
  summaryPillsRow: { flexDirection: 'row', gap: 10, marginTop: 16 },
  summaryPill: { flex: 1, padding: 12, borderRadius: 14, alignItems: 'center' },
  pillLabel: { fontSize: 11, marginBottom: 4 },
  pillValue: { fontSize: 14, fontWeight: '800' },

  // Glass Card
  glassCard: { borderRadius: 20, padding: 18, borderWidth: 1, marginBottom: 16 },

  // Donut
  donutContainer: { alignItems: 'center', marginBottom: 16, position: 'relative' },
  donutCenter: { position: 'absolute', top: 50, alignItems: 'center' },
  donutValue: { fontSize: 16, fontWeight: '800' },
  legendGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  legendItem: { flexDirection: 'row', alignItems: 'center', width: '47%', gap: 8 },
  legendDot: { width: 10, height: 10, borderRadius: 5 },
  legendName: { flex: 1, fontSize: 12, fontWeight: '600' },
  legendAmount: { fontSize: 11 },

  // Markets
  marketsScroll: { marginBottom: 16 },
  marketCard: { width: 120, padding: 14, borderRadius: 16, borderWidth: 1, marginRight: 10 },
  marketName: { fontSize: 10, fontWeight: '600', marginBottom: 4 },
  marketValue: { fontSize: 13, fontWeight: '800' },
  marketChangeBadge: { flexDirection: 'row', alignItems: 'center', gap: 2, marginTop: 6, paddingHorizontal: 6, paddingVertical: 3, borderRadius: 8, alignSelf: 'flex-start' },
  marketChangeText: { fontSize: 10, fontWeight: '700' },

  // Risk
  riskCard: { borderRadius: 20, padding: 18, borderWidth: 1, marginBottom: 16 },
  riskHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  riskBadge: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 14, paddingVertical: 8, borderRadius: 14 },
  riskBadgeText: { fontSize: 14, fontWeight: '700' },
  retakeBtn: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 10, borderWidth: 1 },
  retakeBtnText: { fontSize: 12, fontWeight: '600' },
  strategyName: { fontSize: 16, fontWeight: '700', marginBottom: 12 },
  allocationBar: { flexDirection: 'row', height: 20, borderRadius: 10, overflow: 'hidden', marginBottom: 10 },
  allocationSegment: { justifyContent: 'center', alignItems: 'center' },
  allocationSegmentText: { fontSize: 9, fontWeight: '700', color: '#fff' },
  allocationLegend: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  allocationLegendItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  allocationLegendDot: { width: 8, height: 8, borderRadius: 4 },
  allocationLegendText: { fontSize: 11 },

  // Tax
  taxHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  taxTitle: { fontSize: 15, fontWeight: '700' },
  taxUsed: { fontSize: 12, marginTop: 2 },
  taxPercentBadge: { paddingHorizontal: 10, paddingVertical: 6, borderRadius: 10 },
  taxPercentText: { fontSize: 12, fontWeight: '700' },
  taxBarBg: { height: 8, borderRadius: 4, overflow: 'hidden' },
  taxBarFill: { height: '100%', borderRadius: 4 },

  // FAB
  fab: { position: 'absolute', right: 20, bottom: 90, zIndex: 99999, borderRadius: 28, shadowColor: '#EA580C', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.4, shadowRadius: 12, elevation: 8, borderWidth: 2, borderColor: 'rgba(255,255,255,0.3)' },
  fabGradient: { width: 56, height: 56, borderRadius: 28, justifyContent: 'center', alignItems: 'center' },

  // Modal
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modalKav: { maxHeight: '90%' },
  modalContent: { borderTopLeftRadius: 28, borderTopRightRadius: 28, padding: 24, paddingBottom: 40 },
  modalHandle: { width: 40, height: 4, borderRadius: 2, backgroundColor: '#CBD5E1', alignSelf: 'center', marginBottom: 16 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  modalTitle: { fontSize: 20, fontWeight: '700' },
  input: { height: 52, borderRadius: 14, borderWidth: 1, paddingHorizontal: 16, fontSize: 15, marginBottom: 12 },
  inputRow: { flexDirection: 'row', gap: 10 },
  halfInput: { flex: 1 },
  fieldLabel: { fontSize: 12, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8 },
  catScroll: { maxHeight: 40, marginBottom: 16 },
  catChip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 16, borderWidth: 1, marginRight: 8 },
  saveBtn: { borderRadius: 999, overflow: 'hidden', marginTop: 8 },
  saveBtnGradient: { height: 56, justifyContent: 'center', alignItems: 'center' },
  saveBtnText: { color: '#fff', fontSize: 17, fontWeight: '700' },
  progressRow: { flexDirection: 'row', gap: 6, marginBottom: 20, justifyContent: 'center' },
  progressDot: { height: 6, borderRadius: 3 },
  questionText: { fontSize: 18, fontWeight: '700', textAlign: 'center', marginBottom: 24, lineHeight: 26 },
  optionsContainer: { gap: 10 },
  optionBtn: { padding: 16, borderRadius: 14, borderWidth: 1 },
  optionText: { fontSize: 15, fontWeight: '500', textAlign: 'center' },
});
