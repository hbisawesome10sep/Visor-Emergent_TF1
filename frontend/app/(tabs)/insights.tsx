import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, RefreshControl,
  ActivityIndicator, Dimensions, StatusBar, Animated,
} from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import { LinearGradient } from 'expo-linear-gradient';
import { useAuth } from '../../src/context/AuthContext';
import { useTheme } from '../../src/context/ThemeContext';
import { apiRequest } from '../../src/utils/api';
import { formatINRShort } from '../../src/utils/formatters';
import { HealthScoreCard } from '../../src/components/HealthScoreCard';
import { SpendingBreakdownCard } from '../../src/components/SpendingBreakdownCard';
import { CompareCard } from '../../src/components/CompareCard';
import { AIRecommendations } from '../../src/components/AIRecommendations';
import { Accent } from '../../src/utils/theme';
import AIAdvisorChat from '../../src/components/AIAdvisorChat';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const CARD_WIDTH = SCREEN_WIDTH - 32; // Full width minus padding

type DashboardStats = {
  total_income: number;
  total_expenses: number;
  total_investments: number;
  savings_rate: number;
  category_breakdown: Record<string, number>;
};

// ═══════════════════════════════════════════════════════════════════════════════
// HELPER FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

// Health Score - now uses backend-provided score for consistency with Dashboard
function getScoreLabel(score: number): { label: string; color: string } {
  if (score >= 80) return { label: 'Excellent', color: Accent.emerald };
  if (score >= 65) return { label: 'Good', color: Accent.teal };
  if (score >= 50) return { label: 'Fair', color: Accent.amber };
  if (score >= 35) return { label: 'Needs Work', color: '#F97316' };
  return { label: 'Critical', color: Accent.ruby };
}

function getScoreColor(score: number): string {
  if (score >= 76) return Accent.emerald;
  if (score >= 61) return Accent.teal;
  if (score >= 41) return Accent.amber;
  return Accent.ruby;
}

function getMetricStatus(value: number, target: number, isInverted: boolean = false): 'excellent' | 'good' | 'fair' | 'critical' {
  const ratio = isInverted ? target / (value || 1) : value / (target || 1);
  if (ratio >= 1) return 'excellent';
  if (ratio >= 0.7) return 'good';
  if (ratio >= 0.4) return 'fair';
  return 'critical';
}

function getStatusColor(status: 'excellent' | 'good' | 'fair' | 'critical'): string {
  switch (status) {
    case 'excellent': return Accent.emerald;
    case 'good': return Accent.teal;
    case 'fair': return Accent.amber;
    case 'critical': return Accent.ruby;
  }
}

function getStatusLabel(status: 'excellent' | 'good' | 'fair' | 'critical'): string {
  switch (status) {
    case 'excellent': return 'Excellent';
    case 'good': return 'Good';
    case 'fair': return 'Fair';
    case 'critical': return 'Critical';
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// FLIPPABLE INSIGHT CARD COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface InsightCardProps {
  icon: string;
  title: string;
  value: string;
  subtitle: string;
  status: 'excellent' | 'good' | 'fair' | 'critical';
  fillPercentage: number;
  benchmarkInfo: {
    title: string;
    description: string;
    source: string;
    yourValue: string;
    nationalAverage: string;
    recommended: string;
    calculation?: string;  // Show actual calculation formula
    actualAmounts?: {     // Show rupee amounts
      label1?: string;
      value1?: string;
      label2?: string;
      value2?: string;
      label3?: string;
      value3?: string;
    };
  };
  isDark: boolean;
  colors: any;
}

function InsightCard({
  icon, title, value, subtitle, status, fillPercentage, benchmarkInfo, isDark, colors
}: InsightCardProps) {
  const [showBack, setShowBack] = useState(false);
  const statusColor = getStatusColor(status);
  const statusLabel = getStatusLabel(status);
  const fillAnim = useRef(new Animated.Value(0)).current;
  const waveAnim = useRef(new Animated.Value(0)).current;
  const bubbleAnim = useRef(new Animated.Value(0)).current;

  // Gradient colors based on status
  const getGradient = (): [string, string] => {
    switch (status) {
      case 'excellent': return [Accent.emerald, '#047857'];
      case 'good': return [Accent.teal, '#0F766E'];
      case 'fair': return [Accent.amber, '#D97706'];
      case 'needs_work': return ['#EA580C', Accent.ruby];
      case 'critical': return [Accent.ruby, '#B91C1C'];
      default: return [Accent.sapphire, '#4F46E5'];
    }
  };

  useEffect(() => {
    Animated.timing(fillAnim, {
      toValue: Math.min(Math.max(fillPercentage, 0), 100),
      duration: 1500,
      useNativeDriver: false,
    }).start();

    Animated.loop(
      Animated.sequence([
        Animated.timing(waveAnim, { toValue: 1, duration: 3000, useNativeDriver: true }),
        Animated.timing(waveAnim, { toValue: 0, duration: 3000, useNativeDriver: true }),
      ])
    ).start();

    Animated.loop(
      Animated.sequence([
        Animated.timing(bubbleAnim, { toValue: 1, duration: 2500, useNativeDriver: true }),
        Animated.timing(bubbleAnim, { toValue: 0, duration: 0, useNativeDriver: true }),
      ])
    ).start();
  }, [fillPercentage]);

  const fillHeight = fillAnim.interpolate({
    inputRange: [0, 100],
    outputRange: ['0%', '100%'],
  });

  const waveX = waveAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [-15, 15],
  });

  const bubbleY = bubbleAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0, -50],
  });

  const bubbleOpacity = bubbleAnim.interpolate({
    inputRange: [0, 0.7, 1],
    outputRange: [0.5, 0.2, 0],
  });

  const gradient = getGradient();

  // Card background for back side
  const cardBg = isDark 
    ? 'rgba(30, 41, 59, 0.95)' 
    : 'rgba(255, 255, 255, 0.98)';
  const borderColor = isDark 
    ? `${statusColor}40` 
    : `${statusColor}30`;

  if (showBack) {
    return (
      <TouchableOpacity 
        activeOpacity={0.95} 
        onPress={() => setShowBack(false)}
        style={[styles.insightCard, styles.insightCardBack, { backgroundColor: cardBg, borderColor }]}
      >
        <TouchableOpacity 
          style={[styles.flipIconBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)' }]}
          onPress={() => setShowBack(false)}
        >
          <MaterialCommunityIcons name="rotate-left" size={14} color={colors.textSecondary} />
        </TouchableOpacity>

        <View style={styles.backContent}>
          <Text style={[styles.backTitle, { color: colors.textPrimary }]}>{benchmarkInfo.title}</Text>
          
          {/* Show calculation formula if provided */}
          {benchmarkInfo.calculation && (
            <View style={[styles.calculationBox, { backgroundColor: isDark ? 'rgba(16, 185, 129, 0.1)' : 'rgba(16, 185, 129, 0.08)' }]}>
              <Text style={[styles.calculationLabel, { color: colors.textSecondary }]}>How it's calculated:</Text>
              <Text style={[styles.calculationFormula, { color: Accent.emerald }]}>{benchmarkInfo.calculation}</Text>
            </View>
          )}
          
          {/* Show actual rupee amounts if provided */}
          {benchmarkInfo.actualAmounts && (
            <View style={[styles.amountsBox, { backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)' }]}>
              {benchmarkInfo.actualAmounts.label1 && (
                <View style={styles.amountRow}>
                  <Text style={[styles.amountLabel, { color: colors.textSecondary }]}>{benchmarkInfo.actualAmounts.label1}</Text>
                  <Text style={[styles.amountValue, { color: colors.textPrimary }]}>{benchmarkInfo.actualAmounts.value1}</Text>
                </View>
              )}
              {benchmarkInfo.actualAmounts.label2 && (
                <View style={styles.amountRow}>
                  <Text style={[styles.amountLabel, { color: colors.textSecondary }]}>{benchmarkInfo.actualAmounts.label2}</Text>
                  <Text style={[styles.amountValue, { color: colors.textPrimary }]}>{benchmarkInfo.actualAmounts.value2}</Text>
                </View>
              )}
              {benchmarkInfo.actualAmounts.label3 && (
                <View style={styles.amountRow}>
                  <Text style={[styles.amountLabel, { color: colors.textSecondary }]}>{benchmarkInfo.actualAmounts.label3}</Text>
                  <Text style={[styles.amountValue, { color: statusColor, fontWeight: '700' as any }]}>{benchmarkInfo.actualAmounts.value3}</Text>
                </View>
              )}
            </View>
          )}
          
          {/* Comparison stats */}
          <View style={[styles.backStatsBox, { backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)' }]}>
            <View style={styles.backStatRow}>
              <Text style={[styles.backStatLabel, { color: colors.textSecondary }]}>Your Score</Text>
              <Text style={[styles.backStatValue, { color: statusColor }]}>{benchmarkInfo.yourValue}</Text>
            </View>
            <View style={styles.backStatRow}>
              <Text style={[styles.backStatLabel, { color: colors.textSecondary }]}>India Avg</Text>
              <Text style={[styles.backStatValue, { color: colors.textPrimary }]}>{benchmarkInfo.nationalAverage}</Text>
            </View>
            <View style={styles.backStatRow}>
              <Text style={[styles.backStatLabel, { color: colors.textSecondary }]}>Target</Text>
              <Text style={[styles.backStatValue, { color: Accent.emerald }]}>{benchmarkInfo.recommended}</Text>
            </View>
          </View>
          
          <Text style={[styles.backDesc, { color: colors.textSecondary }]}>{benchmarkInfo.description}</Text>
          <Text style={[styles.backSource, { color: colors.textSecondary }]}>Source: {benchmarkInfo.source}</Text>
        </View>
      </TouchableOpacity>
    );
  }

  return (
    <TouchableOpacity 
      activeOpacity={0.9} 
      onPress={() => setShowBack(true)}
      style={styles.insightCard}
    >
      <LinearGradient
        colors={gradient}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={styles.insightGradient}
      >
        {/* Animated liquid fill */}
        <View style={styles.liquidContainer}>
          <Animated.View
            style={[
              styles.liquidFill,
              { height: fillHeight, backgroundColor: 'rgba(255,255,255,0.12)' },
            ]}
          >
            <Animated.View
              style={[styles.wave, { transform: [{ translateX: waveX }] }]}
            />
          </Animated.View>
          <Animated.View
            style={[styles.bubble, { transform: [{ translateY: bubbleY }], opacity: bubbleOpacity }]}
          />
          <Animated.View
            style={[styles.bubble, styles.bubble2, { transform: [{ translateY: bubbleY }], opacity: bubbleOpacity }]}
          />
        </View>

        {/* Card content */}
        <View style={styles.insightContent}>
          <View style={styles.cardHeader}>
            <View style={styles.insightIconBox}>
              <MaterialCommunityIcons name={icon as any} size={18} color="rgba(255,255,255,0.9)" />
            </View>
            <View style={styles.insightBadge}>
              <Text style={styles.insightBadgeText}>{statusLabel}</Text>
            </View>
          </View>

          {/* Flip info hint */}
          <TouchableOpacity 
            style={styles.flipIconBtnFront}
            onPress={() => setShowBack(true)}
          >
            <MaterialCommunityIcons name="information-outline" size={14} color="rgba(255,255,255,0.6)" />
          </TouchableOpacity>

          <Text style={styles.insightTitle}>{title}</Text>
          <Text style={styles.insightValue}>{value}</Text>
          <Text style={styles.insightSubtitle}>{subtitle}</Text>

          {/* Bottom fill bar */}
          <View style={styles.insightBarBg}>
            <View style={[styles.insightBarFill, { width: `${Math.min(fillPercentage, 100)}%` }]} />
          </View>
        </View>
      </LinearGradient>
    </TouchableOpacity>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN INSIGHTS SCREEN
// ═══════════════════════════════════════════════════════════════════════════════

export default function InsightsScreen() {
  const { user, token, loading: authLoading } = useAuth();
  const { colors, isDark } = useTheme();
  const insets = useSafeAreaInsets();
  
  // Calculate header height dynamically (includes date range pills)
  const HEADER_HEIGHT = 100 + insets.top;

  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedFrequency, setSelectedFrequency] = useState<'Quarter' | 'Month' | 'Year' | 'Custom'>('Month');

  const getDateRange = useCallback((freq: string) => {
    const now = new Date();
    let start: Date;
    switch (freq) {
      case 'Quarter':
        start = new Date(now.getFullYear(), now.getMonth() - 3, now.getDate());
        break;
      case 'Year':
        start = new Date(now.getFullYear(), 0, 1);
        break;
      case 'Custom':
        start = new Date(2020, 0, 1);
        break;
      default: // Month
        start = new Date(now.getFullYear(), now.getMonth(), 1);
        break;
    }
    return {
      start: start.toISOString().split('T')[0],
      end: now.toISOString().split('T')[0],
    };
  }, []);

  const fetchData = useCallback(async () => {
    if (!token) {
      setStats({
        total_income: 150000, total_expenses: 95000, total_investments: 25000,
        savings_rate: 36.7,
        category_breakdown: { 'Housing': 25000, 'Food': 15000, 'Transport': 10000, 'Utilities': 5000, 'Shopping': 12000, 'Entertainment': 8000 },
      });
      setLoading(false);
      return;
    }
    try {
      const { start, end } = getDateRange(selectedFrequency);
      const url = selectedFrequency === 'Custom'
        ? '/dashboard/stats'
        : `/dashboard/stats?start_date=${start}&end_date=${end}`;
      const data = await apiRequest(url, { token });
      setStats(data);
    } catch (e) {
      console.error(e);
      setStats({
        total_income: 150000, total_expenses: 95000, total_investments: 25000,
        savings_rate: 36.7, category_breakdown: {},
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token, selectedFrequency, getDateRange]);

  useEffect(() => {
    if (!authLoading) {
      fetchData();
    }
  }, [authLoading, fetchData]);

  useEffect(() => {
    const timeout = setTimeout(() => {
      if (loading) {
        setStats({
          total_income: 150000,
          total_expenses: 95000,
          total_investments: 25000,
          savings_rate: 36.7,
          category_breakdown: { 'Housing': 25000, 'Food': 15000, 'Transport': 10000 },
        });
        setLoading(false);
      }
    }, 3000);
    return () => clearTimeout(timeout);
  }, [loading]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  // Calculate metrics from real data
  const income = stats?.total_income || 0;
  const expenses = stats?.total_expenses || 0;
  const investments = stats?.total_investments || 0;
  const savingsRate = stats?.savings_rate || 0;
  const goalProgress = stats?.goal_progress || 0;
  
  // Check if we have sufficient data for meaningful calculations
  const hasIncomeData = income > 0;
  const hasSufficientData = stats?.health_score?.has_sufficient_data ?? hasIncomeData;

  // Use backend-provided health score (consistent with Dashboard)
  const healthScore = stats?.health_score?.overall ?? 0;
  const healthGrade = stats?.health_score?.grade ?? 'No Data';
  const breakdown = stats?.health_score?.breakdown ?? { savings: 0, investments: 0, spending: 0, goals: 0 };

  // Calculate all financial metrics - use backend metrics if available, otherwise calculate
  // Get actual EMI from category breakdown (EMI is a category)
  const actualEMI = (stats?.category_breakdown?.['EMI'] as number) || 0;
  const emiRatio = hasIncomeData ? (actualEMI / income) * 100 : 0;
  
  // Use backend metrics for spending/investment rates (they handle edge cases)
  const investmentRate = stats?.health_score?.metrics?.investment_rate ?? 
    (hasIncomeData ? (investments / income) * 100 : 0);
  const spendingRate = stats?.health_score?.metrics?.expense_ratio ?? 
    (hasIncomeData ? Math.min((expenses / income) * 100, 200) : 0);  // Cap at 200%
  
  const monthlySavings = Math.max(0, income - expenses);
  const runwayMonths = expenses > 0 && monthlySavings > 0 
    ? Math.max(0, (monthlySavings * 6) / expenses) 
    : 0;
  const foirRatio = hasIncomeData 
    ? Math.min(((actualEMI + (expenses * 0.15)) / income) * 100, 200) // Cap at 200%
    : 0;
  const currentWealth = investments * 12;
  const projectedWealth5Years = currentWealth * Math.pow(1.12, 5);

  // Spending breakdown
  const spendingData = Object.entries(stats?.category_breakdown || {})
    .map(([category, amount]) => ({ category, amount: amount as number }))
    .sort((a, b) => b.amount - a.amount)
    .slice(0, 6);

  // AI Recommendations based on real data
  // Only show meaningful recommendations when we have income data
  const aiRecommendations = hasSufficientData ? [
    // Savings recommendation
    {
      priority: savingsRate < 20 ? 'high' : savingsRate < 30 ? 'medium' : 'low',
      icon: 'piggy-bank',
      title: savingsRate < 20 ? 'Boost Your Savings' : savingsRate < 30 ? 'Optimize Savings' : 'Excellent Savings!',
      description: savingsRate < 20
        ? `Your savings rate of ${savingsRate.toFixed(0)}% is below the recommended 20%. Consider automating transfers to a separate savings account on payday.`
        : savingsRate < 30
        ? `You're saving ${savingsRate.toFixed(0)}% - good! Push to 30% to accelerate wealth building. Try the 50/30/20 rule.`
        : `Outstanding! Your ${savingsRate.toFixed(0)}% savings rate puts you in the top 5% of Indian savers.`,
      impact: savingsRate < 20 ? `Target: Save ₹${formatINRShort(Math.max(0, (income * 0.2) - monthlySavings))}/month more` : 'On track',
      source: 'RBI Financial Literacy Guidelines',
    },
    // Investment recommendation
    {
      priority: investmentRate < 15 ? 'high' : investmentRate < 20 ? 'medium' : 'low',
      icon: 'chart-line',
      title: investmentRate < 15 ? 'Increase Investments' : 'Strong Investment Habit',
      description: investmentRate < 15
        ? `Only ${investmentRate.toFixed(0)}% goes to investments. Start/increase SIPs in index funds or ELSS for tax benefits under Section 80C.`
        : `${investmentRate.toFixed(0)}% investment rate is excellent! Consider diversifying across equity, debt, and gold.`,
      impact: investmentRate < 15 ? `Potential: ₹${formatINRShort(income * 0.05)}/month additional` : 'Well diversified',
      source: 'SEBI Investor Education',
    },
    // EMI/Debt recommendation
    {
      priority: emiRatio > 40 ? 'high' : emiRatio > 30 ? 'medium' : 'low',
      icon: 'credit-card',
      title: emiRatio > 40 ? 'High EMI Burden' : 'EMI Under Control',
      description: emiRatio > 40
        ? `Your EMI-to-income ratio of ${emiRatio.toFixed(0)}% exceeds RBI's 40% threshold. Avoid new loans and consider prepaying high-interest debt.`
        : actualEMI > 0 
          ? `EMI ratio of ${emiRatio.toFixed(0)}% is healthy. Maintain this to preserve loan eligibility for future needs.`
          : `No EMI payments detected. Great debt-free status! Consider this when planning future loans.`,
      impact: emiRatio > 40 ? 'Risk: Loan rejection, financial stress' : 'Good loan eligibility',
      source: 'RBI Lending Guidelines',
    },
    // Emergency fund recommendation
    {
      priority: runwayMonths < 3 ? 'high' : runwayMonths < 6 ? 'medium' : 'low',
      icon: 'shield-check',
      title: runwayMonths < 6 ? 'Build Emergency Fund' : 'Emergency Fund Ready',
      description: runwayMonths < 6
        ? `You have ${runwayMonths.toFixed(1)} months of expenses covered. RBI recommends 6 months. Park emergency funds in liquid funds or FDs.`
        : `Great! ${runwayMonths.toFixed(1)} months runway provides solid financial security.`,
      impact: runwayMonths < 6 ? `Target: ${formatINRShort(expenses * 6)} total` : 'Well prepared',
      source: 'RBI Financial Literacy',
    },
    // Tax planning recommendation
    {
      priority: 'medium',
      icon: 'file-document',
      title: 'Tax Planning Opportunities',
      description: `Maximize Section 80C (₹1.5L limit): ELSS, PPF, EPF. Section 80D: Health insurance up to ₹25K (₹50K for seniors). NPS gives extra ₹50K deduction under 80CCD(1B).`,
      impact: 'Save up to ₹46,800 in taxes',
      source: 'Income Tax Act, 1961',
    },
    // Spending recommendation
    {
      priority: spendingRate > 70 ? 'medium' : 'low',
      icon: 'wallet',
      title: spendingRate > 70 ? 'Review Spending' : 'Spending in Check',
      description: spendingRate > 70
        ? `${spendingRate.toFixed(0)}% of income goes to expenses. Review subscriptions, dining out, and discretionary spending. Try expense tracking for 30 days.`
        : `Excellent! Keeping expenses at ${spendingRate.toFixed(0)}% leaves room for savings and investments.`,
      impact: spendingRate > 70 ? `Potential savings: ₹${formatINRShort(income * 0.1)}/month` : 'Good discipline',
      source: 'NSO Household Survey',
    },
  ] : [
    // Show helpful prompts when no data
    {
      priority: 'medium',
      icon: 'plus-circle',
      title: 'Add Income Data',
      description: 'Upload bank statements or add income transactions to unlock personalized financial insights and recommendations.',
      impact: 'Get savings rate, investment tips, and more',
      source: 'Visor AI',
    },
    {
      priority: 'low',
      icon: 'bank',
      title: 'Connect Your Accounts',
      description: 'Import transactions from your bank statements to see spending patterns, EMI tracking, and financial health analysis.',
      impact: 'Automated expense categorization',
      source: 'Visor AI',
    },
  ];

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: colors.background }]}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={Accent.emerald} />
          <Text style={[styles.loadingText, { color: colors.textSecondary }]}>
            Analyzing your finances...
          </Text>
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <StatusBar barStyle={isDark ? 'light-content' : 'dark-content'} />

      {/* Clean Header */}
      <View style={[styles.stickyHeader, { paddingTop: insets.top, backgroundColor: isDark ? '#000000' : '#FFFFFF' }]}>
        <View
          style={[
            styles.headerContent,
            {
              backgroundColor: isDark ? '#000000' : '#FFFFFF',
              borderBottomColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)',
            },
          ]}
        >
          <View style={styles.headerLeft}>
            <Text style={[styles.headerTitle, { color: isDark ? Accent.teal : '#008F7A' }]}>Financial Insights</Text>
            <Text style={[styles.headerSubtitle, { color: colors.textSecondary }]}>
              {selectedFrequency === 'Month' ? 'This Month' : selectedFrequency === 'Quarter' ? 'This Quarter' : selectedFrequency === 'Year' ? 'This Year' : 'All Time'}
            </Text>
          </View>
          <TouchableOpacity
            style={[styles.refreshBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)' }]}
            onPress={onRefresh}
          >
            <MaterialCommunityIcons name="refresh" size={20} color={Accent.emerald} />
          </TouchableOpacity>
        </View>
        {/* Date Range Selector */}
        <View style={{ flexDirection: 'row', justifyContent: 'center', gap: 6, paddingBottom: 10, paddingHorizontal: 16 }}>
          {(['Quarter', 'Month', 'Year', 'Custom'] as const).map((freq) => (
            <TouchableOpacity
              key={freq}
              data-testid={`insights-freq-${freq.toLowerCase()}`}
              onPress={() => setSelectedFrequency(freq)}
              style={{
                paddingHorizontal: 14, paddingVertical: 6, borderRadius: 16,
                backgroundColor: selectedFrequency === freq
                  ? isDark ? Accent.emerald : '#008F7A'
                  : isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)',
              }}
            >
              <Text style={{
                fontSize: 12, fontWeight: selectedFrequency === freq ? '700' as any : '500' as any,
                color: selectedFrequency === freq ? '#fff' : colors.textSecondary,
              }}>
                {freq === 'Quarter' ? 'Q' : freq === 'Month' ? 'M' : freq === 'Year' ? 'Y' : 'All'}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={[styles.scrollContent, { paddingTop: HEADER_HEIGHT + 16 }]}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Accent.emerald} />}
        showsVerticalScrollIndicator={false}
      >
        {/* ═══ FINANCIAL HEALTH SCORE ═══ */}
        <HealthScoreCard
          healthScore={healthScore}
          breakdown={breakdown}
          savingsRate={savingsRate}
          spendingRate={spendingRate}
          investmentRate={investmentRate}
          goalProgress={goalProgress}
          isDark={isDark}
          colors={colors}
        />

        {/* ═══ KEY FINANCIAL INSIGHTS ═══ */}
        <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Key Financial Insights</Text>
        
        <View style={styles.insightGrid}>
          <InsightCard
            icon="piggy-bank"
            title="Savings Rate"
            value={`${savingsRate.toFixed(1)}%`}
            subtitle="of income saved"
            status={getMetricStatus(savingsRate, 20)}
            fillPercentage={(savingsRate / 30) * 100}
            benchmarkInfo={{
              title: 'Savings Rate',
              description: 'Your monthly savings as a % of income.',
              source: 'RBI Guidelines',
              yourValue: `${savingsRate.toFixed(1)}%`,
              nationalAverage: '5.1%',
              recommended: '20%+',
              calculation: `(Income - Expenses) ÷ Income × 100`,
              actualAmounts: {
                label1: 'Total Income',
                value1: `₹${formatINRShort(income)}`,
                label2: 'Total Expenses',
                value2: `₹${formatINRShort(expenses)}`,
                label3: 'Monthly Savings',
                value3: `₹${formatINRShort(monthlySavings)}`,
              },
            }}
            isDark={isDark}
            colors={colors}
          />
          <InsightCard
            icon="credit-card"
            title="EMI Ratio"
            value={`${emiRatio.toFixed(1)}%`}
            subtitle="EMI to income"
            status={getMetricStatus(40, emiRatio, true)}
            fillPercentage={emiRatio}
            benchmarkInfo={{
              title: 'EMI-to-Income',
              description: 'Estimated monthly EMI burden.',
              source: 'RBI Lending Rules',
              yourValue: `${emiRatio.toFixed(1)}%`,
              nationalAverage: '28%',
              recommended: '<40%',
              calculation: `Estimated EMIs ÷ Income × 100`,
              actualAmounts: {
                label1: 'Monthly Income',
                value1: `₹${formatINRShort(income)}`,
                label2: 'Est. EMI (35% of expenses)',
                value2: `₹${formatINRShort(emiEstimate)}`,
                label3: 'EMI Ratio',
                value3: `${emiRatio.toFixed(1)}%`,
              },
            }}
            isDark={isDark}
            colors={colors}
          />
          <InsightCard
            icon="chart-line"
            title="Investment Rate"
            value={`${investmentRate.toFixed(1)}%`}
            subtitle="of income invested"
            status={getMetricStatus(investmentRate, 20)}
            fillPercentage={(investmentRate / 30) * 100}
            benchmarkInfo={{
              title: 'Investment Rate',
              description: 'Monthly allocation to wealth-building.',
              source: 'SEBI Guidelines',
              yourValue: `${investmentRate.toFixed(1)}%`,
              nationalAverage: '11.4%',
              recommended: '20%+',
              calculation: `Investments ÷ Income × 100`,
              actualAmounts: {
                label1: 'Monthly Income',
                value1: `₹${formatINRShort(income)}`,
                label2: 'Monthly Investments',
                value2: `₹${formatINRShort(investments)}`,
                label3: 'Investment Rate',
                value3: `${investmentRate.toFixed(1)}%`,
              },
            }}
            isDark={isDark}
            colors={colors}
          />
          <InsightCard
            icon="wallet"
            title="Spending"
            value={`${spendingRate.toFixed(1)}%`}
            subtitle="of income spent"
            status={getMetricStatus(70, spendingRate, true)}
            fillPercentage={spendingRate}
            benchmarkInfo={{
              title: 'Expense Ratio',
              description: 'How much of income goes to expenses.',
              source: 'NSO Survey',
              yourValue: `${spendingRate.toFixed(1)}%`,
              nationalAverage: '75%',
              recommended: '<70%',
              calculation: `Expenses ÷ Income × 100`,
              actualAmounts: {
                label1: 'Monthly Income',
                value1: `₹${formatINRShort(income)}`,
                label2: 'Monthly Expenses',
                value2: `₹${formatINRShort(expenses)}`,
                label3: 'Spending Rate',
                value3: `${spendingRate.toFixed(1)}%`,
              },
            }}
            isDark={isDark}
            colors={colors}
          />
          <InsightCard
            icon="shield-check"
            title="Emergency Fund"
            value={`${runwayMonths.toFixed(1)} mo`}
            subtitle="runway coverage"
            status={getMetricStatus(runwayMonths, 6)}
            fillPercentage={(runwayMonths / 12) * 100}
            benchmarkInfo={{
              title: 'Emergency Runway',
              description: 'How long savings can cover expenses.',
              source: 'RBI Financial Literacy',
              yourValue: `${runwayMonths.toFixed(1)} months`,
              nationalAverage: '2.5 mo',
              recommended: '6+ months',
              calculation: `(Savings × 6) ÷ Monthly Expenses`,
              actualAmounts: {
                label1: 'Monthly Savings',
                value1: `₹${formatINRShort(monthlySavings)}`,
                label2: 'Monthly Expenses',
                value2: `₹${formatINRShort(expenses)}`,
                label3: 'Runway',
                value3: `${runwayMonths.toFixed(1)} months`,
              },
            }}
            isDark={isDark}
            colors={colors}
          />
          <InsightCard
            icon="scale-balance"
            title="FOIR Ratio"
            value={`${foirRatio.toFixed(1)}%`}
            subtitle="fixed obligations"
            status={getMetricStatus(50, foirRatio, true)}
            fillPercentage={foirRatio}
            benchmarkInfo={{
              title: 'Fixed Obligations',
              description: 'All fixed EMIs, rent, insurance as % of income.',
              source: 'Banking Standards',
              yourValue: `${foirRatio.toFixed(1)}%`,
              nationalAverage: '45%',
              recommended: '<50%',
              calculation: `(EMIs + 15% of Expenses) ÷ Income × 100`,
              actualAmounts: {
                label1: 'Monthly Income',
                value1: `₹${formatINRShort(income)}`,
                label2: 'Fixed Obligations Est.',
                value2: `₹${formatINRShort(emiEstimate + (expenses * 0.15))}`,
                label3: 'FOIR Ratio',
                value3: `${foirRatio.toFixed(1)}%`,
              },
            }}
            isDark={isDark}
            colors={colors}
          />
        </View>

        {/* ═══ HOW YOU COMPARE ═══ */}
        <CompareCard
          savingsRate={savingsRate}
          investmentRate={investmentRate}
          spendingRate={spendingRate}
          runwayMonths={runwayMonths}
          isDark={isDark}
          colors={colors}
        />

        {/* ═══ SPENDING BREAKDOWN ═══ */}
        <SpendingBreakdownCard data={spendingData} isDark={isDark} colors={colors} />

        {/* ═══ AI RECOMMENDATIONS ═══ */}
        <AIRecommendations recommendations={aiRecommendations} isDark={isDark} colors={colors} />

        <View style={{ height: 100 }} />
      </ScrollView>

      {/* AI Financial Advisor Button */}
      <AIAdvisorChat token={token} colors={colors} isDark={isDark} />
    </View>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// STYLES
// ═══════════════════════════════════════════════════════════════════════════════

const styles = StyleSheet.create({
  container: { flex: 1 },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 12 },
  loadingText: { fontSize: 14 },

  // Header
  stickyHeader: { position: 'absolute', top: 0, left: 0, right: 0, zIndex: 100 },
  headerContent: { 
    flexDirection: 'row', 
    justifyContent: 'space-between', 
    alignItems: 'center', 
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
  },
  headerLeft: { flex: 1 },
  headerTitle: { fontSize: 22, fontFamily: 'DM Sans', fontWeight: '700' as any },
  headerSubtitle: { fontSize: 12, marginTop: 2 },
  refreshBtn: { width: 40, height: 40, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },

  // Scroll
  scrollView: { flex: 1 },
  scrollContent: { paddingHorizontal: 16, paddingBottom: 100 },

  // Health Score Card
  healthScoreCard: { borderRadius: 20, padding: 20, borderWidth: 2, marginBottom: 24 },
  scoreFlipBtn: { position: 'absolute', top: 12, right: 12, width: 28, height: 28, borderRadius: 14, justifyContent: 'center', alignItems: 'center', zIndex: 10 },
  healthScoreFront: { minHeight: 100 },
  scoreRow: { flexDirection: 'row', alignItems: 'center', gap: 16 },
  scoreRingBox: { width: 100, height: 100, position: 'relative' },
  scoreCenter: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, justifyContent: 'center', alignItems: 'center' },
  scoreNum: { fontSize: 28, fontFamily: 'DM Sans', fontWeight: '700' as any, letterSpacing: -1 },
  scoreOf: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600' as any },
  scoreInfo: { flex: 1, gap: 6 },
  scoreTitle: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '700' as any },
  scoreLabelBadge: { alignSelf: 'flex-start', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  scoreLabelText: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '700' as any },
  scoreDesc: { fontSize: 13, lineHeight: 18 },
  healthScoreBack: { minHeight: 100 },
  scoreBackTitle: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '700' as any, marginBottom: 4 },
  scoreBackDesc: { fontSize: 12, marginBottom: 12 },
  scoreBreakdown: { borderRadius: 12, padding: 12 },
  breakdownRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 8 },
  breakdownLabel: { fontSize: 13 },
  breakdownValue: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '600' as any },
  breakdownTotal: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingTop: 10, marginTop: 4, borderTopWidth: 1 },
  breakdownTotalLabel: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700' as any },
  breakdownTotalValue: { fontSize: 18, fontFamily: 'DM Sans', fontWeight: '700' as any },

  // Section Title
  sectionTitle: { fontSize: 18, fontFamily: 'DM Sans', fontWeight: '700' as any, marginBottom: 4, marginTop: 8 },
  sectionSubtitle: { fontSize: 13, marginBottom: 16 },

  // Insight Grid
  insightGrid: { flexDirection: 'column', gap: 12, marginBottom: 24 },
  insightCard: {
    width: CARD_WIDTH,
    minHeight: 140,
    borderRadius: 18,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.15)',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 6,
  },
  insightCardBack: {
    minHeight: 180,
    padding: 16,
  },
  insightGradient: {
    flex: 1,
    minHeight: 140,
    position: 'relative',
  },
  liquidContainer: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'flex-end',
    overflow: 'hidden',
    borderRadius: 18,
  },
  liquidFill: {
    width: '100%',
    position: 'relative',
    overflow: 'hidden',
  },
  wave: {
    position: 'absolute',
    top: -6,
    left: -15,
    right: -15,
    height: 12,
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderRadius: 6,
  },
  bubble: {
    position: 'absolute',
    bottom: 20,
    left: '30%',
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: 'rgba(255,255,255,0.35)',
  },
  bubble2: {
    left: '60%',
    width: 4,
    height: 4,
    borderRadius: 2,
  },
  insightContent: {
    flex: 1,
    padding: 14,
    justifyContent: 'space-between',
    zIndex: 2,
  },
  insightIconBox: {
    width: 34,
    height: 34,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.2)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  insightBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.2)',
  },
  insightBadgeText: {
    fontSize: 11,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
    color: '#fff',
  },
  flipIconBtnFront: {
    position: 'absolute',
    top: 14,
    right: 14,
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.15)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 3,
  },
  insightTitle: {
    fontSize: 13,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
    color: 'rgba(255,255,255,0.9)',
    marginTop: 4,
    textShadowColor: 'rgba(0,0,0,0.2)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  insightValue: {
    fontSize: 24,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
    color: '#fff',
    letterSpacing: -0.5,
    textShadowColor: 'rgba(0,0,0,0.25)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 3,
  },
  insightSubtitle: {
    fontSize: 11,
    color: 'rgba(255,255,255,0.7)',
    fontFamily: 'DM Sans', fontWeight: '500' as any,
  },
  insightBarBg: {
    height: 4,
    borderRadius: 2,
    backgroundColor: 'rgba(255,255,255,0.2)',
    marginTop: 8,
    overflow: 'hidden',
  },
  insightBarFill: {
    height: '100%',
    borderRadius: 2,
    backgroundColor: 'rgba(255,255,255,0.7)',
  },
  flipIconBtn: { position: 'absolute', top: 10, right: 10, width: 24, height: 24, borderRadius: 12, justifyContent: 'center', alignItems: 'center', zIndex: 10 },
  frontContent: { flex: 1, paddingTop: 8 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  backContent: { flex: 1, paddingTop: 20 },
  backTitle: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' as any, marginBottom: 8 },
  backDesc: { fontSize: 11, lineHeight: 15, marginBottom: 6 },
  calculationBox: { borderRadius: 8, padding: 10, marginBottom: 10 },
  calculationLabel: { fontSize: 10, marginBottom: 4 },
  calculationFormula: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600' as any },
  amountsBox: { borderRadius: 8, padding: 10, marginBottom: 10 },
  amountRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 3 },
  amountLabel: { fontSize: 11 },
  amountValue: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600' as any },
  backStatsBox: { borderRadius: 8, padding: 10, gap: 4, marginBottom: 8 },
  backStatRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  backStatLabel: { fontSize: 10 },
  backStatValue: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '700' as any },
  backSource: { fontSize: 9, textAlign: 'center', opacity: 0.7 },

  // Compare Card
  compareCard: { borderRadius: 16, padding: 16, borderWidth: 1, marginBottom: 24 },
  compareHeader: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 16 },
  compareIcon: { width: 44, height: 44, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  compareTitleBox: { flex: 1 },
  compareTitle: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '700' as any },
  compareSubtitle: { fontSize: 12, marginTop: 2 },
  compareGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  compareItem: { width: (SCREEN_WIDTH - 80) / 2, backgroundColor: 'rgba(0,0,0,0.02)', borderRadius: 12, padding: 12, alignItems: 'center' },
  compareLabel: { fontSize: 11, marginBottom: 4 },
  compareValue: { fontSize: 20, fontFamily: 'DM Sans', fontWeight: '700' as any },
  compareAvg: { fontSize: 10, marginTop: 2 },
  compareSource: { fontSize: 10, textAlign: 'center', marginTop: 12 },

  // Spending Card
  spendingCard: { borderRadius: 16, padding: 16, borderWidth: 1, marginBottom: 24 },
  cardSectionTitle: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '700' as any, marginBottom: 4 },
  cardSectionSubtitle: { fontSize: 12, marginBottom: 14 },
  spendingRow: { marginBottom: 14 },
  spendingLeft: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 6 },
  spendingIcon: { width: 30, height: 30, borderRadius: 8, justifyContent: 'center', alignItems: 'center' },
  spendingCategory: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '600' as any, flex: 1 },
  spendingRight: { position: 'absolute', right: 0, top: 4, alignItems: 'flex-end' },
  spendingAmount: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' as any },
  spendingPercent: { fontSize: 10 },
  spendingBarBg: { height: 6, borderRadius: 3, overflow: 'hidden' },
  spendingBarFill: { height: '100%', borderRadius: 3 },

  // Recommendations
  recommendationCard: { borderRadius: 16, padding: 14, borderWidth: 1, borderLeftWidth: 4, marginBottom: 12 },
  recHeader: { flexDirection: 'row', gap: 12, marginBottom: 12 },
  recIcon: { width: 40, height: 40, borderRadius: 10, justifyContent: 'center', alignItems: 'center' },
  recInfo: { flex: 1 },
  recTitle: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700' as any, marginBottom: 4 },
  recDesc: { fontSize: 12, lineHeight: 18 },
  recFooter: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  impactBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 10, paddingVertical: 5, borderRadius: 10 },
  impactText: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '600' as any },
  sourceText: { fontSize: 10 },
});
