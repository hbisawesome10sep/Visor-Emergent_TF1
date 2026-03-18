import React, { useRef, forwardRef } from 'react';
import { View, Text, StyleSheet, Platform } from 'react-native';
import Svg, { Circle, Defs, LinearGradient as SvgGradient, Stop, G } from 'react-native-svg';
import { LinearGradient } from 'expo-linear-gradient';
import { MaterialCommunityIcons } from '@expo/vector-icons';

const DIM_CONFIG: Record<string, { label: string; icon: string; color: string }> = {
  savings_rate: { label: 'Savings Rate', icon: 'piggy-bank-outline', color: '#10B981' },
  debt_load: { label: 'Debt Load', icon: 'scale-balance', color: '#F59E0B' },
  investment_rate: { label: 'Investment Rate', icon: 'trending-up', color: '#3B82F6' },
  emergency_fund: { label: 'Emergency Fund', icon: 'shield-check-outline', color: '#06B6D4' },
  cc_utilization: { label: 'CC Utilization', icon: 'credit-card-outline', color: '#8B5CF6' },
  goal_progress: { label: 'Goal Progress', icon: 'flag-checkered', color: '#EC4899' },
  insurance_cover: { label: 'Insurance Cover', icon: 'heart-pulse', color: '#EF4444' },
  net_worth_growth: { label: 'Net Worth Growth', icon: 'chart-timeline-variant', color: '#14B8A6' },
};

const getGradeColors = (score: number) => {
  if (score >= 800) return ['#10B981', '#059669'];
  if (score >= 650) return ['#14B8A6', '#0D9488'];
  if (score >= 450) return ['#F59E0B', '#D97706'];
  if (score >= 250) return ['#F97316', '#EA580C'];
  return ['#EF4444', '#DC2626'];
};

const getGradeLabel = (score: number) => {
  if (score >= 800) return 'Excellent';
  if (score >= 650) return 'Good';
  if (score >= 450) return 'Fair';
  if (score >= 250) return 'Needs Work';
  return 'Critical';
};

type Dimension = { score: number; raw_value: number };
type Props = {
  composite_score: number;
  dimensions: Record<string, Dimension>;
  score_change: number;
  userName?: string;
};

export const ShareScoreCard = forwardRef<View, Props>(
  ({ composite_score, dimensions, score_change, userName }, ref) => {
    const gradeColors = getGradeColors(composite_score);
    const grade = getGradeLabel(composite_score);
    const scoreRatio = Math.min(1, composite_score / 1000);
    const circleSize = 140;
    const strokeW = 12;
    const radius = (circleSize - strokeW) / 2;
    const circumference = 2 * Math.PI * radius;
    const dashOffset = circumference * (1 - scoreRatio);

    return (
      <View ref={ref} style={ss.container} collapsable={false}>
        {/* Background */}
        <LinearGradient
          colors={['#0F172A', '#1E293B']}
          style={ss.bg}
        >
          {/* Header */}
          <View style={ss.headerRow}>
            <View style={ss.logoBadge}>
              <MaterialCommunityIcons name="shield-check" size={16} color="#10B981" />
              <Text style={ss.logoText}>Visor</Text>
            </View>
            <Text style={ss.dateText}>
              {new Date().toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })}
            </Text>
          </View>

          {/* Title */}
          <Text style={ss.title}>Financial Health Score</Text>
          {userName ? (
            <Text style={ss.subtitle}>{userName}'s Score</Text>
          ) : null}

          {/* Score Ring */}
          <View style={ss.scoreSection}>
            <View style={{ alignItems: 'center', justifyContent: 'center', width: circleSize, height: circleSize }}>
              <Svg width={circleSize} height={circleSize}>
                <Defs>
                  <SvgGradient id="shareGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <Stop offset="0%" stopColor={gradeColors[0]} />
                    <Stop offset="100%" stopColor={gradeColors[1]} />
                  </SvgGradient>
                </Defs>
                <G rotation="-90" origin={`${circleSize / 2}, ${circleSize / 2}`}>
                  <Circle cx={circleSize / 2} cy={circleSize / 2} r={radius} stroke="rgba(255,255,255,0.08)" strokeWidth={strokeW} fill="transparent" />
                  <Circle cx={circleSize / 2} cy={circleSize / 2} r={radius} stroke="url(#shareGrad)" strokeWidth={strokeW} fill="transparent" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={dashOffset} />
                </G>
              </Svg>
              <View style={{ position: 'absolute', alignItems: 'center' }}>
                <Text style={[ss.scoreNum, { color: gradeColors[0] }]}>{composite_score}</Text>
                <Text style={ss.scoreMax}>/ 1000</Text>
              </View>
            </View>

            <LinearGradient
              colors={[gradeColors[0], gradeColors[1]]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={ss.gradeBadge}
            >
              <Text style={ss.gradeText}>{grade}</Text>
            </LinearGradient>

            {score_change !== 0 && (
              <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 6 }}>
                <MaterialCommunityIcons
                  name={score_change >= 0 ? 'arrow-up' : 'arrow-down'}
                  size={14}
                  color={score_change >= 0 ? '#10B981' : '#EF4444'}
                />
                <Text style={{ color: score_change >= 0 ? '#10B981' : '#EF4444', fontSize: 12, fontWeight: '600' }}>
                  {Math.abs(score_change)} pts this month
                </Text>
              </View>
            )}
          </View>

          {/* Dimension Bars */}
          <View style={ss.dimsContainer}>
            {Object.entries(dimensions).map(([key, dim]) => {
              const cfg = DIM_CONFIG[key];
              if (!cfg) return null;
              return (
                <View key={key} style={ss.dimRow}>
                  <View style={ss.dimLabelRow}>
                    <View style={[ss.dimDot, { backgroundColor: cfg.color }]} />
                    <Text style={ss.dimLabel}>{cfg.label}</Text>
                    <Text style={[ss.dimScore, { color: cfg.color }]}>{dim.score}</Text>
                  </View>
                  <View style={ss.dimTrack}>
                    <View style={[ss.dimFill, { backgroundColor: cfg.color, width: `${dim.score}%` as any }]} />
                  </View>
                </View>
              );
            })}
          </View>

          {/* Footer */}
          <View style={ss.footer}>
            <Text style={ss.footerText}>Track your finances with</Text>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
              <MaterialCommunityIcons name="shield-check" size={14} color="#10B981" />
              <Text style={ss.footerBrand}>Visor Finance</Text>
            </View>
          </View>
        </LinearGradient>
      </View>
    );
  }
);

const ss = StyleSheet.create({
  container: {
    width: 360,
    borderRadius: 24,
    overflow: 'hidden',
  },
  bg: {
    padding: 24,
    paddingBottom: 20,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  logoBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: 'rgba(16,185,129,0.12)',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 12,
  },
  logoText: {
    color: '#10B981',
    fontSize: 14,
    fontWeight: '800',
  },
  dateText: {
    color: 'rgba(255,255,255,0.5)',
    fontSize: 12,
  },
  title: {
    color: '#F8FAFC',
    fontSize: 20,
    fontWeight: '800',
    textAlign: 'center',
  },
  subtitle: {
    color: 'rgba(255,255,255,0.5)',
    fontSize: 13,
    textAlign: 'center',
    marginTop: 4,
  },
  scoreSection: {
    alignItems: 'center',
    marginVertical: 20,
  },
  scoreNum: {
    fontSize: 44,
    fontWeight: '900',
  },
  scoreMax: {
    fontSize: 13,
    fontWeight: '500',
    color: 'rgba(255,255,255,0.4)',
    marginTop: -4,
  },
  gradeBadge: {
    paddingHorizontal: 20,
    paddingVertical: 6,
    borderRadius: 14,
    marginTop: 12,
  },
  gradeText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '800',
  },
  dimsContainer: {
    gap: 8,
    marginBottom: 20,
  },
  dimRow: {},
  dimLabelRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  dimDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 8,
  },
  dimLabel: {
    flex: 1,
    fontSize: 12,
    fontWeight: '500',
    color: 'rgba(255,255,255,0.7)',
  },
  dimScore: {
    fontSize: 13,
    fontWeight: '700',
    minWidth: 28,
    textAlign: 'right',
  },
  dimTrack: {
    height: 5,
    borderRadius: 3,
    backgroundColor: 'rgba(255,255,255,0.06)',
    overflow: 'hidden',
  },
  dimFill: {
    height: '100%',
    borderRadius: 3,
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 6,
    paddingTop: 16,
    borderTopWidth: 0.5,
    borderTopColor: 'rgba(255,255,255,0.08)',
  },
  footerText: {
    color: 'rgba(255,255,255,0.4)',
    fontSize: 11,
  },
  footerBrand: {
    color: '#10B981',
    fontSize: 12,
    fontWeight: '700',
  },
});
