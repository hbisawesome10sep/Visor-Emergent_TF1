import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, RefreshControl,
  ActivityIndicator, Dimensions,
} from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useAuth } from '../../src/context/AuthContext';
import { useTheme } from '../../src/context/ThemeContext';
import { apiRequest } from '../../src/utils/api';
import { formatINRShort } from '../../src/utils/formatters';
import { Accent } from '../../src/utils/theme';
import AIAdvisorChat from '../../src/components/AIAdvisorChat';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

type DashboardStats = {
  total_income: number;
  total_expenses: number;
  total_investments: number;
  savings_rate: number;
  goal_progress: number;
  category_breakdown: Record<string, number>;
  health_score?: {
    overall: number;
    grade: string;
    has_sufficient_data?: boolean;
    breakdown: {
      savings: number;
      investments: number;
      spending: number;
      goals: number;
    };
    metrics?: {
      savings_rate: number;
      investment_rate: number;
      expense_ratio: number;
      goal_progress: number;
    };
  };
};

// Simple status helper - returns muted colors
function getStatusStyle(value: number, threshold: number, inverse: boolean = false) {
  const isGood = inverse ? value <= threshold : value >= threshold;
  return {
    color: isGood ? Accent.emerald : Accent.amber,
    label: isGood ? 'On Track' : 'Review',
  };
}

// Simple circular progress indicator
function CircularProgress({ 
  progress, 
  size = 80, 
  strokeWidth = 6,
  color,
  bgColor,
}: { 
  progress: number; 
  size?: number; 
  strokeWidth?: number;
  color: string;
  bgColor: string;
}) {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const strokeDashoffset = circumference - (Math.min(progress, 100) / 100) * circumference;

  return (
    <View style={{ width: size, height: size }}>
      <View style={[StyleSheet.absoluteFill, { justifyContent: 'center', alignItems: 'center' }]}>
        {/* Background circle */}
        <View style={{
          width: size - strokeWidth,
          height: size - strokeWidth,
          borderRadius: (size - strokeWidth) / 2,
          borderWidth: strokeWidth,
          borderColor: bgColor,
        }} />
      </View>
      <View style={[StyleSheet.absoluteFill, { justifyContent: 'center', alignItems: 'center' }]}>
        {/* Progress circle - simplified as a colored arc */}
        <View style={{
          width: size - strokeWidth,
          height: size - strokeWidth,
          borderRadius: (size - strokeWidth) / 2,
          borderWidth: strokeWidth,
          borderColor: color,
          borderTopColor: 'transparent',
          borderRightColor: progress > 25 ? color : 'transparent',
          borderBottomColor: progress > 50 ? color : 'transparent',
          borderLeftColor: progress > 75 ? color : 'transparent',
          transform: [{ rotate: '-45deg' }],
        }} />
      </View>
    </View>
  );
}

// Metric Card - Clean, minimal design
function MetricCard({
  title,
  value,
  subtitle,
  trend,
  trendLabel,
  icon,
  colors,
  isDark,
}: {
  title: string;
  value: string;
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendLabel?: string;
  icon: string;
  colors: any;
  isDark: boolean;
}) {
  const trendColor = trend === 'up' ? Accent.emerald : trend === 'down' ? Accent.ruby : colors.textSecondary;
  const trendIcon = trend === 'up' ? 'trending-up' : trend === 'down' ? 'trending-down' : 'minus';

  return (
    <View style={[styles.metricCard, { 
      backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
      borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)',
    }]}>
      <View style={styles.metricHeader}>
        <View style={[styles.metricIconContainer, { backgroundColor: `${Accent.sapphire}15` }]}>
          <MaterialCommunityIcons name={icon as any} size={18} color={Accent.sapphire} />
        </View>
        <Text style={[styles.metricTitle, { color: colors.textSecondary }]}>{title}</Text>
      </View>
      
      <Text style={[styles.metricValue, { color: colors.textPrimary }]}>{value}</Text>
      
      {subtitle && (
        <Text style={[styles.metricSubtitle, { color: colors.textSecondary }]}>{subtitle}</Text>
      )}
      
      {trendLabel && (
        <View style={styles.trendContainer}>
          <MaterialCommunityIcons name={trendIcon as any} size={14} color={trendColor} />
          <Text style={[styles.trendLabel, { color: trendColor }]}>{trendLabel}</Text>
        </View>
      )}
    </View>
  );
}

// Insight Card - Actionable recommendation
function InsightCard({
  icon,
  title,
  description,
  action,
  priority,
  colors,
  isDark,
}: {
  icon: string;
  title: string;
  description: string;
  action?: string;
  priority: 'high' | 'medium' | 'low';
  colors: any;
  isDark: boolean;
}) {
  const priorityColor = priority === 'high' ? Accent.amber : priority === 'medium' ? Accent.sapphire : Accent.emerald;

  return (
    <View style={[styles.insightCard, { 
      backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
      borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)',
      borderLeftColor: priorityColor,
    }]}>
      <View style={styles.insightHeader}>
        <View style={[styles.insightIconContainer, { backgroundColor: `${priorityColor}15` }]}>
          <MaterialCommunityIcons name={icon as any} size={20} color={priorityColor} />
        </View>
        <View style={styles.insightTitleContainer}>
          <Text style={[styles.insightTitle, { color: colors.textPrimary }]}>{title}</Text>
        </View>
      </View>
      
      <Text style={[styles.insightDescription, { color: colors.textSecondary }]}>
        {description}
      </Text>
      
      {action && (
        <View style={styles.insightAction}>
          <Text style={[styles.insightActionText, { color: priorityColor }]}>{action}</Text>
          <MaterialCommunityIcons name="chevron-right" size={16} color={priorityColor} />
        </View>
      )}
    </View>
  );
}

// Health Score Summary - Simple, clear
function HealthScoreSummary({
  score,
  grade,
  hasSufficientData,
  colors,
  isDark,
}: {
  score: number;
  grade: string;
  hasSufficientData: boolean;
  colors: any;
  isDark: boolean;
}) {
  const scoreColor = score >= 70 ? Accent.emerald : score >= 40 ? Accent.amber : Accent.ruby;

  if (!hasSufficientData) {
    return (
      <View style={[styles.healthScoreCard, { 
        backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
        borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)',
      }]}>
        <View style={styles.healthScoreContent}>
          <View style={[styles.noDataContainer]}>
            <MaterialCommunityIcons name="database-off-outline" size={32} color={colors.textSecondary} />
            <Text style={[styles.noDataTitle, { color: colors.textPrimary }]}>Add Income Data</Text>
            <Text style={[styles.noDataSubtitle, { color: colors.textSecondary }]}>
              Upload bank statements or add income transactions to calculate your financial health score.
            </Text>
          </View>
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.healthScoreCard, { 
      backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
      borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)',
    }]}>
      <View style={styles.healthScoreContent}>
        <View style={styles.healthScoreLeft}>
          <Text style={[styles.healthScoreLabel, { color: colors.textSecondary }]}>Financial Health</Text>
          <View style={styles.healthScoreValueRow}>
            <Text style={[styles.healthScoreValue, { color: scoreColor }]}>{Math.round(score)}</Text>
            <Text style={[styles.healthScoreMax, { color: colors.textSecondary }]}>/100</Text>
          </View>
          <View style={[styles.healthScoreBadge, { backgroundColor: `${scoreColor}15` }]}>
            <Text style={[styles.healthScoreGrade, { color: scoreColor }]}>{grade}</Text>
          </View>
        </View>
        
        <View style={styles.healthScoreRight}>
          <CircularProgress 
            progress={score} 
            size={70} 
            strokeWidth={5}
            color={scoreColor}
            bgColor={isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)'}
          />
        </View>
      </View>
    </View>
  );
}

// Spending Breakdown - Simple bar chart
function SpendingBreakdown({
  categories,
  totalExpenses,
  colors,
  isDark,
}: {
  categories: { category: string; amount: number }[];
  totalExpenses: number;
  colors: any;
  isDark: boolean;
}) {
  const categoryColors = [Accent.sapphire, Accent.emerald, Accent.amber, Accent.amethyst, Accent.rose, Accent.teal];

  if (categories.length === 0 || totalExpenses === 0) {
    return (
      <View style={[styles.spendingCard, { 
        backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
        borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)',
      }]}>
        <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Spending Breakdown</Text>
        <View style={styles.noDataSmall}>
          <Text style={[styles.noDataText, { color: colors.textSecondary }]}>No expense data for this period</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.spendingCard, { 
      backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
      borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)',
    }]}>
      <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Spending Breakdown</Text>
      
      {categories.slice(0, 5).map((cat, index) => {
        const percentage = (cat.amount / totalExpenses) * 100;
        const color = categoryColors[index % categoryColors.length];
        
        return (
          <View key={cat.category} style={styles.spendingRow}>
            <View style={styles.spendingLabelRow}>
              <View style={[styles.spendingDot, { backgroundColor: color }]} />
              <Text style={[styles.spendingCategory, { color: colors.textPrimary }]}>{cat.category}</Text>
              <Text style={[styles.spendingAmount, { color: colors.textSecondary }]}>₹{formatINRShort(cat.amount)}</Text>
            </View>
            <View style={[styles.spendingBarBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)' }]}>
              <View style={[styles.spendingBar, { width: `${percentage}%`, backgroundColor: color }]} />
            </View>
          </View>
        );
      })}
    </View>
  );
}

export default function InsightsScreen() {
  const { token } = useAuth();
  const { colors, isDark } = useTheme();
  const insets = useSafeAreaInsets();

  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showAI, setShowAI] = useState(false);
  const [selectedPeriod, setSelectedPeriod] = useState<'month' | 'quarter' | 'year'>('quarter');

  const getDateRange = useCallback(() => {
    const now = new Date();
    let start: Date;
    let end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    
    switch (selectedPeriod) {
      case 'month':
        start = new Date(now.getFullYear(), now.getMonth(), 1);
        break;
      case 'quarter':
        const quarterMonth = Math.floor(now.getMonth() / 3) * 3;
        start = new Date(now.getFullYear(), quarterMonth, 1);
        end = new Date(now.getFullYear(), quarterMonth + 3, 0);
        break;
      case 'year':
        // Indian Financial Year (April - March)
        if (now.getMonth() < 3) {
          start = new Date(now.getFullYear() - 1, 3, 1);
          end = new Date(now.getFullYear(), 2, 31);
        } else {
          start = new Date(now.getFullYear(), 3, 1);
          end = new Date(now.getFullYear() + 1, 2, 31);
        }
        break;
    }
    
    return {
      start: start.toISOString().split('T')[0],
      end: end.toISOString().split('T')[0],
    };
  }, [selectedPeriod]);

  const fetchData = useCallback(async () => {
    if (!token) return;
    
    try {
      const { start, end } = getDateRange();
      const data = await apiRequest(`/dashboard/stats?start_date=${start}&end_date=${end}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setStats(data);
    } catch (err) {
      console.error('Failed to fetch insights:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token, getDateRange]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchData();
  }, [fetchData]);

  // Calculate metrics
  const income = stats?.total_income || 0;
  const expenses = stats?.total_expenses || 0;
  const investments = stats?.total_investments || 0;
  const hasSufficientData = stats?.health_score?.has_sufficient_data ?? (income > 0);
  
  const savingsRate = hasSufficientData ? Math.min((income - expenses) / income * 100, 100) : 0;
  const investmentRate = hasSufficientData ? Math.min(investments / income * 100, 100) : 0;
  const expenseRate = hasSufficientData ? Math.min(expenses / income * 100, 200) : 0;
  
  const healthScore = stats?.health_score?.overall ?? 0;
  const healthGrade = stats?.health_score?.grade ?? 'No Data';

  // Spending breakdown
  const spendingData = Object.entries(stats?.category_breakdown || {})
    .map(([category, amount]) => ({ category, amount: amount as number }))
    .sort((a, b) => b.amount - a.amount);

  // Generate insights based on real data
  const insights = hasSufficientData ? [
    savingsRate < 20 && {
      icon: 'piggy-bank',
      title: 'Boost Your Savings',
      description: `You're saving ${savingsRate.toFixed(0)}% of income. Aim for 20%+ by automating transfers on payday.`,
      action: 'Set up auto-save',
      priority: 'high' as const,
    },
    investmentRate < 15 && {
      icon: 'chart-line',
      title: 'Grow Your Investments',
      description: `Only ${investmentRate.toFixed(0)}% goes to investments. Consider starting a SIP for long-term wealth.`,
      action: 'Explore SIP options',
      priority: 'medium' as const,
    },
    expenseRate > 70 && {
      icon: 'wallet-outline',
      title: 'Review Your Spending',
      description: `${expenseRate.toFixed(0)}% of income goes to expenses. Review subscriptions and discretionary spending.`,
      action: 'Analyze expenses',
      priority: 'high' as const,
    },
    savingsRate >= 20 && {
      icon: 'check-circle',
      title: 'Great Savings Habit!',
      description: `You're saving ${savingsRate.toFixed(0)}% of income. Keep it up!`,
      priority: 'low' as const,
    },
  ].filter(Boolean) : [
    {
      icon: 'bank-plus',
      title: 'Connect Your Accounts',
      description: 'Upload bank statements to unlock personalized financial insights and track your spending automatically.',
      action: 'Upload statement',
      priority: 'medium' as const,
    },
    {
      icon: 'cash-plus',
      title: 'Add Income',
      description: 'Add your income sources to calculate savings rate, investment ratio, and financial health score.',
      action: 'Add income',
      priority: 'medium' as const,
    },
  ];

  if (loading) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]} edges={['top']}>
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={[styles.scrollContent, { paddingBottom: insets.bottom + 100 }]}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />
        }
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={[styles.headerTitle, { color: colors.textPrimary }]}>Insights</Text>
          <Text style={[styles.headerSubtitle, { color: colors.textSecondary }]}>
            Your financial overview
          </Text>
        </View>

        {/* Period Selector */}
        <View style={styles.periodSelector}>
          {(['month', 'quarter', 'year'] as const).map((period) => (
            <TouchableOpacity
              key={period}
              style={[
                styles.periodButton,
                selectedPeriod === period && { backgroundColor: `${colors.primary}15` },
              ]}
              onPress={() => setSelectedPeriod(period)}
            >
              <Text style={[
                styles.periodButtonText,
                { color: selectedPeriod === period ? colors.primary : colors.textSecondary },
              ]}>
                {period === 'month' ? 'This Month' : period === 'quarter' ? 'Quarter' : 'FY'}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Health Score */}
        <HealthScoreSummary
          score={healthScore}
          grade={healthGrade}
          hasSufficientData={hasSufficientData}
          colors={colors}
          isDark={isDark}
        />

        {/* Key Metrics */}
        {hasSufficientData && (
          <View style={styles.metricsGrid}>
            <MetricCard
              title="Income"
              value={`₹${formatINRShort(income)}`}
              icon="cash-plus"
              colors={colors}
              isDark={isDark}
            />
            <MetricCard
              title="Expenses"
              value={`₹${formatINRShort(expenses)}`}
              subtitle={`${expenseRate.toFixed(0)}% of income`}
              icon="cash-minus"
              colors={colors}
              isDark={isDark}
            />
            <MetricCard
              title="Savings"
              value={`₹${formatINRShort(Math.max(0, income - expenses))}`}
              subtitle={`${savingsRate.toFixed(0)}% rate`}
              trend={savingsRate >= 20 ? 'up' : 'down'}
              trendLabel={savingsRate >= 20 ? 'On track' : 'Below target'}
              icon="piggy-bank"
              colors={colors}
              isDark={isDark}
            />
            <MetricCard
              title="Investments"
              value={`₹${formatINRShort(investments)}`}
              subtitle={`${investmentRate.toFixed(0)}% of income`}
              icon="chart-line"
              colors={colors}
              isDark={isDark}
            />
          </View>
        )}

        {/* Spending Breakdown */}
        <SpendingBreakdown
          categories={spendingData}
          totalExpenses={expenses}
          colors={colors}
          isDark={isDark}
        />

        {/* Insights */}
        <View style={styles.insightsSection}>
          <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>
            Recommendations
          </Text>
          
          {insights.map((insight: any, index) => (
            <InsightCard
              key={index}
              icon={insight.icon}
              title={insight.title}
              description={insight.description}
              action={insight.action}
              priority={insight.priority}
              colors={colors}
              isDark={isDark}
            />
          ))}
        </View>

        {/* AI Advisor Button */}
        <TouchableOpacity
          style={[styles.aiButton, { backgroundColor: colors.primary }]}
          onPress={() => setShowAI(true)}
        >
          <LinearGradient
            colors={[colors.primary, Accent.emerald]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.aiButtonGradient}
          >
            <MaterialCommunityIcons name="robot" size={22} color="#FFFFFF" />
            <Text style={styles.aiButtonText}>Ask Visor AI</Text>
            <MaterialCommunityIcons name="chevron-right" size={20} color="#FFFFFF" />
          </LinearGradient>
        </TouchableOpacity>
      </ScrollView>

      {/* AI Chat Modal */}
      {showAI && (
        <AIAdvisorChat
          visible={showAI}
          onClose={() => setShowAI(false)}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 16,
  },
  header: {
    marginBottom: 20,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: '700',
    letterSpacing: -0.5,
  },
  headerSubtitle: {
    fontSize: 15,
    marginTop: 4,
  },
  periodSelector: {
    flexDirection: 'row',
    marginBottom: 20,
    gap: 8,
  },
  periodButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
  },
  periodButtonText: {
    fontSize: 14,
    fontWeight: '500',
  },
  healthScoreCard: {
    borderRadius: 16,
    borderWidth: 1,
    padding: 20,
    marginBottom: 16,
  },
  healthScoreContent: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  healthScoreLeft: {
    flex: 1,
  },
  healthScoreLabel: {
    fontSize: 13,
    fontWeight: '500',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 8,
  },
  healthScoreValueRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
  },
  healthScoreValue: {
    fontSize: 42,
    fontWeight: '700',
    letterSpacing: -1,
  },
  healthScoreMax: {
    fontSize: 18,
    fontWeight: '500',
    marginLeft: 4,
  },
  healthScoreBadge: {
    alignSelf: 'flex-start',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
    marginTop: 8,
  },
  healthScoreGrade: {
    fontSize: 13,
    fontWeight: '600',
  },
  healthScoreRight: {
    marginLeft: 20,
  },
  noDataContainer: {
    alignItems: 'center',
    padding: 20,
  },
  noDataTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginTop: 12,
  },
  noDataSubtitle: {
    fontSize: 14,
    textAlign: 'center',
    marginTop: 8,
    lineHeight: 20,
  },
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: 16,
  },
  metricCard: {
    width: (SCREEN_WIDTH - 44) / 2,
    borderRadius: 12,
    borderWidth: 1,
    padding: 16,
  },
  metricHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  metricIconContainer: {
    width: 32,
    height: 32,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 8,
  },
  metricTitle: {
    fontSize: 12,
    fontWeight: '500',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  metricValue: {
    fontSize: 22,
    fontWeight: '700',
    letterSpacing: -0.5,
  },
  metricSubtitle: {
    fontSize: 12,
    marginTop: 4,
  },
  trendContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
  },
  trendLabel: {
    fontSize: 12,
    fontWeight: '500',
    marginLeft: 4,
  },
  spendingCard: {
    borderRadius: 16,
    borderWidth: 1,
    padding: 20,
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 16,
  },
  spendingRow: {
    marginBottom: 14,
  },
  spendingLabelRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
  },
  spendingDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 8,
  },
  spendingCategory: {
    flex: 1,
    fontSize: 14,
    fontWeight: '500',
  },
  spendingAmount: {
    fontSize: 14,
    fontWeight: '600',
  },
  spendingBarBg: {
    height: 6,
    borderRadius: 3,
    overflow: 'hidden',
  },
  spendingBar: {
    height: '100%',
    borderRadius: 3,
  },
  noDataSmall: {
    padding: 20,
    alignItems: 'center',
  },
  noDataText: {
    fontSize: 14,
  },
  insightsSection: {
    marginBottom: 16,
  },
  insightCard: {
    borderRadius: 12,
    borderWidth: 1,
    borderLeftWidth: 3,
    padding: 16,
    marginBottom: 12,
  },
  insightHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  insightIconContainer: {
    width: 36,
    height: 36,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  insightTitleContainer: {
    flex: 1,
  },
  insightTitle: {
    fontSize: 15,
    fontWeight: '600',
  },
  insightDescription: {
    fontSize: 14,
    lineHeight: 20,
  },
  insightAction: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 12,
  },
  insightActionText: {
    fontSize: 14,
    fontWeight: '600',
  },
  aiButton: {
    borderRadius: 16,
    overflow: 'hidden',
    marginTop: 8,
    marginBottom: 20,
  },
  aiButtonGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    paddingHorizontal: 24,
    gap: 10,
  },
  aiButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
    flex: 1,
    textAlign: 'center',
  },
});
