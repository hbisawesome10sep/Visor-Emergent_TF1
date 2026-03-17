/**
 * Holdings Section Component
 * Displays user's investment holdings with add/clear/CAS upload functionality
 */
import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Accent } from '../../utils/theme';
import { formatINR, formatINRShort } from '../../utils/formatters';
import { type HoldingsData } from './types';

interface HoldingsSectionProps {
  holdingsData: HoldingsData | null;
  colors: any;
  isDark: boolean;
  onAddHolding: () => void;
  onClearHoldings: () => void;
  onUploadCAS: () => void;
  onDeleteHolding: (id: string, name: string) => void;
}

// Helper: format price for Indian comma system
const fmtPrice = (p: number) => {
  const num = Math.round(p);
  const str = num.toString();
  const digits = str.split('').reverse();
  let formatted = '';
  for (let i = 0; i < digits.length; i++) {
    if (i === 3 || (i > 3 && (i - 3) % 2 === 0)) formatted = ',' + formatted;
    formatted = digits[i] + formatted;
  }
  return formatted;
};

export const HoldingsSection: React.FC<HoldingsSectionProps> = ({
  holdingsData,
  colors,
  isDark,
  onAddHolding,
  onClearHoldings,
  onUploadCAS,
  onDeleteHolding,
}) => {
  return (
    <>
      {/* Section Header */}
      <View style={styles.sectionHeader}>
        <Text data-testid="holdings-section-title" style={[styles.sectionTitle, { color: colors.textPrimary, marginBottom: 0 }]}>
          My Holdings
        </Text>
        <View style={{ flexDirection: 'row' as any, gap: 8 }}>
          <TouchableOpacity 
            data-testid="clear-holdings-quick-btn" 
            style={[styles.casBtn, { borderColor: Accent.ruby }]} 
            onPress={onClearHoldings}
          >
            <MaterialCommunityIcons name="delete-outline" size={14} color={Accent.ruby} />
            <Text style={[styles.casBtnText, { color: Accent.ruby }]}>Clear</Text>
          </TouchableOpacity>
          <TouchableOpacity 
            data-testid="upload-cas-btn" 
            style={[styles.casBtn, { borderColor: '#F97316' }]} 
            onPress={onUploadCAS}
          >
            <MaterialCommunityIcons name="file-upload-outline" size={14} color="#F97316" />
            <Text style={[styles.casBtnText, { color: '#F97316' }]}>CAS</Text>
          </TouchableOpacity>
          <TouchableOpacity 
            data-testid="add-holding-btn" 
            style={[styles.addGoalBtn, { backgroundColor: '#F97316' }]} 
            onPress={onAddHolding}
          >
            <MaterialCommunityIcons name="plus" size={14} color="#fff" />
            <Text style={styles.addGoalText}>Add</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Holdings Content */}
      {holdingsData && holdingsData.holdings.length > 0 ? (
        <View 
          data-testid="holdings-card" 
          style={[styles.holdingsCard, {
            backgroundColor: isDark ? 'rgba(10,10,11,0.9)' : '#FFFFFF',
            borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
          }]}
        >
          {/* Holdings summary */}
          <View style={styles.holdingsSummaryRow}>
            <View>
              <Text style={[styles.portfolioSmallLabel, { color: colors.textSecondary }]}>Holdings Value</Text>
              <Text style={[styles.holdingsSummaryNum, { color: colors.textPrimary }]}>
                {formatINR(holdingsData.summary.total_current_value)}
              </Text>
            </View>
            <View style={[styles.gainLossBadge, {
              backgroundColor: holdingsData.summary.total_gain_loss >= 0 ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
              marginHorizontal: 0, 
              marginBottom: 0,
            }]}>
              <Text style={[styles.gainLossText, {
                color: holdingsData.summary.total_gain_loss >= 0 ? Accent.emerald : Accent.ruby,
              }]}>
                {holdingsData.summary.total_gain_loss >= 0 ? '+' : ''}{holdingsData.summary.total_gain_loss_pct.toFixed(2)}%
              </Text>
            </View>
          </View>

          {/* Holdings list */}
          {holdingsData.holdings.map((h, idx) => {
            const isGain = h.gain_loss >= 0;
            const isLast = idx === holdingsData.holdings.length - 1;
            return (
              <TouchableOpacity 
                key={h.id} 
                data-testid={`holding-row-${h.id}`}
                style={[styles.holdingRow, !isLast && { 
                  borderBottomWidth: 1, 
                  borderBottomColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.03)' 
                }]}
                onLongPress={() => onDeleteHolding(h.id, h.name)}
              >
                <View style={{ flex: 1 }}>
                  <Text style={[styles.holdingName, { color: colors.textPrimary }]} numberOfLines={1}>
                    {h.name}
                  </Text>
                  <Text style={[styles.holdingSub, { color: colors.textSecondary }]}>
                    {h.quantity} {h.category === 'Mutual Fund' ? 'units' : 'shares'} @ {fmtPrice(Math.round(h.buy_price))}
                  </Text>
                </View>
                <View style={{ alignItems: 'flex-end' as any }}>
                  <Text style={[styles.holdingValue, { color: colors.textPrimary }]}>
                    {formatINRShort(h.current_value)}
                  </Text>
                  <Text style={[styles.holdingGain, { color: isGain ? Accent.emerald : Accent.ruby }]}>
                    {isGain ? '+' : ''}{h.gain_loss_pct.toFixed(1)}%
                  </Text>
                </View>
              </TouchableOpacity>
            );
          })}
        </View>
      ) : (
        <View style={[styles.emptyPortfolio, { 
          backgroundColor: isDark ? 'rgba(10,10,11,0.9)' : '#FFFFFF', 
          borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)' 
        }]}>
          <MaterialCommunityIcons name="briefcase-outline" size={36} color={colors.textSecondary} />
          <Text style={[styles.emptyGoalsTitle, { color: colors.textPrimary }]}>No holdings added</Text>
          <Text style={[styles.emptyGoalsSubtitle, { color: colors.textSecondary }]}>
            Add stocks and mutual funds manually or upload your CAS statement
          </Text>
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
  casBtn: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    gap: 4, 
    paddingHorizontal: 12, 
    paddingVertical: 8, 
    borderRadius: 12, 
    borderWidth: 1 
  },
  casBtnText: { 
    fontSize: 12, 
    fontFamily: 'DM Sans', 
    fontWeight: '700' as any 
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
  holdingsCard: { 
    borderRadius: 18, 
    borderWidth: 1, 
    overflow: 'hidden', 
    marginBottom: 24 
  },
  holdingsSummaryRow: { 
    flexDirection: 'row', 
    justifyContent: 'space-between', 
    alignItems: 'center', 
    padding: 18, 
    paddingBottom: 14 
  },
  portfolioSmallLabel: { 
    fontSize: 11, 
    fontFamily: 'DM Sans', 
    fontWeight: '600' as any, 
    textTransform: 'uppercase', 
    letterSpacing: 0.5 
  },
  holdingsSummaryNum: { 
    fontSize: 20, 
    fontFamily: 'DM Sans', 
    fontWeight: '700' as any, 
    letterSpacing: -0.4, 
    marginTop: 4 
  },
  gainLossBadge: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    gap: 8, 
    paddingHorizontal: 14, 
    paddingVertical: 8, 
    borderRadius: 12 
  },
  gainLossText: { 
    fontSize: 13, 
    fontFamily: 'DM Sans', 
    fontWeight: '700' as any 
  },
  holdingRow: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    justifyContent: 'space-between', 
    paddingHorizontal: 18, 
    paddingVertical: 14 
  },
  holdingName: { 
    fontSize: 14, 
    fontFamily: 'DM Sans', 
    fontWeight: '600' as any, 
    maxWidth: 180 
  },
  holdingSub: { 
    fontSize: 11, 
    fontFamily: 'DM Sans', 
    fontWeight: '500' as any, 
    marginTop: 2 
  },
  holdingValue: { 
    fontSize: 14, 
    fontFamily: 'DM Sans', 
    fontWeight: '700' as any 
  },
  holdingGain: { 
    fontSize: 12, 
    fontFamily: 'DM Sans', 
    fontWeight: '600' as any, 
    marginTop: 2 
  },
  emptyPortfolio: { 
    alignItems: 'center', 
    padding: 28, 
    borderRadius: 18, 
    borderWidth: 1, 
    marginBottom: 24 
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
});

export default HoldingsSection;
