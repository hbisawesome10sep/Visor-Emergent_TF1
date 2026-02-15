import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, RefreshControl,
  ActivityIndicator, Dimensions, Platform, StatusBar, Animated, Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import { LinearGradient } from 'expo-linear-gradient';
import Svg, { Circle, G, Path, Line, Defs, LinearGradient as SvgLinearGradient, Stop } from 'react-native-svg';
import { useAuth } from '../../src/context/AuthContext';
import { useTheme } from '../../src/context/ThemeContext';
import { apiRequest } from '../../src/utils/api';
import { formatINRShort } from '../../src/utils/formatters';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// Investment categories with colors
const INVEST_CATEGORIES = [
  { key: 'stocks', name: 'Stocks', color: '#3B82F6', icon: 'chart-areaspline' },
  { key: 'mutual_funds', name: 'Mutual Funds', color: '#8B5CF6', icon: 'chart-pie' },
  { key: 'fd', name: 'Fixed Deposits', color: '#10B981', icon: 'bank' },
  { key: 'ppf', name: 'PPF', color: '#14B8A6', icon: 'shield-check' },
  { key: 'gold', name: 'Gold', color: '#F59E0B', icon: 'diamond-stone' },
  { key: 'nps', name: 'NPS', color: '#6366F1', icon: 'account-cash' },
  { key: 'real_estate', name: 'Real Estate', color: '#EC4899', icon: 'home-city' },
  { key: 'others', name: 'Others', color: '#64748B', icon: 'dots-horizontal' },
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
    question: 'How would you react if your portfolio dropped 20% in a month?',
    options: [
      { label: 'Sell everything immediately', value: 1 },
      { label: 'Sell some holdings', value: 2 },
      { label: 'Hold and wait', value: 3 },
      { label: 'Buy more at lower prices', value: 4 },
    ],
  },
  {
    question: 'What percentage of monthly income can you invest?',
    options: [
      { label: 'Less than 10%', value: 1 },
      { label: '10-20%', value: 2 },
      { label: '20-30%', value: 3 },
      { label: 'More than 30%', value: 4 },
    ],
  },
  {
    question: 'What is your primary investment goal?',
    options: [
      { label: 'Capital preservation', value: 1 },
      { label: 'Steady income', value: 2 },
      { label: 'Balanced growth', value: 3 },
      { label: 'Aggressive growth', value: 4 },
    ],
  },
  {
    question: 'How much investment experience do you have?',
    options: [
      { label: 'None', value: 1 },
      { label: 'Basic (FDs, savings)', value: 2 },
      { label: 'Intermediate (MFs, stocks)', value: 3 },
      { label: 'Advanced (options, crypto)', value: 4 },
    ],
  },
];

// Market indices data (mock - in production would be fetched)
const MARKET_INDICES = [
  { name: 'Nifty 50', value: 22456.80, change: 1.23, up: true },
  { name: 'Sensex', value: 73890.45, change: 1.18, up: true },
  { name: 'Nifty Bank', value: 47234.65, change: -0.34, up: false },
  { name: 'Gold (10g)', value: 62450, change: 0.56, up: true },
];

type DashboardStats = {
  total_income: number;
  total_expenses: number;
  total_investments: number;
  invest_breakdown: Record<string, number>;
};

export default function InvestmentsScreen() {
  const { user, token } = useAuth();
  const { colors, isDark } = useTheme();

  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showRiskModal, setShowRiskModal] = useState(false);
  const [riskStep, setRiskStep] = useState(0);
  const [riskAnswers, setRiskAnswers] = useState<number[]>([]);
  const [riskProfile, setRiskProfile] = useState<'Conservative' | 'Moderate' | 'Aggressive'>('Moderate');

  // Animation
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const countAnim = useRef(new Animated.Value(0)).current;

  const fetchData = useCallback(async () => {
    if (!token) return;
    try {
      const data = await apiRequest('/dashboard/stats', { token });
      setStats(data);

      Animated.parallel([
        Animated.timing(fadeAnim, { toValue: 1, duration: 500, useNativeDriver: true }),
        Animated.timing(countAnim, { toValue: data.total_investments || 0, duration: 1500, useNativeDriver: false }),
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
    countAnim.setValue(0);
    fetchData();
  };

  // Calculate portfolio data
  const totalInvested = stats?.total_investments || 0;
  const returns = Math.round(totalInvested * 0.127); // 12.7% simulated returns
  const portfolioValue = totalInvested + returns;
  const xirr = 14.2;
  const monthlyChange = Math.round(portfolioValue * 0.0399);

  // Asset allocation from stats
  const allocation = stats?.invest_breakdown || {};
  const allocationData = INVEST_CATEGORIES.map(cat => ({
    ...cat,
    amount: allocation[cat.name] || allocation[cat.key] || 0,
  })).filter(a => a.amount > 0);

  // If no breakdown data, create mock data
  const mockAllocation = allocationData.length === 0 ? [
    { ...INVEST_CATEGORIES[0], amount: totalInvested * 0.30 },
    { ...INVEST_CATEGORIES[1], amount: totalInvested * 0.35 },
    { ...INVEST_CATEGORIES[2], amount: totalInvested * 0.15 },
    { ...INVEST_CATEGORIES[3], amount: totalInvested * 0.10 },
    { ...INVEST_CATEGORIES[4], amount: totalInvested * 0.10 },
  ] : allocationData;

  const totalAllocation = mockAllocation.reduce((s, a) => s + a.amount, 0) || 1;

  // Risk profile calculation
  const calculateRiskProfile = () => {
    const total = riskAnswers.reduce((s, a) => s + a, 0);
    const avg = total / riskAnswers.length;
    if (avg <= 1.5) return 'Conservative';
    if (avg <= 2.8) return 'Moderate';
    return 'Aggressive';
  };

  const handleRiskAnswer = (value: number) => {
    const newAnswers = [...riskAnswers, value];
    setRiskAnswers(newAnswers);

    if (riskStep < RISK_QUESTIONS.length - 1) {
      setRiskStep(riskStep + 1);
    } else {
      // Calculate and set risk profile
      const total = newAnswers.reduce((s, a) => s + a, 0);
      const avg = total / newAnswers.length;
      const profile = avg <= 1.5 ? 'Conservative' : avg <= 2.8 ? 'Moderate' : 'Aggressive';
      setRiskProfile(profile);
      setShowRiskModal(false);
      setRiskStep(0);
      setRiskAnswers([]);
    }
  };

  // Strategy based on risk profile
  const strategies = {
    Conservative: {
      name: 'Safe Harbor Strategy',
      description: 'Focus on capital preservation with stable, predictable returns.',
      allocation: [
        { name: 'FD/PPF/Bonds', percent: 60, color: '#10B981' },
        { name: 'Large-cap Equity', percent: 25, color: '#3B82F6' },
        { name: 'Gold', percent: 10, color: '#F59E0B' },
        { name: 'Cash', percent: 5, color: '#64748B' },
      ],
    },
    Moderate: {
      name: 'Balanced Growth Strategy',
      description: 'Mix of growth and stability for long-term wealth building.',
      allocation: [
        { name: 'Equity', percent: 40, color: '#3B82F6' },
        { name: 'Debt', percent: 30, color: '#10B981' },
        { name: 'Gold', percent: 15, color: '#F59E0B' },
        { name: 'Alternatives', percent: 15, color: '#8B5CF6' },
      ],
    },
    Aggressive: {
      name: 'High Growth Strategy',
      description: 'Maximum equity exposure for higher long-term returns.',
      allocation: [
        { name: 'Equity (incl. small/mid)', percent: 70, color: '#3B82F6' },
        { name: 'Alternatives', percent: 15, color: '#8B5CF6' },
        { name: 'Debt', percent: 10, color: '#10B981' },
        { name: 'Gold', percent: 5, color: '#F59E0B' },
      ],
    },
  };

  const currentStrategy = strategies[riskProfile];

  // Tax saving calculations
  const section80CUsed = Math.min(totalInvested * 0.4, 150000);
  const section80CLimit = 150000;

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: colors.background }]}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#F97316" />
          <Text style={[styles.loadingText, { color: colors.textSecondary }]}>Loading portfolio...</Text>
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
                  colors={['#EA580C', '#DC2626']}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 0 }}
                  style={styles.gradientTitleBg}
                >
                  <Text style={styles.gradientTitle}>Investments</Text>
                </LinearGradient>
                <Text style={[styles.headerSubtitle, { color: colors.textSecondary }]}>
                  Grow your wealth with smart strategies
                </Text>
              </View>
              <TouchableOpacity
                style={[styles.refreshBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)' }]}
                onPress={onRefresh}
              >
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
        {/* ═══ PORTFOLIO SUMMARY CARD ═══ */}
        <Animated.View style={[styles.portfolioCard, {
          backgroundColor: isDark ? 'rgba(249, 115, 22, 0.08)' : 'rgba(249, 115, 22, 0.05)',
          borderColor: isDark ? 'rgba(249, 115, 22, 0.2)' : 'rgba(249, 115, 22, 0.15)',
          opacity: fadeAnim,
        }]}>
          <View style={styles.portfolioHeader}>
            <Text style={[styles.portfolioLabel, { color: colors.textSecondary }]}>Total Portfolio Value</Text>
            <View style={[styles.changeBadge, { backgroundColor: 'rgba(16, 185, 129, 0.1)' }]}>
              <MaterialCommunityIcons name="arrow-up" size={14} color="#10B981" />
              <Text style={[styles.changeText, { color: '#10B981' }]}>+3.99% this month</Text>
            </View>
          </View>

          <Animated.Text style={[styles.portfolioValue, { color: colors.textPrimary }]}>
            ₹{portfolioValue.toLocaleString('en-IN')}
          </Animated.Text>

          <Text style={[styles.portfolioChange, { color: '#10B981' }]}>
            +₹{monthlyChange.toLocaleString('en-IN')} this month
          </Text>

          {/* Mini Sparkline */}
          <View style={styles.sparklineContainer}>
            <Svg width={SCREEN_WIDTH - 80} height={50}>
              <Defs>
                <SvgLinearGradient id="sparklineGrad" x1="0" y1="0" x2="0" y2="1">
                  <Stop offset="0" stopColor="#F97316" stopOpacity="0.3" />
                  <Stop offset="1" stopColor="#F97316" stopOpacity="0" />
                </SvgLinearGradient>
              </Defs>
              <Path
                d={`M 0 40 L 50 35 L 100 38 L 150 30 L 200 25 L 250 20 L ${SCREEN_WIDTH - 80} 15`}
                stroke="#F97316"
                strokeWidth={2}
                fill="none"
              />
              <Path
                d={`M 0 40 L 50 35 L 100 38 L 150 30 L 200 25 L 250 20 L ${SCREEN_WIDTH - 80} 15 L ${SCREEN_WIDTH - 80} 50 L 0 50 Z`}
                fill="url(#sparklineGrad)"
              />
            </Svg>
          </View>

          {/* Summary Pills */}
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
          {/* Donut Chart */}
          <View style={styles.donutContainer}>
            <Svg width={160} height={160}>
              <G rotation="-90" origin="80, 80">
                {mockAllocation.map((item, index) => {
                  const percent = (item.amount / totalAllocation) * 100;
                  const circumference = 2 * Math.PI * 55;
                  const offset = mockAllocation
                    .slice(0, index)
                    .reduce((s, a) => s + (a.amount / totalAllocation) * circumference, 0);
                  return (
                    <Circle
                      key={item.key}
                      cx="80"
                      cy="80"
                      r="55"
                      stroke={item.color}
                      strokeWidth="22"
                      fill="transparent"
                      strokeDasharray={`${(percent / 100) * circumference} ${circumference}`}
                      strokeDashoffset={-offset}
                    />
                  );
                })}
              </G>
            </Svg>
            <View style={styles.donutCenter}>
              <Text style={[styles.donutValue, { color: colors.textPrimary }]}>₹{formatINRShort(portfolioValue)}</Text>
              <Text style={[styles.donutLabel, { color: colors.textSecondary }]}>Total</Text>
            </View>
          </View>

          {/* Legend */}
          <View style={styles.legendGrid}>
            {mockAllocation.map(item => {
              const percent = (item.amount / totalAllocation) * 100;
              return (
                <View key={item.key} style={styles.legendItem}>
                  <View style={[styles.legendDot, { backgroundColor: item.color }]} />
                  <View style={styles.legendInfo}>
                    <Text style={[styles.legendName, { color: colors.textPrimary }]}>{item.name}</Text>
                    <Text style={[styles.legendAmount, { color: colors.textSecondary }]}>
                      ₹{formatINRShort(item.amount)} ({percent.toFixed(0)}%)
                    </Text>
                  </View>
                </View>
              );
            })}
          </View>
        </View>

        {/* ═══ MARKET INDICES ═══ */}
        <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Indian Markets</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.marketsScroll}>
          {MARKET_INDICES.map((index, i) => (
            <View key={i} style={[styles.marketCard, {
              backgroundColor: isDark ? 'rgba(30, 41, 59, 0.7)' : 'rgba(255, 255, 255, 0.85)',
              borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
            }]}>
              <Text style={[styles.marketName, { color: colors.textSecondary }]}>{index.name}</Text>
              <Text style={[styles.marketValue, { color: colors.textPrimary }]}>
                ₹{index.value.toLocaleString('en-IN')}
              </Text>
              <View style={[styles.marketChangeBadge, { backgroundColor: index.up ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)' }]}>
                <MaterialCommunityIcons
                  name={index.up ? 'arrow-up' : 'arrow-down'}
                  size={12}
                  color={index.up ? '#10B981' : '#EF4444'}
                />
                <Text style={[styles.marketChangeText, { color: index.up ? '#10B981' : '#EF4444' }]}>
                  {index.change}%
                </Text>
              </View>
            </View>
          ))}
        </ScrollView>
        <Text style={[styles.lastUpdated, { color: colors.textSecondary }]}>Last updated: Today, 3:30 PM IST</Text>

        {/* ═══ RISK ASSESSMENT ═══ */}
        <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Risk Profile</Text>
        <View style={[styles.riskCard, {
          backgroundColor: isDark ? 'rgba(30, 41, 59, 0.7)' : 'rgba(255, 255, 255, 0.85)',
          borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
        }]}>
          <View style={styles.riskHeader}>
            <View style={[styles.riskBadge, {
              backgroundColor: riskProfile === 'Conservative' ? 'rgba(59, 130, 246, 0.15)'
                : riskProfile === 'Moderate' ? 'rgba(245, 158, 11, 0.15)'
                : 'rgba(239, 68, 68, 0.15)',
            }]}>
              <MaterialCommunityIcons
                name={riskProfile === 'Conservative' ? 'shield-check' : riskProfile === 'Moderate' ? 'scale-balance' : 'rocket-launch'}
                size={24}
                color={riskProfile === 'Conservative' ? '#3B82F6' : riskProfile === 'Moderate' ? '#F59E0B' : '#EF4444'}
              />
              <Text style={[styles.riskBadgeText, {
                color: riskProfile === 'Conservative' ? '#3B82F6' : riskProfile === 'Moderate' ? '#F59E0B' : '#EF4444',
              }]}>
                {riskProfile}
              </Text>
            </View>
            <TouchableOpacity
              style={[styles.retakeBtn, { borderColor: colors.border }]}
              onPress={() => { setShowRiskModal(true); setRiskStep(0); setRiskAnswers([]); }}
            >
              <MaterialCommunityIcons name="refresh" size={16} color={colors.textSecondary} />
              <Text style={[styles.retakeBtnText, { color: colors.textSecondary }]}>Retake</Text>
            </TouchableOpacity>
          </View>
          <Text style={[styles.riskDesc, { color: colors.textSecondary }]}>
            {riskProfile === 'Conservative'
              ? 'You prefer stable, low-risk investments with predictable returns. Your portfolio should favor debt instruments and blue-chip stocks.'
              : riskProfile === 'Moderate'
              ? 'You seek a balance between growth and stability. A mix of equity and debt instruments suits your goals.'
              : 'You are comfortable with high volatility for potentially higher returns. Equity-heavy portfolios with some alternatives are ideal.'}
          </Text>
        </View>

        {/* ═══ AI STRATEGY ═══ */}
        <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Recommended Strategy</Text>
        <View style={[styles.strategyCard, {
          backgroundColor: isDark ? 'rgba(249, 115, 22, 0.08)' : 'rgba(249, 115, 22, 0.05)',
          borderColor: isDark ? 'rgba(249, 115, 22, 0.2)' : 'rgba(249, 115, 22, 0.15)',
        }]}>
          <View style={styles.strategyHeader}>
            <View style={[styles.strategyIcon, { backgroundColor: 'rgba(249, 115, 22, 0.15)' }]}>
              <MaterialCommunityIcons name="lightbulb-on" size={24} color="#F97316" />
            </View>
            <View style={styles.strategyInfo}>
              <Text style={[styles.strategyName, { color: colors.textPrimary }]}>{currentStrategy.name}</Text>
              <Text style={[styles.strategyDesc, { color: colors.textSecondary }]}>{currentStrategy.description}</Text>
            </View>
          </View>

          {/* Recommended Allocation Bar */}
          <Text style={[styles.allocationLabel, { color: colors.textSecondary }]}>Recommended Allocation</Text>
          <View style={styles.allocationBar}>
            {currentStrategy.allocation.map((item, i) => (
              <View key={i} style={[styles.allocationSegment, { width: `${item.percent}%`, backgroundColor: item.color }]}>
                {item.percent >= 15 && (
                  <Text style={styles.allocationSegmentText}>{item.percent}%</Text>
                )}
              </View>
            ))}
          </View>
          <View style={styles.allocationLegend}>
            {currentStrategy.allocation.map((item, i) => (
              <View key={i} style={styles.allocationLegendItem}>
                <View style={[styles.allocationLegendDot, { backgroundColor: item.color }]} />
                <Text style={[styles.allocationLegendText, { color: colors.textSecondary }]}>{item.name}</Text>
              </View>
            ))}
          </View>
        </View>

        {/* ═══ TAX SAVING ═══ */}
        <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Tax-Saving (Section 80C)</Text>
        <View style={[styles.glassCard, {
          backgroundColor: isDark ? 'rgba(30, 41, 59, 0.7)' : 'rgba(255, 255, 255, 0.85)',
          borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
        }]}>
          <View style={styles.taxHeader}>
            <View>
              <Text style={[styles.taxUsed, { color: colors.textPrimary }]}>₹{formatINRShort(section80CUsed)}</Text>
              <Text style={[styles.taxLimit, { color: colors.textSecondary }]}>of ₹1,50,000 limit</Text>
            </View>
            <View style={[styles.taxPercentBadge, {
              backgroundColor: section80CUsed >= section80CLimit ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)',
            }]}>
              <Text style={[styles.taxPercentText, {
                color: section80CUsed >= section80CLimit ? '#10B981' : '#F59E0B',
              }]}>
                {((section80CUsed / section80CLimit) * 100).toFixed(0)}% used
              </Text>
            </View>
          </View>
          <View style={[styles.taxBarBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
            <View style={[styles.taxBarFill, {
              width: `${Math.min((section80CUsed / section80CLimit) * 100, 100)}%`,
              backgroundColor: section80CUsed >= section80CLimit ? '#10B981' : '#F97316',
            }]} />
          </View>
          <Text style={[styles.taxTip, { color: colors.textSecondary }]}>
            {section80CUsed < section80CLimit
              ? `Invest ₹${formatINRShort(section80CLimit - section80CUsed)} more in ELSS, PPF, or NPS to maximize tax savings of up to ₹46,800`
              : 'Great! You have maximized your Section 80C limit this year.'}
          </Text>
        </View>

        {/* ═══ INVESTMENT TIPS ═══ */}
        <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Smart Investment Tips</Text>
        {[
          { icon: 'calendar-sync', title: 'Start a SIP', desc: 'Systematic Investment Plans help you average costs and build wealth over time.', priority: 'green' },
          { icon: 'diversify', title: 'Diversify Portfolio', desc: 'Spread investments across asset classes to reduce risk.', priority: 'green' },
          { icon: 'clock-fast', title: 'Think Long-Term', desc: 'Stay invested for 7+ years to ride out market volatility.', priority: 'orange' },
        ].map((tip, i) => (
          <View key={i} style={[styles.tipCard, {
            backgroundColor: isDark ? 'rgba(30, 41, 59, 0.7)' : 'rgba(255, 255, 255, 0.85)',
            borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
            borderLeftColor: tip.priority === 'green' ? '#10B981' : '#F59E0B',
          }]}>
            <View style={[styles.tipIcon, { backgroundColor: tip.priority === 'green' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)' }]}>
              <MaterialCommunityIcons name={tip.icon as any} size={20} color={tip.priority === 'green' ? '#10B981' : '#F59E0B'} />
            </View>
            <View style={styles.tipContent}>
              <Text style={[styles.tipTitle, { color: colors.textPrimary }]}>{tip.title}</Text>
              <Text style={[styles.tipDesc, { color: colors.textSecondary }]}>{tip.desc}</Text>
            </View>
          </View>
        ))}

        <View style={{ height: 100 }} />
      </ScrollView>

      {/* ═══ RISK ASSESSMENT MODAL ═══ */}
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

            {/* Progress */}
            <View style={styles.progressRow}>
              {RISK_QUESTIONS.map((_, i) => (
                <View key={i} style={[styles.progressDot, {
                  backgroundColor: i <= riskStep ? '#F97316' : colors.border,
                  width: i === riskStep ? 24 : 8,
                }]} />
              ))}
            </View>
            <Text style={[styles.progressText, { color: colors.textSecondary }]}>
              Question {riskStep + 1} of {RISK_QUESTIONS.length}
            </Text>

            <Text style={[styles.questionText, { color: colors.textPrimary }]}>
              {RISK_QUESTIONS[riskStep].question}
            </Text>

            <View style={styles.optionsContainer}>
              {RISK_QUESTIONS[riskStep].options.map((opt, i) => (
                <TouchableOpacity
                  key={i}
                  style={[styles.optionBtn, {
                    backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
                    borderColor: colors.border,
                  }]}
                  onPress={() => handleRiskAnswer(opt.value)}
                >
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
  stickyHeader: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    zIndex: 100,
  },
  headerBlur: { borderBottomWidth: 1 },
  headerSafeArea: { paddingHorizontal: 16, paddingBottom: 12 },
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
  gradientTitle: { fontSize: 22, fontWeight: '800', color: '#fff' },
  headerSubtitle: { fontSize: 12, marginTop: 4 },
  refreshBtn: { width: 40, height: 40, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },

  // Scroll
  scrollView: { flex: 1 },
  scrollContent: { paddingTop: Platform.OS === 'ios' ? 120 : 100, paddingHorizontal: 16 },

  // Portfolio Card
  portfolioCard: {
    borderRadius: 24,
    padding: 20,
    borderWidth: 2,
    marginBottom: 24,
  },
  portfolioHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  portfolioLabel: { fontSize: 13, fontWeight: '600' },
  changeBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  changeText: { fontSize: 12, fontWeight: '700' },
  portfolioValue: { fontSize: 38, fontWeight: '900', letterSpacing: -2 },
  portfolioChange: { fontSize: 14, fontWeight: '600', marginTop: 4 },
  sparklineContainer: { marginVertical: 16 },
  summaryPillsRow: { flexDirection: 'row', gap: 10 },
  summaryPill: { flex: 1, padding: 12, borderRadius: 14, alignItems: 'center' },
  pillLabel: { fontSize: 11, marginBottom: 4 },
  pillValue: { fontSize: 15, fontWeight: '800' },

  // Section Title
  sectionTitle: { fontSize: 18, fontWeight: '700', marginBottom: 14, marginTop: 8 },

  // Glass Card
  glassCard: { borderRadius: 20, padding: 18, borderWidth: 1, marginBottom: 16 },

  // Donut Chart
  donutContainer: { alignItems: 'center', marginBottom: 20, position: 'relative' },
  donutCenter: { position: 'absolute', top: 55, alignItems: 'center' },
  donutValue: { fontSize: 18, fontWeight: '800' },
  donutLabel: { fontSize: 11 },
  legendGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  legendItem: { flexDirection: 'row', alignItems: 'center', width: '47%', gap: 8 },
  legendDot: { width: 10, height: 10, borderRadius: 5 },
  legendInfo: { flex: 1 },
  legendName: { fontSize: 13, fontWeight: '600' },
  legendAmount: { fontSize: 11 },

  // Markets
  marketsScroll: { marginBottom: 8 },
  marketCard: { width: 130, padding: 14, borderRadius: 16, borderWidth: 1, marginRight: 10 },
  marketName: { fontSize: 11, fontWeight: '600', marginBottom: 4 },
  marketValue: { fontSize: 14, fontWeight: '800' },
  marketChangeBadge: { flexDirection: 'row', alignItems: 'center', gap: 2, marginTop: 6, paddingHorizontal: 6, paddingVertical: 3, borderRadius: 8, alignSelf: 'flex-start' },
  marketChangeText: { fontSize: 11, fontWeight: '700' },
  lastUpdated: { fontSize: 10, marginBottom: 16 },

  // Risk Card
  riskCard: { borderRadius: 20, padding: 18, borderWidth: 1, marginBottom: 16 },
  riskHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  riskBadge: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 14, paddingVertical: 10, borderRadius: 16 },
  riskBadgeText: { fontSize: 16, fontWeight: '800' },
  retakeBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 12, paddingVertical: 8, borderRadius: 12, borderWidth: 1 },
  retakeBtnText: { fontSize: 12, fontWeight: '600' },
  riskDesc: { fontSize: 13, lineHeight: 19 },

  // Strategy Card
  strategyCard: { borderRadius: 20, padding: 18, borderWidth: 2, marginBottom: 16 },
  strategyHeader: { flexDirection: 'row', gap: 14, marginBottom: 16 },
  strategyIcon: { width: 48, height: 48, borderRadius: 14, justifyContent: 'center', alignItems: 'center' },
  strategyInfo: { flex: 1 },
  strategyName: { fontSize: 17, fontWeight: '700', marginBottom: 4 },
  strategyDesc: { fontSize: 13, lineHeight: 18 },
  allocationLabel: { fontSize: 12, fontWeight: '600', marginBottom: 8 },
  allocationBar: { flexDirection: 'row', height: 24, borderRadius: 12, overflow: 'hidden', marginBottom: 12 },
  allocationSegment: { justifyContent: 'center', alignItems: 'center' },
  allocationSegmentText: { fontSize: 10, fontWeight: '700', color: '#fff' },
  allocationLegend: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  allocationLegendItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  allocationLegendDot: { width: 8, height: 8, borderRadius: 4 },
  allocationLegendText: { fontSize: 11 },

  // Tax Section
  taxHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  taxUsed: { fontSize: 24, fontWeight: '800' },
  taxLimit: { fontSize: 12 },
  taxPercentBadge: { paddingHorizontal: 10, paddingVertical: 6, borderRadius: 12 },
  taxPercentText: { fontSize: 13, fontWeight: '700' },
  taxBarBg: { height: 8, borderRadius: 4, overflow: 'hidden', marginBottom: 12 },
  taxBarFill: { height: '100%', borderRadius: 4 },
  taxTip: { fontSize: 12, lineHeight: 18 },

  // Tips
  tipCard: { flexDirection: 'row', padding: 14, borderRadius: 16, borderWidth: 1, borderLeftWidth: 4, marginBottom: 10, gap: 12 },
  tipIcon: { width: 40, height: 40, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  tipContent: { flex: 1 },
  tipTitle: { fontSize: 14, fontWeight: '700', marginBottom: 4 },
  tipDesc: { fontSize: 12, lineHeight: 17 },

  // Modal
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modalContent: { borderTopLeftRadius: 28, borderTopRightRadius: 28, padding: 24, paddingBottom: 40 },
  modalHandle: { width: 40, height: 4, borderRadius: 2, backgroundColor: '#CBD5E1', alignSelf: 'center', marginBottom: 16 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  modalTitle: { fontSize: 22, fontWeight: '800' },
  progressRow: { flexDirection: 'row', gap: 6, marginBottom: 8, justifyContent: 'center' },
  progressDot: { height: 6, borderRadius: 3 },
  progressText: { fontSize: 12, textAlign: 'center', marginBottom: 24 },
  questionText: { fontSize: 18, fontWeight: '700', textAlign: 'center', marginBottom: 24, lineHeight: 26 },
  optionsContainer: { gap: 10 },
  optionBtn: { padding: 16, borderRadius: 14, borderWidth: 1 },
  optionText: { fontSize: 15, fontWeight: '500', textAlign: 'center' },
});
