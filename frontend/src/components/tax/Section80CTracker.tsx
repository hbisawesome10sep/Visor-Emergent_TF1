import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { formatINR, formatINRShort } from '../../utils/formatters';
import { Accent } from '../../utils/theme';

const INSTRUMENT_COLORS = [
  '#F59E0B', '#10B981', '#3B82F6', '#8B5CF6',
  '#F97316', '#06B6D4', '#EC4899', '#84CC16',
];

interface Props {
  summary: any;
  colors: any;
  isDark: boolean;
  onOptimize?: () => void;
}

export function Section80CTracker({ summary, colors, isDark, onOptimize }: Props) {
  const [expanded, setExpanded] = useState(false);

  if (!summary) return null;

  const { total_80c, limit_80c, remaining_80c, utilization_percentage, instruments_80c,
    status, recommendation, total_nps, nps_limit, nps_remaining, nps_utilization_pct } = summary;

  const barColor = utilization_percentage >= 80 ? Accent.emerald
    : utilization_percentage >= 50 ? '#F59E0B'
    : '#EF4444';

  return (
    <View
      data-testid="section-80c-tracker"
      style={[styles.card, {
        backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.85)',
        borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
      }]}
    >
      {/* Header */}
      <TouchableOpacity style={styles.headerRow} onPress={() => setExpanded(!expanded)} activeOpacity={0.8}>
        <View style={styles.headerLeft}>
          <MaterialCommunityIcons name="shield-check-outline" size={16} color="#F59E0B" />
          <View style={{ marginLeft: 8 }}>
            <Text style={[styles.title, { color: colors.textPrimary }]}>Section 80C</Text>
            <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
              {formatINR(total_80c)} of {formatINR(limit_80c)} used
            </Text>
          </View>
        </View>
        <View style={styles.headerRight}>
          <View style={[styles.statusBadge, {
            backgroundColor: status === 'optimized'
              ? 'rgba(16,185,129,0.12)' : status === 'good'
              ? 'rgba(245,158,11,0.12)' : 'rgba(239,68,68,0.12)',
          }]}>
            <Text style={[styles.statusText, {
              color: status === 'optimized' ? Accent.emerald : status === 'good' ? '#F59E0B' : '#EF4444',
            }]}>
              {utilization_percentage}%
            </Text>
          </View>
          <MaterialCommunityIcons
            name={expanded ? 'chevron-up' : 'chevron-down'}
            size={16}
            color={colors.textSecondary}
            style={{ marginLeft: 6 }}
          />
        </View>
      </TouchableOpacity>

      {/* Progress Bar */}
      <View style={[styles.progressBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)' }]}>
        {instruments_80c?.length > 0
          ? instruments_80c.map((inst: any, i: number) => {
              const pct = Math.min(100, (inst.amount / limit_80c) * 100);
              return pct > 0 ? (
                <View
                  key={i}
                  style={[styles.progressSegment, {
                    width: `${pct}%`,
                    backgroundColor: INSTRUMENT_COLORS[i % INSTRUMENT_COLORS.length],
                  }]}
                />
              ) : null;
            })
          : <View style={[styles.progressSegment, { width: `${utilization_percentage}%`, backgroundColor: barColor }]} />
        }
      </View>

      {/* Remaining / Limit */}
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 6 }}>
        <Text style={[styles.limitNote, { color: colors.textSecondary }]}>
          {remaining_80c > 0 ? `₹${(remaining_80c / 1000).toFixed(1)}K remaining` : 'Fully utilized'}
        </Text>
        <Text style={[styles.limitNote, { color: colors.textSecondary }]}>Limit: ₹1,50,000</Text>
      </View>

      {/* Expanded: instrument breakdown + NPS */}
      {expanded && (
        <View style={[styles.expandedSection, { borderTopColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)' }]}>

          {/* Instrument breakdown */}
          {instruments_80c?.length > 0 && (
            <>
              <Text style={[styles.sectionLabel, { color: colors.textSecondary }]}>Instrument Breakdown</Text>
              {instruments_80c.map((inst: any, i: number) => (
                <View key={i} style={styles.instrumentRow}>
                  <View style={[styles.instrumentDot, { backgroundColor: INSTRUMENT_COLORS[i % INSTRUMENT_COLORS.length] }]} />
                  <Text style={[styles.instrumentName, { color: colors.textPrimary, flex: 1 }]}>{inst.name}</Text>
                  <Text style={[styles.instrumentAmt, { color: INSTRUMENT_COLORS[i % INSTRUMENT_COLORS.length] }]}>
                    {formatINR(inst.amount)}
                  </Text>
                  <Text style={[styles.sourceTag, { color: colors.textSecondary }]}>
                    {inst.source === 'salary_profile' ? 'Salary' : inst.source === 'manual' ? 'Manual' : 'Auto'}
                  </Text>
                </View>
              ))}
            </>
          )}

          {/* NPS 80CCD(1B) additional */}
          <View style={[styles.npsSection, {
            backgroundColor: isDark ? 'rgba(139,92,246,0.06)' : 'rgba(139,92,246,0.04)',
            borderColor: isDark ? 'rgba(139,92,246,0.15)' : 'rgba(139,92,246,0.1)',
          }]}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <Text style={[styles.npsTitle, { color: '#8B5CF6' }]}>NPS 80CCD(1B) Additional</Text>
              <Text style={[styles.npsAmt, { color: '#8B5CF6' }]}>
                {formatINR(total_nps)} / {formatINR(nps_limit)}
              </Text>
            </View>
            <View style={[styles.progressBg, { backgroundColor: isDark ? 'rgba(139,92,246,0.1)' : 'rgba(139,92,246,0.08)' }]}>
              <View style={[styles.progressSegment, { width: `${nps_utilization_pct}%`, backgroundColor: '#8B5CF6' }]} />
            </View>
            <Text style={[styles.npsNote, { color: colors.textSecondary, marginTop: 4 }]}>
              ₹{(nps_remaining / 1000).toFixed(0)}K extra deduction beyond 80C limit
            </Text>
          </View>

          {/* Recommendation */}
          <Text style={[styles.recText, { color: colors.textSecondary }]}>{recommendation}</Text>

          {/* Optimize CTA */}
          {status !== 'optimized' && onOptimize && (
            <TouchableOpacity
              data-testid="optimize-80c-btn"
              style={[styles.optimizeBtn, { borderColor: '#F59E0B' }]}
              onPress={onOptimize}
              activeOpacity={0.8}
            >
              <MaterialCommunityIcons name="robot-outline" size={14} color="#F59E0B" />
              <Text style={[styles.optimizeBtnText, { color: '#F59E0B' }]}>Optimize with Visor AI</Text>
            </TouchableOpacity>
          )}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderRadius: 14, padding: 14, borderWidth: 1, marginBottom: 12 },
  headerRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 },
  headerLeft: { flexDirection: 'row', alignItems: 'center' },
  headerRight: { flexDirection: 'row', alignItems: 'center' },
  title: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' },
  subtitle: { fontSize: 11, fontFamily: 'DM Sans' },
  statusBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8 },
  statusText: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '800' },
  progressBg: { height: 8, borderRadius: 4, overflow: 'hidden', flexDirection: 'row' },
  progressSegment: { height: '100%' },
  limitNote: { fontSize: 10, fontFamily: 'DM Sans' },
  expandedSection: { borderTopWidth: 1, marginTop: 12, paddingTop: 12 },
  sectionLabel: { fontSize: 10, fontFamily: 'DM Sans', fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8 },
  instrumentRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 5, gap: 8 },
  instrumentDot: { width: 8, height: 8, borderRadius: 4 },
  instrumentName: { fontSize: 12, fontFamily: 'DM Sans' },
  instrumentAmt: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '700' },
  sourceTag: { fontSize: 9, fontFamily: 'DM Sans', fontWeight: '500', textTransform: 'uppercase', letterSpacing: 0.3 },
  npsSection: { borderRadius: 10, padding: 10, borderWidth: 1, marginTop: 12, marginBottom: 10 },
  npsTitle: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '700' },
  npsAmt: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '700' },
  npsNote: { fontSize: 10, fontFamily: 'DM Sans' },
  recText: { fontSize: 11, fontFamily: 'DM Sans', marginTop: 4, marginBottom: 10, fontStyle: 'italic' },
  optimizeBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6,
    borderRadius: 10, borderWidth: 1, paddingVertical: 9,
  },
  optimizeBtnText: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '700' },
});
