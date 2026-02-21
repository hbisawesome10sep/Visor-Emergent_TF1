import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Accent } from '../../utils/theme';
import { formatINR, formatINRShort } from '../../utils/formatters';

interface UserDeductionsSectionProps {
  deductions: any[];
  colors: any;
  isDark: boolean;
  onEdit: (deduction: any) => void;
  onDelete: (deduction: any) => void;
}

export const UserDeductionsSection: React.FC<UserDeductionsSectionProps> = ({
  deductions,
  colors,
  isDark,
  onEdit,
  onDelete,
}) => {
  if (deductions.length === 0) return null;

  return (
    <View style={{ marginBottom: 16 }}>
      <Text style={[styles.subsectionTitle, { color: colors.textSecondary }]}>
        Your Selected Deductions
      </Text>
      {deductions.map((deduction: any) => {
        const pct = deduction.limit && deduction.limit > 0 
          ? Math.min((deduction.invested_amount / deduction.limit) * 100, 100) 
          : 0;
        const isFull = deduction.limit > 0 && deduction.invested_amount >= deduction.limit;
        const barColor = isFull ? Accent.emerald : '#F97316';
        const remaining = deduction.limit ? Math.max(deduction.limit - deduction.invested_amount, 0) : null;

        return (
          <View 
            key={deduction.id} 
            data-testid={`user-deduction-${deduction.deduction_id}`} 
            style={[styles.card, {
              backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.85)',
              borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
            }]}
          >
            <View style={styles.header}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10, flex: 1 }}>
                <View style={[styles.iconWrap, { 
                  backgroundColor: isFull ? 'rgba(16,185,129,0.12)' : 'rgba(249,115,22,0.12)' 
                }]}>
                  <MaterialCommunityIcons 
                    name="file-document-check" 
                    size={18} 
                    color={isFull ? Accent.emerald : '#F97316'} 
                  />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={[styles.title, { color: colors.textPrimary }]}>{deduction.section}</Text>
                  <Text style={[styles.subtitle, { color: colors.textSecondary }]} numberOfLines={1}>
                    {deduction.name}
                  </Text>
                </View>
              </View>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                <TouchableOpacity 
                  data-testid={`edit-deduction-${deduction.id}`}
                  style={[styles.actionBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)' }]} 
                  onPress={() => onEdit(deduction)}
                >
                  <MaterialCommunityIcons name="pencil" size={16} color={colors.textSecondary} />
                </TouchableOpacity>
                <TouchableOpacity 
                  data-testid={`delete-deduction-${deduction.id}`}
                  style={[styles.actionBtn, { backgroundColor: 'rgba(239,68,68,0.1)' }]} 
                  onPress={() => onDelete(deduction)}
                >
                  <MaterialCommunityIcons name="trash-can-outline" size={16} color="#EF4444" />
                </TouchableOpacity>
              </View>
            </View>

            <View style={styles.amountRow}>
              <Text style={[styles.amountLabel, { color: colors.textSecondary }]}>Invested:</Text>
              <Text style={[styles.amountValue, { color: colors.textPrimary }]}>
                {formatINR(deduction.invested_amount || 0)}
                {deduction.limit ? ` / ${formatINRShort(deduction.limit)}` : ''}
              </Text>
            </View>

            {deduction.limit > 0 && (
              <>
                <View style={[styles.barBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
                  <View style={[styles.barFill, { width: `${pct}%`, backgroundColor: barColor }]} />
                </View>
                {remaining !== null && remaining > 0 && (
                  <Text style={[styles.remaining, { color: colors.textSecondary }]}>
                    {formatINRShort(remaining)} remaining for max benefit
                  </Text>
                )}
              </>
            )}
          </View>
        );
      })}
    </View>
  );
};

const styles = StyleSheet.create({
  subsectionTitle: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 10,
  },
  card: {
    borderRadius: 16,
    padding: 14,
    borderWidth: 1,
    marginBottom: 10,
  },
  header: {
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
  title: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  subtitle: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    marginTop: 2,
  },
  actionBtn: {
    width: 30,
    height: 30,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  amountRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  amountLabel: {
    fontSize: 12,
    fontFamily: 'DM Sans',
  },
  amountValue: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    fontWeight: '600',
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
  remaining: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    marginTop: 6,
    textAlign: 'right',
  },
});
