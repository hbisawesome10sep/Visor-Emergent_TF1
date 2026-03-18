import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, ScrollView } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { apiRequest } from '../../utils/api';
import { Accent } from '../../utils/theme';

type Due = {
  id: string;
  name: string;
  type: 'credit_card' | 'loan';
  amount: number;
  due_date: string;
  days_until: number;
  urgency: string;
  icon: string;
};

type Props = { token: string; isDark: boolean; colors: any };

const fmtINR = (n: number) => {
  if (Math.abs(n) >= 100000) return `${(n / 100000).toFixed(1)}L`;
  if (Math.abs(n) >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return `${n.toFixed(0)}`;
};

const getUrgencyColor = (urgency: string) => {
  switch (urgency) {
    case 'critical': return '#EF4444';
    case 'warning': return '#F59E0B';
    case 'upcoming': return '#3B82F6';
    default: return '#6B7280';
  }
};

export const UpcomingDuesCard = ({ token, isDark, colors }: Props) => {
  const [dues, setDues] = useState<Due[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const res = await apiRequest('/dashboard/upcoming-dues', { token });
      setDues(res.dues || []);
    } catch (e) {
      console.warn('Dues fetch error:', e);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) {
    return (
      <View style={[s.card, { backgroundColor: isDark ? 'rgba(10,10,11,0.9)' : 'rgba(255,255,255,0.95)', borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
        <ActivityIndicator size="small" color={colors.primary} style={{ padding: 24 }} />
      </View>
    );
  }

  if (dues.length === 0) return null; // Don't show if no dues

  return (
    <View testID="upcoming-dues-card" style={[s.card, { backgroundColor: isDark ? 'rgba(10,10,11,0.9)' : 'rgba(255,255,255,0.95)', borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
      <View style={s.headerRow}>
        <View style={[s.iconBg, { backgroundColor: isDark ? 'rgba(239,68,68,0.15)' : 'rgba(239,68,68,0.08)' }]}>
          <MaterialCommunityIcons name="calendar-clock" size={18} color="#EF4444" />
        </View>
        <Text style={[s.title, { color: colors.textPrimary }]}>Upcoming Dues</Text>
        <View style={[s.countBadge, { backgroundColor: isDark ? 'rgba(239,68,68,0.15)' : 'rgba(239,68,68,0.08)' }]}>
          <Text style={[s.countText, { color: '#EF4444' }]}>{dues.length}</Text>
        </View>
      </View>

      {dues.slice(0, 5).map((due, idx) => {
        const urgColor = getUrgencyColor(due.urgency);
        const dueDate = new Date(due.due_date);
        const dateStr = dueDate.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });

        return (
          <View key={`${due.id}-${idx}`} style={[s.dueRow, idx < Math.min(dues.length, 5) - 1 && { borderBottomWidth: 0.5, borderBottomColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)' }]}>
            <View style={[s.dueIcon, { backgroundColor: isDark ? `${urgColor}20` : `${urgColor}10` }]}>
              <MaterialCommunityIcons name={due.type === 'credit_card' ? 'credit-card' : 'bank'} size={16} color={urgColor} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={[s.dueName, { color: colors.textPrimary }]} numberOfLines={1}>{due.name}</Text>
              <Text style={[s.dueDate, { color: colors.textSecondary }]}>{dateStr}</Text>
            </View>
            <View style={{ alignItems: 'flex-end' }}>
              <Text style={[s.dueAmount, { color: colors.textPrimary }]}>Rs {fmtINR(due.amount)}</Text>
              <View style={[s.daysBadge, { backgroundColor: `${urgColor}18` }]}>
                <Text style={[s.daysText, { color: urgColor }]}>
                  {due.days_until === 0 ? 'Today' : due.days_until === 1 ? 'Tomorrow' : `${due.days_until}d`}
                </Text>
              </View>
            </View>
          </View>
        );
      })}
    </View>
  );
};

const s = StyleSheet.create({
  card: { borderRadius: 18, borderWidth: 1, padding: 16, marginBottom: 16, overflow: 'hidden' },
  headerRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 12 },
  iconBg: { width: 32, height: 32, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 15, fontWeight: '700', flex: 1 },
  countBadge: { width: 24, height: 24, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  countText: { fontSize: 12, fontWeight: '700' },
  dueRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, gap: 10 },
  dueIcon: { width: 36, height: 36, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  dueName: { fontSize: 13, fontWeight: '600' },
  dueDate: { fontSize: 11, marginTop: 2 },
  dueAmount: { fontSize: 14, fontWeight: '700' },
  daysBadge: { paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6, marginTop: 2 },
  daysText: { fontSize: 10, fontWeight: '700' },
});
