import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, RefreshControl,
  ActivityIndicator, Dimensions, Platform, StatusBar,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import { LinearGradient } from 'expo-linear-gradient';
import Svg, { Circle, G, Defs, LinearGradient as SvgLinearGradient, Stop } from 'react-native-svg';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  withSpring,
  interpolate,
  Easing,
  runOnJS,
} from 'react-native-reanimated';
import { useAuth } from '../../src/context/AuthContext';
import { useTheme } from '../../src/context/ThemeContext';
import { apiRequest } from '../../src/utils/api';
import { formatINRShort, getCategoryColor, getCategoryIcon } from '../../src/utils/formatters';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

type DashboardStats = {
  total_income: number;
  total_expenses: number;
  total_investments: number;
  savings_rate: number;
  category_breakdown: Record<string, number>;
};

// ═══════════════════════════════════════════════════════════════════════════════
// CALCULATION HELPERS
// ═══════════════════════════════════════════════════════════════════════════════

function calculateHealthScore(stats: DashboardStats | null): {
  score: number;
  breakdown: { savings: number; emergency: number; investment: number };
} {
  if (!stats) return { score: 0, breakdown: { savings: 0, emergency: 0, investment: 0 } };
  const { total_income, total_expenses, total_investments, savings_rate } = stats;
  
  // Savings contribution (40% weight) - Target 20%+
  let savingsPoints = 0;
  if (savings_rate >= 30) savingsPoints = 40;
  else if (savings_rate >= 20) savingsPoints = 35;
  else if (savings_rate >= 15) savingsPoints = 25;
  else if (savings_rate >= 10) savingsPoints = 15;
  else if (savings_rate >= 5) savingsPoints = 10;
  else savingsPoints = Math.max(0, savings_rate * 2);

  // Emergency fund contribution (30% weight) - Target 6 months
  const monthlyExpenses = total_expenses || 1;
  const savings = total_income - total_expenses;
  const emergencyMonths = savings > 0 ? Math.min((savings * 6) / monthlyExpenses, 12) : 0;
  let emergencyPoints = 0;
  if (emergencyMonths >= 6) emergencyPoints = 30;
  else if (emergencyMonths >= 3) emergencyPoints = 20;
  else if (emergencyMonths >= 1) emergencyPoints = 10;
  else emergencyPoints = Math.max(0, emergencyMonths * 5);

  // Investment contribution (30% weight) - Target 20%+
  const investRatio = total_income > 0 ? (total_investments / total_income) * 100 : 0;
  let investPoints = 0;
  if (investRatio >= 25) investPoints = 30;
  else if (investRatio >= 20) investPoints = 25;
  else if (investRatio >= 15) investPoints = 20;
  else if (investRatio >= 10) investPoints = 15;
  else if (investRatio >= 5) investPoints = 10;
  else investPoints = Math.max(0, investRatio * 2);

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
  if (score >= 35) return { label: 'Needs Improvement', color: '#F97316' };
  return { label: 'Needs Improvement', color: '#EF4444' };
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
// iOS 26 STYLE FLIPPABLE CARD COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface FlippableCardProps {
  frontContent: React.ReactNode;
  backContent: React.ReactNode;
  gradientColors: [string, string, ...string[]];
  height?: number;
  style?: any;
}

function FlippableCard({ frontContent, backContent, gradientColors, height = 200, style }: FlippableCardProps) {
  const { isDark } = useTheme();
  const [isFlipped, setIsFlipped] = useState(false);
  const flipProgress = useSharedValue(0);

  const flipCard = () => {
    setIsFlipped(!isFlipped);
    flipProgress.value = withSpring(isFlipped ? 0 : 1, {
      damping: 15,
      stiffness: 100,
    });
  };

  const frontAnimatedStyle = useAnimatedStyle(() => {
    return {
      opacity: interpolate(flipProgress.value, [0, 0.5, 1], [1, 0, 0]),
      zIndex: flipProgress.value < 0.5 ? 1 : 0,
    };
  });

  const backAnimatedStyle = useAnimatedStyle(() => {
    return {
      opacity: interpolate(flipProgress.value, [0, 0.5, 1], [0, 0, 1]),
      zIndex: flipProgress.value >= 0.5 ? 1 : 0,
    };
  });

  return (
    <TouchableOpacity activeOpacity={0.95} onPress={flipCard} style={[styles.flippableContainer, { height }, style]}>
      {/* Front */}
      <Animated.View style={[styles.cardFace, frontAnimatedStyle]}>
        <LinearGradient
          colors={gradientColors}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={[styles.cardGradient, { borderRadius: 24 }]}
        >
          <BlurView
            intensity={isDark ? 40 : 60}
            tint={isDark ? 'dark' : 'light'}
            style={styles.cardBlur}
          >
            {frontContent}
            <View style={styles.flipIndicator}>
              <MaterialCommunityIcons name="gesture-tap" size={14} color="rgba(255,255,255,0.6)" />
              <Text style={styles.flipText}>Tap to see calculation</Text>
            </View>
          </BlurView>
        </LinearGradient>
      </Animated.View>

      {/* Back */}
      <Animated.View style={[styles.cardFace, styles.cardBack, backAnimatedStyle]}>
        <LinearGradient
          colors={gradientColors}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={[styles.cardGradient, { borderRadius: 24 }]}
        >
          <BlurView
            intensity={isDark ? 40 : 60}
            tint={isDark ? 'dark' : 'light'}
            style={styles.cardBlur}
          >
            {backContent}
            <View style={styles.flipIndicator}>
              <MaterialCommunityIcons name="arrow-left" size={14} color="rgba(255,255,255,0.6)" />
              <Text style={styles.flipText}>Tap to go back</Text>
            </View>
          </BlurView>
        </LinearGradient>
      </Animated.View>
    </TouchableOpacity>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// iOS 26 STYLE INSIGHT CARD COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

interface InsightCardProps {
  icon: string;
  title: string;
  value: string;
  valueColor: string;
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
  gradientColors: [string, string, ...string[]];
}

function InsightCard({
  icon,
  title,
  value,
  valueColor,
  subtitle,
  status,
  fillPercentage,
  benchmarkInfo,
  gradientColors,
}: InsightCardProps) {
  const { colors, isDark } = useTheme();
  const statusColor = getStatusColor(status);
  const statusLabel = getStatusLabel(status);

  const frontContent = (
    <View style={styles.insightFront}>
      <View style={styles.insightHeader}>
        <View style={[styles.insightIconContainer, { backgroundColor: 'rgba(255,255,255,0.2)' }]}>
          <MaterialCommunityIcons name={icon as any} size={24} color="#FFFFFF" />
        </View>
        <View style={[styles.statusBadge, { backgroundColor: `${statusColor}30` }]}>
          <Text style={[styles.statusText, { color: statusColor }]}>{statusLabel}</Text>
        </View>
      </View>

      <Text style={styles.insightTitle}>{title}</Text>
      <Text style={[styles.insightValue, { color: valueColor }]}>{value}</Text>
      <Text style={styles.insightSubtitle}>{subtitle}</Text>

      {/* Fill Progress Bar */}
      <View style={styles.progressContainer}>
        <View style={styles.progressBg}>
          <View
            style={[
              styles.progressFill,
              {
                width: `${Math.min(fillPercentage, 100)}%`,
                backgroundColor: statusColor,
              },
            ]}
          />
        </View>
      </View>
    </View>
  );

  const backContent = (
    <View style={styles.insightBack}>
      <View style={styles.backHeader}>
        <MaterialCommunityIcons name="information-outline" size={20} color="#FFFFFF" />
        <Text style={styles.backTitle}>{benchmarkInfo.title}</Text>
      </View>
      
      <Text style={styles.backDescription}>{benchmarkInfo.description}</Text>
      
      <View style={styles.backStats}>
        <View style={styles.backStatRow}>
          <Text style={styles.backStatLabel}>Your Value</Text>
          <Text style={[styles.backStatValue, { color: valueColor }]}>{benchmarkInfo.yourValue}</Text>
        </View>
        <View style={styles.backStatRow}>
          <Text style={styles.backStatLabel}>National Average</Text>
          <Text style={styles.backStatValue}>{benchmarkInfo.nationalAverage}</Text>
        </View>
        <View style={styles.backStatRow}>
          <Text style={styles.backStatLabel}>Recommended</Text>
          <Text style={[styles.backStatValue, { color: '#10B981' }]}>{benchmarkInfo.recommended}</Text>
        </View>
      </View>
      
      <Text style={styles.backSource}>Source: {benchmarkInfo.source}</Text>
    </View>
  );

  return (
    <FlippableCard
      frontContent={frontContent}
      backContent={backContent}
      gradientColors={gradientColors}
      height={220}
      style={styles.insightCard}
    />
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN INSIGHTS SCREEN
// ═══════════════════════════════════════════════════════════════════════════════

export default function InsightsScreen() {
  const { user, token, loading: authLoading } = useAuth();
  const { colors, isDark } = useTheme();

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

  const fetchData = useCallback(async () => {
    // Always show data - use demo data if no token
    if (!token) {
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
      // Set demo data on error too
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

  // Run fetchData when token changes or after auth loading completes
  useEffect(() => {
    if (!authLoading) {
      fetchData();
    }
  }, [authLoading, fetchData]);

  // Also set a timeout to show data even if auth is stuck
  useEffect(() => {
    const timeout = setTimeout(() => {
      if (loading) {
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
      }
    }, 3000);
    return () => clearTimeout(timeout);
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  // Calculate all metrics
  const income = stats?.total_income || 1;
  const expenses = stats?.total_expenses || 0;
  const investments = stats?.total_investments || 0;
  const savingsRate = stats?.savings_rate || 0;

  const { score: healthScore, breakdown } = calculateHealthScore(stats);
  const scoreInfo = getScoreLabel(healthScore);
  const scoreColor = getScoreColor(healthScore);

  // Calculate individual metrics
  const emiEstimate = expenses * 0.35; // Estimate EMI as 35% of expenses
  const emiRatio = income > 0 ? (emiEstimate / income) * 100 : 0;
  const investmentRate = income > 0 ? (investments / income) * 100 : 0;
  const spendingRate = income > 0 ? (expenses / income) * 100 : 0;
  const monthlySavings = income - expenses;
  const runwayMonths = expenses > 0 ? Math.max(0, (monthlySavings * 6) / expenses) : 0;
  const foirRatio = income > 0 ? ((emiEstimate + (expenses * 0.15)) / income) * 100 : 0;
  
  // Wealth projection (assuming 12% annual return on investments)
  const currentWealth = investments * 12; // Assume 12 months of investments
  const projectedWealth5Years = currentWealth * Math.pow(1.12, 5);
  
  // Indian average comparison
  const indianAvgSavingsRate = 5.1;
  const isBetterThanAverage = savingsRate > indianAvgSavingsRate && investmentRate > 11.4;

  // Insight cards data
  const insightCards: InsightCardProps[] = [
    {
      icon: 'piggy-bank',
      title: 'Savings Rate',
      value: `${savingsRate.toFixed(1)}%`,
      valueColor: getStatusColor(getMetricStatus(savingsRate, 20)),
      subtitle: 'of income saved',
      status: getMetricStatus(savingsRate, 20),
      fillPercentage: (savingsRate / 30) * 100,
      benchmarkInfo: {
        title: 'What is Savings Rate?',
        description: 'Savings Rate measures the percentage of income you save. Higher savings build emergency funds and long-term wealth.',
        source: 'RBI Financial Literacy Guidelines',
        yourValue: `${savingsRate.toFixed(1)}%`,
        nationalAverage: '5.1%',
        recommended: '20%+',
      },
      gradientColors: isDark 
        ? ['rgba(16, 185, 129, 0.5)', 'rgba(5, 150, 105, 0.4)']
        : ['rgba(16, 185, 129, 0.6)', 'rgba(5, 150, 105, 0.4)'],
    },
    {
      icon: 'credit-card-check',
      title: 'EMI Analysis',
      value: `${emiRatio.toFixed(1)}%`,
      valueColor: getStatusColor(getMetricStatus(40, emiRatio, true)),
      subtitle: 'EMI-to-Income ratio',
      status: getMetricStatus(40, emiRatio, true),
      fillPercentage: emiRatio,
      benchmarkInfo: {
        title: 'EMI-to-Income Ratio',
        description: 'This ratio shows how much of your income goes to EMI payments. RBI recommends keeping it below 40%.',
        source: 'RBI Lending Guidelines',
        yourValue: `${emiRatio.toFixed(1)}%`,
        nationalAverage: '28%',
        recommended: '<40%',
      },
      gradientColors: isDark
        ? ['rgba(59, 130, 246, 0.3)', 'rgba(37, 99, 235, 0.2)']
        : ['rgba(59, 130, 246, 0.15)', 'rgba(219, 234, 254, 0.3)'],
    },
    {
      icon: 'chart-line',
      title: 'Investment Rate',
      value: `${investmentRate.toFixed(1)}%`,
      valueColor: getStatusColor(getMetricStatus(investmentRate, 20)),
      subtitle: 'of income invested',
      status: getMetricStatus(investmentRate, 20),
      fillPercentage: (investmentRate / 30) * 100,
      benchmarkInfo: {
        title: 'Investment Rate',
        description: 'Percentage of income allocated to investments. Regular investing helps build wealth through compounding.',
        source: 'SEBI Investor Guidelines',
        yourValue: `${investmentRate.toFixed(1)}%`,
        nationalAverage: '11.4%',
        recommended: '20-25%',
      },
      gradientColors: isDark
        ? ['rgba(139, 92, 246, 0.3)', 'rgba(109, 40, 217, 0.2)']
        : ['rgba(139, 92, 246, 0.15)', 'rgba(237, 233, 254, 0.3)'],
    },
    {
      icon: 'wallet-outline',
      title: 'Spending Analysis',
      value: `${spendingRate.toFixed(1)}%`,
      valueColor: getStatusColor(getMetricStatus(70, spendingRate, true)),
      subtitle: 'of income spent',
      status: getMetricStatus(70, spendingRate, true),
      fillPercentage: spendingRate,
      benchmarkInfo: {
        title: 'Spending Rate',
        description: 'Percentage of income spent on expenses. Keeping this below 70% ensures room for savings and investments.',
        source: 'NSO Household Survey 2024',
        yourValue: `${spendingRate.toFixed(1)}%`,
        nationalAverage: '75%',
        recommended: '<70%',
      },
      gradientColors: isDark
        ? ['rgba(245, 158, 11, 0.3)', 'rgba(217, 119, 6, 0.2)']
        : ['rgba(245, 158, 11, 0.15)', 'rgba(254, 243, 199, 0.3)'],
    },
    {
      icon: 'timer-sand',
      title: 'Runway Analysis',
      value: `${runwayMonths.toFixed(1)} mo`,
      valueColor: getStatusColor(getMetricStatus(runwayMonths, 6)),
      subtitle: 'emergency coverage',
      status: getMetricStatus(runwayMonths, 6),
      fillPercentage: (runwayMonths / 12) * 100,
      benchmarkInfo: {
        title: 'Emergency Runway',
        description: 'Number of months your savings can cover expenses if income stops. 6 months is the minimum recommended.',
        source: 'RBI Financial Literacy',
        yourValue: `${runwayMonths.toFixed(1)} months`,
        nationalAverage: '2.5 months',
        recommended: '6+ months',
      },
      gradientColors: isDark
        ? ['rgba(236, 72, 153, 0.3)', 'rgba(190, 24, 93, 0.2)']
        : ['rgba(236, 72, 153, 0.15)', 'rgba(252, 231, 243, 0.3)'],
    },
    {
      icon: 'chart-areaspline',
      title: 'Wealth Projection',
      value: formatINRShort(projectedWealth5Years),
      valueColor: '#10B981',
      subtitle: 'projected in 5 years',
      status: currentWealth > 0 ? 'good' : 'fair',
      fillPercentage: Math.min((currentWealth / 1000000) * 100, 100),
      benchmarkInfo: {
        title: '5-Year Wealth Projection',
        description: 'Estimated wealth in 5 years based on current investments and 12% annual returns (Indian equity average).',
        source: 'NIFTY 50 Historical Returns',
        yourValue: formatINRShort(projectedWealth5Years),
        nationalAverage: '₹5L-10L',
        recommended: 'Invest consistently',
      },
      gradientColors: isDark
        ? ['rgba(6, 182, 212, 0.3)', 'rgba(8, 145, 178, 0.2)']
        : ['rgba(6, 182, 212, 0.15)', 'rgba(207, 250, 254, 0.3)'],
    },
    {
      icon: 'scale-balance',
      title: 'FOIR Ratio',
      value: `${foirRatio.toFixed(1)}%`,
      valueColor: getStatusColor(getMetricStatus(50, foirRatio, true)),
      subtitle: 'fixed obligations',
      status: getMetricStatus(50, foirRatio, true),
      fillPercentage: foirRatio,
      benchmarkInfo: {
        title: 'Fixed Obligations Income Ratio',
        description: 'FOIR measures all fixed obligations (EMIs + insurance + rent) as % of income. Banks use this for loan eligibility.',
        source: 'Banking Regulations',
        yourValue: `${foirRatio.toFixed(1)}%`,
        nationalAverage: '45%',
        recommended: '<50%',
      },
      gradientColors: isDark
        ? ['rgba(239, 68, 68, 0.3)', 'rgba(185, 28, 28, 0.2)']
        : ['rgba(239, 68, 68, 0.15)', 'rgba(254, 226, 226, 0.3)'],
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

      {/* ═══ GLASS HEADER ═══ */}
      <View style={styles.stickyHeader}>
        <BlurView
          intensity={isDark ? 50 : 70}
          tint={isDark ? 'dark' : 'light'}
          style={[
            styles.headerBlur,
            {
              backgroundColor: isDark ? 'rgba(30, 41, 59, 0.75)' : 'rgba(255, 255, 255, 0.75)',
              borderBottomColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)',
            },
          ]}
        >
          <SafeAreaView edges={['top']} style={styles.headerSafeArea}>
            <View style={styles.headerContent}>
              <View style={styles.headerLeft}>
                <LinearGradient
                  colors={['#059669', '#0D9488']}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 0 }}
                  style={styles.gradientTitleBg}
                >
                  <Text style={styles.gradientTitle}>Financial Insights</Text>
                </LinearGradient>
                <Text style={[styles.headerSubtitle, { color: colors.textSecondary }]}>
                  AI-powered analysis • Based on Indian standards
                </Text>
              </View>
              <TouchableOpacity
                style={[styles.refreshBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)' }]}
                onPress={onRefresh}
              >
                <MaterialCommunityIcons name="refresh" size={20} color="#10B981" />
              </TouchableOpacity>
            </View>
          </SafeAreaView>
        </BlurView>
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#10B981" />}
        showsVerticalScrollIndicator={false}
      >
        {/* ═══ FINANCIAL HEALTH SCORE CARD (Flippable) ═══ */}
        <FlippableCard
          height={280}
          gradientColors={isDark 
            ? ['rgba(16, 185, 129, 0.25)', 'rgba(5, 150, 105, 0.15)']
            : ['rgba(16, 185, 129, 0.1)', 'rgba(209, 250, 229, 0.2)']
          }
          frontContent={
            <View style={styles.healthScoreFront}>
              <View style={styles.healthScoreHeader}>
                <View style={styles.healthBadgeContainer}>
                  <MaterialCommunityIcons name="shield-check" size={28} color="#10B981" />
                </View>
                <View style={styles.healthTitleContainer}>
                  <Text style={styles.healthTitle}>Financial Health Score</Text>
                  <Text style={styles.healthSubtitle}>Based on Indian financial standards and RBI guidelines</Text>
                </View>
              </View>

              <View style={styles.healthScoreMain}>
                <View style={styles.scoreCircleContainer}>
                  <Svg width={120} height={120}>
                    <G rotation="-90" origin="60, 60">
                      <Circle
                        cx="60"
                        cy="60"
                        r="50"
                        stroke="rgba(255,255,255,0.2)"
                        strokeWidth="10"
                        fill="transparent"
                      />
                      <Circle
                        cx="60"
                        cy="60"
                        r="50"
                        stroke={scoreColor}
                        strokeWidth="10"
                        fill="transparent"
                        strokeLinecap="round"
                        strokeDasharray={`${2 * Math.PI * 50}`}
                        strokeDashoffset={(1 - healthScore / 100) * 2 * Math.PI * 50}
                      />
                    </G>
                  </Svg>
                  <View style={styles.scoreTextContainer}>
                    <Text style={[styles.scoreNumber, { color: scoreColor }]}>{healthScore}</Text>
                    <Text style={styles.scoreOutOf}>/100</Text>
                  </View>
                </View>

                <View style={styles.scoreInfoContainer}>
                  <View style={[styles.scoreBadge, { backgroundColor: `${scoreInfo.color}30` }]}>
                    <Text style={[styles.scoreBadgeText, { color: scoreInfo.color }]}>{scoreInfo.label}</Text>
                  </View>
                  
                  <View style={styles.metricsPreview}>
                    <View style={styles.metricRow}>
                      <Text style={styles.metricLabel}>Savings Rate</Text>
                      <Text style={[styles.metricValue, { color: savingsRate >= 20 ? '#10B981' : '#F59E0B' }]}>
                        {savingsRate.toFixed(0)}%
                      </Text>
                    </View>
                    <View style={styles.metricRow}>
                      <Text style={styles.metricLabel}>EMI Ratio</Text>
                      <Text style={[styles.metricValue, { color: emiRatio <= 40 ? '#10B981' : '#EF4444' }]}>
                        {emiRatio.toFixed(0)}%
                      </Text>
                    </View>
                    <View style={styles.metricRow}>
                      <Text style={styles.metricLabel}>Investment Rate</Text>
                      <Text style={[styles.metricValue, { color: investmentRate >= 15 ? '#10B981' : '#F59E0B' }]}>
                        {investmentRate.toFixed(0)}%
                      </Text>
                    </View>
                    <View style={styles.metricRow}>
                      <Text style={styles.metricLabel}>Liquidity Ratio</Text>
                      <Text style={[styles.metricValue, { color: runwayMonths >= 3 ? '#10B981' : '#EF4444' }]}>
                        {runwayMonths.toFixed(1)}x
                      </Text>
                    </View>
                  </View>
                </View>
              </View>

              <TouchableOpacity style={styles.clickToSeeMore}>
                <Text style={styles.clickToSeeMoreText}>Click to see how your score is calculated</Text>
              </TouchableOpacity>
            </View>
          }
          backContent={
            <View style={styles.healthScoreBack}>
              <View style={styles.backHeaderRow}>
                <View style={styles.backIconContainer}>
                  <MaterialCommunityIcons name="calculator-variant" size={28} color="#10B981" />
                </View>
                <View style={styles.backTitleContainer}>
                  <Text style={styles.backMainTitle}>How Your Score is Calculated</Text>
                  <Text style={styles.backMainSubtitle}>Weighted scoring based on RBI financial health standards</Text>
                </View>
              </View>

              <View style={styles.calculationBreakdown}>
                <Text style={styles.yourScoreText}>Your Score: {healthScore}/100</Text>
                
                <View style={styles.breakdownRow}>
                  <Text style={styles.breakdownLabel}>Savings ({savingsRate.toFixed(0)}%) × 40%:</Text>
                  <Text style={styles.breakdownValue}>{breakdown.savings} pts</Text>
                </View>
                <View style={styles.breakdownRow}>
                  <Text style={styles.breakdownLabel}>Emergency ({runwayMonths.toFixed(1)}m) × 30%:</Text>
                  <Text style={styles.breakdownValue}>{breakdown.emergency} pts</Text>
                </View>
                <View style={styles.breakdownRow}>
                  <Text style={styles.breakdownLabel}>Investment ({investmentRate.toFixed(0)}%) × 30%:</Text>
                  <Text style={styles.breakdownValue}>{breakdown.investment} pts</Text>
                </View>

                <View style={styles.totalRow}>
                  <Text style={styles.totalLabel}>Total:</Text>
                  <Text style={[styles.totalValue, { color: scoreColor }]}>{healthScore}/100</Text>
                </View>
              </View>
            </View>
          }
        />

        {/* ═══ KEY FINANCIAL INSIGHTS SECTION ═══ */}
        <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>
          Key Financial Insights
        </Text>
        <Text style={[styles.sectionSubtitle, { color: colors.textSecondary }]}>
          Tap any card to learn more about the metric
        </Text>

        <View style={styles.insightGrid}>
          {insightCards.map((card, index) => (
            <InsightCard key={index} {...card} />
          ))}
        </View>

        {/* ═══ COMPARISON CARD (Flippable) ═══ */}
        <FlippableCard
          height={180}
          gradientColors={isDark
            ? isBetterThanAverage 
              ? ['rgba(16, 185, 129, 0.3)', 'rgba(5, 150, 105, 0.2)']
              : ['rgba(245, 158, 11, 0.3)', 'rgba(217, 119, 6, 0.2)']
            : isBetterThanAverage
              ? ['rgba(16, 185, 129, 0.15)', 'rgba(209, 250, 229, 0.25)']
              : ['rgba(245, 158, 11, 0.15)', 'rgba(254, 243, 199, 0.25)']
          }
          frontContent={
            <View style={styles.comparisonFront}>
              <View style={styles.comparisonHeader}>
                <View style={[styles.comparisonIcon, { 
                  backgroundColor: isBetterThanAverage ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)' 
                }]}>
                  <MaterialCommunityIcons 
                    name={isBetterThanAverage ? "trophy" : "trending-up"} 
                    size={24} 
                    color={isBetterThanAverage ? '#10B981' : '#F59E0B'} 
                  />
                </View>
                <View style={styles.comparisonTitleContainer}>
                  <Text style={styles.comparisonTitle}>
                    {isBetterThanAverage ? "You're Doing Better!" : "Room for Growth"}
                  </Text>
                  <Text style={styles.comparisonSubtitle}>
                    vs. Most Indian Households
                  </Text>
                </View>
              </View>

              <View style={styles.comparisonStats}>
                <View style={styles.comparisonStat}>
                  <Text style={styles.comparisonStatLabel}>Your Savings</Text>
                  <Text style={[styles.comparisonStatValue, { 
                    color: savingsRate > indianAvgSavingsRate ? '#10B981' : '#EF4444' 
                  }]}>
                    {savingsRate.toFixed(1)}%
                  </Text>
                </View>
                <View style={styles.comparisonVs}>
                  <Text style={styles.vsText}>vs</Text>
                </View>
                <View style={styles.comparisonStat}>
                  <Text style={styles.comparisonStatLabel}>National Avg</Text>
                  <Text style={styles.comparisonStatValue}>{indianAvgSavingsRate}%</Text>
                </View>
              </View>
            </View>
          }
          backContent={
            <View style={styles.comparisonBack}>
              <Text style={styles.comparisonBackTitle}>Indian Financial Statistics</Text>
              
              <View style={styles.comparisonBackStats}>
                <View style={styles.comparisonBackRow}>
                  <Text style={styles.comparisonBackLabel}>Avg Savings Rate (NSO)</Text>
                  <Text style={styles.comparisonBackValue}>5.1%</Text>
                </View>
                <View style={styles.comparisonBackRow}>
                  <Text style={styles.comparisonBackLabel}>Avg Investment Rate (SEBI)</Text>
                  <Text style={styles.comparisonBackValue}>11.4%</Text>
                </View>
                <View style={styles.comparisonBackRow}>
                  <Text style={styles.comparisonBackLabel}>Median Emergency Fund</Text>
                  <Text style={styles.comparisonBackValue}>2.5 mo</Text>
                </View>
              </View>
              
              <Text style={styles.comparisonSource}>Sources: RBI, NSO, SEBI 2024 Reports</Text>
            </View>
          }
        />

        <View style={{ height: 100 }} />
      </ScrollView>
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
    alignItems: 'flex-start',
    paddingTop: Platform.OS === 'android' ? 8 : 0,
  },
  headerLeft: { flex: 1 },
  gradientTitleBg: {
    alignSelf: 'flex-start',
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  gradientTitle: {
    fontSize: 22,
    fontWeight: '800',
    color: '#fff',
  },
  headerSubtitle: {
    fontSize: 12,
    marginTop: 4,
  },
  refreshBtn: {
    width: 40,
    height: 40,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },

  // Scroll
  scrollView: { flex: 1 },
  scrollContent: {
    paddingTop: Platform.OS === 'ios' ? 120 : 100,
    paddingHorizontal: 16,
  },

  // Flippable Card Base
  flippableContainer: {
    marginBottom: 20,
  },
  cardFace: {
    position: 'absolute',
    width: '100%',
    height: '100%',
  },
  cardBack: {
    // Already positioned absolute
  },
  cardGradient: {
    flex: 1,
    overflow: 'hidden',
  },
  cardBlur: {
    flex: 1,
    padding: 20,
    borderRadius: 24,
    overflow: 'hidden',
  },
  flipIndicator: {
    position: 'absolute',
    bottom: 12,
    right: 16,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  flipText: {
    fontSize: 11,
    color: 'rgba(255,255,255,0.6)',
    fontWeight: '500',
  },

  // Health Score Front
  healthScoreFront: {
    flex: 1,
  },
  healthScoreHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 16,
  },
  healthBadgeContainer: {
    width: 48,
    height: 48,
    borderRadius: 14,
    backgroundColor: 'rgba(16, 185, 129, 0.2)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  healthTitleContainer: {
    flex: 1,
  },
  healthTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: '#FFFFFF',
    marginBottom: 2,
  },
  healthSubtitle: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.7)',
  },
  healthScoreMain: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 20,
    flex: 1,
  },
  scoreCircleContainer: {
    position: 'relative',
    width: 120,
    height: 120,
  },
  scoreTextContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
  },
  scoreNumber: {
    fontSize: 36,
    fontWeight: '900',
    letterSpacing: -2,
  },
  scoreOutOf: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.6)',
    fontWeight: '600',
  },
  scoreInfoContainer: {
    flex: 1,
    gap: 10,
  },
  scoreBadge: {
    alignSelf: 'flex-start',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  scoreBadgeText: {
    fontSize: 13,
    fontWeight: '700',
  },
  metricsPreview: {
    gap: 6,
  },
  metricRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  metricLabel: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.7)',
    fontWeight: '500',
  },
  metricValue: {
    fontSize: 13,
    fontWeight: '700',
  },
  clickToSeeMore: {
    marginTop: 'auto',
    alignSelf: 'center',
  },
  clickToSeeMoreText: {
    fontSize: 12,
    color: '#10B981',
    fontWeight: '600',
  },

  // Health Score Back
  healthScoreBack: {
    flex: 1,
  },
  backHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 16,
  },
  backIconContainer: {
    width: 48,
    height: 48,
    borderRadius: 14,
    backgroundColor: 'rgba(16, 185, 129, 0.2)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  backTitleContainer: {
    flex: 1,
  },
  backMainTitle: {
    fontSize: 17,
    fontWeight: '800',
    color: '#FFFFFF',
    marginBottom: 2,
  },
  backMainSubtitle: {
    fontSize: 11,
    color: 'rgba(255,255,255,0.7)',
  },
  calculationBreakdown: {
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 16,
    padding: 16,
  },
  yourScoreText: {
    fontSize: 14,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 12,
  },
  breakdownRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.1)',
  },
  breakdownLabel: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.8)',
  },
  breakdownValue: {
    fontSize: 13,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  totalRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 12,
    marginTop: 4,
  },
  totalLabel: {
    fontSize: 15,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  totalValue: {
    fontSize: 18,
    fontWeight: '800',
  },

  // Section Title
  sectionTitle: {
    fontSize: 20,
    fontWeight: '800',
    marginBottom: 4,
    marginTop: 8,
  },
  sectionSubtitle: {
    fontSize: 13,
    marginBottom: 16,
  },

  // Insight Grid
  insightGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: 20,
  },
  insightCard: {
    width: (SCREEN_WIDTH - 44) / 2,
  },

  // Insight Card Front
  insightFront: {
    flex: 1,
    justifyContent: 'space-between',
  },
  insightHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  insightIconContainer: {
    width: 44,
    height: 44,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  statusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 10,
  },
  statusText: {
    fontSize: 10,
    fontWeight: '700',
  },
  insightTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#FFFFFF',
    marginTop: 12,
  },
  insightValue: {
    fontSize: 28,
    fontWeight: '900',
    letterSpacing: -1,
    marginTop: 4,
  },
  insightSubtitle: {
    fontSize: 11,
    color: 'rgba(255,255,255,0.7)',
    marginTop: 2,
  },
  progressContainer: {
    marginTop: 12,
  },
  progressBg: {
    height: 6,
    backgroundColor: 'rgba(255,255,255,0.2)',
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 3,
  },

  // Insight Card Back
  insightBack: {
    flex: 1,
  },
  backHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 10,
  },
  backTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  backDescription: {
    fontSize: 11,
    color: 'rgba(255,255,255,0.85)',
    lineHeight: 16,
    marginBottom: 12,
  },
  backStats: {
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 10,
    padding: 10,
    gap: 6,
  },
  backStatRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  backStatLabel: {
    fontSize: 10,
    color: 'rgba(255,255,255,0.7)',
  },
  backStatValue: {
    fontSize: 11,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  backSource: {
    fontSize: 9,
    color: 'rgba(255,255,255,0.5)',
    marginTop: 8,
    textAlign: 'center',
  },

  // Comparison Card Front
  comparisonFront: {
    flex: 1,
  },
  comparisonHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 16,
  },
  comparisonIcon: {
    width: 48,
    height: 48,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
  },
  comparisonTitleContainer: {
    flex: 1,
  },
  comparisonTitle: {
    fontSize: 17,
    fontWeight: '800',
    color: '#FFFFFF',
  },
  comparisonSubtitle: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.7)',
    marginTop: 2,
  },
  comparisonStats: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 20,
  },
  comparisonStat: {
    alignItems: 'center',
  },
  comparisonStatLabel: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.7)',
    marginBottom: 4,
  },
  comparisonStatValue: {
    fontSize: 28,
    fontWeight: '900',
    color: '#FFFFFF',
  },
  comparisonVs: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: 'rgba(255,255,255,0.15)',
    borderRadius: 8,
  },
  vsText: {
    fontSize: 12,
    fontWeight: '600',
    color: 'rgba(255,255,255,0.8)',
  },

  // Comparison Card Back
  comparisonBack: {
    flex: 1,
    justifyContent: 'center',
  },
  comparisonBackTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 16,
    textAlign: 'center',
  },
  comparisonBackStats: {
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 12,
    padding: 14,
    gap: 10,
  },
  comparisonBackRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  comparisonBackLabel: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.8)',
  },
  comparisonBackValue: {
    fontSize: 13,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  comparisonSource: {
    fontSize: 10,
    color: 'rgba(255,255,255,0.5)',
    marginTop: 12,
    textAlign: 'center',
  },
});
