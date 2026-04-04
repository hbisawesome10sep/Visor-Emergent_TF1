import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Accent } from '../../utils/theme';
import { formatINR, formatINRShort } from '../../utils/formatters';

interface AutoDeductionsSectionProps {
  autoDeductions: any;
  colors: any;
  isDark: boolean;
  hasUserDeductions: boolean;
  onEditTransaction: (txn: any) => void;
  onDismissTransaction: (txn: any) => void;
  onScanAll?: () => void;
  isScanning?: boolean;
  scanResult?: any;
}

export const AutoDeductionsSection: React.FC<AutoDeductionsSectionProps> = ({
  autoDeductions,
  colors,
  isDark,
  hasUserDeductions,
  onEditTransaction,
  onDismissTransaction,
  onScanAll,
  isScanning,
  scanResult,
}) => {
  if (!autoDeductions || !autoDeductions.sections?.length) return null;

  return (
    <View style={{ marginBottom: 16 }}>
      {/* Scan All Data Button */}
      {onScanAll && (
        <TouchableOpacity
          data-testid="scan-all-data-btn"
          style={[styles.scanBtn, {
            backgroundColor: isDark ? 'rgba(139,92,246,0.12)' : 'rgba(139,92,246,0.08)',
            borderColor: isDark ? 'rgba(139,92,246,0.25)' : 'rgba(139,92,246,0.15)',
          }]}
          onPress={onScanAll}
          disabled={isScanning}
        >
          {isScanning ? (
            <ActivityIndicator size="small" color="#8B5CF6" />
          ) : (
            <MaterialCommunityIcons name="radar" size={18} color="#8B5CF6" />
          )}
          <View style={{ flex: 1 }}>
            <Text style={[styles.scanBtnTitle, { color: colors.textPrimary }]}>
              {isScanning ? 'Scanning all data...' : 'Scan All Data'}
            </Text>
            <Text style={[styles.scanBtnSub, { color: colors.textSecondary }]}>
              Auto-detect deductions from transactions, holdings, SIPs & loans
            </Text>
          </View>
          {!isScanning && (
            <MaterialCommunityIcons name="chevron-right" size={20} color={colors.textSecondary} />
          )}
        </TouchableOpacity>
      )}

      {/* Scan Result Banner */}
      {scanResult && (
        <View style={[styles.scanResult, {
          backgroundColor: scanResult.new_deductions_found > 0 
            ? (isDark ? 'rgba(16,185,129,0.1)' : 'rgba(16,185,129,0.06)')
            : (isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)'),
          borderColor: scanResult.new_deductions_found > 0
            ? (isDark ? 'rgba(16,185,129,0.2)' : 'rgba(16,185,129,0.12)')
            : (isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.04)'),
        }]}>
          <MaterialCommunityIcons 
            name={scanResult.new_deductions_found > 0 ? "check-circle" : "information"} 
            size={16} 
            color={scanResult.new_deductions_found > 0 ? Accent.emerald : colors.textSecondary} 
          />
          <Text style={[styles.scanResultText, { color: colors.textPrimary }]}>
            {scanResult.new_deductions_found > 0
              ? `Found ${scanResult.new_deductions_found} new deduction${scanResult.new_deductions_found > 1 ? 's' : ''} worth ${formatINRShort(scanResult.total_new_amount)}`
              : 'No new deductions found. All data already scanned.'}
          </Text>
        </View>
      )}

      <View style={[styles.header, { marginTop: hasUserDeductions ? 4 : 0 }]}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
          <MaterialCommunityIcons name="lightning-bolt" size={14} color="#8B5CF6" />
          <Text style={[styles.title, { color: '#8B5CF6' }]}>
            Auto-Detected from Transactions
          </Text>
        </View>
        <View style={[styles.countBadge, { backgroundColor: 'rgba(139,92,246,0.12)' }]}>
          <Text style={styles.countText}>{autoDeductions.count}</Text>
        </View>
      </View>

      {autoDeductions.sections.map((section: any) => {
        const pct = section.limit > 0 
          ? Math.min((section.total_amount / section.limit) * 100, 100) 
          : 0;
        const isFull = section.limit > 0 && section.total_amount >= section.limit;
        const barColor = isFull ? Accent.emerald : '#8B5CF6';

        return (
          <View 
            key={section.section} 
            data-testid={`auto-deduction-section-${section.section}`} 
            style={[styles.card, {
              backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.85)',
              borderColor: isDark ? 'rgba(139,92,246,0.15)' : 'rgba(139,92,246,0.1)',
            }]}
          >
            <View style={styles.sectionHeader}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10, flex: 1 }}>
                <View style={[styles.iconWrap, { backgroundColor: 'rgba(139,92,246,0.12)' }]}>
                  <MaterialCommunityIcons name="auto-fix" size={18} color="#8B5CF6" />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>
                    {section.section_label}
                  </Text>
                  <Text style={[styles.sectionSubtitle, { color: colors.textSecondary }]}>
                    {formatINRShort(section.total_amount)}
                    {section.limit > 0 ? ` / ${formatINRShort(section.limit)}` : ''}
                  </Text>
                </View>
              </View>
              {section.limit > 0 && (
                <View style={[styles.percentBadge, { 
                  backgroundColor: isFull ? 'rgba(16,185,129,0.1)' : 'rgba(139,92,246,0.1)' 
                }]}>
                  <Text style={[styles.percentText, { color: isFull ? Accent.emerald : '#8B5CF6' }]}>
                    {pct.toFixed(0)}%
                  </Text>
                </View>
              )}
            </View>

            {section.limit > 0 && (
              <View style={[styles.barBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
                <View style={[styles.barFill, { width: `${pct}%`, backgroundColor: barColor }]} />
              </View>
            )}

            {/* Individual transactions */}
            <View style={{ marginTop: 6, gap: 6 }}>
              {section.transactions.map((txn: any) => (
                <View 
                  key={txn.id} 
                  data-testid={`auto-deduction-txn-${txn.id}`} 
                  style={[styles.txnRow, {
                    backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)',
                  }]}
                >
                  <View style={{ flex: 1 }}>
                    <Text style={[styles.txnName, { color: colors.textPrimary }]} numberOfLines={1}>
                      {txn.name}
                    </Text>
                    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 2, flexWrap: 'wrap' }}>
                      <Text style={[styles.txnMeta, { color: colors.textSecondary }]}>
                        {txn.source_date}
                      </Text>
                      <View style={[styles.txnBadge, { 
                        backgroundColor: txn.detected_from === 'category' 
                          ? 'rgba(59,130,246,0.1)' 
                          : 'rgba(245,158,11,0.1)' 
                      }]}>
                        <Text style={[styles.txnBadgeText, { 
                          color: txn.detected_from === 'category' ? '#3B82F6' : '#F59E0B' 
                        }]}>
                          {txn.detected_from === 'category' ? 'Category' : 'Keywords'}
                        </Text>
                      </View>
                      {/* Confidence Score Badge */}
                      {txn.confidence !== undefined && txn.confidence !== null && (
                        <View style={[styles.confidenceBadge, { 
                          backgroundColor: txn.confidence >= 0.85 
                            ? 'rgba(16,185,129,0.1)' 
                            : txn.confidence >= 0.70 
                              ? 'rgba(245,158,11,0.1)'
                              : 'rgba(239,68,68,0.1)'
                        }]}>
                          <MaterialCommunityIcons 
                            name={txn.confidence >= 0.85 ? "check-circle" : txn.confidence >= 0.70 ? "alert-circle" : "help-circle"} 
                            size={9} 
                            color={txn.confidence >= 0.85 ? '#10B981' : txn.confidence >= 0.70 ? '#F59E0B' : '#EF4444'} 
                          />
                          <Text style={[styles.confidenceText, { 
                            color: txn.confidence >= 0.85 ? '#10B981' : txn.confidence >= 0.70 ? '#F59E0B' : '#EF4444' 
                          }]}>
                            {Math.round(txn.confidence * 100)}%
                          </Text>
                        </View>
                      )}
                    </View>
                  </View>
                  <Text style={[styles.txnAmount, { color: colors.textPrimary }]}>
                    {formatINR(txn.amount)}
                  </Text>
                  <View style={{ flexDirection: 'row', gap: 6, marginLeft: 8 }}>
                    <TouchableOpacity 
                      data-testid={`edit-auto-${txn.id}`}
                      style={[styles.actionBtn, { 
                        backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)' 
                      }]} 
                      onPress={() => onEditTransaction(txn)}
                    >
                      <MaterialCommunityIcons name="pencil" size={13} color={colors.textSecondary} />
                    </TouchableOpacity>
                    <TouchableOpacity 
                      data-testid={`dismiss-auto-${txn.id}`}
                      style={[styles.actionBtn, { backgroundColor: 'rgba(239,68,68,0.1)' }]} 
                      onPress={() => onDismissTransaction(txn)}
                    >
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
  );
};

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  title: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  countBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 10,
  },
  countText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#8B5CF6',
    fontFamily: 'DM Sans',
  },
  card: {
    borderRadius: 16,
    padding: 14,
    borderWidth: 1,
    borderLeftWidth: 3,
    borderLeftColor: '#8B5CF6',
    marginBottom: 10,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  iconWrap: {
    width: 36,
    height: 36,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  sectionTitle: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  sectionSubtitle: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    marginTop: 2,
  },
  percentBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
  },
  percentText: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  barBg: {
    height: 6,
    borderRadius: 3,
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    borderRadius: 3,
  },
  txnRow: {
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
  txnMeta: {
    fontSize: 11,
    fontFamily: 'DM Sans',
  },
  txnBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  txnBadgeText: {
    fontSize: 9,
    fontWeight: '600',
    fontFamily: 'DM Sans',
  },
  txnAmount: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    fontWeight: '600',
  },
  actionBtn: {
    width: 26,
    height: 26,
    borderRadius: 6,
    justifyContent: 'center',
    alignItems: 'center',
  },
  scanBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 14,
    borderRadius: 14,
    borderWidth: 1,
    marginBottom: 14,
  },
  scanBtnTitle: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  scanBtnSub: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    marginTop: 2,
  },
  scanResult: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    padding: 12,
    borderRadius: 10,
    borderWidth: 1,
    marginBottom: 12,
  },
  scanResultText: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    fontWeight: '500',
    flex: 1,
  },
});
