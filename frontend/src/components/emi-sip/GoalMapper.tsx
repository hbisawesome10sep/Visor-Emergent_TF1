import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ActivityIndicator } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { apiRequest } from '../../utils/api';
import { formatINRShort } from '../../utils/formatters';

type GoalAnalysis = {
  goal_id: string; goal_title: string; target_amount: number;
  current_amount: number; gap: number; deadline: string;
  months_left: number; sip_needed_monthly: number;
  mapped_sip_amount: number; shortfall: number;
  on_track: boolean; mapped_sips: string[];
};

type SipItem = { id: string; name: string; amount: number; monthly_equivalent: number; category: string; mapped_goal_id: string };
type Props = { token: string; isDark: boolean; colors: any };

export const GoalMapper = ({ token, isDark, colors }: Props) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [expandedGoal, setExpandedGoal] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    try {
      const res = await apiRequest('/sip-analytics/goal-map', { token, method: 'POST', body: {} });
      setData(res);
    } catch (e) { console.warn(e); }
    finally { setLoading(false); }
  }, [token]);

  useEffect(() => { fetch(); }, [fetch]);

  if (loading) return <ActivityIndicator color={colors.primary} style={{ padding: 24 }} />;

  const goals: GoalAnalysis[] = data?.goal_analysis || [];
  const unmapped: SipItem[] = data?.unmapped_sips || [];
  const onTrack = data?.goals_on_track || 0;
  const totalGoals = data?.total_goals || 0;

  if (totalGoals === 0 && unmapped.length === 0) {
    return (
      <View style={s.empty} data-testid="goal-mapper-empty">
        <MaterialCommunityIcons name="target" size={40} color={colors.textSecondary} />
        <Text style={[s.emptyText, { color: colors.textSecondary }]}>No goals or SIPs found</Text>
        <Text style={[s.emptyHint, { color: colors.textSecondary }]}>Create goals and SIPs in Investments to see the mapping</Text>
      </View>
    );
  }

  return (
    <View data-testid="goal-mapper-section">
      <View style={[s.hdr, { backgroundColor: isDark ? 'rgba(245,158,11,0.08)' : 'rgba(245,158,11,0.04)' }]}>
        <MaterialCommunityIcons name="bullseye-arrow" size={20} color="#F59E0B" />
        <Text style={[s.hdrText, { color: colors.textPrimary }]}>Goal Mapping</Text>
      </View>

      <Text style={[s.desc, { color: colors.textSecondary }]}>
        See if your SIPs are sufficient to reach your financial goals.
      </Text>

      {/* Summary */}
      <View style={[s.summaryBox, {
        backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)',
        borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
      }]}>
        <View style={s.summaryItem}>
          <Text style={[s.summaryLabel, { color: colors.textSecondary }]}>Monthly SIP</Text>
          <Text style={[s.summaryVal, { color: colors.textPrimary }]}>{formatINRShort(data?.total_monthly_sip || 0)}</Text>
        </View>
        <View style={s.summaryItem}>
          <Text style={[s.summaryLabel, { color: colors.textSecondary }]}>Goals</Text>
          <Text style={[s.summaryVal, { color: colors.textPrimary }]}>{totalGoals}</Text>
        </View>
        <View style={s.summaryItem}>
          <Text style={[s.summaryLabel, { color: colors.textSecondary }]}>On Track</Text>
          <Text style={[s.summaryVal, { color: onTrack > 0 ? '#10B981' : '#EF4444' }]}>
            {onTrack}/{totalGoals}
          </Text>
        </View>
      </View>

      {/* Goal cards */}
      {goals.map((g) => {
        const isExpanded = expandedGoal === g.goal_id;
        const progressPct = g.target_amount > 0 ? Math.min(100, (g.current_amount / g.target_amount) * 100) : 0;
        const statusColor = g.on_track ? '#10B981' : g.shortfall > g.sip_needed_monthly ? '#EF4444' : '#F59E0B';

        return (
          <TouchableOpacity
            key={g.goal_id}
            onPress={() => setExpandedGoal(isExpanded ? null : g.goal_id)}
            style={[s.goalCard, {
              backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)',
              borderColor: statusColor + '30',
            }]}
            data-testid={`goal-card-${g.goal_id}`}
          >
            <View style={s.goalTop}>
              <View style={[s.goalStatus, { backgroundColor: statusColor + '18' }]}>
                <MaterialCommunityIcons
                  name={g.on_track ? 'check-circle' : 'alert-circle'}
                  size={18} color={statusColor}
                />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={[s.goalTitle, { color: colors.textPrimary }]}>{g.goal_title}</Text>
                <Text style={[s.goalDeadline, { color: colors.textSecondary }]}>
                  {g.months_left} months left | {g.deadline || 'No deadline'}
                </Text>
              </View>
              <View style={{ alignItems: 'flex-end' }}>
                <Text style={[s.goalTarget, { color: colors.textPrimary }]}>{formatINRShort(g.target_amount)}</Text>
                <Text style={[s.goalCurrent, { color: statusColor }]}>{formatINRShort(g.current_amount)} saved</Text>
              </View>
            </View>

            {/* Progress bar */}
            <View style={[s.progressBar, { backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)' }]}>
              <View style={[s.progressFill, { width: `${progressPct}%`, backgroundColor: statusColor }]} />
            </View>
            <Text style={[s.progressText, { color: colors.textSecondary }]}>{progressPct.toFixed(0)}% achieved</Text>

            {isExpanded && (
              <View style={[s.expandSection, { borderTopColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)' }]}>
                <View style={s.expandRow}>
                  <Text style={[s.expLabel, { color: colors.textSecondary }]}>Gap to Goal</Text>
                  <Text style={[s.expVal, { color: '#EF4444' }]}>{formatINRShort(g.gap)}</Text>
                </View>
                <View style={s.expandRow}>
                  <Text style={[s.expLabel, { color: colors.textSecondary }]}>SIP Needed (at 12% p.a.)</Text>
                  <Text style={[s.expVal, { color: '#F59E0B' }]}>{formatINRShort(g.sip_needed_monthly)}/mo</Text>
                </View>
                <View style={s.expandRow}>
                  <Text style={[s.expLabel, { color: colors.textSecondary }]}>Mapped SIP Amount</Text>
                  <Text style={[s.expVal, { color: '#10B981' }]}>{formatINRShort(g.mapped_sip_amount)}/mo</Text>
                </View>
                {g.shortfall > 0 && (
                  <View style={[s.shortfallBox, { backgroundColor: '#EF444410' }]}>
                    <MaterialCommunityIcons name="alert" size={14} color="#EF4444" />
                    <Text style={s.shortfallText}>
                      Shortfall: {formatINRShort(g.shortfall)}/mo. Consider starting a new SIP or increasing existing ones.
                    </Text>
                  </View>
                )}
                {g.mapped_sips.length > 0 && (
                  <View style={{ marginTop: 6 }}>
                    <Text style={[s.expLabel, { color: colors.textSecondary, marginBottom: 4 }]}>Linked SIPs:</Text>
                    {g.mapped_sips.map((name, i) => (
                      <Text key={i} style={[s.linkedSip, { color: colors.textPrimary }]}>{name}</Text>
                    ))}
                  </View>
                )}
              </View>
            )}
          </TouchableOpacity>
        );
      })}

      {/* Unmapped SIPs */}
      {unmapped.length > 0 && (
        <View style={{ marginTop: 12 }}>
          <Text style={[s.subhead, { color: colors.textPrimary }]}>Unmapped SIPs</Text>
          <Text style={[s.desc, { color: colors.textSecondary, marginBottom: 8 }]}>
            These SIPs aren't linked to any goal yet.
          </Text>
          {unmapped.map(sip => (
            <View key={sip.id} style={[s.unmappedCard, {
              backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)',
              borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
            }]}>
              <MaterialCommunityIcons name="repeat" size={16} color="#3B82F6" />
              <View style={{ flex: 1 }}>
                <Text style={[s.unmappedName, { color: colors.textPrimary }]}>{sip.name}</Text>
              </View>
              <Text style={[s.unmappedAmt, { color: colors.textPrimary }]}>{formatINRShort(sip.monthly_equivalent)}/mo</Text>
            </View>
          ))}
        </View>
      )}
    </View>
  );
};

const s = StyleSheet.create({
  empty: { alignItems: 'center', padding: 32, gap: 8 },
  emptyText: { fontSize: 15, fontWeight: '600' },
  emptyHint: { fontSize: 13, textAlign: 'center' },
  hdr: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 14, paddingVertical: 10, borderRadius: 10, marginBottom: 8 },
  hdrText: { fontSize: 15, fontWeight: '700' },
  desc: { fontSize: 13, paddingHorizontal: 4 },
  summaryBox: { flexDirection: 'row', borderWidth: 1, borderRadius: 10, paddingVertical: 10, paddingHorizontal: 8, marginVertical: 12, justifyContent: 'space-around' },
  summaryItem: { alignItems: 'center' },
  summaryLabel: { fontSize: 10 },
  summaryVal: { fontSize: 15, fontWeight: '700' },
  goalCard: { borderRadius: 12, borderWidth: 1, padding: 14, marginBottom: 10 },
  goalTop: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  goalStatus: { width: 34, height: 34, borderRadius: 8, alignItems: 'center', justifyContent: 'center' },
  goalTitle: { fontSize: 14, fontWeight: '600' },
  goalDeadline: { fontSize: 11, marginTop: 2 },
  goalTarget: { fontSize: 14, fontWeight: '700' },
  goalCurrent: { fontSize: 11, fontWeight: '500' },
  progressBar: { height: 6, borderRadius: 3, overflow: 'hidden', marginTop: 10 },
  progressFill: { height: '100%', borderRadius: 3 },
  progressText: { fontSize: 11, marginTop: 4 },
  expandSection: { borderTopWidth: 1, marginTop: 10, paddingTop: 10 },
  expandRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  expLabel: { fontSize: 12 },
  expVal: { fontSize: 13, fontWeight: '600' },
  shortfallBox: { flexDirection: 'row', gap: 6, padding: 10, borderRadius: 8, marginTop: 6, alignItems: 'flex-start' },
  shortfallText: { flex: 1, fontSize: 12, color: '#EF4444', lineHeight: 16 },
  linkedSip: { fontSize: 12, fontWeight: '500', marginBottom: 2, paddingLeft: 8 },
  subhead: { fontSize: 14, fontWeight: '700', marginBottom: 4 },
  unmappedCard: { flexDirection: 'row', alignItems: 'center', gap: 10, padding: 12, borderRadius: 10, borderWidth: 1, marginBottom: 6 },
  unmappedName: { fontSize: 13, fontWeight: '500' },
  unmappedAmt: { fontSize: 13, fontWeight: '700' },
});
