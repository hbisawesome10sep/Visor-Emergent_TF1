import React, { useState, useMemo } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import RNSlider from '@react-native-community/slider';
import { formatINRShort } from '../utils/formatters';
import { Accent } from '../utils/theme';

const ASSET_METRICS: Record<string, { label: string; color: string; ret: number; vol: number }> = {
  Equity: { label: 'Equity', color: Accent.sapphire, ret: 12, vol: 18 },
  Debt: { label: 'Debt', color: Accent.emerald, ret: 7, vol: 3 },
  Gold: { label: 'Gold', color: '#EAB308', ret: 9, vol: 12 },
  Alt: { label: 'Alternatives', color: Accent.amethyst, ret: 11, vol: 15 },
};

type Props = {
  totalPortfolio: number;
  initialAlloc?: { Equity: number; Debt: number; Gold: number; Alt: number };
  isDark: boolean;
  colors: any;
};

export const WhatIfSimulator = ({ totalPortfolio, initialAlloc, isDark, colors }: Props) => {
  const [showSimulator, setShowSimulator] = useState(false);
  const [simAlloc, setSimAlloc] = useState(initialAlloc || { Equity: 40, Debt: 30, Gold: 15, Alt: 15 });

  const updateSimSlider = (bucket: string, value: number) => {
    setSimAlloc(prev => ({ ...prev, [bucket]: Math.round(value) }));
  };

  const simProjected = useMemo(() => {
    const ret = Object.entries(simAlloc).reduce((s, [k, v]) => s + (ASSET_METRICS[k]?.ret || 0) * v / 100, 0);
    const vol = Object.entries(simAlloc).reduce((s, [k, v]) => s + (ASSET_METRICS[k]?.vol || 0) * v / 100, 0);
    const sharpe = vol > 0 ? (ret - 5) / vol : 0;
    const base = totalPortfolio || 100000;
    return { ret, vol, sharpe, val5: base * Math.pow(1 + ret / 100, 5), val10: base * Math.pow(1 + ret / 100, 10) };
  }, [simAlloc, totalPortfolio]);

  const totalPct = Object.values(simAlloc).reduce((s, v) => s + v, 0);

  return (
    <View>
      <TouchableOpacity data-testid="simulator-toggle" style={[styles.toggle, {
        backgroundColor: isDark ? 'rgba(10, 10, 11, 0.85)' : 'rgba(255, 255, 255, 0.85)',
        borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
      }]} onPress={() => setShowSimulator(!showSimulator)}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
          <View style={[styles.iconWrap, { backgroundColor: 'rgba(99,102,241,0.12)' }]}>
            <MaterialCommunityIcons name="tune-vertical" size={18} color="#6366F1" />
          </View>
          <View>
            <Text style={[styles.toggleTitle, { color: colors.textPrimary }]}>What-If Simulator</Text>
            <Text style={[styles.toggleSub, { color: colors.textSecondary }]}>Explore different allocation scenarios</Text>
          </View>
        </View>
        <MaterialCommunityIcons name={showSimulator ? 'chevron-up' : 'chevron-down'} size={22} color={colors.textSecondary} />
      </TouchableOpacity>

      {showSimulator && (
        <View data-testid="simulator-panel" style={[styles.card, {
          backgroundColor: isDark ? 'rgba(10, 10, 11, 0.85)' : 'rgba(255, 255, 255, 0.85)',
          borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
        }]}>
          {Object.entries(ASSET_METRICS).map(([bucket, m]) => (
            <View key={bucket} data-testid={`sim-slider-${bucket}`} style={styles.sliderRow}>
              <View style={styles.sliderHeader}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                  <View style={[styles.dot, { backgroundColor: m.color }]} />
                  <Text style={[styles.sliderLabel, { color: colors.textPrimary }]}>{m.label}</Text>
                </View>
                <Text style={[styles.sliderVal, { color: m.color }]}>{simAlloc[bucket as keyof typeof simAlloc]}%</Text>
              </View>
              <RNSlider
                style={{ width: '100%', height: 28 }}
                minimumValue={0} maximumValue={100} step={5}
                value={simAlloc[bucket as keyof typeof simAlloc]}
                onValueChange={(v: number) => updateSimSlider(bucket, v)}
                minimumTrackTintColor={m.color}
                maximumTrackTintColor={isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)'}
                thumbTintColor={m.color}
              />
              <Text style={[styles.sliderMeta, { color: colors.textSecondary }]}>
                Avg return: {m.ret}% | Volatility: {m.vol}%
              </Text>
            </View>
          ))}

          <View style={[styles.totalRow, {
            backgroundColor: totalPct === 100 ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)',
          }]}>
            <Text style={[styles.totalText, { color: totalPct === 100 ? Accent.emerald : Accent.ruby }]}>
              Total: {totalPct}%
            </Text>
          </View>

          <View style={styles.allocBar}>
            {Object.entries(simAlloc).map(([bucket, pct]) => pct > 0 ? (
              <View key={bucket} style={[styles.allocSegment, { width: `${pct}%`, backgroundColor: ASSET_METRICS[bucket].color }]}>
                {pct >= 12 && <Text style={styles.allocSegText}>{pct}%</Text>}
              </View>
            ) : null)}
          </View>

          <View style={styles.results}>
            {[
              { label: 'Projected Return', value: `${simProjected.ret.toFixed(1)}% p.a.`, color: simProjected.ret >= 10 ? Accent.emerald : Accent.amber, testId: 'sim-projected-return' },
              { label: 'Volatility', value: `${simProjected.vol.toFixed(1)}%`, color: simProjected.vol > 12 ? Accent.ruby : Accent.emerald, testId: 'sim-volatility' },
              { label: 'Sharpe Ratio', value: simProjected.sharpe.toFixed(2), color: simProjected.sharpe >= 0.5 ? Accent.emerald : Accent.amber, testId: 'sim-sharpe' },
            ].map((r, i) => (
              <View key={i} style={[styles.resultCard, { backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.03)' }]}>
                <Text style={[styles.resultLabel, { color: colors.textSecondary }]}>{r.label}</Text>
                <Text data-testid={r.testId} style={[styles.resultValue, { color: r.color }]}>{r.value}</Text>
              </View>
            ))}
          </View>

          <View style={[styles.projection, { borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
            <Text style={[styles.projectionLabel, { color: colors.textSecondary }]}>
              Portfolio of {formatINRShort(totalPortfolio || 100000)} could become:
            </Text>
            <View style={styles.projectionRow}>
              <View>
                <Text style={[styles.projectionPeriod, { color: colors.textSecondary }]}>5 Years</Text>
                <Text data-testid="sim-val-5y" style={[styles.projectionVal, { color: Accent.emerald }]}>{formatINRShort(simProjected.val5)}</Text>
              </View>
              <View style={[styles.projectionDivider, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)' }]} />
              <View>
                <Text style={[styles.projectionPeriod, { color: colors.textSecondary }]}>10 Years</Text>
                <Text data-testid="sim-val-10y" style={[styles.projectionVal, { color: Accent.emerald }]}>{formatINRShort(simProjected.val10)}</Text>
              </View>
            </View>
          </View>

          <TouchableOpacity data-testid="sim-reset-btn" style={styles.resetBtn} onPress={() => {
            setSimAlloc(initialAlloc || { Equity: 40, Debt: 30, Gold: 15, Alt: 15 });
          }}>
            <MaterialCommunityIcons name="refresh" size={14} color={Accent.emerald} />
            <Text style={styles.resetText}>Reset to recommended</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  toggle: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: 16, borderRadius: 16, borderWidth: 1, marginBottom: 12 },
  toggleTitle: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '600' as any },
  toggleSub: { fontSize: 12, fontFamily: 'DM Sans', marginTop: 1 },
  iconWrap: { width: 36, height: 36, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  card: { borderRadius: 16, borderWidth: 1, padding: 16, marginBottom: 16 },
  sliderRow: { marginBottom: 12 },
  sliderHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 },
  sliderLabel: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '500' as any },
  sliderVal: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700' as any },
  sliderMeta: { fontSize: 10, fontFamily: 'DM Sans', marginTop: -2 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  totalRow: { padding: 8, borderRadius: 8, alignItems: 'center', marginVertical: 8 },
  totalText: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' as any },
  allocBar: { flexDirection: 'row', height: 12, borderRadius: 6, overflow: 'hidden', marginBottom: 12 },
  allocSegment: { height: 12, justifyContent: 'center', alignItems: 'center' },
  allocSegText: { fontSize: 8, color: '#fff', fontWeight: '700' as any },
  results: { flexDirection: 'row', gap: 8, marginBottom: 12 },
  resultCard: { flex: 1, padding: 10, borderRadius: 10, alignItems: 'center' },
  resultLabel: { fontSize: 10, fontFamily: 'DM Sans', marginBottom: 4 },
  resultValue: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '700' as any },
  projection: { borderWidth: 1, borderRadius: 12, padding: 14, marginBottom: 12 },
  projectionLabel: { fontSize: 12, fontFamily: 'DM Sans', marginBottom: 8, textAlign: 'center' },
  projectionRow: { flexDirection: 'row', justifyContent: 'space-around', alignItems: 'center' },
  projectionPeriod: { fontSize: 11, fontFamily: 'DM Sans', textAlign: 'center', marginBottom: 2 },
  projectionVal: { fontSize: 20, fontFamily: 'DM Sans', fontWeight: '800' as any, textAlign: 'center' },
  projectionDivider: { width: 1, height: 36 },
  resetBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, paddingVertical: 8 },
  resetText: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '500' as any, color: Accent.emerald },
});
