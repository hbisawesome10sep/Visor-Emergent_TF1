import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, TouchableOpacity } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { apiRequest } from '../../utils/api';

type DueItem = {
  card_id: string;
  card_name: string;
  last_four: string;
  next_due_date: string;
  days_until_due: number;
  outstanding: number;
  minimum_due: number;
  reminders: { type: string; message: string }[];
  urgency: string;
};

type Props = { token: string; isDark: boolean; colors: any };

const fmtINR = (n: number) => n >= 100000 ? `${(n / 100000).toFixed(1)}L` : n >= 1000 ? `${(n / 1000).toFixed(1)}K` : n.toFixed(0);

const urgencyColors: Record<string, string> = {
  critical: '#EF4444', warning: '#F59E0B', upcoming: '#3B82F6', normal: '#6B7280',
};

export const DueCalendarSection = ({ token, isDark, colors }: Props) => {
  const [calendar, setCalendar] = useState<DueItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetch = useCallback(async () => {
    try {
      const res = await apiRequest('/credit-cards/due-calendar', { token });
      setCalendar(res.calendar || []);
    } catch (e) { console.warn(e); }
    finally { setLoading(false); }
  }, [token]);

  useEffect(() => { fetch(); }, [fetch]);

  if (loading) return <ActivityIndicator style={{ padding: 40 }} color={colors.primary} />;

  return (
    <View testID="cc-due-calendar">
      {/* Timeline header */}
      <View style={[s.header, { backgroundColor: isDark ? 'rgba(239,68,68,0.08)' : 'rgba(239,68,68,0.04)' }]}>
        <MaterialCommunityIcons name="calendar-alert" size={20} color="#EF4444" />
        <Text style={[s.headerText, { color: colors.textPrimary }]}>Payment Due Dates</Text>
      </View>

      {calendar.length === 0 ? (
        <View style={s.empty}>
          <MaterialCommunityIcons name="check-circle-outline" size={36} color="#10B981" />
          <Text style={[s.emptyText, { color: colors.textSecondary }]}>No upcoming dues</Text>
        </View>
      ) : (
        calendar.map((item, idx) => {
          const uc = urgencyColors[item.urgency] || '#6B7280';
          const dueDate = new Date(item.next_due_date);
          const dateStr = dueDate.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });

          return (
            <View key={`${item.card_id}-${idx}`} style={[s.card, { backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : '#fff', borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)', borderLeftColor: uc }]}>
              <View style={s.cardTop}>
                <View style={[s.urgencyDot, { backgroundColor: uc }]} />
                <View style={{ flex: 1 }}>
                  <Text style={[s.cardName, { color: colors.textPrimary }]}>{item.card_name}</Text>
                  <Text style={[s.cardSub, { color: colors.textSecondary }]}>**** {item.last_four}</Text>
                </View>
                <View style={[s.daysBadge, { backgroundColor: `${uc}18` }]}>
                  <Text style={[s.daysText, { color: uc }]}>
                    {item.days_until_due === 0 ? 'TODAY' : item.days_until_due === 1 ? 'TOMORROW' : `${item.days_until_due} DAYS`}
                  </Text>
                </View>
              </View>

              <View style={s.cardDetails}>
                <View style={s.detailCol}>
                  <Text style={[s.detailLabel, { color: colors.textSecondary }]}>Due Date</Text>
                  <Text style={[s.detailVal, { color: colors.textPrimary }]}>{dateStr}</Text>
                </View>
                <View style={s.detailCol}>
                  <Text style={[s.detailLabel, { color: colors.textSecondary }]}>Outstanding</Text>
                  <Text style={[s.detailVal, { color: '#EF4444' }]}>Rs {fmtINR(item.outstanding)}</Text>
                </View>
                <View style={s.detailCol}>
                  <Text style={[s.detailLabel, { color: colors.textSecondary }]}>Min Due</Text>
                  <Text style={[s.detailVal, { color: '#F59E0B' }]}>Rs {fmtINR(item.minimum_due)}</Text>
                </View>
              </View>

              {item.reminders.length > 0 && (
                <View style={[s.reminderBox, { backgroundColor: `${uc}0A` }]}>
                  <MaterialCommunityIcons name="bell-ring-outline" size={14} color={uc} />
                  <Text style={[s.reminderText, { color: uc }]}>{item.reminders[0].message}</Text>
                </View>
              )}
            </View>
          );
        })
      )}
    </View>
  );
};

const s = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', gap: 8, padding: 14, borderRadius: 14, marginBottom: 12 },
  headerText: { fontSize: 16, fontWeight: '700' },
  empty: { alignItems: 'center', paddingVertical: 30, gap: 8 },
  emptyText: { fontSize: 14 },
  card: { borderRadius: 14, borderWidth: 1, borderLeftWidth: 4, padding: 14, marginBottom: 10 },
  cardTop: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 12 },
  urgencyDot: { width: 10, height: 10, borderRadius: 5 },
  cardName: { fontSize: 15, fontWeight: '700' },
  cardSub: { fontSize: 12, marginTop: 1 },
  daysBadge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8 },
  daysText: { fontSize: 11, fontWeight: '800' },
  cardDetails: { flexDirection: 'row', gap: 8, marginBottom: 10 },
  detailCol: { flex: 1 },
  detailLabel: { fontSize: 10, fontWeight: '500', marginBottom: 2 },
  detailVal: { fontSize: 14, fontWeight: '700' },
  reminderBox: { flexDirection: 'row', alignItems: 'center', gap: 8, padding: 10, borderRadius: 10 },
  reminderText: { fontSize: 12, fontWeight: '600', flex: 1 },
});
