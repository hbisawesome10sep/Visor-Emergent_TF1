import React, { useEffect, useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { apiRequest } from '../../utils/api';
import { formatINRShort } from '../../utils/formatters';
import { Accent } from '../../utils/theme';

interface TaxMeterCardProps {
  token: string | null;
  colors: any;
  isDark: boolean;
}

interface TaxMeterData {
  fy: string;
  estimated_tax: number;
  tds_paid_ytd: number;
  tax_due: number;
  refund_expected: number;
  better_regime: string;
  savings_by_switch: number;
  total_deductions: number;
  deduction_80c: {
    used: number;
    limit: number;
    remaining: number;
    utilization_pct: number;
  };
  months_elapsed: number;
  gross_income: number;
  effective_rate: number;
}

export const TaxMeterCard: React.FC<TaxMeterCardProps> = ({ token, colors, isDark }) => {
  const router = useRouter();
  const [data, setData] = useState<TaxMeterData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTaxMeter = async () => {
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const result = await apiRequest('/tax/meter?fy=2025-26', { token });
        setData(result);
      } catch (e: any) {
        setError(e.message || 'Failed to load');
      } finally {
        setLoading(false);
      }
    };
    fetchTaxMeter();
  }, [token]);

  if (loading) {
    return (
      <View style={[styles.card, { backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.9)', borderColor: isDark ? 'rgba(245,158,11,0.15)' : 'rgba(245,158,11,0.1)' }]}>
        <ActivityIndicator size="small" color="#F59E0B" />
      </View>
    );
  }

  if (error || !data) {
    return null; // Silent fail - don't show card if no data
  }

  const hasRefund = data.refund_expected > 0;
  const hasDue = data.tax_due > 0;
  const progressPct = Math.min(100, (data.tds_paid_ytd / Math.max(data.estimated_tax, 1)) * 100);

  return (
    <TouchableOpacity 
      data-testid="tax-meter-card"
      style={[styles.card, { 
        backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.9)', 
        borderColor: isDark ? 'rgba(245,158,11,0.15)' : 'rgba(245,158,11,0.1)',
      }]}
      onPress={() => router.push('/(tabs)/tax')}
      activeOpacity={0.7}
    >
      {/* Header */}
      <View style={styles.header}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <View style={[styles.iconWrap, { backgroundColor: isDark ? 'rgba(245,158,11,0.15)' : 'rgba(245,158,11,0.1)' }]}>
            <MaterialCommunityIcons name="calculator-variant" size={18} color="#F59E0B" />
          </View>
          <View>
            <Text style={[styles.title, { color: colors.textPrimary }]}>Tax Meter</Text>
            <Text style={[styles.subtitle, { color: colors.textSecondary }]}>FY {data.fy}</Text>
          </View>
        </View>
        <MaterialCommunityIcons name="chevron-right" size={20} color={colors.textSecondary} />
      </View>

      {/* Main Stats Row */}
      <View style={styles.statsRow}>
        <View style={styles.statItem}>
          <Text style={[styles.statLabel, { color: colors.textSecondary }]}>Est. Tax</Text>
          <Text style={[styles.statValue, { color: colors.textPrimary }]}>
            {formatINRShort(data.estimated_tax)}
          </Text>
        </View>
        <View style={[styles.divider, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]} />
        <View style={styles.statItem}>
          <Text style={[styles.statLabel, { color: colors.textSecondary }]}>TDS Paid</Text>
          <Text style={[styles.statValue, { color: Accent.emerald }]}>
            {formatINRShort(data.tds_paid_ytd)}
          </Text>
        </View>
        <View style={[styles.divider, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]} />
        <View style={styles.statItem}>
          <Text style={[styles.statLabel, { color: colors.textSecondary }]}>
            {hasRefund ? 'Refund' : 'Due'}
          </Text>
          <Text style={[styles.statValue, { color: hasRefund ? Accent.emerald : Accent.ruby }]}>
            {formatINRShort(hasRefund ? data.refund_expected : data.tax_due)}
          </Text>
        </View>
      </View>

      {/* Progress Bar */}
      <View style={styles.progressSection}>
        <View style={styles.progressHeader}>
          <Text style={[styles.progressLabel, { color: colors.textSecondary }]}>
            TDS Progress ({data.months_elapsed} of 12 months)
          </Text>
          <Text style={[styles.progressPct, { color: progressPct >= 80 ? Accent.emerald : '#F59E0B' }]}>
            {progressPct.toFixed(0)}%
          </Text>
        </View>
        <View style={[styles.progressBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
          <View 
            style={[
              styles.progressFill, 
              { 
                width: `${progressPct}%`, 
                backgroundColor: progressPct >= 80 ? Accent.emerald : '#F59E0B',
              }
            ]} 
          />
        </View>
      </View>

      {/* 80C Utilization Mini Bar */}
      <View style={styles.deductionRow}>
        <View style={{ flex: 1 }}>
          <View style={styles.deductionHeader}>
            <Text style={[styles.deductionLabel, { color: colors.textSecondary }]}>80C Used</Text>
            <Text style={[styles.deductionValue, { color: colors.textPrimary }]}>
              {formatINRShort(data.deduction_80c.used)} / ₹1.5L
            </Text>
          </View>
          <View style={[styles.miniProgressBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.04)' }]}>
            <View 
              style={[
                styles.miniProgressFill, 
                { 
                  width: `${data.deduction_80c.utilization_pct}%`, 
                  backgroundColor: data.deduction_80c.utilization_pct >= 90 ? Accent.emerald : '#8B5CF6',
                }
              ]} 
            />
          </View>
        </View>
        {data.savings_by_switch > 0 && (
          <View style={[styles.regimeBadge, { backgroundColor: 'rgba(16,185,129,0.1)' }]}>
            <MaterialCommunityIcons name="arrow-right-bold" size={10} color={Accent.emerald} />
            <Text style={[styles.regimeText, { color: Accent.emerald }]}>
              {data.better_regime === 'new' ? 'New' : 'Old'} saves {formatINRShort(data.savings_by_switch)}
            </Text>
          </View>
        )}
      </View>

      {/* Effective Rate Badge */}
      <View style={styles.footer}>
        <View style={[styles.rateBadge, { backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.03)' }]}>
          <Text style={[styles.rateLabel, { color: colors.textSecondary }]}>Effective Tax Rate</Text>
          <Text style={[styles.rateValue, { color: '#F59E0B' }]}>{data.effective_rate}%</Text>
        </View>
      </View>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: {
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    marginBottom: 16,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 14,
  },
  iconWrap: {
    width: 36,
    height: 36,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  title: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  subtitle: {
    fontSize: 11,
    fontFamily: 'DM Sans',
  },
  statsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 14,
  },
  statItem: {
    flex: 1,
    alignItems: 'center',
  },
  statLabel: {
    fontSize: 10,
    fontFamily: 'DM Sans',
    marginBottom: 2,
  },
  statValue: {
    fontSize: 15,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  divider: {
    width: 1,
    height: 30,
  },
  progressSection: {
    marginBottom: 12,
  },
  progressHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  progressLabel: {
    fontSize: 11,
    fontFamily: 'DM Sans',
  },
  progressPct: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  progressBg: {
    height: 6,
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 3,
  },
  deductionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 10,
  },
  deductionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  deductionLabel: {
    fontSize: 10,
    fontFamily: 'DM Sans',
  },
  deductionValue: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    fontWeight: '600',
  },
  miniProgressBg: {
    height: 4,
    borderRadius: 2,
    overflow: 'hidden',
  },
  miniProgressFill: {
    height: '100%',
    borderRadius: 2,
  },
  regimeBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  regimeText: {
    fontSize: 9,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  footer: {
    alignItems: 'flex-start',
  },
  rateBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 8,
  },
  rateLabel: {
    fontSize: 10,
    fontFamily: 'DM Sans',
  },
  rateValue: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
});
