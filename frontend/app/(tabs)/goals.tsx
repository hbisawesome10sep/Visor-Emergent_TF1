import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, Modal, TextInput,
  RefreshControl, ActivityIndicator, Alert, KeyboardAvoidingView, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useAuth } from '../../src/context/AuthContext';
import { useTheme } from '../../src/context/ThemeContext';
import { apiRequest } from '../../src/utils/api';
import { formatINR, formatINRShort } from '../../src/utils/formatters';

const GOAL_CATS = ['Safety', 'Travel', 'Purchase', 'Property', 'Education', 'Retirement', 'Wedding', 'Other'];

type Goal = {
  id: string; title: string; target_amount: number; current_amount: number;
  deadline: string; category: string; created_at: string;
};

export default function GoalsScreen() {
  const { token } = useAuth();
  const { colors, isDark } = useTheme();
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editGoal, setEditGoal] = useState<Goal | null>(null);
  const [form, setForm] = useState({ title: '', target_amount: '', current_amount: '', deadline: '', category: '' });
  const [saving, setSaving] = useState(false);

  const fetchGoals = useCallback(async () => {
    if (!token) return;
    try {
      const data = await apiRequest('/goals', { token });
      setGoals(data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); setRefreshing(false); }
  }, [token]);

  useEffect(() => { fetchGoals(); }, [fetchGoals]);

  const openAdd = () => {
    setEditGoal(null);
    setForm({ title: '', target_amount: '', current_amount: '0', deadline: '', category: '' });
    setShowModal(true);
  };

  const openEdit = (g: Goal) => {
    setEditGoal(g);
    setForm({
      title: g.title,
      target_amount: g.target_amount.toString(),
      current_amount: g.current_amount.toString(),
      deadline: g.deadline,
      category: g.category,
    });
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!form.title || !form.target_amount || !form.category) {
      Alert.alert('Error', 'Please fill required fields'); return;
    }
    setSaving(true);
    try {
      const body = {
        title: form.title,
        target_amount: parseFloat(form.target_amount),
        current_amount: parseFloat(form.current_amount || '0'),
        deadline: form.deadline || '2026-12-31',
        category: form.category,
      };
      if (editGoal) {
        await apiRequest(`/goals/${editGoal.id}`, { method: 'PUT', token, body });
      } else {
        await apiRequest('/goals', { method: 'POST', token, body });
      }
      setShowModal(false);
      fetchGoals();
    } catch (e: any) { Alert.alert('Error', e.message); }
    finally { setSaving(false); }
  };

  const handleDelete = (id: string) => {
    Alert.alert('Delete Goal', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: async () => {
        await apiRequest(`/goals/${id}`, { method: 'DELETE', token });
        fetchGoals();
      }},
    ]);
  };

  const totalTarget = goals.reduce((s, g) => s + g.target_amount, 0);
  const totalCurrent = goals.reduce((s, g) => s + g.current_amount, 0);
  const overallProgress = totalTarget > 0 ? (totalCurrent / totalTarget) * 100 : 0;

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: colors.background }]}>
      <View style={[styles.header, { borderBottomColor: colors.border }]}>
        <Text style={[styles.title, { color: colors.textPrimary }]}>Financial Goals</Text>
        <TouchableOpacity testID="add-goal-btn" style={[styles.addBtn, { backgroundColor: colors.primary }]} onPress={openAdd}>
          <MaterialCommunityIcons name="plus" size={22} color="#fff" />
        </TouchableOpacity>
      </View>

      {loading ? (
        <View style={styles.center}><ActivityIndicator size="large" color={colors.primary} /></View>
      ) : (
        <ScrollView
          contentContainerStyle={styles.scroll}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); fetchGoals(); }} tintColor={colors.primary} />}
        >
          {/* Overall Progress */}
          {goals.length > 0 && (
            <View style={[styles.overviewCard, { backgroundColor: colors.primary }]}>
              <Text style={styles.overviewLabel}>Overall Goal Progress</Text>
              <Text style={styles.overviewAmount}>{formatINRShort(totalCurrent)} / {formatINRShort(totalTarget)}</Text>
              <View style={styles.progressBg}>
                <View style={[styles.progressFill, { width: `${Math.min(overallProgress, 100)}%` }]} />
              </View>
              <Text style={styles.overviewPercent}>{overallProgress.toFixed(1)}% Complete</Text>
            </View>
          )}

          {goals.length === 0 ? (
            <View style={styles.empty}>
              <MaterialCommunityIcons name="target" size={48} color={colors.textSecondary} />
              <Text style={[styles.emptyText, { color: colors.textSecondary }]}>No goals yet. Start planning!</Text>
            </View>
          ) : (
            goals.map(goal => {
              const progress = goal.target_amount > 0 ? (goal.current_amount / goal.target_amount) * 100 : 0;
              const progressColor = progress >= 75 ? colors.success : progress >= 40 ? colors.warning : colors.error;
              return (
                <TouchableOpacity
                  key={goal.id}
                  testID={`goal-${goal.id}`}
                  style={[styles.goalCard, { backgroundColor: colors.surface, borderColor: colors.border }]}
                  onPress={() => openEdit(goal)}
                  onLongPress={() => handleDelete(goal.id)}
                >
                  <View style={styles.goalHeader}>
                    <View style={[styles.goalIcon, { backgroundColor: isDark ? colors.primaryLight : '#D1FAE5' }]}>
                      <MaterialCommunityIcons name="target" size={22} color={colors.primary} />
                    </View>
                    <View style={styles.goalInfo}>
                      <Text style={[styles.goalTitle, { color: colors.textPrimary }]}>{goal.title}</Text>
                      <Text style={[styles.goalCat, { color: colors.textSecondary }]}>{goal.category} · Due {goal.deadline}</Text>
                    </View>
                  </View>
                  <View style={styles.goalProgress}>
                    <View style={styles.goalAmounts}>
                      <Text style={[styles.goalCurrent, { color: progressColor }]}>{formatINRShort(goal.current_amount)}</Text>
                      <Text style={[styles.goalTarget, { color: colors.textSecondary }]}>of {formatINRShort(goal.target_amount)}</Text>
                    </View>
                    <View style={[styles.goalBar, { backgroundColor: colors.border }]}>
                      <View style={[styles.goalBarFill, { width: `${Math.min(progress, 100)}%`, backgroundColor: progressColor }]} />
                    </View>
                    <Text style={[styles.goalPercent, { color: progressColor }]}>{progress.toFixed(0)}%</Text>
                  </View>
                </TouchableOpacity>
              );
            })
          )}
          <View style={{ height: 100 }} />
        </ScrollView>
      )}

      {/* Add/Edit Modal */}
      <Modal visible={showModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.modalKav}>
            <View style={[styles.modalContent, { backgroundColor: colors.surface }]}>
              <View style={styles.modalHeader}>
                <Text style={[styles.modalTitle, { color: colors.textPrimary }]}>
                  {editGoal ? 'Edit Goal' : 'New Goal'}
                </Text>
                <TouchableOpacity testID="close-goal-modal" onPress={() => setShowModal(false)}>
                  <MaterialCommunityIcons name="close" size={24} color={colors.textSecondary} />
                </TouchableOpacity>
              </View>

              <TextInput
                testID="goal-title-input"
                style={[styles.input, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                value={form.title}
                onChangeText={v => setForm(p => ({ ...p, title: v }))}
                placeholder="Goal title (e.g., Emergency Fund)"
                placeholderTextColor={colors.textSecondary}
              />

              <View style={styles.row}>
                <TextInput
                  testID="goal-target-input"
                  style={[styles.input, styles.halfInput, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                  value={form.target_amount}
                  onChangeText={v => setForm(p => ({ ...p, target_amount: v }))}
                  placeholder="Target ₹"
                  placeholderTextColor={colors.textSecondary}
                  keyboardType="decimal-pad"
                />
                <TextInput
                  testID="goal-current-input"
                  style={[styles.input, styles.halfInput, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                  value={form.current_amount}
                  onChangeText={v => setForm(p => ({ ...p, current_amount: v }))}
                  placeholder="Saved ₹"
                  placeholderTextColor={colors.textSecondary}
                  keyboardType="decimal-pad"
                />
              </View>

              <TextInput
                testID="goal-deadline-input"
                style={[styles.input, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                value={form.deadline}
                onChangeText={v => setForm(p => ({ ...p, deadline: v }))}
                placeholder="Deadline (YYYY-MM-DD)"
                placeholderTextColor={colors.textSecondary}
              />

              <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>Category</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.catScroll}>
                {GOAL_CATS.map(c => (
                  <TouchableOpacity
                    key={c}
                    testID={`goal-cat-${c}`}
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

              <TouchableOpacity
                testID="save-goal-btn"
                style={[styles.saveBtn, { backgroundColor: colors.primary }]}
                onPress={handleSave}
                disabled={saving}
              >
                {saving ? <ActivityIndicator color="#fff" /> : (
                  <Text style={styles.saveBtnText}>{editGoal ? 'Update Goal' : 'Create Goal'}</Text>
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
  scroll: { paddingHorizontal: 20, paddingTop: 16 },
  empty: { alignItems: 'center', paddingTop: 60, gap: 12 },
  emptyText: { fontSize: 15 },

  overviewCard: { borderRadius: 20, padding: 20, marginBottom: 16 },
  overviewLabel: { color: 'rgba(255,255,255,0.8)', fontSize: 13, fontWeight: '500' },
  overviewAmount: { color: '#fff', fontSize: 22, fontWeight: '800', marginTop: 4, letterSpacing: -0.5 },
  progressBg: { height: 8, backgroundColor: 'rgba(255,255,255,0.3)', borderRadius: 4, marginTop: 16, overflow: 'hidden' },
  progressFill: { height: '100%', backgroundColor: '#fff', borderRadius: 4 },
  overviewPercent: { color: 'rgba(255,255,255,0.9)', fontSize: 13, fontWeight: '600', marginTop: 8 },

  goalCard: { borderRadius: 20, padding: 18, borderWidth: 1, marginBottom: 12 },
  goalHeader: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 14 },
  goalIcon: { width: 44, height: 44, borderRadius: 14, justifyContent: 'center', alignItems: 'center' },
  goalInfo: { flex: 1 },
  goalTitle: { fontSize: 16, fontWeight: '700' },
  goalCat: { fontSize: 12, marginTop: 2 },
  goalProgress: {},
  goalAmounts: { flexDirection: 'row', alignItems: 'baseline', gap: 6, marginBottom: 8 },
  goalCurrent: { fontSize: 18, fontWeight: '800' },
  goalTarget: { fontSize: 13 },
  goalBar: { height: 8, borderRadius: 4, overflow: 'hidden', marginBottom: 6 },
  goalBarFill: { height: '100%', borderRadius: 4 },
  goalPercent: { fontSize: 13, fontWeight: '700', textAlign: 'right' },

  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modalKav: { maxHeight: '90%' },
  modalContent: { borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 24, paddingBottom: 40 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  modalTitle: { fontSize: 20, fontWeight: '700' },
  input: { height: 52, borderRadius: 14, borderWidth: 1, paddingHorizontal: 16, fontSize: 15, marginBottom: 14 },
  row: { flexDirection: 'row', gap: 10 },
  halfInput: { flex: 1 },
  fieldLabel: { fontSize: 12, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8 },
  catScroll: { maxHeight: 40, marginBottom: 14 },
  catChip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 16, borderWidth: 1, marginRight: 8 },
  saveBtn: { height: 56, borderRadius: 999, justifyContent: 'center', alignItems: 'center', marginTop: 8 },
  saveBtnText: { color: '#fff', fontSize: 17, fontWeight: '700' },
});
