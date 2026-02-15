import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, StyleSheet, RefreshControl, ActivityIndicator,
  TouchableOpacity, Dimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useAuth } from '../../src/context/AuthContext';
import { useTheme } from '../../src/context/ThemeContext';
import { apiRequest } from '../../src/utils/api';
import { formatINR, formatINRShort, getGreeting, getCategoryColor } from '../../src/utils/formatters';

type DashboardStats = {
  total_income: number;
  total_expenses: number;
  total_investments: number;
  net_balance: number;
  category_breakdown: Record<string, number>;
  recent_transactions: any[];
  monthly_income: number;
  monthly_expenses: number;
  monthly_investments: number;
  goal_count: number;
  goal_progress: number;
  transaction_count: number;
};

type HealthScore = {
  overall_score: number;
  grade: string;
  savings_rate: number;
  investment_rate: number;
  expense_ratio: number;
};

export default function DashboardScreen() {
  const { user, token } = useAuth();
  const { colors, isDark } = useTheme();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [health, setHealth] = useState<HealthScore | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = useCallback(async () => {
    if (!token) return;
    try {
      const [s, h] = await Promise.all([
        apiRequest('/dashboard/stats', { token }),
        apiRequest('/health-score', { token }),
      ]);
      setStats(s);
      setHealth(h);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const onRefresh = () => { setRefreshing(true); fetchData(); };

  if (loading) {
    return (
      <SafeAreaView style={[styles.safe, { backgroundColor: colors.background }]}>
        <View style={styles.center}><ActivityIndicator size="large" color={colors.primary} /></View>
      </SafeAreaView>
    );
  }

  const scoreColor = health && health.overall_score >= 70 ? colors.success
    : health && health.overall_score >= 45 ? colors.warning : colors.error;

  const categoryEntries = stats ? Object.entries(stats.category_breakdown).sort((a, b) => b[1] - a[1]).slice(0, 6) : [];
  const maxCatAmount = categoryEntries.length > 0 ? categoryEntries[0][1] : 1;

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: colors.background }]}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />}
      >
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={[styles.greeting, { color: colors.textSecondary }]}>{getGreeting()}</Text>
            <Text style={[styles.userName, { color: colors.textPrimary }]}>
              {user?.full_name?.split(' ')[0] || 'User'}
            </Text>
          </View>
          <View style={[styles.avatarCircle, { backgroundColor: colors.primary }]}>
            <Text style={styles.avatarText}>
              {user?.full_name?.charAt(0)?.toUpperCase() || 'V'}
            </Text>
          </View>
        </View>

        {/* Net Balance Card */}
        <View style={[styles.balanceCard, { backgroundColor: colors.primary }]}>
          <Text style={styles.balanceLabel}>Net Balance</Text>
          <Text testID="net-balance" style={styles.balanceAmount}>
            {formatINR(stats?.net_balance || 0)}
          </Text>
          <View style={styles.balanceRow}>
            <View style={styles.balanceStat}>
              <MaterialCommunityIcons name="arrow-down-circle" size={18} color="#34D399" />
              <Text style={styles.balanceStatText}>{formatINRShort(stats?.monthly_income || 0)}</Text>
              <Text style={styles.balanceStatLabel}>Income</Text>
            </View>
            <View style={[styles.balanceDivider, { backgroundColor: 'rgba(255,255,255,0.3)' }]} />
            <View style={styles.balanceStat}>
              <MaterialCommunityIcons name="arrow-up-circle" size={18} color="#FCA5A5" />
              <Text style={styles.balanceStatText}>{formatINRShort(stats?.monthly_expenses || 0)}</Text>
              <Text style={styles.balanceStatLabel}>Expenses</Text>
            </View>
            <View style={[styles.balanceDivider, { backgroundColor: 'rgba(255,255,255,0.3)' }]} />
            <View style={styles.balanceStat}>
              <MaterialCommunityIcons name="chart-line" size={18} color="#A5B4FC" />
              <Text style={styles.balanceStatText}>{formatINRShort(stats?.monthly_investments || 0)}</Text>
              <Text style={styles.balanceStatLabel}>Invested</Text>
            </View>
          </View>
        </View>

        {/* Quick Stats */}
        <View style={styles.statsRow}>
          <View style={[styles.statCard, { backgroundColor: colors.surface, borderColor: colors.border }]}>
            <View style={[styles.statIcon, { backgroundColor: isDark ? '#064E3B' : '#D1FAE5' }]}>
              <MaterialCommunityIcons name="cash-multiple" size={22} color={colors.income} />
            </View>
            <Text style={[styles.statAmount, { color: colors.income }]}>{formatINRShort(stats?.total_income || 0)}</Text>
            <Text style={[styles.statLabel, { color: colors.textSecondary }]}>Total Income</Text>
          </View>
          <View style={[styles.statCard, { backgroundColor: colors.surface, borderColor: colors.border }]}>
            <View style={[styles.statIcon, { backgroundColor: isDark ? '#7F1D1D' : '#FEE2E2' }]}>
              <MaterialCommunityIcons name="cart" size={22} color={colors.expense} />
            </View>
            <Text style={[styles.statAmount, { color: colors.expense }]}>{formatINRShort(stats?.total_expenses || 0)}</Text>
            <Text style={[styles.statLabel, { color: colors.textSecondary }]}>Total Expenses</Text>
          </View>
        </View>

        {/* Financial Health Score */}
        {health && (
          <View style={[styles.healthCard, { backgroundColor: colors.surface, borderColor: colors.border }]}>
            <View style={styles.healthHeader}>
              <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Financial Health</Text>
              <Text style={[styles.healthGrade, { color: scoreColor }]}>{health.grade}</Text>
            </View>
            <View style={styles.healthContent}>
              <View style={[styles.scoreCircle, { borderColor: scoreColor }]}>
                <Text style={[styles.scoreNum, { color: scoreColor }]}>{Math.round(health.overall_score)}</Text>
                <Text style={[styles.scoreMax, { color: colors.textSecondary }]}>/100</Text>
              </View>
              <View style={styles.healthMetrics}>
                <HealthMetric label="Savings Rate" value={`${health.savings_rate}%`} colors={colors} />
                <HealthMetric label="Investment Rate" value={`${health.investment_rate}%`} colors={colors} />
                <HealthMetric label="Expense Ratio" value={`${health.expense_ratio}%`} colors={colors} />
              </View>
            </View>
          </View>
        )}

        {/* Expense Breakdown */}
        {categoryEntries.length > 0 && (
          <View style={[styles.breakdownCard, { backgroundColor: colors.surface, borderColor: colors.border }]}>
            <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Expense Breakdown</Text>
            {categoryEntries.map(([cat, amount]) => (
              <View key={cat} style={styles.barRow}>
                <Text style={[styles.barLabel, { color: colors.textPrimary }]}>{cat}</Text>
                <View style={styles.barContainer}>
                  <View style={[styles.barBg, { backgroundColor: colors.border }]}>
                    <View
                      style={[styles.barFill, {
                        backgroundColor: getCategoryColor(cat, isDark),
                        width: `${(amount / maxCatAmount) * 100}%`,
                      }]}
                    />
                  </View>
                  <Text style={[styles.barAmount, { color: colors.textSecondary }]}>{formatINRShort(amount)}</Text>
                </View>
              </View>
            ))}
          </View>
        )}

        {/* Recent Transactions */}
        {stats && stats.recent_transactions.length > 0 && (
          <View style={[styles.recentCard, { backgroundColor: colors.surface, borderColor: colors.border }]}>
            <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Recent Transactions</Text>
            {stats.recent_transactions.map((txn: any) => (
              <View key={txn.id} style={[styles.txnRow, { borderBottomColor: colors.border }]}>
                <View style={[styles.txnIcon, {
                  backgroundColor: txn.type === 'income'
                    ? (isDark ? '#064E3B' : '#D1FAE5')
                    : txn.type === 'investment'
                    ? (isDark ? '#312E81' : '#E0E7FF')
                    : (isDark ? '#7F1D1D' : '#FEE2E2'),
                }]}>
                  <MaterialCommunityIcons
                    name={txn.type === 'income' ? 'arrow-down' : txn.type === 'investment' ? 'chart-line' : 'arrow-up'}
                    size={18}
                    color={txn.type === 'income' ? colors.income : txn.type === 'investment' ? colors.investment : colors.expense}
                  />
                </View>
                <View style={styles.txnInfo}>
                  <Text style={[styles.txnDesc, { color: colors.textPrimary }]} numberOfLines={1}>{txn.description}</Text>
                  <Text style={[styles.txnCat, { color: colors.textSecondary }]}>{txn.category} · {txn.date}</Text>
                </View>
                <Text style={[styles.txnAmount, {
                  color: txn.type === 'income' ? colors.income : txn.type === 'investment' ? colors.investment : colors.expense,
                }]}>
                  {txn.type === 'income' ? '+' : '-'}{formatINRShort(txn.amount)}
                </Text>
              </View>
            ))}
          </View>
        )}

        <View style={{ height: 24 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

function HealthMetric({ label, value, colors }: { label: string; value: string; colors: any }) {
  return (
    <View style={styles.metricRow}>
      <Text style={[styles.metricLabel, { color: colors.textSecondary }]}>{label}</Text>
      <Text style={[styles.metricValue, { color: colors.textPrimary }]}>{value}</Text>
    </View>
  );
}

const { width } = Dimensions.get('window');
const styles = StyleSheet.create({
  safe: { flex: 1 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  scroll: { paddingHorizontal: 20, paddingTop: 16 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  greeting: { fontSize: 14 },
  userName: { fontSize: 24, fontWeight: '800', letterSpacing: -0.5, marginTop: 2 },
  avatarCircle: { width: 48, height: 48, borderRadius: 24, justifyContent: 'center', alignItems: 'center' },
  avatarText: { color: '#fff', fontSize: 20, fontWeight: '700' },

  balanceCard: { borderRadius: 24, padding: 24, marginBottom: 16 },
  balanceLabel: { color: 'rgba(255,255,255,0.8)', fontSize: 14, fontWeight: '500' },
  balanceAmount: { color: '#fff', fontSize: 32, fontWeight: '800', marginTop: 4, letterSpacing: -1 },
  balanceRow: { flexDirection: 'row', marginTop: 20, justifyContent: 'space-between' },
  balanceStat: { alignItems: 'center', flex: 1 },
  balanceStatText: { color: '#fff', fontSize: 15, fontWeight: '700', marginTop: 4 },
  balanceStatLabel: { color: 'rgba(255,255,255,0.7)', fontSize: 11, marginTop: 2 },
  balanceDivider: { width: 1, height: 40 },

  statsRow: { flexDirection: 'row', gap: 12, marginBottom: 16 },
  statCard: { flex: 1, borderRadius: 20, padding: 16, borderWidth: 1 },
  statIcon: { width: 40, height: 40, borderRadius: 12, justifyContent: 'center', alignItems: 'center', marginBottom: 12 },
  statAmount: { fontSize: 20, fontWeight: '800', letterSpacing: -0.5 },
  statLabel: { fontSize: 12, marginTop: 4 },

  healthCard: { borderRadius: 20, padding: 20, borderWidth: 1, marginBottom: 16 },
  healthHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  healthGrade: { fontSize: 14, fontWeight: '700' },
  healthContent: { flexDirection: 'row', alignItems: 'center', gap: 20 },
  scoreCircle: { width: 88, height: 88, borderRadius: 44, borderWidth: 4, justifyContent: 'center', alignItems: 'center' },
  scoreNum: { fontSize: 28, fontWeight: '800' },
  scoreMax: { fontSize: 12, marginTop: -2 },
  healthMetrics: { flex: 1, gap: 8 },
  metricRow: { flexDirection: 'row', justifyContent: 'space-between' },
  metricLabel: { fontSize: 13 },
  metricValue: { fontSize: 13, fontWeight: '700' },

  breakdownCard: { borderRadius: 20, padding: 20, borderWidth: 1, marginBottom: 16 },
  sectionTitle: { fontSize: 17, fontWeight: '700', marginBottom: 16 },
  barRow: { marginBottom: 14 },
  barLabel: { fontSize: 13, fontWeight: '600', marginBottom: 6 },
  barContainer: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  barBg: { flex: 1, height: 8, borderRadius: 4, overflow: 'hidden' },
  barFill: { height: '100%', borderRadius: 4 },
  barAmount: { fontSize: 12, fontWeight: '600', width: 50, textAlign: 'right' },

  recentCard: { borderRadius: 20, padding: 20, borderWidth: 1, marginBottom: 16 },
  txnRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, borderBottomWidth: 0.5, gap: 12 },
  txnIcon: { width: 40, height: 40, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  txnInfo: { flex: 1 },
  txnDesc: { fontSize: 14, fontWeight: '600' },
  txnCat: { fontSize: 12, marginTop: 2 },
  txnAmount: { fontSize: 15, fontWeight: '700' },
});
