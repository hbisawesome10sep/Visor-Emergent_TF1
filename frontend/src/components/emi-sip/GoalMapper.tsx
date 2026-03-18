import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ActivityIndicator, Modal, FlatList } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { apiRequest } from '../../utils/api';
import { formatINRShort } from '../../utils/formatters';
import { JarProgressView } from '../JarProgressView';

type GoalAnalysis = {
  goal_id: string; goal_title: string; target_amount: number;
  current_amount: number; gap: number; deadline: string;
  months_left: number; sip_needed_monthly: number;
  mapped_sip_amount: number; shortfall: number;
  on_track: boolean; mapped_sips: string[];
  mapped_sip_details?: Array<{ id: string; name: string }>;
};

type SipItem = {
  id: string; name: string; amount: number;
  monthly_equivalent: number; category: string; mapped_goal_id: string;
};

type Props = { token: string; isDark: boolean; colors: any };

type LinkModal = { visible: boolean; sipId: string; sipName: string } | null;

export const GoalMapper = ({ token, isDark, colors }: Props) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [expandedGoal, setExpandedGoal] = useState<string | null>(null);
  const [linkModal, setLinkModal] = useState<LinkModal>(null);
  const [linking, setLinking] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const res = await apiRequest('/sip-analytics/goal-map', { token, method: 'POST', body: {} });
      setData(res);
    } catch (e) { console.warn(e); }
    finally { setLoading(false); }
  }, [token]);

  useEffect(() => { loadData(); }, [loadData]);

  const handleLinkSip = async (goalId: string) => {
    if (!linkModal) return;
    setLinking(true);
    try {
      await apiRequest('/sip-analytics/link-sip', {
        token, method: 'POST',
        body: { sip_id: linkModal.sipId, goal_id: goalId },
      });
      setLinkModal(null);
      await loadData();
    } catch (e) { console.warn(e); }
    finally { setLinking(false); }
  };

  const handleUnlinkSip = async (sipId: string) => {
    try {
      await apiRequest('/sip-analytics/unlink-sip', {
        token, method: 'POST',
        body: { sip_id: sipId },
      });
      await loadData();
    } catch (e) { console.warn(e); }
  };

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
      {/* Header */}
      <View style={[s.hdr, { backgroundColor: isDark ? 'rgba(245,158,11,0.08)' : 'rgba(245,158,11,0.04)' }]}>
        <MaterialCommunityIcons name="bullseye-arrow" size={20} color="#F59E0B" />
        <Text style={[s.hdrText, { color: colors.textPrimary }]}>Goal Mapping</Text>
      </View>
      <Text style={[s.desc, { color: colors.textSecondary }]}>
        See if your SIPs are sufficient to reach your financial goals.
      </Text>

      {/* Summary row */}
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

      {/* Goal cards with jar visualization */}
      {goals.map((g) => {
        const isExpanded = expandedGoal === g.goal_id;
        const progressPct = g.target_amount > 0 ? Math.min(100, (g.current_amount / g.target_amount) * 100) : 0;
        const statusColor = g.on_track ? '#10B981' : g.shortfall > g.sip_needed_monthly ? '#EF4444' : '#F59E0B';
        const sip_details = g.mapped_sip_details || g.mapped_sips.map((name) => ({ id: '', name }));

        return (
          <TouchableOpacity
            key={g.goal_id}
            onPress={() => setExpandedGoal(isExpanded ? null : g.goal_id)}
            style={[s.goalCard, {
              backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)',
              borderColor: statusColor + '30',
            }]}
            data-testid={`goal-card-${g.goal_id}`}
            activeOpacity={0.85}
          >
            <View style={s.goalMain}>
              {/* Jar on left */}
              <JarProgressView
                percentage={progressPct}
                color={statusColor}
                uid={`gm-${g.goal_id}`}
                width={50}
              />

              {/* Content on right */}
              <View style={{ flex: 1 }}>
                <View style={s.goalTop}>
                  <View style={{ flex: 1 }}>
                    <Text style={[s.goalTitle, { color: colors.textPrimary }]}>{g.goal_title}</Text>
                    <Text style={[s.goalDeadline, { color: colors.textSecondary }]}>
                      {g.months_left} months left
                    </Text>
                  </View>
                  <View style={{ alignItems: 'flex-end' }}>
                    <Text style={[s.goalTarget, { color: colors.textPrimary }]}>{formatINRShort(g.target_amount)}</Text>
                    <Text style={[s.goalCurrent, { color: statusColor }]}>{formatINRShort(g.current_amount)} saved</Text>
                  </View>
                </View>

                {/* SIP status */}
                <View style={s.sipStatus}>
                  <MaterialCommunityIcons
                    name={g.on_track ? 'check-circle' : 'alert-circle'}
                    size={12} color={statusColor}
                  />
                  <Text style={[s.sipStatusText, { color: statusColor }]}>
                    {g.on_track ? 'On Track' : `Shortfall ${formatINRShort(g.shortfall)}/mo`}
                  </Text>
                  <MaterialCommunityIcons
                    name={isExpanded ? 'chevron-up' : 'chevron-down'}
                    size={14} color={colors.textSecondary}
                    style={{ marginLeft: 'auto' }}
                  />
                </View>
              </View>
            </View>

            {/* Expanded detail */}
            {isExpanded && (
              <View style={[s.expandSection, { borderTopColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)' }]}>
                <View style={s.expandRow}>
                  <Text style={[s.expLabel, { color: colors.textSecondary }]}>Gap to Goal</Text>
                  <Text style={[s.expVal, { color: '#EF4444' }]}>{formatINRShort(g.gap)}</Text>
                </View>
                <View style={s.expandRow}>
                  <Text style={[s.expLabel, { color: colors.textSecondary }]}>SIP Needed (12% p.a.)</Text>
                  <Text style={[s.expVal, { color: '#F59E0B' }]}>{formatINRShort(g.sip_needed_monthly)}/mo</Text>
                </View>
                <View style={s.expandRow}>
                  <Text style={[s.expLabel, { color: colors.textSecondary }]}>Mapped SIP Amount</Text>
                  <Text style={[s.expVal, { color: '#10B981' }]}>{formatINRShort(g.mapped_sip_amount)}/mo</Text>
                </View>

                {/* Linked SIPs with unlink option */}
                {sip_details.length > 0 && (
                  <View style={{ marginTop: 8 }}>
                    <Text style={[s.expLabel, { color: colors.textSecondary, marginBottom: 6 }]}>Linked SIPs:</Text>
                    {sip_details.map((sip, i) => (
                      <View key={sip.id || i} style={s.linkedSipRow}>
                        <MaterialCommunityIcons name="repeat" size={13} color="#3B82F6" />
                        <Text style={[s.linkedSip, { color: colors.textPrimary, flex: 1 }]}>{sip.name}</Text>
                        {sip.id ? (
                          <TouchableOpacity
                            data-testid={`unlink-sip-${sip.id}`}
                            onPress={() => handleUnlinkSip(sip.id)}
                            style={s.unlinkBtn}
                          >
                            <MaterialCommunityIcons name="link-off" size={13} color="#EF4444" />
                            <Text style={s.unlinkText}>Unlink</Text>
                          </TouchableOpacity>
                        ) : null}
                      </View>
                    ))}
                  </View>
                )}

                {g.shortfall > 0 && (
                  <View style={[s.shortfallBox, { backgroundColor: '#EF444410' }]}>
                    <MaterialCommunityIcons name="alert" size={14} color="#EF4444" />
                    <Text style={s.shortfallText}>
                      Shortfall: {formatINRShort(g.shortfall)}/mo. Consider linking more SIPs or starting a new one.
                    </Text>
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
            Link these SIPs to a goal to track progress.
          </Text>
          {unmapped.map(sip => (
            <View key={sip.id} style={[s.unmappedCard, {
              backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)',
              borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
            }]}>
              <MaterialCommunityIcons name="repeat" size={16} color="#3B82F6" />
              <View style={{ flex: 1 }}>
                <Text style={[s.unmappedName, { color: colors.textPrimary }]}>{sip.name}</Text>
                <Text style={[s.unmappedAmt, { color: colors.textSecondary }]}>{formatINRShort(sip.monthly_equivalent)}/mo</Text>
              </View>
              {goals.length > 0 && (
                <TouchableOpacity
                  data-testid={`link-sip-btn-${sip.id}`}
                  style={[s.linkBtn, { backgroundColor: isDark ? 'rgba(59,130,246,0.15)' : 'rgba(59,130,246,0.1)' }]}
                  onPress={() => setLinkModal({ visible: true, sipId: sip.id, sipName: sip.name })}
                >
                  <MaterialCommunityIcons name="link" size={13} color="#3B82F6" />
                  <Text style={s.linkBtnText}>Link</Text>
                </TouchableOpacity>
              )}
            </View>
          ))}
        </View>
      )}

      {/* Goal Selection Modal for Linking */}
      <Modal
        visible={linkModal?.visible || false}
        transparent
        animationType="slide"
        onRequestClose={() => setLinkModal(null)}
      >
        <View style={s.modalOverlay}>
          <View style={[s.modalBox, { backgroundColor: isDark ? '#1E293B' : '#FFFFFF' }]}>
            <View style={s.modalHeader}>
              <Text style={[s.modalTitle, { color: colors.textPrimary }]}>
                Link "{linkModal?.sipName}" to a Goal
              </Text>
              <TouchableOpacity onPress={() => setLinkModal(null)}>
                <MaterialCommunityIcons name="close" size={20} color={colors.textSecondary} />
              </TouchableOpacity>
            </View>

            {linking ? (
              <ActivityIndicator color="#3B82F6" style={{ padding: 24 }} />
            ) : (
              <FlatList
                data={goals}
                keyExtractor={(g) => g.goal_id}
                renderItem={({ item: g }) => {
                  const pct = g.target_amount > 0 ? Math.min(100, (g.current_amount / g.target_amount) * 100) : 0;
                  const statusColor = g.on_track ? '#10B981' : g.shortfall > g.sip_needed_monthly ? '#EF4444' : '#F59E0B';
                  return (
                    <TouchableOpacity
                      data-testid={`select-goal-${g.goal_id}`}
                      style={[s.goalOption, {
                        backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)',
                        borderColor: statusColor + '40',
                      }]}
                      onPress={() => handleLinkSip(g.goal_id)}
                    >
                      <JarProgressView
                        percentage={pct}
                        color={statusColor}
                        uid={`modal-${g.goal_id}`}
                        width={36}
                        showLabel={false}
                      />
                      <View style={{ flex: 1 }}>
                        <Text style={[s.goalOptionTitle, { color: colors.textPrimary }]}>{g.goal_title}</Text>
                        <Text style={[s.goalOptionSub, { color: colors.textSecondary }]}>
                          {formatINRShort(g.current_amount)} / {formatINRShort(g.target_amount)}
                        </Text>
                      </View>
                      <MaterialCommunityIcons name="chevron-right" size={18} color={colors.textSecondary} />
                    </TouchableOpacity>
                  );
                }}
              />
            )}
          </View>
        </View>
      </Modal>
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
  goalMain: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  goalTop: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 6 },
  goalTitle: { fontSize: 14, fontWeight: '600' },
  goalDeadline: { fontSize: 11, marginTop: 2 },
  goalTarget: { fontSize: 13, fontWeight: '700' },
  goalCurrent: { fontSize: 11, fontWeight: '500', textAlign: 'right' },
  sipStatus: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 2 },
  sipStatusText: { fontSize: 11, fontWeight: '600' },
  expandSection: { borderTopWidth: 1, marginTop: 10, paddingTop: 10 },
  expandRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  expLabel: { fontSize: 12 },
  expVal: { fontSize: 13, fontWeight: '600' },
  shortfallBox: { flexDirection: 'row', gap: 6, padding: 10, borderRadius: 8, marginTop: 6, alignItems: 'flex-start' },
  shortfallText: { flex: 1, fontSize: 12, color: '#EF4444', lineHeight: 16 },
  linkedSipRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 4 },
  linkedSip: { fontSize: 12, fontWeight: '500' },
  unlinkBtn: { flexDirection: 'row', alignItems: 'center', gap: 3, paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6, backgroundColor: 'rgba(239,68,68,0.1)' },
  unlinkText: { fontSize: 11, color: '#EF4444', fontWeight: '600' },
  subhead: { fontSize: 14, fontWeight: '700', marginBottom: 4 },
  unmappedCard: { flexDirection: 'row', alignItems: 'center', gap: 10, padding: 12, borderRadius: 10, borderWidth: 1, marginBottom: 6 },
  unmappedName: { fontSize: 13, fontWeight: '600' },
  unmappedAmt: { fontSize: 11, marginTop: 1 },
  linkBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8 },
  linkBtnText: { fontSize: 12, color: '#3B82F6', fontWeight: '700' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end' },
  modalBox: { borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 20, maxHeight: '70%' },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  modalTitle: { fontSize: 15, fontWeight: '700', flex: 1, marginRight: 8 },
  goalOption: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 12, borderRadius: 10, borderWidth: 1, marginBottom: 8 },
  goalOptionTitle: { fontSize: 13, fontWeight: '600' },
  goalOptionSub: { fontSize: 11, marginTop: 2 },
});
