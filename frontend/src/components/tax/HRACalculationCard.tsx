import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { formatINR } from '../../utils/formatters';
import { Accent } from '../../utils/theme';

interface Props {
  hraData: any;
  colors: any;
  isDark: boolean;
}

export function HRACalculationCard({ hraData, colors, isDark }: Props) {
  const [expanded, setExpanded] = useState(false);

  if (!hraData) return null;

  if (!hraData.applicable) {
    return (
      <View style={[styles.card, {
        backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.85)',
        borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
      }]}>
        <View style={styles.row}>
          <MaterialCommunityIcons name="home-city-outline" size={16} color={colors.textSecondary} />
          <Text style={[styles.naTitle, { color: colors.textSecondary }]}>HRA Exemption</Text>
          <View style={[styles.naBadge, { backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)' }]}>
            <Text style={[styles.naBadgeText, { color: colors.textSecondary }]}>
              {hraData.message || 'Not applicable'}
            </Text>
          </View>
        </View>
      </View>
    );
  }

  const conditions = [
    { label: 'Actual HRA Received', value: hraData.condition_1_actual_hra },
    { label: `${hraData.city_type === 'metro' ? '50' : '40'}% of Basic (${hraData.city_type === 'metro' ? 'Metro' : 'Non-Metro'})`, value: hraData.condition_2_city_pct },
    { label: 'Rent Paid − 10% of Basic', value: hraData.condition_3_rent_minus_basic },
  ];

  return (
    <View
      data-testid="hra-calculation-card"
      style={[styles.card, {
        backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.85)',
        borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
      }]}
    >
      <TouchableOpacity style={styles.row} onPress={() => setExpanded(!expanded)} activeOpacity={0.8}>
        <MaterialCommunityIcons name="home-city-outline" size={16} color="#F59E0B" />
        <View style={{ flex: 1, marginLeft: 8 }}>
          <Text style={[styles.label, { color: colors.textSecondary }]}>HRA Exemption (Sec 10(13A))</Text>
          <Text style={[styles.amount, { color: Accent.emerald }]}>{formatINR(hraData.hra_exemption)}/year</Text>
        </View>
        <View style={{ alignItems: 'flex-end', gap: 2 }}>
          <Text style={[styles.saved, { color: Accent.emerald }]}>
            Saves {formatINR(hraData.tax_saved_30_slab)} @ 30%
          </Text>
          <MaterialCommunityIcons
            name={expanded ? 'chevron-up' : 'chevron-down'}
            size={16}
            color={colors.textSecondary}
          />
        </View>
      </TouchableOpacity>

      {expanded && (
        <View style={[styles.breakdown, { borderTopColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)' }]}>
          <Text style={[styles.breakdownTitle, { color: colors.textSecondary }]}>
            Exemption = Minimum of 3 conditions
          </Text>
          {conditions.map((c, i) => {
            const isLimiting = hraData.limiting_condition?.includes(c.label.split('−')[0].trim()) ||
              hraData.limiting_condition?.includes(c.label.split('(')[0].trim()) ||
              c.value === hraData.hra_exemption;
            return (
              <View
                key={i}
                style={[styles.condRow, {
                  backgroundColor: isLimiting
                    ? (isDark ? 'rgba(245,158,11,0.08)' : 'rgba(245,158,11,0.06)')
                    : 'transparent',
                  borderRadius: 8, paddingHorizontal: 8, paddingVertical: 6,
                }]}
              >
                <View style={styles.condLeft}>
                  {isLimiting && (
                    <MaterialCommunityIcons name="arrow-right" size={12} color="#F59E0B" style={{ marginRight: 4 }} />
                  )}
                  <Text style={[styles.condLabel, { color: isLimiting ? '#F59E0B' : colors.textSecondary }]}>
                    {`(${i + 1})`} {c.label}
                  </Text>
                </View>
                <Text style={[styles.condValue, { color: isLimiting ? '#F59E0B' : colors.textPrimary, fontWeight: isLimiting ? '700' : '500' }]}>
                  {formatINR(c.value)}
                </Text>
              </View>
            );
          })}

          <View style={[styles.resultRow, { borderTopColor: isDark ? 'rgba(245,158,11,0.2)' : 'rgba(245,158,11,0.15)' }]}>
            <Text style={[styles.resultLabel, { color: colors.textPrimary }]}>HRA Exemption</Text>
            <Text style={[styles.resultValue, { color: Accent.emerald }]}>{formatINR(hraData.hra_exemption)}</Text>
          </View>

          <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 4 }}>
            <Text style={[styles.subNote, { color: colors.textSecondary }]}>
              Taxable HRA: {formatINR(hraData.taxable_hra)}
            </Text>
            <Text style={[styles.subNote, { color: colors.textSecondary }]}>
              Monthly benefit: {formatINR(hraData.monthly_benefit)}
            </Text>
          </View>

          {hraData.warning && (
            <View style={[styles.warningBanner, { backgroundColor: isDark ? 'rgba(239,68,68,0.1)' : 'rgba(239,68,68,0.06)', borderColor: isDark ? 'rgba(239,68,68,0.25)' : 'rgba(239,68,68,0.15)' }]}>
              <MaterialCommunityIcons name="alert-outline" size={13} color="#EF4444" />
              <Text style={[styles.warningText, { color: '#EF4444' }]}>{hraData.warning}</Text>
            </View>
          )}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderRadius: 14, padding: 14, borderWidth: 1, marginBottom: 12 },
  row: { flexDirection: 'row', alignItems: 'center' },
  label: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '500' },
  amount: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '800' },
  saved: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '600' },
  naTitle: { fontSize: 12, fontFamily: 'DM Sans', marginLeft: 6, flex: 1 },
  naBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
  naBadgeText: { fontSize: 11, fontFamily: 'DM Sans' },
  breakdown: { borderTopWidth: 1, marginTop: 12, paddingTop: 12 },
  breakdownTitle: { fontSize: 10, fontFamily: 'DM Sans', fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8 },
  condRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 },
  condLeft: { flexDirection: 'row', alignItems: 'center', flex: 1 },
  condLabel: { fontSize: 11, fontFamily: 'DM Sans', flex: 1 },
  condValue: { fontSize: 12, fontFamily: 'DM Sans' },
  resultRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderTopWidth: 1, paddingTop: 10, marginTop: 8 },
  resultLabel: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' },
  resultValue: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '800' },
  subNote: { fontSize: 10, fontFamily: 'DM Sans' },
  warningBanner: { flexDirection: 'row', alignItems: 'center', gap: 6, padding: 8, borderRadius: 8, borderWidth: 1, marginTop: 10 },
  warningText: { fontSize: 11, fontFamily: 'DM Sans', flex: 1 },
});
