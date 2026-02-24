import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  RefreshControl, ActivityIndicator, Modal, Alert,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useTheme } from '../context/ThemeContext';
import { apiRequest } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { formatINR, formatINRShort } from '../utils/formatters';
import { Accent } from '../utils/theme';

type EMISummary = {
  total_monthly_emi: number;
  total_outstanding: number;
  total_principal: number;
  total_paid: number;
  active_count: number;
  overall_progress: number;
};

type ActiveEMI = {
  id: string;
  name: string;
  loan_type: string;
  lender: string;
  principal_amount: number;
  interest_rate: number;
  tenure_months: number;
  emi_amount: number;
  outstanding: number;
  total_paid: number;
  principal_paid: number;
  interest_paid: number;
  remaining_emis: number;
  paid_emis: number;
  progress: number;
  start_date: string;
  next_emi_date: string | null;
  source: string;
};

type UpcomingPayment = {
  loan_id: string;
  loan_name: string;
  amount: number;
  due_date: string;
  principal: number;
  interest: number;
  status: string;
};

type Props = {
  visible: boolean;
  onClose: () => void;
};

export default function EMITrackerModal({ visible, onClose }: Props) {
  const { colors, isDark } = useTheme();
  const { token } = useAuth();
  
  const [summary, setSummary] = useState<EMISummary | null>(null);
  const [activeEMIs, setActiveEMIs] = useState<ActiveEMI[]>([]);
  const [upcomingPayments, setUpcomingPayments] = useState<UpcomingPayment[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedEMI, setSelectedEMI] = useState<ActiveEMI | null>(null);

  const fetchData = useCallback(async () => {
    if (!token) return;
    try {
      const data = await apiRequest('/emi-tracker/dashboard', { token });
      setSummary(data.summary);
      setActiveEMIs(data.active_emis || []);
      setUpcomingPayments(data.upcoming_payments || []);
    } catch (error) {
      console.error('Error fetching EMI data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token]);

  useEffect(() => {
    if (visible) {
      fetchData();
    }
  }, [visible, fetchData]);

  const getLoanTypeIcon = (type: string) => {
    const typeMap: Record<string, string> = {
      'Home': 'home',
      'Car': 'car',
      'Personal': 'account-cash',
      'Education': 'school',
      'Credit Card EMI': 'credit-card',
      'Other': 'cash',
    };
    return typeMap[type] || 'cash';
  };

  const getLoanTypeColor = (type: string) => {
    const colorMap: Record<string, string> = {
      'Home': Accent.sapphire,
      'Car': Accent.emerald,
      'Personal': Accent.amber,
      'Education': Accent.amethyst,
      'Credit Card EMI': '#8B5CF6',
      'Other': colors.textSecondary,
    };
    return colorMap[type] || colors.textSecondary;
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  const getDaysUntil = (dateStr: string) => {
    if (!dateStr) return null;
    const today = new Date();
    const dueDate = new Date(dateStr);
    const diff = Math.ceil((dueDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
    return diff;
  };

  return (
    <Modal visible={visible} animationType="slide" transparent>
      <View style={styles.overlay}>
        <View style={[styles.container, { backgroundColor: colors.card }]}>
          {/* Header */}
          <View style={styles.header}>
            <View style={styles.headerLeft}>
              <View style={[styles.headerIcon, { backgroundColor: isDark ? 'rgba(245, 158, 11, 0.15)' : 'rgba(245, 158, 11, 0.1)' }]}>
                <MaterialCommunityIcons name="calendar-clock" size={24} color={Accent.amber} />
              </View>
              <View>
                <Text style={[styles.title, { color: colors.textPrimary }]}>EMI Tracker</Text>
                <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
                  Track all your loan payments
                </Text>
              </View>
            </View>
            <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
              <MaterialCommunityIcons name="close" size={24} color={colors.textSecondary} />
            </TouchableOpacity>
          </View>

          <ScrollView
            style={styles.scrollView}
            refreshControl={
              <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); fetchData(); }} />
            }
            showsVerticalScrollIndicator={false}
          >
            {loading ? (
              <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color={colors.primary} />
              </View>
            ) : (
              <>
                {/* Summary Cards */}
                {summary && (
                  <View style={styles.summarySection}>
                    <LinearGradient
                      colors={isDark ? ['#1E3A5F', '#0F2847'] : ['#EEF2FF', '#E0E7FF']}
                      style={styles.summaryCard}
                    >
                      <View style={styles.summaryRow}>
                        <View style={styles.summaryItem}>
                          <Text style={[styles.summaryLabel, { color: isDark ? 'rgba(255,255,255,0.7)' : colors.textSecondary }]}>
                            Monthly EMI
                          </Text>
                          <Text style={[styles.summaryValue, { color: isDark ? '#fff' : colors.textPrimary }]}>
                            {formatINR(summary.total_monthly_emi)}
                          </Text>
                        </View>
                        <View style={[styles.summaryDivider, { backgroundColor: isDark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.08)' }]} />
                        <View style={styles.summaryItem}>
                          <Text style={[styles.summaryLabel, { color: isDark ? 'rgba(255,255,255,0.7)' : colors.textSecondary }]}>
                            Outstanding
                          </Text>
                          <Text style={[styles.summaryValue, { color: Accent.ruby }]}>
                            {formatINRShort(summary.total_outstanding)}
                          </Text>
                        </View>
                        <View style={[styles.summaryDivider, { backgroundColor: isDark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.08)' }]} />
                        <View style={styles.summaryItem}>
                          <Text style={[styles.summaryLabel, { color: isDark ? 'rgba(255,255,255,0.7)' : colors.textSecondary }]}>
                            Paid So Far
                          </Text>
                          <Text style={[styles.summaryValue, { color: Accent.emerald }]}>
                            {formatINRShort(summary.total_paid)}
                          </Text>
                        </View>
                      </View>

                      {/* Overall Progress */}
                      <View style={styles.overallProgress}>
                        <View style={styles.progressHeader}>
                          <Text style={[styles.progressLabel, { color: isDark ? 'rgba(255,255,255,0.7)' : colors.textSecondary }]}>
                            Overall Repayment Progress
                          </Text>
                          <Text style={[styles.progressValue, { color: isDark ? '#fff' : colors.textPrimary }]}>
                            {summary.overall_progress}%
                          </Text>
                        </View>
                        <View style={[styles.progressBar, { backgroundColor: isDark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.08)' }]}>
                          <LinearGradient
                            colors={[Accent.emerald, '#34D399']}
                            start={{ x: 0, y: 0 }}
                            end={{ x: 1, y: 0 }}
                            style={[styles.progressFill, { width: `${Math.min(summary.overall_progress, 100)}%` }]}
                          />
                        </View>
                      </View>
                    </LinearGradient>
                  </View>
                )}

                {/* Upcoming Payments */}
                {upcomingPayments.length > 0 && (
                  <View style={styles.section}>
                    <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>
                      Upcoming Payments
                    </Text>
                    {upcomingPayments.map((payment, index) => {
                      const daysUntil = getDaysUntil(payment.due_date);
                      return (
                        <View
                          key={`${payment.loan_id}-${index}`}
                          style={[styles.upcomingCard, {
                            backgroundColor: isDark ? 'rgba(239, 68, 68, 0.08)' : 'rgba(239, 68, 68, 0.05)',
                            borderColor: Accent.ruby,
                          }]}
                        >
                          <View style={styles.upcomingLeft}>
                            <Text style={[styles.upcomingName, { color: colors.textPrimary }]}>
                              {payment.loan_name}
                            </Text>
                            <Text style={[styles.upcomingDate, { color: colors.textSecondary }]}>
                              Due: {formatDate(payment.due_date)}
                              {daysUntil !== null && daysUntil >= 0 && (
                                <Text style={{ color: daysUntil <= 5 ? Accent.ruby : Accent.amber }}>
                                  {' '}({daysUntil === 0 ? 'Today' : `${daysUntil} days`})
                                </Text>
                              )}
                            </Text>
                          </View>
                          <View style={styles.upcomingRight}>
                            <Text style={[styles.upcomingAmount, { color: Accent.ruby }]}>
                              {formatINR(payment.amount)}
                            </Text>
                            <Text style={[styles.upcomingBreakdown, { color: colors.textSecondary }]}>
                              P: {formatINRShort(payment.principal)} | I: {formatINRShort(payment.interest)}
                            </Text>
                          </View>
                        </View>
                      );
                    })}
                  </View>
                )}

                {/* Active EMIs */}
                <View style={styles.section}>
                  <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>
                    Active Loans & EMIs ({activeEMIs.length})
                  </Text>
                  
                  {activeEMIs.length === 0 ? (
                    <View style={[styles.emptyState, { backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)' }]}>
                      <MaterialCommunityIcons name="check-circle-outline" size={48} color={Accent.emerald} />
                      <Text style={[styles.emptyTitle, { color: colors.textPrimary }]}>No Active EMIs</Text>
                      <Text style={[styles.emptySubtitle, { color: colors.textSecondary }]}>
                        You don't have any active loans or EMI payments.
                      </Text>
                    </View>
                  ) : (
                    activeEMIs.map((emi) => {
                      const typeColor = getLoanTypeColor(emi.loan_type);
                      return (
                        <TouchableOpacity
                          key={emi.id}
                          style={[styles.emiCard, {
                            backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : '#fff',
                            borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
                          }]}
                          onPress={() => setSelectedEMI(emi)}
                          activeOpacity={0.7}
                        >
                          {/* Header */}
                          <View style={styles.emiHeader}>
                            <View style={[styles.emiIcon, { backgroundColor: `${typeColor}15` }]}>
                              <MaterialCommunityIcons 
                                name={getLoanTypeIcon(emi.loan_type) as any} 
                                size={22} 
                                color={typeColor} 
                              />
                            </View>
                            <View style={styles.emiInfo}>
                              <Text style={[styles.emiName, { color: colors.textPrimary }]} numberOfLines={1}>
                                {emi.name}
                              </Text>
                              <Text style={[styles.emiLender, { color: colors.textSecondary }]}>
                                {emi.lender || emi.loan_type}
                              </Text>
                            </View>
                            <View style={styles.emiAmountBox}>
                              <Text style={[styles.emiAmountLabel, { color: colors.textSecondary }]}>EMI</Text>
                              <Text style={[styles.emiAmount, { color: Accent.amber }]}>
                                {formatINR(emi.emi_amount)}
                              </Text>
                            </View>
                          </View>

                          {/* Progress Bar */}
                          {emi.source === 'loan' && (
                            <View style={styles.emiProgress}>
                              <View style={styles.progressHeader}>
                                <Text style={[styles.progressLabel, { color: colors.textSecondary }]}>
                                  {emi.paid_emis} of {emi.tenure_months} EMIs paid
                                </Text>
                                <Text style={[styles.progressValue, { color: typeColor }]}>
                                  {emi.progress}%
                                </Text>
                              </View>
                              <View style={[styles.progressBar, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.06)' }]}>
                                <View style={[styles.progressFill, { width: `${emi.progress}%`, backgroundColor: typeColor }]} />
                              </View>
                            </View>
                          )}

                          {/* Stats Row */}
                          <View style={styles.emiStats}>
                            <View style={styles.emiStat}>
                              <Text style={[styles.emiStatLabel, { color: colors.textSecondary }]}>Outstanding</Text>
                              <Text style={[styles.emiStatValue, { color: Accent.ruby }]}>
                                {formatINRShort(emi.outstanding)}
                              </Text>
                            </View>
                            <View style={styles.emiStat}>
                              <Text style={[styles.emiStatLabel, { color: colors.textSecondary }]}>Paid</Text>
                              <Text style={[styles.emiStatValue, { color: Accent.emerald }]}>
                                {formatINRShort(emi.total_paid)}
                              </Text>
                            </View>
                            {emi.next_emi_date && (
                              <View style={styles.emiStat}>
                                <Text style={[styles.emiStatLabel, { color: colors.textSecondary }]}>Next EMI</Text>
                                <Text style={[styles.emiStatValue, { color: colors.textPrimary }]}>
                                  {formatDate(emi.next_emi_date).split(',')[0]}
                                </Text>
                              </View>
                            )}
                          </View>
                        </TouchableOpacity>
                      );
                    })
                  )}
                </View>

                <View style={{ height: 40 }} />
              </>
            )}
          </ScrollView>

          {/* EMI Detail Modal */}
          <Modal visible={!!selectedEMI} animationType="slide" transparent>
            <View style={styles.detailOverlay}>
              <View style={[styles.detailContainer, { backgroundColor: colors.card }]}>
                {selectedEMI && (
                  <>
                    <View style={styles.detailHeader}>
                      <Text style={[styles.detailTitle, { color: colors.textPrimary }]}>
                        {selectedEMI.name}
                      </Text>
                      <TouchableOpacity onPress={() => setSelectedEMI(null)}>
                        <MaterialCommunityIcons name="close" size={24} color={colors.textSecondary} />
                      </TouchableOpacity>
                    </View>

                    <ScrollView showsVerticalScrollIndicator={false}>
                      {/* Loan Info */}
                      <View style={[styles.detailSection, { borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
                        <View style={styles.detailRow}>
                          <Text style={[styles.detailLabel, { color: colors.textSecondary }]}>Loan Type</Text>
                          <Text style={[styles.detailValue, { color: colors.textPrimary }]}>{selectedEMI.loan_type}</Text>
                        </View>
                        <View style={styles.detailRow}>
                          <Text style={[styles.detailLabel, { color: colors.textSecondary }]}>Lender</Text>
                          <Text style={[styles.detailValue, { color: colors.textPrimary }]}>{selectedEMI.lender || '-'}</Text>
                        </View>
                        {selectedEMI.principal_amount > 0 && (
                          <>
                            <View style={styles.detailRow}>
                              <Text style={[styles.detailLabel, { color: colors.textSecondary }]}>Principal Amount</Text>
                              <Text style={[styles.detailValue, { color: colors.textPrimary }]}>{formatINR(selectedEMI.principal_amount)}</Text>
                            </View>
                            <View style={styles.detailRow}>
                              <Text style={[styles.detailLabel, { color: colors.textSecondary }]}>Interest Rate</Text>
                              <Text style={[styles.detailValue, { color: colors.textPrimary }]}>{selectedEMI.interest_rate}% p.a.</Text>
                            </View>
                            <View style={styles.detailRow}>
                              <Text style={[styles.detailLabel, { color: colors.textSecondary }]}>Tenure</Text>
                              <Text style={[styles.detailValue, { color: colors.textPrimary }]}>{selectedEMI.tenure_months} months</Text>
                            </View>
                          </>
                        )}
                      </View>

                      {/* Payment Info */}
                      <View style={[styles.detailSection, { borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
                        <View style={styles.detailRow}>
                          <Text style={[styles.detailLabel, { color: colors.textSecondary }]}>Monthly EMI</Text>
                          <Text style={[styles.detailValue, { color: Accent.amber, fontWeight: '700' }]}>{formatINR(selectedEMI.emi_amount)}</Text>
                        </View>
                        <View style={styles.detailRow}>
                          <Text style={[styles.detailLabel, { color: colors.textSecondary }]}>Outstanding</Text>
                          <Text style={[styles.detailValue, { color: Accent.ruby }]}>{formatINR(selectedEMI.outstanding)}</Text>
                        </View>
                        <View style={styles.detailRow}>
                          <Text style={[styles.detailLabel, { color: colors.textSecondary }]}>Total Paid</Text>
                          <Text style={[styles.detailValue, { color: Accent.emerald }]}>{formatINR(selectedEMI.total_paid)}</Text>
                        </View>
                        {selectedEMI.principal_paid > 0 && (
                          <>
                            <View style={styles.detailRow}>
                              <Text style={[styles.detailLabel, { color: colors.textSecondary }]}>Principal Paid</Text>
                              <Text style={[styles.detailValue, { color: colors.textPrimary }]}>{formatINR(selectedEMI.principal_paid)}</Text>
                            </View>
                            <View style={styles.detailRow}>
                              <Text style={[styles.detailLabel, { color: colors.textSecondary }]}>Interest Paid</Text>
                              <Text style={[styles.detailValue, { color: colors.textPrimary }]}>{formatINR(selectedEMI.interest_paid)}</Text>
                            </View>
                          </>
                        )}
                      </View>

                      {/* Progress */}
                      {selectedEMI.source === 'loan' && (
                        <View style={[styles.detailSection, { borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
                          <Text style={[styles.detailSectionTitle, { color: colors.textPrimary }]}>Repayment Progress</Text>
                          <View style={styles.progressCircle}>
                            <View style={[styles.progressCircleInner, { borderColor: getLoanTypeColor(selectedEMI.loan_type) }]}>
                              <Text style={[styles.progressCircleValue, { color: getLoanTypeColor(selectedEMI.loan_type) }]}>
                                {selectedEMI.progress}%
                              </Text>
                              <Text style={[styles.progressCircleLabel, { color: colors.textSecondary }]}>Complete</Text>
                            </View>
                          </View>
                          <View style={styles.progressStats}>
                            <View style={styles.progressStatItem}>
                              <Text style={[styles.progressStatValue, { color: Accent.emerald }]}>{selectedEMI.paid_emis}</Text>
                              <Text style={[styles.progressStatLabel, { color: colors.textSecondary }]}>Paid</Text>
                            </View>
                            <View style={styles.progressStatItem}>
                              <Text style={[styles.progressStatValue, { color: Accent.amber }]}>{selectedEMI.remaining_emis}</Text>
                              <Text style={[styles.progressStatLabel, { color: colors.textSecondary }]}>Remaining</Text>
                            </View>
                            <View style={styles.progressStatItem}>
                              <Text style={[styles.progressStatValue, { color: colors.textPrimary }]}>{selectedEMI.tenure_months}</Text>
                              <Text style={[styles.progressStatLabel, { color: colors.textSecondary }]}>Total</Text>
                            </View>
                          </View>
                        </View>
                      )}

                      <View style={{ height: 30 }} />
                    </ScrollView>
                  </>
                )}
              </View>
            </View>
          </Modal>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  container: {
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: '92%',
    minHeight: '70%',
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
    fontWeight: '700',
  },
  subtitle: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    marginTop: 2,
  },
  closeBtn: {
    padding: 8,
  },
  scrollView: {
    flex: 1,
  },
  loadingContainer: {
    paddingVertical: 60,
    alignItems: 'center',
  },
  summarySection: {
    paddingHorizontal: 20,
    marginBottom: 20,
  },
  summaryCard: {
    borderRadius: 16,
    padding: 16,
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  summaryItem: {
    flex: 1,
    alignItems: 'center',
  },
  summaryDivider: {
    width: 1,
    height: 40,
  },
  summaryLabel: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    marginBottom: 4,
  },
  summaryValue: {
    fontSize: 16,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  overallProgress: {
    marginTop: 16,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.1)',
  },
  progressHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  progressLabel: {
    fontSize: 12,
    fontFamily: 'DM Sans',
  },
  progressValue: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    fontWeight: '600',
  },
  progressBar: {
    height: 8,
    borderRadius: 4,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 4,
  },
  section: {
    paddingHorizontal: 20,
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 16,
    fontFamily: 'DM Sans',
    fontWeight: '600',
    marginBottom: 12,
  },
  upcomingCard: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 14,
    borderRadius: 12,
    borderLeftWidth: 3,
    marginBottom: 10,
  },
  upcomingLeft: {
    flex: 1,
  },
  upcomingName: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    fontWeight: '600',
  },
  upcomingDate: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    marginTop: 4,
  },
  upcomingRight: {
    alignItems: 'flex-end',
  },
  upcomingAmount: {
    fontSize: 16,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  upcomingBreakdown: {
    fontSize: 10,
    fontFamily: 'DM Sans',
    marginTop: 2,
  },
  emptyState: {
    padding: 40,
    borderRadius: 16,
    alignItems: 'center',
  },
  emptyTitle: {
    fontSize: 16,
    fontFamily: 'DM Sans',
    fontWeight: '600',
    marginTop: 12,
  },
  emptySubtitle: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    marginTop: 6,
    textAlign: 'center',
  },
  emiCard: {
    borderRadius: 16,
    borderWidth: 1,
    padding: 16,
    marginBottom: 12,
  },
  emiHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 14,
  },
  emiIcon: {
    width: 44,
    height: 44,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emiInfo: {
    flex: 1,
    marginLeft: 12,
  },
  emiName: {
    fontSize: 15,
    fontFamily: 'DM Sans',
    fontWeight: '600',
  },
  emiLender: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    marginTop: 2,
  },
  emiAmountBox: {
    alignItems: 'flex-end',
  },
  emiAmountLabel: {
    fontSize: 10,
    fontFamily: 'DM Sans',
  },
  emiAmount: {
    fontSize: 16,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  emiProgress: {
    marginBottom: 14,
  },
  emiStats: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: 'rgba(128,128,128,0.15)',
  },
  emiStat: {
    alignItems: 'center',
  },
  emiStatLabel: {
    fontSize: 10,
    fontFamily: 'DM Sans',
    marginBottom: 4,
  },
  emiStatValue: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    fontWeight: '600',
  },
  // Detail Modal
  detailOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  detailContainer: {
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: '80%',
    padding: 20,
  },
  detailHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  detailTitle: {
    fontSize: 18,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  detailSection: {
    paddingVertical: 16,
    borderBottomWidth: 1,
  },
  detailSectionTitle: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    fontWeight: '600',
    marginBottom: 16,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  detailLabel: {
    fontSize: 13,
    fontFamily: 'DM Sans',
  },
  detailValue: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    fontWeight: '500',
  },
  progressCircle: {
    alignItems: 'center',
    marginBottom: 20,
  },
  progressCircleInner: {
    width: 100,
    height: 100,
    borderRadius: 50,
    borderWidth: 6,
    alignItems: 'center',
    justifyContent: 'center',
  },
  progressCircleValue: {
    fontSize: 24,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  progressCircleLabel: {
    fontSize: 11,
    fontFamily: 'DM Sans',
  },
  progressStats: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  progressStatItem: {
    alignItems: 'center',
  },
  progressStatValue: {
    fontSize: 20,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  progressStatLabel: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    marginTop: 4,
  },
});
