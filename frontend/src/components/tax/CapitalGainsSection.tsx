import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Accent } from '../../utils/theme';
import { formatINR } from '../../utils/formatters';

interface CapitalGainsSectionProps {
  capitalGainsData: any;
  colors: any;
  isDark: boolean;
}

export const CapitalGainsSection: React.FC<CapitalGainsSectionProps> = ({
  capitalGainsData,
  colors,
  isDark,
}) => {
  if (!capitalGainsData || (!capitalGainsData.gains?.length && !capitalGainsData.summary?.total_estimated_tax)) {
    return (
      <View style={{ marginTop: 20 }}>
        <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Capital Gains / Loss</Text>
        <View style={[styles.emptyCard, { 
          backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.85)', 
          borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)' 
        }]}>
          <MaterialCommunityIcons name="chart-timeline-variant" size={32} color={colors.textSecondary} />
          <Text style={[styles.emptyText, { color: colors.textSecondary }]}>
            No capital gains/losses recorded yet
          </Text>
        </View>
      </View>
    );
  }

  return (
    <View data-testid="capital-gains-section">
      <Text style={[styles.sectionTitle, { color: colors.textPrimary, marginTop: 20 }]}>
        Capital Gains / Loss
      </Text>
      
      {/* Summary Card */}
      <View style={[styles.card, {
        backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.85)',
        borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
      }]}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 }}>
          <View style={{ flex: 1 }}>
            <Text style={[styles.label, { color: colors.textSecondary }]}>Short Term (STCG)</Text>
            <Text style={[styles.value, { color: Accent.ruby }]}>
              {formatINR(capitalGainsData.summary?.total_stcg || 0)}
            </Text>
            <Text style={[styles.taxLabel, { color: colors.textSecondary }]}>
              Tax: {formatINR(capitalGainsData.summary?.estimated_stcg_tax || 0)}
            </Text>
          </View>
          <View style={{ flex: 1, alignItems: 'flex-end' }}>
            <Text style={[styles.label, { color: colors.textSecondary }]}>Long Term (LTCG)</Text>
            <Text style={[styles.value, { color: Accent.sapphire }]}>
              {formatINR(capitalGainsData.summary?.total_ltcg || 0)}
            </Text>
            <Text style={[styles.taxLabel, { color: colors.textSecondary }]}>
              Tax: {formatINR(capitalGainsData.summary?.estimated_ltcg_tax || 0)}
            </Text>
          </View>
        </View>

        {capitalGainsData.summary?.ltcg_exemption > 0 && capitalGainsData.summary?.total_ltcg > 0 && (
          <View style={[styles.infoBanner, { 
            backgroundColor: isDark ? 'rgba(59,130,246,0.1)' : 'rgba(59,130,246,0.06)' 
          }]}>
            <MaterialCommunityIcons name="information" size={14} color={Accent.sapphire} />
            <Text style={[styles.infoText, { color: colors.textSecondary }]}>
              LTCG exemption: {formatINR(capitalGainsData.summary.ltcg_exemption)} 
              (Taxable: {formatINR(capitalGainsData.summary.ltcg_taxable)})
            </Text>
          </View>
        )}

        <View style={[styles.totalRow, { borderTopColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
          <Text style={[styles.totalLabel, { color: colors.textPrimary }]}>Total Estimated Tax</Text>
          <Text style={[styles.totalValue, { color: Accent.ruby }]}>
            {formatINR(capitalGainsData.summary?.total_estimated_tax || 0)}
          </Text>
        </View>
      </View>

      {/* Individual Gains */}
      {capitalGainsData.gains?.map((gain: any, idx: number) => (
        <View key={idx} data-testid={`capital-gain-item-${idx}`} style={[styles.gainCard, {
          backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.85)',
          borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
        }]}>
          <View style={styles.gainHeader}>
            <Text style={[styles.gainTitle, { color: colors.textPrimary }]} numberOfLines={1}>
              {gain.description}
            </Text>
            <View style={[styles.typeBadge, { 
              backgroundColor: gain.is_long_term ? 'rgba(59,130,246,0.1)' : 'rgba(239,68,68,0.1)' 
            }]}>
              <Text style={[styles.typeBadgeText, { 
                color: gain.is_long_term ? Accent.sapphire : Accent.ruby 
              }]}>
                {gain.is_long_term ? 'LTCG' : 'STCG'}
              </Text>
            </View>
          </View>
          <View style={styles.gainDetails}>
            <Text style={[styles.gainMeta, { color: colors.textSecondary }]}>
              Sold: {formatINR(gain.sell_amount)} | Cost: {formatINR(gain.cost_basis)}
            </Text>
            <Text style={[styles.gainAmount, { color: gain.gain_loss >= 0 ? Accent.emerald : Accent.ruby }]}>
              {gain.gain_loss >= 0 ? '+' : ''}{formatINR(gain.gain_loss)}
            </Text>
          </View>
          <Text style={[styles.gainFooter, { color: colors.textSecondary }]}>
            {gain.holding_days} days | Tax: {formatINR(gain.tax_liability)} @ {(gain.tax_rate * 100).toFixed(1)}%
          </Text>
        </View>
      ))}

      {/* Notes */}
      {capitalGainsData.notes?.length > 0 && (
        <View style={{ marginBottom: 16, paddingHorizontal: 4 }}>
          {capitalGainsData.notes.map((note: string, idx: number) => (
            <Text key={idx} style={[styles.note, { color: colors.textSecondary }]}>
              * {note}
            </Text>
          ))}
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  sectionTitle: {
    fontSize: 18,
    fontFamily: 'DM Sans',
    fontWeight: '700',
    marginBottom: 12,
  },
  card: {
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    marginBottom: 12,
  },
  label: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    marginBottom: 4,
  },
  value: {
    fontSize: 16,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  taxLabel: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    marginTop: 2,
  },
  infoBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    padding: 8,
    borderRadius: 8,
    marginBottom: 10,
  },
  infoText: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    flex: 1,
  },
  totalRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 10,
    borderTopWidth: 1,
  },
  totalLabel: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  totalValue: {
    fontSize: 16,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  gainCard: {
    borderRadius: 16,
    padding: 14,
    borderWidth: 1,
    marginBottom: 8,
  },
  gainHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  gainTitle: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    fontWeight: '700',
    flex: 1,
  },
  typeBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  typeBadgeText: {
    fontSize: 10,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  gainDetails: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  gainMeta: {
    fontSize: 12,
    fontFamily: 'DM Sans',
  },
  gainAmount: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  gainFooter: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    marginTop: 4,
  },
  note: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    marginBottom: 2,
  },
  emptyCard: {
    borderRadius: 16,
    padding: 24,
    borderWidth: 1,
    alignItems: 'center',
    gap: 8,
  },
  emptyText: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    textAlign: 'center',
  },
});
