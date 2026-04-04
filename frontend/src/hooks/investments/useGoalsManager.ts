import { useState } from 'react';
import { Alert } from 'react-native';
import { apiRequest } from '../../utils/api';
import type { Goal } from '../../components/investments/types';

export function useGoalsManager(token: string | null, fetchData: () => void) {
  const [showGoalModal, setShowGoalModal] = useState(false);
  const [editGoal, setEditGoal] = useState<Goal | null>(null);
  const [goalForm, setGoalForm] = useState({
    title: '',
    target_amount: '',
    current_amount: '0',
    deadline: '',
    category: 'Safety',
  });
  const [saving, setSaving] = useState(false);

  const handleAddGoal = () => {
    setEditGoal(null);
    setGoalForm({ title: '', target_amount: '', current_amount: '0', deadline: '', category: 'Safety' });
    setShowGoalModal(true);
  };

  const handleEditGoal = (goal: Goal) => {
    setEditGoal(goal);
    setGoalForm({
      title: goal.title,
      target_amount: goal.target_amount.toString(),
      current_amount: goal.current_amount.toString(),
      deadline: goal.deadline,
      category: goal.category,
    });
    setShowGoalModal(true);
  };

  const handleSaveGoal = async () => {
    if (!goalForm.title.trim() || !goalForm.target_amount || !goalForm.deadline) {
      Alert.alert('Missing Info', 'Please fill all required fields');
      return;
    }
    setSaving(true);
    try {
      const body = {
        title: goalForm.title.trim(),
        target_amount: parseFloat(goalForm.target_amount),
        current_amount: parseFloat(goalForm.current_amount || '0'),
        deadline: goalForm.deadline,
        category: goalForm.category,
      };
      if (editGoal) {
        await apiRequest(`/goals/${editGoal.id}`, { token, method: 'PUT', body });
      } else {
        await apiRequest('/goals', { token, method: 'POST', body });
      }
      setShowGoalModal(false);
      fetchData();
    } catch (e: any) {
      Alert.alert('Error', e.message || 'Failed to save goal');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteGoal = (goalId: string) => {
    Alert.alert('Delete Goal?', 'This goal will be permanently deleted.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          try {
            await apiRequest(`/goals/${goalId}`, { method: 'DELETE', token });
            fetchData();
          } catch (e: any) {
            Alert.alert('Error', e.message || 'Failed to delete goal');
          }
        },
      },
    ]);
  };

  return {
    showGoalModal,
    setShowGoalModal,
    editGoal,
    goalForm,
    setGoalForm,
    saving,
    handleAddGoal,
    handleEditGoal,
    handleSaveGoal,
    handleDeleteGoal,
  };
}
