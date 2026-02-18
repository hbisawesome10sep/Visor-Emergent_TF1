import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { formatINRShort, getCategoryColor, getCategoryIcon } from '../utils/formatters';
import { Accent } from '../utils/theme';

type SpendingItem = { category: string; amount: number };

type Props = {
  data: SpendingItem[];
  isDark: boolean;
  colors: any;
};

export const SpendingBreakdownCard = ({ data, isDark, colors }: Props) => {
  const total = data.reduce((s, d) => s + d.amount, 0) || 1;

  if (data.length === 0) return null;

  return (
    <View style={[styles.card, {
      backgroundColor: isDark ? 'rgba(10, 10, 11, 0.9)' : 'rgba(255, 255, 255, 0.95)',
      borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
    }]}>
      <Text style={[styles.title, { color: colors.textPrimary }]}>Spending Breakdown</Text>
      <Text style={[styles.subtitle, { color: colors.textSecondary }]}>Where your money goes this period</Text>

      {data.map((item) => {
        const percent = (item.amount / total) * 100;
        const barColor = getCategoryColor(item.category, isDark);
        return (
          <View key={item.category} style={styles.row}>
            <View style={styles.left}>
              <View style={[styles.icon, { backgroundColor: `${barColor}15` }]}>
                <MaterialCommunityIcons name={getCategoryIcon(item.category) as any} size={16} color={barColor} />
              </View>
              <Text style={[styles.category, { color: colors.textPrimary }]}>{item.category}</Text>
            </View>
            <View style={styles.right}>
              <Text style={[styles.amount, { color: colors.textPrimary }]}>{formatINRShort(item.amount)}</Text>
              <Text style={[styles.percent, { color: colors.textSecondary }]}>{percent.toFixed(0)}%</Text>
            </View>
            <View style={[styles.barBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
              <View style={[styles.barFill, { width: `${percent}%`, backgroundColor: barColor }]} />
            </View>
          </View>
        );
      })}
    </View>
  );
};

const styles = StyleSheet.create({
  card: { borderRadius: 20, borderWidth: 1, padding: 20, marginBottom: 16 },
  title: { fontSize: 18, fontFamily: 'DM Sans', fontWeight: '700' as any, marginBottom: 2 },
  subtitle: { fontSize: 12, fontFamily: 'DM Sans', marginBottom: 16 },
  row: { marginBottom: 14 },
  left: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 4 },
  icon: { width: 28, height: 28, borderRadius: 8, alignItems: 'center', justifyContent: 'center' },
  category: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '500' as any },
  right: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
  amount: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '600' as any },
  percent: { fontSize: 12, fontFamily: 'DM Sans' },
  barBg: { height: 4, borderRadius: 2, overflow: 'hidden' },
  barFill: { height: 4, borderRadius: 2 },
});
