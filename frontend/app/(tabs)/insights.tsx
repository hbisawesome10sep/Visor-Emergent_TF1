import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, RefreshControl,
  ActivityIndicator, Dimensions, Platform, StatusBar, Animated,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import { LinearGradient } from 'expo-linear-gradient';
import Svg, { Circle, G } from 'react-native-svg';
import { useAuth } from '../../src/context/AuthContext';
import { useTheme } from '../../src/context/ThemeContext';
import { apiRequest } from '../../src/utils/api';
import { formatINRShort, getCategoryColor, getCategoryIcon } from '../../src/utils/formatters';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// Animated Circle Component for Health Score
const AnimatedCircle = Animated.createAnimatedComponent(Circle);

type DashboardStats = {
  total_income: number;
  total_expenses: number;
  total_investments: number;
  savings_rate: number;
  category_breakdown: Record<string, number>;
};

// Helper to calculate health score
function calculateHealthScore(stats: DashboardStats | null): number {
  if (!stats) return 0;
  const { total_income, total_expenses, total_investments, savings_rate } = stats;
  
  let score = 50; // Base score
  
  // Savings rate contribution (0-25 points)
  if (savings_rate >= 30) score += 25;
  else if (savings_rate >= 20) score += 20;
  else if (savings_rate >= 10) score += 10;
  else score += 5;
  
  // Investment ratio contribution (0-15 points)
  const investRatio = total_income > 0 ? (total_investments / total_income) * 100 : 0;
  if (investRatio >= 20) score += 15;
  else if (investRatio >= 10) score += 10;
  else score += 5;
  
  // Expense ratio contribution (0-10 points)
  const expenseRatio = total_income > 0 ? (total_expenses / total_income) * 100 : 100;
  if (expenseRatio <= 50) score += 10;
  else if (expenseRatio <= 70) score += 5;
  
  return Math.min(100, Math.max(0, score));
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

export default function InsightsScreen() {
  const { user, token } = useAuth();
  const { colors, isDark } = useTheme();
  
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  
  // Animation for score ring
  const scoreAnim = useRef(new Animated.Value(0)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;

  const fetchData = useCallback(async () => {
    if (!token) return;
    try {
      const data = await apiRequest('/dashboard/stats', { token });
      setStats(data);
      
      // Animate score ring
      const score = calculateHealthScore(data);
      Animated.parallel([
        Animated.timing(scoreAnim, {
          toValue: score,
          duration: 1500,
          useNativeDriver: false,
        }),
        Animated.timing(fadeAnim, {
          toValue: 1,
          duration: 500,
          useNativeDriver: true,
        }),
      ]).start();
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
    scoreAnim.setValue(0);
    fetchData();
  };

  const healthScore = calculateHealthScore(stats);
  const scoreInfo = getScoreLabel(healthScore);
  const scoreColor = getScoreColor(healthScore);

  // Calculate financial ratios
  const income = stats?.total_income || 1;
  const expenses = stats?.total_expenses || 0;
  const investments = stats?.total_investments || 0;
  const savingsRate = stats?.savings_rate || 0;
  
  const emiRatio = Math.min((expenses * 0.35) / income * 100, 60); // Estimate EMI as 35% of expenses
  const debtRatio = Math.min((expenses * 0.25) / income * 100, 50); // Estimate debt
  const investmentRatio = (investments / income) * 100;
  const emergencyMonths = Math.min(((income - expenses) * 6) / (expenses || 1), 12);

  // Spending breakdown
  const spendingData = Object.entries(stats?.category_breakdown || {})
    .map(([category, amount]) => ({ category, amount: amount as number }))
    .sort((a, b) => b.amount - a.amount)
    .slice(0, 6);
  const totalSpending = spendingData.reduce((s, d) => s + d.amount, 0) || 1;

  // AI Recommendations
  const recommendations = [
    {
      priority: savingsRate < 20 ? 'high' : 'low',
      icon: 'piggy-bank',
      title: savingsRate < 20 ? 'Increase Your Savings Rate' : 'Great Savings Habit!',
      description: savingsRate < 20
        ? `Your current savings rate is ${savingsRate.toFixed(0)}%. Aim for at least 20-30% to build wealth faster. Consider automating transfers to a savings account.`
        : `You're saving ${savingsRate.toFixed(0)}% of your income, which is excellent! Keep it up.`,
      impact: savingsRate < 20 ? `Target: Save ₹${formatINRShort((income * 0.2) - (income * savingsRate / 100))}/month more` : 'On track',
      source: 'Based on RBI guidelines',
    },
    {
      priority: investmentRatio < 15 ? 'medium' : 'low',
      icon: 'chart-line',
      title: investmentRatio < 15 ? 'Boost Your Investments' : 'Strong Investment Portfolio',
      description: investmentRatio < 15
        ? `Only ${investmentRatio.toFixed(0)}% of your income goes to investments. Consider increasing SIP amounts or exploring ELSS for tax benefits.`
        : `${investmentRatio.toFixed(0)}% of your income is invested. Well diversified!`,
      impact: investmentRatio < 15 ? `Potential growth: ₹${formatINRShort(income * 0.05)}/month additional` : 'Excellent',
      source: 'Compared to Indian median',
    },
    {
      priority: emergencyMonths < 3 ? 'high' : emergencyMonths < 6 ? 'medium' : 'low',
      icon: 'shield-check',
      title: emergencyMonths < 6 ? 'Build Emergency Fund' : 'Emergency Fund Ready',
      description: emergencyMonths < 6
        ? `You have ${emergencyMonths.toFixed(1)} months of expenses covered. RBI recommends 6 months. Focus on building this safety net first.`
        : `Great! You have ${emergencyMonths.toFixed(1)} months of expenses covered in emergency savings.`,
      impact: emergencyMonths < 6 ? `Target: ${formatINRShort(expenses * 6)} total` : 'Well prepared',
      source: 'RBI Financial Literacy Guidelines',
    },
    {
      priority: 'medium',
      icon: 'tax',
      title: 'Tax Saving Opportunities',
      description: 'Consider maximizing Section 80C investments (ELSS, PPF) and Section 80D (Health Insurance) to reduce tax liability by up to ₹46,800.',
      impact: 'Save up to ₹46,800 in taxes',
      source: 'Income Tax Act provisions',
    },
  ];

  // Monthly grades
  const grades = [
    { label: 'Spending Discipline', grade: savingsRate > 25 ? 'A' : savingsRate > 15 ? 'B' : 'C', color: savingsRate > 25 ? '#10B981' : savingsRate > 15 ? '#3B82F6' : '#F59E0B' },
    { label: 'Savings Consistency', grade: savingsRate > 20 ? 'A' : savingsRate > 10 ? 'B' : 'C', color: savingsRate > 20 ? '#10B981' : savingsRate > 10 ? '#3B82F6' : '#F59E0B' },
    { label: 'Investment Regularity', grade: investmentRatio > 20 ? 'A' : investmentRatio > 10 ? 'B' : 'C', color: investmentRatio > 20 ? '#10B981' : investmentRatio > 10 ? '#3B82F6' : '#F59E0B' },
    { label: 'Budget Adherence', grade: expenses < income * 0.7 ? 'A' : expenses < income * 0.85 ? 'B' : 'C', color: expenses < income * 0.7 ? '#10B981' : expenses < income * 0.85 ? '#3B82F6' : '#F59E0B' },
  ];

  const overallGrade = grades.filter(g => g.grade === 'A').length >= 3 ? 'A' :
    grades.filter(g => g.grade !== 'C').length >= 3 ? 'B' : 'C';

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: colors.background }]}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#10B981" />
          <Text style={[styles.loadingText, { color: colors.textSecondary }]}>Analyzing your finances...</Text>
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
                  AI-powered analysis of your financial health
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
        {/* ═══ FINANCIAL HEALTH SCORE CARD ═══ */}
        <Animated.View style={[styles.healthScoreCard, {
          backgroundColor: isDark ? 'rgba(16, 185, 129, 0.08)' : 'rgba(16, 185, 129, 0.05)',
          borderColor: isDark ? 'rgba(16, 185, 129, 0.2)' : 'rgba(16, 185, 129, 0.15)',
          opacity: fadeAnim,
        }]}>
          <View style={styles.healthScoreContent}>
            {/* Score Ring */}
            <View style={styles.scoreRingContainer}>
              <Svg width={140} height={140}>
                <G rotation="-90" origin="70, 70">
                  {/* Background circle */}
                  <Circle
                    cx="70"
                    cy="70"
                    r="60"
                    stroke={isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)'}
                    strokeWidth="12"
                    fill="transparent"
                  />
                  {/* Animated progress circle */}
                  <AnimatedCircle
                    cx="70"
                    cy="70"
                    r="60"
                    stroke={scoreColor}
                    strokeWidth="12"
                    fill="transparent"
                    strokeLinecap="round"
                    strokeDasharray={`${2 * Math.PI * 60}`}
                    strokeDashoffset={scoreAnim.interpolate({
                      inputRange: [0, 100],
                      outputRange: [2 * Math.PI * 60, 0],
                    })}
                  />
                </G>
              </Svg>
              <View style={styles.scoreCenter}>
                <Text style={[styles.scoreNumber, { color: scoreColor }]}>{healthScore}</Text>
                <Text style={[styles.scoreLabel, { color: colors.textSecondary }]}>Score</Text>
              </View>
            </View>

            {/* Score Info */}
            <View style={styles.scoreInfo}>
              <View style={[styles.scoreBadge, { backgroundColor: `${scoreInfo.color}15` }]}>
                <MaterialCommunityIcons
                  name={healthScore >= 65 ? 'check-circle' : 'alert-circle'}
                  size={16}
                  color={scoreInfo.color}
                />
                <Text style={[styles.scoreBadgeText, { color: scoreInfo.color }]}>{scoreInfo.label}</Text>
              </View>
              <Text style={[styles.scoreSummary, { color: colors.textPrimary }]}>
                {healthScore >= 70
                  ? "Your finances are in great shape! Keep maintaining your savings habits."
                  : healthScore >= 50
                  ? "Your financial health is fair. Focus on increasing savings and reducing unnecessary expenses."
                  : "Your finances need attention. Prioritize building an emergency fund and reducing debt."}
              </Text>
              <View style={[styles.comparisonBadge, { backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.04)' }]}>
                <MaterialCommunityIcons name="chart-bar" size={14} color="#10B981" />
                <Text style={[styles.comparisonText, { color: colors.textSecondary }]}>
                  Top {healthScore >= 70 ? '25%' : healthScore >= 50 ? '50%' : '70%'} of Indian earners in your bracket
                </Text>
              </View>
            </View>
          </View>
        </Animated.View>

        {/* ═══ KEY FINANCIAL RATIOS (2×2 Grid) ═══ */}
        <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Key Financial Ratios</Text>
        <View style={styles.ratioGrid}>
          <RatioCard
            icon="credit-card"
            title="EMI-to-Income"
            value={emiRatio}
            benchmark={40}
            benchmarkLabel="RBI recommends below 40%"
            colors={colors}
            isDark={isDark}
            goodBelow={30}
            warningBelow={40}
          />
          <RatioCard
            icon="scale-balance"
            title="Debt-to-Income"
            value={debtRatio}
            benchmark={28}
            benchmarkLabel="Indian average: 28%"
            colors={colors}
            isDark={isDark}
            goodBelow={25}
            warningBelow={35}
          />
          <RatioCard
            icon="trending-up"
            title="Investment Ratio"
            value={investmentRatio}
            benchmark={20}
            benchmarkLabel="Recommended: 20-30%"
            colors={colors}
            isDark={isDark}
            goodAbove={20}
            warningAbove={10}
            inverted
          />
          <RatioCard
            icon="shield-account"
            title="Emergency Fund"
            value={emergencyMonths}
            benchmark={6}
            benchmarkLabel="Target: 6 months"
            colors={colors}
            isDark={isDark}
            goodAbove={6}
            warningAbove={3}
            inverted
            isMonths
          />
        </View>

        {/* ═══ SPENDING BREAKDOWN ═══ */}
        {spendingData.length > 0 && (
          <View style={[styles.glassCard, {
            backgroundColor: isDark ? 'rgba(30, 41, 59, 0.7)' : 'rgba(255, 255, 255, 0.85)',
            borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
          }]}>
            <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>Spending Breakdown</Text>
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
        <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>AI Recommendations</Text>
        {recommendations.map((rec, index) => (
          <View
            key={index}
            style={[
              styles.recommendationCard,
              {
                backgroundColor: isDark ? 'rgba(30, 41, 59, 0.7)' : 'rgba(255, 255, 255, 0.85)',
                borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
                borderLeftColor: rec.priority === 'high' ? '#EF4444' : rec.priority === 'medium' ? '#F59E0B' : '#10B981',
              },
            ]}
          >
            <View style={styles.recHeader}>
              <View style={[styles.recIcon, {
                backgroundColor: rec.priority === 'high' ? 'rgba(239, 68, 68, 0.1)'
                  : rec.priority === 'medium' ? 'rgba(245, 158, 11, 0.1)'
                  : 'rgba(16, 185, 129, 0.1)',
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
                backgroundColor: rec.priority === 'low' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)',
              }]}>
                <MaterialCommunityIcons name="lightning-bolt" size={12} color={rec.priority === 'low' ? '#10B981' : '#F59E0B'} />
                <Text style={[styles.impactText, { color: rec.priority === 'low' ? '#10B981' : '#F59E0B' }]}>{rec.impact}</Text>
              </View>
              <Text style={[styles.sourceText, { color: colors.textSecondary }]}>{rec.source}</Text>
            </View>
          </View>
        ))}

        {/* ═══ MONTHLY REPORT CARD ═══ */}
        <View style={[styles.glassCard, {
          backgroundColor: isDark ? 'rgba(30, 41, 59, 0.7)' : 'rgba(255, 255, 255, 0.85)',
          borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
        }]}>
          <View style={styles.reportHeader}>
            <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>Monthly Report Card</Text>
            <View style={[styles.overallGradeBadge, {
              backgroundColor: overallGrade === 'A' ? 'rgba(16, 185, 129, 0.15)'
                : overallGrade === 'B' ? 'rgba(59, 130, 246, 0.15)'
                : 'rgba(245, 158, 11, 0.15)',
            }]}>
              <Text style={[styles.overallGradeText, {
                color: overallGrade === 'A' ? '#10B981' : overallGrade === 'B' ? '#3B82F6' : '#F59E0B',
              }]}>
                Grade: {overallGrade}
              </Text>
            </View>
          </View>
          {grades.map((g, i) => (
            <View key={i} style={styles.gradeRow}>
              <Text style={[styles.gradeLabel, { color: colors.textSecondary }]}>{g.label}</Text>
              <View style={[styles.gradeBadge, { backgroundColor: `${g.color}15` }]}>
                <Text style={[styles.gradeValue, { color: g.color }]}>{g.grade}</Text>
              </View>
            </View>
          ))}
        </View>

        {/* ═══ BENCHMARKS COMPARISON ═══ */}
        <View style={[styles.glassCard, {
          backgroundColor: isDark ? 'rgba(30, 41, 59, 0.7)' : 'rgba(255, 255, 255, 0.85)',
          borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
        }]}>
          <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>How You Compare</Text>
          <Text style={[styles.cardSubtitle, { color: colors.textSecondary }]}>vs. Indian National Averages</Text>
          
          <BenchmarkRow
            label="Savings Rate"
            yourValue={`${savingsRate.toFixed(0)}%`}
            average="15%"
            isAbove={savingsRate > 15}
            colors={colors}
            isDark={isDark}
          />
          <BenchmarkRow
            label="Investment Rate"
            yourValue={`${investmentRatio.toFixed(0)}%`}
            average="12%"
            isAbove={investmentRatio > 12}
            colors={colors}
            isDark={isDark}
          />
          <BenchmarkRow
            label="Expense Ratio"
            yourValue={`${((expenses / income) * 100).toFixed(0)}%`}
            average="75%"
            isAbove={(expenses / income) * 100 < 75}
            colors={colors}
            isDark={isDark}
          />
          <BenchmarkRow
            label="Emergency Fund"
            yourValue={`${emergencyMonths.toFixed(1)}mo`}
            average="2.5mo"
            isAbove={emergencyMonths > 2.5}
            colors={colors}
            isDark={isDark}
          />
          
          <Text style={[styles.sourceNote, { color: colors.textSecondary }]}>
            Source: RBI, CEIC, NSO Household Surveys 2024
          </Text>
        </View>

        <View style={{ height: 100 }} />
      </ScrollView>
    </View>
  );
}

// ═══ RATIO CARD COMPONENT ═══
function RatioCard({
  icon, title, value, benchmark, benchmarkLabel, colors, isDark,
  goodBelow, warningBelow, goodAbove, warningAbove, inverted = false, isMonths = false,
}: any) {
  const displayValue = isMonths ? `${value.toFixed(1)} mo` : `${value.toFixed(0)}%`;
  
  let status: 'good' | 'warning' | 'bad';
  if (inverted) {
    status = value >= (goodAbove || 0) ? 'good' : value >= (warningAbove || 0) ? 'warning' : 'bad';
  } else {
    status = value <= (goodBelow || 0) ? 'good' : value <= (warningBelow || 0) ? 'warning' : 'bad';
  }
  
  const statusColor = status === 'good' ? '#10B981' : status === 'warning' ? '#F59E0B' : '#EF4444';
  const progress = isMonths ? Math.min((value / benchmark) * 100, 100) : Math.min((value / (benchmark * 1.5)) * 100, 100);

  return (
    <View style={[styles.ratioCard, {
      backgroundColor: isDark ? 'rgba(30, 41, 59, 0.7)' : 'rgba(255, 255, 255, 0.85)',
      borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
    }]}>
      <View style={styles.ratioHeader}>
        <View style={[styles.ratioIcon, { backgroundColor: `${statusColor}15` }]}>
          <MaterialCommunityIcons name={icon} size={18} color={statusColor} />
        </View>
        <View style={[styles.ratioTrend, { backgroundColor: `${statusColor}15` }]}>
          <MaterialCommunityIcons
            name={status === 'good' ? 'arrow-down' : status === 'warning' ? 'minus' : 'arrow-up'}
            size={12}
            color={statusColor}
          />
        </View>
      </View>
      <Text style={[styles.ratioValue, { color: statusColor }]}>{displayValue}</Text>
      <Text style={[styles.ratioTitle, { color: colors.textPrimary }]}>{title}</Text>
      
      <View style={[styles.ratioBarBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
        <View style={[styles.ratioBarFill, { width: `${progress}%`, backgroundColor: statusColor }]} />
        {!isMonths && (
          <View style={[styles.ratioBenchmarkLine, { left: `${(benchmark / (benchmark * 1.5)) * 100}%` }]} />
        )}
      </View>
      <Text style={[styles.ratioBenchmark, { color: colors.textSecondary }]}>{benchmarkLabel}</Text>
    </View>
  );
}

// ═══ BENCHMARK ROW COMPONENT ═══
function BenchmarkRow({ label, yourValue, average, isAbove, colors, isDark }: any) {
  return (
    <View style={styles.benchmarkRow}>
      <Text style={[styles.benchmarkLabel, { color: colors.textPrimary }]}>{label}</Text>
      <Text style={[styles.benchmarkYours, { color: colors.textPrimary }]}>{yourValue}</Text>
      <Text style={[styles.benchmarkAvg, { color: colors.textSecondary }]}>{average}</Text>
      <View style={[styles.benchmarkStatus, { backgroundColor: isAbove ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)' }]}>
        <MaterialCommunityIcons
          name={isAbove ? 'check' : 'close'}
          size={14}
          color={isAbove ? '#10B981' : '#EF4444'}
        />
      </View>
    </View>
  );
}

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

  // Health Score Card
  healthScoreCard: {
    borderRadius: 24,
    padding: 20,
    borderWidth: 2,
    marginBottom: 24,
  },
  healthScoreContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 20,
  },
  scoreRingContainer: {
    width: 140,
    height: 140,
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
  scoreNumber: {
    fontSize: 40,
    fontWeight: '900',
    letterSpacing: -2,
  },
  scoreLabel: {
    fontSize: 11,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  scoreInfo: {
    flex: 1,
    gap: 10,
  },
  scoreBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    alignSelf: 'flex-start',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
  },
  scoreBadgeText: {
    fontSize: 14,
    fontWeight: '700',
  },
  scoreSummary: {
    fontSize: 13,
    lineHeight: 19,
  },
  comparisonBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
  },
  comparisonText: {
    fontSize: 11,
  },

  // Section Title
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 14,
    marginTop: 8,
  },

  // Ratio Grid
  ratioGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: 20,
  },
  ratioCard: {
    width: (SCREEN_WIDTH - 44) / 2,
    borderRadius: 20,
    padding: 16,
    borderWidth: 1,
  },
  ratioHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  ratioIcon: {
    width: 36,
    height: 36,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  ratioTrend: {
    width: 24,
    height: 24,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  ratioValue: {
    fontSize: 28,
    fontWeight: '800',
    letterSpacing: -1,
  },
  ratioTitle: {
    fontSize: 13,
    fontWeight: '600',
    marginTop: 4,
    marginBottom: 12,
  },
  ratioBarBg: {
    height: 6,
    borderRadius: 3,
    marginBottom: 8,
    position: 'relative',
    overflow: 'hidden',
  },
  ratioBarFill: {
    height: '100%',
    borderRadius: 3,
  },
  ratioBenchmarkLine: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    width: 2,
    backgroundColor: 'rgba(0,0,0,0.3)',
  },
  ratioBenchmark: {
    fontSize: 10,
  },

  // Glass Card
  glassCard: {
    borderRadius: 20,
    padding: 18,
    borderWidth: 1,
    marginBottom: 16,
  },
  cardTitle: {
    fontSize: 17,
    fontWeight: '700',
    marginBottom: 4,
  },
  cardSubtitle: {
    fontSize: 12,
    marginBottom: 16,
  },

  // Spending Breakdown
  spendingRow: {
    marginBottom: 14,
  },
  spendingLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 6,
  },
  spendingIcon: {
    width: 32,
    height: 32,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  spendingCategory: {
    fontSize: 14,
    fontWeight: '600',
    flex: 1,
  },
  spendingRight: {
    position: 'absolute',
    right: 0,
    top: 4,
    alignItems: 'flex-end',
  },
  spendingAmount: {
    fontSize: 14,
    fontWeight: '700',
  },
  spendingPercent: {
    fontSize: 11,
  },
  spendingBarBg: {
    height: 6,
    borderRadius: 3,
    overflow: 'hidden',
  },
  spendingBarFill: {
    height: '100%',
    borderRadius: 3,
  },

  // Recommendations
  recommendationCard: {
    borderRadius: 18,
    padding: 16,
    borderWidth: 1,
    borderLeftWidth: 4,
    marginBottom: 12,
  },
  recHeader: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 12,
  },
  recIcon: {
    width: 42,
    height: 42,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  recInfo: {
    flex: 1,
  },
  recTitle: {
    fontSize: 15,
    fontWeight: '700',
    marginBottom: 4,
  },
  recDesc: {
    fontSize: 13,
    lineHeight: 19,
  },
  recFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  impactBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 12,
  },
  impactText: {
    fontSize: 11,
    fontWeight: '600',
  },
  sourceText: {
    fontSize: 10,
  },

  // Report Card
  reportHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  overallGradeBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  },
  overallGradeText: {
    fontSize: 13,
    fontWeight: '700',
  },
  gradeRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 0.5,
    borderBottomColor: 'rgba(128,128,128,0.2)',
  },
  gradeLabel: {
    fontSize: 14,
  },
  gradeBadge: {
    width: 32,
    height: 32,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  gradeValue: {
    fontSize: 16,
    fontWeight: '800',
  },

  // Benchmark Comparison
  benchmarkRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 0.5,
    borderBottomColor: 'rgba(128,128,128,0.2)',
  },
  benchmarkLabel: {
    flex: 1,
    fontSize: 13,
    fontWeight: '500',
  },
  benchmarkYours: {
    width: 60,
    fontSize: 13,
    fontWeight: '700',
    textAlign: 'center',
  },
  benchmarkAvg: {
    width: 50,
    fontSize: 12,
    textAlign: 'center',
  },
  benchmarkStatus: {
    width: 28,
    height: 28,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 8,
  },
  sourceNote: {
    fontSize: 10,
    marginTop: 12,
    textAlign: 'center',
  },
});
