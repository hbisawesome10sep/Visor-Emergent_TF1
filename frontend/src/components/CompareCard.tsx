import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { formatINRShort } from '../utils/formatters';
import { Accent } from '../utils/theme';

type Props = {
  savingsRate: number;
  investmentRate: number;
  spendingRate: number;
  runwayMonths: number;
  indianAvgSavingsRate?: number;
  indianAvgInvestmentRate?: number;
  indianAvgExpenseRatio?: number;
  isDark: boolean;
  colors: any;
};

export const CompareCard = ({
  savingsRate, investmentRate, spendingRate, runwayMonths,
  indianAvgSavingsRate = 5.1, indianAvgInvestmentRate = 11.4, indianAvgExpenseRatio = 75,
  isDark, colors,
}: Props) => {
  const isBetter = savingsRate > indianAvgSavingsRate;

  return (
    <View style={[styles.card, {
      backgroundColor: isDark ? 'rgba(10, 10, 11, 0.9)' : 'rgba(255, 255, 255, 0.95)',
      borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
    }]}>
      <View style={styles.header}>
        <View style={[styles.icon, { backgroundColor: isBetter ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)' }]}>
          <MaterialCommunityIcons name={isBetter ? "trophy" : "trending-up"} size={24} color={isBetter ? Accent.emerald : Accent.amber} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={[styles.title, { color: colors.textPrimary }]}>
            {isBetter ? "You're Doing Better!" : "Room for Growth"}
          </Text>
          <Text style={[styles.subtitle, { color: colors.textSecondary }]}>vs. Indian National Averages</Text>
        </View>
      </View>

      <View style={styles.grid}>
        {[
          { label: 'Your Savings', value: `${savingsRate.toFixed(1)}%`, avg: `${indianAvgSavingsRate}%`, good: savingsRate > indianAvgSavingsRate },
          { label: 'Investment Rate', value: `${investmentRate.toFixed(1)}%`, avg: `${indianAvgInvestmentRate}%`, good: investmentRate > indianAvgInvestmentRate },
          { label: 'Expense Ratio', value: `${spendingRate.toFixed(1)}%`, avg: `${indianAvgExpenseRatio}%`, good: spendingRate < indianAvgExpenseRatio },
          { label: 'Emergency Fund', value: `${runwayMonths.toFixed(1)} mo`, avg: '2.5 mo', good: runwayMonths > 2.5 },
        ].map((item, i) => (
          <View key={i} style={styles.item}>
            <Text style={[styles.itemLabel, { color: colors.textSecondary }]}>{item.label}</Text>
            <Text style={[styles.itemValue, { color: item.good ? Accent.emerald : Accent.ruby }]}>{item.value}</Text>
            <Text style={[styles.itemAvg, { color: colors.textSecondary }]}>Avg: {item.avg}</Text>
          </View>
        ))}
      </View>
      <Text style={[styles.source, { color: colors.textSecondary }]}>Sources: RBI, NSO, SEBI Household Surveys 2024</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  card: { borderRadius: 20, borderWidth: 1, padding: 20, marginBottom: 16 },
  header: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 16 },
  icon: { width: 48, height: 48, borderRadius: 14, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 18, fontFamily: 'DM Sans', fontWeight: '700' as any },
  subtitle: { fontSize: 12, fontFamily: 'DM Sans', marginTop: 2 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 0 },
  item: { width: '50%', paddingVertical: 8, paddingHorizontal: 4 },
  itemLabel: { fontSize: 11, fontFamily: 'DM Sans', marginBottom: 2 },
  itemValue: { fontSize: 18, fontFamily: 'DM Sans', fontWeight: '700' as any },
  itemAvg: { fontSize: 10, fontFamily: 'DM Sans', marginTop: 1 },
  source: { fontSize: 10, fontFamily: 'DM Sans', marginTop: 8, textAlign: 'center', fontStyle: 'italic' },
});
