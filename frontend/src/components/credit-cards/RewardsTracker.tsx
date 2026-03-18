import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { apiRequest } from '../../utils/api';

type CardReward = {
  card_name: string;
  last_four: string;
  total_spend: number;
  reward_points: number;
  rupee_value: number;
  point_value: number;
  benefits: string[];
  monthly_trend: { month: string; points: number; spend: number }[];
};

type Props = { token: string; isDark: boolean; colors: any };

const fmtINR = (n: number) => n >= 100000 ? `${(n / 100000).toFixed(1)}L` : n >= 1000 ? `${(n / 1000).toFixed(1)}K` : n.toFixed(0);

export const RewardsTracker = ({ token, isDark, colors }: Props) => {
  const [data, setData] = useState<{ total_points: number; total_rupee_value: number; cards: CardReward[] } | null>(null);
  const [loading, setLoading] = useState(true);

  const fetch = useCallback(async () => {
    try {
      const res = await apiRequest('/credit-cards/rewards', { token });
      setData(res);
    } catch (e) { console.warn(e); }
    finally { setLoading(false); }
  }, [token]);

  useEffect(() => { fetch(); }, [fetch]);

  if (loading) return <ActivityIndicator style={{ padding: 40 }} color={colors.primary} />;

  if (!data) return null;

  const maxTrend = Math.max(...(data.cards[0]?.monthly_trend.map(m => m.points) || [1]));

  return (
    <View testID="cc-rewards-tracker">
      {/* Summary */}
      <View style={[s.summaryCard, { backgroundColor: isDark ? 'rgba(139,92,246,0.1)' : 'rgba(139,92,246,0.04)', borderColor: isDark ? 'rgba(139,92,246,0.25)' : 'rgba(139,92,246,0.15)' }]}>
        <View style={s.summaryRow}>
          <View style={[s.summaryIconBg, { backgroundColor: isDark ? 'rgba(139,92,246,0.2)' : 'rgba(139,92,246,0.1)' }]}>
            <MaterialCommunityIcons name="star-circle" size={24} color="#8B5CF6" />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={[s.summaryLabel, { color: colors.textSecondary }]}>Total Rewards</Text>
            <Text style={[s.summaryPoints, { color: '#8B5CF6' }]}>{data.total_points.toLocaleString()} pts</Text>
          </View>
          <View style={{ alignItems: 'flex-end' }}>
            <Text style={[s.summaryLabel, { color: colors.textSecondary }]}>Value</Text>
            <Text style={[s.summaryValue, { color: '#10B981' }]}>Rs {fmtINR(data.total_rupee_value)}</Text>
          </View>
        </View>
      </View>

      {/* Per Card Breakdown */}
      {data.cards.map((card, idx) => (
        <View key={idx} style={[s.cardBlock, { backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : '#fff', borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
          <View style={s.cardHeader}>
            <MaterialCommunityIcons name="credit-card-outline" size={18} color="#8B5CF6" />
            <Text style={[s.cardName, { color: colors.textPrimary }]}>{card.card_name}</Text>
            <Text style={[s.cardFour, { color: colors.textSecondary }]}>*{card.last_four}</Text>
          </View>

          <View style={s.statsRow}>
            <View style={s.statCol}>
              <Text style={[s.statLabel, { color: colors.textSecondary }]}>Spend</Text>
              <Text style={[s.statVal, { color: colors.textPrimary }]}>Rs {fmtINR(card.total_spend)}</Text>
            </View>
            <View style={s.statCol}>
              <Text style={[s.statLabel, { color: colors.textSecondary }]}>Points</Text>
              <Text style={[s.statVal, { color: '#8B5CF6' }]}>{card.reward_points}</Text>
            </View>
            <View style={s.statCol}>
              <Text style={[s.statLabel, { color: colors.textSecondary }]}>Value</Text>
              <Text style={[s.statVal, { color: '#10B981' }]}>Rs {card.rupee_value.toFixed(0)}</Text>
            </View>
          </View>

          {/* Mini Trend */}
          <View style={s.trendRow}>
            {card.monthly_trend.map((m, i) => {
              const h = maxTrend > 0 ? Math.max(4, (m.points / maxTrend) * 40) : 4;
              return (
                <View key={i} style={s.trendCol}>
                  <View style={[s.trendBar, { height: h, backgroundColor: m.points > 0 ? '#8B5CF6' : isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]} />
                  <Text style={[s.trendLabel, { color: colors.textSecondary }]}>{m.month}</Text>
                </View>
              );
            })}
          </View>

          {/* Benefits */}
          {card.benefits.length > 0 && (
            <View style={[s.benefitsBox, { backgroundColor: isDark ? 'rgba(139,92,246,0.06)' : 'rgba(139,92,246,0.03)' }]}>
              {card.benefits.slice(0, 3).map((b, i) => (
                <View key={i} style={s.benefitRow}>
                  <MaterialCommunityIcons name="check-circle" size={13} color="#8B5CF6" />
                  <Text style={[s.benefitText, { color: colors.textSecondary }]}>{b}</Text>
                </View>
              ))}
            </View>
          )}
        </View>
      ))}
    </View>
  );
};

const s = StyleSheet.create({
  summaryCard: { borderRadius: 16, borderWidth: 1, padding: 16, marginBottom: 14 },
  summaryRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  summaryIconBg: { width: 44, height: 44, borderRadius: 14, alignItems: 'center', justifyContent: 'center' },
  summaryLabel: { fontSize: 11, fontWeight: '500', marginBottom: 2 },
  summaryPoints: { fontSize: 22, fontWeight: '800' },
  summaryValue: { fontSize: 18, fontWeight: '700' },
  cardBlock: { borderRadius: 14, borderWidth: 1, padding: 14, marginBottom: 10 },
  cardHeader: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 12 },
  cardName: { fontSize: 14, fontWeight: '700', flex: 1 },
  cardFour: { fontSize: 12 },
  statsRow: { flexDirection: 'row', gap: 10, marginBottom: 12 },
  statCol: { flex: 1 },
  statLabel: { fontSize: 10, fontWeight: '500', marginBottom: 2 },
  statVal: { fontSize: 15, fontWeight: '700' },
  trendRow: { flexDirection: 'row', gap: 4, alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 12, height: 55 },
  trendCol: { flex: 1, alignItems: 'center', justifyContent: 'flex-end' },
  trendBar: { width: '70%', borderRadius: 3 },
  trendLabel: { fontSize: 9, marginTop: 3 },
  benefitsBox: { borderRadius: 10, padding: 10, gap: 6 },
  benefitRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  benefitText: { fontSize: 11, flex: 1 },
});
