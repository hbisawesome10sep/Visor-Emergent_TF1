import React from 'react';
import { View, Text, ScrollView, StyleSheet, Dimensions } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Accent } from '../../utils/theme';
import { formatINR, formatINRShort } from '../../utils/formatters';

const HALF_SCREEN = Dimensions.get('window').height * 0.42;

interface MFHolding {
  id: string;
  name: string;
  isin: string;
  quantity: number;
  buy_price: number;
  current_value: number;
  invested_value: number;
  gain_loss: number;
  gain_loss_pct: number;
}

interface Props {
  holdings: MFHolding[];
  xirr: number | null;
  colors: any;
  isDark: boolean;
}

export const MutualFundHoldingsCard: React.FC<Props> = ({ holdings, xirr, colors, isDark }) => {
  if (!holdings.length) return null;

  const totalInvested = holdings.reduce((s, h) => s + h.invested_value, 0);
  const totalCurrent = holdings.reduce((s, h) => s + h.current_value, 0);
  const totalGain = totalCurrent - totalInvested;
  const isGain = totalGain >= 0;

  return (
    <View data-testid="mf-holdings-card" style={[s.card, {
      backgroundColor: isDark ? 'rgba(10,10,11,0.95)' : '#FFFFFF',
      borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
    }]}>
      {/* Frozen Header */}
      <View style={[s.frozenHeader, { borderBottomColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)' }]}>
        <View style={s.headerTop}>
          <View style={s.headerLeft}>
            <View style={[s.iconWrap, { backgroundColor: isDark ? 'rgba(99,102,241,0.15)' : 'rgba(99,102,241,0.08)' }]}>
              <MaterialCommunityIcons name="chart-arc" size={18} color="#6366F1" />
            </View>
            <View>
              <Text style={[s.headerTitle, { color: colors.textPrimary }]}>Mutual Funds</Text>
              <Text style={[s.headerCount, { color: colors.textSecondary }]}>{holdings.length} fund{holdings.length !== 1 ? 's' : ''}</Text>
            </View>
          </View>
          {xirr !== null && xirr < 500 && (
            <View style={[s.xirrBadge, { backgroundColor: isDark ? 'rgba(99,102,241,0.15)' : 'rgba(99,102,241,0.08)' }]}>
              <Text style={[s.xirrLabel, { color: '#6366F1' }]}>XIRR</Text>
              <Text style={[s.xirrValue, { color: xirr >= 0 ? Accent.emerald : Accent.ruby }]}>
                {xirr >= 0 ? '+' : ''}{xirr.toFixed(1)}%
              </Text>
            </View>
          )}
        </View>
        <View style={s.summaryRow}>
          <View style={{ flex: 1 }}>
            <Text style={[s.summaryLabel, { color: colors.textSecondary }]}>Invested</Text>
            <Text style={[s.summaryValue, { color: colors.textPrimary }]}>{formatINR(totalInvested)}</Text>
          </View>
          <View style={[s.divider, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]} />
          <View style={{ flex: 1, alignItems: 'flex-end' as any }}>
            <Text style={[s.summaryLabel, { color: colors.textSecondary }]}>Current</Text>
            <Text style={[s.summaryValue, { color: isGain ? Accent.emerald : Accent.ruby }]}>{formatINR(totalCurrent)}</Text>
          </View>
        </View>
        <View style={[s.gainStrip, { backgroundColor: isGain ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)' }]}>
          <MaterialCommunityIcons name={isGain ? 'trending-up' : 'trending-down'} size={14} color={isGain ? Accent.emerald : Accent.ruby} />
          <Text style={[s.gainStripText, { color: isGain ? Accent.emerald : Accent.ruby }]}>
            P&L: {isGain ? '+' : ''}{formatINR(totalGain)} ({isGain ? '+' : ''}{totalInvested > 0 ? ((totalGain / totalInvested) * 100).toFixed(2) : 0}%)
          </Text>
        </View>
      </View>

      {/* Scrollable fund list */}
      <ScrollView style={{ maxHeight: HALF_SCREEN - 160 }} showsVerticalScrollIndicator={false} nestedScrollEnabled>
        {holdings.map((h, idx) => {
          const hGain = h.gain_loss >= 0;
          const nav = h.current_value / h.quantity;
          return (
            <View key={h.id} data-testid={`mf-row-${h.id}`} style={[s.fundRow, idx < holdings.length - 1 && {
              borderBottomWidth: 1,
              borderBottomColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.03)',
            }]}>
              <Text style={[s.fundName, { color: colors.textPrimary }]} numberOfLines={2}>{h.name}</Text>
              <View style={s.fundStats}>
                <View style={s.statItem}>
                  <Text style={[s.statLabel, { color: colors.textSecondary }]}>Units</Text>
                  <Text style={[s.statVal, { color: colors.textPrimary }]}>{h.quantity.toFixed(3)}</Text>
                </View>
                <View style={s.statItem}>
                  <Text style={[s.statLabel, { color: colors.textSecondary }]}>Avg NAV</Text>
                  <Text style={[s.statVal, { color: colors.textSecondary }]}>{formatINRShort(h.buy_price)}</Text>
                </View>
                <View style={s.statItem}>
                  <Text style={[s.statLabel, { color: colors.textSecondary }]}>Cur NAV</Text>
                  <Text style={[s.statVal, { color: colors.textPrimary }]}>{formatINRShort(nav)}</Text>
                </View>
                <View style={s.statItem}>
                  <Text style={[s.statLabel, { color: colors.textSecondary }]}>Returns</Text>
                  <Text style={[s.statVal, { color: hGain ? Accent.emerald : Accent.ruby }]}>
                    {hGain ? '+' : ''}{h.gain_loss_pct.toFixed(1)}%
                  </Text>
                </View>
              </View>
              <View style={s.fundValues}>
                <Text style={[s.fundInvested, { color: colors.textSecondary }]}>Inv: {formatINRShort(h.invested_value)}</Text>
                <Text style={[s.fundCurrent, { color: hGain ? Accent.emerald : Accent.ruby }]}>Cur: {formatINRShort(h.current_value)}</Text>
              </View>
            </View>
          );
        })}
      </ScrollView>
    </View>
  );
};

const s = StyleSheet.create({
  card: { borderRadius: 18, borderWidth: 1, overflow: 'hidden', marginBottom: 20 },
  frozenHeader: { padding: 16, paddingBottom: 0, borderBottomWidth: 1 },
  headerTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  headerLeft: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  iconWrap: { width: 34, height: 34, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  headerTitle: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '700' },
  headerCount: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '500', marginTop: 1 },
  xirrBadge: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 10, paddingVertical: 5, borderRadius: 10 },
  xirrLabel: { fontSize: 10, fontFamily: 'DM Sans', fontWeight: '700', letterSpacing: 0.5 },
  xirrValue: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' },
  summaryRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  summaryLabel: { fontSize: 10, fontFamily: 'DM Sans', fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5 },
  summaryValue: { fontSize: 18, fontFamily: 'DM Sans', fontWeight: '700', letterSpacing: -0.3, marginTop: 2 },
  divider: { width: 1, height: 32, marginHorizontal: 14 },
  gainStrip: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 12, paddingVertical: 8, borderRadius: 10, marginBottom: 14 },
  gainStripText: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '700' },
  fundRow: { paddingHorizontal: 16, paddingVertical: 14 },
  fundName: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '600', marginBottom: 8 },
  fundStats: { flexDirection: 'row', gap: 0 },
  statItem: { flex: 1 },
  statLabel: { fontSize: 9, fontFamily: 'DM Sans', fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.3, marginBottom: 2 },
  statVal: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '700' },
  fundValues: { flexDirection: 'row', gap: 16, marginTop: 8 },
  fundInvested: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '600' },
  fundCurrent: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '700' },
});
