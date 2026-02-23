import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Animated, Dimensions } from 'react-native';
import Svg, { Circle, Defs, LinearGradient as SvgGradient, Stop, G } from 'react-native-svg';
import { LinearGradient } from 'expo-linear-gradient';
import { MaterialCommunityIcons } from '@expo/vector-icons';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

type HealthData = {
  overall_score: number;
  grade: string;
  has_sufficient_data: boolean;
  savings_rate: number;
  investment_rate: number;
  expense_ratio: number;
  goal_progress: number;
  breakdown: {
    savings: number;
    investments: number;
    spending: number;
    goals: number;
  };
};

type Props = {
  data: HealthData;
  isDark: boolean;
  colors: any;
  compact?: boolean;
};

const getGradeConfig = (score: number, hasData: boolean) => {
  if (!hasData) return { 
    label: 'Add Data', 
    emoji: '📊',
    gradient: ['#64748B', '#475569'],
    description: 'Upload statements to see your score',
    iconBg: '#64748B20'
  };
  
  if (score >= 80) return { 
    label: 'Excellent', 
    emoji: '🏆',
    gradient: ['#10B981', '#059669'],
    description: 'Outstanding! You\'re on track to financial freedom',
    iconBg: '#10B98130'
  };
  if (score >= 65) return { 
    label: 'Good', 
    emoji: '💪',
    gradient: ['#14B8A6', '#0D9488'],
    description: 'Great progress! A few tweaks and you\'ll excel',
    iconBg: '#14B8A630'
  };
  if (score >= 50) return { 
    label: 'Fair', 
    emoji: '📈',
    gradient: ['#F59E0B', '#D97706'],
    description: 'You\'re building momentum. Stay consistent!',
    iconBg: '#F59E0B30'
  };
  if (score >= 35) return { 
    label: 'Needs Work', 
    emoji: '💡',
    gradient: ['#F97316', '#EA580C'],
    description: 'Focus on reducing expenses & building savings',
    iconBg: '#F9731630'
  };
  return { 
    label: 'Critical', 
    emoji: '🎯',
    gradient: ['#EF4444', '#DC2626'],
    description: 'Let\'s prioritize your emergency fund first',
    iconBg: '#EF444430'
  };
};

const MetricBar = ({ label, value, maxValue, color, isDark, icon }: { label: string; value: number; maxValue: number; color: string; isDark: boolean; icon: string }) => {
  const percentage = Math.min(100, (value / maxValue) * 100);
  const animatedWidth = React.useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(animatedWidth, {
      toValue: percentage,
      duration: 1000,
      useNativeDriver: false,
    }).start();
  }, [percentage]);

  return (
    <View style={metricStyles.container}>
      <View style={metricStyles.labelRow}>
        <View style={[metricStyles.iconBg, { backgroundColor: isDark ? `${color}30` : `${color}20` }]}>
          <MaterialCommunityIcons name={icon as any} size={14} color={color} />
        </View>
        <Text style={[metricStyles.label, { color: isDark ? '#E2E8F0' : '#334155' }]}>{label}</Text>
        <Text style={[metricStyles.value, { color }]}>{value.toFixed(0)}%</Text>
      </View>
      <View style={[metricStyles.track, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)' }]}>
        <Animated.View
          style={[
            metricStyles.fill,
            {
              backgroundColor: color,
              width: animatedWidth.interpolate({
                inputRange: [0, 100],
                outputRange: ['0%', '100%'],
              }),
            },
          ]}
        />
      </View>
    </View>
  );
};

const metricStyles = StyleSheet.create({
  container: { marginBottom: 12 },
  labelRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 6 },
  iconBg: { width: 24, height: 24, borderRadius: 6, alignItems: 'center', justifyContent: 'center', marginRight: 8 },
  label: { flex: 1, fontSize: 13, fontFamily: 'DM Sans', fontWeight: '500' as any },
  value: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700' as any },
  track: { height: 8, borderRadius: 4, overflow: 'hidden' },
  fill: { height: '100%', borderRadius: 4 },
});

export const FinancialHealthCard = ({ data, isDark, colors, compact = false }: Props) => {
  const [expanded, setExpanded] = useState(false);
  const score = data.overall_score || 0;
  const config = getGradeConfig(score, data.has_sufficient_data);
  
  const circleSize = compact ? 80 : 110;
  const strokeWidth = compact ? 8 : 10;
  const radius = (circleSize - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference * (1 - score / 100);

  // Animation for score number
  const animatedScore = React.useRef(new Animated.Value(0)).current;
  const [displayScore, setDisplayScore] = useState(0);

  useEffect(() => {
    animatedScore.setValue(0);
    Animated.timing(animatedScore, {
      toValue: score,
      duration: 1500,
      useNativeDriver: false,
    }).start();

    animatedScore.addListener(({ value }) => {
      setDisplayScore(Math.round(value));
    });

    return () => animatedScore.removeAllListeners();
  }, [score]);

  if (!data.has_sufficient_data) {
    return (
      <View
        data-testid="financial-health-card-empty"
        style={[styles.card, { 
          backgroundColor: isDark ? 'rgba(100, 116, 139, 0.15)' : '#F8FAFC',
          borderColor: isDark ? 'rgba(100, 116, 139, 0.3)' : '#E2E8F0',
        }]}
      >
        <View style={styles.emptyState}>
          <View style={[styles.emptyIcon, { backgroundColor: isDark ? 'rgba(100, 116, 139, 0.3)' : 'rgba(100, 116, 139, 0.1)' }]}>
            <MaterialCommunityIcons name="chart-donut" size={32} color="#64748B" />
          </View>
          <Text style={[styles.emptyTitle, { color: colors.textPrimary }]}>Calculate Your Score</Text>
          <Text style={[styles.emptyDesc, { color: colors.textSecondary }]}>
            Upload bank statements or add transactions to see your personalized financial health analysis
          </Text>
        </View>
      </View>
    );
  }

  return (
    <TouchableOpacity
      activeOpacity={0.98}
      onPress={() => setExpanded(!expanded)}
      data-testid="financial-health-card"
    >
      <LinearGradient
        colors={isDark 
          ? [`${config.gradient[0]}20`, `${config.gradient[1]}10`]
          : [`${config.gradient[0]}15`, `${config.gradient[1]}08`]
        }
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={[styles.card, { borderColor: isDark ? `${config.gradient[0]}40` : `${config.gradient[0]}30` }]}
      >
        {/* Header Badge */}
        <View style={styles.header}>
          <View style={[styles.headerBadge, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)' }]}>
            <MaterialCommunityIcons name="shield-check" size={14} color={config.gradient[0]} />
            <Text style={[styles.headerBadgeText, { color: colors.textSecondary }]}>Financial Health</Text>
          </View>
          <TouchableOpacity 
            style={[styles.expandBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)' }]}
            onPress={() => setExpanded(!expanded)}
          >
            <MaterialCommunityIcons 
              name={expanded ? "chevron-up" : "chevron-down"} 
              size={18} 
              color={colors.textSecondary} 
            />
          </TouchableOpacity>
        </View>

        {/* Main Content */}
        <View style={styles.mainContent}>
          {/* Score Ring */}
          <View style={[styles.scoreRing, { width: circleSize, height: circleSize }]}>
            <Svg width={circleSize} height={circleSize}>
              <Defs>
                <SvgGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <Stop offset="0%" stopColor={config.gradient[0]} />
                  <Stop offset="100%" stopColor={config.gradient[1]} />
                </SvgGradient>
              </Defs>
              <G rotation="-90" origin={`${circleSize/2}, ${circleSize/2}`}>
                <Circle
                  cx={circleSize/2}
                  cy={circleSize/2}
                  r={radius}
                  stroke={isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)'}
                  strokeWidth={strokeWidth}
                  fill="transparent"
                />
                <Circle
                  cx={circleSize/2}
                  cy={circleSize/2}
                  r={radius}
                  stroke="url(#scoreGradient)"
                  strokeWidth={strokeWidth}
                  fill="transparent"
                  strokeLinecap="round"
                  strokeDasharray={circumference}
                  strokeDashoffset={strokeDashoffset}
                />
              </G>
            </Svg>
            <View style={styles.scoreCenter}>
              <Text style={[styles.scoreNumber, { color: config.gradient[0] }]}>{displayScore}</Text>
              <Text style={[styles.scoreMax, { color: colors.textSecondary }]}>/ 100</Text>
            </View>
          </View>

          {/* Score Info */}
          <View style={styles.scoreInfo}>
            <View style={styles.gradeRow}>
              <Text style={styles.gradeEmoji}>{config.emoji}</Text>
              <LinearGradient
                colors={config.gradient}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={styles.gradeBadge}
              >
                <Text style={styles.gradeText}>{config.label}</Text>
              </LinearGradient>
            </View>
            <Text style={[styles.gradeDesc, { color: colors.textSecondary }]}>{config.description}</Text>
            
            {/* Quick Stats */}
            <View style={styles.quickStats}>
              <View style={[styles.statPill, { backgroundColor: isDark ? 'rgba(16, 185, 129, 0.2)' : 'rgba(16, 185, 129, 0.15)' }]}>
                <MaterialCommunityIcons name="piggy-bank-outline" size={12} color="#10B981" />
                <Text style={[styles.statText, { color: '#10B981' }]}>{data.savings_rate.toFixed(0)}% saved</Text>
              </View>
              <View style={[styles.statPill, { backgroundColor: isDark ? 'rgba(59, 130, 246, 0.2)' : 'rgba(59, 130, 246, 0.15)' }]}>
                <MaterialCommunityIcons name="trending-up" size={12} color="#3B82F6" />
                <Text style={[styles.statText, { color: '#3B82F6' }]}>{data.investment_rate.toFixed(0)}% invested</Text>
              </View>
            </View>
          </View>
        </View>

        {/* Expanded Breakdown */}
        {expanded && (
          <View style={[styles.breakdown, { borderTopColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)' }]}>
            <Text style={[styles.breakdownTitle, { color: colors.textPrimary }]}>Score Breakdown</Text>
            <Text style={[styles.breakdownSubtitle, { color: colors.textSecondary }]}>Based on your financial activity</Text>
            
            <View style={styles.metricsContainer}>
              <MetricBar
                label="Savings Rate"
                value={data.savings_rate}
                maxValue={40}
                color="#10B981"
                isDark={isDark}
                icon="piggy-bank-outline"
              />
              <MetricBar
                label="Investment Rate"
                value={data.investment_rate}
                maxValue={30}
                color="#3B82F6"
                isDark={isDark}
                icon="trending-up"
              />
              <MetricBar
                label="Expense Control"
                value={Math.max(0, 100 - data.expense_ratio)}
                maxValue={100}
                color="#F59E0B"
                isDark={isDark}
                icon="wallet-outline"
              />
              <MetricBar
                label="Goal Progress"
                value={data.goal_progress}
                maxValue={100}
                color="#8B5CF6"
                isDark={isDark}
                icon="flag-checkered"
              />
            </View>

            {/* Tip */}
            <View style={[styles.tipBox, { backgroundColor: isDark ? 'rgba(139, 92, 246, 0.15)' : 'rgba(139, 92, 246, 0.1)' }]}>
              <MaterialCommunityIcons name="lightbulb-outline" size={18} color="#8B5CF6" />
              <Text style={[styles.tipText, { color: isDark ? '#C4B5FD' : '#7C3AED' }]}>
                {score < 50 
                  ? "Tip: Start with building an emergency fund of 3-6 months expenses"
                  : score < 70 
                    ? "Tip: Try to increase your investment allocation by 5% this month"
                    : "Tip: Consider diversifying into mutual funds or stocks for growth"
                }
              </Text>
            </View>
          </View>
        )}
      </LinearGradient>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: {
    borderRadius: 20,
    borderWidth: 1.5,
    padding: 16,
    marginBottom: 16,
    overflow: 'hidden',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  headerBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 20,
    gap: 6,
  },
  headerBadgeText: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    fontWeight: '600' as any,
  },
  expandBtn: {
    width: 28,
    height: 28,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  mainContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  scoreRing: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  scoreCenter: {
    position: 'absolute',
    alignItems: 'center',
  },
  scoreNumber: {
    fontSize: 32,
    fontFamily: 'DM Sans',
    fontWeight: '800' as any,
  },
  scoreMax: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    fontWeight: '500' as any,
    marginTop: -4,
  },
  scoreInfo: {
    flex: 1,
  },
  gradeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 6,
  },
  gradeEmoji: {
    fontSize: 20,
  },
  gradeBadge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  gradeText: {
    color: '#FFFFFF',
    fontSize: 13,
    fontFamily: 'DM Sans',
    fontWeight: '700' as any,
  },
  gradeDesc: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    lineHeight: 18,
    marginBottom: 10,
  },
  quickStats: {
    flexDirection: 'row',
    gap: 8,
    flexWrap: 'wrap',
  },
  statPill: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
    gap: 4,
  },
  statText: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    fontWeight: '600' as any,
  },
  breakdown: {
    marginTop: 16,
    paddingTop: 16,
    borderTopWidth: 1,
  },
  breakdownTitle: {
    fontSize: 15,
    fontFamily: 'DM Sans',
    fontWeight: '700' as any,
    marginBottom: 2,
  },
  breakdownSubtitle: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    marginBottom: 16,
  },
  metricsContainer: {
    gap: 4,
  },
  tipBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    padding: 12,
    borderRadius: 12,
    marginTop: 16,
    gap: 10,
  },
  tipText: {
    flex: 1,
    fontSize: 12,
    fontFamily: 'DM Sans',
    lineHeight: 18,
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 24,
  },
  emptyIcon: {
    width: 64,
    height: 64,
    borderRadius: 32,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  emptyTitle: {
    fontSize: 17,
    fontFamily: 'DM Sans',
    fontWeight: '700' as any,
    marginBottom: 6,
  },
  emptyDesc: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    textAlign: 'center',
    lineHeight: 18,
    paddingHorizontal: 20,
  },
});
