import { useState } from 'react';
import { Alert } from 'react-native';
import { apiRequest } from '../../utils/api';
import type { RecurringTransaction } from '../../components/investments/types';

export function useSIPManager(token: string | null, fetchData: () => void) {
  const [showSipModal, setShowSipModal] = useState(false);
  const [editSip, setEditSip] = useState<RecurringTransaction | null>(null);
  const [sipForm, setSipForm] = useState({
    name: '',
    amount: '',
    frequency: 'monthly',
    category: 'SIP',
    start_date: '',
    day_of_month: '5',
    notes: '',
  });
  const [saving, setSaving] = useState(false);

  const handleAddSip = () => {
    setEditSip(null);
    setSipForm({ name: '', amount: '', frequency: 'monthly', category: 'SIP', start_date: '', day_of_month: '5', notes: '' });
    setShowSipModal(true);
  };

  const handleEditSip = (sip: RecurringTransaction) => {
    setEditSip(sip);
    setSipForm({
      name: sip.name,
      amount: sip.amount.toString(),
      frequency: sip.frequency,
      category: sip.category,
      start_date: sip.start_date,
      day_of_month: sip.day_of_month?.toString() || '5',
      notes: sip.notes || '',
    });
    setShowSipModal(true);
  };

  const handleSaveSip = async () => {
    if (!sipForm.name.trim() || !sipForm.amount || !sipForm.start_date) {
      Alert.alert('Missing Info', 'Please fill all required fields');
      return;
    }
    setSaving(true);
    try {
      const body = {
        name: sipForm.name.trim(),
        amount: parseFloat(sipForm.amount),
        frequency: sipForm.frequency,
        category: sipForm.category,
        start_date: sipForm.start_date,
        day_of_month: parseInt(sipForm.day_of_month),
        notes: sipForm.notes,
      };
      if (editSip) {
        await apiRequest(`/recurring/${editSip.id}`, { token, method: 'PUT', body });
      } else {
        await apiRequest('/recurring', { token, method: 'POST', body });
      }
      setShowSipModal(false);
      fetchData();
    } catch (e: any) {
      Alert.alert('Error', e.message || 'Failed to save SIP');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteSip = (sipId: string) => {
    Alert.alert('Delete SIP?', 'This recurring investment will be removed.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          try {
            await apiRequest(`/recurring/${sipId}`, { method: 'DELETE', token });
            fetchData();
          } catch (e: any) {
            Alert.alert('Error', e.message || 'Failed to delete SIP');
          }
        },
      },
    ]);
  };

  return {
    showSipModal,
    setShowSipModal,
    editSip,
    sipForm,
    setSipForm,
    saving,
    handleAddSip,
    handleEditSip,
    handleSaveSip,
    handleDeleteSip,
  };
}
