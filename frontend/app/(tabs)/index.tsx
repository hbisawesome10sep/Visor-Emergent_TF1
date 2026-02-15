import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, StyleSheet, RefreshControl, ActivityIndicator,
  TouchableOpacity, Dimensions, Modal, TextInput, Alert,
  KeyboardAvoidingView, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useAuth } from '../../src/context/AuthContext';
import { useTheme } from '../../src/context/ThemeContext';
import { apiRequest } from '../../src/utils/api';
import { formatINR, formatINRShort, getGreeting, getCategoryColor } from '../../src/utils/formatters';
import WaterfillCard from '../../src/components/WaterfillCard';
import FAB from '../../src/components/FAB';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const CARD_WIDTH = (SCREEN_WIDTH - 52) / 2;

const EXPENSE_CATS = ['Rent', 'Groceries', 'Food', 'Transport', 'Shopping', 'Utilities', 'Entertainment', 'Health', 'EMI', 'Other'];
const INCOME_CATS = ['Salary', 'Freelance', 'Bonus', 'Interest', 'Dividend', 'Other'];
const INVEST_CATS = ['SIP', 'PPF', 'Stocks', 'Mutual Funds', 'FD', 'Gold', 'NPS', 'Other'];

type DashboardStats = {
  total_income: number;
  total_expenses: number;
  total_investments: number;
  net_balance: number;
  savings: number;
  savings_rate: number;
  expense_ratio: number;
  investment_ratio: number;
  category_breakdown: Record<string, number>;
  budget_items: Array<{ category: string; amount: number; percentage: number }>;
  invest_breakdown: Record<string, number>;
  recent_transactions: any[];
  monthly_income: number;
  monthly_expenses: number;
  monthly_investments: number;
  monthly_savings: number;
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
  goal_progress: number;
  breakdown: { savings: number; investments: number; spending: number; goals: number };
};

export default function DashboardScreen() {
  const { user, token } = useAuth();
  const { colors, isDark } = useTheme();
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [health, setHealth] = useState<HealthScore | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showTxnModal, setShowTxnModal] = useState(false);
  const [txnForm, setTxnForm] = useState({ type: 'expense', amount: '', category: '', description: '', date: '' });
  const [saving, setSaving] = useState(false);

  const fetchData = useCallback(async () => {
    if (!token) return;
    try {
      const [s, h] = await Promise.all([
        apiRequest('/dashboard/stats', { token }),
        apiRequest('/health-score', { token }),
      ]);
      setStats(s);
      setHealth(h);
    } catch (e) { console.error(e); }
    finally { setLoading(false); setRefreshing(false); }
  }, [token]);

  useEffect(() => { fetchData(); }, [fetchData]);
  const onRefresh = () => { setRefreshing(true); fetchData(); };

  const handleAddTxn = async () => {
    if (!txnForm.amount || !txnForm.category || !txnForm.description) {
      Alert.alert('Error', 'Please fill all fields'); return;
    }
    setSaving(true);
    try {
      const today = new Date().toISOString().split('T')[0];
      await apiRequest('/transactions', {
        method: 'POST', token,
        body: { ...txnForm, amount: parseFloat(txnForm.amount), date: txnForm.date || today },
      });
      setShowTxnModal(false);
      setTxnForm({ type: 'expense', amount: '', category: '', description: '', date: '' });
      fetchData();
    } catch (e: any) { Alert.alert('Error', e.message); }
    finally { setSaving(false); }
  };

  if (loading) {
    return (
      <SafeAreaView style={[styles.safe, { backgroundColor: colors.background }]}>
        <View style={styles.center}><ActivityIndicator size="large" color={colors.primary} /></View>
      </SafeAreaView>
    );
  }

  // Waterfill calculations
  const incomePercent = stats ? Math.max(100 - (stats.expense_ratio || 0), 0) : 100;
  const expensePercent = stats ? Math.min(stats.expense_ratio || 0, 100) : 0;
  const savingsPercent = stats ? Math.min(stats.savings_rate || 0, 100) : 0;
  const investPercent = stats ? Math.min(stats.investment_ratio || 0, 100) : 0;

  // Health score color
  const scoreColor = health && health.overall_score >= 70 ? colors.success
    : health && health.overall_score >= 45 ? colors.warning : colors.error;

  // Budget items (top 6)
  const budgetItems = stats?.budget_items?.slice(0, 6) || [];

  // Expense breakdown for stacked bar
  const categoryEntries = stats ? Object.entries(stats.category_breakdown).sort((a, b) => b[1] - a[1]) : [];
  const totalExpenseForBar = categoryEntries.reduce((s, [, v]) => s + v, 0) || 1;

  // Investment breakdown
  const investEntries = stats ? Object.entries(stats.invest_breakdown).sort((a, b) => b[1] - a[1]) : [];

  const fabActions = [
    { icon: 'cash-minus', label: 'Add Expense', color: colors.expense, onPress: () => { setTxnForm(p => ({ ...p, type: 'expense' })); setShowTxnModal(true); } },
    { icon: 'cash-plus', label: 'Add Income', color: colors.income, onPress: () => { setTxnForm(p => ({ ...p, type: 'income' })); setShowTxnModal(true); } },
    { icon: 'chart-line', label: 'Add Investment', color: colors.investment, onPress: () => { setTxnForm(p => ({ ...p, type: 'investment' })); setShowTxnModal(true); } },
  ];

  const cats = txnForm.type === 'income' ? INCOME_CATS : txnForm.type === 'investment' ? INVEST_CATS : EXPENSE_CATS;

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: colors.background }]}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />}
        showsVerticalScrollIndicator={false}
      >
        {/* ═══ HEADER ═══ */}
        <View style={styles.header}>
          <View>
            <Text style={[styles.greeting, { color: colors.textSecondary }]}>{getGreeting()},</Text>
            <Text style={[styles.userName, { color: colors.textPrimary }]}>
              {user?.full_name?.split(' ')[0] || 'User'}
            </Text>
          </View>
          <TouchableOpacity testID="profile-avatar" style={[styles.avatarCircle, { backgroundColor: colors.primary }]}>
            <Text style={styles.avatarText}>{user?.full_name?.charAt(0)?.toUpperCase() || 'V'}</Text>
          </TouchableOpacity>
        </View>

        {/* ═══ NET WORTH CARD (Glass) ═══ */}
        <View style={[styles.netWorthCard, {
          backgroundColor: isDark ? 'rgba(16, 185, 129, 0.15)' : 'rgba(5, 150, 105, 0.08)',
          borderColor: isDark ? 'rgba(16, 185, 129, 0.3)' : 'rgba(5, 150, 105, 0.2)',
        }]}>
          <View style={styles.netWorthHeader}>
            <Text style={[styles.netWorthLabel, { color: colors.primary }]}>Net Worth</Text>
            <View style={[styles.trendBadge, { backgroundColor: `${colors.success}20` }]}>
              <MaterialCommunityIcons name="trending-up" size={14} color={colors.success} />
              <Text style={[styles.trendText, { color: colors.success }]}>+{stats?.savings_rate || 0}%</Text>
            </View>
          </View>
          <Text testID="net-balance" style={[styles.netWorthAmount, { color: colors.textPrimary }]}>
            {formatINR(stats?.net_balance || 0)}
          </Text>
          <View style={styles.netWorthMeta}>
            <View style={styles.metaItem}>
              <MaterialCommunityIcons name="arrow-down-circle" size={16} color={colors.income} />
              <Text style={[styles.metaText, { color: colors.textSecondary }]}>
                {formatINRShort(stats?.monthly_income || 0)}
                <Text style={styles.metaLabel}> income</Text>
              </Text>
            </View>
            <View style={[styles.metaDot, { backgroundColor: colors.border }]} />
            <View style={styles.metaItem}>
              <MaterialCommunityIcons name="arrow-up-circle" size={16} color={colors.expense} />
              <Text style={[styles.metaText, { color: colors.textSecondary }]}>
                {formatINRShort(stats?.monthly_expenses || 0)}
                <Text style={styles.metaLabel}> spent</Text>
              </Text>
            </View>
            <View style={[styles.metaDot, { backgroundColor: colors.border }]} />
            <View style={styles.metaItem}>
              <MaterialCommunityIcons name="piggy-bank" size={16} color={colors.success} />
              <Text style={[styles.metaText, { color: colors.textSecondary }]}>
                {formatINRShort(stats?.monthly_savings || 0)}
                <Text style={styles.metaLabel}> saved</Text>
              </Text>
            </View>
          </View>
        </View>

        {/* ═══ WATERFILL OVERVIEW CARDS (2x2 Grid) ═══ */}
        <Text style={[styles.sectionLabel, { color: colors.textPrimary }]}>Overview</Text>
        <View style={styles.cardGrid}>
          <WaterfillCard
            title="Income"
            amount={formatINRShort(stats?.total_income || 0)}
            subtitle="Remaining after expenses"
            fillPercent={incomePercent}
            icon="arrow-down-circle"
            mode="drain"
            colors={colors}
            isDark={isDark}
            accentColor={colors.income}
            iconBgColor={isDark ? '#064E3B' : '#D1FAE5'}
          />
          <WaterfillCard
            title="Expenses"
            amount={formatINRShort(stats?.total_expenses || 0)}
            subtitle="of total income"
            fillPercent={expensePercent}
            icon="arrow-up-circle"
            mode="fill"
            colors={colors}
            isDark={isDark}
            accentColor={colors.expense}
            iconBgColor={isDark ? '#7F1D1D' : '#FEE2E2'}
          />
        </View>
        <View style={[styles.cardGrid, { marginTop: 12 }]}>
          <WaterfillCard
            title="Savings"
            amount={formatINRShort(stats?.savings || 0)}
            subtitle="savings rate"
            fillPercent={savingsPercent}
            icon="piggy-bank"
            mode="drain"
            colors={colors}
            isDark={isDark}
            accentColor={colors.success}
            iconBgColor={isDark ? '#064E3B' : '#D1FAE5'}
          />
          <WaterfillCard
            title="Invested"
            amount={formatINRShort(stats?.total_investments || 0)}
            subtitle="of income invested"
            fillPercent={investPercent}
            icon="chart-line"
            mode="drain"
            colors={colors}
            isDark={isDark}
            accentColor={colors.investment}
            iconBgColor={isDark ? '#312E81' : '#E0E7FF'}
          />
        </View>

        {/* ═══ FINANCIAL HEALTH SCORE (Glass) ═══ */}
        {health && (
          <View style={[styles.glassCard, {
            backgroundColor: isDark ? 'rgba(30, 41, 59, 0.8)' : 'rgba(255, 255, 255, 0.85)',
            borderColor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)',
          }]}>
            <View style={styles.healthHeader}>
              <View>
                <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Financial Health</Text>
                <Text style={[styles.healthGradeLabel, { color: scoreColor }]}>{health.grade}</Text>
              </View>
              <View style={[styles.scoreRing, { borderColor: scoreColor }]}>
                <Text style={[styles.scoreNum, { color: scoreColor }]}>{Math.round(health.overall_score)}</Text>
              </View>
            </View>
            {/* Score breakdown bars */}
            <View style={styles.breakdownBars}>
              <ScoreBar label="Savings" value={health.breakdown.savings} color={colors.success} colors={colors} isDark={isDark} />
              <ScoreBar label="Investments" value={health.breakdown.investments} color={colors.investment} colors={colors} isDark={isDark} />
              <ScoreBar label="Spending" value={health.breakdown.spending} color={colors.warning} colors={colors} isDark={isDark} />
              <ScoreBar label="Goals" value={health.breakdown.goals} color={colors.primary} colors={colors} isDark={isDark} />
            </View>
          </View>
        )}

        {/* ═══ BUDGET SECTION (Segmented Progress Bars) ═══ */}
        {budgetItems.length > 0 && (
          <View style={[styles.glassCard, {
            backgroundColor: isDark ? 'rgba(30, 41, 59, 0.8)' : 'rgba(255, 255, 255, 0.85)',
            borderColor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)',
          }]}>
            <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Budget Breakdown</Text>

            {/* Stacked Bar Chart */}
            <View style={[styles.stackedBar, { backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.04)' }]}>
              {categoryEntries.slice(0, 6).map(([cat, amount], i) => (
                <View key={cat} style={[styles.stackedSegment, {
                  width: `${(amount / totalExpenseForBar) * 100}%`,
                  backgroundColor: getCategoryColor(cat, isDark),
                  borderTopLeftRadius: i === 0 ? 8 : 0,
                  borderBottomLeftRadius: i === 0 ? 8 : 0,
                  borderTopRightRadius: i === categoryEntries.slice(0, 6).length - 1 ? 8 : 0,
                  borderBottomRightRadius: i === categoryEntries.slice(0, 6).length - 1 ? 8 : 0,
                }]} />
              ))}
            </View>

            {/* Category Legend */}
            <View style={styles.legendGrid}>
              {budgetItems.map(item => {
                const barColor = getCategoryColor(item.category, isDark);
                const semantic = item.percentage > 30 ? colors.error : item.percentage > 20 ? colors.warning : colors.success;
                return (
                  <View key={item.category} style={styles.budgetRow}>
                    <View style={styles.budgetLeft}>
                      <View style={[styles.legendDot, { backgroundColor: barColor }]} />
                      <Text style={[styles.budgetCat, { color: colors.textPrimary }]}>{item.category}</Text>
                    </View>
                    <View style={styles.budgetRight}>
                      <Text style={[styles.budgetAmount, { color: colors.textPrimary }]}>{formatINRShort(item.amount)}</Text>
                      <View style={[styles.budgetPctBadge, { backgroundColor: `${semantic}18` }]}>
                        <Text style={[styles.budgetPct, { color: semantic }]}>{item.percentage}%</Text>
                      </View>
                    </View>
                  </View>
                );
              })}
            </View>
          </View>
        )}

        {/* ═══ INVESTMENT ALLOCATION ═══ */}
        {investEntries.length > 0 && (
          <View style={[styles.glassCard, {
            backgroundColor: isDark ? 'rgba(30, 41, 59, 0.8)' : 'rgba(255, 255, 255, 0.85)',
            borderColor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)',
          }]}>
            <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Investment Allocation</Text>
            <View style={styles.investGrid}>
              {investEntries.map(([cat, amount]) => {
                const pct = ((amount / (stats?.total_investments || 1)) * 100).toFixed(0);
                return (
                  <View key={cat} style={[styles.investChip, {
                    backgroundColor: isDark ? 'rgba(99, 102, 241, 0.1)' : 'rgba(99, 102, 241, 0.06)',
                    borderColor: isDark ? 'rgba(99, 102, 241, 0.2)' : 'rgba(99, 102, 241, 0.15)',
                  }]}>
                    <Text style={[styles.investName, { color: colors.investment }]}>{cat}</Text>
                    <Text style={[styles.investAmt, { color: colors.textPrimary }]}>{formatINRShort(amount)}</Text>
                    <Text style={[styles.investPct, { color: colors.textSecondary }]}>{pct}%</Text>
                  </View>
                );
              })}
            </View>
          </View>
        )}

        {/* ═══ RECENT TRANSACTIONS ═══ */}
        {stats && stats.recent_transactions.length > 0 && (
          <View style={[styles.glassCard, {
            backgroundColor: isDark ? 'rgba(30, 41, 59, 0.8)' : 'rgba(255, 255, 255, 0.85)',
            borderColor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)',
          }]}>
            <View style={styles.recentHeader}>
              <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Recent Transactions</Text>
              <TouchableOpacity testID="view-all-txns" onPress={() => router.push('/(tabs)/transactions')}>
                <Text style={[styles.viewAllText, { color: colors.primary }]}>View All</Text>
              </TouchableOpacity>
            </View>
            {stats.recent_transactions.map((txn: any, index: number) => (
              <View key={txn.id} style={[styles.txnRow, {
                borderBottomColor: colors.border,
                borderBottomWidth: index < stats.recent_transactions.length - 1 ? 0.5 : 0,
              }]}>
                <View style={[styles.txnIcon, {
                  backgroundColor: txn.type === 'income' ? (isDark ? '#064E3B' : '#D1FAE5')
                    : txn.type === 'investment' ? (isDark ? '#312E81' : '#E0E7FF')
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
                  <Text style={[styles.txnMeta, { color: colors.textSecondary }]}>{txn.category} · {txn.date}</Text>
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

        <View style={{ height: 100 }} />
      </ScrollView>

      {/* ═══ FLOATING ACTION BUTTON ═══ */}
      <FAB actions={fabActions} colors={colors} isDark={isDark} />

      {/* ═══ QUICK ADD TRANSACTION MODAL ═══ */}
      <Modal visible={showTxnModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.modalKav}>
            <View style={[styles.modalContent, { backgroundColor: colors.surface }]}>
              <View style={styles.modalHandle} />
              <View style={styles.modalHeader}>
                <Text style={[styles.modalTitle, { color: colors.textPrimary }]}>
                  Quick Add {txnForm.type.charAt(0).toUpperCase() + txnForm.type.slice(1)}
                </Text>
                <TouchableOpacity testID="close-quick-add" onPress={() => setShowTxnModal(false)}>
                  <MaterialCommunityIcons name="close" size={24} color={colors.textSecondary} />
                </TouchableOpacity>
              </View>

              {/* Type Tabs */}
              <View style={styles.typeRow}>
                {(['expense', 'income', 'investment'] as const).map(t => (
                  <TouchableOpacity key={t} testID={`quick-type-${t}`}
                    style={[styles.typeTab, {
                      backgroundColor: txnForm.type === t
                        ? (t === 'income' ? colors.income : t === 'investment' ? colors.investment : colors.expense)
                        : colors.background,
                      borderColor: colors.border,
                    }]}
                    onPress={() => setTxnForm(p => ({ ...p, type: t, category: '' }))}
                  >
                    <MaterialCommunityIcons
                      name={t === 'income' ? 'arrow-down' : t === 'investment' ? 'chart-line' : 'arrow-up'}
                      size={16} color={txnForm.type === t ? '#fff' : colors.textSecondary}
                    />
                    <Text style={{ fontSize: 13, fontWeight: '600', color: txnForm.type === t ? '#fff' : colors.textSecondary }}>
                      {t.charAt(0).toUpperCase() + t.slice(1)}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>

              {/* Amount */}
              <View style={[styles.amountRow, { borderColor: colors.border, backgroundColor: colors.background }]}>
                <Text style={[styles.rupeeSymbol, { color: colors.primary }]}>₹</Text>
                <TextInput testID="quick-amount" style={[styles.amountInput, { color: colors.textPrimary }]}
                  value={txnForm.amount} onChangeText={v => setTxnForm(p => ({ ...p, amount: v }))}
                  placeholder="0" placeholderTextColor={colors.textSecondary} keyboardType="decimal-pad"
                />
              </View>

              {/* Categories */}
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.catScroll}>
                {cats.map(c => (
                  <TouchableOpacity key={c} testID={`quick-cat-${c}`}
                    style={[styles.catChip, {
                      backgroundColor: txnForm.category === c ? colors.primary : colors.background,
                      borderColor: txnForm.category === c ? colors.primary : colors.border,
                    }]}
                    onPress={() => setTxnForm(p => ({ ...p, category: c }))}
                  >
                    <Text style={{ color: txnForm.category === c ? '#fff' : colors.textSecondary, fontSize: 13 }}>{c}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>

              {/* Description */}
              <TextInput testID="quick-desc" style={[styles.descInput, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                value={txnForm.description} onChangeText={v => setTxnForm(p => ({ ...p, description: v }))}
                placeholder="What was this for?" placeholderTextColor={colors.textSecondary}
              />

              <TouchableOpacity testID="quick-save" style={[styles.saveBtn, { backgroundColor: colors.primary }]}
                onPress={handleAddTxn} disabled={saving}
              >
                {saving ? <ActivityIndicator color="#fff" /> :
                  <Text style={styles.saveBtnText}>Add {txnForm.type.charAt(0).toUpperCase() + txnForm.type.slice(1)}</Text>
                }
              </TouchableOpacity>
            </View>
          </KeyboardAvoidingView>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

// ── Score Bar Component ──
function ScoreBar({ label, value, color, colors, isDark }: { label: string; value: number; color: string; colors: any; isDark: boolean }) {
  return (
    <View style={styles.scoreBarRow}>
      <View style={styles.scoreBarLeft}>
        <View style={[styles.scoreBarDot, { backgroundColor: color }]} />
        <Text style={[styles.scoreBarLabel, { color: colors.textSecondary }]}>{label}</Text>
      </View>
      <View style={[styles.scoreBarTrack, { backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)' }]}>
        <View style={[styles.scoreBarFill, { width: `${Math.min(value, 100)}%`, backgroundColor: color }]} />
      </View>
      <Text style={[styles.scoreBarValue, { color: colors.textPrimary }]}>{value.toFixed(0)}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  scroll: { paddingHorizontal: 16, paddingTop: 12 },

  // Header
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, paddingHorizontal: 4 },
  greeting: { fontSize: 14, fontWeight: '400' },
  userName: { fontSize: 26, fontWeight: '800', letterSpacing: -0.8, marginTop: 2 },
  avatarCircle: { width: 48, height: 48, borderRadius: 24, justifyContent: 'center', alignItems: 'center' },
  avatarText: { color: '#fff', fontSize: 20, fontWeight: '700' },

  // Net Worth
  netWorthCard: { borderRadius: 24, padding: 20, borderWidth: 1, marginBottom: 20 },
  netWorthHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  netWorthLabel: { fontSize: 13, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5 },
  trendBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8 },
  trendText: { fontSize: 12, fontWeight: '700' },
  netWorthAmount: { fontSize: 34, fontWeight: '800', letterSpacing: -1.5, marginTop: 4 },
  netWorthMeta: { flexDirection: 'row', alignItems: 'center', marginTop: 14, gap: 6, flexWrap: 'wrap' },
  metaItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  metaText: { fontSize: 13, fontWeight: '500' },
  metaLabel: { fontWeight: '400' },
  metaDot: { width: 3, height: 3, borderRadius: 1.5 },

  // Section
  sectionLabel: { fontSize: 17, fontWeight: '700', marginBottom: 12, paddingHorizontal: 4 },

  // Card Grid
  cardGrid: { flexDirection: 'row', gap: 12 },

  // Glass Card
  glassCard: {
    borderRadius: 24, padding: 20, borderWidth: 1, marginTop: 20,
    shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.1, shadowRadius: 16, elevation: 5,
  },
  sectionTitle: { fontSize: 17, fontWeight: '700', marginBottom: 4 },

  // Health Score
  healthHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  healthGradeLabel: { fontSize: 13, fontWeight: '600', marginTop: 4 },
  scoreRing: { width: 64, height: 64, borderRadius: 32, borderWidth: 3, justifyContent: 'center', alignItems: 'center' },
  scoreNum: { fontSize: 22, fontWeight: '800' },
  breakdownBars: { gap: 10 },
  scoreBarRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  scoreBarLeft: { flexDirection: 'row', alignItems: 'center', gap: 6, width: 90 },
  scoreBarDot: { width: 8, height: 8, borderRadius: 4 },
  scoreBarLabel: { fontSize: 12, fontWeight: '500' },
  scoreBarTrack: { flex: 1, height: 6, borderRadius: 3, overflow: 'hidden' },
  scoreBarFill: { height: '100%', borderRadius: 3 },
  scoreBarValue: { width: 28, fontSize: 12, fontWeight: '700', textAlign: 'right' },

  // Budget
  stackedBar: { height: 16, borderRadius: 8, flexDirection: 'row', overflow: 'hidden', marginTop: 12, marginBottom: 16 },
  stackedSegment: { height: '100%' },
  legendGrid: { gap: 10 },
  budgetRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  budgetLeft: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  legendDot: { width: 10, height: 10, borderRadius: 5 },
  budgetCat: { fontSize: 13, fontWeight: '600' },
  budgetRight: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  budgetAmount: { fontSize: 13, fontWeight: '700' },
  budgetPctBadge: { paddingHorizontal: 7, paddingVertical: 2, borderRadius: 6 },
  budgetPct: { fontSize: 11, fontWeight: '700' },

  // Investments
  investGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginTop: 12 },
  investChip: { borderRadius: 14, paddingHorizontal: 14, paddingVertical: 12, borderWidth: 1, minWidth: 100 },
  investName: { fontSize: 11, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.3 },
  investAmt: { fontSize: 16, fontWeight: '800', marginTop: 4 },
  investPct: { fontSize: 11, marginTop: 2 },

  // Transactions
  recentHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  viewAllText: { fontSize: 13, fontWeight: '600' },
  txnRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, gap: 12 },
  txnIcon: { width: 40, height: 40, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  txnInfo: { flex: 1 },
  txnDesc: { fontSize: 14, fontWeight: '600' },
  txnMeta: { fontSize: 11, marginTop: 2 },
  txnAmount: { fontSize: 15, fontWeight: '700' },

  // Modal
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modalKav: { maxHeight: '85%' },
  modalContent: { borderTopLeftRadius: 28, borderTopRightRadius: 28, padding: 24, paddingBottom: 40 },
  modalHandle: { width: 40, height: 4, borderRadius: 2, backgroundColor: '#CBD5E1', alignSelf: 'center', marginBottom: 16 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  modalTitle: { fontSize: 20, fontWeight: '700' },
  typeRow: { flexDirection: 'row', gap: 8, marginBottom: 20 },
  typeTab: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, paddingVertical: 12, borderRadius: 14, borderWidth: 1 },
  amountRow: { flexDirection: 'row', alignItems: 'center', height: 60, borderRadius: 16, borderWidth: 1, marginBottom: 16, paddingHorizontal: 16 },
  rupeeSymbol: { fontSize: 24, fontWeight: '800' },
  amountInput: { flex: 1, fontSize: 28, fontWeight: '800', paddingHorizontal: 8, height: '100%' },
  catScroll: { maxHeight: 40, marginBottom: 16 },
  catChip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 16, borderWidth: 1, marginRight: 8 },
  descInput: { height: 48, borderRadius: 14, borderWidth: 1, paddingHorizontal: 16, fontSize: 15, marginBottom: 16 },
  saveBtn: { height: 56, borderRadius: 999, justifyContent: 'center', alignItems: 'center' },
  saveBtnText: { color: '#fff', fontSize: 17, fontWeight: '700' },
});
