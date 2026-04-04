import React, { useEffect, useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { apiRequest } from '../../utils/api';
import { formatINRShort } from '../../utils/formatters';
import { Accent } from '../../utils/theme';

interface TDSMismatchCardProps {
  token: string;
  colors: any;
  isDark: boolean;
}

interface TDSSource {
  source: string;
  source_type: string;
  deductor: string;
  expected_tds: number | null;
  reported_tds: number | null;
  mismatch: number | null;
  mismatch_pct?: number;
  status: string;
  tan?: string;
}

export const TDSMismatchCard: React.FC<TDSMismatchCardProps> = ({ token, colors, isDark }) => {
  const [data, setData] = useState<{
    tds_sources: TDSSource[];
    summary: any;
    recommendations: (string | null)[];
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const result = await apiRequest('/tax/tds-mismatch?fy=2025-26', { token });
        setData(result);
      } catch (e) {
        console.error('TDS mismatch fetch error:', e);
      } finally {
        setLoading(false);
      }
    };
    if (token) fetchData();
  }, [token]);

  if (loading) {
    return (
      <View style={[styles.card, { backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.9)', borderColor: isDark ? 'rgba(245,158,11,0.15)' : 'rgba(245,158,11,0.1)' }]}>
        <ActivityIndicator size="small" color="#F59E0B" />
      </View>
    );
  }

  if (!data) return null;

  const { summary, tds_sources, recommendations } = data;
  const statusColor = summary.status === 'all_matched' 
    ? Accent.emerald 
    : summary.status === 'minor_mismatch' 
      ? '#F59E0B' 
      : '#EF4444';

  const statusIcon = summary.status === 'all_matched' 
    ? 'check-circle' 
    : summary.status === 'minor_mismatch' 
      ? 'alert-circle' 
      : 'alert-octagon';

  return (
    <View style={{ marginBottom: 16 }}>
      <TouchableOpacity
        data-testid="tds-mismatch-header"
        style={[styles.card, {
          backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.9)',
          borderColor: isDark ? 'rgba(245,158,11,0.15)' : 'rgba(245,158,11,0.1)',
        }]}
        onPress={() => setExpanded(!expanded)}
        activeOpacity={0.7}
      >
        <View style={styles.header}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
            <View style={[styles.iconWrap, { backgroundColor: `${statusColor}15` }]}>
              <MaterialCommunityIcons name={statusIcon as any} size={18} color={statusColor} />
            </View>
            <View>
              <Text style={[styles.title, { color: colors.textPrimary }]}>TDS Verification</Text>
              <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
                {summary.status === 'all_matched' 
                  ? 'All TDS matched'
                  : summary.status === 'minor_mismatch'
                    ? 'Minor variance detected'
                    : 'Verification needed'
                }
              </Text>
            </View>
          </View>
          <View style={{ alignItems: 'flex-end' }}>
            {summary.overall_difference > 0 && (
              <>
                <Text style={[styles.diffLabel, { color: colors.textSecondary }]}>Difference</Text>
                <Text style={[styles.diffValue, { color: statusColor }]}>
                  {formatINRShort(summary.overall_difference)}
                </Text>
              </>
            )}
          </View>
        </View>

        {/* Quick Summary */}
        <View style={styles.summaryRow}>
          <View style={styles.summaryItem}>
            <Text style={[styles.summaryLabel, { color: colors.textSecondary }]}>Expected TDS</Text>
            <Text style={[styles.summaryValue, { color: colors.textPrimary }]}>
              {formatINRShort(summary.total_expected_tds)}
            </Text>
          </View>
          <View style={[styles.summaryDivider, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]} />
          <View style={styles.summaryItem}>
            <Text style={[styles.summaryLabel, { color: colors.textSecondary }]}>In Form 26AS</Text>
            <Text style={[styles.summaryValue, { color: summary.total_reported_tds > 0 ? Accent.emerald : colors.textSecondary }]}>
              {summary.total_reported_tds > 0 ? formatINRShort(summary.total_reported_tds) : 'Not uploaded'}
            </Text>
          </View>
        </View>

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
          borderColor: isDark ? 'rgba(245,158,11,0.1)' : 'rgba(245,158,11,0.06)',
        }]}>
          {/* TDS Sources */}
          <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>
            TDS Sources
          </Text>
          {tds_sources.map((source, idx) => (
            <View key={idx} style={[styles.sourceItem, { borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)' }]}>
              <View style={styles.sourceHeader}>
                <Text style={[styles.sourceDeductor, { color: colors.textPrimary }]} numberOfLines={1}>
                  {source.deductor}
                </Text>
                <View style={[styles.statusBadge, { 
                  backgroundColor: source.status === 'matched' 
                    ? 'rgba(16,185,129,0.1)' 
                    : source.status.includes('mismatch')
                      ? 'rgba(239,68,68,0.1)'
                      : 'rgba(245,158,11,0.1)'
                }]}>
                  <Text style={[styles.statusText, { 
                    color: source.status === 'matched' 
                      ? Accent.emerald 
                      : source.status.includes('mismatch')
                        ? '#EF4444'
                        : '#F59E0B'
                  }]}>
                    {source.status === 'matched' ? 'Matched' 
                      : source.status === 'not_found_in_26as' ? 'Upload 26AS'
                      : source.status === 'additional_in_26as' ? 'Extra in 26AS'
                      : 'Mismatch'}
                  </Text>
                </View>
              </View>
              <View style={styles.sourceDetails}>
                {source.expected_tds !== null && (
                  <Text style={[styles.sourceAmount, { color: colors.textSecondary }]}>
                    Expected: {formatINRShort(source.expected_tds)}
                  </Text>
                )}
                {source.reported_tds !== null && (
                  <Text style={[styles.sourceAmount, { color: Accent.emerald }]}>
                    Reported: {formatINRShort(source.reported_tds)}
                  </Text>
                )}
              </View>
            </View>
          ))}

          {/* Recommendations */}
          {recommendations.filter(Boolean).length > 0 && (
            <View style={styles.recsSection}>
              <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>
                Actions Needed
              </Text>
              {recommendations.filter(Boolean).map((rec, idx) => (
                <View key={idx} style={styles.recItem}>
                  <MaterialCommunityIcons name="information-outline" size={14} color="#F59E0B" />
                  <Text style={[styles.recText, { color: colors.textSecondary }]}>
                    {rec}
                  </Text>
                </View>
              ))}
            </View>
          )}
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
    marginBottom: 12,
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
  diffLabel: {
    fontSize: 10,
    fontFamily: 'DM Sans',
  },
  diffValue: {
    fontSize: 16,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  summaryRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  summaryItem: {
    flex: 1,
    alignItems: 'center',
  },
  summaryLabel: {
    fontSize: 10,
    fontFamily: 'DM Sans',
    marginBottom: 2,
  },
  summaryValue: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  summaryDivider: {
    width: 1,
    height: 30,
  },
  expandedSection: {
    marginTop: 8,
    padding: 14,
    borderRadius: 14,
    borderWidth: 1,
  },
  sectionTitle: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    fontWeight: '700',
    marginBottom: 10,
  },
  sourceItem: {
    paddingVertical: 10,
    borderBottomWidth: 1,
  },
  sourceHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  sourceDeductor: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    fontWeight: '600',
    flex: 1,
    marginRight: 10,
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
  sourceDetails: {
    flexDirection: 'row',
    gap: 16,
  },
  sourceAmount: {
    fontSize: 11,
    fontFamily: 'DM Sans',
  },
  recsSection: {
    marginTop: 12,
  },
  recItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    marginBottom: 8,
  },
  recText: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    flex: 1,
  },
});
