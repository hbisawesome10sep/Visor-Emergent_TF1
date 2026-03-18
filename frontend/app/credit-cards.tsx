import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, TextInput,
  Modal, Alert, RefreshControl, ActivityIndicator, Platform,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useTheme } from '../src/context/ThemeContext';
import { apiRequest } from '../src/utils/api';
import { useAuth } from '../src/context/AuthContext';
import { formatINR, formatINRShort } from '../src/utils/formatters';
import { DueCalendarSection } from '../src/components/credit-cards/DueCalendarSection';
import { InterestCalculator } from '../src/components/credit-cards/InterestCalculator';
import { RewardsTracker } from '../src/components/credit-cards/RewardsTracker';
import { CardRecommender } from '../src/components/credit-cards/CardRecommender';

const CC_CATEGORIES = ['Food & Dining', 'Shopping', 'Travel', 'Entertainment', 'Utilities', 'Healthcare', 'Fuel', 'Education', 'EMI', 'Subscriptions', 'Other'];
const TXN_TYPES = [
  { key: 'expense', label: 'Expense', icon: 'credit-card-minus', color: '#EF4444' },
  { key: 'payment', label: 'Payment', icon: 'credit-card-check', color: '#10B981' },
];

type CreditCard = {
  id: string;
  card_name: string;
  issuer: string;
  last_four: string;
  credit_limit: number;
  billing_cycle_day: number;
  due_day: number;
  is_default: boolean;
  is_active: boolean;
  current_outstanding: number;
  available_credit: number;
};

export default function CreditCardsScreen() {
  const { colors, isDark } = useTheme();
  const { token } = useAuth();
  const router = useRouter();
  
  const [cards, setCards] = useState<CreditCard[]>([]);
  const [issuers, setIssuers] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingCard, setEditingCard] = useState<CreditCard | null>(null);
  
  // Add Transaction state
  const [showTxnModal, setShowTxnModal] = useState(false);
  const [savingTxn, setSavingTxn] = useState(false);
  const [txnForm, setTxnForm] = useState({
    card_id: '',
    type: 'expense',
    amount: '',
    description: '',
    merchant: '',
    category: 'Food & Dining',
    date: new Date().toISOString().split('T')[0],
    notes: '',
  });

  // Form state
  const [formData, setFormData] = useState({
    card_name: '',
    issuer: '',
    card_number: '',
    credit_limit: '',
    billing_cycle_day: '5',
    due_day: '20',
    is_default: false,
  });

  // Tab state for analytics sections
  const [activeTab, setActiveTab] = useState<'cards' | 'dues' | 'rewards' | 'interest' | 'recommend'>('cards');

  const fetchCards = useCallback(async () => {
    if (!token) return;
    try {
      const [cardsData, issuersData] = await Promise.all([
        apiRequest('/credit-cards', { token }),
        apiRequest('/credit-cards/issuers-list', { token }),
      ]);
      setCards(cardsData || []);
      setIssuers(issuersData?.issuers || []);
    } catch (error) {
      console.error('Error fetching cards:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token]);

  useEffect(() => {
    fetchCards();
  }, [fetchCards]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchCards();
  };

  const resetForm = () => {
    setFormData({
      card_name: '',
      issuer: '',
      card_number: '',
      credit_limit: '',
      billing_cycle_day: '5',
      due_day: '20',
      is_default: false,
    });
    setEditingCard(null);
  };

  const handleAddCard = async () => {
    if (!formData.card_name || !formData.issuer) {
      Alert.alert('Error', 'Card name and issuer are required');
      return;
    }

    try {
      const payload = {
        card_name: formData.card_name,
        issuer: formData.issuer,
        card_number: formData.card_number,
        credit_limit: parseFloat(formData.credit_limit) || 0,
        billing_cycle_day: parseInt(formData.billing_cycle_day) || 5,
        due_day: parseInt(formData.due_day) || 20,
        is_default: formData.is_default,
      };

      if (editingCard) {
        await apiRequest(`/credit-cards/${editingCard.id}`, {
          method: 'PUT',
          body: payload,
          token,
        });
        Alert.alert('Success', 'Credit card updated');
      } else {
        await apiRequest('/credit-cards', {
          method: 'POST',
          body: payload,
          token,
        });
        Alert.alert('Success', 'Credit card added');
      }

      setShowAddModal(false);
      resetForm();
      fetchCards();
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to save card');
    }
  };

  const handleDeleteCard = (card: CreditCard) => {
    Alert.alert(
      'Delete Card',
      `Are you sure you want to delete "${card.card_name}"? All transactions will also be deleted.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await apiRequest(`/credit-cards/${card.id}`, {
                method: 'DELETE',
                token,
              });
              fetchCards();
            } catch (error: any) {
              Alert.alert('Error', error.message);
            }
          },
        },
      ]
    );
  };

  const handleEditCard = (card: CreditCard) => {
    setEditingCard(card);
    setFormData({
      card_name: card.card_name,
      issuer: card.issuer,
      card_number: '',
      credit_limit: card.credit_limit.toString(),
      billing_cycle_day: card.billing_cycle_day.toString(),
      due_day: card.due_day.toString(),
      is_default: card.is_default,
    });
    setShowAddModal(true);
  };

  const getUtilizationColor = (utilization: number) => {
    if (utilization >= 80) return '#EF4444';
    if (utilization >= 50) return '#F59E0B';
    return '#10B981';
  };

  const openAddTransaction = (card?: CreditCard) => {
    setTxnForm({
      card_id: card?.id || (cards.length > 0 ? cards[0].id : ''),
      type: 'expense',
      amount: '',
      description: '',
      merchant: '',
      category: 'Food & Dining',
      date: new Date().toISOString().split('T')[0],
      notes: '',
    });
    setShowTxnModal(true);
  };

  const handleAddTransaction = async () => {
    if (!txnForm.card_id) {
      Alert.alert('Error', 'Please select a credit card');
      return;
    }
    if (!txnForm.amount || parseFloat(txnForm.amount) <= 0) {
      Alert.alert('Error', 'Please enter a valid amount');
      return;
    }
    if (!txnForm.description.trim()) {
      Alert.alert('Error', 'Description is required');
      return;
    }

    setSavingTxn(true);
    try {
      await apiRequest('/credit-card-transactions', {
        method: 'POST',
        body: {
          card_id: txnForm.card_id,
          type: txnForm.type,
          amount: parseFloat(txnForm.amount),
          description: txnForm.description.trim(),
          merchant: txnForm.merchant.trim(),
          category: txnForm.category,
          date: txnForm.date,
          notes: txnForm.notes.trim(),
        },
        token,
      });
      setShowTxnModal(false);
      Alert.alert('Success', `Transaction recorded successfully`);
      fetchCards(); // Refresh outstanding amounts
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to record transaction');
    } finally {
      setSavingTxn(false);
    }
  };

  if (loading) {
    return (
      <View style={[styles.loadingContainer, { backgroundColor: colors.background }]}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <ScrollView
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />}
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity
            testID="cc-back-btn"
            onPress={() => router.back()}
            style={[styles.backBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}
          >
            <MaterialCommunityIcons name="arrow-left" size={20} color={colors.textPrimary} />
          </TouchableOpacity>
          <View style={{ flex: 1 }}>
            <Text style={[styles.title, { color: colors.textPrimary }]}>Credit Cards</Text>
            <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
              Manage your cards and track spending
            </Text>
          </View>
        </View>

        {/* Analytics Tab Bar */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 14, flexGrow: 0 }}>
          {[
            { key: 'cards', label: 'My Cards', icon: 'credit-card' },
            { key: 'dues', label: 'Dues', icon: 'calendar-clock' },
            { key: 'rewards', label: 'Rewards', icon: 'star-circle' },
            { key: 'interest', label: 'Interest', icon: 'calculator-variant' },
            { key: 'recommend', label: 'Best Card', icon: 'brain' },
          ].map((tab) => (
            <TouchableOpacity
              key={tab.key}
              testID={`cc-tab-${tab.key}`}
              style={[
                styles.analyticsTab,
                {
                  backgroundColor: activeTab === tab.key
                    ? (isDark ? 'rgba(99,102,241,0.2)' : 'rgba(99,102,241,0.1)')
                    : (isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)'),
                  borderColor: activeTab === tab.key ? '#6366F1' : 'transparent',
                },
              ]}
              onPress={() => setActiveTab(tab.key as any)}
            >
              <MaterialCommunityIcons
                name={tab.icon as any}
                size={16}
                color={activeTab === tab.key ? '#6366F1' : colors.textSecondary}
              />
              <Text style={[
                styles.analyticsTabText,
                { color: activeTab === tab.key ? '#6366F1' : colors.textSecondary },
              ]}>
                {tab.label}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* Summary Card */}
        {cards.length > 0 && (
          <View style={[styles.summaryCard, { 
            backgroundColor: isDark ? 'rgba(99, 102, 241, 0.15)' : 'rgba(99, 102, 241, 0.08)',
            borderColor: isDark ? 'rgba(99, 102, 241, 0.3)' : 'rgba(99, 102, 241, 0.2)',
          }]}>
            <View style={styles.summaryRow}>
              <View style={styles.summaryItem}>
                <Text style={[styles.summaryLabel, { color: colors.textSecondary }]}>Total Limit</Text>
                <Text style={[styles.summaryValue, { color: colors.textPrimary }]}>
                  {formatINRShort(cards.reduce((sum, c) => sum + c.credit_limit, 0))}
                </Text>
              </View>
              <View style={styles.summaryItem}>
                <Text style={[styles.summaryLabel, { color: colors.textSecondary }]}>Outstanding</Text>
                <Text style={[styles.summaryValue, { color: '#EF4444' }]}>
                  {formatINRShort(cards.reduce((sum, c) => sum + c.current_outstanding, 0))}
                </Text>
              </View>
              <View style={styles.summaryItem}>
                <Text style={[styles.summaryLabel, { color: colors.textSecondary }]}>Available</Text>
                <Text style={[styles.summaryValue, { color: '#10B981' }]}>
                  {formatINRShort(cards.reduce((sum, c) => sum + c.available_credit, 0))}
                </Text>
              </View>
            </View>
          </View>
        )}

        {/* Quick Add Transaction Banner */}
        {cards.length > 0 && activeTab === 'cards' && (
          <TouchableOpacity
            testID="add-txn-banner"
            activeOpacity={0.85}
            onPress={() => openAddTransaction()}
            style={[styles.quickAddBanner, {
              backgroundColor: isDark ? 'rgba(16, 185, 129, 0.1)' : 'rgba(16, 185, 129, 0.07)',
              borderColor: isDark ? 'rgba(16, 185, 129, 0.3)' : 'rgba(16, 185, 129, 0.2)',
            }]}
          >
            <View style={[styles.quickAddIcon, { backgroundColor: isDark ? 'rgba(16,185,129,0.2)' : 'rgba(16,185,129,0.15)' }]}>
              <MaterialCommunityIcons name="plus" size={20} color="#10B981" />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={[styles.quickAddTitle, { color: colors.textPrimary }]}>Record a Transaction</Text>
              <Text style={[styles.quickAddSubtitle, { color: colors.textSecondary }]}>Add expense or payment manually</Text>
            </View>
            <MaterialCommunityIcons name="chevron-right" size={20} color="#10B981" />
          </TouchableOpacity>
        )}

        {/* Cards List - only show on cards tab */}
        {activeTab === 'cards' && (cards.length === 0 ? (
          <View style={[styles.emptyState, { backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)' }]}>
            <MaterialCommunityIcons name="credit-card-off-outline" size={48} color={colors.textSecondary} />
            <Text style={[styles.emptyText, { color: colors.textSecondary }]}>No credit cards added</Text>
            <Text style={[styles.emptySubtext, { color: colors.textSecondary }]}>
              Add your credit cards to track expenses and manage payments
            </Text>
          </View>
        ) : (
          cards.map((card) => {
            const utilization = card.credit_limit > 0 
              ? (card.current_outstanding / card.credit_limit) * 100 
              : 0;
            
            return (
              <TouchableOpacity
                key={card.id}
                style={[styles.cardItem, {
                  backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : '#fff',
                  borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
                }]}
                onPress={() => handleEditCard(card)}
                activeOpacity={0.7}
              >
                <View style={styles.cardHeader}>
                  <View style={[styles.cardIcon, { backgroundColor: isDark ? 'rgba(99, 102, 241, 0.2)' : 'rgba(99, 102, 241, 0.1)' }]}>
                    <MaterialCommunityIcons name="credit-card" size={24} color="#6366F1" />
                  </View>
                  <View style={styles.cardInfo}>
                    <Text style={[styles.cardName, { color: colors.textPrimary }]}>{card.card_name}</Text>
                    <Text style={[styles.cardIssuer, { color: colors.textSecondary }]}>
                      {card.issuer} •••• {card.last_four}
                    </Text>
                  </View>
                  {card.is_default && (
                    <View style={[styles.defaultBadge, { backgroundColor: '#10B98120' }]}>
                      <Text style={styles.defaultText}>Default</Text>
                    </View>
                  )}
                  <TouchableOpacity onPress={() => handleDeleteCard(card)} style={styles.deleteBtn}>
                    <MaterialCommunityIcons name="delete-outline" size={20} color="#EF4444" />
                  </TouchableOpacity>
                </View>

                <View style={styles.cardDetails}>
                  <View style={styles.detailRow}>
                    <Text style={[styles.detailLabel, { color: colors.textSecondary }]}>Credit Limit</Text>
                    <Text style={[styles.detailValue, { color: colors.textPrimary }]}>{formatINRShort(card.credit_limit)}</Text>
                  </View>
                  <View style={styles.detailRow}>
                    <Text style={[styles.detailLabel, { color: colors.textSecondary }]}>Outstanding</Text>
                    <Text style={[styles.detailValue, { color: '#EF4444' }]}>{formatINRShort(card.current_outstanding)}</Text>
                  </View>
                  <View style={styles.detailRow}>
                    <Text style={[styles.detailLabel, { color: colors.textSecondary }]}>Due Date</Text>
                    <Text style={[styles.detailValue, { color: colors.textPrimary }]}>{card.due_day}th of month</Text>
                  </View>
                </View>

                {/* Utilization Bar */}
                <View style={styles.utilizationContainer}>
                  <View style={styles.utilizationHeader}>
                    <Text style={[styles.utilizationLabel, { color: colors.textSecondary }]}>Utilization</Text>
                    <Text style={[styles.utilizationValue, { color: getUtilizationColor(utilization) }]}>
                      {utilization.toFixed(1)}%
                    </Text>
                  </View>
                  <View style={[styles.utilizationBar, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.06)' }]}>
                    <View 
                      style={[styles.utilizationFill, { 
                        width: `${Math.min(utilization, 100)}%`,
                        backgroundColor: getUtilizationColor(utilization),
                      }]} 
                    />
                  </View>
                </View>

                {/* Card Action Row */}
                <View style={[styles.cardActionRow, { borderTopColor: isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.06)' }]}>
                  <TouchableOpacity
                    testID={`add-expense-btn-${card.id}`}
                    style={[styles.cardActionBtn, { backgroundColor: isDark ? 'rgba(239,68,68,0.12)' : 'rgba(239,68,68,0.07)' }]}
                    onPress={() => openAddTransaction(card)}
                  >
                    <MaterialCommunityIcons name="credit-card-minus" size={14} color="#EF4444" />
                    <Text style={[styles.cardActionText, { color: '#EF4444' }]}>Add Expense</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    testID={`add-payment-btn-${card.id}`}
                    style={[styles.cardActionBtn, { backgroundColor: isDark ? 'rgba(16,185,129,0.12)' : 'rgba(16,185,129,0.07)' }]}
                    onPress={() => {
                      openAddTransaction(card);
                      setTxnForm(f => ({ ...f, type: 'payment', category: 'Payment' }));
                    }}
                  >
                    <MaterialCommunityIcons name="credit-card-check" size={14} color="#10B981" />
                    <Text style={[styles.cardActionText, { color: '#10B981' }]}>Record Payment</Text>
                  </TouchableOpacity>
                </View>
              </TouchableOpacity>
            );
          })
        ))}

        {/* Analytics Sections */}
        {activeTab === 'dues' && token && (
          <DueCalendarSection token={token} isDark={isDark} colors={colors} />
        )}
        {activeTab === 'rewards' && token && (
          <RewardsTracker token={token} isDark={isDark} colors={colors} />
        )}
        {activeTab === 'interest' && token && (
          <InterestCalculator token={token} isDark={isDark} colors={colors} cards={cards} />
        )}
        {activeTab === 'recommend' && token && (
          <CardRecommender token={token} isDark={isDark} colors={colors} />
        )}

        <View style={{ height: 100 }} />
      </ScrollView>

      {/* Add Button */}
      <TouchableOpacity
        style={[styles.addButton, { backgroundColor: colors.primary }]}
        onPress={() => {
          resetForm();
          setShowAddModal(true);
        }}
      >
        <MaterialCommunityIcons name="plus" size={28} color="#fff" />
      </TouchableOpacity>

      {/* Add/Edit Card Modal */}
      <Modal visible={showAddModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, { backgroundColor: colors.card }]}>
            <View style={styles.modalHeader}>
              <Text style={[styles.modalTitle, { color: colors.textPrimary }]}>
                {editingCard ? 'Edit Credit Card' : 'Add Credit Card'}
              </Text>
              <TouchableOpacity onPress={() => { setShowAddModal(false); resetForm(); }}>
                <MaterialCommunityIcons name="close" size={24} color={colors.textSecondary} />
              </TouchableOpacity>
            </View>

            <ScrollView showsVerticalScrollIndicator={false}>
              <Text style={[styles.inputLabel, { color: colors.textSecondary }]}>Card Name *</Text>
              <TextInput
                style={[styles.input, { 
                  backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : '#F3F4F6',
                  color: colors.textPrimary,
                  borderColor: isDark ? 'rgba(255,255,255,0.1)' : '#D1D5DB',
                }]}
                placeholder="e.g., HDFC Regalia"
                placeholderTextColor={colors.textSecondary}
                value={formData.card_name}
                onChangeText={(text) => setFormData({ ...formData, card_name: text })}
              />

              <Text style={[styles.inputLabel, { color: colors.textSecondary }]}>Card Issuer *</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.issuerScroll}>
                {issuers.slice(0, 10).map((issuer) => (
                  <TouchableOpacity
                    key={issuer}
                    style={[styles.issuerChip, {
                      backgroundColor: formData.issuer === issuer 
                        ? colors.primary 
                        : (isDark ? 'rgba(255,255,255,0.08)' : '#F3F4F6'),
                      borderColor: formData.issuer === issuer 
                        ? colors.primary 
                        : (isDark ? 'rgba(255,255,255,0.1)' : '#D1D5DB'),
                    }]}
                    onPress={() => setFormData({ ...formData, issuer })}
                  >
                    <Text style={[styles.issuerText, { 
                      color: formData.issuer === issuer ? '#fff' : colors.textPrimary 
                    }]}>{issuer}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>

              <Text style={[styles.inputLabel, { color: colors.textSecondary }]}>Card Number (Optional)</Text>
              <TextInput
                style={[styles.input, { 
                  backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : '#F3F4F6',
                  color: colors.textPrimary,
                  borderColor: isDark ? 'rgba(255,255,255,0.1)' : '#D1D5DB',
                }]}
                placeholder="Last 4 digits will be shown"
                placeholderTextColor={colors.textSecondary}
                value={formData.card_number}
                onChangeText={(text) => setFormData({ ...formData, card_number: text })}
                keyboardType="numeric"
                maxLength={16}
              />

              <Text style={[styles.inputLabel, { color: colors.textSecondary }]}>Credit Limit</Text>
              <TextInput
                style={[styles.input, { 
                  backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : '#F3F4F6',
                  color: colors.textPrimary,
                  borderColor: isDark ? 'rgba(255,255,255,0.1)' : '#D1D5DB',
                }]}
                placeholder="₹3,00,000"
                placeholderTextColor={colors.textSecondary}
                value={formData.credit_limit}
                onChangeText={(text) => setFormData({ ...formData, credit_limit: text })}
                keyboardType="numeric"
              />

              <View style={styles.rowInputs}>
                <View style={{ flex: 1, marginRight: 8 }}>
                  <Text style={[styles.inputLabel, { color: colors.textSecondary }]}>Bill Day</Text>
                  <TextInput
                    style={[styles.input, { 
                      backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : '#F3F4F6',
                      color: colors.textPrimary,
                      borderColor: isDark ? 'rgba(255,255,255,0.1)' : '#D1D5DB',
                    }]}
                    placeholder="5"
                    placeholderTextColor={colors.textSecondary}
                    value={formData.billing_cycle_day}
                    onChangeText={(text) => setFormData({ ...formData, billing_cycle_day: text })}
                    keyboardType="numeric"
                    maxLength={2}
                  />
                </View>
                <View style={{ flex: 1, marginLeft: 8 }}>
                  <Text style={[styles.inputLabel, { color: colors.textSecondary }]}>Due Day</Text>
                  <TextInput
                    style={[styles.input, { 
                      backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : '#F3F4F6',
                      color: colors.textPrimary,
                      borderColor: isDark ? 'rgba(255,255,255,0.1)' : '#D1D5DB',
                    }]}
                    placeholder="20"
                    placeholderTextColor={colors.textSecondary}
                    value={formData.due_day}
                    onChangeText={(text) => setFormData({ ...formData, due_day: text })}
                    keyboardType="numeric"
                    maxLength={2}
                  />
                </View>
              </View>

              <TouchableOpacity
                style={styles.defaultToggle}
                onPress={() => setFormData({ ...formData, is_default: !formData.is_default })}
              >
                <MaterialCommunityIcons
                  name={formData.is_default ? 'checkbox-marked' : 'checkbox-blank-outline'}
                  size={24}
                  color={formData.is_default ? colors.primary : colors.textSecondary}
                />
                <Text style={[styles.defaultToggleText, { color: colors.textPrimary }]}>
                  Set as default card
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.submitBtn, { backgroundColor: colors.primary }]}
                onPress={handleAddCard}
              >
                <Text style={styles.submitBtnText}>
                  {editingCard ? 'Update Card' : 'Add Card'}
                </Text>
              </TouchableOpacity>
            </ScrollView>
          </View>
        </View>
      </Modal>
      {/* ── Add Transaction Modal ── */}
      <Modal visible={showTxnModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, { backgroundColor: colors.card }]}>
            <View style={styles.modalHeader}>
              <Text style={[styles.modalTitle, { color: colors.textPrimary }]}>Record Transaction</Text>
              <TouchableOpacity onPress={() => setShowTxnModal(false)}>
                <MaterialCommunityIcons name="close" size={24} color={colors.textSecondary} />
              </TouchableOpacity>
            </View>

            <ScrollView showsVerticalScrollIndicator={false}>
              {/* Transaction Type Toggle */}
              <Text style={[styles.inputLabel, { color: colors.textSecondary }]}>Type</Text>
              <View style={styles.typeToggleRow}>
                {TXN_TYPES.map(t => (
                  <TouchableOpacity
                    testID={`txn-type-${t.key}`}
                    key={t.key}
                    style={[styles.typeToggleBtn, {
                      backgroundColor: txnForm.type === t.key
                        ? t.color + '20'
                        : (isDark ? 'rgba(255,255,255,0.06)' : '#F3F4F6'),
                      borderColor: txnForm.type === t.key ? t.color : 'transparent',
                      borderWidth: 1.5,
                    }]}
                    onPress={() => setTxnForm({ ...txnForm, type: t.key })}
                  >
                    <MaterialCommunityIcons name={t.icon as any} size={18} color={txnForm.type === t.key ? t.color : colors.textSecondary} />
                    <Text style={{ fontSize: 13, fontFamily: 'DM Sans', fontWeight: '600', color: txnForm.type === t.key ? t.color : colors.textSecondary }}>
                      {t.label}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>

              {/* Card Selector */}
              <Text style={[styles.inputLabel, { color: colors.textSecondary }]}>Card *</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.issuerScroll}>
                {cards.map(card => (
                  <TouchableOpacity
                    testID={`card-select-${card.id}`}
                    key={card.id}
                    style={[styles.issuerChip, {
                      backgroundColor: txnForm.card_id === card.id
                        ? '#6366F1'
                        : (isDark ? 'rgba(255,255,255,0.08)' : '#F3F4F6'),
                      borderColor: txnForm.card_id === card.id
                        ? '#6366F1'
                        : (isDark ? 'rgba(255,255,255,0.1)' : '#D1D5DB'),
                    }]}
                    onPress={() => setTxnForm({ ...txnForm, card_id: card.id })}
                  >
                    <Text style={[styles.issuerText, { color: txnForm.card_id === card.id ? '#fff' : colors.textPrimary }]}>
                      {card.card_name}
                    </Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>

              {/* Amount */}
              <Text style={[styles.inputLabel, { color: colors.textSecondary }]}>Amount (₹) *</Text>
              <TextInput
                testID="txn-amount-input"
                style={[styles.input, {
                  backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : '#F3F4F6',
                  color: colors.textPrimary,
                  borderColor: isDark ? 'rgba(255,255,255,0.1)' : '#D1D5DB',
                }]}
                placeholder="0.00"
                placeholderTextColor={colors.textSecondary}
                value={txnForm.amount}
                onChangeText={t => setTxnForm({ ...txnForm, amount: t })}
                keyboardType="decimal-pad"
              />

              {/* Description */}
              <Text style={[styles.inputLabel, { color: colors.textSecondary }]}>Description *</Text>
              <TextInput
                testID="txn-description-input"
                style={[styles.input, {
                  backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : '#F3F4F6',
                  color: colors.textPrimary,
                  borderColor: isDark ? 'rgba(255,255,255,0.1)' : '#D1D5DB',
                }]}
                placeholder="e.g., Dinner at Zomato"
                placeholderTextColor={colors.textSecondary}
                value={txnForm.description}
                onChangeText={t => setTxnForm({ ...txnForm, description: t })}
              />

              {/* Merchant */}
              <Text style={[styles.inputLabel, { color: colors.textSecondary }]}>Merchant (Optional)</Text>
              <TextInput
                style={[styles.input, {
                  backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : '#F3F4F6',
                  color: colors.textPrimary,
                  borderColor: isDark ? 'rgba(255,255,255,0.1)' : '#D1D5DB',
                }]}
                placeholder="e.g., Zomato"
                placeholderTextColor={colors.textSecondary}
                value={txnForm.merchant}
                onChangeText={t => setTxnForm({ ...txnForm, merchant: t })}
              />

              {/* Category */}
              {txnForm.type === 'expense' && (
                <>
                  <Text style={[styles.inputLabel, { color: colors.textSecondary }]}>Category</Text>
                  <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.issuerScroll}>
                    {CC_CATEGORIES.map(cat => (
                      <TouchableOpacity
                        testID={`category-${cat}`}
                        key={cat}
                        style={[styles.issuerChip, {
                          backgroundColor: txnForm.category === cat
                            ? '#6366F1'
                            : (isDark ? 'rgba(255,255,255,0.08)' : '#F3F4F6'),
                          borderColor: txnForm.category === cat
                            ? '#6366F1'
                            : (isDark ? 'rgba(255,255,255,0.1)' : '#D1D5DB'),
                        }]}
                        onPress={() => setTxnForm({ ...txnForm, category: cat })}
                      >
                        <Text style={[styles.issuerText, { color: txnForm.category === cat ? '#fff' : colors.textPrimary }]}>{cat}</Text>
                      </TouchableOpacity>
                    ))}
                  </ScrollView>
                </>
              )}

              {/* Date */}
              <Text style={[styles.inputLabel, { color: colors.textSecondary }]}>Date</Text>
              <TextInput
                testID="txn-date-input"
                style={[styles.input, {
                  backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : '#F3F4F6',
                  color: colors.textPrimary,
                  borderColor: isDark ? 'rgba(255,255,255,0.1)' : '#D1D5DB',
                }]}
                placeholder="YYYY-MM-DD"
                placeholderTextColor={colors.textSecondary}
                value={txnForm.date}
                onChangeText={t => setTxnForm({ ...txnForm, date: t })}
              />

              <TouchableOpacity
                testID="txn-submit-btn"
                style={[styles.submitBtn, {
                  backgroundColor: txnForm.type === 'expense' ? '#EF4444' : '#10B981',
                  opacity: savingTxn ? 0.7 : 1,
                }]}
                onPress={handleAddTransaction}
                disabled={savingTxn}
              >
                {savingTxn ? (
                  <ActivityIndicator size="small" color="#fff" />
                ) : (
                  <Text style={styles.submitBtnText}>
                    {txnForm.type === 'expense' ? 'Record Expense' : 'Record Payment'}
                  </Text>
                )}
              </TouchableOpacity>
            </ScrollView>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 20,
    paddingBottom: 10,
    paddingTop: 56,
    gap: 14,
  },
  backBtn: {
    width: 40,
    height: 40,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: { fontSize: 28, fontFamily: 'DM Sans', fontWeight: '700' },
  subtitle: { fontSize: 14, fontFamily: 'DM Sans', marginTop: 4 },
  summaryCard: {
    marginHorizontal: 20,
    padding: 16,
    borderRadius: 16,
    borderWidth: 1,
    marginBottom: 16,
  },
  summaryRow: { flexDirection: 'row', justifyContent: 'space-between' },
  summaryItem: { alignItems: 'center' },
  summaryLabel: { fontSize: 11, fontFamily: 'DM Sans', marginBottom: 4 },
  summaryValue: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '700' },
  emptyState: {
    margin: 20,
    padding: 40,
    borderRadius: 16,
    alignItems: 'center',
  },
  emptyText: { fontSize: 18, fontFamily: 'DM Sans', fontWeight: '600', marginTop: 16 },
  emptySubtext: { fontSize: 14, fontFamily: 'DM Sans', marginTop: 8, textAlign: 'center' },
  cardItem: {
    marginHorizontal: 20,
    marginBottom: 12,
    borderRadius: 16,
    borderWidth: 1,
    padding: 16,
  },
  cardHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 16 },
  cardIcon: { width: 48, height: 48, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  cardInfo: { flex: 1, marginLeft: 12 },
  cardName: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '600' },
  cardIssuer: { fontSize: 13, fontFamily: 'DM Sans', marginTop: 2 },
  defaultBadge: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8, marginRight: 8 },
  defaultText: { fontSize: 10, fontFamily: 'DM Sans', fontWeight: '600', color: '#10B981' },
  deleteBtn: { padding: 8 },
  cardDetails: { borderTopWidth: 1, borderTopColor: 'rgba(128, 128, 128, 0.15)', paddingTop: 12 },
  detailRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  detailLabel: { fontSize: 13, fontFamily: 'DM Sans' },
  detailValue: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '600' },
  utilizationContainer: { marginTop: 12 },
  utilizationHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  utilizationLabel: { fontSize: 12, fontFamily: 'DM Sans' },
  utilizationValue: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '700' },
  utilizationBar: { height: 6, borderRadius: 3, overflow: 'hidden' },
  utilizationFill: { height: '100%', borderRadius: 3 },
  addButton: {
    position: 'absolute',
    bottom: 24,
    right: 24,
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
  },

  // Quick Add Banner
  quickAddBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 20,
    marginBottom: 12,
    padding: 14,
    borderRadius: 14,
    borderWidth: 1,
    gap: 12,
  },
  quickAddIcon: {
    width: 38,
    height: 38,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  quickAddTitle: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700' },
  quickAddSubtitle: { fontSize: 12, fontFamily: 'DM Sans', marginTop: 1 },

  // Card Action Row
  cardActionRow: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
  },
  cardActionBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 5,
    paddingVertical: 8,
    borderRadius: 10,
  },
  cardActionText: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600' },

  // Transaction type toggle
  typeToggleRow: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 16,
  },
  typeToggleBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 12,
    borderRadius: 12,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.82)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 20,
    maxHeight: '85%',
  },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  modalTitle: { fontSize: 20, fontFamily: 'DM Sans', fontWeight: '700' },
  inputLabel: { fontSize: 13, fontFamily: 'DM Sans', marginBottom: 6, marginTop: 12 },
  input: {
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
    fontSize: 15,
    fontFamily: 'DM Sans',
  },
  issuerScroll: { marginVertical: 8 },
  issuerChip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1,
    marginRight: 8,
  },
  issuerText: { fontSize: 13, fontFamily: 'DM Sans' },
  rowInputs: { flexDirection: 'row', marginTop: 4 },
  defaultToggle: { flexDirection: 'row', alignItems: 'center', marginTop: 16 },
  defaultToggleText: { fontSize: 14, fontFamily: 'DM Sans', marginLeft: 8 },
  submitBtn: {
    marginTop: 24,
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginBottom: 20,
  },
  submitBtnText: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '600', color: '#fff' },
  analyticsTab: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 14,
    paddingVertical: 9,
    borderRadius: 12,
    borderWidth: 1.5,
    marginRight: 8,
  },
  analyticsTabText: { fontSize: 12, fontWeight: '600' },
});
