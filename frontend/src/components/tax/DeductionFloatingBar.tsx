import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Modal, ScrollView, Animated } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { Accent } from '../../utils/theme';
import { formatINR, formatINRShort } from '../../utils/formatters';

interface DeductionFloatingBarProps {
  autoDeductions: any;
  userDeductions: any[];
  colors: any;
  isDark: boolean;
  onApprove: (txn: any) => void;
  onDismiss: (txn: any) => void;
  onEdit: (txn: any) => void;
  onViewAll: () => void;
}

export const DeductionFloatingBar: React.FC<DeductionFloatingBarProps> = ({
  autoDeductions,
  userDeductions,
  colors,
  isDark,
  onApprove,
  onDismiss,
  onEdit,
  onViewAll,
}) => {
  const [expanded, setExpanded] = useState(false);
  const [showDetailsModal, setShowDetailsModal] = useState(false);

  // Calculate totals
  const autoTotal = autoDeductions?.sections?.reduce((sum: number, s: any) => sum + s.total_amount, 0) || 0;
  const autoCount = autoDeductions?.count || 0;
  const userTotal = userDeductions?.reduce((sum: number, d: any) => sum + (d.invested_amount || 0), 0) || 0;
  const totalDeductions = autoTotal + userTotal;

  // Get pending transactions that need approval (not yet in userDeductions)
  const pendingTransactions = autoDeductions?.sections?.flatMap((s: any) => 
    s.transactions.filter((t: any) => t.status !== 'approved')
  ) || [];
  const pendingCount = pendingTransactions.length;

  // Section limits
  const sectionLimits: Record<string, number> = {
    '80C': 150000,
    '80D': 25000, // Basic, can be higher for senior citizens
    '80E': 0, // No limit
    '80G': 0, // Varies
    '80TTA': 10000,
    '80EE': 50000,
    '80EEA': 150000,
    '80CCD(1B)': 50000,
    '80CCD(2)': 0, // 10% of basic
  };

  if (autoCount === 0) return null;

  return (
    <>
      {/* Floating Bar */}
      <TouchableOpacity
        activeOpacity={0.95}
        onPress={() => setShowDetailsModal(true)}
        data-testid="deduction-floating-bar"
      >
        <LinearGradient
          colors={isDark 
            ? ['rgba(139, 92, 246, 0.25)', 'rgba(139, 92, 246, 0.15)']
            : ['rgba(139, 92, 246, 0.15)', 'rgba(139, 92, 246, 0.08)']
          }
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 0 }}
          style={[styles.floatingBar, { borderColor: isDark ? 'rgba(139, 92, 246, 0.4)' : 'rgba(139, 92, 246, 0.3)' }]}
        >
          <View style={styles.barContent}>
            <View style={[styles.iconContainer, { backgroundColor: 'rgba(139, 92, 246, 0.2)' }]}>
              <MaterialCommunityIcons name="lightning-bolt" size={18} color="#8B5CF6" />
            </View>
            
            <View style={styles.barInfo}>
              <Text style={[styles.barTitle, { color: colors.textPrimary }]}>
                {autoCount} Deductions Detected
              </Text>
              <Text style={[styles.barSubtitle, { color: colors.textSecondary }]}>
                {formatINRShort(autoTotal)} eligible • Tap to review
              </Text>
            </View>

            <View style={styles.barActions}>
              {pendingCount > 0 && (
                <View style={[styles.pendingBadge, { backgroundColor: '#F59E0B' }]}>
                  <Text style={styles.pendingText}>{pendingCount}</Text>
                </View>
              )}
              <MaterialCommunityIcons name="chevron-right" size={20} color={colors.textSecondary} />
            </View>
          </View>

          {/* Mini progress bars for top sections */}
          {autoDeductions?.sections?.slice(0, 3).map((section: any, idx: number) => {
            const limit = sectionLimits[section.section] || section.limit || 0;
            const pct = limit > 0 ? Math.min((section.total_amount / limit) * 100, 100) : 0;
            return (
              <View key={section.section} style={styles.miniProgress}>
                <Text style={[styles.miniLabel, { color: colors.textSecondary }]}>
                  {section.section}
                </Text>
                <View style={[styles.miniTrack, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)' }]}>
                  <View style={[styles.miniFill, { width: `${pct}%`, backgroundColor: '#8B5CF6' }]} />
                </View>
                <Text style={[styles.miniValue, { color: '#8B5CF6' }]}>
                  {pct.toFixed(0)}%
                </Text>
              </View>
            );
          })}
        </LinearGradient>
      </TouchableOpacity>

      {/* Details Modal */}
      <Modal
        visible={showDetailsModal}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setShowDetailsModal(false)}
      >
        <View style={[styles.modalContainer, { backgroundColor: colors.background }]}>
          {/* Modal Header */}
          <View style={[styles.modalHeader, { borderBottomColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)' }]}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
              <View style={[styles.modalIcon, { backgroundColor: 'rgba(139, 92, 246, 0.15)' }]}>
                <MaterialCommunityIcons name="receipt-text-check-outline" size={24} color="#8B5CF6" />
              </View>
              <View>
                <Text style={[styles.modalTitle, { color: colors.textPrimary }]}>
                  Tax Deduction Tracker
                </Text>
                <Text style={[styles.modalSubtitle, { color: colors.textSecondary }]}>
                  Review and approve detected deductions
                </Text>
              </View>
            </View>
            <TouchableOpacity
              style={[styles.closeBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)' }]}
              onPress={() => setShowDetailsModal(false)}
            >
              <MaterialCommunityIcons name="close" size={20} color={colors.textSecondary} />
            </TouchableOpacity>
          </View>

          {/* Summary Cards */}
          <View style={styles.summaryRow}>
            <View style={[styles.summaryCard, { backgroundColor: isDark ? 'rgba(139, 92, 246, 0.15)' : 'rgba(139, 92, 246, 0.1)' }]}>
              <Text style={[styles.summaryLabel, { color: '#8B5CF6' }]}>Auto-Detected</Text>
              <Text style={[styles.summaryValue, { color: colors.textPrimary }]}>{formatINRShort(autoTotal)}</Text>
              <Text style={[styles.summaryCount, { color: colors.textSecondary }]}>{autoCount} items</Text>
            </View>
            <View style={[styles.summaryCard, { backgroundColor: isDark ? 'rgba(16, 185, 129, 0.15)' : 'rgba(16, 185, 129, 0.1)' }]}>
              <Text style={[styles.summaryLabel, { color: Accent.emerald }]}>User Added</Text>
              <Text style={[styles.summaryValue, { color: colors.textPrimary }]}>{formatINRShort(userTotal)}</Text>
              <Text style={[styles.summaryCount, { color: colors.textSecondary }]}>{userDeductions?.length || 0} items</Text>
            </View>
          </View>

          {/* Section-wise breakdown */}
          <ScrollView style={styles.sectionsList} showsVerticalScrollIndicator={false}>
            <Text style={[styles.listTitle, { color: colors.textPrimary }]}>
              Section-wise Breakdown
            </Text>

            {autoDeductions?.sections?.map((section: any) => {
              const limit = sectionLimits[section.section] || section.limit || 0;
              const pct = limit > 0 ? Math.min((section.total_amount / limit) * 100, 100) : 100;
              const isFull = limit > 0 && section.total_amount >= limit;

              return (
                <View 
                  key={section.section}
                  style={[styles.sectionCard, {
                    backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)',
                    borderColor: isDark ? 'rgba(139, 92, 246, 0.2)' : 'rgba(139, 92, 246, 0.15)',
                  }]}
                >
                  <View style={styles.sectionHeader}>
                    <View style={{ flex: 1 }}>
                      <Text style={[styles.sectionName, { color: colors.textPrimary }]}>
                        Section {section.section}
                      </Text>
                      <Text style={[styles.sectionDesc, { color: colors.textSecondary }]}>
                        {section.section_label}
                      </Text>
                    </View>
                    <View style={{ alignItems: 'flex-end' }}>
                      <Text style={[styles.sectionAmount, { color: isFull ? Accent.emerald : '#8B5CF6' }]}>
                        {formatINR(section.total_amount)}
                      </Text>
                      {limit > 0 && (
                        <Text style={[styles.sectionLimit, { color: colors.textSecondary }]}>
                          of {formatINRShort(limit)} limit
                        </Text>
                      )}
                    </View>
                  </View>

                  {/* Progress bar */}
                  {limit > 0 && (
                    <View style={[styles.progressTrack, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
                      <View 
                        style={[styles.progressFill, { 
                          width: `${pct}%`, 
                          backgroundColor: isFull ? Accent.emerald : '#8B5CF6' 
                        }]} 
                      />
                    </View>
                  )}

                  {/* Transactions in this section */}
                  <View style={styles.txnList}>
                    {section.transactions.map((txn: any) => (
                      <View 
                        key={txn.id}
                        style={[styles.txnItem, {
                          backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
                        }]}
                      >
                        <View style={{ flex: 1 }}>
                          <Text style={[styles.txnName, { color: colors.textPrimary }]} numberOfLines={1}>
                            {txn.name}
                          </Text>
                          <Text style={[styles.txnDate, { color: colors.textSecondary }]}>
                            {txn.source_date}
                          </Text>
                        </View>
                        <Text style={[styles.txnAmount, { color: colors.textPrimary }]}>
                          {formatINR(txn.amount)}
                        </Text>
                        
                        <View style={styles.txnActions}>
                          <TouchableOpacity
                            style={[styles.actionBtn, { backgroundColor: 'rgba(16, 185, 129, 0.15)' }]}
                            onPress={() => {
                              onApprove(txn);
                            }}
                          >
                            <MaterialCommunityIcons name="check" size={16} color={Accent.emerald} />
                          </TouchableOpacity>
                          <TouchableOpacity
                            style={[styles.actionBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)' }]}
                            onPress={() => onEdit(txn)}
                          >
                            <MaterialCommunityIcons name="pencil" size={14} color={colors.textSecondary} />
                          </TouchableOpacity>
                          <TouchableOpacity
                            style={[styles.actionBtn, { backgroundColor: 'rgba(239, 68, 68, 0.15)' }]}
                            onPress={() => onDismiss(txn)}
                          >
                            <MaterialCommunityIcons name="close" size={16} color="#EF4444" />
                          </TouchableOpacity>
                        </View>
                      </View>
                    ))}
                  </View>
                </View>
              );
            })}

            {/* Tax Saving Tip */}
            <View style={[styles.tipCard, { backgroundColor: isDark ? 'rgba(245, 158, 11, 0.15)' : 'rgba(245, 158, 11, 0.1)' }]}>
              <MaterialCommunityIcons name="lightbulb-on-outline" size={20} color="#F59E0B" />
              <View style={{ flex: 1, marginLeft: 10 }}>
                <Text style={[styles.tipTitle, { color: '#F59E0B' }]}>Tax Saving Tip</Text>
                <Text style={[styles.tipText, { color: isDark ? '#FDE68A' : '#B45309' }]}>
                  {autoDeductions?.sections?.find((s: any) => s.section === '80C' && (sectionLimits['80C'] - s.total_amount) > 10000)
                    ? `You can save ₹${Math.round((sectionLimits['80C'] - (autoDeductions.sections.find((s: any) => s.section === '80C')?.total_amount || 0)) * 0.3).toLocaleString('en-IN')} more tax by maximizing your 80C limit`
                    : 'Review your deductions regularly to ensure maximum tax savings'
                  }
                </Text>
              </View>
            </View>
          </ScrollView>
        </View>
      </Modal>
    </>
  );
};

const styles = StyleSheet.create({
  floatingBar: {
    borderRadius: 16,
    borderWidth: 1.5,
    padding: 12,
    marginBottom: 16,
  },
  barContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  iconContainer: {
    width: 40,
    height: 40,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  barInfo: {
    flex: 1,
    marginLeft: 12,
  },
  barTitle: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  barSubtitle: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    marginTop: 2,
  },
  barActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  pendingBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 10,
  },
  pendingText: {
    color: '#FFF',
    fontSize: 11,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  miniProgress: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
    gap: 8,
  },
  miniLabel: {
    fontSize: 10,
    fontFamily: 'DM Sans',
    fontWeight: '600',
    width: 45,
  },
  miniTrack: {
    flex: 1,
    height: 4,
    borderRadius: 2,
    overflow: 'hidden',
  },
  miniFill: {
    height: '100%',
    borderRadius: 2,
  },
  miniValue: {
    fontSize: 10,
    fontFamily: 'DM Sans',
    fontWeight: '700',
    width: 30,
    textAlign: 'right',
  },
  modalContainer: {
    flex: 1,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
  },
  modalIcon: {
    width: 48,
    height: 48,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  modalTitle: {
    fontSize: 18,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  modalSubtitle: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    marginTop: 2,
  },
  closeBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  summaryRow: {
    flexDirection: 'row',
    padding: 16,
    gap: 12,
  },
  summaryCard: {
    flex: 1,
    padding: 14,
    borderRadius: 14,
    alignItems: 'center',
  },
  summaryLabel: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    fontWeight: '600',
    textTransform: 'uppercase',
  },
  summaryValue: {
    fontSize: 20,
    fontFamily: 'DM Sans',
    fontWeight: '700',
    marginTop: 4,
  },
  summaryCount: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    marginTop: 2,
  },
  sectionsList: {
    flex: 1,
    paddingHorizontal: 16,
  },
  listTitle: {
    fontSize: 15,
    fontFamily: 'DM Sans',
    fontWeight: '700',
    marginBottom: 12,
  },
  sectionCard: {
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderLeftWidth: 3,
    borderLeftColor: '#8B5CF6',
    marginBottom: 12,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  sectionName: {
    fontSize: 15,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  sectionDesc: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    marginTop: 2,
  },
  sectionAmount: {
    fontSize: 16,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  sectionLimit: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    marginTop: 2,
  },
  progressTrack: {
    height: 6,
    borderRadius: 3,
    overflow: 'hidden',
    marginBottom: 12,
  },
  progressFill: {
    height: '100%',
    borderRadius: 3,
  },
  txnList: {
    gap: 6,
  },
  txnItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 10,
    borderRadius: 10,
  },
  txnName: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    fontWeight: '500',
  },
  txnDate: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    marginTop: 2,
  },
  txnAmount: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    fontWeight: '600',
    marginLeft: 8,
  },
  txnActions: {
    flexDirection: 'row',
    gap: 6,
    marginLeft: 10,
  },
  actionBtn: {
    width: 28,
    height: 28,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tipCard: {
    flexDirection: 'row',
    padding: 14,
    borderRadius: 14,
    marginVertical: 16,
    alignItems: 'flex-start',
  },
  tipTitle: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    fontWeight: '700',
    marginBottom: 4,
  },
  tipText: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    lineHeight: 18,
  },
});
