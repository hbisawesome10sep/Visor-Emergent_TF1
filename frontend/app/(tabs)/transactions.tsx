import React, { useEffect, useState, useCallback, useMemo } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, TextInput, Modal,
  RefreshControl, ActivityIndicator, Alert, KeyboardAvoidingView, Platform,
  Switch, Animated,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useAuth } from '../../src/context/AuthContext';
import { useTheme } from '../../src/context/ThemeContext';
import { apiRequest } from '../../src/utils/api';
import { formatINR, formatINRShort, getCategoryColor, getCategoryIcon } from '../../src/utils/formatters';

const EXPENSE_CATS = ['Rent', 'Groceries', 'Food', 'Transport', 'Shopping', 'Utilities', 'Entertainment', 'Health', 'EMI', 'Other'];
const INCOME_CATS = ['Salary', 'Freelance', 'Bonus', 'Interest', 'Dividend', 'Rental Income', 'Other'];
const INVEST_CATS = ['SIP', 'PPF', 'Stocks', 'Mutual Funds', 'FD', 'Gold', 'NPS', 'ELSS', 'Other'];
const RECURRING_FREQ = ['Daily', 'Weekly', 'Monthly', 'Quarterly', 'Yearly'];

type Transaction = {
  id: string; type: string; amount: number; category: string;
  description: string; date: string; created_at: string;
  is_recurring?: boolean; recurring_frequency?: string;
  is_split?: boolean; split_count?: number; notes?: string;
};

// ── Date grouping helper ──
function getDateLabel(dateStr: string): string {
  const today = new Date();
  const d = new Date(dateStr + 'T00:00:00');
  const todayStr = today.toISOString().split('T')[0];
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const yesterdayStr = yesterday.toISOString().split('T')[0];

  if (dateStr === todayStr) return 'Today';
  if (dateStr === yesterdayStr) return 'Yesterday';

  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${months[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`;
}

function groupByDate(txns: Transaction[]): Array<{ label: string; date: string; transactions: Transaction[] }> {
  const grouped: Record<string, Transaction[]> = {};
  txns.forEach(t => {
    const key = t.date;
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(t);
  });
  return Object.entries(grouped)
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([date, transactions]) => ({
      label: getDateLabel(date),
      date,
      transactions,
    }));
}

export default function TransactionsScreen() {
  const { token } = useAuth();
  const { colors, isDark } = useTheme();
  const router = useRouter();
  const params = useLocalSearchParams<{ type?: string }>();

  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [modalStep, setModalStep] = useState(1);

  // Filters
  const [activeType, setActiveType] = useState<string>(params.type || 'all');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState<string>('');
  const [showSearch, setShowSearch] = useState(false);

  // Form
  const [form, setForm] = useState({
    type: 'expense', amount: '', category: '', description: '',
    date: '', notes: '', is_recurring: false, recurring_frequency: '',
    is_split: false, split_count: '1',
  });
  const [saving, setSaving] = useState(false);

  // Summary
  const summary = useMemo(() => {
    const inc = transactions.filter(t => t.type === 'income').reduce((s, t) => s + t.amount, 0);
    const exp = transactions.filter(t => t.type === 'expense').reduce((s, t) => s + t.amount, 0);
    const inv = transactions.filter(t => t.type === 'investment').reduce((s, t) => s + t.amount, 0);
    return { income: inc, expense: exp, investment: inv, total: transactions.length };
  }, [transactions]);

  const fetchTxns = useCallback(async () => {
    if (!token) return;
    try {
      const params = new URLSearchParams();
      if (activeType !== 'all') params.append('type', activeType);
      if (activeCategory) params.append('category', activeCategory);
      if (searchQuery.trim()) params.append('search', searchQuery.trim());
      const qs = params.toString() ? `?${params.toString()}` : '';
      const data = await apiRequest(`/transactions${qs}`, { token });
      setTransactions(data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); setRefreshing(false); }
  }, [token, activeType, activeCategory, searchQuery]);

  useEffect(() => { fetchTxns(); }, [fetchTxns]);
  const onRefresh = () => { setRefreshing(true); fetchTxns(); };

  // ── Modal handlers ──
  const openAdd = (type?: string) => {
    setForm({
      type: type || 'expense', amount: '', category: '', description: '',
      date: '', notes: '', is_recurring: false, recurring_frequency: '',
      is_split: false, split_count: '1',
    });
    setModalStep(1);
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!form.amount || !form.category || !form.description) {
      Alert.alert('Missing Info', 'Please fill in amount, category, and description'); return;
    }
    setSaving(true);
    try {
      const today = new Date().toISOString().split('T')[0];
      await apiRequest('/transactions', {
        method: 'POST', token,
        body: {
          type: form.type,
          amount: parseFloat(form.amount),
          category: form.category,
          description: form.description,
          date: form.date || today,
          notes: form.notes || null,
          is_recurring: form.is_recurring,
          recurring_frequency: form.is_recurring ? form.recurring_frequency : null,
          is_split: form.is_split,
          split_count: form.is_split ? parseInt(form.split_count) || 1 : 1,
        },
      });
      setShowModal(false);
      fetchTxns();
    } catch (e: any) { Alert.alert('Error', e.message); }
    finally { setSaving(false); }
  };

  const handleDelete = (id: string, desc: string) => {
    Alert.alert('Delete Transaction', `Remove "${desc}"?`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: async () => {
        try {
          await apiRequest(`/transactions/${id}`, { method: 'DELETE', token });
          setTransactions(prev => prev.filter(t => t.id !== id));
        } catch (e: any) { Alert.alert('Error', e.message); }
      }},
    ]);
  };

  const dateGroups = useMemo(() => groupByDate(transactions), [transactions]);
  const cats = form.type === 'income' ? INCOME_CATS : form.type === 'investment' ? INVEST_CATS : EXPENSE_CATS;
  const typeFilters = ['all', 'income', 'expense', 'investment'];
  const quickCatFilters = ['Rent', 'Food', 'Transport', 'Groceries', 'SIP', 'Salary'];

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: colors.background }]}>
      {/* ═══ HEADER ═══ */}
      <View style={[styles.header, { borderBottomColor: colors.border }]}>
        <View>
          <Text style={[styles.title, { color: colors.textPrimary }]}>Transactions</Text>
          <Text style={[styles.subtitle, { color: colors.textSecondary }]}>{summary.total} total</Text>
        </View>
        <View style={styles.headerActions}>
          <TouchableOpacity testID="toggle-search-btn"
            style={[styles.iconBtn, { backgroundColor: showSearch ? colors.primary : colors.surface, borderColor: colors.border }]}
            onPress={() => { setShowSearch(!showSearch); if (showSearch) { setSearchQuery(''); } }}
          >
            <MaterialCommunityIcons name={showSearch ? 'close' : 'magnify'} size={20} color={showSearch ? '#fff' : colors.textSecondary} />
          </TouchableOpacity>
          <TouchableOpacity testID="add-transaction-btn"
            style={[styles.addBtn, { backgroundColor: colors.primary }]}
            onPress={() => openAdd()}
          >
            <MaterialCommunityIcons name="plus" size={22} color="#fff" />
          </TouchableOpacity>
        </View>
      </View>

      {/* ═══ SEARCH BAR ═══ */}
      {showSearch && (
        <View style={[styles.searchBar, { backgroundColor: colors.surface, borderColor: colors.border }]}>
          <MaterialCommunityIcons name="magnify" size={20} color={colors.textSecondary} />
          <TextInput
            testID="search-input"
            style={[styles.searchInput, { color: colors.textPrimary }]}
            value={searchQuery}
            onChangeText={setSearchQuery}
            placeholder="Search transactions..."
            placeholderTextColor={colors.textSecondary}
            autoFocus
          />
          {searchQuery.length > 0 && (
            <TouchableOpacity testID="clear-search-btn" onPress={() => setSearchQuery('')}>
              <MaterialCommunityIcons name="close-circle" size={18} color={colors.textSecondary} />
            </TouchableOpacity>
          )}
        </View>
      )}

      {/* ═══ TYPE FILTER TABS ═══ */}
      <View style={[styles.filterRow, { borderBottomColor: colors.border }]}>
        {typeFilters.map(f => {
          const isActive = activeType === f;
          const count = f === 'all' ? summary.total
            : f === 'income' ? transactions.filter(t => t.type === 'income').length
            : f === 'expense' ? transactions.filter(t => t.type === 'expense').length
            : transactions.filter(t => t.type === 'investment').length;
          return (
            <TouchableOpacity key={f} testID={`filter-${f}-btn`}
              style={[styles.filterTab, isActive && { borderBottomColor: colors.primary, borderBottomWidth: 2 }]}
              onPress={() => { setActiveType(f); setActiveCategory(''); }}
            >
              <Text style={[styles.filterLabel, { color: isActive ? colors.primary : colors.textSecondary }]}>
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* ═══ QUICK CATEGORY CHIPS ═══ */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false}
        style={styles.catChipScroll} contentContainerStyle={styles.catChipContainer}
      >
        {quickCatFilters.map(c => (
          <TouchableOpacity key={c} testID={`chip-${c}`}
            style={[styles.catChip, {
              backgroundColor: activeCategory === c ? colors.primary : isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.04)',
              borderColor: activeCategory === c ? colors.primary : colors.border,
            }]}
            onPress={() => setActiveCategory(activeCategory === c ? '' : c)}
          >
            <MaterialCommunityIcons
              name={getCategoryIcon(c) as any}
              size={14}
              color={activeCategory === c ? '#fff' : colors.textSecondary}
            />
            <Text style={[styles.catChipText, { color: activeCategory === c ? '#fff' : colors.textSecondary }]}>{c}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* ═══ SUMMARY STRIP ═══ */}
      <View style={[styles.summaryStrip, { backgroundColor: isDark ? 'rgba(30,41,59,0.6)' : 'rgba(255,255,255,0.7)', borderColor: colors.border }]}>
        <SummaryPill label="Income" amount={summary.income} color={colors.income} colors={colors} />
        <View style={[styles.summaryDivider, { backgroundColor: colors.border }]} />
        <SummaryPill label="Expense" amount={summary.expense} color={colors.expense} colors={colors} />
        <View style={[styles.summaryDivider, { backgroundColor: colors.border }]} />
        <SummaryPill label="Invested" amount={summary.investment} color={colors.investment} colors={colors} />
      </View>

      {/* ═══ TRANSACTION LIST ═══ */}
      {loading ? (
        <View style={styles.center}><ActivityIndicator size="large" color={colors.primary} /></View>
      ) : transactions.length === 0 ? (
        <View style={styles.emptyState}>
          <View style={[styles.emptyIcon, { backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.04)' }]}>
            <MaterialCommunityIcons name="receipt" size={48} color={colors.textSecondary} />
          </View>
          <Text style={[styles.emptyTitle, { color: colors.textPrimary }]}>No transactions found</Text>
          <Text style={[styles.emptySubtitle, { color: colors.textSecondary }]}>
            {searchQuery ? `No results for "${searchQuery}"` : activeCategory ? `No ${activeCategory} transactions` : 'Start tracking by adding your first transaction'}
          </Text>
          {!searchQuery && (
            <TouchableOpacity testID="empty-add-btn" style={[styles.emptyAddBtn, { backgroundColor: colors.primary }]} onPress={() => openAdd()}>
              <MaterialCommunityIcons name="plus" size={18} color="#fff" />
              <Text style={styles.emptyAddText}>Add Transaction</Text>
            </TouchableOpacity>
          )}
        </View>
      ) : (
        <ScrollView
          contentContainerStyle={styles.list}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />}
          showsVerticalScrollIndicator={false}
        >
          {dateGroups.map(group => (
            <View key={group.date}>
              {/* Date Header */}
              <View style={styles.dateHeader}>
                <Text style={[styles.dateLabel, { color: colors.textPrimary }]}>{group.label}</Text>
                <Text style={[styles.dateSublabel, { color: colors.textSecondary }]}>
                  {group.transactions.length} transaction{group.transactions.length > 1 ? 's' : ''}
                </Text>
              </View>

              {/* Transaction Cards */}
              {group.transactions.map(txn => (
                <TouchableOpacity key={txn.id} testID={`txn-${txn.id}`}
                  style={[styles.txnCard, {
                    backgroundColor: isDark ? 'rgba(30, 41, 59, 0.7)' : 'rgba(255, 255, 255, 0.85)',
                    borderColor: isDark ? 'rgba(255, 255, 255, 0.06)' : 'rgba(0, 0, 0, 0.05)',
                  }]}
                  onLongPress={() => handleDelete(txn.id, txn.description)}
                  activeOpacity={0.7}
                >
                  <View style={[styles.txnIconWrap, {
                    backgroundColor: txn.type === 'income' ? (isDark ? '#064E3B' : '#D1FAE5')
                      : txn.type === 'investment' ? (isDark ? '#312E81' : '#E0E7FF')
                      : (isDark ? '#7F1D1D' : '#FEE2E2'),
                  }]}>
                    <MaterialCommunityIcons
                      name={getCategoryIcon(txn.category) as any}
                      size={20}
                      color={txn.type === 'income' ? colors.income : txn.type === 'investment' ? colors.investment : colors.expense}
                    />
                  </View>
                  <View style={styles.txnBody}>
                    <Text style={[styles.txnDesc, { color: colors.textPrimary }]} numberOfLines={1}>{txn.description}</Text>
                    <View style={styles.txnMeta}>
                      <View style={[styles.txnCatBadge, { backgroundColor: `${getCategoryColor(txn.category, isDark)}15` }]}>
                        <Text style={[styles.txnCatText, { color: getCategoryColor(txn.category, isDark) }]}>{txn.category}</Text>
                      </View>
                      {txn.is_recurring && (
                        <View style={[styles.txnBadge, { backgroundColor: isDark ? 'rgba(99,102,241,0.15)' : 'rgba(99,102,241,0.08)' }]}>
                          <MaterialCommunityIcons name="repeat" size={10} color={colors.investment} />
                          <Text style={[styles.txnBadgeText, { color: colors.investment }]}>{txn.recurring_frequency || 'Recurring'}</Text>
                        </View>
                      )}
                      {txn.is_split && (
                        <View style={[styles.txnBadge, { backgroundColor: isDark ? 'rgba(245,158,11,0.15)' : 'rgba(245,158,11,0.08)' }]}>
                          <MaterialCommunityIcons name="call-split" size={10} color={colors.warning} />
                          <Text style={[styles.txnBadgeText, { color: colors.warning }]}>Split ÷{txn.split_count}</Text>
                        </View>
                      )}
                    </View>
                  </View>
                  <View style={styles.txnRight}>
                    <Text style={[styles.txnAmount, {
                      color: txn.type === 'income' ? colors.income : txn.type === 'investment' ? colors.investment : colors.expense,
                    }]}>
                      {txn.type === 'income' ? '+' : '-'}{formatINR(txn.amount)}
                    </Text>
                    {txn.is_split && txn.split_count && txn.split_count > 1 && (
                      <Text style={[styles.txnSplitAmt, { color: colors.textSecondary }]}>
                        each: {formatINRShort(txn.amount / txn.split_count)}
                      </Text>
                    )}
                  </View>
                </TouchableOpacity>
              ))}
            </View>
          ))}
          <View style={{ height: 100 }} />
        </ScrollView>
      )}

      {/* ═══ ADD TRANSACTION MODAL (Multi-Step) ═══ */}
      <Modal visible={showModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.modalKav}>
            <View style={[styles.modalContent, { backgroundColor: colors.surface }]}>
              <View style={styles.modalHandle} />

              {/* Modal Header */}
              <View style={styles.modalHeader}>
                <Text style={[styles.modalTitle, { color: colors.textPrimary }]}>
                  {modalStep === 1 ? 'New Transaction' : modalStep === 2 ? 'Details' : 'Options'}
                </Text>
                <View style={styles.modalHeaderRight}>
                  <View style={styles.stepIndicator}>
                    {[1, 2, 3].map(s => (
                      <View key={s} style={[styles.stepDot, {
                        backgroundColor: s <= modalStep ? colors.primary : colors.border,
                        width: s === modalStep ? 20 : 8,
                      }]} />
                    ))}
                  </View>
                  <TouchableOpacity testID="close-txn-modal" onPress={() => setShowModal(false)}>
                    <MaterialCommunityIcons name="close" size={24} color={colors.textSecondary} />
                  </TouchableOpacity>
                </View>
              </View>

              <ScrollView showsVerticalScrollIndicator={false}>
                {/* ── STEP 1: Type + Amount + Category ── */}
                {modalStep === 1 && (
                  <View>
                    {/* Type Selector */}
                    <View style={styles.typeRow}>
                      {(['expense', 'income', 'investment'] as const).map(t => {
                        const isActive = form.type === t;
                        const tColor = t === 'income' ? colors.income : t === 'investment' ? colors.investment : colors.expense;
                        return (
                          <TouchableOpacity key={t} testID={`type-${t}-btn`}
                            style={[styles.typeCard, {
                              backgroundColor: isActive ? tColor : isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
                              borderColor: isActive ? tColor : colors.border,
                            }]}
                            onPress={() => setForm(p => ({ ...p, type: t, category: '' }))}
                          >
                            <MaterialCommunityIcons
                              name={t === 'income' ? 'arrow-down-circle' : t === 'investment' ? 'chart-line' : 'arrow-up-circle'}
                              size={22} color={isActive ? '#fff' : tColor}
                            />
                            <Text style={[styles.typeCardLabel, { color: isActive ? '#fff' : colors.textPrimary }]}>
                              {t.charAt(0).toUpperCase() + t.slice(1)}
                            </Text>
                          </TouchableOpacity>
                        );
                      })}
                    </View>

                    {/* Amount Input */}
                    <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>Amount</Text>
                    <View style={[styles.amountBox, { borderColor: colors.border, backgroundColor: colors.background }]}>
                      <Text style={[styles.rupee, { color: colors.primary }]}>₹</Text>
                      <TextInput testID="amount-input"
                        style={[styles.amountField, { color: colors.textPrimary }]}
                        value={form.amount}
                        onChangeText={v => setForm(p => ({ ...p, amount: v }))}
                        placeholder="0.00"
                        placeholderTextColor={colors.textSecondary}
                        keyboardType="decimal-pad"
                      />
                    </View>

                    {/* Category Selection */}
                    <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>Category</Text>
                    <View style={styles.catGrid}>
                      {cats.map(c => {
                        const isActive = form.category === c;
                        const catColor = getCategoryColor(c, isDark);
                        return (
                          <TouchableOpacity key={c} testID={`cat-${c}-btn`}
                            style={[styles.catOption, {
                              backgroundColor: isActive ? `${catColor}15` : isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
                              borderColor: isActive ? catColor : colors.border,
                            }]}
                            onPress={() => setForm(p => ({ ...p, category: c }))}
                          >
                            <MaterialCommunityIcons name={getCategoryIcon(c) as any} size={18} color={isActive ? catColor : colors.textSecondary} />
                            <Text style={[styles.catOptionText, { color: isActive ? catColor : colors.textPrimary }]}>{c}</Text>
                          </TouchableOpacity>
                        );
                      })}
                    </View>

                    <TouchableOpacity testID="step1-next"
                      style={[styles.nextBtn, { backgroundColor: form.amount && form.category ? colors.primary : colors.border }]}
                      onPress={() => { if (form.amount && form.category) setModalStep(2); }}
                    >
                      <Text style={styles.nextBtnText}>Continue</Text>
                      <MaterialCommunityIcons name="arrow-right" size={18} color="#fff" />
                    </TouchableOpacity>
                  </View>
                )}

                {/* ── STEP 2: Description + Date + Notes ── */}
                {modalStep === 2 && (
                  <View>
                    <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>Description</Text>
                    <TextInput testID="description-input"
                      style={[styles.textField, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                      value={form.description}
                      onChangeText={v => setForm(p => ({ ...p, description: v }))}
                      placeholder="e.g., Swiggy order, Axis Bluechip SIP"
                      placeholderTextColor={colors.textSecondary}
                    />

                    <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>Date</Text>
                    <TextInput testID="date-input"
                      style={[styles.textField, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                      value={form.date}
                      onChangeText={v => setForm(p => ({ ...p, date: v }))}
                      placeholder="YYYY-MM-DD (blank = today)"
                      placeholderTextColor={colors.textSecondary}
                    />

                    <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>Notes (optional)</Text>
                    <TextInput testID="notes-input"
                      style={[styles.textField, styles.notesField, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                      value={form.notes}
                      onChangeText={v => setForm(p => ({ ...p, notes: v }))}
                      placeholder="Any additional details..."
                      placeholderTextColor={colors.textSecondary}
                      multiline
                      numberOfLines={3}
                    />

                    <View style={styles.stepBtnRow}>
                      <TouchableOpacity testID="step2-back" style={[styles.backStepBtn, { borderColor: colors.border }]} onPress={() => setModalStep(1)}>
                        <MaterialCommunityIcons name="arrow-left" size={18} color={colors.textSecondary} />
                        <Text style={[styles.backStepText, { color: colors.textSecondary }]}>Back</Text>
                      </TouchableOpacity>
                      <TouchableOpacity testID="step2-next"
                        style={[styles.nextBtn, { flex: 1, backgroundColor: form.description ? colors.primary : colors.border }]}
                        onPress={() => { if (form.description) setModalStep(3); }}
                      >
                        <Text style={styles.nextBtnText}>Continue</Text>
                        <MaterialCommunityIcons name="arrow-right" size={18} color="#fff" />
                      </TouchableOpacity>
                    </View>
                  </View>
                )}

                {/* ── STEP 3: Recurring + Split + Save ── */}
                {modalStep === 3 && (
                  <View>
                    {/* Recurring Toggle */}
                    <View style={[styles.optionCard, { backgroundColor: colors.background, borderColor: colors.border }]}>
                      <View style={styles.optionRow}>
                        <View style={[styles.optionIcon, { backgroundColor: isDark ? '#312E81' : '#E0E7FF' }]}>
                          <MaterialCommunityIcons name="repeat" size={20} color={colors.investment} />
                        </View>
                        <View style={styles.optionInfo}>
                          <Text style={[styles.optionTitle, { color: colors.textPrimary }]}>Recurring Transaction</Text>
                          <Text style={[styles.optionDesc, { color: colors.textSecondary }]}>Repeats automatically</Text>
                        </View>
                        <Switch
                          testID="recurring-switch"
                          value={form.is_recurring}
                          onValueChange={v => setForm(p => ({ ...p, is_recurring: v }))}
                          trackColor={{ false: colors.border, true: `${colors.investment}60` }}
                          thumbColor={form.is_recurring ? colors.investment : '#ccc'}
                        />
                      </View>
                      {form.is_recurring && (
                        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.freqScroll}>
                          {RECURRING_FREQ.map(freq => (
                            <TouchableOpacity key={freq} testID={`freq-${freq}`}
                              style={[styles.freqChip, {
                                backgroundColor: form.recurring_frequency === freq ? colors.investment : 'transparent',
                                borderColor: form.recurring_frequency === freq ? colors.investment : colors.border,
                              }]}
                              onPress={() => setForm(p => ({ ...p, recurring_frequency: freq }))}
                            >
                              <Text style={{ fontSize: 13, color: form.recurring_frequency === freq ? '#fff' : colors.textSecondary }}>
                                {freq}
                              </Text>
                            </TouchableOpacity>
                          ))}
                        </ScrollView>
                      )}
                    </View>

                    {/* Split Toggle */}
                    <View style={[styles.optionCard, { backgroundColor: colors.background, borderColor: colors.border }]}>
                      <View style={styles.optionRow}>
                        <View style={[styles.optionIcon, { backgroundColor: isDark ? '#78350F' : '#FEF3C7' }]}>
                          <MaterialCommunityIcons name="call-split" size={20} color={colors.warning} />
                        </View>
                        <View style={styles.optionInfo}>
                          <Text style={[styles.optionTitle, { color: colors.textPrimary }]}>Split Expense</Text>
                          <Text style={[styles.optionDesc, { color: colors.textSecondary }]}>Divide among people</Text>
                        </View>
                        <Switch
                          testID="split-switch"
                          value={form.is_split}
                          onValueChange={v => setForm(p => ({ ...p, is_split: v }))}
                          trackColor={{ false: colors.border, true: `${colors.warning}60` }}
                          thumbColor={form.is_split ? colors.warning : '#ccc'}
                        />
                      </View>
                      {form.is_split && (
                        <View style={styles.splitRow}>
                          <Text style={[styles.splitLabel, { color: colors.textSecondary }]}>Number of people:</Text>
                          <View style={styles.splitControls}>
                            <TouchableOpacity testID="split-minus"
                              style={[styles.splitBtn, { borderColor: colors.border }]}
                              onPress={() => setForm(p => ({ ...p, split_count: String(Math.max(2, parseInt(p.split_count) - 1)) }))}
                            >
                              <MaterialCommunityIcons name="minus" size={18} color={colors.textPrimary} />
                            </TouchableOpacity>
                            <Text style={[styles.splitCount, { color: colors.textPrimary }]}>{form.split_count}</Text>
                            <TouchableOpacity testID="split-plus"
                              style={[styles.splitBtn, { borderColor: colors.border }]}
                              onPress={() => setForm(p => ({ ...p, split_count: String(parseInt(p.split_count) + 1) }))}
                            >
                              <MaterialCommunityIcons name="plus" size={18} color={colors.textPrimary} />
                            </TouchableOpacity>
                          </View>
                          <Text style={[styles.splitEach, { color: colors.warning }]}>
                            Each pays: {formatINRShort(parseFloat(form.amount || '0') / (parseInt(form.split_count) || 1))}
                          </Text>
                        </View>
                      )}
                    </View>

                    {/* Summary */}
                    <View style={[styles.saveSummary, {
                      backgroundColor: isDark ? 'rgba(16,185,129,0.08)' : 'rgba(5,150,105,0.05)',
                      borderColor: isDark ? 'rgba(16,185,129,0.2)' : 'rgba(5,150,105,0.15)',
                    }]}>
                      <Text style={[styles.summaryRow, { color: colors.textSecondary }]}>
                        {form.type.charAt(0).toUpperCase() + form.type.slice(1)} · {form.category}
                      </Text>
                      <Text style={[styles.summaryAmount, { color: colors.textPrimary }]}>{formatINR(parseFloat(form.amount || '0'))}</Text>
                      <Text style={[styles.summaryRow, { color: colors.textSecondary }]}>{form.description}</Text>
                    </View>

                    <View style={styles.stepBtnRow}>
                      <TouchableOpacity testID="step3-back" style={[styles.backStepBtn, { borderColor: colors.border }]} onPress={() => setModalStep(2)}>
                        <MaterialCommunityIcons name="arrow-left" size={18} color={colors.textSecondary} />
                        <Text style={[styles.backStepText, { color: colors.textSecondary }]}>Back</Text>
                      </TouchableOpacity>
                      <TouchableOpacity testID="save-transaction-btn"
                        style={[styles.saveBtn, { flex: 1, backgroundColor: colors.primary }]}
                        onPress={handleSave}
                        disabled={saving}
                      >
                        {saving ? <ActivityIndicator color="#fff" /> : (
                          <>
                            <MaterialCommunityIcons name="check" size={18} color="#fff" />
                            <Text style={styles.saveBtnText}>Save Transaction</Text>
                          </>
                        )}
                      </TouchableOpacity>
                    </View>
                  </View>
                )}
              </ScrollView>
            </View>
          </KeyboardAvoidingView>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

function SummaryPill({ label, amount, color, colors }: { label: string; amount: number; color: string; colors: any }) {
  return (
    <View style={styles.summaryPill}>
      <View style={[styles.summaryPillDot, { backgroundColor: color }]} />
      <View>
        <Text style={[styles.summaryPillAmount, { color }]}>{formatINRShort(amount)}</Text>
        <Text style={[styles.summaryPillLabel, { color: colors.textSecondary }]}>{label}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },

  // Header
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 20, paddingTop: 12, paddingBottom: 12, borderBottomWidth: 1 },
  title: { fontSize: 26, fontWeight: '800', letterSpacing: -0.8 },
  subtitle: { fontSize: 13, marginTop: 2 },
  headerActions: { flexDirection: 'row', gap: 10 },
  iconBtn: { width: 44, height: 44, borderRadius: 14, justifyContent: 'center', alignItems: 'center', borderWidth: 1 },
  addBtn: { width: 44, height: 44, borderRadius: 14, justifyContent: 'center', alignItems: 'center' },

  // Search
  searchBar: { flexDirection: 'row', alignItems: 'center', marginHorizontal: 16, marginTop: 10, paddingHorizontal: 14, height: 48, borderRadius: 14, borderWidth: 1, gap: 10 },
  searchInput: { flex: 1, fontSize: 15, height: '100%' },

  // Filters
  filterRow: { flexDirection: 'row', paddingHorizontal: 16, borderBottomWidth: 1 },
  filterTab: { flex: 1, paddingVertical: 12, alignItems: 'center' },
  filterLabel: { fontSize: 14, fontWeight: '600' },

  // Category Chips
  catChipScroll: { maxHeight: 44 },
  catChipContainer: { paddingHorizontal: 16, gap: 8, paddingVertical: 8 },
  catChip: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 12, paddingVertical: 7, borderRadius: 20, borderWidth: 1 },
  catChipText: { fontSize: 12, fontWeight: '600' },

  // Summary Strip
  summaryStrip: { flexDirection: 'row', marginHorizontal: 16, marginTop: 6, marginBottom: 4, paddingVertical: 10, paddingHorizontal: 4, borderRadius: 16, borderWidth: 1, justifyContent: 'space-around' },
  summaryPill: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  summaryPillDot: { width: 8, height: 8, borderRadius: 4 },
  summaryPillAmount: { fontSize: 14, fontWeight: '800' },
  summaryPillLabel: { fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.3 },
  summaryDivider: { width: 1, height: 30 },

  // List
  list: { paddingHorizontal: 16, paddingTop: 4 },

  // Date Header
  dateHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 10, marginTop: 6 },
  dateLabel: { fontSize: 15, fontWeight: '700' },
  dateSublabel: { fontSize: 12 },

  // Transaction Card
  txnCard: { flexDirection: 'row', alignItems: 'center', padding: 14, borderRadius: 18, borderWidth: 1, marginBottom: 8, gap: 12 },
  txnIconWrap: { width: 46, height: 46, borderRadius: 14, justifyContent: 'center', alignItems: 'center' },
  txnBody: { flex: 1 },
  txnDesc: { fontSize: 15, fontWeight: '600' },
  txnMeta: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 5 },
  txnCatBadge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 6 },
  txnCatText: { fontSize: 11, fontWeight: '600' },
  txnBadge: { flexDirection: 'row', alignItems: 'center', gap: 3, paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6 },
  txnBadgeText: { fontSize: 10, fontWeight: '600' },
  txnRight: { alignItems: 'flex-end' },
  txnAmount: { fontSize: 16, fontWeight: '800', letterSpacing: -0.3 },
  txnSplitAmt: { fontSize: 11, marginTop: 2 },

  // Empty State
  emptyState: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingTop: 60, paddingHorizontal: 40 },
  emptyIcon: { width: 96, height: 96, borderRadius: 48, justifyContent: 'center', alignItems: 'center', marginBottom: 16 },
  emptyTitle: { fontSize: 18, fontWeight: '700', marginBottom: 8 },
  emptySubtitle: { fontSize: 14, textAlign: 'center', lineHeight: 20, marginBottom: 20 },
  emptyAddBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 20, paddingVertical: 12, borderRadius: 999 },
  emptyAddText: { color: '#fff', fontSize: 14, fontWeight: '700' },

  // Modal
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modalKav: { maxHeight: '92%' },
  modalContent: { borderTopLeftRadius: 28, borderTopRightRadius: 28, padding: 24, paddingBottom: 40, maxHeight: '100%' },
  modalHandle: { width: 40, height: 4, borderRadius: 2, backgroundColor: '#CBD5E1', alignSelf: 'center', marginBottom: 16 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  modalTitle: { fontSize: 22, fontWeight: '800' },
  modalHeaderRight: { flexDirection: 'row', alignItems: 'center', gap: 14 },
  stepIndicator: { flexDirection: 'row', gap: 4, alignItems: 'center' },
  stepDot: { height: 4, borderRadius: 2 },

  // Type Selector
  typeRow: { flexDirection: 'row', gap: 10, marginBottom: 20 },
  typeCard: { flex: 1, alignItems: 'center', gap: 8, paddingVertical: 16, borderRadius: 16, borderWidth: 1.5 },
  typeCardLabel: { fontSize: 13, fontWeight: '700' },

  // Fields
  fieldLabel: { fontSize: 12, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8, marginTop: 4 },
  amountBox: { flexDirection: 'row', alignItems: 'center', height: 64, borderRadius: 18, borderWidth: 1.5, paddingHorizontal: 18, marginBottom: 16 },
  rupee: { fontSize: 28, fontWeight: '800' },
  amountField: { flex: 1, fontSize: 32, fontWeight: '800', paddingHorizontal: 8, height: '100%' },
  textField: { height: 52, borderRadius: 14, borderWidth: 1, paddingHorizontal: 16, fontSize: 15, marginBottom: 14 },
  notesField: { height: 80, paddingTop: 14, textAlignVertical: 'top' },

  // Category Grid
  catGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 20 },
  catOption: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 12, paddingVertical: 10, borderRadius: 12, borderWidth: 1 },
  catOptionText: { fontSize: 13, fontWeight: '600' },

  // Step buttons
  nextBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, height: 54, borderRadius: 999 },
  nextBtnText: { color: '#fff', fontSize: 16, fontWeight: '700' },
  stepBtnRow: { flexDirection: 'row', gap: 10, marginTop: 8 },
  backStepBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 4, paddingHorizontal: 20, height: 54, borderRadius: 999, borderWidth: 1 },
  backStepText: { fontSize: 14, fontWeight: '600' },

  // Options
  optionCard: { borderRadius: 18, padding: 16, borderWidth: 1, marginBottom: 12 },
  optionRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  optionIcon: { width: 40, height: 40, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  optionInfo: { flex: 1 },
  optionTitle: { fontSize: 15, fontWeight: '600' },
  optionDesc: { fontSize: 12, marginTop: 2 },
  freqScroll: { marginTop: 12 },
  freqChip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20, borderWidth: 1, marginRight: 8 },

  // Split
  splitRow: { marginTop: 12, gap: 10 },
  splitLabel: { fontSize: 13 },
  splitControls: { flexDirection: 'row', alignItems: 'center', gap: 14 },
  splitBtn: { width: 36, height: 36, borderRadius: 18, borderWidth: 1, justifyContent: 'center', alignItems: 'center' },
  splitCount: { fontSize: 20, fontWeight: '800', minWidth: 30, textAlign: 'center' },
  splitEach: { fontSize: 14, fontWeight: '700' },

  // Save Summary
  saveSummary: { borderRadius: 16, padding: 16, borderWidth: 1, marginBottom: 16, alignItems: 'center' },
  summaryRow: { fontSize: 13 },
  summaryAmount: { fontSize: 28, fontWeight: '800', marginVertical: 4, letterSpacing: -1 },

  // Save Button
  saveBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, height: 56, borderRadius: 999 },
  saveBtnText: { color: '#fff', fontSize: 17, fontWeight: '700' },
});
