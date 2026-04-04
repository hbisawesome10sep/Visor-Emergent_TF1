import React, { useEffect, useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, ScrollView } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { apiRequest } from '../../utils/api';
import { Accent } from '../../utils/theme';

interface TaxCalendarCardProps {
  token: string;
  colors: any;
  isDark: boolean;
}

interface CalendarEvent {
  date: string;
  month: string;
  day: number;
  event: string;
  action: string;
  is_applicable: boolean;
  status: string;
  days_until: number;
}

export const TaxCalendarCard: React.FC<TaxCalendarCardProps> = ({ token, colors, isDark }) => {
  const [data, setData] = useState<{
    events: CalendarEvent[];
    urgent_count: number;
    upcoming_count: number;
    next_deadline: CalendarEvent | null;
    income_types: string[];
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const result = await apiRequest('/tax/calendar?fy=2025-26', { token });
        setData(result);
      } catch (e) {
        console.error('Tax calendar fetch error:', e);
      } finally {
        setLoading(false);
      }
    };
    if (token) fetchData();
  }, [token]);

  if (loading) {
    return (
      <View style={[styles.card, { backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.9)', borderColor: isDark ? 'rgba(59,130,246,0.15)' : 'rgba(59,130,246,0.1)' }]}>
        <ActivityIndicator size="small" color="#3B82F6" />
      </View>
    );
  }

  if (!data) return null;

  const upcomingEvents = data.events.filter(e => e.status === 'upcoming' || e.status === 'urgent');
  const applicableEvents = data.events.filter(e => e.is_applicable);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'urgent': return '#EF4444';
      case 'upcoming': return '#F59E0B';
      case 'future': return '#3B82F6';
      case 'completed': return Accent.emerald;
      default: return colors.textSecondary;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'urgent': return 'alert-circle';
      case 'upcoming': return 'clock-outline';
      case 'future': return 'calendar-outline';
      case 'completed': return 'check-circle';
      default: return 'calendar-check';
    }
  };

  return (
    <View style={{ marginBottom: 16 }}>
      <TouchableOpacity
        data-testid="tax-calendar-header"
        style={[styles.card, {
          backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.9)',
          borderColor: isDark ? 'rgba(59,130,246,0.15)' : 'rgba(59,130,246,0.1)',
        }]}
        onPress={() => setExpanded(!expanded)}
        activeOpacity={0.7}
      >
        <View style={styles.header}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
            <View style={[styles.iconWrap, { backgroundColor: 'rgba(59,130,246,0.12)' }]}>
              <MaterialCommunityIcons name="calendar-clock" size={18} color="#3B82F6" />
            </View>
            <View>
              <Text style={[styles.title, { color: colors.textPrimary }]}>Tax Calendar</Text>
              <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
                FY 2025-26 Important Dates
              </Text>
            </View>
          </View>
          {data.urgent_count > 0 && (
            <View style={[styles.urgentBadge, { backgroundColor: 'rgba(239,68,68,0.1)' }]}>
              <MaterialCommunityIcons name="alert" size={12} color="#EF4444" />
              <Text style={[styles.urgentText, { color: '#EF4444' }]}>
                {data.urgent_count} urgent
              </Text>
            </View>
          )}
        </View>

        {/* Next Deadline Preview */}
        {data.next_deadline && !expanded && (
          <View style={[styles.nextDeadline, { backgroundColor: `${getStatusColor(data.next_deadline.status)}10` }]}>
            <View style={styles.deadlineDateBox}>
              <Text style={[styles.deadlineMonth, { color: getStatusColor(data.next_deadline.status) }]}>
                {data.next_deadline.month.substring(0, 3)}
              </Text>
              <Text style={[styles.deadlineDay, { color: getStatusColor(data.next_deadline.status) }]}>
                {data.next_deadline.day}
              </Text>
            </View>
            <View style={{ flex: 1 }}>
              <Text style={[styles.deadlineEvent, { color: colors.textPrimary }]} numberOfLines={1}>
                {data.next_deadline.event}
              </Text>
              <Text style={[styles.deadlineDays, { color: getStatusColor(data.next_deadline.status) }]}>
                {data.next_deadline.days_until > 0 
                  ? `${data.next_deadline.days_until} days remaining`
                  : 'Today!'
                }
              </Text>
            </View>
          </View>
        )}

        <MaterialCommunityIcons 
          name={expanded ? 'chevron-up' : 'chevron-down'} 
          size={20} 
          color={colors.textSecondary}
          style={{ position: 'absolute', right: 14, top: 14 }}
        />
      </TouchableOpacity>

      {/* Expanded Calendar */}
      {expanded && (
        <View style={[styles.expandedSection, {
          backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.9)',
          borderColor: isDark ? 'rgba(59,130,246,0.1)' : 'rgba(59,130,246,0.06)',
        }]}>
          {/* Applicable Events Only Toggle Info */}
          <Text style={[styles.filterNote, { color: colors.textSecondary }]}>
            Showing events for: {data.income_types.join(', ')}
          </Text>

          {/* Timeline */}
          {applicableEvents.map((event, idx) => (
            <View key={idx} style={styles.eventRow}>
              {/* Date Column */}
              <View style={styles.dateColumn}>
                <Text style={[styles.eventMonth, { color: colors.textSecondary }]}>
                  {event.month.substring(0, 3)}
                </Text>
                <Text style={[styles.eventDay, { color: colors.textPrimary }]}>
                  {event.day}
                </Text>
              </View>

              {/* Timeline Indicator */}
              <View style={styles.timeline}>
                <View style={[styles.timelineDot, { backgroundColor: getStatusColor(event.status) }]}>
                  <MaterialCommunityIcons 
                    name={getStatusIcon(event.status) as any} 
                    size={10} 
                    color="#fff" 
                  />
                </View>
                {idx < applicableEvents.length - 1 && (
                  <View style={[styles.timelineLine, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)' }]} />
                )}
              </View>

              {/* Event Details */}
              <View style={[styles.eventContent, { 
                backgroundColor: event.status === 'urgent' 
                  ? 'rgba(239,68,68,0.06)' 
                  : event.status === 'upcoming'
                    ? 'rgba(245,158,11,0.06)'
                    : isDark ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.02)',
                borderColor: `${getStatusColor(event.status)}20`,
              }]}>
                <View style={styles.eventHeader}>
                  <Text style={[styles.eventTitle, { color: colors.textPrimary }]} numberOfLines={1}>
                    {event.event}
                  </Text>
                  {event.status !== 'past' && (
                    <View style={[styles.statusPill, { backgroundColor: `${getStatusColor(event.status)}15` }]}>
                      <Text style={[styles.statusPillText, { color: getStatusColor(event.status) }]}>
                        {event.status === 'urgent' ? 'Urgent' 
                          : event.status === 'upcoming' ? `${event.days_until}d`
                          : event.status === 'completed' ? 'Done'
                          : event.days_until + 'd'}
                      </Text>
                    </View>
                  )}
                </View>
                <Text style={[styles.eventAction, { color: colors.textSecondary }]} numberOfLines={2}>
                  {event.action}
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
  urgentBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  urgentText: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    fontWeight: '600',
  },
  nextDeadline: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 10,
    borderRadius: 10,
  },
  deadlineDateBox: {
    alignItems: 'center',
    minWidth: 40,
  },
  deadlineMonth: {
    fontSize: 10,
    fontFamily: 'DM Sans',
    fontWeight: '600',
    textTransform: 'uppercase',
  },
  deadlineDay: {
    fontSize: 18,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  deadlineEvent: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    fontWeight: '600',
  },
  deadlineDays: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    fontWeight: '500',
    marginTop: 2,
  },
  expandedSection: {
    marginTop: 8,
    padding: 14,
    borderRadius: 14,
    borderWidth: 1,
  },
  filterNote: {
    fontSize: 10,
    fontFamily: 'DM Sans',
    fontStyle: 'italic',
    marginBottom: 12,
    textAlign: 'center',
  },
  eventRow: {
    flexDirection: 'row',
    marginBottom: 0,
  },
  dateColumn: {
    width: 36,
    alignItems: 'center',
    paddingTop: 4,
  },
  eventMonth: {
    fontSize: 9,
    fontFamily: 'DM Sans',
    fontWeight: '500',
    textTransform: 'uppercase',
  },
  eventDay: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  timeline: {
    width: 24,
    alignItems: 'center',
    paddingTop: 4,
  },
  timelineDot: {
    width: 18,
    height: 18,
    borderRadius: 9,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1,
  },
  timelineLine: {
    width: 2,
    flex: 1,
    marginTop: -2,
    minHeight: 40,
  },
  eventContent: {
    flex: 1,
    padding: 10,
    borderRadius: 10,
    borderWidth: 1,
    marginBottom: 8,
    marginLeft: 8,
  },
  eventHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  eventTitle: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    fontWeight: '600',
    flex: 1,
    marginRight: 8,
  },
  statusPill: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  statusPillText: {
    fontSize: 9,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  eventAction: {
    fontSize: 11,
    fontFamily: 'DM Sans',
  },
});
