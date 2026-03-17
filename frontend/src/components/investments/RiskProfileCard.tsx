/**
 * Risk Profile Card Component
 * Displays risk profile assessment result and strategy recommendation
 */
import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Accent } from '../../utils/theme';
import { RISK_CATEGORY_LABELS } from './types';

interface RiskProfileCardProps {
  riskProfile: 'Conservative' | 'Moderate' | 'Aggressive';
  riskScore: number;
  riskBreakdown: Record<string, number>;
  riskSaved: boolean;
  colors: any;
  isDark: boolean;
  onRetake: () => void;
}

// Strategy configurations based on risk profile
const strategies = {
  Conservative: { 
    name: 'Safe Harbor', 
    allocation: [
      { name: 'Debt', p: 60, c: Accent.emerald }, 
      { name: 'Equity', p: 25, c: Accent.sapphire }, 
      { name: 'Gold', p: 15, c: Accent.amber }
    ] 
  },
  Moderate: { 
    name: 'Balanced Growth', 
    allocation: [
      { name: 'Equity', p: 40, c: Accent.sapphire }, 
      { name: 'Debt', p: 30, c: Accent.emerald }, 
      { name: 'Gold', p: 15, c: Accent.amber }, 
      { name: 'Alt', p: 15, c: Accent.amethyst }
    ] 
  },
  Aggressive: { 
    name: 'High Growth', 
    allocation: [
      { name: 'Equity', p: 70, c: Accent.sapphire }, 
      { name: 'Alt', p: 15, c: Accent.amethyst }, 
      { name: 'Debt', p: 10, c: Accent.emerald }, 
      { name: 'Gold', p: 5, c: Accent.amber }
    ] 
  },
};

export const RiskProfileCard: React.FC<RiskProfileCardProps> = ({
  riskProfile,
  riskScore,
  riskBreakdown,
  riskSaved,
  colors,
  isDark,
  onRetake,
}) => {
  const currentStrategy = strategies[riskProfile];
  
  const getBadgeStyle = () => {
    switch (riskProfile) {
      case 'Conservative':
        return { bg: 'rgba(59,130,246,0.15)', color: Accent.sapphire };
      case 'Moderate':
        return { bg: 'rgba(245,158,11,0.15)', color: Accent.amber };
      case 'Aggressive':
        return { bg: 'rgba(239,68,68,0.15)', color: Accent.ruby };
    }
  };
  
  const badgeStyle = getBadgeStyle();
  
  const getIcon = () => {
    switch (riskProfile) {
      case 'Conservative': return 'shield-check';
      case 'Moderate': return 'scale-balance';
      case 'Aggressive': return 'rocket-launch';
    }
  };

  return (
    <View 
      data-testid="risk-card" 
      style={[styles.riskCard, {
        backgroundColor: isDark ? 'rgba(10, 10, 11, 0.85)' : 'rgba(255, 255, 255, 0.85)',
        borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
      }]}
    >
      {/* Header */}
      <View style={styles.riskHeader}>
        <View style={[styles.riskBadge, { backgroundColor: badgeStyle.bg }]}>
          <MaterialCommunityIcons name={getIcon()} size={20} color={badgeStyle.color} />
          <Text data-testid="risk-profile-label" style={[styles.riskBadgeText, { color: badgeStyle.color }]}>
            {riskProfile}
          </Text>
          {riskSaved && riskScore > 0 && (
            <Text style={[styles.riskScoreText, { color: colors.textSecondary }]}>
              {riskScore.toFixed(1)}/5
            </Text>
          )}
        </View>
        <TouchableOpacity 
          data-testid="risk-retake-btn" 
          style={[styles.retakeBtn, { borderColor: colors.border }]} 
          onPress={onRetake}
        >
          <Text style={[styles.retakeBtnText, { color: colors.textSecondary }]}>
            {riskSaved ? 'Retake' : 'Take Assessment'}
          </Text>
        </TouchableOpacity>
      </View>

      {/* Score breakdown bars */}
      {riskSaved && Object.keys(riskBreakdown).length > 0 && (
        <View style={styles.breakdownSection}>
          {Object.entries(riskBreakdown).map(([cat, val]) => {
            const pct = (val / 5) * 100;
            const barColor = val <= 2 ? Accent.sapphire : val <= 3.5 ? Accent.amber : Accent.ruby;
            return (
              <View key={cat} data-testid={`risk-breakdown-${cat}`} style={styles.breakdownRow}>
                <Text style={[styles.breakdownLabel, { color: colors.textSecondary }]}>
                  {RISK_CATEGORY_LABELS[cat] || cat}
                </Text>
                <View style={[styles.breakdownBarBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
                  <View style={[styles.breakdownBarFill, { width: `${pct}%`, backgroundColor: barColor }]} />
                </View>
                <Text style={[styles.breakdownVal, { color: colors.textPrimary }]}>{val.toFixed(1)}</Text>
              </View>
            );
          })}
        </View>
      )}

      {/* Strategy */}
      <Text style={[styles.strategyName, { color: colors.textPrimary }]}>{currentStrategy.name} Strategy</Text>
      <View style={styles.strategyBar}>
        {currentStrategy.allocation.map((item, i) => (
          <View key={i} style={[styles.strategySegment, { width: `${item.p}%`, backgroundColor: item.c }]}>
            {item.p >= 15 && <Text style={styles.strategySegmentText}>{item.p}%</Text>}
          </View>
        ))}
      </View>
      <View style={styles.strategyLegend}>
        {currentStrategy.allocation.map((item, i) => (
          <View key={i} style={styles.strategyLegendItem}>
            <View style={[styles.strategyLegendDot, { backgroundColor: item.c }]} />
            <Text style={[styles.strategyLegendText, { color: colors.textSecondary }]}>
              {item.name} ({item.p}%)
            </Text>
          </View>
        ))}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  riskCard: { 
    borderRadius: 20, 
    padding: 20, 
    borderWidth: 1, 
    marginBottom: 20 
  },
  riskHeader: { 
    flexDirection: 'row', 
    justifyContent: 'space-between', 
    alignItems: 'center', 
    marginBottom: 14 
  },
  riskBadge: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    gap: 8, 
    paddingHorizontal: 14, 
    paddingVertical: 8, 
    borderRadius: 14 
  },
  riskBadgeText: { 
    fontSize: 14, 
    fontFamily: 'DM Sans', 
    fontWeight: '700' as any 
  },
  retakeBtn: { 
    paddingHorizontal: 14, 
    paddingVertical: 8, 
    borderRadius: 12, 
    borderWidth: 1 
  },
  retakeBtnText: { 
    fontSize: 12, 
    fontFamily: 'DM Sans', 
    fontWeight: '600' as any 
  },
  riskScoreText: { 
    fontSize: 12, 
    fontFamily: 'DM Sans', 
    fontWeight: '600' as any, 
    marginLeft: 4 
  },
  breakdownSection: { 
    marginBottom: 16, 
    gap: 10 
  },
  breakdownRow: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    gap: 8 
  },
  breakdownLabel: { 
    fontSize: 11, 
    fontFamily: 'DM Sans', 
    fontWeight: '600' as any, 
    width: 100 
  },
  breakdownBarBg: { 
    flex: 1, 
    height: 6, 
    borderRadius: 3, 
    overflow: 'hidden' 
  },
  breakdownBarFill: { 
    height: '100%', 
    borderRadius: 3 
  },
  breakdownVal: { 
    fontSize: 11, 
    fontFamily: 'DM Sans', 
    fontWeight: '700' as any, 
    width: 28, 
    textAlign: 'right' 
  },
  strategyName: { 
    fontSize: 17, 
    fontFamily: 'DM Sans', 
    fontWeight: '700' as any, 
    marginBottom: 14 
  },
  strategyBar: { 
    flexDirection: 'row', 
    height: 22, 
    borderRadius: 11, 
    overflow: 'hidden', 
    marginBottom: 12 
  },
  strategySegment: { 
    justifyContent: 'center', 
    alignItems: 'center' 
  },
  strategySegmentText: { 
    fontSize: 10, 
    fontFamily: 'DM Sans', 
    fontWeight: '700' as any, 
    color: '#fff' 
  },
  strategyLegend: { 
    flexDirection: 'row', 
    flexWrap: 'wrap', 
    gap: 12 
  },
  strategyLegendItem: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    gap: 6 
  },
  strategyLegendDot: { 
    width: 8, 
    height: 8, 
    borderRadius: 4 
  },
  strategyLegendText: { 
    fontSize: 12 
  },
});

export default RiskProfileCard;
