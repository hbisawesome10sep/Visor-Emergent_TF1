import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import Svg, { Circle, G } from 'react-native-svg';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Accent } from '../../src/utils/theme';

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

type Props = {
  healthScore: number;
  breakdown: { savings: number; investments: number; spending: number; goals: number };
  savingsRate: number;
  spendingRate: number;
  investmentRate: number;
  goalProgress: number;
  isDark: boolean;
  colors: any;
};

export const HealthScoreCard = ({ healthScore, breakdown, savingsRate, spendingRate, investmentRate, goalProgress, isDark, colors }: Props) => {
  const [showBack, setShowBack] = React.useState(false);
  const scoreColor = getScoreColor(healthScore);
  const scoreInfo = getScoreLabel(healthScore);

  return (
    <TouchableOpacity
      activeOpacity={0.95}
      onPress={() => setShowBack(!showBack)}
      data-testid="health-score-card"
      style={[styles.card, {
        backgroundColor: isDark ? 'rgba(16, 185, 129, 0.1)' : 'rgba(16, 185, 129, 0.08)',
        borderColor: isDark ? 'rgba(16, 185, 129, 0.3)' : 'rgba(16, 185, 129, 0.2)',
      }]}
    >
      <TouchableOpacity
        style={[styles.flipBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)' }]}
        onPress={() => setShowBack(!showBack)}
      >
        <MaterialCommunityIcons name={showBack ? "rotate-left" : "information-outline"} size={16} color={colors.textSecondary} />
      </TouchableOpacity>

      {!showBack ? (
        <View style={styles.front}>
          <View style={styles.row}>
            <View style={styles.ringBox}>
              <Svg width={100} height={100}>
                <G rotation="-90" origin="50, 50">
                  <Circle cx="50" cy="50" r="42" stroke={isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)'} strokeWidth="10" fill="transparent" />
                  <Circle cx="50" cy="50" r="42" stroke={scoreColor} strokeWidth="10" fill="transparent" strokeLinecap="round"
                    strokeDasharray={`${2 * Math.PI * 42}`}
                    strokeDashoffset={(1 - healthScore / 100) * 2 * Math.PI * 42}
                  />
                </G>
              </Svg>
              <View style={styles.center}>
                <Text style={[styles.scoreNum, { color: scoreColor }]}>{healthScore}</Text>
                <Text style={[styles.scoreOf, { color: colors.textSecondary }]}>/100</Text>
              </View>
            </View>
            <View style={styles.info}>
              <Text style={[styles.title, { color: colors.textPrimary }]}>Your Financial Health Score</Text>
              <View style={[styles.badge, { backgroundColor: `${scoreInfo.color}20` }]}>
                <Text style={[styles.badgeText, { color: scoreInfo.color }]}>{scoreInfo.label}</Text>
              </View>
              <Text style={[styles.desc, { color: colors.textSecondary }]}>
                {healthScore >= 70 ? "Great financial habits! Keep it up." : healthScore >= 50 ? "Good progress. Focus on savings & investments." : "Needs attention. Prioritize emergency fund."}
              </Text>
            </View>
          </View>
        </View>
      ) : (
        <View style={styles.back}>
          <Text style={[styles.backTitle, { color: colors.textPrimary }]}>How Your Score is Calculated</Text>
          <Text style={[styles.backDesc, { color: colors.textSecondary }]}>Based on RBI financial health framework</Text>
          <View style={[styles.breakdownBox, { backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)' }]}>
            {[
              { label: `Savings (${savingsRate.toFixed(0)}% of income)`, val: `${Math.round(breakdown.savings)}/25` },
              { label: `Spending (${spendingRate.toFixed(0)}% of income)`, val: `${Math.round(breakdown.spending)}/25` },
              { label: `Investments (${investmentRate.toFixed(0)}% of income)`, val: `${Math.round(breakdown.investments)}/25` },
              { label: `Goals (${goalProgress.toFixed(0)}% achieved)`, val: `${Math.round(breakdown.goals)}/25` },
            ].map((item, i) => (
              <View key={i} style={styles.breakdownRow}>
                <Text style={[styles.breakdownLabel, { color: colors.textSecondary }]}>{item.label}</Text>
                <Text style={[styles.breakdownValue, { color: colors.textPrimary }]}>{item.val}</Text>
              </View>
            ))}
            <View style={[styles.totalRow, { borderTopColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)' }]}>
              <Text style={[styles.totalLabel, { color: colors.textPrimary }]}>Total Score</Text>
              <Text style={[styles.totalValue, { color: scoreColor }]}>{healthScore}/100</Text>
            </View>
          </View>
        </View>
      )}
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: { borderRadius: 20, borderWidth: 1, padding: 20, marginBottom: 16, position: 'relative' },
  flipBtn: { position: 'absolute', top: 12, right: 12, width: 28, height: 28, borderRadius: 14, alignItems: 'center', justifyContent: 'center', zIndex: 1 },
  front: { minHeight: 100 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 16 },
  ringBox: { width: 100, height: 100, alignItems: 'center', justifyContent: 'center' },
  center: { position: 'absolute', alignItems: 'center' },
  scoreNum: { fontSize: 28, fontFamily: 'DM Sans', fontWeight: '800' as any },
  scoreOf: { fontSize: 12, fontFamily: 'DM Sans', marginTop: -2 },
  info: { flex: 1 },
  title: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '700' as any, marginBottom: 6 },
  badge: { alignSelf: 'flex-start', paddingHorizontal: 10, paddingVertical: 3, borderRadius: 8, marginBottom: 6 },
  badgeText: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '700' as any },
  desc: { fontSize: 12, fontFamily: 'DM Sans', lineHeight: 16 },
  back: { minHeight: 100 },
  backTitle: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '700' as any, marginBottom: 4 },
  backDesc: { fontSize: 12, fontFamily: 'DM Sans', marginBottom: 12 },
  breakdownBox: { borderRadius: 12, padding: 12 },
  breakdownRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8 },
  breakdownLabel: { fontSize: 13, fontFamily: 'DM Sans' },
  breakdownValue: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '600' as any },
  totalRow: { flexDirection: 'row', justifyContent: 'space-between', paddingTop: 10, marginTop: 6, borderTopWidth: 1 },
  totalLabel: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700' as any },
  totalValue: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '800' as any },
});
