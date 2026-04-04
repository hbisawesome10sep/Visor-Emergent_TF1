import React, { useEffect, useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, ScrollView } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { apiRequest } from '../../utils/api';
import { formatINRShort } from '../../utils/formatters';
import { Accent } from '../../utils/theme';

interface DeductionGapCardProps {
  token: string;
  colors: any;
  isDark: boolean;
}

interface GapItem {
  section: string;
  limit: number;
  used: number;
  remaining: number;
  utilization_pct: number;
  status: string;
  potential_tax_savings_30: number;
  recommendations: {
    product: string;
    priority: number;
    lock_in: string;
    expected_returns: string;
    tax_benefit: string;
  }[];
}

interface TopAction {
  section: string;
  action: string;
  tax_savings: string;
  product: string;
}

export const DeductionGapCard: React.FC<DeductionGapCardProps> = ({ token, colors, isDark }) => {
  const [data, setData] = useState<{ gaps: GapItem[]; summary: any; top_actions: TopAction[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const result = await apiRequest('/tax/deduction-gap?fy=2025-26', { token });
        setData(result);
      } catch (e) {
        console.error('Deduction gap fetch error:', e);
      } finally {
        setLoading(false);
      }
    };
    if (token) fetchData();
  }, [token]);

  if (loading) {
    return (
      <View style={[styles.card, { backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.9)', borderColor: isDark ? 'rgba(139,92,246,0.15)' : 'rgba(139,92,246,0.1)' }]}>
        <ActivityIndicator size="small" color="#8B5CF6" />
      </View>
    );
  }

  if (!data || data.gaps.length === 0) return null;

  const totalSavings = data.summary?.potential_tax_savings || 0;
  const underUtilized = data.summary?.sections_under_utilized || 0;

  return (
    <View style={{ marginBottom: 16 }}>
      {/* Header */}
      <TouchableOpacity
        data-testid="deduction-gap-header"
        style={[styles.card, {
          backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.9)',
          borderColor: isDark ? 'rgba(139,92,246,0.15)' : 'rgba(139,92,246,0.1)',
        }]}
        onPress={() => setExpanded(!expanded)}
        activeOpacity={0.7}
      >
        <View style={styles.header}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
            <View style={[styles.iconWrap, { backgroundColor: 'rgba(139,92,246,0.12)' }]}>
              <MaterialCommunityIcons name="chart-arc" size={18} color="#8B5CF6" />
            </View>
            <View>
              <Text style={[styles.title, { color: colors.textPrimary }]}>Deduction Gap Analysis</Text>
              <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
                {underUtilized} sections under-utilized
              </Text>
            </View>
          </View>
          <View style={{ alignItems: 'flex-end' }}>
            <Text style={[styles.savingsLabel, { color: colors.textSecondary }]}>Potential Savings</Text>
            <Text style={[styles.savingsValue, { color: Accent.emerald }]}>
              {formatINRShort(totalSavings)}
            </Text>
          </View>
        </View>

        {/* Top Actions Preview */}
        {data.top_actions.length > 0 && !expanded && (
          <View style={styles.actionsPreview}>
            {data.top_actions.slice(0, 2).map((action, idx) => (
              <View key={idx} style={[styles.actionChip, { backgroundColor: 'rgba(139,92,246,0.08)' }]}>
                <MaterialCommunityIcons name="lightbulb-outline" size={12} color="#8B5CF6" />
                <Text style={[styles.actionChipText, { color: colors.textPrimary }]} numberOfLines={1}>
                  {action.product}
                </Text>
              </View>
            ))}
          </View>
        )}

        <MaterialCommunityIcons 
          name={expanded ? 'chevron-up' : 'chevron-down'} 
          size={20} 
          color={colors.textSecondary}
          style={{ position: 'absolute', right: 14, top: 14 }}
        />
      </TouchableOpacity>

      {/* Expanded Details */}
      {expanded && (
        <View style={[styles.expandedSection, {
          backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.9)',
          borderColor: isDark ? 'rgba(139,92,246,0.1)' : 'rgba(139,92,246,0.06)',
        }]}>
          {/* Top Actions */}
          {data.top_actions.length > 0 && (
            <View style={styles.topActionsSection}>
              <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>
                Top Recommendations
              </Text>
              {data.top_actions.map((action, idx) => (
                <View key={idx} style={[styles.actionItem, { backgroundColor: 'rgba(139,92,246,0.06)' }]}>
                  <View style={[styles.actionNumber, { backgroundColor: '#8B5CF6' }]}>
                    <Text style={styles.actionNumberText}>{idx + 1}</Text>
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={[styles.actionTitle, { color: colors.textPrimary }]}>
                      {action.product}
                    </Text>
                    <Text style={[styles.actionDesc, { color: colors.textSecondary }]}>
                      {action.action}
                    </Text>
                    <Text style={[styles.actionSaving, { color: Accent.emerald }]}>
                      {action.tax_savings}
                    </Text>
                  </View>
                </View>
              ))}
            </View>
          )}

          {/* Section-wise Gaps */}
          <Text style={[styles.sectionTitle, { color: colors.textPrimary, marginTop: 12 }]}>
            Section-wise Breakdown
          </Text>
          {data.gaps.filter(g => g.remaining > 0).slice(0, 5).map((gap, idx) => (
            <View key={idx} style={[styles.gapItem, { borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)' }]}>
              <View style={styles.gapHeader}>
                <Text style={[styles.gapSection, { color: colors.textPrimary }]}>
                  Section {gap.section}
                </Text>
                <View style={[styles.statusBadge, { 
                  backgroundColor: gap.status === 'under_utilized' 
                    ? 'rgba(239,68,68,0.1)' 
                    : gap.status === 'good' 
                      ? 'rgba(245,158,11,0.1)'
                      : 'rgba(16,185,129,0.1)'
                }]}>
                  <Text style={[styles.statusText, { 
                    color: gap.status === 'under_utilized' 
                      ? '#EF4444' 
                      : gap.status === 'good' 
                        ? '#F59E0B'
                        : Accent.emerald
                  }]}>
                    {gap.utilization_pct.toFixed(0)}% used
                  </Text>
                </View>
              </View>
              
              {/* Progress Bar */}
              <View style={[styles.progressBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.04)' }]}>
                <View 
                  style={[styles.progressFill, { 
                    width: `${Math.min(100, gap.utilization_pct)}%`,
                    backgroundColor: gap.utilization_pct >= 90 ? Accent.emerald : gap.utilization_pct >= 50 ? '#F59E0B' : '#EF4444',
                  }]} 
                />
              </View>
              
              <View style={styles.gapFooter}>
                <Text style={[styles.gapAmount, { color: colors.textSecondary }]}>
                  {formatINRShort(gap.used)} / {formatINRShort(gap.limit)}
                </Text>
                <Text style={[styles.gapRemaining, { color: '#8B5CF6' }]}>
                  {formatINRShort(gap.remaining)} remaining
                </Text>
              </View>
            </View>
          ))}
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  iconWrap: {
    width: 40,
    height: 40,
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
    marginTop: 2,
  },
  savingsLabel: {
    fontSize: 10,
    fontFamily: 'DM Sans',
  },
  savingsValue: {
    fontSize: 16,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  actionsPreview: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 12,
  },
  actionChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 8,
  },
  actionChipText: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    fontWeight: '500',
  },
  expandedSection: {
    marginTop: 8,
    padding: 14,
    borderRadius: 14,
    borderWidth: 1,
  },
  topActionsSection: {
    marginBottom: 8,
  },
  sectionTitle: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    fontWeight: '700',
    marginBottom: 10,
  },
  actionItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
    padding: 10,
    borderRadius: 10,
    marginBottom: 8,
  },
  actionNumber: {
    width: 22,
    height: 22,
    borderRadius: 11,
    justifyContent: 'center',
    alignItems: 'center',
  },
  actionNumberText: {
    color: '#fff',
    fontSize: 11,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  actionTitle: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    fontWeight: '600',
  },
  actionDesc: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    marginTop: 2,
  },
  actionSaving: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    fontWeight: '600',
    marginTop: 4,
  },
  gapItem: {
    paddingVertical: 10,
    borderBottomWidth: 1,
  },
  gapHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  gapSection: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    fontWeight: '600',
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  statusText: {
    fontSize: 10,
    fontFamily: 'DM Sans',
    fontWeight: '600',
  },
  progressBg: {
    height: 4,
    borderRadius: 2,
    overflow: 'hidden',
    marginBottom: 6,
  },
  progressFill: {
    height: '100%',
    borderRadius: 2,
  },
  gapFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  gapAmount: {
    fontSize: 10,
    fontFamily: 'DM Sans',
  },
  gapRemaining: {
    fontSize: 10,
    fontFamily: 'DM Sans',
    fontWeight: '600',
  },
});
