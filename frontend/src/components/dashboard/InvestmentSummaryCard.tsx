import React, { useState, useEffect, useCallback, useRef } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, TouchableOpacity, Animated } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { apiRequest } from '../../utils/api';
import { Accent } from '../../utils/theme';

type AllocationItem = {
  category: string;
  invested: number;
  current_value: number;
  percentage: number;
  count: number;
};

type InvData = {
  total_invested: number;
  current_value: number;
  absolute_gain: number;
  absolute_return_pct: number;
  xirr: number | null;
  holdings_count: number;
  allocation: AllocationItem[];
};

type Props = { token: string; isDark: boolean; colors: any; onPress?: () => void };

const fmtINR = (n: number) => {
  if (Math.abs(n) >= 10000000) return `${(n / 10000000).toFixed(2)}Cr`;
  if (Math.abs(n) >= 100000) return `${(n / 100000).toFixed(2)}L`;
  if (Math.abs(n) >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return n.toFixed(0);
};

const CAT_COLORS: Record<string, string> = {
  'Stock': Accent.sapphire,
  'Mutual Fund': Accent.emerald,
  'Gold': '#F59E0B',
  'NPS': '#8B5CF6',
  'PPF': '#06B6D4',
  'Fixed Deposit': '#EC4899',
  'Other': '#6B7280',
};

export const InvestmentSummaryCard = ({ token, isDark, colors, onPress }: Props) => {
  const [data, setData] = useState<InvData | null>(null);
  const [insight, setInsight] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [isFlipped, setIsFlipped] = useState(false);
  const flipAnim = useRef(new Animated.Value(0)).current;

  const fetchData = useCallback(async () => {
    try {
      const [res, insightRes] = await Promise.all([
        apiRequest('/dashboard/investment-summary', { token }),
        apiRequest('/dashboard/investment-insight', { token }).catch(() => null),
      ]);
      setData(res);
      if (insightRes?.insight) setInsight(insightRes.insight);
    } catch (e) {
      console.warn('Inv summary fetch error:', e);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const toggleFlip = () => {
    const toValue = isFlipped ? 0 : 1;
    Animated.spring(flipAnim, {
      toValue,
      friction: 8,
      tension: 10,
      useNativeDriver: true,
    }).start();
    setIsFlipped(!isFlipped);
  };

  const frontInterpolate = flipAnim.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: ['0deg', '90deg', '180deg'],
  });
  const backInterpolate = flipAnim.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: ['180deg', '270deg', '360deg'],
  });
  const frontOpacity = flipAnim.interpolate({
    inputRange: [0, 0.5, 0.5, 1],
    outputRange: [1, 1, 0, 0],
  });
  const backOpacity = flipAnim.interpolate({
    inputRange: [0, 0.5, 0.5, 1],
    outputRange: [0, 0, 1, 1],
  });

  if (loading) {
    return (
      <View style={[s.card, { backgroundColor: isDark ? 'rgba(10,10,11,0.9)' : 'rgba(255,255,255,0.95)', borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
        <ActivityIndicator size="small" color={colors.primary} style={{ padding: 32 }} />
      </View>
    );
  }

  if (!data || (data.total_invested === 0 && data.holdings_count === 0)) {
    return (
      <TouchableOpacity testID="investment-summary-empty" onPress={onPress} activeOpacity={0.85} style={[s.card, { backgroundColor: isDark ? 'rgba(59,130,246,0.08)' : 'rgba(59,130,246,0.04)', borderColor: isDark ? 'rgba(59,130,246,0.2)' : 'rgba(59,130,246,0.15)' }]}>
        <View style={{ alignItems: 'center', paddingVertical: 16 }}>
          <MaterialCommunityIcons name="chart-areaspline" size={28} color={Accent.sapphire} />
          <Text style={[s.emptyTitle, { color: colors.textPrimary }]}>No Investments Yet</Text>
          <Text style={[s.emptyDesc, { color: colors.textSecondary }]}>Upload eCAS or add holdings to see portfolio summary</Text>
        </View>
      </TouchableOpacity>
    );
  }

  const isGain = data.absolute_gain >= 0;
  const allocation = data.allocation || [];

  return (
    <View style={{ marginBottom: 16 }}>
      {/* Front Side */}
      <Animated.View
        style={[
          { transform: [{ perspective: 1000 }, { rotateY: frontInterpolate }], opacity: frontOpacity },
          isFlipped && { position: 'absolute', top: 0, left: 0, right: 0 },
        ]}
        pointerEvents={isFlipped ? 'none' : 'auto'}
      >
        <TouchableOpacity testID="investment-summary-card" onPress={onPress} onLongPress={toggleFlip} activeOpacity={0.9}>
          <LinearGradient
            colors={isDark ? ['rgba(59,130,246,0.12)', 'rgba(99,102,241,0.06)'] : ['rgba(59,130,246,0.06)', 'rgba(99,102,241,0.03)']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={[s.card, { borderColor: isDark ? 'rgba(59,130,246,0.25)' : 'rgba(59,130,246,0.15)' }]}
          >
            <View style={s.headerRow}>
              <View style={[s.iconBg, { backgroundColor: isDark ? 'rgba(59,130,246,0.15)' : 'rgba(59,130,246,0.1)' }]}>
                <MaterialCommunityIcons name="chart-areaspline" size={18} color={Accent.sapphire} />
              </View>
              <Text style={[s.title, { color: colors.textSecondary }]}>Investments</Text>
              <TouchableOpacity data-testid="flip-investment-card" onPress={toggleFlip} style={[s.flipHint, { backgroundColor: isDark ? 'rgba(59,130,246,0.15)' : 'rgba(59,130,246,0.08)' }]}>
                <MaterialCommunityIcons name="rotate-3d-variant" size={14} color={Accent.sapphire} />
                <Text style={{ fontSize: 10, color: Accent.sapphire, fontWeight: '600' }}>Flip</Text>
              </TouchableOpacity>
            </View>

            <View style={s.valuesRow}>
              <View style={{ flex: 1 }}>
                <Text style={[s.label, { color: colors.textSecondary }]}>Invested</Text>
                <Text style={[s.value, { color: colors.textPrimary }]} numberOfLines={1} adjustsFontSizeToFit minimumFontScale={0.75}>Rs {fmtINR(data.total_invested)}</Text>
              </View>
              <MaterialCommunityIcons name="arrow-right-thin" size={18} color={colors.textSecondary} style={{ marginHorizontal: 6, marginTop: 10 }} />
              <View style={{ flex: 1, alignItems: 'flex-end' }}>
                <Text style={[s.label, { color: colors.textSecondary }]}>Current Value</Text>
                <Text style={[s.value, { color: isGain ? Accent.emerald : Accent.ruby }]} numberOfLines={1} adjustsFontSizeToFit minimumFontScale={0.75}>Rs {fmtINR(data.current_value)}</Text>
              </View>
            </View>

            <View style={[s.returnRow, { backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)' }]}>
              <View style={s.returnItem}>
                <Text style={[s.returnLabel, { color: colors.textSecondary }]}>Returns</Text>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                  <MaterialCommunityIcons name={isGain ? 'trending-up' : 'trending-down'} size={14} color={isGain ? Accent.emerald : Accent.ruby} />
                  <Text style={[s.returnVal, { color: isGain ? Accent.emerald : Accent.ruby }]}>
                    {isGain ? '+' : ''}{data.absolute_return_pct.toFixed(1)}%
                  </Text>
                </View>
              </View>
              {data.xirr !== null && data.xirr < 500 && (
                <View style={s.returnItem}>
                  <Text style={[s.returnLabel, { color: colors.textSecondary }]}>XIRR</Text>
                  <Text style={[s.returnVal, { color: data.xirr >= 0 ? Accent.emerald : Accent.ruby }]}>
                    {data.xirr >= 0 ? '+' : ''}{data.xirr.toFixed(1)}%
                  </Text>
                </View>
              )}
              <View style={s.returnItem}>
                <Text style={[s.returnLabel, { color: colors.textSecondary }]}>P&L</Text>
                <Text style={[s.returnVal, { color: isGain ? Accent.emerald : Accent.ruby }]}>
                  {isGain ? '+' : ''}Rs {fmtINR(data.absolute_gain)}
                </Text>
              </View>
            </View>
          </LinearGradient>
        </TouchableOpacity>
      </Animated.View>

      {/* Back Side */}
      <Animated.View
        style={[
          { transform: [{ perspective: 1000 }, { rotateY: backInterpolate }], opacity: backOpacity },
          !isFlipped && { position: 'absolute', top: 0, left: 0, right: 0 },
        ]}
        pointerEvents={isFlipped ? 'auto' : 'none'}
      >
        <TouchableOpacity onPress={toggleFlip} activeOpacity={0.95}>
          <LinearGradient
            colors={isDark ? ['rgba(99,102,241,0.12)', 'rgba(59,130,246,0.06)'] : ['rgba(99,102,241,0.06)', 'rgba(59,130,246,0.03)']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={[s.card, { borderColor: isDark ? 'rgba(99,102,241,0.25)' : 'rgba(99,102,241,0.15)' }]}
          >
            {/* Header */}
            <View style={s.headerRow}>
              <View style={[s.iconBg, { backgroundColor: isDark ? 'rgba(99,102,241,0.15)' : 'rgba(99,102,241,0.1)' }]}>
                <MaterialCommunityIcons name="chart-donut" size={18} color="#6366F1" />
              </View>
              <Text style={[s.title, { color: colors.textSecondary }]}>Asset Allocation</Text>
              <TouchableOpacity onPress={toggleFlip} style={[s.flipHint, { backgroundColor: isDark ? 'rgba(99,102,241,0.15)' : 'rgba(99,102,241,0.08)' }]}>
                <MaterialCommunityIcons name="rotate-3d-variant" size={14} color="#6366F1" />
                <Text style={{ fontSize: 10, color: '#6366F1', fontWeight: '600' }}>Flip</Text>
              </TouchableOpacity>
            </View>

            {/* Allocation Bars */}
            {allocation.length > 0 ? (
              <View style={{ gap: 8, marginBottom: 12 }}>
                {allocation.map((item) => {
                  const color = CAT_COLORS[item.category] || CAT_COLORS.Other;
                  return (
                    <View key={item.category} data-testid={`allocation-${item.category.toLowerCase()}`}>
                      <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 }}>
                        <Text style={{ fontSize: 12, fontWeight: '600', color: colors.textPrimary }}>
                          {item.category} ({item.count})
                        </Text>
                        <Text style={{ fontSize: 12, fontWeight: '700', color }}>
                          {item.percentage.toFixed(1)}% - Rs {fmtINR(item.current_value)}
                        </Text>
                      </View>
                      <View style={[s.barBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)' }]}>
                        <View style={[s.barFill, { width: `${Math.max(2, item.percentage)}%`, backgroundColor: color }]} />
                      </View>
                    </View>
                  );
                })}
              </View>
            ) : (
              <Text style={{ fontSize: 12, color: colors.textSecondary, marginBottom: 12 }}>No allocation data</Text>
            )}

            {/* AI Insight */}
            {insight ? (
              <View style={[s.insightBox, { backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)' }]}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                  <MaterialCommunityIcons name="lightbulb-on-outline" size={14} color="#F59E0B" />
                  <Text style={{ fontSize: 10, fontWeight: '700', color: '#F59E0B', textTransform: 'uppercase', letterSpacing: 0.5 }}>AI Insight</Text>
                </View>
                <Text style={{ fontSize: 12, lineHeight: 17, color: colors.textPrimary, fontWeight: '500' }}>{insight}</Text>
              </View>
            ) : null}
          </LinearGradient>
        </TouchableOpacity>
      </Animated.View>
    </View>
  );
};

const s = StyleSheet.create({
  card: { borderRadius: 18, borderWidth: 1, padding: 16, overflow: 'hidden' },
  headerRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 12 },
  iconBg: { width: 32, height: 32, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 14, fontWeight: '600', flex: 1 },
  flipHint: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8 },
  countBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8 },
  countText: { fontSize: 11, fontWeight: '600' },
  valuesRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 14 },
  label: { fontSize: 11, fontWeight: '500', marginBottom: 2 },
  value: { fontSize: 18, fontWeight: '700' },
  returnRow: { flexDirection: 'row', borderRadius: 12, padding: 12, gap: 4 },
  returnItem: { flex: 1, alignItems: 'center' },
  returnLabel: { fontSize: 10, fontWeight: '500', marginBottom: 2 },
  returnVal: { fontSize: 13, fontWeight: '700' },
  emptyTitle: { fontSize: 15, fontWeight: '700', marginTop: 8, marginBottom: 4 },
  emptyDesc: { fontSize: 12, textAlign: 'center', paddingHorizontal: 20 },
  barBg: { height: 6, borderRadius: 3, overflow: 'hidden' },
  barFill: { height: 6, borderRadius: 3 },
  insightBox: { borderRadius: 12, padding: 12 },
});
