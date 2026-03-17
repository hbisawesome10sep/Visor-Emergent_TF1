/**
 * Recurring Investments (SIP) Section Component
 * Displays SIP summary, list of SIPs, and action buttons
 */
import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Accent } from '../../utils/theme';
import { formatINR, formatINRShort } from '../../utils/formatters';
import { type RecurringTransaction, type RecurringData, ASSET_CATEGORIES } from './types';

interface RecurringInvestmentsSectionProps {
  recurringData: RecurringData | null;
  colors: any;
  isDark: boolean;
  onAddSip: () => void;
  onEditSip: (sip: RecurringTransaction) => void;
  onDeleteSip: (id: string, name: string) => void;
  onPauseSip: (sip: RecurringTransaction) => void;
  onExecuteSip: (sip: RecurringTransaction) => void;
}

export const RecurringInvestmentsSection: React.FC<RecurringInvestmentsSectionProps> = ({
  recurringData,
  colors,
  isDark,
  onAddSip,
  onEditSip,
  onDeleteSip,
  onPauseSip,
  onExecuteSip,
}) => {
  return (
    <>
      {/* Section Header */}
      <View style={styles.sectionHeader}>
        <Text data-testid="sip-section-title" style={[styles.sectionTitle, { color: colors.textPrimary, marginBottom: 0 }]}>
          Recurring Investments
        </Text>
        <TouchableOpacity 
          data-testid="add-sip-btn" 
          style={[styles.addGoalBtn, { backgroundColor: '#6366F1' }]} 
          onPress={onAddSip}
        >
          <MaterialCommunityIcons name="plus" size={16} color="#fff" />
          <Text style={styles.addGoalText}>Add SIP</Text>
        </TouchableOpacity>
      </View>

      {/* SIP Summary Card */}
      {recurringData && recurringData.recurring.length > 0 && (
        <View 
          data-testid="sip-summary-card" 
          style={[styles.sipSummaryCard, {
            backgroundColor: isDark ? 'rgba(99,102,241,0.1)' : 'rgba(99,102,241,0.06)',
            borderColor: isDark ? 'rgba(99,102,241,0.25)' : 'rgba(99,102,241,0.15)',
          }]}
        >
          <View style={styles.sipSummaryRow}>
            <View>
              <Text style={[styles.sipSummaryLabel, { color: colors.textSecondary }]}>Monthly Commitment</Text>
              <Text data-testid="sip-monthly-commitment" style={[styles.sipSummaryAmount, { color: '#6366F1' }]}>
                {formatINR(recurringData.summary.monthly_commitment)}/mo
              </Text>
            </View>
            <View style={styles.sipCountBadge}>
              <Text style={styles.sipCountText}>{recurringData.summary.active_count} Active</Text>
            </View>
          </View>
        </View>
      )}

      {/* Empty State */}
      {(!recurringData || recurringData.recurring.length === 0) && (
        <View style={[styles.emptyGoals, { 
          backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)', 
          borderColor: colors.border 
        }]}>
          <MaterialCommunityIcons name="calendar-sync-outline" size={36} color={colors.textSecondary} />
          <Text style={[styles.emptyGoalsTitle, { color: colors.textPrimary }]}>No recurring investments</Text>
          <Text style={[styles.emptyGoalsSubtitle, { color: colors.textSecondary }]}>
            Set up SIPs to automate your investments
          </Text>
        </View>
      )}

      {/* SIP Cards */}
      {recurringData && recurringData.recurring.length > 0 && (
        <View style={styles.sipList}>
          {recurringData.recurring.map(sip => {
            const catColor = ASSET_CATEGORIES[sip.category]?.color || '#6366F1';
            const freqLabel = sip.frequency.charAt(0).toUpperCase() + sip.frequency.slice(1);
            const nextDate = sip.next_execution 
              ? new Date(sip.next_execution).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) 
              : '-';
            
            return (
              <View 
                key={sip.id} 
                data-testid={`sip-card-${sip.id}`} 
                style={[styles.sipCard, {
                  backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : '#FFFFFF',
                  borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
                  opacity: sip.is_active ? 1 : 0.6,
                }]}
              >
                {/* SIP Header */}
                <View style={styles.sipCardHeader}>
                  <View style={[styles.sipIconWrap, { backgroundColor: catColor + '20' }]}>
                    <MaterialCommunityIcons name="calendar-sync" size={18} color={catColor} />
                  </View>
                  <View style={{ flex: 1 }}>
                    <View style={styles.sipNameRow}>
                      <Text style={[styles.sipName, { color: colors.textPrimary, flex: 1 }]} numberOfLines={1}>
                        {sip.name}
                      </Text>
                      {(sip as any).auto_detected && (
                        <View style={[styles.autoDetectedBadge, { backgroundColor: '#6366F120' }]}>
                          <MaterialCommunityIcons name="magic-staff" size={10} color="#6366F1" />
                          <Text style={[styles.autoDetectedText, { color: '#6366F1' }]}>Auto</Text>
                        </View>
                      )}
                    </View>
                    <Text style={[styles.sipCategory, { color: colors.textSecondary }]}>
                      {sip.category} • {freqLabel}
                    </Text>
                  </View>
                  <View style={{ alignItems: 'flex-end' as any }}>
                    <Text style={[styles.sipAmount, { color: colors.textPrimary }]}>{formatINR(sip.amount)}</Text>
                    {!sip.is_active && (
                      <View style={[styles.sipPausedBadge, { backgroundColor: '#F59E0B20' }]}>
                        <Text style={[styles.sipPausedText, { color: '#F59E0B' }]}>Paused</Text>
                      </View>
                    )}
                  </View>
                </View>

                {/* Next Execution & Stats */}
                <View style={[styles.sipStatsRow, { borderTopColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)' }]}>
                  <View style={styles.sipStat}>
                    <Text style={[styles.sipStatLabel, { color: colors.textSecondary }]}>Next</Text>
                    <Text style={[styles.sipStatValue, { color: colors.textPrimary }]}>{nextDate}</Text>
                  </View>
                  <View style={styles.sipStatDivider} />
                  <View style={styles.sipStat}>
                    <Text style={[styles.sipStatLabel, { color: colors.textSecondary }]}>Invested</Text>
                    <Text style={[styles.sipStatValue, { color: Accent.emerald }]}>{formatINRShort(sip.total_invested)}</Text>
                  </View>
                  <View style={styles.sipStatDivider} />
                  <View style={styles.sipStat}>
                    <Text style={[styles.sipStatLabel, { color: colors.textSecondary }]}>Count</Text>
                    <Text style={[styles.sipStatValue, { color: colors.textPrimary }]}>{sip.execution_count}</Text>
                  </View>
                </View>

                {/* Action Buttons */}
                <View style={styles.sipActions}>
                  <TouchableOpacity
                    data-testid={`sip-execute-${sip.id}`}
                    style={[styles.sipActionBtn, { backgroundColor: Accent.emerald + '15', borderColor: Accent.emerald + '30' }]}
                    onPress={() => onExecuteSip(sip)}
                    disabled={!sip.is_active}
                  >
                    <MaterialCommunityIcons name="check-circle-outline" size={16} color={Accent.emerald} />
                    <Text style={[styles.sipActionText, { color: Accent.emerald }]}>Execute</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    data-testid={`sip-pause-${sip.id}`}
                    style={[styles.sipActionBtn, { backgroundColor: '#F59E0B15', borderColor: '#F59E0B30' }]}
                    onPress={() => onPauseSip(sip)}
                  >
                    <MaterialCommunityIcons 
                      name={sip.is_active ? 'pause-circle-outline' : 'play-circle-outline'} 
                      size={16} 
                      color="#F59E0B" 
                    />
                    <Text style={[styles.sipActionText, { color: '#F59E0B' }]}>
                      {sip.is_active ? 'Pause' : 'Resume'}
                    </Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    data-testid={`sip-edit-${sip.id}`}
                    style={[styles.sipActionBtn, { 
                      backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)', 
                      borderColor: colors.border 
                    }]}
                    onPress={() => onEditSip(sip)}
                  >
                    <MaterialCommunityIcons name="pencil-outline" size={16} color={colors.textSecondary} />
                  </TouchableOpacity>
                  <TouchableOpacity
                    data-testid={`sip-delete-${sip.id}`}
                    style={[styles.sipActionBtn, { backgroundColor: Accent.ruby + '10', borderColor: Accent.ruby + '20' }]}
                    onPress={() => onDeleteSip(sip.id, sip.name)}
                  >
                    <MaterialCommunityIcons name="delete-outline" size={16} color={Accent.ruby} />
                  </TouchableOpacity>
                </View>
              </View>
            );
          })}
        </View>
      )}
    </>
  );
};

const styles = StyleSheet.create({
  sectionHeader: { 
    flexDirection: 'row', 
    justifyContent: 'space-between', 
    alignItems: 'center', 
    marginBottom: 14 
  },
  sectionTitle: { 
    fontSize: 18, 
    fontFamily: 'DM Sans', 
    fontWeight: '700' as any, 
    letterSpacing: -0.3 
  },
  addGoalBtn: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    gap: 6, 
    paddingHorizontal: 14, 
    paddingVertical: 8, 
    borderRadius: 12 
  },
  addGoalText: { 
    color: '#fff', 
    fontSize: 13, 
    fontFamily: 'DM Sans', 
    fontWeight: '700' as any 
  },
  sipSummaryCard: { 
    borderRadius: 16, 
    padding: 16, 
    borderWidth: 1, 
    marginBottom: 16 
  },
  sipSummaryRow: { 
    flexDirection: 'row', 
    justifyContent: 'space-between', 
    alignItems: 'center' 
  },
  sipSummaryLabel: { 
    fontSize: 12, 
    fontFamily: 'DM Sans', 
    fontWeight: '600' as any 
  },
  sipSummaryAmount: { 
    fontSize: 20, 
    fontFamily: 'DM Sans', 
    fontWeight: '700' as any, 
    marginTop: 4 
  },
  sipCountBadge: { 
    backgroundColor: '#6366F120', 
    paddingHorizontal: 12, 
    paddingVertical: 6, 
    borderRadius: 12 
  },
  sipCountText: { 
    color: '#6366F1', 
    fontSize: 13, 
    fontFamily: 'DM Sans', 
    fontWeight: '700' as any 
  },
  emptyGoals: { 
    alignItems: 'center', 
    padding: 28, 
    borderRadius: 18, 
    borderWidth: 1, 
    marginBottom: 16 
  },
  emptyGoalsTitle: { 
    fontSize: 15, 
    fontFamily: 'DM Sans', 
    fontWeight: '700' as any, 
    marginTop: 10 
  },
  emptyGoalsSubtitle: { 
    fontSize: 12, 
    marginTop: 4 
  },
  sipList: { 
    gap: 12, 
    marginBottom: 24 
  },
  sipCard: { 
    borderRadius: 16, 
    borderWidth: 1, 
    overflow: 'hidden' 
  },
  sipCardHeader: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    padding: 16, 
    gap: 12 
  },
  sipNameRow: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    gap: 6, 
    marginBottom: 2 
  },
  autoDetectedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
    paddingHorizontal: 5,
    paddingVertical: 2,
    borderRadius: 6,
  },
  autoDetectedText: { 
    fontSize: 9, 
    fontFamily: 'DM Sans', 
    fontWeight: '700' as any 
  },
  sipIconWrap: { 
    width: 40, 
    height: 40, 
    borderRadius: 12, 
    justifyContent: 'center', 
    alignItems: 'center' 
  },
  sipName: { 
    fontSize: 15, 
    fontFamily: 'DM Sans', 
    fontWeight: '700' as any 
  },
  sipCategory: { 
    fontSize: 12, 
    fontFamily: 'DM Sans', 
    fontWeight: '500' as any, 
    marginTop: 2 
  },
  sipAmount: { 
    fontSize: 16, 
    fontFamily: 'DM Sans', 
    fontWeight: '700' as any 
  },
  sipPausedBadge: { 
    paddingHorizontal: 8, 
    paddingVertical: 3, 
    borderRadius: 6, 
    marginTop: 4 
  },
  sipPausedText: { 
    fontSize: 10, 
    fontFamily: 'DM Sans', 
    fontWeight: '700' as any 
  },
  sipStatsRow: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    paddingHorizontal: 16, 
    paddingVertical: 12, 
    borderTopWidth: 1 
  },
  sipStat: { 
    flex: 1, 
    alignItems: 'center' 
  },
  sipStatLabel: { 
    fontSize: 10, 
    fontFamily: 'DM Sans', 
    fontWeight: '500' as any, 
    marginBottom: 2 
  },
  sipStatValue: { 
    fontSize: 14, 
    fontFamily: 'DM Sans', 
    fontWeight: '700' as any 
  },
  sipStatDivider: { 
    width: 1, 
    height: 24, 
    backgroundColor: 'rgba(128,128,128,0.2)' 
  },
  sipActions: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    paddingHorizontal: 12, 
    paddingVertical: 10, 
    gap: 8, 
    borderTopWidth: 1, 
    borderTopColor: 'rgba(128,128,128,0.1)' 
  },
  sipActionBtn: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    gap: 4, 
    paddingHorizontal: 10, 
    paddingVertical: 6, 
    borderRadius: 8, 
    borderWidth: 1 
  },
  sipActionText: { 
    fontSize: 12, 
    fontFamily: 'DM Sans', 
    fontWeight: '600' as any 
  },
});

export default RecurringInvestmentsSection;
