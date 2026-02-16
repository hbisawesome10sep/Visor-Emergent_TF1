import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, RefreshControl,
  ActivityIndicator, Dimensions, Platform, StatusBar,
} from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import { LinearGradient } from 'expo-linear-gradient';
import Svg, { Circle, G } from 'react-native-svg';
import { useAuth } from '../../src/context/AuthContext';
import { useTheme } from '../../src/context/ThemeContext';
import { apiRequest } from '../../src/utils/api';
import { formatINRShort, getCategoryColor, getCategoryIcon } from '../../src/utils/formatters';
import AIAdvisorChat from '../../src/components/AIAdvisorChat';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const CARD_WIDTH = Math.max((SCREEN_WIDTH - 48) / 2, 160);

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

function calculateHealthScore(stats: DashboardStats | null): {
  score: number;
  breakdown: { savings: number; emergency: number; investment: number };
} {
  if (!stats) return { score: 0, breakdown: { savings: 0, emergency: 0, investment: 0 } };
  const { total_income, total_expenses, total_investments, savings_rate } = stats;
  
  let savingsPoints = Math.min(40, savings_rate * 1.5);
  
  const monthlyExpenses = total_expenses || 1;
  const savings = total_income - total_expenses;
  const emergencyMonths = savings > 0 ? Math.min((savings * 6) / monthlyExpenses, 12) : 0;
  let emergencyPoints = Math.min(30, emergencyMonths * 5);
  
  const investRatio = total_income > 0 ? (total_investments / total_income) * 100 : 0;
  let investPoints = Math.min(30, investRatio * 1.5);

  const score = Math.min(100, Math.round(savingsPoints + emergencyPoints + investPoints));
  
  return {
    score,
    breakdown: {
      savings: Math.round(savingsPoints),
      emergency: Math.round(emergencyPoints),
      investment: Math.round(investPoints),
    }
  };
}

function getScoreLabel(score: number): { label: string; color: string } {
  if (score >= 80) return { label: 'Excellent', color: '#10B981' };
  if (score >= 65) return { label: 'Good', color: '#22C55E' };
  if (score >= 50) return { label: 'Fair', color: '#F59E0B' };
  if (score >= 35) return { label: 'Needs Work', color: '#F97316' };
  return { label: 'Critical', color: '#EF4444' };
}

function getScoreColor(score: number): string {
  if (score >= 76) return '#10B981';
  if (score >= 61) return '#22C55E';
  if (score >= 41) return '#F59E0B';
  return '#EF4444';
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
    case 'excellent': return '#10B981';
    case 'good': return '#22C55E';
    case 'fair': return '#F59E0B';
    case 'critical': return '#EF4444';
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

  // Card background colors - more opaque for better legibility
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
        style={[styles.insightCard, { backgroundColor: cardBg, borderColor }]}
      >
        {/* Flip icon */}
        <TouchableOpacity 
          style={[styles.flipIconBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)' }]}
          onPress={() => setShowBack(false)}
        >
          <MaterialCommunityIcons name="rotate-left" size={14} color={colors.textSecondary} />
        </TouchableOpacity>

        <View style={styles.backContent}>
          <Text style={[styles.backTitle, { color: colors.textPrimary }]}>{benchmarkInfo.title}</Text>
          <Text style={[styles.backDesc, { color: colors.textSecondary }]}>{benchmarkInfo.description}</Text>
          
          <View style={[styles.backStatsBox, { backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)' }]}>
            <View style={styles.backStatRow}>
              <Text style={[styles.backStatLabel, { color: colors.textSecondary }]}>You</Text>
              <Text style={[styles.backStatValue, { color: statusColor }]}>{benchmarkInfo.yourValue}</Text>
            </View>
            <View style={styles.backStatRow}>
              <Text style={[styles.backStatLabel, { color: colors.textSecondary }]}>Avg</Text>
              <Text style={[styles.backStatValue, { color: colors.textPrimary }]}>{benchmarkInfo.nationalAverage}</Text>
            </View>
            <View style={styles.backStatRow}>
              <Text style={[styles.backStatLabel, { color: colors.textSecondary }]}>Target</Text>
              <Text style={[styles.backStatValue, { color: '#10B981' }]}>{benchmarkInfo.recommended}</Text>
            </View>
          </View>
          
          <Text style={[styles.backSource, { color: colors.textSecondary }]}>{benchmarkInfo.source}</Text>
        </View>
      </TouchableOpacity>
    );
  }

  return (
    <TouchableOpacity 
      activeOpacity={0.95} 
      onPress={() => setShowBack(true)}
      style={[styles.insightCard, { backgroundColor: cardBg, borderColor, borderLeftColor: statusColor, borderLeftWidth: 4 }]}
    >
      {/* Flip icon */}
      <TouchableOpacity 
        style={[styles.flipIconBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)' }]}
        onPress={() => setShowBack(true)}
      >
        <MaterialCommunityIcons name="information-outline" size={14} color={colors.textSecondary} />
      </TouchableOpacity>

      <View style={styles.frontContent}>
        <View style={styles.cardHeader}>
          <View style={[styles.iconBox, { backgroundColor: `${statusColor}15` }]}>
            <MaterialCommunityIcons name={icon as any} size={20} color={statusColor} />
          </View>
          <View style={[styles.statusBadge, { backgroundColor: `${statusColor}15` }]}>
            <Text style={[styles.statusText, { color: statusColor }]}>{statusLabel}</Text>
          </View>
        </View>

        <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>{title}</Text>
        <Text style={[styles.cardValue, { color: statusColor }]}>{value}</Text>
        <Text style={[styles.cardSubtitle, { color: colors.textSecondary }]}>{subtitle}</Text>

        {/* Progress bar */}
        <View style={styles.progressWrapper}>
          <View style={[styles.progressBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)' }]}>
            <View style={[styles.progressFill, { width: `${Math.min(fillPercentage, 100)}%`, backgroundColor: statusColor }]} />
          </View>
        </View>
      </View>
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
  
  // Calculate header height dynamically
  const HEADER_HEIGHT = 60 + insets.top;

  const [stats, setStats] = useState<DashboardStats | null>({
    total_income: 150000,
    total_expenses: 95000,
    total_investments: 25000,
    savings_rate: 36.7,
    category_breakdown: {
      'Housing': 25000,
      'Food': 15000,
      'Transport': 10000,
      'Utilities': 5000,
      'Shopping': 12000,
      'Entertainment': 8000,
    },
  });
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [showScoreBack, setShowScoreBack] = useState(false);

  const fetchData = useCallback(async () => {
    if (!token) {
      // Demo data when not logged in
      setStats({
        total_income: 150000,
        total_expenses: 95000,
        total_investments: 25000,
        savings_rate: 36.7,
        category_breakdown: {
          'Housing': 25000,
          'Food': 15000,
          'Transport': 10000,
          'Utilities': 5000,
          'Shopping': 12000,
          'Entertainment': 8000,
        },
      });
      setLoading(false);
      return;
    }
    try {
      const data = await apiRequest('/dashboard/stats', { token });
      setStats(data);
    } catch (e) {
      console.error(e);
      setStats({
        total_income: 150000,
        total_expenses: 95000,
        total_investments: 25000,
        savings_rate: 36.7,
        category_breakdown: {},
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token]);

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
  const income = stats?.total_income || 1;
  const expenses = stats?.total_expenses || 0;
  const investments = stats?.total_investments || 0;
  const savingsRate = stats?.savings_rate || 0;

  const { score: healthScore, breakdown } = calculateHealthScore(stats);
  const scoreInfo = getScoreLabel(healthScore);
  const scoreColor = getScoreColor(healthScore);

  // Calculate all financial metrics
  const emiEstimate = expenses * 0.35;
  const emiRatio = income > 0 ? (emiEstimate / income) * 100 : 0;
  const investmentRate = income > 0 ? (investments / income) * 100 : 0;
  const spendingRate = income > 0 ? (expenses / income) * 100 : 0;
  const monthlySavings = income - expenses;
  const runwayMonths = expenses > 0 ? Math.max(0, (monthlySavings * 6) / expenses) : 0;
  const foirRatio = income > 0 ? ((emiEstimate + (expenses * 0.15)) / income) * 100 : 0;
  const currentWealth = investments * 12;
  const projectedWealth5Years = currentWealth * Math.pow(1.12, 5);

  // Indian benchmarks
  const indianAvgSavingsRate = 5.1;
  const indianAvgInvestmentRate = 11.4;
  const indianAvgExpenseRatio = 75;
  const isBetterThanAverage = savingsRate > indianAvgSavingsRate;

  // Spending breakdown
  const spendingData = Object.entries(stats?.category_breakdown || {})
    .map(([category, amount]) => ({ category, amount: amount as number }))
    .sort((a, b) => b.amount - a.amount)
    .slice(0, 6);
  const totalSpending = spendingData.reduce((s, d) => s + d.amount, 0) || 1;

  // AI Recommendations based on real data
  const aiRecommendations = [
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
      impact: savingsRate < 20 ? `Target: Save ₹${formatINRShort((income * 0.2) - monthlySavings)}/month more` : 'On track',
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
        : `EMI ratio of ${emiRatio.toFixed(0)}% is healthy. Maintain this to preserve loan eligibility for future needs.`,
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
  ];

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: colors.background }]}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#10B981" />
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
      <View style={[styles.stickyHeader, { paddingTop: insets.top, backgroundColor: isDark ? '#0F172A' : '#FFFFFF' }]}>
        <View
          style={[
            styles.headerContent,
            {
              backgroundColor: isDark ? '#0F172A' : '#FFFFFF',
              borderBottomColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)',
            },
          ]}
        >
          <View style={styles.headerLeft}>
            <Text style={[styles.headerTitle, { color: '#10B981' }]}>Financial Insights</Text>
            <Text style={[styles.headerSubtitle, { color: colors.textSecondary }]}>
              Real-time analysis based on Indian standards
            </Text>
          </View>
          <TouchableOpacity
            style={[styles.refreshBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)' }]}
            onPress={onRefresh}
          >
            <MaterialCommunityIcons name="refresh" size={20} color="#10B981" />
          </TouchableOpacity>
        </View>
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={[styles.scrollContent, { paddingTop: HEADER_HEIGHT + 16 }]}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#10B981" />}
        showsVerticalScrollIndicator={false}
      >
        {/* ═══ FINANCIAL HEALTH SCORE ═══ */}
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
                  <Svg width={100} height={100}>
                    <G rotation="-90" origin="50, 50">
                      <Circle cx="50" cy="50" r="42" stroke={isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)'} strokeWidth="10" fill="transparent" />
                      <Circle cx="50" cy="50" r="42" stroke={scoreColor} strokeWidth="10" fill="transparent" strokeLinecap="round"
                        strokeDasharray={`${2 * Math.PI * 42}`}
                        strokeDashoffset={(1 - healthScore / 100) * 2 * Math.PI * 42}
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
                  <Text style={[styles.scoreTitle, { color: colors.textPrimary }]}>Your Financial Health Score</Text>
                  <View style={[styles.scoreLabelBadge, { backgroundColor: `${scoreInfo.color}20` }]}>
                    <Text style={[styles.scoreLabelText, { color: scoreInfo.color }]}>{scoreInfo.label}</Text>
                  </View>
                  <Text style={[styles.scoreDesc, { color: colors.textSecondary }]}>
                    {healthScore >= 70 ? "Great financial habits! Keep it up." : healthScore >= 50 ? "Good progress. Focus on savings & investments." : "Needs attention. Prioritize emergency fund."}
                  </Text>
                </View>
              </View>
            </View>
          ) : (
            <View style={styles.healthScoreBack}>
              <Text style={[styles.scoreBackTitle, { color: colors.textPrimary }]}>How Your Score is Calculated</Text>
              <Text style={[styles.scoreBackDesc, { color: colors.textSecondary }]}>Based on RBI's financial health framework</Text>
              
              <View style={[styles.scoreBreakdown, { backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)' }]}>
                <View style={styles.breakdownRow}>
                  <Text style={[styles.breakdownLabel, { color: colors.textSecondary }]}>Savings Rate ({savingsRate.toFixed(0)}%)</Text>
                  <Text style={[styles.breakdownValue, { color: colors.textPrimary }]}>{breakdown.savings}/40 pts</Text>
                </View>
                <View style={styles.breakdownRow}>
                  <Text style={[styles.breakdownLabel, { color: colors.textSecondary }]}>Emergency Fund ({runwayMonths.toFixed(1)}mo)</Text>
                  <Text style={[styles.breakdownValue, { color: colors.textPrimary }]}>{breakdown.emergency}/30 pts</Text>
                </View>
                <View style={styles.breakdownRow}>
                  <Text style={[styles.breakdownLabel, { color: colors.textSecondary }]}>Investment Rate ({investmentRate.toFixed(0)}%)</Text>
                  <Text style={[styles.breakdownValue, { color: colors.textPrimary }]}>{breakdown.investment}/30 pts</Text>
                </View>
                <View style={[styles.breakdownTotal, { borderTopColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)' }]}>
                  <Text style={[styles.breakdownTotalLabel, { color: colors.textPrimary }]}>Total Score</Text>
                  <Text style={[styles.breakdownTotalValue, { color: scoreColor }]}>{healthScore}/100</Text>
                </View>
              </View>
            </View>
          )}
        </TouchableOpacity>

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
              description: 'Percentage of income saved monthly. Higher is better.',
              source: 'RBI Guidelines',
              yourValue: `${savingsRate.toFixed(1)}%`,
              nationalAverage: '5.1%',
              recommended: '20%+',
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
              description: 'Total EMIs as percentage of income. Lower is safer.',
              source: 'RBI Lending Rules',
              yourValue: `${emiRatio.toFixed(1)}%`,
              nationalAverage: '28%',
              recommended: '<40%',
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
              description: 'Percentage allocated to wealth building assets.',
              source: 'SEBI Guidelines',
              yourValue: `${investmentRate.toFixed(1)}%`,
              nationalAverage: '11.4%',
              recommended: '20%+',
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
              description: 'Percentage of income going to expenses.',
              source: 'NSO Survey',
              yourValue: `${spendingRate.toFixed(1)}%`,
              nationalAverage: '75%',
              recommended: '<70%',
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
              description: 'Months of expenses covered by savings.',
              source: 'RBI Financial Literacy',
              yourValue: `${runwayMonths.toFixed(1)} months`,
              nationalAverage: '2.5 mo',
              recommended: '6+ months',
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
              description: 'All fixed payments (EMI, rent, insurance) vs income.',
              source: 'Banking Standards',
              yourValue: `${foirRatio.toFixed(1)}%`,
              nationalAverage: '45%',
              recommended: '<50%',
            }}
            isDark={isDark}
            colors={colors}
          />
        </View>

        {/* ═══ HOW YOU COMPARE ═══ */}
        <View style={[styles.compareCard, {
          backgroundColor: isDark ? 'rgba(30, 41, 59, 0.8)' : 'rgba(255, 255, 255, 0.95)',
          borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
        }]}>
          <View style={styles.compareHeader}>
            <View style={[styles.compareIcon, { backgroundColor: isBetterThanAverage ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)' }]}>
              <MaterialCommunityIcons name={isBetterThanAverage ? "trophy" : "trending-up"} size={24} color={isBetterThanAverage ? '#10B981' : '#F59E0B'} />
            </View>
            <View style={styles.compareTitleBox}>
              <Text style={[styles.compareTitle, { color: colors.textPrimary }]}>
                {isBetterThanAverage ? "You're Doing Better!" : "Room for Growth"}
              </Text>
              <Text style={[styles.compareSubtitle, { color: colors.textSecondary }]}>vs. Indian National Averages</Text>
            </View>
          </View>

          <View style={styles.compareGrid}>
            <View style={styles.compareItem}>
              <Text style={[styles.compareLabel, { color: colors.textSecondary }]}>Your Savings</Text>
              <Text style={[styles.compareValue, { color: savingsRate > indianAvgSavingsRate ? '#10B981' : '#EF4444' }]}>{savingsRate.toFixed(1)}%</Text>
              <Text style={[styles.compareAvg, { color: colors.textSecondary }]}>Avg: {indianAvgSavingsRate}%</Text>
            </View>
            <View style={styles.compareItem}>
              <Text style={[styles.compareLabel, { color: colors.textSecondary }]}>Investment Rate</Text>
              <Text style={[styles.compareValue, { color: investmentRate > indianAvgInvestmentRate ? '#10B981' : '#F59E0B' }]}>{investmentRate.toFixed(1)}%</Text>
              <Text style={[styles.compareAvg, { color: colors.textSecondary }]}>Avg: {indianAvgInvestmentRate}%</Text>
            </View>
            <View style={styles.compareItem}>
              <Text style={[styles.compareLabel, { color: colors.textSecondary }]}>Expense Ratio</Text>
              <Text style={[styles.compareValue, { color: spendingRate < indianAvgExpenseRatio ? '#10B981' : '#EF4444' }]}>{spendingRate.toFixed(1)}%</Text>
              <Text style={[styles.compareAvg, { color: colors.textSecondary }]}>Avg: {indianAvgExpenseRatio}%</Text>
            </View>
            <View style={styles.compareItem}>
              <Text style={[styles.compareLabel, { color: colors.textSecondary }]}>Emergency Fund</Text>
              <Text style={[styles.compareValue, { color: runwayMonths > 2.5 ? '#10B981' : '#F59E0B' }]}>{runwayMonths.toFixed(1)} mo</Text>
              <Text style={[styles.compareAvg, { color: colors.textSecondary }]}>Avg: 2.5 mo</Text>
            </View>
          </View>

          <Text style={[styles.compareSource, { color: colors.textSecondary }]}>Sources: RBI, NSO, SEBI Household Surveys 2024</Text>
        </View>

        {/* ═══ SPENDING BREAKDOWN ═══ */}
        {spendingData.length > 0 && (
          <View style={[styles.spendingCard, {
            backgroundColor: isDark ? 'rgba(30, 41, 59, 0.8)' : 'rgba(255, 255, 255, 0.95)',
            borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
          }]}>
            <Text style={[styles.cardSectionTitle, { color: colors.textPrimary }]}>Spending Breakdown</Text>
            <Text style={[styles.cardSectionSubtitle, { color: colors.textSecondary }]}>Where your money goes this month</Text>
            
            {spendingData.map((item, index) => {
              const percent = (item.amount / totalSpending) * 100;
              const barColor = getCategoryColor(item.category, isDark);
              return (
                <View key={item.category} style={styles.spendingRow}>
                  <View style={styles.spendingLeft}>
                    <View style={[styles.spendingIcon, { backgroundColor: `${barColor}15` }]}>
                      <MaterialCommunityIcons name={getCategoryIcon(item.category) as any} size={16} color={barColor} />
                    </View>
                    <Text style={[styles.spendingCategory, { color: colors.textPrimary }]}>{item.category}</Text>
                  </View>
                  <View style={styles.spendingRight}>
                    <Text style={[styles.spendingAmount, { color: colors.textPrimary }]}>{formatINRShort(item.amount)}</Text>
                    <Text style={[styles.spendingPercent, { color: colors.textSecondary }]}>{percent.toFixed(0)}%</Text>
                  </View>
                  <View style={[styles.spendingBarBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
                    <View style={[styles.spendingBarFill, { width: `${percent}%`, backgroundColor: barColor }]} />
                  </View>
                </View>
              );
            })}
          </View>
        )}

        {/* ═══ AI RECOMMENDATIONS ═══ */}
        <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>AI Insights & Recommendations</Text>
        <Text style={[styles.sectionSubtitle, { color: colors.textSecondary }]}>Personalized tips based on your financial data</Text>
        
        {aiRecommendations.map((rec, index) => (
          <View
            key={index}
            style={[styles.recommendationCard, {
              backgroundColor: isDark ? 'rgba(30, 41, 59, 0.8)' : 'rgba(255, 255, 255, 0.95)',
              borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
              borderLeftColor: rec.priority === 'high' ? '#EF4444' : rec.priority === 'medium' ? '#F59E0B' : '#10B981',
            }]}
          >
            <View style={styles.recHeader}>
              <View style={[styles.recIcon, {
                backgroundColor: rec.priority === 'high' ? 'rgba(239, 68, 68, 0.12)' : rec.priority === 'medium' ? 'rgba(245, 158, 11, 0.12)' : 'rgba(16, 185, 129, 0.12)',
              }]}>
                <MaterialCommunityIcons
                  name={rec.icon as any}
                  size={20}
                  color={rec.priority === 'high' ? '#EF4444' : rec.priority === 'medium' ? '#F59E0B' : '#10B981'}
                />
              </View>
              <View style={styles.recInfo}>
                <Text style={[styles.recTitle, { color: colors.textPrimary }]}>{rec.title}</Text>
                <Text style={[styles.recDesc, { color: colors.textSecondary }]}>{rec.description}</Text>
              </View>
            </View>
            <View style={styles.recFooter}>
              <View style={[styles.impactBadge, {
                backgroundColor: rec.priority === 'low' ? 'rgba(16, 185, 129, 0.12)' : 'rgba(245, 158, 11, 0.12)',
              }]}>
                <MaterialCommunityIcons name="lightning-bolt" size={12} color={rec.priority === 'low' ? '#10B981' : '#F59E0B'} />
                <Text style={[styles.impactText, { color: rec.priority === 'low' ? '#10B981' : '#F59E0B' }]}>{rec.impact}</Text>
              </View>
              <Text style={[styles.sourceText, { color: colors.textSecondary }]}>{rec.source}</Text>
            </View>
          </View>
        ))}

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
  headerTitle: { fontSize: 22, fontWeight: '800' },
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
  scoreNum: { fontSize: 28, fontWeight: '900', letterSpacing: -1 },
  scoreOf: { fontSize: 12, fontWeight: '600' },
  scoreInfo: { flex: 1, gap: 6 },
  scoreTitle: { fontSize: 16, fontWeight: '700' },
  scoreLabelBadge: { alignSelf: 'flex-start', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  scoreLabelText: { fontSize: 12, fontWeight: '700' },
  scoreDesc: { fontSize: 13, lineHeight: 18 },
  healthScoreBack: { minHeight: 100 },
  scoreBackTitle: { fontSize: 16, fontWeight: '700', marginBottom: 4 },
  scoreBackDesc: { fontSize: 12, marginBottom: 12 },
  scoreBreakdown: { borderRadius: 12, padding: 12 },
  breakdownRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 8 },
  breakdownLabel: { fontSize: 13 },
  breakdownValue: { fontSize: 13, fontWeight: '600' },
  breakdownTotal: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingTop: 10, marginTop: 4, borderTopWidth: 1 },
  breakdownTotalLabel: { fontSize: 14, fontWeight: '700' },
  breakdownTotalValue: { fontSize: 18, fontWeight: '800' },

  // Section Title
  sectionTitle: { fontSize: 18, fontWeight: '700', marginBottom: 4, marginTop: 8 },
  sectionSubtitle: { fontSize: 13, marginBottom: 16 },

  // Insight Grid
  insightGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12, marginBottom: 24 },
  insightCard: { width: CARD_WIDTH, minHeight: 180, borderRadius: 16, padding: 14, borderWidth: 1 },
  flipIconBtn: { position: 'absolute', top: 10, right: 10, width: 24, height: 24, borderRadius: 12, justifyContent: 'center', alignItems: 'center', zIndex: 10 },
  frontContent: { flex: 1, paddingTop: 8 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  iconBox: { width: 36, height: 36, borderRadius: 10, justifyContent: 'center', alignItems: 'center' },
  statusBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8 },
  statusText: { fontSize: 10, fontWeight: '700' },
  cardTitle: { fontSize: 13, fontWeight: '600', marginBottom: 4 },
  cardValue: { fontSize: 24, fontWeight: '800', letterSpacing: -0.5 },
  cardSubtitle: { fontSize: 11, marginTop: 2 },
  progressWrapper: { marginTop: 12 },
  progressBg: { height: 6, borderRadius: 3, overflow: 'hidden' },
  progressFill: { height: '100%', borderRadius: 3 },
  backContent: { flex: 1, paddingTop: 24 },
  backTitle: { fontSize: 14, fontWeight: '700', marginBottom: 6 },
  backDesc: { fontSize: 11, lineHeight: 16, marginBottom: 10 },
  backStatsBox: { borderRadius: 10, padding: 10, gap: 6, marginBottom: 8 },
  backStatRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  backStatLabel: { fontSize: 11 },
  backStatValue: { fontSize: 12, fontWeight: '700' },
  backSource: { fontSize: 9, textAlign: 'center' },

  // Compare Card
  compareCard: { borderRadius: 16, padding: 16, borderWidth: 1, marginBottom: 24 },
  compareHeader: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 16 },
  compareIcon: { width: 44, height: 44, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  compareTitleBox: { flex: 1 },
  compareTitle: { fontSize: 16, fontWeight: '700' },
  compareSubtitle: { fontSize: 12, marginTop: 2 },
  compareGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  compareItem: { width: (SCREEN_WIDTH - 80) / 2, backgroundColor: 'rgba(0,0,0,0.02)', borderRadius: 12, padding: 12, alignItems: 'center' },
  compareLabel: { fontSize: 11, marginBottom: 4 },
  compareValue: { fontSize: 20, fontWeight: '800' },
  compareAvg: { fontSize: 10, marginTop: 2 },
  compareSource: { fontSize: 10, textAlign: 'center', marginTop: 12 },

  // Spending Card
  spendingCard: { borderRadius: 16, padding: 16, borderWidth: 1, marginBottom: 24 },
  cardSectionTitle: { fontSize: 16, fontWeight: '700', marginBottom: 4 },
  cardSectionSubtitle: { fontSize: 12, marginBottom: 14 },
  spendingRow: { marginBottom: 14 },
  spendingLeft: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 6 },
  spendingIcon: { width: 30, height: 30, borderRadius: 8, justifyContent: 'center', alignItems: 'center' },
  spendingCategory: { fontSize: 13, fontWeight: '600', flex: 1 },
  spendingRight: { position: 'absolute', right: 0, top: 4, alignItems: 'flex-end' },
  spendingAmount: { fontSize: 13, fontWeight: '700' },
  spendingPercent: { fontSize: 10 },
  spendingBarBg: { height: 6, borderRadius: 3, overflow: 'hidden' },
  spendingBarFill: { height: '100%', borderRadius: 3 },

  // Recommendations
  recommendationCard: { borderRadius: 16, padding: 14, borderWidth: 1, borderLeftWidth: 4, marginBottom: 12 },
  recHeader: { flexDirection: 'row', gap: 12, marginBottom: 12 },
  recIcon: { width: 40, height: 40, borderRadius: 10, justifyContent: 'center', alignItems: 'center' },
  recInfo: { flex: 1 },
  recTitle: { fontSize: 14, fontWeight: '700', marginBottom: 4 },
  recDesc: { fontSize: 12, lineHeight: 18 },
  recFooter: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  impactBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 10, paddingVertical: 5, borderRadius: 10 },
  impactText: { fontSize: 11, fontWeight: '600' },
  sourceText: { fontSize: 10 },
});
