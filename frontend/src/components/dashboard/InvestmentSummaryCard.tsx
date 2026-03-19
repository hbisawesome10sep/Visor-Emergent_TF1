import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, TouchableOpacity } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { apiRequest } from '../../utils/api';
import { Accent } from '../../utils/theme';

type InvData = {
  total_invested: number;
  current_value: number;
  absolute_gain: number;
  absolute_return_pct: number;
  xirr: number | null;
  holdings_count: number;
};

type Props = { token: string; isDark: boolean; colors: any; onPress?: () => void };

const fmtINR = (n: number) => {
  if (Math.abs(n) >= 10000000) return `${(n / 10000000).toFixed(2)}Cr`;
  if (Math.abs(n) >= 100000) return `${(n / 100000).toFixed(2)}L`;
  if (Math.abs(n) >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return n.toFixed(0);
};

export const InvestmentSummaryCard = ({ token, isDark, colors, onPress }: Props) => {
  const [data, setData] = useState<InvData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const res = await apiRequest('/dashboard/investment-summary', { token });
      setData(res);
    } catch (e) {
      console.warn('Inv summary fetch error:', e);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchData(); }, [fetchData]);

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

  return (
    <TouchableOpacity testID="investment-summary-card" onPress={onPress} activeOpacity={0.9}>
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
          <View style={[s.countBadge, { backgroundColor: isDark ? 'rgba(59,130,246,0.2)' : 'rgba(59,130,246,0.1)' }]}>
            <Text style={[s.countText, { color: Accent.sapphire }]}>{data.holdings_count} holdings</Text>
          </View>
        </View>

        <View style={s.valuesRow}>
          <View style={{ flex: 1 }}>
            <Text style={[s.label, { color: colors.textSecondary }]}>Invested</Text>
            <Text style={[s.value, { color: colors.textPrimary }]} numberOfLines={1}>Rs {fmtINR(data.total_invested)}</Text>
          </View>
          <MaterialCommunityIcons name="arrow-right-thin" size={18} color={colors.textSecondary} style={{ marginHorizontal: 6, marginTop: 10 }} />
          <View style={{ flex: 1, alignItems: 'flex-end' }}>
            <Text style={[s.label, { color: colors.textSecondary }]}>Current Value</Text>
            <Text style={[s.value, { color: isGain ? Accent.emerald : Accent.ruby }]} numberOfLines={1}>Rs {fmtINR(data.current_value)}</Text>
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
  );
};

const s = StyleSheet.create({
  card: { borderRadius: 18, borderWidth: 1, padding: 16, marginBottom: 16, overflow: 'hidden' },
  headerRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 12 },
  iconBg: { width: 32, height: 32, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 14, fontWeight: '600', flex: 1 },
  countBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8 },
  countText: { fontSize: 11, fontWeight: '600' },
  valuesRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 14 },
  arrowCol: { paddingHorizontal: 12 },
  label: { fontSize: 11, fontWeight: '500', marginBottom: 2 },
  value: { fontSize: 18, fontWeight: '700' },
  returnRow: { flexDirection: 'row', borderRadius: 12, padding: 12, gap: 4 },
  returnItem: { flex: 1, alignItems: 'center' },
  returnLabel: { fontSize: 10, fontWeight: '500', marginBottom: 2 },
  returnVal: { fontSize: 13, fontWeight: '700' },
  emptyTitle: { fontSize: 15, fontWeight: '700', marginTop: 8, marginBottom: 4 },
  emptyDesc: { fontSize: 12, textAlign: 'center', paddingHorizontal: 20 },
});
