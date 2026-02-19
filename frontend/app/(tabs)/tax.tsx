import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, RefreshControl,
  ActivityIndicator, Dimensions, Platform, StatusBar, Modal,
  TextInput, KeyboardAvoidingView, Alert,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useAuth } from '../../src/context/AuthContext';
import { useTheme } from '../../src/context/ThemeContext';
import { useScreenContext } from '../../src/context/ScreenContext';
import { Accent } from '../../src/utils/theme';
import { apiRequest } from '../../src/utils/api';
import { formatINR, formatINRShort } from '../../src/utils/formatters';
import TaxDeductionsModal from '../../src/components/TaxDeductionsModal';
import { TaxDeduction } from '../../src/data/taxDeductions';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// Financial Year options
const FY_OPTIONS = [
  { fy: '2025-26', ay: '2026-27', label: 'FY 2025-26' },
  { fy: '2024-25', ay: '2025-26', label: 'FY 2024-25' },
  { fy: '2023-24', ay: '2024-25', label: 'FY 2023-24' },
];

export default function TaxScreen() {
  const { token } = useAuth();
  const { colors, isDark } = useTheme();
  const { setCurrentScreen } = useScreenContext();
  const insets = useSafeAreaInsets();
  const HEADER_HEIGHT = 70 + insets.top;

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedFY, setSelectedFY] = useState(FY_OPTIONS[0]);
  const [showFYPicker, setShowFYPicker] = useState(false);

  // Tax Planning state
  const [taxData, setTaxData] = useState<any>(null);
  const [userTaxDeductions, setUserTaxDeductions] = useState<any[]>([]);
  const [userDeductions, setUserDeductions] = useState<string[]>([]);
  const [showTaxDeductionsModal, setShowTaxDeductionsModal] = useState(false);
  const [editingDeduction, setEditingDeduction] = useState<any | null>(null);
  const [showEditDeductionModal, setShowEditDeductionModal] = useState(false);
  const [deductionAmount, setDeductionAmount] = useState('');

  // Auto-detected deductions state
  const [autoDeductions, setAutoDeductions] = useState<any>(null);
  const [editingAutoDeduction, setEditingAutoDeduction] = useState<any | null>(null);
  const [showEditAutoModal, setShowEditAutoModal] = useState(false);
  const [autoDeductionAmount, setAutoDeductionAmount] = useState('');

  // Capital Gains state
  const [capitalGainsData, setCapitalGainsData] = useState<any>(null);

  // Tax Calculator state
  const [taxCalcData, setTaxCalcData] = useState<any>(null);
  const [activeRegime, setActiveRegime] = useState<'old' | 'new'>('new');

  // Set screen context for AI awareness
  useEffect(() => {
    setCurrentScreen('tax');
  }, [setCurrentScreen]);

  const fetchData = useCallback(async () => {
    if (!token) return;
    try {
      const [taxSummary, userTaxDeductionsData, capGains, taxCalc, autoDeductionsData] = await Promise.all([
        apiRequest('/tax-summary', { token }),
        apiRequest('/user-tax-deductions', { token }),
        apiRequest('/capital-gains', { token }),
        apiRequest(`/tax-calculator?fy=${selectedFY.fy}`, { token }),
        apiRequest(`/auto-tax-deductions?fy=${selectedFY.fy}`, { token }),
      ]);
      setTaxData(taxSummary);
      setCapitalGainsData(capGains);
      setTaxCalcData(taxCalc);
      setAutoDeductions(autoDeductionsData);
      if (userTaxDeductionsData?.deductions) {
        setUserTaxDeductions(userTaxDeductionsData.deductions);
        setUserDeductions(userTaxDeductionsData.deductions.map((d: any) => d.deduction_id));
      }
    } catch (e) {
      console.error('[Tax] Error fetching data:', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token, selectedFY]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const onRefresh = () => { setRefreshing(true); fetchData(); };

  // Tax Deduction Handlers
  const handleAddUserDeduction = async (deduction: TaxDeduction) => {
    if (!token) return;
    try {
      const result = await apiRequest('/user-tax-deductions', {
        method: 'POST', token,
        body: { deduction_id: deduction.id, section: deduction.section, name: deduction.name, limit: deduction.limit, invested_amount: 0 },
      });
      setUserTaxDeductions(prev => [...prev, result]);
      setUserDeductions(prev => [...prev, deduction.id]);
    } catch (e: any) { Alert.alert('Error', e.message || 'Failed to add deduction'); }
  };

  const handleEditDeduction = (deduction: any) => {
    setEditingDeduction(deduction);
    setDeductionAmount(deduction.invested_amount?.toString() || '0');
    setShowEditDeductionModal(true);
  };

  const handleSaveDeductionAmount = async () => {
    if (!token || !editingDeduction) return;
    try {
      const amount = parseFloat(deductionAmount) || 0;
      await apiRequest(`/user-tax-deductions/${editingDeduction.id}`, { method: 'PUT', token, body: { invested_amount: amount } });
      setUserTaxDeductions(prev => prev.map(d => d.id === editingDeduction.id ? { ...d, invested_amount: amount } : d));
      setShowEditDeductionModal(false);
      setEditingDeduction(null);
      fetchData(); // Refresh tax calc
    } catch (e: any) { Alert.alert('Error', e.message || 'Failed to update amount'); }
  };

  const handleDeleteDeduction = (deduction: any) => {
    Alert.alert('Remove Deduction', `Remove "${deduction.name}" from your tax planning?`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Remove', style: 'destructive', onPress: async () => {
        if (!token) return;
        try {
          await apiRequest(`/user-tax-deductions/${deduction.id}`, { method: 'DELETE', token });
          setUserTaxDeductions(prev => prev.filter(d => d.id !== deduction.id));
          setUserDeductions(prev => prev.filter(id => id !== deduction.deduction_id));
          fetchData();
        } catch (e: any) { Alert.alert('Error', e.message || 'Failed to remove deduction'); }
      }},
    ]);
  };

  // Auto-detected deduction handlers
  const handleEditAutoDeduction = (txn: any) => {
    setEditingAutoDeduction(txn);
    setAutoDeductionAmount(txn.amount?.toString() || '0');
    setShowEditAutoModal(true);
  };

  const handleSaveAutoDeductionAmount = async () => {
    if (!token || !editingAutoDeduction) return;
    try {
      const amount = parseFloat(autoDeductionAmount) || 0;
      await apiRequest(`/auto-tax-deductions/${editingAutoDeduction.id}`, {
        method: 'PUT', token, body: { invested_amount: amount },
      });
      setShowEditAutoModal(false);
      setEditingAutoDeduction(null);
      fetchData();
    } catch (e: any) { Alert.alert('Error', e.message || 'Failed to update amount'); }
  };

  const handleDismissAutoDeduction = (txn: any) => {
    Alert.alert('Dismiss Deduction', `Remove this auto-detected deduction for "${txn.name}"?`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Dismiss', style: 'destructive', onPress: async () => {
        if (!token) return;
        try {
          await apiRequest(`/auto-tax-deductions/${txn.id}`, { method: 'DELETE', token });
          fetchData();
        } catch (e: any) { Alert.alert('Error', e.message || 'Failed to dismiss'); }
      }},
    ]);
  };

  const taxSections = taxData?.sections || [];
  const regimeData = taxCalcData ? (activeRegime === 'old' ? taxCalcData.old_regime : taxCalcData.new_regime) : null;

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: colors.background }]}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={Accent.amber} />
          <Text style={[styles.loadingText, { color: colors.textSecondary }]}>Calculating your taxes...</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <StatusBar barStyle={isDark ? 'light-content' : 'dark-content'} />

      {/* Header */}
      <View style={[styles.stickyHeader, { paddingTop: insets.top, backgroundColor: isDark ? '#000000' : '#FFFFFF' }]}>
        <View style={[styles.headerContent, { backgroundColor: isDark ? '#000000' : '#FFFFFF', borderBottomColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)' }]}>
          <View style={styles.headerLeft}>
            <Text data-testid="tax-header-title" style={[styles.headerTitle, { color: isDark ? '#F59E0B' : '#B45309' }]}>Tax</Text>
            <TouchableOpacity
              data-testid="fy-selector-btn"
              style={[styles.fyBadge, { backgroundColor: isDark ? 'rgba(245,158,11,0.15)' : 'rgba(245,158,11,0.1)' }]}
              onPress={() => setShowFYPicker(true)}
            >
              <Text style={[styles.fyBadgeText, { color: '#F59E0B' }]}>{selectedFY.label} (AY {selectedFY.ay})</Text>
              <MaterialCommunityIcons name="chevron-down" size={16} color="#F59E0B" />
            </TouchableOpacity>
          </View>
          <TouchableOpacity data-testid="tax-refresh-btn" style={[styles.refreshBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)' }]} onPress={onRefresh}>
            <MaterialCommunityIcons name="refresh" size={20} color="#F59E0B" />
          </TouchableOpacity>
        </View>
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={[styles.scrollContent, { paddingTop: HEADER_HEIGHT + 12 }]}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#F59E0B" />}
        showsVerticalScrollIndicator={false}
      >

        {/* ═══ SECTION 1: TAX PLANNING ═══ */}
        <View style={styles.taxPlanningHeader}>
          <View>
            <Text data-testid="tax-planning-title" style={[styles.sectionTitle, { color: colors.textPrimary, marginBottom: 0 }]}>Tax Planning</Text>
            <Text style={[styles.taxFyLabel, { color: colors.textSecondary, marginTop: 2 }]}>Chapter VI-A Deductions</Text>
          </View>
          <TouchableOpacity
            data-testid="add-deduction-btn"
            style={[styles.addDeductionBtn, { backgroundColor: isDark ? 'rgba(249,115,22,0.15)' : 'rgba(249,115,22,0.1)' }]}
            onPress={() => setShowTaxDeductionsModal(true)}
            activeOpacity={0.7}
          >
            <MaterialCommunityIcons name="plus" size={20} color="#F97316" />
          </TouchableOpacity>
        </View>

        {taxData?.tax_saved_30_slab > 0 && (
          <View data-testid="tax-saved-badge" style={[styles.taxSavedBadge, { backgroundColor: 'rgba(16,185,129,0.1)' }]}>
            <MaterialCommunityIcons name="cash-check" size={16} color={Accent.emerald} />
            <Text style={[styles.taxSavedText, { color: Accent.emerald }]}>
              Est. tax saved: {formatINR(taxData.tax_saved_30_slab)} (30% slab) / {formatINR(taxData.tax_saved_20_slab)} (20% slab)
            </Text>
          </View>
        )}

        {/* User-Added Tax Deductions */}
        {userTaxDeductions.length > 0 && (
          <View style={{ marginBottom: 16 }}>
            <Text style={[styles.taxSubsectionTitle, { color: colors.textSecondary, marginBottom: 10 }]}>Your Selected Deductions</Text>
            {userTaxDeductions.map((deduction: any) => {
              const pct = deduction.limit && deduction.limit > 0 ? Math.min((deduction.invested_amount / deduction.limit) * 100, 100) : 0;
              const isFull = deduction.limit > 0 && deduction.invested_amount >= deduction.limit;
              const barColor = isFull ? Accent.emerald : '#F97316';
              const remaining = deduction.limit ? Math.max(deduction.limit - deduction.invested_amount, 0) : null;
              return (
                <View key={deduction.id} data-testid={`user-deduction-${deduction.deduction_id}`} style={[styles.glassCard, {
                  backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.85)',
                  borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)', marginBottom: 10,
                }]}>
                  <View style={styles.taxHeader}>
                    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10, flex: 1 }}>
                      <View style={[styles.taxIconWrap, { backgroundColor: isFull ? 'rgba(16,185,129,0.12)' : 'rgba(249,115,22,0.12)' }]}>
                        <MaterialCommunityIcons name="file-document-check" size={18} color={isFull ? Accent.emerald : '#F97316'} />
                      </View>
                      <View style={{ flex: 1 }}>
                        <Text style={[styles.taxTitle, { color: colors.textPrimary }]}>{deduction.section}</Text>
                        <Text style={[styles.taxUsed, { color: colors.textSecondary }]} numberOfLines={1}>{deduction.name}</Text>
                      </View>
                    </View>
                    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                      <TouchableOpacity data-testid={`edit-deduction-${deduction.id}`} style={[styles.deductionActionBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)' }]} onPress={() => handleEditDeduction(deduction)}>
                        <MaterialCommunityIcons name="pencil" size={16} color={colors.textSecondary} />
                      </TouchableOpacity>
                      <TouchableOpacity data-testid={`delete-deduction-${deduction.id}`} style={[styles.deductionActionBtn, { backgroundColor: 'rgba(239,68,68,0.1)' }]} onPress={() => handleDeleteDeduction(deduction)}>
                        <MaterialCommunityIcons name="trash-can-outline" size={16} color="#EF4444" />
                      </TouchableOpacity>
                    </View>
                  </View>
                  <View style={styles.deductionAmountRow}>
                    <Text style={[styles.deductionAmountLabel, { color: colors.textSecondary }]}>Invested:</Text>
                    <Text style={[styles.deductionAmountValue, { color: colors.textPrimary }]}>
                      {formatINR(deduction.invested_amount || 0)}{deduction.limit ? ` / ${formatINRShort(deduction.limit)}` : ''}
                    </Text>
                  </View>
                  {deduction.limit > 0 && (
                    <>
                      <View style={[styles.taxBarBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
                        <View style={[styles.taxBarFill, { width: `${pct}%`, backgroundColor: barColor }]} />
                      </View>
                      {remaining !== null && remaining > 0 && (
                        <Text style={[styles.taxRemaining, { color: colors.textSecondary }]}>{formatINRShort(remaining)} remaining for max benefit</Text>
                      )}
                    </>
                  )}
                </View>
              );
            })}
          </View>
        )}

        {/* ═══ AUTO-DETECTED DEDUCTIONS FROM TRANSACTIONS ═══ */}
        {autoDeductions && autoDeductions.sections?.length > 0 && (
          <View style={{ marginBottom: 16 }}>
            <View style={[styles.autoDetectedHeader, { marginBottom: 10, marginTop: userTaxDeductions.length > 0 ? 4 : 0 }]}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                <MaterialCommunityIcons name="lightning-bolt" size={14} color="#8B5CF6" />
                <Text style={[styles.taxSubsectionTitle, { color: '#8B5CF6', marginBottom: 0 }]}>Auto-Detected from Transactions</Text>
              </View>
              <View style={[styles.autoCountBadge, { backgroundColor: 'rgba(139,92,246,0.12)' }]}>
                <Text style={{ fontSize: 10, fontWeight: '700', color: '#8B5CF6', fontFamily: 'DM Sans' }}>{autoDeductions.count}</Text>
              </View>
            </View>

            {autoDeductions.sections.map((section: any) => {
              const pct = section.limit > 0 ? Math.min((section.total_amount / section.limit) * 100, 100) : 0;
              const isFull = section.limit > 0 && section.total_amount >= section.limit;
              const barColor = isFull ? Accent.emerald : '#8B5CF6';
              return (
                <View key={section.section} data-testid={`auto-deduction-section-${section.section}`} style={[styles.glassCard, {
                  backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.85)',
                  borderColor: isDark ? 'rgba(139,92,246,0.15)' : 'rgba(139,92,246,0.1)',
                  borderLeftWidth: 3, borderLeftColor: '#8B5CF6', marginBottom: 10,
                }]}>
                  <View style={styles.taxHeader}>
                    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10, flex: 1 }}>
                      <View style={[styles.taxIconWrap, { backgroundColor: 'rgba(139,92,246,0.12)' }]}>
                        <MaterialCommunityIcons name="auto-fix" size={18} color="#8B5CF6" />
                      </View>
                      <View style={{ flex: 1 }}>
                        <Text style={[styles.taxTitle, { color: colors.textPrimary }]}>{section.section_label}</Text>
                        <Text style={[styles.taxUsed, { color: colors.textSecondary }]}>
                          {formatINRShort(section.total_amount)}{section.limit > 0 ? ` / ${formatINRShort(section.limit)}` : ''}
                        </Text>
                      </View>
                    </View>
                    {section.limit > 0 && (
                      <View style={[styles.taxPercentBadge, { backgroundColor: isFull ? 'rgba(16,185,129,0.1)' : 'rgba(139,92,246,0.1)' }]}>
                        <Text style={[styles.taxPercentText, { color: isFull ? Accent.emerald : '#8B5CF6' }]}>{pct.toFixed(0)}%</Text>
                      </View>
                    )}
                  </View>

                  {section.limit > 0 && (
                    <View style={[styles.taxBarBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
                      <View style={[styles.taxBarFill, { width: `${pct}%`, backgroundColor: barColor }]} />
                    </View>
                  )}

                  {/* Individual transactions */}
                  <View style={{ marginTop: 6, gap: 6 }}>
                    {section.transactions.map((txn: any) => (
                      <View key={txn.id} data-testid={`auto-deduction-txn-${txn.id}`} style={[styles.autoTxnRow, {
                        backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)',
                      }]}>
                        <View style={{ flex: 1 }}>
                          <Text style={[styles.autoTxnName, { color: colors.textPrimary }]} numberOfLines={1}>{txn.name}</Text>
                          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 2 }}>
                            <Text style={[styles.autoTxnMeta, { color: colors.textSecondary }]}>{txn.source_date}</Text>
                            <View style={[styles.autoTxnBadge, { backgroundColor: txn.detected_from === 'category' ? 'rgba(59,130,246,0.1)' : 'rgba(245,158,11,0.1)' }]}>
                              <Text style={{ fontSize: 9, fontWeight: '600', color: txn.detected_from === 'category' ? '#3B82F6' : '#F59E0B', fontFamily: 'DM Sans' }}>
                                {txn.detected_from === 'category' ? 'Category' : 'Keywords'}
                              </Text>
                            </View>
                          </View>
                        </View>
                        <Text style={[styles.autoTxnAmount, { color: colors.textPrimary }]}>{formatINR(txn.amount)}</Text>
                        <View style={{ flexDirection: 'row', gap: 6, marginLeft: 8 }}>
                          <TouchableOpacity data-testid={`edit-auto-${txn.id}`} style={[styles.deductionActionBtn, { width: 26, height: 26, backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)' }]} onPress={() => handleEditAutoDeduction(txn)}>
                            <MaterialCommunityIcons name="pencil" size={13} color={colors.textSecondary} />
                          </TouchableOpacity>
                          <TouchableOpacity data-testid={`dismiss-auto-${txn.id}`} style={[styles.deductionActionBtn, { width: 26, height: 26, backgroundColor: 'rgba(239,68,68,0.1)' }]} onPress={() => handleDismissAutoDeduction(txn)}>
                            <MaterialCommunityIcons name="close" size={13} color="#EF4444" />
                          </TouchableOpacity>
                        </View>
                      </View>
                    ))}
                  </View>
                </View>
              );
            })}
          </View>
        )}

        {/* System Tax Sections (auto-detected) */}
        {(() => {
          const activeTaxSections = taxSections.filter((sec: any) => sec.used > 0);
          if (activeTaxSections.length === 0) return null;
          return (
            <>
              <Text style={[styles.taxSubsectionTitle, { color: colors.textSecondary, marginBottom: 10, marginTop: userTaxDeductions.length > 0 ? 8 : 0 }]}>Auto-detected from Transactions</Text>
              {activeTaxSections.map((sec: any) => {
                const pct = sec.limit > 0 ? Math.min((sec.used / sec.limit) * 100, 100) : 0;
                const isFull = sec.limit > 0 && sec.used >= sec.limit;
                const barColor = isFull ? Accent.emerald : '#F97316';
                return (
                  <View key={sec.section} data-testid={`tax-section-${sec.section}`} style={[styles.glassCard, {
                    backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.85)',
                    borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)', marginBottom: 12,
                  }]}>
                    <View style={styles.taxHeader}>
                      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
                        <View style={[styles.taxIconWrap, { backgroundColor: isFull ? 'rgba(16,185,129,0.12)' : 'rgba(249,115,22,0.12)' }]}>
                          <MaterialCommunityIcons name={sec.icon || 'file-document-outline'} size={18} color={isFull ? Accent.emerald : '#F97316'} />
                        </View>
                        <View>
                          <Text style={[styles.taxTitle, { color: colors.textPrimary }]}>{sec.label}</Text>
                          <Text style={[styles.taxUsed, { color: colors.textSecondary }]}>{formatINRShort(sec.used)} {sec.limit > 0 ? `/ ${formatINRShort(sec.limit)}` : '(no limit)'}</Text>
                        </View>
                      </View>
                      {sec.limit > 0 && (
                        <View style={[styles.taxPercentBadge, { backgroundColor: isFull ? 'rgba(16,185,129,0.1)' : 'rgba(245,158,11,0.1)' }]}>
                          <Text style={[styles.taxPercentText, { color: isFull ? Accent.emerald : Accent.amber }]}>{pct.toFixed(0)}%</Text>
                        </View>
                      )}
                    </View>
                    {sec.limit > 0 && (
                      <View style={[styles.taxBarBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
                        <View style={[styles.taxBarFill, { width: `${pct}%`, backgroundColor: barColor }]} />
                      </View>
                    )}
                    {sec.items?.length > 0 && (
                      <View style={styles.taxItemsList}>
                        {sec.items.map((item: any, idx: number) => (
                          <View key={idx} style={styles.taxItemRow}>
                            <Text style={[styles.taxItemName, { color: colors.textSecondary }]}>{item.name}</Text>
                            <Text style={[styles.taxItemAmt, { color: colors.textPrimary }]}>{formatINR(item.amount)}</Text>
                          </View>
                        ))}
                      </View>
                    )}
                    {sec.remaining > 0 && (
                      <Text style={[styles.taxRemaining, { color: colors.textSecondary }]}>{formatINRShort(sec.remaining)} remaining</Text>
                    )}
                  </View>
                );
              })}
            </>
          );
        })()}

        {/* ═══ SECTION 2: CAPITAL GAINS / LOSS ═══ */}
        {capitalGainsData && (capitalGainsData.gains?.length > 0 || capitalGainsData.summary?.total_estimated_tax > 0) && (
          <View data-testid="capital-gains-section">
            <Text style={[styles.sectionTitle, { color: colors.textPrimary, marginTop: 20 }]}>Capital Gains / Loss</Text>
            <View style={[styles.glassCard, {
              backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.85)',
              borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)', marginBottom: 12,
            }]}>
              <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 }}>
                <View style={{ flex: 1 }}>
                  <Text style={[styles.taxUsed, { color: colors.textSecondary, marginBottom: 4 }]}>Short Term (STCG)</Text>
                  <Text style={[styles.taxTitle, { color: Accent.ruby }]}>{formatINR(capitalGainsData.summary?.total_stcg || 0)}</Text>
                  <Text style={{ fontSize: 11, color: colors.textSecondary, marginTop: 2 }}>Tax: {formatINR(capitalGainsData.summary?.estimated_stcg_tax || 0)}</Text>
                </View>
                <View style={{ flex: 1, alignItems: 'flex-end' }}>
                  <Text style={[styles.taxUsed, { color: colors.textSecondary, marginBottom: 4 }]}>Long Term (LTCG)</Text>
                  <Text style={[styles.taxTitle, { color: Accent.sapphire }]}>{formatINR(capitalGainsData.summary?.total_ltcg || 0)}</Text>
                  <Text style={{ fontSize: 11, color: colors.textSecondary, marginTop: 2 }}>Tax: {formatINR(capitalGainsData.summary?.estimated_ltcg_tax || 0)}</Text>
                </View>
              </View>
              {capitalGainsData.summary?.ltcg_exemption > 0 && capitalGainsData.summary?.total_ltcg > 0 && (
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, padding: 8, borderRadius: 8, backgroundColor: isDark ? 'rgba(59,130,246,0.1)' : 'rgba(59,130,246,0.06)', marginBottom: 10 }}>
                  <MaterialCommunityIcons name="information" size={14} color={Accent.sapphire} />
                  <Text style={{ fontSize: 11, color: colors.textSecondary, flex: 1 }}>LTCG exemption: {formatINR(capitalGainsData.summary.ltcg_exemption)} (Taxable: {formatINR(capitalGainsData.summary.ltcg_taxable)})</Text>
                </View>
              )}
              <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingTop: 10, borderTopWidth: 1, borderTopColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }}>
                <Text style={[styles.taxTitle, { color: colors.textPrimary }]}>Total Estimated Tax</Text>
                <Text style={[styles.taxTitle, { color: Accent.ruby, fontSize: 16 }]}>{formatINR(capitalGainsData.summary?.total_estimated_tax || 0)}</Text>
              </View>
            </View>

            {capitalGainsData.gains?.length > 0 && capitalGainsData.gains.map((gain: any, idx: number) => (
              <View key={idx} data-testid={`capital-gain-item-${idx}`} style={[styles.glassCard, {
                backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.85)',
                borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)', marginBottom: 8, padding: 14,
              }]}>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <Text style={[styles.taxTitle, { color: colors.textPrimary, flex: 1 }]} numberOfLines={1}>{gain.description}</Text>
                  <View style={[styles.taxPercentBadge, { backgroundColor: gain.is_long_term ? 'rgba(59,130,246,0.1)' : 'rgba(239,68,68,0.1)' }]}>
                    <Text style={[styles.taxPercentText, { color: gain.is_long_term ? Accent.sapphire : Accent.ruby, fontSize: 10 }]}>{gain.is_long_term ? 'LTCG' : 'STCG'}</Text>
                  </View>
                </View>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                  <Text style={{ fontSize: 12, color: colors.textSecondary }}>Sold: {formatINR(gain.sell_amount)} | Cost: {formatINR(gain.cost_basis)}</Text>
                  <Text style={{ fontSize: 13, fontWeight: '700', color: gain.gain_loss >= 0 ? Accent.emerald : Accent.ruby }}>{gain.gain_loss >= 0 ? '+' : ''}{formatINR(gain.gain_loss)}</Text>
                </View>
                <Text style={{ fontSize: 11, color: colors.textSecondary, marginTop: 4 }}>{gain.holding_days} days | Tax: {formatINR(gain.tax_liability)} @ {(gain.tax_rate * 100).toFixed(1)}%</Text>
              </View>
            ))}

            {capitalGainsData.notes?.length > 0 && (
              <View style={{ marginBottom: 16, paddingHorizontal: 4 }}>
                {capitalGainsData.notes.map((note: string, idx: number) => (
                  <Text key={idx} style={{ fontSize: 11, color: colors.textSecondary, marginBottom: 2 }}>* {note}</Text>
                ))}
              </View>
            )}
          </View>
        )}

        {/* Empty state for capital gains */}
        {(!capitalGainsData || (!capitalGainsData.gains?.length && !capitalGainsData.summary?.total_estimated_tax)) && (
          <View style={{ marginTop: 20 }}>
            <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Capital Gains / Loss</Text>
            <View style={[styles.emptyCard, { backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.85)', borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)' }]}>
              <MaterialCommunityIcons name="chart-timeline-variant" size={32} color={colors.textSecondary} />
              <Text style={[styles.emptyText, { color: colors.textSecondary }]}>No capital gains/losses recorded yet</Text>
            </View>
          </View>
        )}

        {/* ═══ SECTION 3: INCOME TAX CALCULATOR ═══ */}
        <Text style={[styles.sectionTitle, { color: colors.textPrimary, marginTop: 24 }]}>Income Tax Calculator</Text>

        {/* Regime Toggle */}
        <View data-testid="regime-toggle" style={[styles.regimeToggle, { backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)' }]}>
          <TouchableOpacity
            data-testid="old-regime-btn"
            style={[styles.regimeBtn, activeRegime === 'old' && { backgroundColor: isDark ? '#B45309' : '#F59E0B' }]}
            onPress={() => setActiveRegime('old')}
          >
            <Text style={[styles.regimeBtnText, { color: activeRegime === 'old' ? '#fff' : colors.textSecondary }]}>Old Regime</Text>
          </TouchableOpacity>
          <TouchableOpacity
            data-testid="new-regime-btn"
            style={[styles.regimeBtn, activeRegime === 'new' && { backgroundColor: isDark ? '#B45309' : '#F59E0B' }]}
            onPress={() => setActiveRegime('new')}
          >
            <Text style={[styles.regimeBtnText, { color: activeRegime === 'new' ? '#fff' : colors.textSecondary }]}>New Regime</Text>
          </TouchableOpacity>
        </View>

        {/* Comparison Banner */}
        {taxCalcData?.comparison && taxCalcData.comparison.better_regime !== 'equal' && (
          <View data-testid="regime-comparison-banner" style={[styles.comparisonBanner, {
            backgroundColor: isDark ? 'rgba(16,185,129,0.1)' : 'rgba(16,185,129,0.06)',
            borderColor: isDark ? 'rgba(16,185,129,0.25)' : 'rgba(16,185,129,0.15)',
          }]}>
            <MaterialCommunityIcons name="lightbulb-on-outline" size={18} color={Accent.emerald} />
            <Text style={[styles.comparisonText, { color: Accent.emerald }]}>
              {taxCalcData.comparison.better_regime === 'new' ? 'New' : 'Old'} Regime saves you {formatINR(taxCalcData.comparison.savings)}
            </Text>
          </View>
        )}

        {taxCalcData && regimeData && (
          <>
            {/* Income Summary */}
            <View data-testid="income-summary-card" style={[styles.glassCard, {
              backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.85)',
              borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)', marginBottom: 12,
            }]}>
              <Text style={[styles.calcSectionTitle, { color: colors.textPrimary }]}>Income Summary</Text>
              <CalcRow label="Salary Income" value={taxCalcData.income.salary} colors={colors} />
              {taxCalcData.income.other > 0 && <CalcRow label="Other Income" value={taxCalcData.income.other} colors={colors} />}
              <CalcRow label="Gross Total Income" value={taxCalcData.income.gross_total} colors={colors} bold />
            </View>

            {/* Deductions */}
            <View data-testid="deductions-card" style={[styles.glassCard, {
              backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.85)',
              borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)', marginBottom: 12,
            }]}>
              <Text style={[styles.calcSectionTitle, { color: colors.textPrimary }]}>Deductions ({activeRegime === 'old' ? 'Old Regime' : 'New Regime'})</Text>
              <CalcRow label="Standard Deduction" value={regimeData.standard_deduction} colors={colors} />
              {activeRegime === 'old' && taxCalcData.deductions?.map((d: any, i: number) => (
                <CalcRow key={i} label={`${d.label} (${d.section})`} value={d.capped_amount} colors={colors} sublabel={d.limit ? `Limit: ${formatINRShort(d.limit)}` : undefined} />
              ))}
              {activeRegime === 'new' && regimeData.nps_deduction > 0 && (
                <CalcRow label="NPS 80CCD(1B)" value={regimeData.nps_deduction} colors={colors} />
              )}
              <CalcRow label="Total Deductions" value={regimeData.total_deductions} colors={colors} bold highlight="#F59E0B" />
            </View>

            {/* Tax Computation */}
            <View data-testid="tax-computation-card" style={[styles.glassCard, {
              backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.85)',
              borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)', marginBottom: 12,
            }]}>
              <Text style={[styles.calcSectionTitle, { color: colors.textPrimary }]}>Tax Computation</Text>
              <CalcRow label="Taxable Income" value={regimeData.taxable_income} colors={colors} bold />

              {/* Slab Breakdown */}
              {regimeData.slab_breakdown?.length > 0 && (
                <View style={[styles.slabSection, { borderTopColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)' }]}>
                  <Text style={[styles.slabTitle, { color: colors.textSecondary }]}>Slab-wise Tax</Text>
                  {regimeData.slab_breakdown.map((slab: any, i: number) => (
                    <View key={i} style={styles.slabRow}>
                      <View style={{ flex: 1 }}>
                        <Text style={[styles.slabRange, { color: colors.textSecondary }]}>{slab.range}</Text>
                        <Text style={[styles.slabRate, { color: colors.textSecondary }]}>@ {slab.rate} on {formatINRShort(slab.income)}</Text>
                      </View>
                      <Text style={[styles.slabTax, { color: colors.textPrimary }]}>{formatINR(slab.tax)}</Text>
                    </View>
                  ))}
                </View>
              )}

              <CalcRow label="Tax on Income" value={regimeData.tax_on_income} colors={colors} />
              {regimeData.rebate_87a > 0 && <CalcRow label="Less: Rebate u/s 87A" value={-regimeData.rebate_87a} colors={colors} highlight={Accent.emerald} />}
              <CalcRow label="Tax after Rebate" value={regimeData.tax_after_rebate} colors={colors} />
              {regimeData.surcharge > 0 && <CalcRow label="Add: Surcharge" value={regimeData.surcharge} colors={colors} />}
              <CalcRow label="Add: Cess (4%)" value={regimeData.cess} colors={colors} />
              <CalcRow label="Tax on Income" value={regimeData.total_tax_on_income} colors={colors} bold />
            </View>

            {/* Capital Gains Tax + Total */}
            <View data-testid="total-tax-card" style={[styles.glassCard, {
              backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.85)',
              borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)', marginBottom: 12,
            }]}>
              {taxCalcData.capital_gains.total_cg_tax > 0 && (
                <>
                  <CalcRow label="STCG Tax (20%)" value={taxCalcData.capital_gains.stcg_tax} colors={colors} />
                  <CalcRow label="LTCG Tax (12.5%)" value={taxCalcData.capital_gains.ltcg_tax} colors={colors} />
                  <CalcRow label="Total Capital Gains Tax" value={taxCalcData.capital_gains.total_cg_tax} colors={colors} />
                </>
              )}
              <View style={[styles.totalTaxRow, { borderTopColor: isDark ? 'rgba(245,158,11,0.3)' : 'rgba(245,158,11,0.2)' }]}>
                <Text style={[styles.totalTaxLabel, { color: colors.textPrimary }]}>Total Tax Liability</Text>
                <Text data-testid="total-tax-amount" style={[styles.totalTaxAmount, { color: Accent.ruby }]}>{formatINR(regimeData.total_tax)}</Text>
              </View>
              <View style={styles.effectiveRateRow}>
                <Text style={[styles.effectiveRateLabel, { color: colors.textSecondary }]}>Effective Tax Rate</Text>
                <Text style={[styles.effectiveRateValue, { color: '#F59E0B' }]}>
                  {activeRegime === 'old' ? taxCalcData.comparison.old_effective_rate : taxCalcData.comparison.new_effective_rate}%
                </Text>
              </View>
            </View>

            {/* Side-by-side Comparison */}
            <View data-testid="regime-comparison-card" style={[styles.glassCard, {
              backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.85)',
              borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)', marginBottom: 12,
            }]}>
              <Text style={[styles.calcSectionTitle, { color: colors.textPrimary }]}>Regime Comparison</Text>
              <View style={styles.comparisonGrid}>
                <View style={styles.comparisonCol}>
                  <Text style={[styles.comparisonColTitle, { color: colors.textSecondary }]}>Old Regime</Text>
                  <Text style={[styles.comparisonTax, { color: taxCalcData.comparison.better_regime === 'old' ? Accent.emerald : colors.textPrimary }]}>
                    {formatINR(taxCalcData.old_regime.total_tax)}
                  </Text>
                  <Text style={[styles.comparisonRate, { color: colors.textSecondary }]}>{taxCalcData.comparison.old_effective_rate}% eff.</Text>
                </View>
                <View style={[styles.comparisonDivider, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]} />
                <View style={styles.comparisonCol}>
                  <Text style={[styles.comparisonColTitle, { color: colors.textSecondary }]}>New Regime</Text>
                  <Text style={[styles.comparisonTax, { color: taxCalcData.comparison.better_regime === 'new' ? Accent.emerald : colors.textPrimary }]}>
                    {formatINR(taxCalcData.new_regime.total_tax)}
                  </Text>
                  <Text style={[styles.comparisonRate, { color: colors.textSecondary }]}>{taxCalcData.comparison.new_effective_rate}% eff.</Text>
                </View>
              </View>
            </View>

            {/* Tax Notes */}
            {taxCalcData.notes?.length > 0 && (
              <View style={[styles.notesCard, {
                backgroundColor: isDark ? 'rgba(245,158,11,0.06)' : 'rgba(245,158,11,0.04)',
                borderColor: isDark ? 'rgba(245,158,11,0.15)' : 'rgba(245,158,11,0.1)',
              }]}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                  <MaterialCommunityIcons name="information-outline" size={16} color="#F59E0B" />
                  <Text style={[styles.notesTitle, { color: '#F59E0B' }]}>Tax Rules (FY {selectedFY.fy})</Text>
                </View>
                {taxCalcData.notes.map((note: string, idx: number) => (
                  <Text key={idx} style={[styles.noteText, { color: colors.textSecondary }]}>* {note}</Text>
                ))}
              </View>
            )}
          </>
        )}

        {/* No income data */}
        {(!taxCalcData || taxCalcData.income.gross_total === 0) && (
          <View style={[styles.emptyCard, { backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.85)', borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)', marginTop: 12 }]}>
            <MaterialCommunityIcons name="calculator-variant-outline" size={36} color={colors.textSecondary} />
            <Text style={[styles.emptyText, { color: colors.textPrimary, fontWeight: '600', marginBottom: 4 }]}>Add Income to Calculate Tax</Text>
            <Text style={[styles.emptyText, { color: colors.textSecondary }]}>Record your salary and other income transactions to get a complete tax computation</Text>
          </View>
        )}

        <View style={{ height: 100 }} />
      </ScrollView>

      {/* FY Picker Modal */}
      <Modal visible={showFYPicker} transparent animationType="fade">
        <TouchableOpacity style={styles.modalOverlay} activeOpacity={1} onPress={() => setShowFYPicker(false)}>
          <View style={[styles.fyPickerCard, { backgroundColor: isDark ? '#1F2937' : '#FFFFFF' }]}>
            <Text style={[styles.fyPickerTitle, { color: colors.textPrimary }]}>Select Financial Year</Text>
            {FY_OPTIONS.map(opt => (
              <TouchableOpacity
                key={opt.fy}
                data-testid={`fy-option-${opt.fy}`}
                style={[styles.fyOption, selectedFY.fy === opt.fy && { backgroundColor: isDark ? 'rgba(245,158,11,0.15)' : 'rgba(245,158,11,0.1)' }]}
                onPress={() => { setSelectedFY(opt); setShowFYPicker(false); }}
              >
                <View>
                  <Text style={[styles.fyOptionLabel, { color: selectedFY.fy === opt.fy ? '#F59E0B' : colors.textPrimary }]}>{opt.label}</Text>
                  <Text style={[styles.fyOptionSub, { color: colors.textSecondary }]}>Assessment Year {opt.ay}</Text>
                </View>
                {selectedFY.fy === opt.fy && <MaterialCommunityIcons name="check-circle" size={20} color="#F59E0B" />}
              </TouchableOpacity>
            ))}
          </View>
        </TouchableOpacity>
      </Modal>

      {/* Edit Deduction Modal */}
      <Modal visible={showEditDeductionModal} transparent animationType="slide">
        <KeyboardAvoidingView style={styles.modalOverlay} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
          <View style={[styles.editModal, { backgroundColor: isDark ? '#1F2937' : '#FFFFFF' }]}>
            <Text style={[styles.editModalTitle, { color: colors.textPrimary }]}>Update Amount</Text>
            {editingDeduction && (
              <Text style={[styles.editModalSub, { color: colors.textSecondary }]}>{editingDeduction.section} - {editingDeduction.name}</Text>
            )}
            <TextInput
              data-testid="deduction-amount-input"
              style={[styles.editModalInput, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.04)', color: colors.textPrimary, borderColor: isDark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.1)' }]}
              placeholder="Enter invested amount"
              placeholderTextColor={colors.textSecondary}
              keyboardType="numeric"
              value={deductionAmount}
              onChangeText={setDeductionAmount}
            />
            <View style={styles.editModalBtns}>
              <TouchableOpacity style={[styles.editModalCancelBtn, { borderColor: colors.border }]} onPress={() => setShowEditDeductionModal(false)}>
                <Text style={[styles.editModalCancelText, { color: colors.textSecondary }]}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity data-testid="save-deduction-btn" style={styles.editModalSaveBtn} onPress={handleSaveDeductionAmount}>
                <Text style={styles.editModalSaveText}>Save</Text>
              </TouchableOpacity>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>

      {/* Tax Deductions Browser Modal */}
      <TaxDeductionsModal
        visible={showTaxDeductionsModal}
        onClose={() => setShowTaxDeductionsModal(false)}
        onAddDeduction={handleAddUserDeduction}
        colors={colors}
        isDark={isDark}
        userDeductions={userDeductions}
      />
    </View>
  );
}

// Calculator Row Component
function CalcRow({ label, value, colors, bold, highlight, sublabel }: {
  label: string; value: number; colors: any; bold?: boolean; highlight?: string; sublabel?: string;
}) {
  return (
    <View style={styles.calcRow}>
      <View style={{ flex: 1 }}>
        <Text style={[styles.calcLabel, { color: bold ? colors.textPrimary : colors.textSecondary, fontWeight: bold ? '700' : '400' }]}>{label}</Text>
        {sublabel && <Text style={{ fontSize: 10, color: colors.textSecondary, marginTop: 1 }}>{sublabel}</Text>}
      </View>
      <Text style={[styles.calcValue, { color: highlight || (bold ? colors.textPrimary : colors.textSecondary), fontWeight: bold ? '700' : '500' }]}>
        {value < 0 ? `- ${formatINR(Math.abs(value))}` : formatINR(value)}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 12 },
  loadingText: { fontSize: 14, fontFamily: 'DM Sans' },

  // Header
  stickyHeader: { position: 'absolute', top: 0, left: 0, right: 0, zIndex: 100 },
  headerContent: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 12, borderBottomWidth: 1 },
  headerLeft: { flex: 1, gap: 4 },
  headerTitle: { fontSize: 22, fontFamily: 'DM Sans', fontWeight: '800' },
  fyBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 10, paddingVertical: 5, borderRadius: 8, alignSelf: 'flex-start' },
  fyBadgeText: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '700' },
  refreshBtn: { width: 36, height: 36, borderRadius: 10, justifyContent: 'center', alignItems: 'center' },

  // Scroll
  scrollView: { flex: 1 },
  scrollContent: { paddingHorizontal: 16, paddingBottom: 100 },

  // Section Title
  sectionTitle: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '800', marginBottom: 12, letterSpacing: -0.3 },
  taxFyLabel: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '500' },
  taxSubsectionTitle: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5 },

  // Tax Planning Header
  taxPlanningHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, marginTop: 4 },
  addDeductionBtn: { width: 36, height: 36, borderRadius: 10, justifyContent: 'center', alignItems: 'center' },

  // Tax Saved Badge
  taxSavedBadge: { flexDirection: 'row', alignItems: 'center', gap: 8, padding: 10, borderRadius: 10, marginBottom: 14 },
  taxSavedText: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600', flex: 1 },

  // Glass Card
  glassCard: { borderRadius: 16, padding: 16, borderWidth: 1, marginBottom: 0 },

  // Tax Section Styles
  taxHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  taxIconWrap: { width: 34, height: 34, borderRadius: 10, justifyContent: 'center', alignItems: 'center' },
  taxTitle: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' },
  taxUsed: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '500' },
  taxPercentBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
  taxPercentText: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '700' },
  taxBarBg: { height: 6, borderRadius: 3, overflow: 'hidden', marginBottom: 6 },
  taxBarFill: { height: '100%', borderRadius: 3 },
  taxRemaining: { fontSize: 10, fontFamily: 'DM Sans', fontWeight: '500', marginTop: 2 },
  taxItemsList: { marginTop: 4, gap: 4 },
  taxItemRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  taxItemName: { fontSize: 11, fontFamily: 'DM Sans' },
  taxItemAmt: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '600' },

  // Deduction Action Buttons
  deductionActionBtn: { width: 30, height: 30, borderRadius: 8, justifyContent: 'center', alignItems: 'center' },
  deductionAmountRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  deductionAmountLabel: { fontSize: 12, fontFamily: 'DM Sans' },
  deductionAmountValue: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' },

  // Regime Toggle
  regimeToggle: { flexDirection: 'row', borderRadius: 12, padding: 4, marginBottom: 14 },
  regimeBtn: { flex: 1, paddingVertical: 10, borderRadius: 10, alignItems: 'center' },
  regimeBtnText: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700' },

  // Comparison Banner
  comparisonBanner: { flexDirection: 'row', alignItems: 'center', gap: 8, padding: 12, borderRadius: 12, borderWidth: 1, marginBottom: 14 },
  comparisonText: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700', flex: 1 },

  // Calculator Rows
  calcSectionTitle: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700', marginBottom: 12 },
  calcRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 6 },
  calcLabel: { fontSize: 12, fontFamily: 'DM Sans' },
  calcValue: { fontSize: 12, fontFamily: 'DM Sans' },

  // Slab Breakdown
  slabSection: { borderTopWidth: 1, marginTop: 8, paddingTop: 8, marginBottom: 4 },
  slabTitle: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '700', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 0.5 },
  slabRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 4 },
  slabRange: { fontSize: 11, fontFamily: 'DM Sans' },
  slabRate: { fontSize: 10, fontFamily: 'DM Sans', marginTop: 1 },
  slabTax: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600' },

  // Total Tax
  totalTaxRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingTop: 14, borderTopWidth: 2, marginTop: 8 },
  totalTaxLabel: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '800' },
  totalTaxAmount: { fontSize: 18, fontFamily: 'DM Sans', fontWeight: '800' },
  effectiveRateRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 6 },
  effectiveRateLabel: { fontSize: 11, fontFamily: 'DM Sans' },
  effectiveRateValue: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' },

  // Comparison Grid
  comparisonGrid: { flexDirection: 'row', alignItems: 'center' },
  comparisonCol: { flex: 1, alignItems: 'center', paddingVertical: 10 },
  comparisonDivider: { width: 1, height: 50 },
  comparisonColTitle: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600', marginBottom: 6 },
  comparisonTax: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '800', marginBottom: 2 },
  comparisonRate: { fontSize: 11, fontFamily: 'DM Sans' },

  // Notes
  notesCard: { borderRadius: 12, padding: 14, borderWidth: 1, marginBottom: 16 },
  notesTitle: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '700' },
  noteText: { fontSize: 11, fontFamily: 'DM Sans', marginBottom: 3 },

  // Empty State
  emptyCard: { borderRadius: 16, padding: 24, borderWidth: 1, alignItems: 'center', gap: 8 },
  emptyText: { fontSize: 12, fontFamily: 'DM Sans', textAlign: 'center' },

  // FY Picker Modal
  modalOverlay: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.5)' },
  fyPickerCard: { width: SCREEN_WIDTH - 48, borderRadius: 16, padding: 20 },
  fyPickerTitle: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '700', marginBottom: 16 },
  fyOption: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 14, paddingHorizontal: 12, borderRadius: 10, marginBottom: 4 },
  fyOptionLabel: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700' },
  fyOptionSub: { fontSize: 11, fontFamily: 'DM Sans', marginTop: 2 },

  // Edit Modal
  editModal: { width: SCREEN_WIDTH - 48, borderRadius: 16, padding: 20 },
  editModalTitle: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '700', marginBottom: 4 },
  editModalSub: { fontSize: 12, fontFamily: 'DM Sans', marginBottom: 16 },
  editModalInput: { height: 48, borderRadius: 10, paddingHorizontal: 14, fontSize: 16, fontFamily: 'DM Sans', borderWidth: 1, marginBottom: 16 },
  editModalBtns: { flexDirection: 'row', gap: 10 },
  editModalCancelBtn: { flex: 1, height: 44, borderRadius: 10, justifyContent: 'center', alignItems: 'center', borderWidth: 1 },
  editModalCancelText: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '600' },
  editModalSaveBtn: { flex: 1, height: 44, borderRadius: 10, justifyContent: 'center', alignItems: 'center', backgroundColor: '#F59E0B' },
  editModalSaveText: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700', color: '#fff' },
});
