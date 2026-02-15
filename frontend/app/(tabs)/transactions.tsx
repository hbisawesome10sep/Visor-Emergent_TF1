import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, TextInput, Modal,
  RefreshControl, ActivityIndicator, Alert, KeyboardAvoidingView, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useAuth } from '../../src/context/AuthContext';
import { useTheme } from '../../src/context/ThemeContext';
import { apiRequest } from '../../src/utils/api';
import { formatINR, getCategoryColor } from '../../src/utils/formatters';

const EXPENSE_CATS = ['Rent', 'Groceries', 'Food', 'Transport', 'Shopping', 'Utilities', 'Entertainment', 'Health', 'EMI', 'Other'];
const INCOME_CATS = ['Salary', 'Freelance', 'Bonus', 'Interest', 'Dividend', 'Other'];
const INVEST_CATS = ['SIP', 'PPF', 'Stocks', 'Mutual Funds', 'FD', 'Gold', 'NPS', 'Other'];

type Transaction = {
  id: string; type: string; amount: number; category: string;
  description: string; date: string; created_at: string;
};

export default function TransactionsScreen() {
  const { token } = useAuth();
  const { colors, isDark } = useTheme();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [filter, setFilter] = useState<string>('all');
  const [form, setForm] = useState({ type: 'expense', amount: '', category: '', description: '', date: '' });
  const [saving, setSaving] = useState(false);

  const fetchTxns = useCallback(async () => {
    if (!token) return;
    try {
      const params = filter !== 'all' ? `?type=${filter}` : '';
      const data = await apiRequest(`/transactions${params}`, { token });
      setTransactions(data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); setRefreshing(false); }
  }, [token, filter]);

  useEffect(() => { fetchTxns(); }, [fetchTxns]);

  const onRefresh = () => { setRefreshing(true); fetchTxns(); };

  const handleAdd = async () => {
    if (!form.amount || !form.category || !form.description) {
      Alert.alert('Error', 'Please fill all fields'); return;
    }
    setSaving(true);
    try {
      const today = new Date().toISOString().split('T')[0];
      await apiRequest('/transactions', {
        method: 'POST', token,
        body: { ...form, amount: parseFloat(form.amount), date: form.date || today },
      });
      setShowModal(false);
      setForm({ type: 'expense', amount: '', category: '', description: '', date: '' });
      fetchTxns();
    } catch (e: any) { Alert.alert('Error', e.message); }
    finally { setSaving(false); }
  };

  const handleDelete = (id: string) => {
    Alert.alert('Delete', 'Remove this transaction?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: async () => {
        await apiRequest(`/transactions/${id}`, { method: 'DELETE', token });
        fetchTxns();
      }},
    ]);
  };

  const cats = form.type === 'income' ? INCOME_CATS : form.type === 'investment' ? INVEST_CATS : EXPENSE_CATS;
  const filters = ['all', 'income', 'expense', 'investment'];

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: colors.background }]}>
      {/* Header */}
      <View style={[styles.header, { borderBottomColor: colors.border }]}>
        <Text style={[styles.title, { color: colors.textPrimary }]}>Transactions</Text>
        <TouchableOpacity testID="add-transaction-btn" style={[styles.addBtn, { backgroundColor: colors.primary }]} onPress={() => setShowModal(true)}>
          <MaterialCommunityIcons name="plus" size={22} color="#fff" />
        </TouchableOpacity>
      </View>

      {/* Filters */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.filterScroll} contentContainerStyle={styles.filterContainer}>
        {filters.map(f => (
          <TouchableOpacity
            key={f}
            testID={`filter-${f}-btn`}
            style={[styles.filterChip, {
              backgroundColor: filter === f ? colors.primary : colors.surface,
              borderColor: filter === f ? colors.primary : colors.border,
            }]}
            onPress={() => setFilter(f)}
          >
            <Text style={[styles.filterText, { color: filter === f ? '#fff' : colors.textSecondary }]}>
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {loading ? (
        <View style={styles.center}><ActivityIndicator size="large" color={colors.primary} /></View>
      ) : (
        <ScrollView
          contentContainerStyle={styles.list}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />}
        >
          {transactions.length === 0 ? (
            <View style={styles.empty}>
              <MaterialCommunityIcons name="receipt" size={48} color={colors.textSecondary} />
              <Text style={[styles.emptyText, { color: colors.textSecondary }]}>No transactions yet</Text>
            </View>
          ) : (
            transactions.map(txn => (
              <TouchableOpacity
                key={txn.id}
                testID={`txn-${txn.id}`}
                style={[styles.txnCard, { backgroundColor: colors.surface, borderColor: colors.border }]}
                onLongPress={() => handleDelete(txn.id)}
              >
                <View style={[styles.txnIcon, {
                  backgroundColor: txn.type === 'income' ? (isDark ? '#064E3B' : '#D1FAE5')
                    : txn.type === 'investment' ? (isDark ? '#312E81' : '#E0E7FF')
                    : (isDark ? '#7F1D1D' : '#FEE2E2'),
                }]}>
                  <MaterialCommunityIcons
                    name={txn.type === 'income' ? 'arrow-down' : txn.type === 'investment' ? 'chart-line' : 'arrow-up'}
                    size={20}
                    color={txn.type === 'income' ? colors.income : txn.type === 'investment' ? colors.investment : colors.expense}
                  />
                </View>
                <View style={styles.txnInfo}>
                  <Text style={[styles.txnDesc, { color: colors.textPrimary }]} numberOfLines={1}>{txn.description}</Text>
                  <Text style={[styles.txnMeta, { color: colors.textSecondary }]}>
                    {txn.category} · {txn.date}
                  </Text>
                </View>
                <Text style={[styles.txnAmount, {
                  color: txn.type === 'income' ? colors.income : txn.type === 'investment' ? colors.investment : colors.expense,
                }]}>
                  {txn.type === 'income' ? '+' : '-'}{formatINR(txn.amount)}
                </Text>
              </TouchableOpacity>
            ))
          )}
          <View style={{ height: 100 }} />
        </ScrollView>
      )}

      {/* Add Transaction Modal */}
      <Modal visible={showModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.modalKav}>
            <View style={[styles.modalContent, { backgroundColor: colors.surface }]}>
              <View style={styles.modalHeader}>
                <Text style={[styles.modalTitle, { color: colors.textPrimary }]}>Add Transaction</Text>
                <TouchableOpacity testID="close-modal-btn" onPress={() => setShowModal(false)}>
                  <MaterialCommunityIcons name="close" size={24} color={colors.textSecondary} />
                </TouchableOpacity>
              </View>

              {/* Type Selector */}
              <View style={styles.typeRow}>
                {(['expense', 'income', 'investment'] as const).map(t => (
                  <TouchableOpacity
                    key={t}
                    testID={`type-${t}-btn`}
                    style={[styles.typeBtn, {
                      backgroundColor: form.type === t ? (t === 'income' ? colors.income : t === 'investment' ? colors.investment : colors.expense) : colors.background,
                      borderColor: colors.border,
                    }]}
                    onPress={() => setForm(p => ({ ...p, type: t, category: '' }))}
                  >
                    <Text style={[styles.typeText, { color: form.type === t ? '#fff' : colors.textSecondary }]}>
                      {t.charAt(0).toUpperCase() + t.slice(1)}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>

              {/* Amount */}
              <View style={[styles.modalInput, { borderColor: colors.border, backgroundColor: colors.background }]}>
                <Text style={[styles.rupee, { color: colors.textPrimary }]}>₹</Text>
                <TextInput
                  testID="amount-input"
                  style={[styles.amountInput, { color: colors.textPrimary }]}
                  value={form.amount}
                  onChangeText={v => setForm(p => ({ ...p, amount: v }))}
                  placeholder="0.00"
                  placeholderTextColor={colors.textSecondary}
                  keyboardType="decimal-pad"
                />
              </View>

              {/* Category */}
              <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>Category</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.catScroll}>
                {cats.map(c => (
                  <TouchableOpacity
                    key={c}
                    testID={`cat-${c}-btn`}
                    style={[styles.catChip, {
                      backgroundColor: form.category === c ? colors.primary : colors.background,
                      borderColor: form.category === c ? colors.primary : colors.border,
                    }]}
                    onPress={() => setForm(p => ({ ...p, category: c }))}
                  >
                    <Text style={{ color: form.category === c ? '#fff' : colors.textSecondary, fontSize: 13 }}>{c}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>

              {/* Description */}
              <TextInput
                testID="description-input"
                style={[styles.modalInput, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary, paddingHorizontal: 16 }]}
                value={form.description}
                onChangeText={v => setForm(p => ({ ...p, description: v }))}
                placeholder="Description"
                placeholderTextColor={colors.textSecondary}
              />

              {/* Date */}
              <TextInput
                testID="date-input"
                style={[styles.modalInput, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary, paddingHorizontal: 16 }]}
                value={form.date}
                onChangeText={v => setForm(p => ({ ...p, date: v }))}
                placeholder="YYYY-MM-DD (leave empty for today)"
                placeholderTextColor={colors.textSecondary}
              />

              <TouchableOpacity
                testID="save-transaction-btn"
                style={[styles.saveBtn, { backgroundColor: colors.primary }]}
                onPress={handleAdd}
                disabled={saving}
              >
                {saving ? <ActivityIndicator color="#fff" /> : (
                  <Text style={styles.saveBtnText}>Save Transaction</Text>
                )}
              </TouchableOpacity>
            </View>
          </KeyboardAvoidingView>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 20, paddingVertical: 16, borderBottomWidth: 1 },
  title: { fontSize: 24, fontWeight: '800', letterSpacing: -0.5 },
  addBtn: { width: 44, height: 44, borderRadius: 22, justifyContent: 'center', alignItems: 'center' },
  filterScroll: { maxHeight: 48, paddingVertical: 0 },
  filterContainer: { paddingHorizontal: 20, gap: 8, paddingVertical: 8 },
  filterChip: { paddingHorizontal: 16, paddingVertical: 8, borderRadius: 20, borderWidth: 1 },
  filterText: { fontSize: 13, fontWeight: '600' },
  list: { paddingHorizontal: 20, paddingTop: 8 },
  empty: { alignItems: 'center', paddingTop: 60, gap: 12 },
  emptyText: { fontSize: 15 },

  txnCard: { flexDirection: 'row', alignItems: 'center', padding: 16, borderRadius: 16, borderWidth: 1, marginBottom: 10, gap: 12 },
  txnIcon: { width: 44, height: 44, borderRadius: 14, justifyContent: 'center', alignItems: 'center' },
  txnInfo: { flex: 1 },
  txnDesc: { fontSize: 15, fontWeight: '600' },
  txnMeta: { fontSize: 12, marginTop: 2 },
  txnAmount: { fontSize: 16, fontWeight: '700' },

  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modalKav: { maxHeight: '90%' },
  modalContent: { borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 24, paddingBottom: 40 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  modalTitle: { fontSize: 20, fontWeight: '700' },
  typeRow: { flexDirection: 'row', gap: 8, marginBottom: 20 },
  typeBtn: { flex: 1, paddingVertical: 12, borderRadius: 14, borderWidth: 1, alignItems: 'center' },
  typeText: { fontSize: 14, fontWeight: '600' },
  modalInput: { height: 52, borderRadius: 14, borderWidth: 1, flexDirection: 'row', alignItems: 'center', marginBottom: 14 },
  rupee: { fontSize: 20, fontWeight: '700', paddingLeft: 16 },
  amountInput: { flex: 1, fontSize: 24, fontWeight: '700', paddingHorizontal: 8, height: '100%' },
  fieldLabel: { fontSize: 12, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8 },
  catScroll: { maxHeight: 40, marginBottom: 14 },
  catChip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 16, borderWidth: 1, marginRight: 8 },
  saveBtn: { height: 56, borderRadius: 999, justifyContent: 'center', alignItems: 'center', marginTop: 8 },
  saveBtnText: { color: '#fff', fontSize: 17, fontWeight: '700' },
});
