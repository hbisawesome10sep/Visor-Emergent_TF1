import React from 'react';
import { View, Text, ScrollView, StyleSheet, Dimensions } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Accent } from '../../utils/theme';
import { formatINR, formatINRShort } from '../../utils/formatters';

const HALF_SCREEN = Dimensions.get('window').height * 0.42;

interface StockHolding {
  id: string;
  name: string;
  ticker: string;
  quantity: number;
  buy_price: number;
  current_value: number;
  invested_value: number;
  gain_loss: number;
  gain_loss_pct: number;
}

interface Props {
  holdings: StockHolding[];
  colors: any;
  isDark: boolean;
}

export const StockHoldingsCard: React.FC<Props> = ({ holdings, colors, isDark }) => {
  if (!holdings.length) return null;

  const totalInvested = holdings.reduce((s, h) => s + h.invested_value, 0);
  const totalCurrent = holdings.reduce((s, h) => s + h.current_value, 0);
  const totalGain = totalCurrent - totalInvested;
  const isGain = totalGain >= 0;

  return (
    <View data-testid="stock-holdings-card" style={[s.card, {
      backgroundColor: isDark ? 'rgba(10,10,11,0.95)' : '#FFFFFF',
      borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
    }]}>
      {/* Frozen Header */}
      <View style={[s.frozenHeader, { borderBottomColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)' }]}>
        <View style={s.headerTop}>
          <View style={s.headerLeft}>
            <View style={[s.iconWrap, { backgroundColor: isDark ? 'rgba(249,115,22,0.15)' : 'rgba(249,115,22,0.08)' }]}>
              <MaterialCommunityIcons name="chart-line" size={18} color="#F97316" />
            </View>
            <View>
              <Text style={[s.headerTitle, { color: colors.textPrimary }]}>Stocks</Text>
              <Text style={[s.headerCount, { color: colors.textSecondary }]}>{holdings.length} holding{holdings.length !== 1 ? 's' : ''}</Text>
            </View>
          </View>
          <View style={[s.gainBadge, { backgroundColor: isGain ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)' }]}>
            <MaterialCommunityIcons name={isGain ? 'trending-up' : 'trending-down'} size={14} color={isGain ? Accent.emerald : Accent.ruby} />
            <Text style={[s.gainText, { color: isGain ? Accent.emerald : Accent.ruby }]}>
              {isGain ? '+' : ''}{((totalGain / totalInvested) * 100).toFixed(1)}%
            </Text>
          </View>
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
      </View>

      {/* Column Headers */}
      <View style={[s.colHeaders, { backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)' }]}>
        <Text style={[s.colH, { flex: 1.4, color: colors.textSecondary }]}>Stock</Text>
        <Text style={[s.colH, { flex: 0.7, textAlign: 'right', color: colors.textSecondary }]}>Qty</Text>
        <Text style={[s.colH, { flex: 1, textAlign: 'right', color: colors.textSecondary }]}>Avg Cost</Text>
        <Text style={[s.colH, { flex: 1, textAlign: 'right', color: colors.textSecondary }]}>CMP</Text>
        <Text style={[s.colH, { flex: 0.8, textAlign: 'right', color: colors.textSecondary }]}>P&L %</Text>
      </View>

      {/* Scrollable body */}
      <ScrollView style={{ maxHeight: HALF_SCREEN - 140 }} showsVerticalScrollIndicator={false} nestedScrollEnabled>
        {holdings.map((h, idx) => {
          const hGain = h.gain_loss >= 0;
          const cmp = h.current_value / h.quantity;
          return (
            <View key={h.id} data-testid={`stock-row-${h.id}`} style={[s.row, idx < holdings.length - 1 && {
              borderBottomWidth: 1,
              borderBottomColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.03)',
            }]}>
              <View style={{ flex: 1.4 }}>
                <Text style={[s.stockName, { color: colors.textPrimary }]} numberOfLines={1}>{h.name}</Text>
                <Text style={[s.stockTicker, { color: colors.textSecondary }]}>{h.ticker?.replace('.NS', '') || '-'}</Text>
              </View>
              <Text style={[s.cellVal, { flex: 0.7, color: colors.textPrimary }]}>{h.quantity}</Text>
              <Text style={[s.cellVal, { flex: 1, color: colors.textSecondary }]}>{formatINRShort(h.buy_price)}</Text>
              <Text style={[s.cellVal, { flex: 1, color: colors.textPrimary }]}>{formatINRShort(cmp)}</Text>
              <Text style={[s.cellVal, { flex: 0.8, color: hGain ? Accent.emerald : Accent.ruby }]}>
                {hGain ? '+' : ''}{h.gain_loss_pct.toFixed(1)}%
              </Text>
            </View>
          );
        })}
      </ScrollView>
    </View>
  );
};

const s = StyleSheet.create({
  card: { borderRadius: 18, borderWidth: 1, overflow: 'hidden', marginBottom: 20 },
  frozenHeader: { padding: 16, paddingBottom: 14, borderBottomWidth: 1 },
  headerTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  headerLeft: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  iconWrap: { width: 34, height: 34, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  headerTitle: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '700' },
  headerCount: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '500', marginTop: 1 },
  gainBadge: { flexDirection: 'row', alignItems: 'center', gap: 5, paddingHorizontal: 10, paddingVertical: 5, borderRadius: 10 },
  gainText: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' },
  summaryRow: { flexDirection: 'row', alignItems: 'center' },
  summaryLabel: { fontSize: 10, fontFamily: 'DM Sans', fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5 },
  summaryValue: { fontSize: 18, fontFamily: 'DM Sans', fontWeight: '700', letterSpacing: -0.3, marginTop: 2 },
  divider: { width: 1, height: 32, marginHorizontal: 14 },
  colHeaders: { flexDirection: 'row', paddingHorizontal: 16, paddingVertical: 8 },
  colH: { fontSize: 9, fontFamily: 'DM Sans', fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5 },
  row: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 12 },
  stockName: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '600' },
  stockTicker: { fontSize: 10, fontFamily: 'DM Sans', fontWeight: '500', marginTop: 1 },
  cellVal: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600', textAlign: 'right' },
});
