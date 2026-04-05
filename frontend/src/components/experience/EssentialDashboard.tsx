// /app/frontend/src/components/experience/EssentialDashboard.tsx
/**
 * Essential Mode Dashboard
 * Simplified, AI-curated home screen for Essential mode users
 * Shows: AI Morning Brief, 3-card snapshot, Smart Alerts
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
  Dimensions,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { useExperienceMode } from '../../context/ExperienceModeContext';
import { apiRequest } from '../../utils/api';
import { formatINR, formatINRShort } from '../../utils/formatters';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

interface SnapshotData {
  spent_this_month: number;
  safe_to_spend: number;
  saved_this_month: number;
  income_this_month: number;
  budget_status: 'on_track' | 'over_budget' | 'under_budget';
  savings_rate: number;
}

interface Alert {
  id: string;
  type: 'warning' | 'info' | 'success' | 'action';
  title: string;
  message: string;
  action_label?: string;
  action_route?: string;
  priority: number;
}

interface MorningBrief {
  greeting: string;
  headline: string;
  highlights: string[];
  quick_stat: {
    label: string;
    value: string;
    trend?: 'up' | 'down' | 'neutral';
  };
  tip_of_day?: string;
  generated_at: string;
}

interface Props {
  insets: { top: number; bottom: number };
}

export function EssentialDashboard({ insets }: Props) {
  const { token, user } = useAuth();
  const { colors, isDark } = useTheme();
  const { setMode, trackBehavior } = useExperienceMode();
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [snapshot, setSnapshot] = useState<SnapshotData | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [morningBrief, setMorningBrief] = useState<MorningBrief | null>(null);
  const [briefLoading, setBriefLoading] = useState(true);

  const fetchData = useCallback(async () => {
    if (!token) return;
    
    try {
      const [snapshotRes, alertsRes] = await Promise.all([
        apiRequest('/experience/essential/snapshot', { token }),
        apiRequest('/experience/essential/alerts?limit=5', { token }),
      ]);
      
      // Map backend response to our expected format
      const mappedSnapshot: SnapshotData = {
        spent_this_month: snapshotRes.spent?.amount || 0,
        safe_to_spend: snapshotRes.safe_to_spend?.amount || 0,
        saved_this_month: snapshotRes.saved?.amount || 0,
        income_this_month: 0, // Not provided by this endpoint
        budget_status: snapshotRes.spent?.trend === 'up' ? 'over_budget' : snapshotRes.saved?.amount > 0 ? 'under_budget' : 'on_track',
        savings_rate: snapshotRes.saved?.progress_pct || 0,
      };
      
      // Map alerts to our expected format
      const mappedAlerts: Alert[] = (alertsRes.alerts || []).map((a: any, idx: number) => ({
        id: `alert-${idx}`,
        type: a.priority === 'high' ? 'warning' : a.type === 'info' ? 'info' : 'action',
        title: a.title,
        message: a.message,
        action_label: a.action?.label,
        action_route: a.action?.route,
        priority: a.priority === 'high' ? 1 : a.priority === 'medium' ? 2 : 3,
      }));
      
      setSnapshot(mappedSnapshot);
      setAlerts(mappedAlerts);
    } catch (e) {
      console.error('[EssentialDashboard] Error fetching data:', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token]);

  const fetchBrief = useCallback(async () => {
    if (!token) return;
    
    try {
      const briefRes = await apiRequest('/experience/essential/brief', { token });
      // Map backend response to our expected format
      const mappedBrief: MorningBrief = {
        greeting: briefRes.message || `Good ${getTimeOfDay()}, ${user?.full_name?.split(' ')[0] || 'there'}!`,
        headline: "Here's your financial snapshot",
        highlights: briefRes.alerts || [],
        quick_stat: { 
          label: 'Spent', 
          value: `₹${(briefRes.snapshot?.spent || 0).toLocaleString('en-IN')}`,
          trend: 'neutral' 
        },
        tip_of_day: briefRes.tip,
        generated_at: briefRes.generated_at || new Date().toISOString(),
      };
      setMorningBrief(mappedBrief);
    } catch (e) {
      console.error('[EssentialDashboard] Error fetching brief:', e);
      // Fallback brief
      setMorningBrief({
        greeting: `Good ${getTimeOfDay()}, ${user?.full_name?.split(' ')[0] || 'there'}!`,
        headline: "Here's your financial snapshot",
        highlights: [],
        quick_stat: { label: 'Ask Visor AI', value: 'for insights', trend: 'neutral' },
        generated_at: new Date().toISOString(),
      });
    } finally {
      setBriefLoading(false);
    }
  }, [token, user]);

  useEffect(() => {
    fetchData();
    fetchBrief();
  }, [fetchData, fetchBrief]);

  const onRefresh = () => {
    setRefreshing(true);
    setBriefLoading(true);
    fetchData();
    fetchBrief();
  };

  const getTimeOfDay = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'morning';
    if (hour < 17) return 'afternoon';
    return 'evening';
  };

  const handleAlertAction = (alert: Alert) => {
    if (alert.action_route) {
      router.push(alert.action_route as any);
    }
    trackBehavior('alert_action', { alert_id: alert.id, type: alert.type });
  };

  const navigateToAI = () => {
    trackBehavior('essential_ai_tap', {});
    router.push('/(tabs)/insights');
  };

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: colors.background, justifyContent: 'center', alignItems: 'center' }]}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={[styles.loadingText, { color: colors.textSecondary }]}>
          Preparing your financial snapshot...
        </Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: colors.background }]}
      contentContainerStyle={[styles.content, { paddingTop: insets.top + 16, paddingBottom: insets.bottom + 100 }]}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />
      }
      showsVerticalScrollIndicator={false}
    >
      {/* ═══ AI MORNING BRIEF ═══ */}
      <View style={[styles.briefCard, { backgroundColor: isDark ? '#0D1117' : '#F0FDF4', borderColor: isDark ? '#10B981' + '30' : '#10B981' + '20' }]}>
        {briefLoading ? (
          <View style={{ alignItems: 'center', padding: 20 }}>
            <ActivityIndicator size="small" color="#10B981" />
            <Text style={[styles.briefLoadingText, { color: colors.textSecondary }]}>
              Generating your personalized brief...
            </Text>
          </View>
        ) : morningBrief && (
          <>
            <View style={styles.briefHeader}>
              <View style={[styles.briefIcon, { backgroundColor: '#10B981' + '20' }]}>
                <MaterialCommunityIcons name="robot-happy" size={24} color="#10B981" />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={[styles.briefGreeting, { color: colors.textPrimary }]}>
                  {morningBrief.greeting}
                </Text>
                <Text style={[styles.briefHeadline, { color: colors.textSecondary }]}>
                  {morningBrief.headline}
                </Text>
              </View>
            </View>

            {morningBrief.highlights.length > 0 && (
              <View style={styles.highlightsList}>
                {morningBrief.highlights.slice(0, 3).map((highlight, idx) => (
                  <View key={idx} style={styles.highlightItem}>
                    <MaterialCommunityIcons name="circle-small" size={20} color="#10B981" />
                    <Text style={[styles.highlightText, { color: colors.textPrimary }]}>
                      {highlight}
                    </Text>
                  </View>
                ))}
              </View>
            )}

            {morningBrief.tip_of_day && (
              <View style={[styles.tipBox, { backgroundColor: isDark ? 'rgba(16,185,129,0.1)' : 'rgba(16,185,129,0.08)' }]}>
                <MaterialCommunityIcons name="lightbulb-on-outline" size={16} color="#10B981" />
                <Text style={[styles.tipText, { color: colors.textSecondary }]}>
                  {morningBrief.tip_of_day}
                </Text>
              </View>
            )}

            <TouchableOpacity 
              style={styles.askAIButton}
              onPress={navigateToAI}
              data-testid="essential-ask-ai-btn"
            >
              <MaterialCommunityIcons name="chat-processing" size={18} color="#fff" />
              <Text style={styles.askAIText}>Ask Visor AI anything</Text>
              <MaterialCommunityIcons name="arrow-right" size={16} color="#fff" />
            </TouchableOpacity>
          </>
        )}
      </View>

      {/* ═══ 3-CARD SNAPSHOT ═══ */}
      <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>This Month</Text>
      
      <View style={styles.snapshotGrid}>
        {/* Spent Card */}
        <View style={[styles.snapshotCard, { backgroundColor: isDark ? '#1A0A0A' : '#FEF2F2', borderColor: '#EF4444' + '30' }]}>
          <View style={[styles.snapshotIcon, { backgroundColor: '#EF4444' + '20' }]}>
            <MaterialCommunityIcons name="cash-minus" size={22} color="#EF4444" />
          </View>
          <Text style={[styles.snapshotLabel, { color: colors.textSecondary }]}>Spent</Text>
          <Text style={[styles.snapshotValue, { color: '#EF4444' }]}>
            {formatINRShort(snapshot?.spent_this_month || 0)}
          </Text>
        </View>

        {/* Safe to Spend Card */}
        <View style={[styles.snapshotCard, { backgroundColor: isDark ? '#0A1A0A' : '#F0FDF4', borderColor: '#10B981' + '30' }]}>
          <View style={[styles.snapshotIcon, { backgroundColor: '#10B981' + '20' }]}>
            <MaterialCommunityIcons name="shield-check" size={22} color="#10B981" />
          </View>
          <Text style={[styles.snapshotLabel, { color: colors.textSecondary }]}>Safe to Spend</Text>
          <Text style={[styles.snapshotValue, { color: '#10B981' }]}>
            {formatINRShort(snapshot?.safe_to_spend || 0)}
          </Text>
        </View>

        {/* Saved Card */}
        <View style={[styles.snapshotCard, { backgroundColor: isDark ? '#0A0A1A' : '#EFF6FF', borderColor: '#3B82F6' + '30' }]}>
          <View style={[styles.snapshotIcon, { backgroundColor: '#3B82F6' + '20' }]}>
            <MaterialCommunityIcons name="piggy-bank" size={22} color="#3B82F6" />
          </View>
          <Text style={[styles.snapshotLabel, { color: colors.textSecondary }]}>Saved</Text>
          <Text style={[styles.snapshotValue, { color: '#3B82F6' }]}>
            {formatINRShort(snapshot?.saved_this_month || 0)}
          </Text>
          {snapshot && snapshot.savings_rate > 0 && (
            <Text style={[styles.snapshotSubtext, { color: colors.textSecondary }]}>
              {snapshot.savings_rate.toFixed(0)}% of income
            </Text>
          )}
        </View>
      </View>

      {/* Budget Status */}
      {snapshot && (
        <View style={[styles.budgetStatus, {
          backgroundColor: snapshot.budget_status === 'on_track' 
            ? (isDark ? 'rgba(16,185,129,0.1)' : 'rgba(16,185,129,0.06)')
            : snapshot.budget_status === 'over_budget'
            ? (isDark ? 'rgba(239,68,68,0.1)' : 'rgba(239,68,68,0.06)')
            : (isDark ? 'rgba(245,158,11,0.1)' : 'rgba(245,158,11,0.06)'),
          borderColor: snapshot.budget_status === 'on_track' ? '#10B981' + '30' : snapshot.budget_status === 'over_budget' ? '#EF4444' + '30' : '#F59E0B' + '30',
        }]}>
          <MaterialCommunityIcons 
            name={snapshot.budget_status === 'on_track' ? 'check-circle' : snapshot.budget_status === 'over_budget' ? 'alert-circle' : 'information'}
            size={20}
            color={snapshot.budget_status === 'on_track' ? '#10B981' : snapshot.budget_status === 'over_budget' ? '#EF4444' : '#F59E0B'}
          />
          <Text style={[styles.budgetStatusText, {
            color: snapshot.budget_status === 'on_track' ? '#10B981' : snapshot.budget_status === 'over_budget' ? '#EF4444' : '#F59E0B'
          }]}>
            {snapshot.budget_status === 'on_track' 
              ? "You're on track this month!" 
              : snapshot.budget_status === 'over_budget'
              ? "Spending is higher than usual"
              : "Great job saving!"}
          </Text>
        </View>
      )}

      {/* ═══ SMART ALERTS ═══ */}
      {alerts.length > 0 && (
        <>
          <Text style={[styles.sectionTitle, { color: colors.textPrimary, marginTop: 24 }]}>Smart Alerts</Text>
          
          <View style={styles.alertsList}>
            {alerts.map((alert) => (
              <TouchableOpacity 
                key={alert.id}
                style={[styles.alertCard, {
                  backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
                  borderColor: alert.type === 'warning' ? '#F59E0B' + '40' : alert.type === 'action' ? '#6366F1' + '40' : colors.border + '40',
                }]}
                onPress={() => handleAlertAction(alert)}
                disabled={!alert.action_route}
              >
                <View style={[styles.alertIcon, {
                  backgroundColor: alert.type === 'warning' ? '#F59E0B' + '20' : alert.type === 'success' ? '#10B981' + '20' : alert.type === 'action' ? '#6366F1' + '20' : colors.primary + '20',
                }]}>
                  <MaterialCommunityIcons 
                    name={alert.type === 'warning' ? 'alert' : alert.type === 'success' ? 'check-circle' : alert.type === 'action' ? 'lightning-bolt' : 'information'}
                    size={20}
                    color={alert.type === 'warning' ? '#F59E0B' : alert.type === 'success' ? '#10B981' : alert.type === 'action' ? '#6366F1' : colors.primary}
                  />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={[styles.alertTitle, { color: colors.textPrimary }]}>{alert.title}</Text>
                  <Text style={[styles.alertMessage, { color: colors.textSecondary }]}>{alert.message}</Text>
                </View>
                {alert.action_route && (
                  <MaterialCommunityIcons name="chevron-right" size={20} color={colors.textSecondary} />
                )}
              </TouchableOpacity>
            ))}
          </View>
        </>
      )}

      {/* ═══ WANT MORE? UPGRADE CTA ═══ */}
      <View style={[styles.upgradeCta, { backgroundColor: isDark ? 'rgba(99,102,241,0.1)' : 'rgba(99,102,241,0.06)', borderColor: '#6366F1' + '30' }]}>
        <View style={styles.upgradeContent}>
          <MaterialCommunityIcons name="chart-line" size={24} color="#6366F1" />
          <View style={{ flex: 1, marginLeft: 12 }}>
            <Text style={[styles.upgradeTitle, { color: colors.textPrimary }]}>Want more details?</Text>
            <Text style={[styles.upgradeText, { color: colors.textSecondary }]}>
              Upgrade to Plus for full transaction history, holdings breakdown, and health score.
            </Text>
          </View>
        </View>
        <TouchableOpacity 
          style={styles.upgradeButton}
          onPress={() => setMode('plus', 'essential_dashboard_cta')}
          data-testid="essential-upgrade-btn"
        >
          <Text style={styles.upgradeButtonText}>Explore Plus</Text>
          <MaterialCommunityIcons name="arrow-right" size={16} color="#fff" />
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    paddingHorizontal: 16,
  },
  loadingText: {
    marginTop: 12,
    fontSize: 14,
    fontFamily: 'DM Sans',
  },

  // Brief Card
  briefCard: {
    borderRadius: 20,
    padding: 20,
    borderWidth: 1,
    marginBottom: 24,
  },
  briefHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    marginBottom: 16,
  },
  briefIcon: {
    width: 44,
    height: 44,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  briefGreeting: {
    fontSize: 18,
    fontWeight: '700',
    fontFamily: 'DM Sans',
    marginBottom: 2,
  },
  briefHeadline: {
    fontSize: 14,
    fontFamily: 'DM Sans',
  },
  briefLoadingText: {
    marginTop: 8,
    fontSize: 13,
    fontFamily: 'DM Sans',
  },
  highlightsList: {
    marginBottom: 16,
  },
  highlightItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 6,
  },
  highlightText: {
    flex: 1,
    fontSize: 14,
    fontFamily: 'DM Sans',
    lineHeight: 20,
  },
  tipBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    padding: 12,
    borderRadius: 12,
    marginBottom: 16,
  },
  tipText: {
    flex: 1,
    fontSize: 13,
    fontFamily: 'DM Sans',
    lineHeight: 18,
  },
  askAIButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#10B981',
    paddingVertical: 14,
    borderRadius: 14,
  },
  askAIText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '700',
    fontFamily: 'DM Sans',
  },

  // Section Title
  sectionTitle: {
    fontSize: 16,
    fontWeight: '800',
    fontFamily: 'DM Sans',
    marginBottom: 12,
    letterSpacing: -0.3,
  },

  // Snapshot Grid
  snapshotGrid: {
    flexDirection: 'row',
    gap: 10,
  },
  snapshotCard: {
    flex: 1,
    borderRadius: 16,
    padding: 14,
    borderWidth: 1,
    alignItems: 'center',
  },
  snapshotIcon: {
    width: 40,
    height: 40,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 10,
  },
  snapshotLabel: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 4,
  },
  snapshotValue: {
    fontSize: 18,
    fontWeight: '800',
    fontFamily: 'DM Sans',
  },
  snapshotSubtext: {
    fontSize: 10,
    fontFamily: 'DM Sans',
    marginTop: 2,
  },

  // Budget Status
  budgetStatus: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    padding: 14,
    borderRadius: 12,
    borderWidth: 1,
    marginTop: 12,
  },
  budgetStatusText: {
    flex: 1,
    fontSize: 14,
    fontWeight: '600',
    fontFamily: 'DM Sans',
  },

  // Alerts
  alertsList: {
    gap: 10,
  },
  alertCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 14,
    borderRadius: 14,
    borderWidth: 1,
  },
  alertIcon: {
    width: 40,
    height: 40,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  alertTitle: {
    fontSize: 14,
    fontWeight: '700',
    fontFamily: 'DM Sans',
    marginBottom: 2,
  },
  alertMessage: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    lineHeight: 18,
  },

  // Upgrade CTA
  upgradeCta: {
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    marginTop: 24,
  },
  upgradeContent: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 14,
  },
  upgradeTitle: {
    fontSize: 15,
    fontWeight: '700',
    fontFamily: 'DM Sans',
    marginBottom: 4,
  },
  upgradeText: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    lineHeight: 18,
  },
  upgradeButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    backgroundColor: '#6366F1',
    paddingVertical: 12,
    borderRadius: 12,
  },
  upgradeButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '700',
    fontFamily: 'DM Sans',
  },
});

export default EssentialDashboard;
