import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { apiRequest } from '../../utils/api';
import { Accent } from '../../utils/theme';

type NetWorthData = {
  net_worth: number;
  total_assets: number;
  total_liabilities: number;
  breakdown: {
    assets: { bank_balance: number; investments: number };
    liabilities: { loans: number; credit_cards: number };
  };
};

type Props = { token: string; isDark: boolean; colors: any };

const formatINR = (n: number) => {
  if (Math.abs(n) >= 10000000) return `${(n / 10000000).toFixed(1)}Cr`;
  if (Math.abs(n) >= 100000) return `${(n / 100000).toFixed(1)}L`;
  if (Math.abs(n) >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return n.toFixed(0);
};

export const NetWorthCard = ({ token, isDark, colors }: Props) => {
  const [data, setData] = useState<NetWorthData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const res = await apiRequest('/dashboard/net-worth', { token });
      setData(res);
    } catch (e) {
      console.warn('Net worth fetch error:', e);
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

  if (!data) return null;

  const isPositive = data.net_worth >= 0;
  const assetPct = data.total_assets > 0 ? Math.min(100, (data.total_assets / (data.total_assets + data.total_liabilities)) * 100) : 50;

  return (
    <View testID="net-worth-card" style={[s.card, { backgroundColor: isDark ? 'rgba(10,10,11,0.9)' : 'rgba(255,255,255,0.95)', borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
      <View style={s.headerRow}>
        <View style={[s.iconBg, { backgroundColor: isDark ? 'rgba(20,184,166,0.15)' : 'rgba(20,184,166,0.1)' }]}>
          <MaterialCommunityIcons name="bank" size={18} color={Accent.teal} />
        </View>
        <Text style={[s.title, { color: colors.textSecondary }]}>Net Worth</Text>
      </View>

      <Text testID="net-worth-value" style={[s.amount, { color: isPositive ? Accent.emerald : Accent.ruby }]}>
        {isPositive ? '' : '-'}Rs {formatINR(Math.abs(data.net_worth))}
      </Text>

      {/* Assets vs Liabilities Bar */}
      <View style={s.barContainer}>
        <View style={[s.barTrack, { backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)' }]}>
          <LinearGradient colors={[Accent.emerald, '#059669']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={[s.barFill, { width: `${assetPct}%` as any }]} />
        </View>
      </View>

      <View style={s.splitRow}>
        <View style={s.splitItem}>
          <View style={[s.splitDot, { backgroundColor: Accent.emerald }]} />
          <Text style={[s.splitLabel, { color: colors.textSecondary }]}>Assets</Text>
          <Text style={[s.splitValue, { color: Accent.emerald }]}>Rs {formatINR(data.total_assets)}</Text>
        </View>
        <View style={s.splitItem}>
          <View style={[s.splitDot, { backgroundColor: Accent.ruby }]} />
          <Text style={[s.splitLabel, { color: colors.textSecondary }]}>Liabilities</Text>
          <Text style={[s.splitValue, { color: Accent.ruby }]}>Rs {formatINR(data.total_liabilities)}</Text>
        </View>
      </View>

      {/* Detail breakdown */}
      <View style={[s.breakdown, { borderTopColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)' }]}>
        <View style={s.breakdownRow}>
          <MaterialCommunityIcons name="wallet-outline" size={14} color={colors.textSecondary} />
          <Text style={[s.breakdownLabel, { color: colors.textSecondary }]}>Bank & Savings</Text>
          <Text style={[s.breakdownVal, { color: colors.textPrimary }]}>Rs {formatINR(data.breakdown.assets.bank_balance)}</Text>
        </View>
        <View style={s.breakdownRow}>
          <MaterialCommunityIcons name="chart-line" size={14} color={colors.textSecondary} />
          <Text style={[s.breakdownLabel, { color: colors.textSecondary }]}>Investments</Text>
          <Text style={[s.breakdownVal, { color: colors.textPrimary }]}>Rs {formatINR(data.breakdown.assets.investments)}</Text>
        </View>
        <View style={s.breakdownRow}>
          <MaterialCommunityIcons name="bank-transfer-out" size={14} color={colors.textSecondary} />
          <Text style={[s.breakdownLabel, { color: colors.textSecondary }]}>Loans</Text>
          <Text style={[s.breakdownVal, { color: Accent.ruby }]}>Rs {formatINR(data.breakdown.liabilities.loans)}</Text>
        </View>
        <View style={s.breakdownRow}>
          <MaterialCommunityIcons name="credit-card-outline" size={14} color={colors.textSecondary} />
          <Text style={[s.breakdownLabel, { color: colors.textSecondary }]}>Credit Cards</Text>
          <Text style={[s.breakdownVal, { color: Accent.ruby }]}>Rs {formatINR(data.breakdown.liabilities.credit_cards)}</Text>
        </View>
      </View>
    </View>
  );
};

const s = StyleSheet.create({
  card: { borderRadius: 18, borderWidth: 1, padding: 16, marginBottom: 16, overflow: 'hidden' },
  headerRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 8 },
  iconBg: { width: 32, height: 32, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 14, fontWeight: '600' },
  amount: { fontSize: 28, fontWeight: '800', marginBottom: 12 },
  barContainer: { marginBottom: 10 },
  barTrack: { height: 8, borderRadius: 4, overflow: 'hidden' },
  barFill: { height: '100%', borderRadius: 4 },
  splitRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 },
  splitItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  splitDot: { width: 8, height: 8, borderRadius: 4 },
  splitLabel: { fontSize: 12, fontWeight: '500' },
  splitValue: { fontSize: 13, fontWeight: '700' },
  breakdown: { borderTopWidth: 1, paddingTop: 12, gap: 8 },
  breakdownRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  breakdownLabel: { flex: 1, fontSize: 12 },
  breakdownVal: { fontSize: 13, fontWeight: '600' },
});
