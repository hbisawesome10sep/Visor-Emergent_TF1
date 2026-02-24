import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  Modal, Alert, RefreshControl, ActivityIndicator,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useTheme } from '../context/ThemeContext';
import { apiRequest } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { formatINR } from '../utils/formatters';
import { Accent } from '../utils/theme';

type FlaggedTransaction = {
  id: string;
  type: string;
  amount: number;
  category: string;
  description: string;
  date: string;
  flagged_type: string;
  source: 'bank' | 'credit_card';
  card_name?: string;
  merchant?: string;
  is_approved: boolean;
};

type Props = {
  visible: boolean;
  onClose: () => void;
  onApproved: () => void;
};

export default function FlaggedTransactionsModal({ visible, onClose, onApproved }: Props) {
  const { colors, isDark } = useTheme();
  const { token } = useAuth();
  
  const [transactions, setTransactions] = useState<FlaggedTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [processingId, setProcessingId] = useState<string | null>(null);

  const fetchFlagged = useCallback(async () => {
    if (!token) return;
    try {
      const data = await apiRequest('/flagged-transactions', { token });
      setTransactions(data || []);
    } catch (error) {
      console.error('Error fetching flagged:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token]);

  useEffect(() => {
    if (visible) {
      fetchFlagged();
    }
  }, [visible, fetchFlagged]);

  const handleApprove = async (txn: FlaggedTransaction, approvedType: string) => {
    setProcessingId(txn.id);
    try {
      await apiRequest(`/approve-flagged/${txn.id}`, {
        method: 'POST',
        body: {
          source: txn.source,
          approved_type: approvedType,
          create_recurring: true,
        },
        token,
      });
      
      Alert.alert(
        'Success',
        `Transaction approved as ${approvedType}. ${approvedType === 'SIP' ? 'Added to your investments.' : 'Set as recurring payment.'}`,
      );
      
      // Remove from list
      setTransactions(prev => prev.filter(t => t.id !== txn.id));
      onApproved();
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to approve transaction');
    } finally {
      setProcessingId(null);
    }
  };

  const handleReject = async (txn: FlaggedTransaction) => {
    setProcessingId(txn.id);
    try {
      await apiRequest(`/reject-flagged/${txn.id}`, {
        method: 'POST',
        body: { source: txn.source },
        token,
      });
      
      // Remove from list
      setTransactions(prev => prev.filter(t => t.id !== txn.id));
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to reject');
    } finally {
      setProcessingId(null);
    }
  };

  const getTypeIcon = (flaggedType: string) => {
    switch (flaggedType) {
      case 'EMI': return 'calendar-clock';
      case 'SIP': return 'chart-line';
      case 'Subscription': return 'repeat';
      default: return 'help-circle';
    }
  };

  const getTypeColor = (flaggedType: string) => {
    switch (flaggedType) {
      case 'EMI': return Accent.amber;
      case 'SIP': return Accent.emerald;
      case 'Subscription': return Accent.sapphire;
      default: return colors.textSecondary;
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  return (
    <Modal visible={visible} animationType="slide" transparent>
      <View style={styles.overlay}>
        <View style={[styles.container, { backgroundColor: colors.card }]}>
          {/* Header */}
          <View style={styles.header}>
            <View style={styles.headerLeft}>
              <View style={[styles.headerIcon, { backgroundColor: isDark ? 'rgba(245, 158, 11, 0.15)' : 'rgba(245, 158, 11, 0.1)' }]}>
                <MaterialCommunityIcons name="flag-checkered" size={24} color={Accent.amber} />
              </View>
              <View>
                <Text style={[styles.title, { color: colors.textPrimary }]}>Review Transactions</Text>
                <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
                  {transactions.length} items detected as EMI/SIP
                </Text>
              </View>
            </View>
            <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
              <MaterialCommunityIcons name="close" size={24} color={colors.textSecondary} />
            </TouchableOpacity>
          </View>

          {/* Info Banner */}
          <View style={[styles.infoBanner, { backgroundColor: isDark ? 'rgba(59, 130, 246, 0.1)' : 'rgba(59, 130, 246, 0.08)' }]}>
            <MaterialCommunityIcons name="information" size={18} color={Accent.sapphire} />
            <Text style={[styles.infoText, { color: colors.textSecondary }]}>
              We detected potential recurring payments. Approve to track them automatically.
            </Text>
          </View>

          {/* Content */}
          <ScrollView
            style={styles.scrollView}
            refreshControl={
              <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); fetchFlagged(); }} />
            }
            showsVerticalScrollIndicator={false}
          >
            {loading ? (
              <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color={colors.primary} />
                <Text style={[styles.loadingText, { color: colors.textSecondary }]}>Loading...</Text>
              </View>
            ) : transactions.length === 0 ? (
              <View style={styles.emptyState}>
                <View style={[styles.emptyIcon, { backgroundColor: isDark ? 'rgba(16, 185, 129, 0.15)' : 'rgba(16, 185, 129, 0.1)' }]}>
                  <MaterialCommunityIcons name="check-circle" size={48} color={Accent.emerald} />
                </View>
                <Text style={[styles.emptyTitle, { color: colors.textPrimary }]}>All caught up!</Text>
                <Text style={[styles.emptySubtitle, { color: colors.textSecondary }]}>
                  No transactions need your review right now.
                </Text>
              </View>
            ) : (
              transactions.map((txn) => {
                const typeColor = getTypeColor(txn.flagged_type);
                const isProcessing = processingId === txn.id;
                
                return (
                  <View
                    key={txn.id}
                    style={[styles.txnCard, {
                      backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
                      borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
                      opacity: isProcessing ? 0.6 : 1,
                    }]}
                  >
                    {/* Type Badge */}
                    <View style={[styles.typeBadge, { backgroundColor: `${typeColor}20` }]}>
                      <MaterialCommunityIcons name={getTypeIcon(txn.flagged_type) as any} size={16} color={typeColor} />
                      <Text style={[styles.typeBadgeText, { color: typeColor }]}>{txn.flagged_type}</Text>
                    </View>

                    {/* Transaction Info */}
                    <View style={styles.txnInfo}>
                      <Text style={[styles.txnDescription, { color: colors.textPrimary }]} numberOfLines={2}>
                        {txn.description}
                      </Text>
                      <View style={styles.txnMeta}>
                        <Text style={[styles.txnSource, { color: colors.textSecondary }]}>
                          {txn.source === 'credit_card' ? `💳 ${txn.card_name}` : '🏦 Bank/UPI'}
                        </Text>
                        <Text style={[styles.txnDate, { color: colors.textSecondary }]}>
                          {formatDate(txn.date)}
                        </Text>
                      </View>
                      <Text style={[styles.txnAmount, { color: Accent.ruby }]}>
                        {formatINR(txn.amount)}
                      </Text>
                    </View>

                    {/* Actions */}
                    <View style={styles.actions}>
                      <Text style={[styles.actionLabel, { color: colors.textSecondary }]}>Is this a recurring payment?</Text>
                      
                      <View style={styles.actionButtons}>
                        {/* Approve Buttons */}
                        <TouchableOpacity
                          style={[styles.approveBtn, { backgroundColor: `${Accent.emerald}15`, borderColor: Accent.emerald }]}
                          onPress={() => handleApprove(txn, txn.flagged_type)}
                          disabled={isProcessing}
                        >
                          <MaterialCommunityIcons name="check" size={18} color={Accent.emerald} />
                          <Text style={[styles.approveBtnText, { color: Accent.emerald }]}>
                            Yes, it's {txn.flagged_type}
                          </Text>
                        </TouchableOpacity>

                        {/* Change Type */}
                        {txn.flagged_type !== 'EMI' && (
                          <TouchableOpacity
                            style={[styles.changeBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)' }]}
                            onPress={() => handleApprove(txn, 'EMI')}
                            disabled={isProcessing}
                          >
                            <Text style={[styles.changeBtnText, { color: colors.textSecondary }]}>Mark as EMI</Text>
                          </TouchableOpacity>
                        )}
                        {txn.flagged_type !== 'SIP' && (
                          <TouchableOpacity
                            style={[styles.changeBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)' }]}
                            onPress={() => handleApprove(txn, 'SIP')}
                            disabled={isProcessing}
                          >
                            <Text style={[styles.changeBtnText, { color: colors.textSecondary }]}>Mark as SIP</Text>
                          </TouchableOpacity>
                        )}
                        {txn.flagged_type !== 'Subscription' && (
                          <TouchableOpacity
                            style={[styles.changeBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)' }]}
                            onPress={() => handleApprove(txn, 'Subscription')}
                            disabled={isProcessing}
                          >
                            <Text style={[styles.changeBtnText, { color: colors.textSecondary }]}>Mark as Subscription</Text>
                          </TouchableOpacity>
                        )}

                        {/* Reject Button */}
                        <TouchableOpacity
                          style={[styles.rejectBtn, { backgroundColor: `${Accent.ruby}10`, borderColor: `${Accent.ruby}30` }]}
                          onPress={() => handleReject(txn)}
                          disabled={isProcessing}
                        >
                          <MaterialCommunityIcons name="close" size={16} color={Accent.ruby} />
                          <Text style={[styles.rejectBtnText, { color: Accent.ruby }]}>Not recurring</Text>
                        </TouchableOpacity>
                      </View>
                    </View>

                    {isProcessing && (
                      <View style={styles.processingOverlay}>
                        <ActivityIndicator size="small" color={colors.primary} />
                      </View>
                    )}
                  </View>
                );
              })
            )}
            <View style={{ height: 40 }} />
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.62)',
    backdropFilter: 'blur(12px)',
    WebkitBackdropFilter: 'blur(12px)',
    justifyContent: 'flex-end',
  },
  container: {
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: '90%',
    minHeight: '60%',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 20,
    paddingBottom: 12,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  headerIcon: {
    width: 44,
    height: 44,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    fontSize: 20,
    fontFamily: 'DM Sans',
    fontWeight: '700' as any,
  },
  subtitle: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    marginTop: 2,
  },
  closeBtn: {
    padding: 8,
  },
  infoBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 20,
    padding: 12,
    borderRadius: 12,
    gap: 10,
    marginBottom: 12,
  },
  infoText: {
    flex: 1,
    fontSize: 12,
    fontFamily: 'DM Sans',
    lineHeight: 18,
  },
  scrollView: {
    flex: 1,
    paddingHorizontal: 20,
  },
  loadingContainer: {
    paddingVertical: 60,
    alignItems: 'center',
  },
  loadingText: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    marginTop: 12,
  },
  emptyState: {
    paddingVertical: 60,
    alignItems: 'center',
  },
  emptyIcon: {
    width: 80,
    height: 80,
    borderRadius: 40,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  emptyTitle: {
    fontSize: 18,
    fontFamily: 'DM Sans',
    fontWeight: '600' as any,
  },
  emptySubtitle: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    marginTop: 8,
    textAlign: 'center',
  },
  txnCard: {
    borderRadius: 16,
    borderWidth: 1,
    padding: 16,
    marginBottom: 12,
  },
  typeBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 8,
    gap: 6,
    marginBottom: 12,
  },
  typeBadgeText: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    fontWeight: '600' as any,
  },
  txnInfo: {
    marginBottom: 16,
  },
  txnDescription: {
    fontSize: 15,
    fontFamily: 'DM Sans',
    fontWeight: '600' as any,
    marginBottom: 8,
  },
  txnMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 8,
  },
  txnSource: {
    fontSize: 12,
    fontFamily: 'DM Sans',
  },
  txnDate: {
    fontSize: 12,
    fontFamily: 'DM Sans',
  },
  txnAmount: {
    fontSize: 18,
    fontFamily: 'DM Sans',
    fontWeight: '700' as any,
  },
  actions: {
    borderTopWidth: 1,
    borderTopColor: 'rgba(128,128,128,0.15)',
    paddingTop: 14,
  },
  actionLabel: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    marginBottom: 10,
  },
  actionButtons: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  approveBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 10,
    borderWidth: 1,
    gap: 6,
  },
  approveBtnText: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    fontWeight: '600' as any,
  },
  changeBtn: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
  },
  changeBtnText: {
    fontSize: 12,
    fontFamily: 'DM Sans',
  },
  rejectBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    gap: 4,
  },
  rejectBtnText: {
    fontSize: 12,
    fontFamily: 'DM Sans',
  },
  processingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.1)',
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
